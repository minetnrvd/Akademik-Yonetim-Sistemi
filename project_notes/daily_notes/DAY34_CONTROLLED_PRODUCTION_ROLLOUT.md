# Day 34 - Controlled Production Rollout

## Goal
Establish a gate-driven rollout decision flow and produce an approved canary rollout artifact.

## What Was Implemented

### 1) Controlled Rollout Gate Script
- Added `scripts/controlled_rollout.py`.
- Script gates:
  1. Latest Day 33 rehearsal report status is `ok`.
  2. Fresh pre-rollout backup is created.
  3. Regression tests are green.
  4. UAT smoke pass rate is 100%.
  5. `/health` returns valid snapshot payload.
- Output:
  - JSON decision report under `project_notes/rollout/`.
  - Console status line (`approved` or `blocked`).

### 2) Controlled Rollout Runbook
- Added `project_notes/CONTROLLED_PRODUCTION_ROLLOUT_RUNBOOK.md`.
- Includes command, enforced gates, outputs, and promotion rule.

### 3) Bug Fix During Execution
- First controlled rollout run was `blocked` due to rehearsal JSON parsing issue (BOM in report file).
- Updated script to read rehearsal JSON with `utf-8-sig`.
- Re-ran successfully.

## Final Successful Evidence
- Command:
  - `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe scripts/controlled_rollout.py --phase canary --include-qr-assets --uat-avg-threshold-ms 8.0`
- Report:
  - `project_notes/rollout/controlled_rollout_2026-03-29T23-31-27Z.json`
- Status:
  - `CONTROLLED_ROLLOUT_STATUS approved`
- Recommended action:
  - Proceed with canary rollout window and monitor health/metrics dashboards.

## Validation
- Regression tests re-run after script fix:
  - `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe -m unittest tests/test_permissions.py`
- Result:
  - `Ran 83 tests in 4.962s`
  - `OK`

## Outcome
- Controlled rollout process is now gate-based, repeatable, and evidence-backed.
- Project is ready for Day 35 post-go-live monitoring and closeout.
