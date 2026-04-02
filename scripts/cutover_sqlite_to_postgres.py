import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import MetaData, create_engine, func, insert, select, text
from sqlalchemy.engine import Engine

ROOT_DIR = Path(__file__).resolve().parents[1]
SQLITE_PATH = ROOT_DIR / 'instance' / 'attendance.db'


def _normalize_pg_url(url: str) -> str:
    normalized = (url or '').strip()
    if normalized.startswith('postgres://'):
        normalized = normalized.replace('postgres://', 'postgresql://', 1)
    return normalized


def _require_pg_url() -> str:
    url = _normalize_pg_url(os.getenv('DATABASE_URL', ''))
    if not url:
        raise RuntimeError('DATABASE_URL is not set. Provide a PostgreSQL connection URL.')
    if not url.startswith('postgresql://'):
        raise RuntimeError('DATABASE_URL must start with postgresql:// (or postgres://).')
    return url


def _run_alembic_upgrade(pg_url: str) -> tuple[int, str]:
    env = os.environ.copy()
    env['ALEMBIC_DB_URL'] = pg_url
    cmd = [sys.executable, '-m', 'alembic', 'upgrade', 'head']
    completed = subprocess.run(cmd, cwd=str(ROOT_DIR), env=env, capture_output=True, text=True)
    output = ((completed.stdout or '') + (completed.stderr or '')).strip()
    return completed.returncode, output


def _reflect(engine: Engine) -> MetaData:
    md = MetaData()
    md.reflect(bind=engine)
    return md


def _table_count(engine: Engine, table) -> int:
    with engine.connect() as conn:
        return int(conn.execute(select(func.count()).select_from(table)).scalar_one())


def _truncate_target(engine: Engine, table_names: list[str]) -> None:
    if not table_names:
        return
    names_sql = ', '.join(f'"{name}"' for name in table_names)
    with engine.begin() as conn:
        conn.execute(text(f'TRUNCATE TABLE {names_sql} RESTART IDENTITY CASCADE'))


def _copy_table(source_engine: Engine, tgt_conn, source_table, target_table, chunk_size: int = 1000):
    """Copy rows from source_table to target_table using a pre-opened target connection."""
    copied = 0
    with source_engine.connect() as src_conn:
        rows = src_conn.execute(select(source_table)).mappings()
        batch = []
        for row in rows:
            batch.append(dict(row))
            if len(batch) >= chunk_size:
                tgt_conn.execute(insert(target_table), batch)
                copied += len(batch)
                batch.clear()
        if batch:
            tgt_conn.execute(insert(target_table), batch)
            copied += len(batch)
    return copied


def _sync_sequences(engine: Engine, table_names: list[str]) -> dict[str, int]:
    """Advance PostgreSQL sequences to max(id) for copied tables to avoid PK collisions."""
    updated = {}
    if not table_names:
        return updated

    with engine.begin() as conn:
        for table_name in table_names:
            # Only apply to tables that use the conventional integer primary key column.
            has_id_col = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = :table_name AND column_name = 'id'
                    """
                ),
                {'table_name': table_name},
            ).scalar()
            if not has_id_col:
                continue

            sequence_name = conn.execute(
                text("SELECT pg_get_serial_sequence(:qualified_table, 'id')"),
                {'qualified_table': f'public.{table_name}'},
            ).scalar()
            if not sequence_name:
                continue

            max_id = conn.execute(text(f'SELECT COALESCE(MAX(id), 0) FROM "{table_name}"')).scalar() or 0
            conn.execute(
                text('SELECT setval(:seq_name, :next_value, false)'),
                {'seq_name': sequence_name, 'next_value': int(max_id) + 1},
            )
            updated[table_name] = int(max_id) + 1

    return updated


def main():
    parser = argparse.ArgumentParser(description='Cut over SQLite data into PostgreSQL target using Alembic + data copy.')
    parser.add_argument('--output-dir', default='project_notes/closeout')
    parser.add_argument('--skip-alembic', action='store_true', help='Skip alembic upgrade step if schema already applied.')
    args = parser.parse_args()

    if not SQLITE_PATH.exists():
        raise RuntimeError(f'SQLite source database not found: {SQLITE_PATH}')

    pg_url = _require_pg_url()

    source_engine = create_engine(f"sqlite:///{SQLITE_PATH.as_posix()}")
    target_engine = create_engine(pg_url)

    report = {
        'captured_at_utc': dt.datetime.now(dt.UTC).isoformat().replace('+00:00', 'Z'),
        'status': 'running',
        'steps': [],
        'table_results': [],
    }

    try:
        # 1) Ensure target schema exists
        if args.skip_alembic:
            report['steps'].append({'name': 'alembic_upgrade', 'passed': True, 'detail': 'skipped by flag'})
        else:
            code, out = _run_alembic_upgrade(pg_url)
            passed = code == 0
            report['steps'].append({'name': 'alembic_upgrade', 'passed': passed, 'detail': out[-4000:]})
            if not passed:
                raise RuntimeError('Alembic upgrade failed.')

        # 2) Reflect source/target tables
        source_md = _reflect(source_engine)
        target_md = _reflect(target_engine)

        source_tables = {t.name: t for t in source_md.sorted_tables}
        target_tables = {t.name: t for t in target_md.sorted_tables}

        # Skip alembic_version to avoid version ledger conflicts.
        copy_order = [t.name for t in target_md.sorted_tables if t.name in source_tables and t.name != 'alembic_version']

        report['steps'].append(
            {
                'name': 'table_mapping',
                'passed': len(copy_order) > 0,
                'detail': {
                    'source_tables': len(source_tables),
                    'target_tables': len(target_tables),
                    'copy_tables': copy_order,
                },
            }
        )
        if not copy_order:
            raise RuntimeError('No overlapping tables found for copy.')

        # 3) Truncate target tables in one go (FK-safe with CASCADE)
        _truncate_target(target_engine, copy_order)
        report['steps'].append({'name': 'truncate_target', 'passed': True, 'detail': {'tables': copy_order}})

        # 4) Copy and verify row counts table-by-table (FK checks disabled for the session)
        # 4) Copy all tables in a single transaction with FK checks disabled
        copied_counts: dict[str, int] = {}
        with target_engine.begin() as tgt_conn:
            tgt_conn.execute(text("SET session_replication_role = 'replica'"))
            for table_name in copy_order:
                src_table = source_tables[table_name]
                tgt_table = target_tables[table_name]
                copied_counts[table_name] = _copy_table(source_engine, tgt_conn, src_table, tgt_table)
            tgt_conn.execute(text("SET session_replication_role = 'origin'"))
        # Transaction committed — verify row counts against committed data

        all_ok = True
        for table_name in copy_order:
            src_table = source_tables[table_name]
            tgt_table = target_tables[table_name]

            src_count = _table_count(source_engine, src_table)
            copied = copied_counts[table_name]
            tgt_count = _table_count(target_engine, tgt_table)

            ok = src_count == tgt_count == copied
            all_ok = all_ok and ok
            report['table_results'].append(
                {
                    'table': table_name,
                    'source_count': src_count,
                    'copied_count': copied,
                    'target_count': tgt_count,
                    'passed': ok,
                }
            )

        report['steps'].append({'name': 'row_count_verification', 'passed': all_ok, 'detail': 'See table_results'})
        report['status'] = 'completed' if all_ok else 'failed'
        if not all_ok:
            raise RuntimeError('Row count verification failed for one or more tables.')

        sequence_updates = _sync_sequences(target_engine, copy_order)
        report['steps'].append(
            {
                'name': 'sequence_sync',
                'passed': True,
                'detail': {
                    'updated_sequences': sequence_updates,
                    'updated_count': len(sequence_updates),
                },
            }
        )

    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = str(exc)

    out_dir = ROOT_DIR / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime('%Y-%m-%dT%H-%M-%SZ')
    out_path = out_dir / f'sqlite_to_postgres_cutover_{stamp}.json'
    out_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

    print(f'SQLITE_TO_POSTGRES_REPORT {out_path.as_posix()}')
    print(f'SQLITE_TO_POSTGRES_STATUS {report["status"]}')

    if report['status'] != 'completed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
