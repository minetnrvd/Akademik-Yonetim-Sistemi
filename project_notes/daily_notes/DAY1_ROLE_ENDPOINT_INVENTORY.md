# Day 1 - Endpoint and Role Inventory

Date: 2026-03-28

## Coverage Summary

- Total endpoints: 34
- role:student protected: 16
- role:teacher protected: 11
- role:admin protected: 0
- login_required_session only: 3
- no auth decorator: 4

## Endpoints by Guard Type

### Public / No role_required

| Line | Route | Function | Notes |
|---|---|---|---|
| 900 | /set-language (POST) | set_language | Public utility route |
| 913 | /register (GET, POST) | register | Public auth route |
| 968 | /login (GET, POST) | login | Public auth route |
| 1008 | /logout | logout | Should typically require login |

### login_required_session (authenticated but role-agnostic)

| Line | Route | Function | Risk |
|---|---|---|---|
| 1182 | /teacher/session/<int:session_id>/stats | session_stats | Teacher-prefixed endpoint without role lock |
| 1202 | /teacher/history | teacher_history_redirect | Teacher-prefixed endpoint without role lock |
| 2071 | /view_qr/<token> | view_qr | Shared QR page, currently role-agnostic |

### role:teacher

| Line | Route | Function |
|---|---|---|
| 1017 | /teacher_dashboard (GET, POST) | teacher_dashboard |
| 1054 | /teacher/history/<int:class_id> | teacher_class_history |
| 1101 | /teacher/history/<int:class_id>/export | export_teacher_class_history |
| 1209 | /teacher/session/<int:session_id> | session_detail |
| 1254 | /teacher/session/<int:session_id>/delete (POST) | delete_session |
| 1276 | /teacher/account (GET, POST) | teacher_account |
| 1998 | /teacher/create_class (GET, POST) | create_class |
| 2034 | /create_session (POST) | create_session |
| 2083 | /teacher/class/<int:class_id> | class_detail |
| 2163 | /teacher/session/<int:session_id>/update_attendance (POST) | update_attendance |
| 2198 | /teacher/session/<int:session_id>/stop | stop_session |

### role:student

| Line | Route | Function |
|---|---|---|
| 1336 | /student/account (GET, POST) | student_account |
| 1374 | /student_dashboard (GET, POST) | student_dashboard |
| 1526 | /student/absence (GET, POST) | student_absence |
| 1633 | /student/identity | student_identity_info |
| 1743 | /student/education | student_education_info |
| 1789 | /student/family | student_family_info |
| 1801 | /student/documents | student_documents_info |
| 1813 | /student/contact | student_contact_info |
| 1830 | /student/current-account | student_current_account |
| 1842 | /student/payment | student_payment_info |
| 1854 | /student/term-courses | student_term_courses |
| 1874 | /student/transcript | student_transcript |
| 1920 | /student/academic-calendar | student_academic_calendar |
| 1949 | /student/exams | student_exams |
| 1967 | /student/history/<int:class_id> | student_class_history |
| 2114 | /attendance/<token> | mark_attendance |

## Critical Observations (Day 1)

1. No admin endpoint exists yet (role:admin count is 0).
2. Three teacher-related endpoints use login_required_session instead of role_required('teacher').
3. logout is public route; behavior is usually safe but should be standardized to auth-required flow.
4. Prefix consistency is mixed: /teacher/... exists, but create_session is not under /teacher prefix.

## Recommended Next Step (Day 2)

- Define a permission map (action-based), starting with:
  - teacher.session.read
  - teacher.session.update_attendance
  - teacher.class.export
  - student.profile.read
  - student.attendance.mark
- Then bind each endpoint to permission checks and keep role_required as outer guard.
