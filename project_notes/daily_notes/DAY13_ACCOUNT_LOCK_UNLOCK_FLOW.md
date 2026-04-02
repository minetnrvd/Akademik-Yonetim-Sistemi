# Day 13 - Account Lock/Unlock Flow

Date: 2026-03-29
Scope: Week 3 - Admin Operations

## Goal

Implement admin-controlled account lock/unlock flow with safe guards, audit logging, and negative tests.

## Implemented

1. User lock state model
- Added `users.is_locked` boolean field to `User` model.
- Added migration `7f3b8b7ef2b2_add_user_lock_flag.py`.

2. Login and session enforcement
- Login now blocks locked users with a clear message.
- Added `enforce_account_lock_policy` `before_request` guard.
- If an already logged-in account becomes locked, session is cleared and user is redirected to login.

3. Permission and route integration
- Added permission: `ADMIN_USER_LOCK_TOGGLE` (`admin.user.lock_toggle`).
- Added permission mapping for `admin_toggle_user_lock`.
- Added admin route: `POST /admin/users/<int:user_id>/lock`.

4. Validation and safety rules
- Added `validate_admin_lock_update` helper.
- Rules:
  - Only admin can toggle lock state.
  - Admin cannot lock own account.
  - System must keep at least one unlocked admin.

5. Admin operation audit coverage
- Lock/unlock operations are logged with `_log_admin_operation`.
- `status` values cover `rejected`, `noop`, `error`, `updated`.

6. Admin inventory UI updates
- Added account status column (Active/Locked).
- Added lock/unlock action button per user.
- Self-action is blocked in UI for lock operation.

## Validation

- Unit tests executed:
  - `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe -m unittest tests.test_permissions`
- Result: `OK` (25 tests).
- Added new tests for lock permission map and lock validation helper.

## Notes

- Existing `role_required` and permission guards remain unchanged.
- Lock guard is centralized at request level to enforce consistent behavior.
- Migration is written idempotently for safer repeated local runs.
