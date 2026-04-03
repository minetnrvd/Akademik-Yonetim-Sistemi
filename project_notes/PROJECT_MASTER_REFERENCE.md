# Project Master Reference

## 1) Project Purpose
QR Attendance Project is a Flask-based attendance and university portal system with role-based workflows:
- Student: attendance scan/join/history/account
- Teacher: class/session creation, QR operations, reporting
- Admin: user/role/lock operations, permission and operation audits, health/metrics

The project has been production-prepared with backup/restore drills, controlled rollout gates, and SQLite -> PostgreSQL cutover.

## 2) Core Stack
- Python + Flask
- SQLAlchemy ORM
- Alembic migrations
- Jinja templates
- Pytest/unittest test suites
- PostgreSQL target deployment support

## 3) Main Application Files
- app.py: central routes, auth, permission checks, request metrics, security controls
- models.py: DB models and relationships
- migrations/: Alembic migration chain
- templates/: server-rendered HTML views
- static/: QR and static assets
- tests/: regression and UI smoke tests
- scripts/: operational and deployment automation scripts

## 4) Security and Reliability Controls
- CSRF validation for state-changing requests
- Role-permission mapping and endpoint guards
- Login rate limiting and lockout protections
- Security response headers (CSP, X-Frame-Options, nosniff, Referrer-Policy)
- Request metrics and health snapshot endpoint
- Backup + restore + hash verification runbooks

## 5) Operational Script Map
- scripts/backup_restore_drill.ps1: backup/restore/verify drill flow
- scripts/automated_backup.py: automated backup with retention and manifest
- scripts/release_rollback_rehearsal.ps1: release rehearsal + rollback proof
- scripts/controlled_rollout.py: gated canary rollout decision
- scripts/post_go_live_closeout.py: post-go-live closeout status generation
- scripts/cutover_sqlite_to_postgres.py: SQLite -> PostgreSQL migration + count verification + sequence sync
- scripts/uat_checklist.py: UAT smoke checks
- scripts/day9_alerting_validation.py: monitoring/alerting validation

## 6) Database and Cutover Status
- SQLite source used during development.
- PostgreSQL cutover completed successfully.
- Sequence synchronization step added in cutover to prevent PK collisions after migration.
- Row-count verification passed across copied tables.

## 7) Testing Baseline
- Full test suite: 99 passed
- Permission/security tests: 96 passed
- UI smoke tests: 3 passed

## 8) Deployment Gate Summary
- Rehearsal gate: PASS
- Controlled rollout gate: PASS
- Post-go-live closeout: CLOSED
- UAT smoke: 100%

## 9) Runbook Entry Points
- project_notes/RELEASE_ROLLBACK_REHEARSAL_RUNBOOK.md
- project_notes/CONTROLLED_PRODUCTION_ROLLOUT_RUNBOOK.md
- project_notes/POST_GO_LIVE_MONITORING_RUNBOOK.md
- project_notes/BACKUP_RESTORE_DRILL_RUNBOOK.md
- project_notes/POSTGRES_PRODUCTION_CUTOVER_CHECKLIST.md

## 10) Day-Report Consolidation Pointer
For condensed day-level outcomes and retained evidence artifacts, see:
- project_notes/REPORTS_CONSOLIDATED_SUMMARY.md

## 11) Current Working Conventions
- i18n keys required for UI text in TR/EN dictionaries
- Keep behavior stable; prefer small, test-backed refactors
- Use runbook-driven operations for release and rollback
