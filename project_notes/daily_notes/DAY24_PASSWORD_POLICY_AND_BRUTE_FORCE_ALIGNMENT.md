# Day 24 - Password Policy and Brute-Force Alignment

Date: 2026-03-29
Status: Completed
Related plan: project_notes/daily_notes/MASTER_35_DAY_EXECUTION_PLAN.md

## 1) Goal

Enforce stronger password policy on registration/password-change paths and align auth hardening with existing login brute-force controls.

## 2) Implemented

Updated file:
- `app.py`

Password policy additions:
1. Configurable minimum password length:
- `PASSWORD_MIN_LENGTH` (bounded, default 10)

2. Central policy validator:
- `validate_password_policy(password, user_name=None, user_email=None)`
- checks:
  - minimum length
  - uppercase/lowercase/digit/special complexity
  - password does not contain user name
  - password does not contain email local-part

3. Enforcement points:
- registration flow (`POST /register`)
- teacher password change (`POST /teacher/account`, `action=change_password`)
- student password change (`POST /student/account`, `action=change_password`)

Brute-force alignment:
- existing login rate limiting from Day 23 remains active and unchanged,
- password strengthening now complements login throttling controls.

Updated file:
- `tests/test_permissions.py`

New test groups:
1. `PasswordPolicyTests`
- short password rejection
- complexity rejection
- name/email local-part rejection
- strong password acceptance

2. `RegisterPasswordPolicyRouteTests`
- weak password registration rejected
- DB row is not created for rejected weak password

## 3) Validation

Executed:
- `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe -m unittest tests.test_permissions`

Result:
- `Ran 78 tests ... OK`

Diagnostics:
- no editor errors in touched files.

## 4) Day 24 Exit Gate

Day 24 is complete because:
1. weak passwords are now blocked on creation and password update paths,
2. policy is centralized in a reusable validator,
3. auth hardening now combines password quality and login throttling,
4. regression suite is green with expanded policy tests.

## 5) Next Day Input (Day 25)

1. define backup/restore drill checklist for DB and critical artifacts,
2. script a local backup command path and restore verification steps,
3. produce an operational runbook note with pass/fail criteria.
