# Backup/Restore Drill Runbook

## Scope

This runbook defines the local backup and restore drill for the QR attendance project.

## Primary Assets

1. Database: `instance/attendance.db`
2. Migration history: `migrations/`
3. Optional QR assets: `static/qrcodes`, `static/qr_codes`

## Script

- Path: `scripts/backup_restore_drill.ps1`
- Modes:
  1. `backup`
  2. `restore`
  3. `verify`

## Drill Steps

1. Create backup

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup_restore_drill.ps1 -Mode backup -IncludeQrAssets
```

Expected output:
- `BACKUP_OK <backup_dir>`

2. Restore to drill directory

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup_restore_drill.ps1 -Mode restore -BackupDir <backup_dir>
```

Expected output:
- `RESTORE_OK <restore_dir>`

3. Verify backup/restore hash

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup_restore_drill.ps1 -Mode verify -BackupDir <backup_dir> -RestoreDir <restore_dir>
```

Expected output:
- `VERIFY_OK backup_sha256=<sha256>`

## Pass Criteria

1. Backup command completes without errors.
2. Restore command completes without errors.
3. Verify command returns `VERIFY_OK`.
4. `manifest.txt` exists in backup directory.

## Fail Criteria

1. Missing DB file in backup or restore output.
2. Verify hash mismatch.
3. Command exits with non-zero status.

## Operator Notes

1. Drill restore output is intentionally written to a separate directory.
2. Script does not overwrite live database by default.
3. Keep only approved backup directories for retention policy.
