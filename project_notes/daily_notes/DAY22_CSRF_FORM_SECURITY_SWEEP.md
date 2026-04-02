# Day 22 - CSRF and Form Security Sweep

Date: 2026-03-29
Status: Completed
Related plan: project_notes/daily_notes/MASTER_35_DAY_EXECUTION_PLAN.md

## 1) Goal

Introduce lightweight CSRF protection for state-changing admin forms and verify route-level enforcement with tests.

## 2) Implemented

Updated file:
- `app.py`

Security additions:
1. Added CSRF token lifecycle helpers:
- `_get_or_create_csrf_token()`
- `_is_csrf_token_valid()`

2. Added template-level CSRF helper exposure:
- `csrf_token` is now available from context processor

3. Added route guard decorator:
- `@csrf_protect`
- checks POST/PUT/PATCH/DELETE requests
- validates `csrf_token` form field or `X-CSRF-Token` header
- rejects invalid/missing token with guarded redirect

4. Applied CSRF guard to admin mutating routes:
- `POST /admin/users/<int:user_id>/role`
- `POST /admin/users/<int:user_id>/lock`
- `POST /admin/classes/<int:class_id>/assign-teacher`

Updated files:
- `templates/admin_user_inventory.html`
- `templates/admin_class_assignments.html`

Form updates:
1. Added hidden `csrf_token` input to role update form
2. Added hidden `csrf_token` input to lock/unlock form
3. Added hidden `csrf_token` input to class assignment form

Updated file:
- `tests/test_permissions.py`

Test updates:
1. Admin integration POST calls now include CSRF token payload
2. Added explicit rejection test for missing CSRF token
3. Preserved DB state assertions for rejected mutation requests

## 3) Validation

Executed:
- `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe -m unittest tests.test_permissions`

Result:
- `Ran 70 tests ... OK`

Diagnostics:
- no editor errors in touched files.

## 4) Day 22 Exit Gate

Day 22 is complete because:
1. high-risk admin forms now require valid CSRF token,
2. templates are aligned with server-side CSRF checks,
3. missing-token mutation is blocked and test-proven,
4. test suite remains green.

## 5) Next Day Input (Day 23)

1. Start rate limiting for sensitive routes (login and admin mutation endpoints).
2. Define per-endpoint limits and safe default policy.
3. Add tests for over-limit and reset behavior.
