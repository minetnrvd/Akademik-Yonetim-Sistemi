# Performance Baseline Runbook

## Purpose
Collect a repeatable local latency baseline before/after performance changes.

## Command

```powershell
c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe scripts/perf_baseline.py --warmup 5 --iterations 30
```

## Output
- JSON report path: `project_notes/performance/baseline_<UTC_TIMESTAMP>.json`
- Console summary per endpoint:
  - average latency
  - p50 latency
  - p95 latency
  - max latency
  - error rate

## Endpoints Measured
- `/health`
- `/login`
- `/admin/security/request-metrics` (admin session)
- `/teacher_dashboard` (teacher session)

## Day 30 Load Profile Command

```powershell
c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe scripts/perf_load_compare.py --iterations 200 --baseline project_notes/performance/baseline_2026-03-29T20-43-58Z.json
```

## Load Output
- JSON report path: `project_notes/performance/load_profile_<UTC_TIMESTAMP>.json`
- Includes per-endpoint deltas vs baseline:
  - `avg_ms_delta`
  - `p95_ms_delta`

## Notes
- Uses Flask test client; no external HTTP server is required.
- Script seeds temporary admin/teacher/class records and cleans them up after run.
- Use same `warmup` and `iterations` values between runs for comparable data.
