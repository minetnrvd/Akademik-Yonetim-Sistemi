"""Environment loading shared by the app (app.py) and Alembic (migrations/env.py)."""
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def load_dotenv(path: str | None = None) -> None:
    """Load KEY=VALUE lines from a local .env file; real environment variables take precedence."""
    path = path or os.path.join(PROJECT_ROOT, '.env')
    if not os.path.isfile(path):
        return
    with open(path, encoding='utf-8-sig') as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if key:
                os.environ.setdefault(key, value)


def resolve_database_url() -> str:
    """Return the PostgreSQL URL from DATABASE_URL; the app has no other database backend."""
    url = (os.getenv('DATABASE_URL') or '').strip()
    if not url:
        raise RuntimeError(
            'DATABASE_URL is not set. Copy .env.example to .env and set a PostgreSQL URL, '
            'e.g. postgresql://postgres:password@localhost:5432/attendance'
        )
    # SQLAlchemy expects the postgresql:// prefix; accept Heroku-style postgres:// too.
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    if not url.startswith('postgresql'):
        raise RuntimeError('DATABASE_URL must point to PostgreSQL (postgresql://...).')
    return url
