"""Back up the PostgreSQL database from DATABASE_URL with pg_dump (custom format).

Usage:
    python scripts/backup_db.py                 # writes backups/<db>_<timestamp>.dump
    python scripts/backup_db.py --keep 10       # also deletes all but the newest 10 dumps of this database

Restore:
    pg_restore --clean --if-exists -d <DATABASE_URL> backups/<file>.dump

pg_dump is taken from PG_DUMP, PATH, or the default Windows install folder.
"""
import argparse
import datetime
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy.engine import make_url

from env_config import load_dotenv, resolve_database_url


def _find_pg_dump() -> str:
    candidates = [os.getenv('PG_DUMP'), shutil.which('pg_dump')]
    candidates += sorted(glob.glob(r'C:\Program Files\PostgreSQL\*\bin\pg_dump.exe'), reverse=True)
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    raise SystemExit('pg_dump not found. Install PostgreSQL client tools or set PG_DUMP to its full path.')


def main() -> int:
    parser = argparse.ArgumentParser(description='Back up the app database with pg_dump.')
    parser.add_argument('--output-dir', default=str(ROOT_DIR / 'backups'))
    parser.add_argument('--keep', type=int, default=0, help='keep only the newest N dumps of this database (0 = keep all)')
    args = parser.parse_args()

    load_dotenv()
    url = make_url(resolve_database_url())
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out_file = out_dir / f'{url.database}_{stamp}.dump'

    env = dict(os.environ, PGPASSWORD=url.password or '')
    cmd = [
        _find_pg_dump(),
        '--format=custom',
        '--no-owner',
        f'--host={url.host or "localhost"}',
        f'--port={url.port or 5432}',
        f'--username={url.username}',
        f'--file={out_file}',
        url.database,
    ]
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        out_file.unlink(missing_ok=True)
        print('Backup failed.', file=sys.stderr)
        return result.returncode
    print(f'Backup written: {out_file} ({out_file.stat().st_size // 1024} KB)')

    if args.keep > 0:
        dumps = sorted(out_dir.glob(f'{url.database}_*.dump'), reverse=True)
        for old in dumps[args.keep:]:
            old.unlink()
            print(f'Removed old backup: {old.name}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
