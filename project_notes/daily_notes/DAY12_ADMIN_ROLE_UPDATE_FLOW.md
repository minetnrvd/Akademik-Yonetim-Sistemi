# Day 12 - Admin Role Update Flow

## Scope
- Implement a safe admin-only role update flow for users.
- Add operation-level audit logging for admin role changes.
- Extend permission tests with role-update denial/guard scenarios.

## Implemented Changes

### 1) Permission and endpoint integration
- Added `ADMIN_USER_UPDATE_ROLE` permission constant.
- Mapped `/admin/users/<int:user_id>/role` endpoint to `ADMIN_USER_UPDATE_ROLE` in permission map.
- Granted this permission to `admin` role only.

### 2) Role update validation and execution
- Added `validate_admin_role_update(actor_user, target_user, target_role)` helper with guardrails:
  - only admin can perform updates,
  - target role must be in allowed role set,
  - admin cannot change their own role,
  - last active admin cannot be downgraded.
- Added `admin_update_user_role(user_id)` route (POST) protected by `permission_required(ADMIN_USER_UPDATE_ROLE)`.
- Added student profile auto-create when target role becomes `student` and profile is missing.

### 3) Admin operation audit model and logging
- Added `AdminOperationLog` model in `models.py`.
- Added `_log_admin_operation(...)` helper in `app.py` to persist role-update operation outcomes.

### 4) UI updates
- Updated admin user inventory table with inline role update controls per user row.
- Prevented self-role update action in UI for current admin user.

### 5) Tests
- Extended `tests/test_permissions.py` coverage:
  - permission map assertion for role update endpoint,
  - non-admin denied,
  - invalid target role denied,
  - self-role-change denied,
  - last-admin downgrade denied.

## Migration
- Created migration: `1d65a70de5ac_add_admin_operation_logs.py`.
- Trimmed autogenerate noise and kept migration focused on `admin_operation_logs` table only.
- Added idempotent table existence checks in upgrade/downgrade.

## Verification
- Applied migration:
  - `alembic upgrade head` -> success.
- Revision check:
  - `alembic current` -> `1d65a70de5ac (head)`.
- Syntax check:
  - `python -m py_compile app.py models.py attendance.py qr.py qr_manager.py` -> success.
- Permission test suite:
  - `python -m unittest tests.test_permissions` -> `Ran 21 tests ... OK`.

## Notes / Risks
- SQLAlchemy emitted existing `datetime.utcnow()` deprecation warnings during tests (pre-existing pattern). No functional regression observed in Day 12 scope.
- Next day (Day 13) can build on this by adding account lock/unlock workflow and extending admin operation audit reporting.
