# Day 02 - PostgreSQL Migration Checklist and Index Inventory

Date: 2026-03-29
Status: Completed
Related plan: MASTER_35_DAY_EXECUTION_PLAN.md

## 1) Objective

Define a rollback-safe path from current SQLite schema (`instance/attendance.db`) to PostgreSQL with:
1. table/constraint inventory,
2. index gap analysis,
3. migration execution checklist,
4. rollback and validation gates.

## 2) Current Schema Inventory (Observed)

### Tables
1. users
2. students
3. classes
4. student_classes
5. attendance_sessions
6. attendance_records
7. academic_terms
8. courses
9. course_enrollments
10. grade_records
11. announcements
12. messages
13. student_calendar_events

### Existing Uniques / Auto-indexes
1. users.email (unique)
2. classes.qr_token (unique behavior in DB state)
3. attendance_sessions.qr_token (unique)
4. academic_terms.name (unique)
5. courses.code (unique)
6. course_enrollments(student_id, course_id) (unique)

## 3) Index Candidate List (High Priority)

These are not all guaranteed present today and should be explicit in PostgreSQL migrations:

1. users(role)
2. classes(teacher_id)
3. student_classes(student_id)
4. student_classes(class_id)
5. attendance_sessions(class_id, date DESC)
6. attendance_sessions(class_id, active)
7. attendance_records(session_id, present)
8. attendance_records(student_id, session_id)
9. announcements(target_role, created_at DESC)
10. announcements(course_id, created_at DESC)
11. messages(recipient_id, is_read, sent_at DESC)
12. messages(sender_id, sent_at DESC)
13. student_calendar_events(student_id, event_date)
14. courses(teacher_id, term_id)
15. course_enrollments(student_id)
16. course_enrollments(course_id)
17. grade_records(enrollment_id, created_at DESC)

## 4) SQLite -> PostgreSQL Type Notes

1. BOOLEAN: enforce explicit true/false defaults in migrations.
2. DATETIME/DATE: map to PostgreSQL `timestamp` / `date` explicitly.
3. TEXT columns currently added by ALTER in SQLite should be normalized to expected VARCHAR/TEXT types.
4. Ensure timezone strategy (`timestamp without time zone` vs `with time zone`) is chosen once and used consistently.

## 5) Migration Tooling Decision

Recommended baseline:
1. Use Alembic with SQLAlchemy metadata as source of truth.
2. Create versioned migrations instead of runtime `_ensure_column(...)` growth.
3. Keep `_ensure_column(...)` temporary only during transition window.

## 6) Execution Checklist (Day 03 input)

### Phase A - Preparation
1. Add PostgreSQL connection config via environment variables.
2. Initialize Alembic and pin first baseline migration from current models.
3. Add explicit indexes listed in Section 3 to migration scripts.

### Phase B - Dry Run
1. Create fresh PostgreSQL schema in dev.
2. Apply migrations to empty DB.
3. Run app startup + smoke test.
4. Export SQLite data snapshot.
5. Write one-time data copy script (SQLite -> PostgreSQL).

### Phase C - Verification
1. Row-count comparison per table.
2. Critical query checks (dashboard, attendance, history, transcript).
3. Permission and auth sanity checks.
4. Unit tests and compile checks green.

### Phase D - Cutover
1. Freeze writes briefly.
2. Final incremental data copy.
3. Switch DB URL to PostgreSQL.
4. Run post-cutover smoke test.

## 7) Rollback Strategy (Mandatory)

### Rollback triggers
1. Migration apply failure.
2. Data mismatch in verification step.
3. Critical endpoint failure after cutover.

### Rollback actions
1. Keep SQLite snapshot untouched before cutover.
2. Revert app DB URL to SQLite.
3. Restart app with known-good config.
4. Log failed migration version and root cause.
5. Re-run cutover only after fix + dry run pass.

## 8) Day 02 Exit Gate

Day 02 is complete because:
1. Current DB tables and unique constraints are inventoried.
2. High-value index plan is documented.
3. End-to-end migration checklist exists.
4. Rollback process is explicit and testable.

## 9) Next Day Input (Day 03)

1. Initialize Alembic in repo.
2. Create first migration baseline.
3. Apply migration to clean PostgreSQL dev DB.
4. Produce rollback rehearsal notes.
