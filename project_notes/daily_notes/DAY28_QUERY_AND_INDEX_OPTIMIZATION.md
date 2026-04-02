# Day 28 - Query and Index Optimization

## Goal
Reduce request latency on frequently used teacher/admin flows with low-risk database optimizations.

## What Was Implemented

### 1) Query Optimization for Teacher Dashboard
- Refactored teacher dashboard data loading to avoid N+1 queries.
- Batched active sessions fetch for all teacher classes.
- Batched confirmed sessions fetch for all teacher classes.
- Batched class-size aggregation with a single grouped query.
- Batched present-count aggregation for active sessions.
- Batched attendance record fetch for active sessions and grouped in memory.

### 2) Query Optimization for Teacher History
- Replaced per-session present-count query loop with one grouped aggregate query.

### 3) Index Strategy (Migration + Model Alignment)
Added indexes for columns frequently used in filter/order patterns:
- users: role, is_locked
- classes: name, teacher_id
- attendance_sessions: class_id, date, active, confirmed
- attendance_sessions composite: (class_id, active, date), (class_id, confirmed, date)
- attendance_records: student_id, session_id, present
- attendance_records composite: (session_id, present), (student_id, session_id, present)
- student_calendar_events: student_id, event_date
- permission_audit_logs: created_at, permission, role, endpoint
- admin_operation_logs: created_at, actor_user_id, target_user_id, action, status

## Files Updated
- app.py
- models.py
- migrations/versions/a9f3c1d2e4b7_add_query_performance_indexes.py

## Validation
- Test command:
  - c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe -m unittest tests/test_permissions.py
- Result:
  - Ran 82 tests in 4.760s
  - OK

## Notes
- Migration is written with index-existence checks to remain idempotent across environments.
- This pass intentionally focused on high-impact, low-risk changes without altering route behavior or response contracts.
