# Day 17 - Teacher Negative Access Tests

Date: 2026-03-29
Status: Completed
Related plan: project_notes/daily_notes/MASTER_35_DAY_EXECUTION_PLAN.md

## 1) Goal

Add negative access tests to ensure teacher role cannot access admin-only routes and actions.

## 2) Implemented

Updated file:
- `tests/test_permissions.py`

New test class:
- `TeacherNegativeAccessRouteTests`

Covered admin-only routes (teacher should be redirected to login):
1. `GET /admin/dashboard`
2. `GET /admin/users`
3. `GET /admin/class-assignments`
4. `GET /admin/security/permission-audit`
5. `GET /admin/security/admin-operations`
6. `POST /admin/users/1/role`
7. `POST /admin/users/1/lock`
8. `POST /admin/classes/1/assign-teacher`

Assertion strategy:
- HTTP status code is `302`
- redirect target contains `/login`

## 3) Validation

Executed:
- `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe -m unittest tests.test_permissions`

Result:
- `Ran 46 tests ... OK`

Diagnostics:
- no editor errors in touched files.

## 4) Day 17 Exit Gate

Day 17 is complete because:
1. teacher negative access coverage now includes all core admin routes added in Week 3,
2. both read and state-changing admin endpoints are validated,
3. route guard behavior is explicitly asserted by redirect target.

## 5) Next Day Input (Day 18)

1. Add student negative access tests for teacher/admin endpoints.
2. Expand student ownership boundary tests for class/session operations.
3. Keep assertion pattern aligned: status + redirect/json expectations.
