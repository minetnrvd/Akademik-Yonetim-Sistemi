import datetime as dt
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SQLITE_DB = ROOT_DIR / 'instance' / 'attendance.db'
MIGRATIONS_DIR = ROOT_DIR / 'migrations' / 'versions'


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest().upper()


def _run(cmd):
    completed = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True)
    output = ((completed.stdout or '') + (completed.stderr or '')).strip()
    return completed.returncode, output


def _sqlite_inventory(db_path: Path):
    if not db_path.exists():
        return {'exists': False, 'tables': [], 'row_counts': {}, 'error': 'attendance.db not found'}

    conn = sqlite3.connect(str(db_path))
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]

        key_tables = [
            'users',
            'students',
            'classes',
            'attendance_sessions',
            'attendance_records',
            'permission_audit_logs',
            'admin_operation_logs',
        ]
        row_counts = {}
        for table in key_tables:
            try:
                row_counts[table] = int(conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0])
            except sqlite3.Error:
                row_counts[table] = None

        return {
            'exists': True,
            'tables': tables,
            'table_count': len(tables),
            'row_counts': row_counts,
        }
    finally:
        conn.close()


def _resolve_target_db_url():
    url = (os.getenv('DATABASE_URL') or '').strip()
    if not url:
        return {'configured': False, 'is_postgres': False, 'value_masked': None}

    normalized = url.replace('postgres://', 'postgresql://', 1) if url.startswith('postgres://') else url
    is_pg = normalized.startswith('postgresql://')

    masked = normalized
    if '@' in normalized and '://' in normalized:
        scheme, rest = normalized.split('://', 1)
        creds_host = rest.split('@', 1)
        if len(creds_host) == 2:
            masked = f"{scheme}://***@{creds_host[1]}"

    return {'configured': True, 'is_postgres': is_pg, 'value_masked': masked}


def main():
    report_dir = ROOT_DIR / 'project_notes' / 'closeout'
    report_dir.mkdir(parents=True, exist_ok=True)

    inventory = _sqlite_inventory(SQLITE_DB)

    backup_cmd = [
        'powershell',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        str(ROOT_DIR / 'scripts' / 'backup_restore_drill.ps1'),
        '-Mode',
        'backup',
        '-ProjectRoot',
        str(ROOT_DIR),
        '-IncludeQrAssets',
    ]
    backup_code, backup_output = _run(backup_cmd)

    backup_dir = None
    if 'BACKUP_OK' in backup_output:
        backup_dir = backup_output.split('BACKUP_OK', 1)[1].strip().splitlines()[0].strip()

    migration_files = sorted(MIGRATIONS_DIR.glob('*.py')) if MIGRATIONS_DIR.exists() else []
    db_hash = _sha256_file(SQLITE_DB) if SQLITE_DB.exists() else None
    target_db = _resolve_target_db_url()

    gates = {
        'gate_1_sqlite_inventory_available': inventory.get('exists', False),
        'gate_2_pre_migration_backup_created': backup_code == 0 and bool(backup_dir),
        'gate_3_migration_chain_present': len(migration_files) > 0,
        'gate_4_postgres_target_configured': target_db['configured'] and target_db['is_postgres'],
    }

    # Day 11 in this environment is readiness + freeze checkpoint.
    # PostgreSQL target may be intentionally pending in local Windows env.
    status = 'READY_WITH_ENV_PENDING' if all([gates['gate_1_sqlite_inventory_available'], gates['gate_2_pre_migration_backup_created'], gates['gate_3_migration_chain_present']]) else 'BLOCKED'

    report = {
        'date': dt.datetime.now(dt.UTC).date().isoformat(),
        'day': 'Day 11 (DB Migration Readiness)',
        'status': status,
        'sqlite_source': {
            'path': str(SQLITE_DB),
            'sha256': db_hash,
            'inventory': inventory,
        },
        'backup_checkpoint': {
            'command': 'powershell -ExecutionPolicy Bypass -File scripts/backup_restore_drill.ps1 -Mode backup -IncludeQrAssets',
            'exit_code': backup_code,
            'output': backup_output,
            'backup_dir': backup_dir,
        },
        'migration_assets': {
            'migrations_dir': str(MIGRATIONS_DIR),
            'migration_file_count': len(migration_files),
            'latest_migrations': [p.name for p in migration_files[-5:]],
        },
        'target_database': target_db,
        'gates': gates,
        'next_actions': [
            'Provision PostgreSQL target and set DATABASE_URL=postgresql://... in deployment environment',
            'Run Alembic upgrade against PostgreSQL target',
            'Perform data move strategy validation (dual-write or cutover window)',
            'Run full regression + UAT after DB cutover',
        ],
    }

    stamp = dt.datetime.now(dt.UTC).strftime('%Y-%m-%dT%H-%M-%SZ')
    out_path = report_dir / f'day11_db_migration_readiness_{stamp}.json'
    out_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

    print(f'DAY11_DB_READINESS_REPORT {out_path.as_posix()}')
    print(f'DAY11_DB_READINESS_STATUS {status}')
    for name, passed in gates.items():
        marker = 'PASS' if passed else 'PENDING' if name == 'gate_4_postgres_target_configured' else 'FAIL'
        print(f'[{marker}] {name}')

    if status == 'BLOCKED':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
