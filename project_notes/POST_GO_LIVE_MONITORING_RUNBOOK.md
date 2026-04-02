# Post-Go-Live Monitoring Runbook

## Purpose
Run Day 35 closeout checks and produce a final monitoring/closure artifact.

## Script
- Path: `scripts/post_go_live_closeout.py`

## Command

```powershell
c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe scripts/post_go_live_closeout.py
```

## Checks Included
1. Day 33 rehearsal report status is `ok`.
2. Day 34 controlled rollout report status is `approved`.
3. Latest UAT smoke report has 100% pass.
4. `/health` returns a valid status payload.
5. Performance baseline and load profile reports are present.

## Output
- Report path: `project_notes/closeout/post_go_live_closeout_<UTC_TIMESTAMP>.json`
- Console lines:
  - `POST_GO_LIVE_CLOSEOUT_REPORT <path>`
  - `POST_GO_LIVE_CLOSEOUT_STATUS closed|attention_required`

## Closure Rule
- Mark Day 35 complete only when status is `closed`.
