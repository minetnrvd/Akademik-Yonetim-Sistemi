# Day 27 - Health Checks and Alert Thresholds

Date: 2026-03-29
Status: Completed
Related plan: project_notes/daily_notes/MASTER_35_DAY_EXECUTION_PLAN.md

## 1) Goal

Provide operational health visibility with a health-check endpoint and threshold-based status evaluation using existing request metrics.

## 2) Implemented

Updated file:
- `app.py`

Health baseline additions:
1. Threshold configs
- `HEALTH_WARN_ERROR_RATE_PCT` (default 5)
- `HEALTH_WARN_P95_MS` (default 1000)

2. Health helpers
- `_percentile(values, pct)`
- `_build_health_snapshot()`
  - DB probe (`SELECT 1`)
  - error rate calculation
  - latency summary (avg + p95 estimate)
  - status decision (`healthy`, `degraded`, `unhealthy`)

3. Endpoints
- Public health endpoint:
  - `GET /health`
  - returns JSON snapshot
  - status code `200` for healthy/degraded, `503` for unhealthy

- Admin health status page:
  - `GET /admin/security/health-status`
  - protected with admin role + metrics permission

4. Dashboard integration
- Added quick link:
  - `/admin/security/health-status`

5. Permission mapping
- `admin_health_status_report` -> `ADMIN_METRICS_READ`

New template:
- `templates/admin_health_status.html`
- includes:
  - status summary cards,
  - thresholds,
  - error/latency snapshot table,
  - reasons and DB error fields.

Updated tests:
- `tests/test_permissions.py`

Added coverage:
1. permission map assertion for health status route
2. health endpoint JSON snapshot shape test
3. admin integration test access to health status page

## 3) Validation

Executed:
- `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe -m unittest tests.test_permissions`

Result:
- `Ran 82 tests ... OK`

Diagnostics:
- no editor errors in touched files.

## 4) Day 27 Exit Gate

Day 27 is complete because:
1. health-check endpoint exists with machine-readable status,
2. admin can review threshold-based health summary in UI,
3. health status integrates DB and request-metric signals,
4. permission + integration tests remain green.

## 5) Next Day Input (Day 28)

1. query/index optimization pass on heavy admin and history queries,
2. identify top high-frequency endpoints from metrics page,
3. apply low-risk DB/index improvements and verify behavior.
