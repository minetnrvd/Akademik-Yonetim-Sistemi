# Day 25 - Backup and Restore Drill

Date: 2026-03-29
Status: Completed
Related plan: project_notes/daily_notes/MASTER_35_DAY_EXECUTION_PLAN.md

## 1) Goal

Execute a practical backup/restore drill with explicit pass/fail criteria and an operator runbook.

## 2) Implemented

New operational script:
- `scripts/backup_restore_drill.ps1`

Supported modes:
1. `backup`
2. `restore`
3. `verify`

Coverage in script:
1. Backs up primary DB: `instance/attendance.db`
2. Backs up migration directory: `migrations/`
3. Optionally includes QR assets: `static/qrcodes`, `static/qr_codes`
4. Writes `manifest.txt` with DB SHA256
5. Restores into separate drill directory
6. Verifies backup and restore hash equality

New runbook:
- `project_notes/BACKUP_RESTORE_DRILL_RUNBOOK.md`

Runbook includes:
1. exact execution commands
2. expected output markers
3. pass/fail criteria
4. operator safety notes

## 3) Drill Execution (This Session)

Executed commands:
1. `powershell -ExecutionPolicy Bypass -File scripts/backup_restore_drill.ps1 -Mode backup -IncludeQrAssets`
2. `powershell -ExecutionPolicy Bypass -File scripts/backup_restore_drill.ps1 -Mode restore -BackupDir C:\Uygulama\qr_attandance_project\backups\drill_20260329_225210`
3. `powershell -ExecutionPolicy Bypass -File scripts/backup_restore_drill.ps1 -Mode verify -BackupDir C:\Uygulama\qr_attandance_project\backups\drill_20260329_225210 -RestoreDir C:\Uygulama\qr_attandance_project\restore_drill\drill_20260329_225210`

Observed outputs:
1. `BACKUP_OK C:\Uygulama\qr_attandance_project\backups\drill_20260329_225210`
2. `RESTORE_OK C:\Uygulama\qr_attandance_project\restore_drill\drill_20260329_225210`
3. `VERIFY_OK backup_sha256=41188F33BC37E404509520871F456929A1E3890274D77B7FB7357FBA4DC75A5A`

## 4) Validation

Result: Drill passed.

Pass checklist:
1. backup completed
2. restore completed
3. hash verify completed
4. drill artifacts generated under `backups/` and `restore_drill/`

## 5) Day 25 Exit Gate

Day 25 is complete because:
1. backup/restore process is scripted and repeatable,
2. runbook provides deterministic operator flow,
3. practical drill was executed successfully in the current workspace,
4. integrity verification is automated via SHA256 check.

## 6) Next Day Input (Day 26)

1. start error/latency instrumentation baseline,
2. define minimal metrics map for core routes,
3. add lightweight request timing logging and aggregation path.
