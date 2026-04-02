# Release + Rollback Rehearsal Runbook

## Purpose
Execute a Day 33 release rehearsal with rollback proof in a single flow.

## Script
- Path: `scripts/release_rollback_rehearsal.ps1`

## Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts/release_rollback_rehearsal.ps1 -IncludeQrAssets -UatAvgThresholdMs 8.0
```

## What It Does
1. Creates backup using `scripts/backup_restore_drill.ps1`.
2. Runs release regression tests (`tests/test_permissions.py`).
3. Runs release UAT smoke (`scripts/uat_checklist.py`).
4. Executes rollback restore to drill directory.
5. Verifies restore hash equality.
6. Writes JSON report to `project_notes/release/`.

## Expected Outputs
- `REHEARSAL_REPORT <path>`
- `REHEARSAL_STATUS ok`

## Pass Criteria
1. All rehearsal steps are marked `passed=true` in JSON report.
2. Final `REHEARSAL_STATUS` is `ok`.
3. Rollback verify step returns `VERIFY_OK` detail.

## Fail Criteria
1. Any step marked `passed=false`.
2. Final status `failed`.
3. Missing report output.
