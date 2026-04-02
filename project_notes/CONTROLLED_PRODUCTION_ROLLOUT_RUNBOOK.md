# Controlled Production Rollout Runbook

## Purpose
Run Day 34 gated rollout checks and generate a rollout decision artifact.

## Script
- Path: `scripts/controlled_rollout.py`

## Command

```powershell
c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe scripts/controlled_rollout.py --phase canary --include-qr-assets --uat-avg-threshold-ms 8.0
```

## Gates Enforced
1. Latest Day 33 release+rollback rehearsal report exists and status is `ok`.
2. Fresh backup is created before rollout decision.
3. Regression test suite passes.
4. UAT smoke pass rate is 100%.
5. `/health` returns a valid snapshot payload.

## Output
- JSON report: `project_notes/rollout/controlled_rollout_<UTC_TIMESTAMP>.json`
- Console lines:
  - `CONTROLLED_ROLLOUT_REPORT <path>`
  - `CONTROLLED_ROLLOUT_STATUS approved|blocked`

## Promotion Rule
- Promote rollout only when `CONTROLLED_ROLLOUT_STATUS approved`.
- If blocked, resolve failed gates and re-run before promotion.
