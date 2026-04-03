# PostgreSQL Production Cutover Checklist

## Purpose
Execute SQLite to PostgreSQL cutover in a controlled production sequence with clear go or no-go gates and a machine-readable evidence artifact.

## Script
- Path: scripts/cutover_sqlite_to_postgres.py

## Preconditions (Must Pass)
1. Fresh backup exists and hash verification is successful.
2. Application maintenance window is approved.
3. PostgreSQL target is reachable and credentials are validated.
4. Environment variable DATABASE_URL points to production PostgreSQL.
5. Rollback owner and contact channel are assigned.

## Required Inputs
- SQLite source database:
  - instance/attendance.db
- PostgreSQL URL:
  - DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db>

## Step 1: Pre-cutover Safety Checks
Run in project root:

```powershell
& c:/Uygulama/qr_attandance_project/venv/Scripts/Activate.ps1
$env:DATABASE_URL = "postgresql://<user>:<password>@<host>:<port>/<db>"
python -c "import os; u=os.getenv('DATABASE_URL',''); print('DATABASE_URL_OK', u.startswith('postgresql://') or u.startswith('postgres://'))"
```

Expected:
- DATABASE_URL_OK True

## Step 2: Schema + Data Cutover (Standard)

```powershell
python scripts/cutover_sqlite_to_postgres.py --output-dir project_notes/closeout
```

Expected console output:
- SQLITE_TO_POSTGRES_REPORT <path>
- SQLITE_TO_POSTGRES_STATUS completed

## Step 3: Data-Only Re-run (If Schema Already Migrated)
Use only when Alembic schema is already applied and confirmed.

```powershell
python scripts/cutover_sqlite_to_postgres.py --skip-alembic --output-dir project_notes/closeout
```

## Step 4: Hard Verification Gate
Open the newest cutover report under project_notes/closeout and verify:
1. status is completed.
2. steps includes:
   - table_mapping passed true
   - truncate_target passed true
   - row_count_verification passed true
   - sequence_sync passed true
3. all table_results entries have passed true.

## Step 5: Application Health Validation

```powershell
python -m pytest tests/test_permissions.py
python -m pytest tests/test_ui_smoke.py
python -c "from app import app; c=app.test_client(); r=c.get('/health'); print('HEALTH', r.status_code, r.json.get('status'))"
```

Expected:
- Permission regression passes.
- UI smoke passes.
- HEALTH 200 healthy

## Rollback Trigger Conditions (Immediate)
Trigger rollback if any condition occurs:
1. SQLITE_TO_POSTGRES_STATUS is failed.
2. Any table row-count verification fails.
3. sequence_sync step is missing or failed.
4. Health endpoint is not 200 healthy after cutover.

## Rollback Action
1. Stop write traffic (maintenance mode).
2. Restore latest verified SQLite backup with backup restore drill procedure.
3. Repoint runtime DB configuration to known-good source.
4. Re-run health and smoke checks before reopening traffic.

## Output Evidence
- Primary artifact:
  - project_notes/closeout/sqlite_to_postgres_cutover_<UTC_TIMESTAMP>.json
- Suggested handoff note:
  - Append artifact path to project_notes/REPORTS_CONSOLIDATED_SUMMARY.md
- Execution log template:
  - project_notes/POSTGRES_CUTOVER_EXECUTION_LOG_TEMPLATE.md

## Sign-off
- Technical owner:
- Reviewer:
- Maintenance window start/end:
- Cutover report path:
- Final decision: GO / NO-GO
