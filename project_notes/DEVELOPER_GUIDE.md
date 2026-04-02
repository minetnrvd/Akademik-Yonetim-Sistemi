# Developer Guide

## 1. Local Setup
1. Create environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Configure app variables:
- `FLASK_SECRET_KEY`
- `DATABASE_URL`
- session and login hardening variables as needed.

3. Start app:

```powershell
python app.py
```

## 2. Project Structure (Key Files)
- `app.py`: routes, auth, permission checks, metrics, security middleware.
- `models.py`: SQLAlchemy models.
- `templates/`: Jinja templates.
- `scripts/`: operational scripts (backup, rollout, performance, rehearsal).
- `tests/`: permission/security and UI smoke tests.

## 3. Database and Migration
- Alembic files in `migrations/`.
- App supports `DATABASE_URL` normalization for PostgreSQL compatibility.
- For schema changes: create migration, test on local DB, verify rollback path.

## 4. Testing Strategy
- Fast security/permission regression:

```powershell
python -m pytest tests/test_permissions.py
```

- UI smoke checks:

```powershell
python -m pytest tests/test_ui_smoke.py
```

- Before merging: run both suites.

## 5. Security Baseline
- CSRF checks on state-changing routes.
- Role-permission mapping and endpoint permission enforcement.
- Rate limits for login and admin mutation paths.
- Login failure lockout controls.
- Security response headers (CSP, X-Frame-Options, nosniff, referrer policy).

## 6. Maintenance Checklist
- Verify backup script outputs and manifest hashes.
- Review request metrics and health status pages.
- Inspect lock/role changes in admin operation audit.
- Keep dependencies updated and re-run tests.

## 7. Contribution Rules
- Prefer small, targeted changes.
- Add or update tests for behavior changes.
- Avoid breaking route contracts used by existing templates.
