# QR Attendance Project

A Flask-based QR attendance tracking system with role-based access for student, teacher, and admin users.

## Features
- Role-based authentication and authorization.
- QR-based attendance session flow.
- Student attendance and absence tracking.
- Teacher class/session management and reports.
- Admin user operations, permission matrix, and audit screens.
- Backup/restore and production hardening scripts.

## Tech Stack
- Python 3.14+
- Flask + SQLAlchemy
- Alembic migrations
- Jinja2 templates
- Pytest / unittest

## Quick Start (Windows PowerShell)
1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Configure environment variables (example):

```powershell
$env:FLASK_SECRET_KEY="change-me"
$env:DATABASE_URL="sqlite:///attendance.db"
$env:SESSION_COOKIE_SECURE="0"
```

4. Run the app:

```powershell
python app.py
```

5. Open in browser:
- http://127.0.0.1:5000

## Configuration Notes
- `DATABASE_URL` is preferred. `postgres://` is normalized to `postgresql://`.
- Login protections include rate-limiting and lockout controls:
  - `LOGIN_RATE_LIMIT_MAX_ATTEMPTS`
  - `LOGIN_RATE_LIMIT_WINDOW_SECONDS`
  - `LOGIN_LOCK_MAX_FAILURES`
  - `LOGIN_LOCK_WINDOW_SECONDS`
- Cookie/session security is configurable via environment variables.

## Testing
Run full permission/security suite:

```powershell
python -m pytest tests/test_permissions.py
```

Run UI smoke tests:

```powershell
python -m pytest tests/test_ui_smoke.py
```

## Maintenance
- Backup/restore drills: see scripts under `scripts/` and reports under `project_notes/`.
- Health and request metrics: admin security pages.
- Log rotation: configured in app logging setup.

## Documentation
- User guide: `project_notes/USER_GUIDE.md`
- Developer guide: `project_notes/DEVELOPER_GUIDE.md`
- Operational runbooks: `project_notes/*RUNBOOK*.md`

## License
Internal project repository.
