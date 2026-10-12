"""Point the test run at a separate PostgreSQL database before `app` is imported.

Uses TEST_DATABASE_URL when set, otherwise DATABASE_URL with the database name suffixed by `_test`.
The test database is created on first use; the run aborts if it would hit the main database.
"""
import os

import psycopg2
from psycopg2 import sql
from sqlalchemy.engine import make_url

from env_config import load_dotenv, resolve_database_url

load_dotenv()
_main_url = make_url(resolve_database_url())
_test_url = make_url(os.getenv('TEST_DATABASE_URL') or _main_url.set(database=f'{_main_url.database}_test'))

if (_test_url.host, _test_url.port, _test_url.database) == (_main_url.host, _main_url.port, _main_url.database):
    raise RuntimeError('Test database must differ from DATABASE_URL; refusing to run tests against the main database.')


def _ensure_database_exists(url) -> None:
    conn = psycopg2.connect(
        dbname='postgres',
        user=url.username,
        password=url.password,
        host=url.host or 'localhost',
        port=url.port or 5432,
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM pg_database WHERE datname = %s', (url.database,))
            if cur.fetchone() is None:
                cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(url.database)))
    finally:
        conn.close()


_ensure_database_exists(_test_url)
os.environ['DATABASE_URL'] = _test_url.render_as_string(hide_password=False)


import pytest  # noqa: E402


@pytest.fixture(scope='session', autouse=True)
def _sync_id_sequences():
    """Some tests insert rows with explicit ids (max + 100) and never clean up; move the serial sequences
    past them so later sequence-generated ids cannot collide."""
    from sqlalchemy import text

    from app import app, db

    with app.app_context():
        for table in ('users', 'classes', 'courses'):
            db.session.execute(text(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"GREATEST((SELECT COALESCE(MAX(id), 1) FROM {table}), 1))"
            ))
        db.session.commit()
    yield
