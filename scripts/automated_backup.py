import argparse
import datetime
import hashlib
import json
import os
import shutil
from pathlib import Path


def sha256_of(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def resolve_db_file(project_root: Path) -> Path:
    candidates = [
        project_root / 'instance' / 'attendance.db',
        project_root / 'attendance.db',
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError('attendance.db not found in instance/ or project root')


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def run_backup(project_root: Path, include_assets: bool, retention: int) -> Path:
    source_db = resolve_db_file(project_root)
    backups_dir = project_root / 'backups'
    ensure_dir(backups_dir)

    timestamp = datetime.datetime.now(datetime.UTC).strftime('%Y%m%d_%H%M%S')
    backup_dir = backups_dir / f'auto_{timestamp}'
    ensure_dir(backup_dir)

    target_db = backup_dir / 'attendance.db'
    shutil.copy2(source_db, target_db)

    migrations_src = project_root / 'migrations'
    if migrations_src.exists() and migrations_src.is_dir():
        shutil.copytree(migrations_src, backup_dir / 'migrations', dirs_exist_ok=True)

    copied_assets = []
    if include_assets:
        for rel in ('static/qrcodes', 'static/qr_codes'):
            src = project_root / rel
            if src.exists() and src.is_dir():
                dst = backup_dir / rel
                ensure_dir(dst.parent)
                shutil.copytree(src, dst, dirs_exist_ok=True)
                copied_assets.append(rel)

    manifest = {
        'backup_time_utc': datetime.datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z'),
        'project_root': str(project_root),
        'source_db': str(source_db),
        'backup_db': str(target_db),
        'db_sha256': sha256_of(target_db),
        'include_assets': include_assets,
        'copied_assets': copied_assets,
    }
    (backup_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')

    if retention > 0:
        auto_backups = sorted([p for p in backups_dir.glob('auto_*') if p.is_dir()])
        stale = auto_backups[:-retention]
        for old in stale:
            shutil.rmtree(old, ignore_errors=True)

    return backup_dir


def verify_backup(backup_dir: Path) -> bool:
    db_file = backup_dir / 'attendance.db'
    manifest_file = backup_dir / 'manifest.json'
    if not db_file.exists() or not manifest_file.exists():
        return False

    manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
    expected = manifest.get('db_sha256', '')
    if not expected:
        return False
    return sha256_of(db_file) == expected


def main() -> int:
    parser = argparse.ArgumentParser(description='Create automated backup snapshot with retention policy.')
    parser.add_argument('--project-root', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--include-assets', action='store_true', help='Copy QR asset folders into backup.')
    parser.add_argument('--retention', type=int, default=10, help='Number of auto backups to keep.')
    parser.add_argument('--verify', action='store_true', help='Verify backup hash after creation.')
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    backup_dir = run_backup(project_root, include_assets=args.include_assets, retention=max(1, args.retention))

    if args.verify:
        ok = verify_backup(backup_dir)
        if not ok:
            print(f'BACKUP_VERIFY_FAIL {backup_dir}')
            return 1

    print(f'BACKUP_OK {backup_dir}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
