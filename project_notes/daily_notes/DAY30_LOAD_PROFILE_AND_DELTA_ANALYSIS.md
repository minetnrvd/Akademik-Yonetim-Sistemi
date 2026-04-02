# Day 30 - Load Profile and Delta Analysis

## Goal
Run a higher-iteration load profile and compare latency against Day 29 baseline.

## What Was Implemented

### 1) Load Profile + Compare Script
- Added `scripts/perf_load_compare.py`.
- Script behavior:
  - Runs higher-iteration request loops per endpoint.
  - Supports optional baseline JSON input.
  - Computes avg/p95/max/error metrics.
  - Computes baseline deltas (`avg_ms_delta`, `p95_ms_delta`).
  - Writes JSON report under `project_notes/performance/`.
  - Seeds temporary admin/teacher/class data and cleans up after run.

### 2) Runbook Update
- Updated `project_notes/PERFORMANCE_BASELINE_RUNBOOK.md` with Day 30 command and delta fields.

### 3) Day 30 Execution
- Executed:
  - `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe scripts/perf_load_compare.py --iterations 200 --baseline project_notes/performance/baseline_2026-03-29T20-43-58Z.json`
- Generated report:
  - `project_notes/performance/load_profile_2026-03-29T20-45-07Z.json`
- Console summary:
  - `/health`: avg=0.28ms, p95=0.32ms, error=0.0%, avg_delta=0.0, p95_delta=-0.03
  - `/login`: avg=0.36ms, p95=0.48ms, error=0.0%, avg_delta=0.07, p95_delta=0.15
  - `/admin/security/request-metrics`: avg=0.74ms, p95=0.95ms, error=0.0%, avg_delta=0.02, p95_delta=0.07
  - `/teacher_dashboard`: avg=2.81ms, p95=3.26ms, error=0.0%, avg_delta=0.13, p95_delta=0.08

## Validation
- Test command:
  - `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe -m unittest tests/test_permissions.py`
- Result:
  - `Ran 82 tests in 3.763s`
  - `OK`

## Outcome
- Load profile is in place and compared to baseline.
- Error rate remained 0.0% for all measured endpoints.
- Latency deltas are small and stable under this local profile.
