# Day 4 - Student Permission Rollout (Controlled)

Date: 2026-03-28

## Scope Completed

Applied the permission layer to student endpoints while keeping existing role checks unchanged.

## What Changed

1. `PERMISSION_MAP` expanded with student endpoint permissions:
- student_account
- student_dashboard
- student_absence
- student_identity_info
- student_education_info
- student_family_info
- student_documents_info
- student_contact_info
- student_current_account
- student_payment_info
- student_term_courses
- student_transcript
- student_academic_calendar
- student_exams
- student_class_history
- mark_attendance

2. `ROLE_PERMISSIONS['student']` expanded with corresponding student permissions.

3. Added `@permission_required()` to all active student routes listed above.

## Safety Guarantees Preserved

- Existing `@role_required('student')` decorators remain in place.
- Existing ownership/data checks inside handlers are unchanged.
- Day 3 teacher permission coverage remains intact.

## Validation

- Static editor diagnostics: no errors in app.py
- Syntax compile check: `py -m py_compile app.py` passed

## Next Step (Day 5)

1. Normalize mixed read/write permissions for GET+POST handlers:
- `student_account`
- `student_absence`
- `student_dashboard`
- `teacher_account`

2. Introduce action-level checks in handlers:
- `student.account.read` vs `student.account.update`
- `student.absence.read` vs `student.absence.update`
- `teacher.account.read` vs `teacher.account.update`

3. Add a small denied-access monitoring helper/report for admin-only diagnostics.
