# Day 03 - Alembic Baseline and Rollback Rehearsal

Date: 2026-03-29
Status: Completed
Related plan: project_notes/daily_notes/MASTER_35_DAY_EXECUTION_PLAN.md

## 1) What Was Implemented

1. Installed Alembic into project virtual environment.
2. Initialized migration scaffolding:
   - `alembic.ini`
   - `migrations/`
   - `migrations/env.py`
3. Connected Alembic metadata to SQLAlchemy models (`db.metadata`).
4. Added runtime DB URL resolver in Alembic env:
   - Uses `ALEMBIC_DB_URL` if provided.
   - Defaults to local SQLite DB at `instance/attendance.db`.
5. Generated baseline migration from models:
   - `migrations/versions/11518b6da746_baseline_schema.py`

## 2) Rehearsal Performed

A temporary DB was used for safe rehearsal:
- Target: `sqlite:///instance/alembic_baseline_tmp.db`

Executed successfully:
1. `alembic revision --autogenerate -m "baseline_schema"`
2. `alembic upgrade head`
3. `alembic downgrade base`

Result:
- Upgrade and downgrade both succeeded.
- Rollback path is validated at migration framework level.

## 3) Files Updated

1. `alembic.ini` (default URL set to sqlite local path)
2. `migrations/env.py` (metadata + URL resolver)
3. `migrations/versions/11518b6da746_baseline_schema.py` (baseline revision)

## 4) Notes and Constraints

1. Baseline revision currently creates all tables/constraints from model metadata.
2. Performance indexes planned in Day 02 are not fully represented yet; they should be added in follow-up migration(s).
3. For PostgreSQL dry-run, set:
   - `ALEMBIC_DB_URL=postgresql+psycopg://...`

## 5) Day 03 Exit Gate

Day 03 is complete because:
1. Alembic is initialized and wired to model metadata.
2. Baseline revision exists in version control path.
3. Upgrade/downgrade rehearsal passed.
4. Transition to PostgreSQL is now migration-tool ready.

## 6) Next Day Input (Day 04)

1. Add persistent audit log table/model migration.
2. Route denied-permission events to DB persistence layer.
3. Keep in-memory buffer only as short-term fallback.
