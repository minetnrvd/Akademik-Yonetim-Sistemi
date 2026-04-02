# Day 33 - Release + Rollback Rehearsal

## Goal
Execute an end-to-end release rehearsal with rollback proof and machine-readable evidence.

## What Was Implemented

### 1) Rehearsal Orchestration Script
- Added `scripts/release_rollback_rehearsal.ps1`.
- Script flow:
  1. Backup creation (`backup_restore_drill.ps1`)
  2. Release regression tests (`tests/test_permissions.py`)
  3. Release UAT smoke (`scripts/uat_checklist.py`)
  4. Rollback restore (`backup_restore_drill.ps1 -Mode restore`)
  5. Rollback hash verify (`backup_restore_drill.ps1 -Mode verify`)
  6. JSON report output to `project_notes/release/`

### 2) Rehearsal Runbook
- Added `project_notes/RELEASE_ROLLBACK_REHEARSAL_RUNBOOK.md`.
- Includes command, expected outputs, pass/fail criteria.

## Execution Notes
- First execution failed because strict-mode command capture treated missing `$LASTEXITCODE` as fatal.
- Fixed script with safe exit-code handling and stderr-tolerant capture.
- Re-ran successfully.

## Final Successful Rehearsal Evidence
- Command:
  - `powershell -ExecutionPolicy Bypass -File scripts/release_rollback_rehearsal.ps1 -IncludeQrAssets -UatAvgThresholdMs 8.0`
- Report:
  - `project_notes/release/release_rollback_rehearsal_2026-03-29T23-28-36Z.json`
- Status:
  - `REHEARSAL_STATUS ok`
- Key step results:
  - Backup creation: pass
  - Release regression tests: pass
  - Release UAT smoke: pass (10/10)
  - Rollback restore: pass
  - Rollback hash verify: pass (`VERIFY_OK`)

## Validation
- Regression tests re-run after script updates:
  - `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe -m unittest tests/test_permissions.py`
- Result:
  - `Ran 83 tests in 4.844s`
  - `OK`

## Outcome
- Release + rollback rehearsal is now reproducible and evidence-backed.
- Project is ready for Day 34 (controlled production rollout).
