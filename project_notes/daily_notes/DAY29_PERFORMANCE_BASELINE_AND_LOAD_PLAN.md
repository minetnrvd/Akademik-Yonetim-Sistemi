# Day 29 - Performance Baseline and Load Plan

## Goal
Create a repeatable baseline measurement flow so Day 30 load/perf work can be compared against a known reference.

## What Was Implemented

### 1) Baseline Script
- Added `scripts/perf_baseline.py`.
- Script behavior:
  - Runs warmup + measured iterations per endpoint.
  - Measures avg/p50/p95/max latency and error rate.
  - Stores JSON output under `project_notes/performance/`.
  - Seeds temporary admin/teacher/class data and cleans up afterwards.

### 2) Performance Runbook
- Added `project_notes/PERFORMANCE_BASELINE_RUNBOOK.md`.
- Includes command, output format, measured endpoints, and comparability notes.

### 3) First Baseline Capture
- Executed:
  - `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe scripts/perf_baseline.py --warmup 5 --iterations 30`
- Generated report:
  - `project_notes/performance/baseline_2026-03-29T20-43-58Z.json`
- Console summary:
  - `/health`: avg=0.28ms, p95=0.35ms, error=0.0%
  - `/login`: avg=0.29ms, p95=0.33ms, error=0.0%
  - `/admin/security/request-metrics`: avg=0.72ms, p95=0.88ms, error=0.0%
  - `/teacher_dashboard`: avg=2.68ms, p95=3.18ms, error=0.0%

## Validation
- Test command:
  - `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe -m unittest tests/test_permissions.py`
- Result:
  - `Ran 82 tests in 3.781s`
  - `OK`

## Day 30 Ready State
- Baseline exists and is reproducible.
- Next day can focus on controlled load scenarios and delta analysis against this baseline.
