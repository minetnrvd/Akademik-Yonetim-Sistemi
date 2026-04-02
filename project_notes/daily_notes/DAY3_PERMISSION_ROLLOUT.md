# Day 3 - Permission Rollout (Controlled Phase)

Date: 2026-03-28

## Scope Completed

Implemented a controlled permission layer rollout focused on teacher endpoints while preserving existing role checks.

## What Was Added

1. Permission map expansion:
- Added permission keys for all current teacher handlers.

2. Role permission set expansion:
- Teacher role now has explicit permissions for dashboard, class history/export, session read/delete/stop, account manage, class create/read, session create/update, QR view.

3. Denied-access audit log improvement:
- Permission-denied logs now include:
  - user_id
  - role
  - endpoint
  - permission
  - HTTP method
  - path
  - IP address

## Endpoints Now Covered by permission_required

- /teacher_dashboard
- /teacher/history/<int:class_id>
- /teacher/history/<int:class_id>/export
- /teacher/session/<int:session_id>/stats
- /teacher/history
- /teacher/session/<int:session_id>
- /teacher/session/<int:session_id>/delete
- /teacher/account
- /teacher/create_class
- /create_session
- /view_qr/<token>
- /teacher/class/<int:class_id>
- /teacher/session/<int:session_id>/update_attendance
- /teacher/session/<int:session_id>/stop

## Controlled-Risk Notes

- Existing role guards (`role_required('teacher')`) were kept in place.
- Permission checks were layered in addition to role checks, not replacing them.
- Ownership checks (teacher owns class/session) remain active in handlers.

## Next Safe Step (Day 4)

- Introduce the same permission pattern to selected student write/read routes.
- Start separating read/update permissions for mixed GET+POST handlers (e.g., account pages).
- Add a lightweight denied-access report endpoint for admin-only visibility.
