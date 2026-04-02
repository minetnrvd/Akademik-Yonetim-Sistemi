# Day 23 - Rate Limiting on Sensitive Routes

Date: 2026-03-29
Status: Completed
Related plan: project_notes/daily_notes/MASTER_35_DAY_EXECUTION_PLAN.md

## 1) Goal

Apply lightweight rate limiting to sensitive endpoints (login and admin mutation routes) and add test coverage for over-limit and reset behavior.

## 2) Implemented

Updated file:
- `app.py`

Rate limit components:
1. in-memory event store:
- `RATE_LIMIT_EVENTS`

2. helper functions:
- `_is_rate_limited(scope, key, limit, window_seconds, now_ts=None)`
- `_admin_mutation_rate_key()`
- `rate_limit_protect(...)` decorator

3. config knobs (bounded via existing safe parser):
- `LOGIN_RATE_LIMIT_MAX_ATTEMPTS` (default 8)
- `LOGIN_RATE_LIMIT_WINDOW_SECONDS` (default 300)
- `ADMIN_MUTATION_RATE_LIMIT_MAX` (default 30)
- `ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS` (default 60)

4. protected endpoints:
- login POST flow now checks login throttling before credential validation
- admin mutating routes now include `@rate_limit_protect(...)`:
  - `POST /admin/users/<int:user_id>/role`
  - `POST /admin/users/<int:user_id>/lock`
  - `POST /admin/classes/<int:class_id>/assign-teacher`

Behavior notes:
- on over-limit, request is redirected with warning flash
- successful login clears login bucket for that key

Updated file:
- `tests/test_permissions.py`

New tests:
1. `RateLimitHelperTests`
- over-limit branch assertion
- window reset branch assertion

2. `LoginRateLimitRouteTests`
- login POST throttling verification with temporary low threshold

## 3) Validation

Executed:
- `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe -m unittest tests.test_permissions`

Result:
- `Ran 73 tests ... OK`

Diagnostics:
- no editor errors in touched files.

## 4) Day 23 Exit Gate

Day 23 is complete because:
1. sensitive auth/admin mutation routes now enforce request throttling,
2. throttle logic is configurable and bounded,
3. over-limit and reset behavior are test-covered,
4. suite remains green after hardening.

## 5) Next Day Input (Day 24)

1. implement password policy checks (complexity + minimum length),
2. add brute-force friendly lockout/backoff alignment with login policy,
3. expand auth tests for weak-password rejection paths.
