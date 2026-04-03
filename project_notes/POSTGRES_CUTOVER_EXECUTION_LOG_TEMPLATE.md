# PostgreSQL Cutover Execution Log Template

## Document Purpose
Capture the live execution timeline of SQLite to PostgreSQL cutover, including operator actions, verification outputs, risk decisions, and final go or no-go status.

## Session Metadata
- Date (UTC):
- Change ticket ID:
- Environment: production / staging
- Technical owner:
- Secondary reviewer:
- Incident bridge channel:
- Maintenance window (start/end):

## Pre-Cutover Gate Check
- [ ] Latest backup created
- [ ] Backup hash verified
- [ ] DATABASE_URL validated for PostgreSQL target
- [ ] App write traffic freeze confirmed
- [ ] Rollback owner on-call confirmed

Evidence paths:
- Backup artifact:
- Restore/hash verification artifact:

## Live Timeline (UTC)
Use one line per action.

| Time | Action | Command/Step | Result | Operator |
|------|--------|--------------|--------|----------|
|      |        |              |        |          |
|      |        |              |        |          |
|      |        |              |        |          |

## Cutover Command Record
Standard run:

```powershell
python scripts/cutover_sqlite_to_postgres.py --output-dir project_notes/closeout
```

Or data-only run:

```powershell
python scripts/cutover_sqlite_to_postgres.py --skip-alembic --output-dir project_notes/closeout
```

Execution result:
- SQLITE_TO_POSTGRES_REPORT:
- SQLITE_TO_POSTGRES_STATUS: completed / failed

## Verification Checklist
- [ ] Report status is completed
- [ ] table_mapping passed=true
- [ ] truncate_target passed=true
- [ ] row_count_verification passed=true
- [ ] sequence_sync passed=true
- [ ] All table_results entries passed=true
- [ ] /health result is 200 healthy
- [ ] Permission regression test passed
- [ ] UI smoke tests passed

Verification evidence paths:
- Cutover JSON report:
- Health check output:
- Permission test output:
- UI smoke output:

## Risk / Incident Notes
- Any anomaly detected:
- User impact observed:
- Mitigation action:
- Decision owner:

## Rollback Decision Block
Rollback required: YES / NO

If YES:
- Trigger time (UTC):
- Trigger reason:
- Backup restored from:
- Post-rollback health status:

If NO:
- Final go-live confirmation time (UTC):

## Final Sign-off
- Technical owner sign-off:
- Reviewer sign-off:
- Final decision: GO / NO-GO
- Follow-up actions (if any):

## Archive and Traceability
1. Save completed log under project_notes/closeout/ with timestamp suffix.
2. Link the final log and cutover JSON in project_notes/REPORTS_CONSOLIDATED_SUMMARY.md.
3. Include related release/rollout/UAT artifact paths for full audit chain.
