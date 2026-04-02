# Day 2 - Permission Matrix and Endpoint Mapping

Date: 2026-03-28

## Purpose

This document defines action-based permissions and maps each endpoint to a required permission.
It is designed to be layered on top of existing role checks.

## Permission Naming Standard

Format:

- `domain.resource.action`

Examples:

- `teacher.session.read`
- `teacher.session.update_attendance`
- `student.profile.read`
- `student.attendance.mark`

## Core Permission Catalog (MVP)

### Public/Auth

- `public.auth.login`
- `public.auth.register`
- `public.ui.set_language`
- `auth.session.logout`

### Teacher

- `teacher.dashboard.view`
- `teacher.class.create`
- `teacher.class.read`
- `teacher.class.history.read`
- `teacher.class.history.export`
- `teacher.session.create`
- `teacher.session.read`
- `teacher.session.stats.read`
- `teacher.session.stop`
- `teacher.session.delete`
- `teacher.session.update_attendance`
- `teacher.account.read`
- `teacher.account.update`
- `teacher.qr.view`

### Student

- `student.dashboard.view`
- `student.account.read`
- `student.account.update`
- `student.attendance.mark`
- `student.absence.read`
- `student.absence.update`
- `student.class.history.read`
- `student.identity.read`
- `student.education.read`
- `student.family.read`
- `student.documents.read`
- `student.contact.read`
- `student.current_account.read`
- `student.payment.read`
- `student.term_courses.read`
- `student.transcript.read`
- `student.academic_calendar.read`
- `student.exams.read`

### Admin (reserved for Day 3+)

- `admin.dashboard.view`
- `admin.user.read`
- `admin.user.update_role`
- `admin.class.assign`
- `admin.audit.read`

## Endpoint -> Permission Map

## Public/Auth Routes

| Line | Method | Route | Function | Guard now | Required permission |
|---|---|---|---|---|---|
| 900 | POST | /set-language | set_language | public | public.ui.set_language |
| 913 | GET,POST | /register | register | public | public.auth.register |
| 968 | GET,POST | /login | login | public | public.auth.login |
| 1008 | GET | /logout | logout | public | auth.session.logout |

## Teacher Routes

| Line | Method | Route | Function | Guard now | Required permission |
|---|---|---|---|---|---|
| 1017 | GET,POST | /teacher_dashboard | teacher_dashboard | role:teacher | teacher.dashboard.view |
| 1054 | GET | /teacher/history/<int:class_id> | teacher_class_history | role:teacher | teacher.class.history.read |
| 1101 | GET | /teacher/history/<int:class_id>/export | export_teacher_class_history | role:teacher | teacher.class.history.export |
| 1182 | GET | /teacher/session/<int:session_id>/stats | session_stats | auth:any | teacher.session.stats.read |
| 1202 | GET | /teacher/history | teacher_history_redirect | auth:any | teacher.class.history.read |
| 1209 | GET | /teacher/session/<int:session_id> | session_detail | role:teacher | teacher.session.read |
| 1254 | POST | /teacher/session/<int:session_id>/delete | delete_session | role:teacher | teacher.session.delete |
| 1276 | GET,POST | /teacher/account | teacher_account | role:teacher | teacher.account.read / teacher.account.update |
| 1998 | GET,POST | /teacher/create_class | create_class | role:teacher | teacher.class.create |
| 2034 | POST | /create_session | create_session | role:teacher | teacher.session.create |
| 2071 | GET | /view_qr/<token> | view_qr | auth:any | teacher.qr.view |
| 2083 | GET | /teacher/class/<int:class_id> | class_detail | role:teacher | teacher.class.read |
| 2163 | POST | /teacher/session/<int:session_id>/update_attendance | update_attendance | role:teacher | teacher.session.update_attendance |
| 2198 | GET | /teacher/session/<int:session_id>/stop | stop_session | role:teacher | teacher.session.stop |

## Student Routes

| Line | Method | Route | Function | Guard now | Required permission |
|---|---|---|---|---|---|
| 1336 | GET,POST | /student/account | student_account | role:student | student.account.read / student.account.update |
| 1374 | GET,POST | /student_dashboard | student_dashboard | role:student | student.dashboard.view |
| 1526 | GET,POST | /student/absence | student_absence | role:student | student.absence.read / student.absence.update |
| 1633 | GET | /student/identity | student_identity_info | role:student | student.identity.read |
| 1743 | GET | /student/education | student_education_info | role:student | student.education.read |
| 1789 | GET | /student/family | student_family_info | role:student | student.family.read |
| 1801 | GET | /student/documents | student_documents_info | role:student | student.documents.read |
| 1813 | GET | /student/contact | student_contact_info | role:student | student.contact.read |
| 1830 | GET | /student/current-account | student_current_account | role:student | student.current_account.read |
| 1842 | GET | /student/payment | student_payment_info | role:student | student.payment.read |
| 1854 | GET | /student/term-courses | student_term_courses | role:student | student.term_courses.read |
| 1874 | GET | /student/transcript | student_transcript | role:student | student.transcript.read |
| 1920 | GET | /student/academic-calendar | student_academic_calendar | role:student | student.academic_calendar.read |
| 1949 | GET | /student/exams | student_exams | role:student | student.exams.read |
| 1967 | GET | /student/history/<int:class_id> | student_class_history | role:student | student.class.history.read |
| 2114 | GET | /attendance/<token> | mark_attendance | role:student | student.attendance.mark |

## Priority Gaps to Fix First (Day 3)

1. Tighten non-role teacher routes:
   - `/teacher/session/<int:session_id>/stats`
   - `/teacher/history`
   - `/view_qr/<token>`
2. Standardize route prefix for teacher write actions:
   - move `/create_session` to `/teacher/create_session`
3. Add explicit permission check helper while keeping `role_required`.

## Suggested Implementation Order (Day 3)

1. Introduce `PERMISSION_MAP` dict keyed by function name.
2. Add `has_permission(user, permission)` helper.
3. Add `permission_required(permission_key)` decorator.
4. Apply to 5 critical teacher write/read endpoints first.
5. Add request-level audit log for denied permission attempts.
