# Developer Guide

## 1. Local Setup
1. Create environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Configure app variables: copy `.env.example` to `.env` and set at least `DATABASE_URL` (PostgreSQL, required) and `FLASK_SECRET_KEY`. Every other variable is documented there with its default. Shell variables override `.env`.

3. Start app:

```powershell
python app.py
```

## 2. Project Structure (Key Files)
- `app.py`: routes, auth, permission checks, metrics, security middleware.
- `models.py`: SQLAlchemy models.
- `env_config.py`: `.env` loading and `DATABASE_URL` resolution, shared by the app and Alembic.
- `templates/`: Jinja templates.
- `scripts/`: `seed_production_data.py` (demo data + demo accounts), `bootstrap_first_admin.py`, `backup_db.py` (pg_dump).
- `tests/`: permission/security and UI smoke tests; `conftest.py` selects the test database.

## 3. Database and Migration
- PostgreSQL is the only supported database; the app stops with a clear error if `DATABASE_URL` is missing or not PostgreSQL.
- On startup the app runs `db.create_all()` and adds newer columns with `_ensure_column(...)`, so a fresh empty database works without running migrations.
- Alembic files are in `migrations/`; `migrations/env.py` reads the same `DATABASE_URL`.
- For schema changes: update the model, add an Alembic revision and/or an `_ensure_column` entry, and test on a local database.

## 4. Testing Strategy
- Tests run against a separate database: `TEST_DATABASE_URL`, or `<main database>_test` (created automatically). They never touch the main database.
- Full suite:

```powershell
python -m pytest tests
```

- Fast security/permission regression:

```powershell
python -m pytest tests/test_permissions.py
```

- UI smoke checks:

```powershell
python -m pytest tests/test_ui_smoke.py
```

- Translation keys: `./check_i18n.ps1` must print "i18n check passed".
- Before merging: run the full suite and the i18n check.

## 5. Security Baseline
- CSRF checks on state-changing routes.
- Role-permission mapping and endpoint permission enforcement.
- Rate limits for login and admin mutation paths.
- Login failure lockout controls.
- Security response headers (CSP, X-Frame-Options, nosniff, referrer policy).

## 6. Maintenance Checklist
- Back up the database with `python scripts/backup_db.py --keep 10`; restore with `pg_restore --clean --if-exists -d <DATABASE_URL> <file>.dump`.
- Review request metrics and health status pages.
- Inspect lock/role changes in admin operation audit.
- Keep dependencies updated and re-run tests.

## 7. Contribution Rules
- Prefer small, targeted changes.
- Add or update tests for behavior changes.
- Avoid breaking route contracts used by existing templates.
