# Day 5 - Action Permission Split (Controlled)

Date: 2026-03-28

## Scope Completed

Introduced action-level permission checks for mixed GET+POST endpoints without removing existing route-level guards.

## Key Changes

1. Route-level permission mapping split to read-level for mixed pages:
- `teacher_account` -> `teacher.account.read`
- `student_account` -> `student.account.read`
- `student_absence` -> `student.absence.read`

2. Role permission sets expanded with update/action permissions:
- `teacher.account.update`
- `student.account.update`
- `student.absence.update`
- `student.dashboard.calendar.update`

3. Added reusable helpers:
- `_log_permission_denied(permission_key)`
- `ensure_permission(permission_key, redirect_endpoint='login')`

4. Action-level enforcement added inside handlers:
- `teacher_account` POST requires `teacher.account.update`
- `student_account` POST requires `student.account.update`
- `student_dashboard` POST (calendar add/delete) requires `student.dashboard.calendar.update`
- `student_absence` POST (join class) requires `student.absence.update`

## Safety Notes

- Existing `@role_required(...)` checks are unchanged.
- Existing `@permission_required()` route checks are unchanged.
- This rollout adds finer control for write actions while keeping previous behavior for allowed users.

## Validation

- Editor diagnostics: no errors in app.py
- Syntax check: `py -m py_compile app.py` passed

## Next Step (Day 6)

1. Add admin-visible denied-access report endpoint.
2. Introduce per-action permission constants to reduce typo risk.
3. Start unit tests for permission helper and mixed GET/POST handlers.
