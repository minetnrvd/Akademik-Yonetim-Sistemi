# Day 26 - Error and Latency Metric Instrumentation

Date: 2026-03-29
Status: Completed
Related plan: project_notes/daily_notes/MASTER_35_DAY_EXECUTION_PLAN.md

## 1) Goal

Add lightweight request-level instrumentation for latency and error tracking, then expose a protected admin metrics view.

## 2) Implemented

Updated file:
- `app.py`

Instrumentation core:
1. Added in-memory metrics store:
- `REQUEST_METRICS`
- tracks:
  - start time
  - total request count
  - 4xx count
  - 5xx count
  - per-endpoint latency stats

2. Added request timing hooks:
- `@app.before_request def mark_request_start_time()`
- `@app.after_request def collect_request_metrics(response)`

3. Added slow-request threshold config:
- `METRICS_SLOW_REQUEST_MS` (bounded)
- logs warning for requests above threshold

Admin metrics visibility:
1. Added permission:
- `ADMIN_METRICS_READ`

2. Added endpoint mapping + role permission:
- `admin_request_metrics_report`

3. Added admin route:
- `GET /admin/security/request-metrics`

4. Added dashboard quick link:
- `/admin/security/request-metrics`

5. Added template:
- `templates/admin_request_metrics.html`
- includes summary cards and endpoint metrics table

Updated file:
- `tests/test_permissions.py`

New/updated tests:
1. permission model includes admin metrics permission and route map check
2. request metric collection test confirms `GET /login` metrics capture
3. admin integration test now validates access to request metrics page
4. test file repaired and normalized after malformed patch conflict

## 3) Validation

Executed:
- `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe -m unittest tests.test_permissions`

Result:
- `Ran 80 tests ... OK`

Diagnostics:
- no editor errors in touched files.

## 4) Day 26 Exit Gate

Day 26 is complete because:
1. request latency/error counters are collected automatically per request,
2. admin can inspect aggregated metrics through protected UI,
3. permission model covers metrics endpoint explicitly,
4. regression suite remains green.

## 5) Next Day Input (Day 27)

1. design health-check route and alert threshold baseline,
2. define acceptable error/latency bounds from collected metrics,
3. add operational status panel for quick readiness checks.
