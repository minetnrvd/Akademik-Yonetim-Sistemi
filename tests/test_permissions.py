import unittest
import os
import datetime
from uuid import uuid4
from types import SimpleNamespace
from models import Announcement, UserCalendarEvent, _utc_now_naive

from app import (
    app,
    db,
    User,
    Student,
    Class,
    Course,
    CourseEnrollment,
    PERMISSIONS,
    PERMISSION_MAP,
    ROLE_PERMISSIONS,
    has_permission,
    ensure_teacher_class_ownership,
    ensure_teacher_session_ownership,
    ensure_student_class_membership,
    ensure_student_event_ownership,
    ensure_permission,
    permission_required,
    validate_admin_lock_update,
    validate_admin_role_update,
    validate_admin_teacher_assignment,
    validate_password_policy,
    _safe_int_env,
    _normalize_samesite,
    _parse_filter_datetime,
    _parse_optional_int,
    RATE_LIMIT_EVENTS,
    _is_rate_limited,
    REQUEST_METRICS,
)


class PermissionModelTests(unittest.TestCase):
    def test_permission_map_uses_known_constants(self):
        known_values = set(PERMISSIONS.values())
        for endpoint, permission in PERMISSION_MAP.items():
            with self.subTest(endpoint=endpoint):
                self.assertIn(permission, known_values)

    def test_teacher_expected_permission(self):
        self.assertTrue(has_permission('teacher', PERMISSIONS['TEACHER_SESSION_CREATE']))
        self.assertFalse(has_permission('teacher', PERMISSIONS['STUDENT_ACCOUNT_UPDATE']))

    def test_student_expected_permission(self):
        self.assertTrue(has_permission('student', PERMISSIONS['STUDENT_ATTENDANCE_MARK']))
        self.assertFalse(has_permission('student', PERMISSIONS['TEACHER_CLASS_CREATE']))

    def test_empty_permission_key_is_allowed(self):
        self.assertTrue(has_permission('teacher', None))

    def test_unknown_role_denied_for_known_permission(self):
        self.assertFalse(has_permission('guest', PERMISSIONS['TEACHER_DASHBOARD_VIEW']))

    def test_admin_permissions_are_explicit(self):
        self.assertIn(PERMISSIONS['ADMIN_DASHBOARD_VIEW'], ROLE_PERMISSIONS['admin'])
        self.assertIn(PERMISSIONS['ADMIN_USER_READ'], ROLE_PERMISSIONS['admin'])
        self.assertIn(PERMISSIONS['ADMIN_USER_UPDATE_ROLE'], ROLE_PERMISSIONS['admin'])
        self.assertIn(PERMISSIONS['ADMIN_USER_LOCK_TOGGLE'], ROLE_PERMISSIONS['admin'])
        self.assertIn(PERMISSIONS['ADMIN_CLASS_ASSIGN_TEACHER'], ROLE_PERMISSIONS['admin'])
        self.assertIn(PERMISSIONS['ADMIN_AUDIT_READ'], ROLE_PERMISSIONS['admin'])
        self.assertIn(PERMISSIONS['ADMIN_METRICS_READ'], ROLE_PERMISSIONS['admin'])

    def test_admin_inventory_route_has_admin_permission(self):
        self.assertEqual(PERMISSION_MAP['admin_user_inventory'], PERMISSIONS['ADMIN_USER_READ'])

    def test_admin_role_update_route_has_permission(self):
        self.assertEqual(PERMISSION_MAP['admin_update_user_role'], PERMISSIONS['ADMIN_USER_UPDATE_ROLE'])

    def test_admin_lock_toggle_route_has_permission(self):
        self.assertEqual(PERMISSION_MAP['admin_toggle_user_lock'], PERMISSIONS['ADMIN_USER_LOCK_TOGGLE'])

    def test_admin_class_assignment_routes_have_permission(self):
        self.assertEqual(PERMISSION_MAP['admin_class_assignments'], PERMISSIONS['ADMIN_CLASS_ASSIGN_TEACHER'])
        self.assertEqual(PERMISSION_MAP['admin_assign_class_teacher'], PERMISSIONS['ADMIN_CLASS_ASSIGN_TEACHER'])

    def test_admin_operation_audit_route_has_permission(self):
        self.assertEqual(PERMISSION_MAP['admin_operation_audit_report'], PERMISSIONS['ADMIN_AUDIT_READ'])

    def test_admin_health_status_route_has_permission(self):
        self.assertEqual(PERMISSION_MAP['admin_health_status_report'], PERMISSIONS['ADMIN_METRICS_READ'])

    def test_admin_permission_matrix_route_has_permission(self):
        self.assertEqual(PERMISSION_MAP['admin_permission_matrix'], PERMISSIONS['ADMIN_PERMISSION_MATRIX_READ'])

    def test_admin_notifications_route_has_permission(self):
        self.assertEqual(PERMISSION_MAP['admin_notifications'], PERMISSIONS['ADMIN_NOTIFICATION_SEND'])

    def test_admin_password_reset_route_has_permission(self):
        self.assertEqual(PERMISSION_MAP['admin_reset_user_password'], PERMISSIONS['ADMIN_USER_PASSWORD_RESET'])

    def test_admin_permission_set_includes_new_permissions(self):
        self.assertIn(PERMISSIONS['ADMIN_PERMISSION_MATRIX_READ'], ROLE_PERMISSIONS['admin'])
        self.assertIn(PERMISSIONS['ADMIN_NOTIFICATION_SEND'], ROLE_PERMISSIONS['admin'])
        self.assertIn(PERMISSIONS['ADMIN_USER_PASSWORD_RESET'], ROLE_PERMISSIONS['admin'])
        self.assertIn(PERMISSIONS['ADMIN_DASHBOARD_CALENDAR_UPDATE'], ROLE_PERMISSIONS['admin'])
        self.assertIn(PERMISSIONS['TEACHER_DASHBOARD_CALENDAR_UPDATE'], ROLE_PERMISSIONS['teacher'])


class SessionConfigHardeningTests(unittest.TestCase):
    def test_safe_int_env_uses_default_for_invalid(self):
        name = 'TEST_INVALID_INT_ENV'
        old_value = os.environ.get(name)
        os.environ[name] = 'bad-value'
        try:
            self.assertEqual(_safe_int_env(name, 7, minimum=1, maximum=10), 7)
        finally:
            if old_value is None:
                del os.environ[name]
            else:
                os.environ[name] = old_value

    def test_safe_int_env_applies_bounds(self):
        name = 'TEST_BOUNDED_INT_ENV'
        old_value = os.environ.get(name)
        os.environ[name] = '999'
        try:
            self.assertEqual(_safe_int_env(name, 7, minimum=1, maximum=30), 30)
        finally:
            if old_value is None:
                del os.environ[name]
            else:
                os.environ[name] = old_value

    def test_normalize_samesite_defaults_to_lax(self):
        self.assertEqual(_normalize_samesite(None), 'Lax')
        self.assertEqual(_normalize_samesite('invalid'), 'Lax')

    def test_normalize_samesite_accepts_strict_and_none(self):
        self.assertEqual(_normalize_samesite('strict'), 'Strict')
        self.assertEqual(_normalize_samesite('none'), 'None')

    def test_session_cookie_defaults_are_hardened(self):
        self.assertTrue(app.config['SESSION_COOKIE_HTTPONLY'])
        self.assertEqual(app.config['SESSION_COOKIE_NAME'], 'qr_attendance_session')
        self.assertIn(app.config['SESSION_COOKIE_SAMESITE'], {'Lax', 'Strict', 'None'})


class UtcTimestampHelperTests(unittest.TestCase):
    def test_utc_helper_returns_naive_datetime(self):
        value = _utc_now_naive()
        self.assertIsInstance(value, datetime.datetime)
        self.assertIsNone(value.tzinfo)


class RateLimitHelperTests(unittest.TestCase):
    def setUp(self):
        RATE_LIMIT_EVENTS.clear()

    def tearDown(self):
        RATE_LIMIT_EVENTS.clear()

    def test_rate_limit_blocks_after_threshold(self):
        self.assertFalse(_is_rate_limited('test_scope', 'key1', limit=2, window_seconds=60, now_ts=100.0))
        self.assertFalse(_is_rate_limited('test_scope', 'key1', limit=2, window_seconds=60, now_ts=110.0))
        self.assertTrue(_is_rate_limited('test_scope', 'key1', limit=2, window_seconds=60, now_ts=115.0))

    def test_rate_limit_resets_after_window(self):
        self.assertFalse(_is_rate_limited('test_scope', 'key2', limit=1, window_seconds=30, now_ts=200.0))
        self.assertTrue(_is_rate_limited('test_scope', 'key2', limit=1, window_seconds=30, now_ts=205.0))
        self.assertFalse(_is_rate_limited('test_scope', 'key2', limit=1, window_seconds=30, now_ts=231.0))


class RequestMetricsCollectionTests(unittest.TestCase):
    def setUp(self):
        REQUEST_METRICS['total_requests'] = 0
        REQUEST_METRICS['error_4xx'] = 0
        REQUEST_METRICS['error_5xx'] = 0
        REQUEST_METRICS['by_endpoint'].clear()

    def test_after_request_collects_endpoint_metrics(self):
        client = app.test_client()
        response = client.get('/login', follow_redirects=False)
        self.assertEqual(response.status_code, 200)

        self.assertGreaterEqual(REQUEST_METRICS['total_requests'], 1)
        self.assertIn('GET login', REQUEST_METRICS['by_endpoint'])
        bucket = REQUEST_METRICS['by_endpoint']['GET login']
        self.assertGreaterEqual(bucket['count'], 1)
        self.assertGreaterEqual(bucket['max_ms'], bucket['min_ms'])


class HealthEndpointTests(unittest.TestCase):
    def test_health_endpoint_returns_snapshot(self):
        client = app.test_client()
        response = client.get('/health', follow_redirects=False)
        self.assertIn(response.status_code, (200, 503))
        payload = response.get_json()
        self.assertIsInstance(payload, dict)
        self.assertIn('status', payload)
        self.assertIn('totals', payload)
        self.assertIn('latency_ms', payload)


class LoginRateLimitRouteTests(unittest.TestCase):
    def setUp(self):
        RATE_LIMIT_EVENTS.clear()

    def tearDown(self):
        RATE_LIMIT_EVENTS.clear()

    def test_login_post_is_rate_limited(self):
        old_limit = app.config['LOGIN_RATE_LIMIT_MAX_ATTEMPTS']
        old_window = app.config['LOGIN_RATE_LIMIT_WINDOW_SECONDS']
        app.config['LOGIN_RATE_LIMIT_MAX_ATTEMPTS'] = 1
        app.config['LOGIN_RATE_LIMIT_WINDOW_SECONDS'] = 300

        try:
            client = app.test_client()
            first = client.post('/login', data={'email': 'nobody@example.com', 'password': 'x'}, follow_redirects=False)
            second = client.post('/login', data={'email': 'nobody@example.com', 'password': 'x'}, follow_redirects=False)
            self.assertEqual(first.status_code, 302)
            self.assertIn('/login', first.location)
            self.assertEqual(second.status_code, 302)
            self.assertIn('/login', second.location)
        finally:
            app.config['LOGIN_RATE_LIMIT_MAX_ATTEMPTS'] = old_limit
            app.config['LOGIN_RATE_LIMIT_WINDOW_SECONDS'] = old_window


class LoginSecurityHardeningRouteTests(unittest.TestCase):
    def setUp(self):
        RATE_LIMIT_EVENTS.clear()

    def tearDown(self):
        RATE_LIMIT_EVENTS.clear()

    def test_login_repeated_failures_lock_account(self):
        token = uuid4().hex[:8]
        email = f'lock.user.{token}@example.com'

        with app.app_context():
            next_user_id = (db.session.query(db.func.max(User.id)).scalar() or 0) + 200
            user = User(id=next_user_id, name=f'Lock User {token}', email=email, role='student')
            user.set_password('CorrectPass123!')
            db.session.add(user)
            db.session.add(Student(id=user.id, student_number=f'LOCK-{token}'))
            db.session.commit()

        old_rate_limit = app.config['LOGIN_RATE_LIMIT_MAX_ATTEMPTS']
        old_rate_window = app.config['LOGIN_RATE_LIMIT_WINDOW_SECONDS']
        old_lock_limit = app.config['LOGIN_LOCK_MAX_FAILURES']
        old_lock_window = app.config['LOGIN_LOCK_WINDOW_SECONDS']

        app.config['LOGIN_RATE_LIMIT_MAX_ATTEMPTS'] = 100
        app.config['LOGIN_RATE_LIMIT_WINDOW_SECONDS'] = 300
        app.config['LOGIN_LOCK_MAX_FAILURES'] = 3
        app.config['LOGIN_LOCK_WINDOW_SECONDS'] = 900

        try:
            client = app.test_client()
            for _ in range(3):
                response = client.post('/login', data={'email': email, 'password': 'WrongPass123!'}, follow_redirects=False)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/login', response.location)

            with app.app_context():
                locked_user = User.query.filter_by(email=email).first()
                self.assertIsNotNone(locked_user)
                self.assertTrue(locked_user.is_locked)

            blocked_response = client.post('/login', data={'email': email, 'password': 'CorrectPass123!'}, follow_redirects=False)
            self.assertEqual(blocked_response.status_code, 302)
            self.assertIn('/login', blocked_response.location)
        finally:
            app.config['LOGIN_RATE_LIMIT_MAX_ATTEMPTS'] = old_rate_limit
            app.config['LOGIN_RATE_LIMIT_WINDOW_SECONDS'] = old_rate_window
            app.config['LOGIN_LOCK_MAX_FAILURES'] = old_lock_limit
            app.config['LOGIN_LOCK_WINDOW_SECONDS'] = old_lock_window

    def test_security_headers_present_on_login(self):
        client = app.test_client()
        response = client.get('/login', follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.headers.get('X-Frame-Options'), 'DENY')
        self.assertEqual(response.headers.get('Referrer-Policy'), 'strict-origin-when-cross-origin')
        self.assertIn('default-src', response.headers.get('Content-Security-Policy', ''))


class PasswordPolicyTests(unittest.TestCase):
    def test_password_policy_rejects_short_password(self):
        old_min = app.config['PASSWORD_MIN_LENGTH']
        app.config['PASSWORD_MIN_LENGTH'] = 10
        try:
            error = validate_password_policy('Ab1!x', user_name='John Doe', user_email='john@example.com')
            self.assertIn('at least', error)
        finally:
            app.config['PASSWORD_MIN_LENGTH'] = old_min

    def test_password_policy_rejects_missing_complexity(self):
        error = validate_password_policy('abcdefghijk', user_name='John Doe', user_email='john@example.com')
        self.assertIn('uppercase, lowercase, digit, and special character', error)

    def test_password_policy_rejects_name_and_email_local_part(self):
        self.assertEqual(
            validate_password_policy('JohnDoe12!A', user_name='John Doe', user_email='john@example.com'),
            'Password cannot contain your name.',
        )
        self.assertEqual(
            validate_password_policy('john123!Abc', user_name='Other Name', user_email='john@example.com'),
            'Password cannot contain your email username.',
        )

    def test_password_policy_accepts_strong_password(self):
        self.assertIsNone(validate_password_policy('Strong!Pass123', user_name='John Doe', user_email='john@example.com'))


class ParsingHelperTests(unittest.TestCase):
    def test_parse_filter_datetime_accepts_supported_formats(self):
        self.assertIsNotNone(_parse_filter_datetime('2026-04-01'))
        self.assertIsNotNone(_parse_filter_datetime('2026-04-01T12:30'))
        self.assertIsNotNone(_parse_filter_datetime('2026-04-01 12:30:45'))

    def test_parse_filter_datetime_rejects_invalid(self):
        self.assertIsNone(_parse_filter_datetime('01/04/2026'))
        self.assertIsNone(_parse_filter_datetime(''))

    def test_parse_optional_int(self):
        self.assertEqual(_parse_optional_int('42'), 42)
        self.assertEqual(_parse_optional_int(' 7 '), 7)
        self.assertIsNone(_parse_optional_int('x7'))
        self.assertIsNone(_parse_optional_int(''))


class RegisterPasswordPolicyRouteTests(unittest.TestCase):
    def test_register_rejects_weak_password(self):
        token = uuid4().hex[:8]
        email = f'weak.pass.{token}@example.com'

        client = app.test_client()
        response = client.post(
            '/register',
            data={
                'name': 'Weak User',
                'email': email,
                'password': 'weak',
                'role': 'teacher',
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/register', response.location)

        with app.app_context():
            self.assertIsNone(User.query.filter_by(email=email).first())

    def test_register_rejects_admin_role_submission(self):
        token = uuid4().hex[:8]
        email = f'admin.register.{token}@example.com'

        client = app.test_client()
        response = client.post(
            '/register',
            data={
                'name': 'Admin Candidate',
                'email': email,
                'password': 'Strong!Pass123',
                'role': 'admin',
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/register', response.location)

        with app.app_context():
            created = User.query.filter_by(email=email).first()
            self.assertIsNone(created)


class AdminRoleUpdateValidationTests(unittest.TestCase):
    def test_non_admin_cannot_update_role(self):
        error = validate_admin_role_update(
            actor_user_id=10,
            actor_role='teacher',
            target_user_id=20,
            target_user_role='student',
            new_role='teacher',
            admin_count=2,
        )
        self.assertEqual(error, 'Only admin can update roles.')

    def test_invalid_target_role_denied(self):
        error = validate_admin_role_update(
            actor_user_id=1,
            actor_role='admin',
            target_user_id=20,
            target_user_role='student',
            new_role='superadmin',
            admin_count=2,
        )
        self.assertEqual(error, 'Invalid target role.')

    def test_self_role_change_denied(self):
        error = validate_admin_role_update(
            actor_user_id=1,
            actor_role='admin',
            target_user_id=1,
            target_user_role='admin',
            new_role='teacher',
            admin_count=2,
        )
        self.assertEqual(error, 'You cannot change your own role.')

    def test_last_admin_downgrade_denied(self):
        error = validate_admin_role_update(
            actor_user_id=2,
            actor_role='admin',
            target_user_id=1,
            target_user_role='admin',
            new_role='teacher',
            admin_count=1,
        )
        self.assertEqual(error, 'At least one admin account must remain in the system.')


class AdminLockUpdateValidationTests(unittest.TestCase):
    def test_non_admin_cannot_update_lock(self):
        error = validate_admin_lock_update(
            actor_user_id=10,
            actor_role='teacher',
            target_user_id=20,
            target_user_role='student',
            target_user_locked=False,
            lock_state=True,
            unlocked_admin_count=1,
        )
        self.assertEqual(error, 'Only admin can update lock status.')

    def test_self_lock_denied(self):
        error = validate_admin_lock_update(
            actor_user_id=1,
            actor_role='admin',
            target_user_id=1,
            target_user_role='admin',
            target_user_locked=False,
            lock_state=True,
            unlocked_admin_count=2,
        )
        self.assertEqual(error, 'You cannot lock your own account.')

    def test_last_unlocked_admin_lock_denied(self):
        error = validate_admin_lock_update(
            actor_user_id=2,
            actor_role='admin',
            target_user_id=1,
            target_user_role='admin',
            target_user_locked=False,
            lock_state=True,
            unlocked_admin_count=1,
        )
        self.assertEqual(error, 'At least one unlocked admin account must remain in the system.')


class AdminTeacherAssignmentValidationTests(unittest.TestCase):
    def test_non_admin_cannot_assign_teacher(self):
        class_obj = SimpleNamespace(id=10)
        teacher_user = SimpleNamespace(id=20, role='teacher', is_locked=False)
        error = validate_admin_teacher_assignment(
            actor_role='teacher',
            class_obj=class_obj,
            teacher_user=teacher_user,
            current_teacher_id=1,
            target_teacher_id=20,
        )
        self.assertEqual(error, 'Only admin can assign class teacher.')

    def test_locked_teacher_assignment_denied(self):
        class_obj = SimpleNamespace(id=10)
        teacher_user = SimpleNamespace(id=20, role='teacher', is_locked=True)
        error = validate_admin_teacher_assignment(
            actor_role='admin',
            class_obj=class_obj,
            teacher_user=teacher_user,
            current_teacher_id=1,
            target_teacher_id=20,
        )
        self.assertEqual(error, 'Locked teacher accounts cannot be assigned.')

    def test_noop_teacher_assignment_denied(self):
        class_obj = SimpleNamespace(id=10)
        teacher_user = SimpleNamespace(id=20, role='teacher', is_locked=False)
        error = validate_admin_teacher_assignment(
            actor_role='admin',
            class_obj=class_obj,
            teacher_user=teacher_user,
            current_teacher_id=20,
            target_teacher_id=20,
        )
        self.assertEqual(error, 'Class is already assigned to selected teacher.')

    def test_missing_class_denied(self):
        teacher_user = SimpleNamespace(id=20, role='teacher', is_locked=False)
        error = validate_admin_teacher_assignment(
            actor_role='admin',
            class_obj=None,
            teacher_user=teacher_user,
            current_teacher_id=1,
            target_teacher_id=20,
        )
        self.assertEqual(error, 'Sınıf bulunamadı.')

    def test_invalid_teacher_role_denied(self):
        class_obj = SimpleNamespace(id=10)
        teacher_user = SimpleNamespace(id=20, role='student', is_locked=False)
        error = validate_admin_teacher_assignment(
            actor_role='admin',
            class_obj=class_obj,
            teacher_user=teacher_user,
            current_teacher_id=1,
            target_teacher_id=20,
        )
        self.assertEqual(error, 'Target teacher user is invalid.')


class TeacherOwnershipHelperTests(unittest.TestCase):
    def test_teacher_ownership_allows_access(self):
        class_obj = SimpleNamespace(id=10, teacher_id=42)
        with app.test_request_context('/teacher/class/10'):
            from flask import session

            session['user_id'] = 42
            session['role'] = 'teacher'
            self.assertIsNone(ensure_teacher_class_ownership(class_obj, on_fail='teacher_dashboard'))

    def test_teacher_ownership_denies_with_redirect(self):
        class_obj = SimpleNamespace(id=10, teacher_id=100)
        with app.test_request_context('/teacher/class/10'):
            from flask import session

            session['user_id'] = 42
            session['role'] = 'teacher'
            response = ensure_teacher_class_ownership(class_obj, on_fail='teacher_dashboard')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/teacher_dashboard', response.location)

    def test_teacher_ownership_denies_with_json(self):
        class_obj = SimpleNamespace(id=10, teacher_id=100)
        with app.test_request_context('/teacher/session/1/stats'):
            from flask import session

            session['user_id'] = 42
            session['role'] = 'teacher'
            response, status_code = ensure_teacher_class_ownership(class_obj, on_fail='json')
            self.assertEqual(status_code, 403)
            self.assertEqual(response.get_json(), {'error': 'forbidden'})

    def test_teacher_session_ownership_missing_session_redirects(self):
        with app.test_request_context('/teacher/session/999'):
            from flask import session

            session['user_id'] = 42
            session['role'] = 'teacher'
            response = ensure_teacher_session_ownership(None, on_fail='teacher_dashboard')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/teacher_dashboard', response.location)


class StudentOwnershipHelperTests(unittest.TestCase):
    def test_student_membership_allows_access(self):
        class_obj = SimpleNamespace(id=7)
        student_obj = SimpleNamespace(id=42, classes=[class_obj])
        with app.test_request_context('/attendance/token'):
            from flask import session

            session['user_id'] = 42
            session['role'] = 'student'
            self.assertIsNone(ensure_student_class_membership(student_obj, class_obj, on_fail='student_absence'))

    def test_student_membership_denies_with_redirect(self):
        class_obj = SimpleNamespace(id=7)
        student_obj = SimpleNamespace(id=42, classes=[])
        with app.test_request_context('/student/history/7'):
            from flask import session

            session['user_id'] = 42
            session['role'] = 'student'
            response = ensure_student_class_membership(student_obj, class_obj, on_fail='student_absence')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/student/absence', response.location)

    def test_student_event_ownership_denies_with_redirect(self):
        student_obj = SimpleNamespace(id=42)
        event_obj = SimpleNamespace(id=8, student_id=99)
        with app.test_request_context('/student_dashboard'):
            from flask import session

            session['user_id'] = 42
            session['role'] = 'student'
            response = ensure_student_event_ownership(
                student_obj,
                event_obj,
                on_fail='student_dashboard',
                fail_message='Event not found.',
            )
            self.assertEqual(response.status_code, 302)
            self.assertIn('/student_dashboard', response.location)

    def test_student_event_ownership_allows_access(self):
        student_obj = SimpleNamespace(id=42)
        event_obj = SimpleNamespace(id=8, student_id=42)
        with app.test_request_context('/student_dashboard'):
            from flask import session

            session['user_id'] = 42
            session['role'] = 'student'
            self.assertIsNone(
                ensure_student_event_ownership(
                    student_obj,
                    event_obj,
                    on_fail='student_dashboard',
                )
            )


class PermissionFlowTests(unittest.TestCase):
    def test_ensure_permission_allows_authorized_role(self):
        with app.test_request_context('/teacher/account'):
            from flask import session

            session['user_id'] = 7
            session['role'] = 'teacher'
            self.assertIsNone(ensure_permission(PERMISSIONS['TEACHER_ACCOUNT_UPDATE'], 'teacher_account'))

    def test_ensure_permission_denies_unauthorized_role(self):
        with app.test_request_context('/student/account'):
            from flask import session

            session['user_id'] = 7
            session['role'] = 'teacher'
            response = ensure_permission(PERMISSIONS['STUDENT_ACCOUNT_UPDATE'], 'student_account')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/student/account', response.location)

    def test_ensure_permission_allows_empty_permission(self):
        with app.test_request_context('/student/account'):
            from flask import session

            session['user_id'] = 7
            session['role'] = 'teacher'
            self.assertIsNone(ensure_permission(None, 'student_account'))

    def test_permission_required_redirects_when_not_logged_in(self):
        @permission_required(PERMISSIONS['TEACHER_DASHBOARD_VIEW'])
        def protected_view():
            return 'ok'

        with app.test_request_context('/teacher_dashboard'):
            response = protected_view()
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.location)

    def test_permission_required_denies_wrong_role(self):
        @permission_required(PERMISSIONS['TEACHER_DASHBOARD_VIEW'])
        def protected_view():
            return 'ok'

        with app.test_request_context('/teacher_dashboard'):
            from flask import session

            session['user_id'] = 42
            session['role'] = 'student'
            response = protected_view()
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.location)

    def test_permission_required_allows_correct_role(self):
        @permission_required(PERMISSIONS['TEACHER_DASHBOARD_VIEW'])
        def protected_view():
            return 'ok'

        with app.test_request_context('/teacher_dashboard'):
            from flask import session

            session['user_id'] = 42
            session['role'] = 'teacher'
            self.assertEqual(protected_view(), 'ok')

    def test_permission_required_without_mapping_allows_when_logged_in(self):
        @permission_required()
        def protected_view():
            return 'ok'

        with app.test_request_context('/unmapped-endpoint'):
            from flask import session

            session['user_id'] = 42
            session['role'] = 'student'
            self.assertEqual(protected_view(), 'ok')


class TeacherNegativeAccessRouteTests(unittest.TestCase):
    def _teacher_client(self):
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = 42
            sess['role'] = 'teacher'
        return client

    def test_teacher_cannot_access_admin_dashboard(self):
        client = self._teacher_client()
        response = client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_teacher_cannot_access_admin_user_inventory(self):
        client = self._teacher_client()
        response = client.get('/admin/users', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_teacher_cannot_access_admin_class_assignments(self):
        client = self._teacher_client()
        response = client.get('/admin/class-assignments', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_teacher_cannot_access_admin_permission_audit(self):
        client = self._teacher_client()
        response = client.get('/admin/security/permission-audit', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_teacher_cannot_access_admin_operation_audit(self):
        client = self._teacher_client()
        response = client.get('/admin/security/admin-operations', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_teacher_cannot_post_admin_role_update(self):
        client = self._teacher_client()
        response = client.post('/admin/users/1/role', data={'role': 'student'}, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_teacher_cannot_post_admin_lock_toggle(self):
        client = self._teacher_client()
        response = client.post('/admin/users/1/lock', data={'action': 'lock'}, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_teacher_cannot_post_admin_class_assignment(self):
        client = self._teacher_client()
        response = client.post('/admin/classes/1/assign-teacher', data={'teacher_id': '2'}, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)


class StudentNegativeAccessRouteTests(unittest.TestCase):
    def _student_client(self):
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = 52
            sess['role'] = 'student'
        return client

    def test_student_cannot_access_teacher_dashboard(self):
        client = self._student_client()
        response = client.get('/teacher_dashboard', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_student_cannot_access_teacher_history(self):
        client = self._student_client()
        response = client.get('/teacher/history/1', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_student_cannot_access_teacher_account(self):
        client = self._student_client()
        response = client.get('/teacher/account', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_student_cannot_post_teacher_create_class(self):
        client = self._student_client()
        response = client.post('/teacher/create_class', data={'class_name': 'x'}, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_student_cannot_post_teacher_delete_session(self):
        client = self._student_client()
        response = client.post('/teacher/session/1/delete', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_student_cannot_access_admin_dashboard(self):
        client = self._student_client()
        response = client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_student_cannot_access_admin_users(self):
        client = self._student_client()
        response = client.get('/admin/users', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_student_cannot_post_admin_role_update(self):
        client = self._student_client()
        response = client.post('/admin/users/1/role', data={'role': 'teacher'}, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)


class AdminIntegrationRouteTests(unittest.TestCase):
    def _seed_admin_fixture(self):
        token = uuid4().hex[:8]

        next_user_id = (db.session.query(db.func.max(User.id)).scalar() or 0) + 100
        next_class_id = (db.session.query(db.func.max(Class.id)).scalar() or 0) + 100

        actor_admin = User(id=next_user_id, name=f'Admin Actor {token}', email=f'admin.actor.{token}@example.com', role='admin')
        actor_admin.set_password('Pass123!')

        target_student = User(id=next_user_id + 1, name=f'Target Student {token}', email=f'student.target.{token}@example.com', role='student')
        target_student.set_password('Pass123!')

        target_teacher = User(id=next_user_id + 2, name=f'Target Teacher {token}', email=f'teacher.target.{token}@example.com', role='teacher')
        target_teacher.set_password('Pass123!')

        source_teacher = User(id=next_user_id + 3, name=f'Source Teacher {token}', email=f'teacher.source.{token}@example.com', role='teacher')
        source_teacher.set_password('Pass123!')

        db.session.add_all([actor_admin, target_student, target_teacher, source_teacher])
        db.session.commit()

        student_profile = Student(id=target_student.id, student_number=f'AUTO-{token}')
        db.session.add(student_profile)

        class_obj = Class(id=next_class_id, name=f'Integration Class {token}', teacher_id=source_teacher.id)
        db.session.add(class_obj)
        db.session.commit()

        return {
            'actor_admin_id': actor_admin.id,
            'target_student_id': target_student.id,
            'target_teacher_id': target_teacher.id,
            'source_teacher_id': source_teacher.id,
            'class_id': class_obj.id,
        }

    def _admin_client(self, admin_user_id):
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user_id
            sess['role'] = 'admin'
            sess['_csrf_token'] = 'test-csrf-token'
        return client

    def _csrf_payload(self, data=None):
        payload = dict(data or {})
        payload['csrf_token'] = 'test-csrf-token'
        return payload

    def _teacher_client(self, teacher_user_id):
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = teacher_user_id
            sess['role'] = 'teacher'
        return client

    def test_admin_can_open_inventory_and_audit_pages(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])

        inventory_response = client.get('/admin/users', follow_redirects=False)
        self.assertEqual(inventory_response.status_code, 200)
        self.assertIn(b'Admin User Inventory', inventory_response.data)

        operation_audit_response = client.get('/admin/security/admin-operations', follow_redirects=False)
        self.assertEqual(operation_audit_response.status_code, 200)
        self.assertIn(b'Admin Operation Audit', operation_audit_response.data)

        health_response = client.get('/admin/security/health-status', follow_redirects=False)
        self.assertEqual(health_response.status_code, 200)
        self.assertIn(b'Health Status', health_response.data)

    def test_admin_role_update_success_path(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])
        response = client.post(
            f"/admin/users/{fixture['target_student_id']}/role",
            data=self._csrf_payload({'role': 'teacher'}),
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/users', response.location)

        with app.app_context():
            updated_user = db.session.get(User, fixture['target_student_id'])
            self.assertEqual(updated_user.role, 'teacher')

    def test_admin_lock_toggle_success_path(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])

        lock_response = client.post(
            f"/admin/users/{fixture['target_teacher_id']}/lock",
            data=self._csrf_payload({'action': 'lock'}),
            follow_redirects=False,
        )
        self.assertEqual(lock_response.status_code, 302)
        self.assertIn('/admin/users', lock_response.location)

        with app.app_context():
            locked_user = db.session.get(User, fixture['target_teacher_id'])
            self.assertTrue(locked_user.is_locked)

        unlock_response = client.post(
            f"/admin/users/{fixture['target_teacher_id']}/lock",
            data=self._csrf_payload({'action': 'unlock'}),
            follow_redirects=False,
        )
        self.assertEqual(unlock_response.status_code, 302)
        self.assertIn('/admin/users', unlock_response.location)

        with app.app_context():
            unlocked_user = db.session.get(User, fixture['target_teacher_id'])
            self.assertFalse(unlocked_user.is_locked)

    def test_admin_teacher_assignment_success_path(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])
        response = client.post(
            f"/admin/classes/{fixture['class_id']}/assign-teacher",
            data=self._csrf_payload({'teacher_id': str(fixture['target_teacher_id'])}),
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/class-assignments', response.location)

        with app.app_context():
            class_obj = db.session.get(Class, fixture['class_id'])
            self.assertEqual(class_obj.teacher_id, fixture['target_teacher_id'])

    def test_admin_role_update_rejects_invalid_role_value(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])
        response = client.post(
            f"/admin/users/{fixture['target_student_id']}/role",
            data=self._csrf_payload({'role': 'superadmin'}),
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/users', response.location)

        with app.app_context():
            target_user = db.session.get(User, fixture['target_student_id'])
            self.assertEqual(target_user.role, 'student')

    def test_admin_cannot_change_own_role_via_route(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])
        response = client.post(
            f"/admin/users/{fixture['actor_admin_id']}/role",
            data=self._csrf_payload({'role': 'teacher'}),
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/users', response.location)

        with app.app_context():
            actor_admin = db.session.get(User, fixture['actor_admin_id'])
            self.assertEqual(actor_admin.role, 'admin')

    def test_admin_lock_toggle_rejects_invalid_action(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])
        response = client.post(
            f"/admin/users/{fixture['target_teacher_id']}/lock",
            data=self._csrf_payload({'action': 'freeze'}),
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/users', response.location)

        with app.app_context():
            target_user = db.session.get(User, fixture['target_teacher_id'])
            self.assertFalse(target_user.is_locked)

    def test_admin_cannot_lock_own_account_via_route(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])
        response = client.post(
            f"/admin/users/{fixture['actor_admin_id']}/lock",
            data=self._csrf_payload({'action': 'lock'}),
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/users', response.location)

        with app.app_context():
            actor_admin = db.session.get(User, fixture['actor_admin_id'])
            self.assertFalse(actor_admin.is_locked)

    def test_admin_assignment_rejects_invalid_teacher_id_payload(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])
        response = client.post(
            f"/admin/classes/{fixture['class_id']}/assign-teacher",
            data=self._csrf_payload({'teacher_id': 'not-a-number'}),
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/class-assignments', response.location)

        with app.app_context():
            class_obj = db.session.get(Class, fixture['class_id'])
            self.assertEqual(class_obj.teacher_id, fixture['source_teacher_id'])

    def test_admin_assignment_rejects_locked_teacher_target(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()
            target_teacher = db.session.get(User, fixture['target_teacher_id'])
            target_teacher.is_locked = True
            db.session.commit()

        client = self._admin_client(fixture['actor_admin_id'])
        response = client.post(
            f"/admin/classes/{fixture['class_id']}/assign-teacher",
            data=self._csrf_payload({'teacher_id': str(fixture['target_teacher_id'])}),
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/class-assignments', response.location)

        with app.app_context():
            class_obj = db.session.get(Class, fixture['class_id'])
            self.assertEqual(class_obj.teacher_id, fixture['source_teacher_id'])

    def test_admin_post_without_csrf_token_is_rejected(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = fixture['actor_admin_id']
            sess['role'] = 'admin'
            sess['_csrf_token'] = 'expected-token'

        response = client.post(
            f"/admin/users/{fixture['target_student_id']}/role",
            data={'role': 'teacher'},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

        with app.app_context():
            target_user = db.session.get(User, fixture['target_student_id'])
            self.assertEqual(target_user.role, 'student')

    def test_admin_can_open_permission_matrix_and_notifications_pages(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])

        matrix_response = client.get('/admin/security/permission-matrix', follow_redirects=False)
        self.assertEqual(matrix_response.status_code, 200)
        self.assertIn(b'Permission Matrix', matrix_response.data)

        notify_response = client.get('/admin/notifications', follow_redirects=False)
        self.assertEqual(notify_response.status_code, 200)
        self.assertIn(b'Email Notifications', notify_response.data)

    def test_admin_notifications_send_test_rejects_invalid_email(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])
        response = client.post(
            '/admin/notifications',
            data=self._csrf_payload(
                {
                    'action': 'send_test',
                    'test_email': 'not-an-email',
                    'subject': 'T',
                    'body': 'B',
                }
            ),
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Email Notifications', response.data)

    def test_admin_notifications_send_broadcast_works_in_dry_run(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        old_dry_run = app.config.get('EMAIL_DRY_RUN', True)
        app.config['EMAIL_DRY_RUN'] = True
        try:
            client = self._admin_client(fixture['actor_admin_id'])
            response = client.post(
                '/admin/notifications',
                data=self._csrf_payload(
                    {
                        'action': 'send_broadcast',
                        'target_role': 'teacher',
                        'max_recipients': '2',
                        'subject': 'Dry Run',
                        'body': 'Notification body',
                    }
                ),
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Email Notifications', response.data)
        finally:
            app.config['EMAIL_DRY_RUN'] = old_dry_run

    def test_admin_can_publish_announcement_from_notifications_page(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])
        response = client.post(
            '/admin/notifications',
            data=self._csrf_payload(
                {
                    'action': 'publish_announcement',
                    'announcement_target_role': 'student',
                    'announcement_title': 'Maintenance Notice',
                    'announcement_body': 'System maintenance will start at 22:00.',
                }
            ),
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Maintenance Notice', response.data)

        with app.app_context():
            announcement = Announcement.query.order_by(Announcement.id.desc()).first()
            self.assertIsNotNone(announcement)
            self.assertEqual(announcement.title, 'Maintenance Notice')
            self.assertEqual(announcement.target_role, 'student')
            self.assertEqual(announcement.author_id, fixture['actor_admin_id'])

    def test_admin_can_update_and_delete_announcement_from_notifications_page(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()
            course = Course(title='Announcement Course', code='ANN-101', teacher_id=fixture['target_teacher_id'])
            db.session.add(course)
            db.session.flush()
            announcement = Announcement(
                title='Old Title',
                body='Old Body',
                author_id=fixture['actor_admin_id'],
                target_role='student',
                course_id=course.id,
            )
            db.session.add(announcement)
            db.session.commit()
            announcement_id = announcement.id
            course_id = course.id

        client = self._admin_client(fixture['actor_admin_id'])
        update_response = client.post(
            '/admin/notifications',
            data=self._csrf_payload(
                {
                    'action': 'update_announcement',
                    'announcement_id': str(announcement_id),
                    'announcement_target_role': 'teacher',
                    'announcement_course_id': str(course_id),
                    'announcement_starts_at': '2026-04-01T09:00',
                    'announcement_ends_at': '2026-04-02T18:30',
                    'announcement_title': 'Updated Title',
                    'announcement_body': 'Updated Body',
                }
            ),
            follow_redirects=False,
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertIn(b'Updated Title', update_response.data)

        with app.app_context():
            updated = db.session.get(Announcement, announcement_id)
            self.assertIsNotNone(updated)
            self.assertEqual(updated.title, 'Updated Title')
            self.assertEqual(updated.body, 'Updated Body')
            self.assertEqual(updated.target_role, 'teacher')
            self.assertEqual(updated.course_id, course_id)
            self.assertEqual(updated.starts_at, datetime.datetime(2026, 4, 1, 9, 0))
            self.assertEqual(updated.ends_at, datetime.datetime(2026, 4, 2, 18, 30))

        delete_response = client.post(
            '/admin/notifications',
            data=self._csrf_payload(
                {
                    'action': 'delete_announcement',
                    'announcement_id': str(announcement_id),
                }
            ),
            follow_redirects=False,
        )
        self.assertEqual(delete_response.status_code, 200)

        with app.app_context():
            self.assertIsNone(db.session.get(Announcement, announcement_id))

    def test_admin_can_add_and_delete_personal_dashboard_calendar_event(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])
        add_response = client.post(
            '/admin/dashboard',
            data={
                'action': 'add_calendar_event',
                'title': 'Infra Review',
                'event_type': 'activity',
                'event_date': '2026-04-10',
                'note': 'Check rollout tasks',
            },
            follow_redirects=False,
        )
        self.assertEqual(add_response.status_code, 302)
        self.assertIn('/admin/dashboard', add_response.location)

        with app.app_context():
            event = UserCalendarEvent.query.filter_by(user_id=fixture['actor_admin_id']).order_by(UserCalendarEvent.id.desc()).first()
            self.assertIsNotNone(event)
            self.assertEqual(event.title, 'Infra Review')
            event_id = event.id

        delete_response = client.post(
            '/admin/dashboard',
            data={
                'action': 'delete_calendar_event',
                'event_id': str(event_id),
            },
            follow_redirects=False,
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertIn('/admin/dashboard', delete_response.location)

        with app.app_context():
            self.assertIsNone(db.session.get(UserCalendarEvent, event_id))

    def test_teacher_can_add_and_delete_personal_dashboard_calendar_event(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._teacher_client(fixture['target_teacher_id'])
        add_response = client.post(
            '/teacher_dashboard',
            data={
                'action': 'add_calendar_event',
                'title': 'Office Hour',
                'event_type': 'activity',
                'event_date': '2026-04-11',
                'note': 'Meet students',
            },
            follow_redirects=False,
        )
        self.assertEqual(add_response.status_code, 302)
        self.assertIn('/teacher_dashboard', add_response.location)

        with app.app_context():
            event = UserCalendarEvent.query.filter_by(user_id=fixture['target_teacher_id']).order_by(UserCalendarEvent.id.desc()).first()
            self.assertIsNotNone(event)
            self.assertEqual(event.title, 'Office Hour')
            event_id = event.id

        delete_response = client.post(
            '/teacher_dashboard',
            data={
                'action': 'delete_calendar_event',
                'event_id': str(event_id),
            },
            follow_redirects=False,
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertIn('/teacher_dashboard', delete_response.location)

        with app.app_context():
            self.assertIsNone(db.session.get(UserCalendarEvent, event_id))

    def test_teacher_can_preview_student_dashboard_by_student_number(self):
        token = uuid4().hex[:8]
        with app.app_context():
            fixture = self._seed_admin_fixture()

            class_obj = db.session.get(Class, fixture['class_id'])
            class_obj.teacher_id = fixture['target_teacher_id']

            next_user_id = (db.session.query(db.func.max(User.id)).scalar() or 0) + 10
            student_user = User(
                id=next_user_id,
                name=f'Lookup Student {token}',
                email=f'lookup.student.{token}@example.com',
                role='student',
            )
            student_user.set_password('Pass123!')
            db.session.add(student_user)
            db.session.flush()

            student_profile = Student(id=student_user.id, student_number=f'LOOK-{token}')
            class_obj.students.append(student_profile)

            course = Course(title=f'Lookup Course {token}', code=f'LKP-{token}', teacher_id=fixture['target_teacher_id'])
            db.session.add(course)
            db.session.flush()

            db.session.add(CourseEnrollment(student_id=student_profile.id, course_id=course.id))
            db.session.add(
                Announcement(
                    title='Student Notice',
                    body='Dashboard preview notice',
                    author_id=fixture['actor_admin_id'],
                    target_role='student',
                    course_id=course.id,
                )
            )
            db.session.add(
                UserCalendarEvent(
                    user_id=fixture['target_teacher_id'],
                    title='Teacher Reminder',
                    event_type='activity',
                    event_date=datetime.date(2026, 4, 15),
                    note='n',
                )
            )
            db.session.commit()

            lookup_number = student_profile.student_number

        client = self._teacher_client(fixture['target_teacher_id'])
        response = client.get(f'/teacher_dashboard?student_number={lookup_number}', follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn(lookup_number.encode('utf-8'), response.data)
        self.assertIn(b'Lookup Student', response.data)

    def test_teacher_cannot_preview_student_outside_own_classes(self):
        token = uuid4().hex[:8]
        with app.app_context():
            fixture = self._seed_admin_fixture()

            next_user_id = (db.session.query(db.func.max(User.id)).scalar() or 0) + 10
            external_student_user = User(
                id=next_user_id,
                name=f'External Student {token}',
                email=f'external.student.{token}@example.com',
                role='student',
            )
            external_student_user.set_password('Pass123!')
            db.session.add(external_student_user)
            db.session.flush()

            external_student = Student(id=external_student_user.id, student_number=f'OUT-{token}')
            db.session.add(external_student)
            db.session.commit()

            lookup_number = external_student.student_number

        client = self._teacher_client(fixture['target_teacher_id'])
        response = client.get(f'/teacher_dashboard?student_number={lookup_number}', follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'This student number was not found in your classes.', response.data)

    def test_teacher_can_preview_student_registered_to_taught_course(self):
        token = uuid4().hex[:8]
        with app.app_context():
            fixture = self._seed_admin_fixture()

            next_user_id = (db.session.query(db.func.max(User.id)).scalar() or 0) + 10
            student_user = User(
                id=next_user_id,
                name=f'Enrolled Student {token}',
                email=f'enrolled.student.{token}@example.com',
                role='student',
            )
            student_user.set_password('Pass123!')
            db.session.add(student_user)
            db.session.flush()

            student_profile = Student(id=student_user.id, student_number=f'ENR-{token}')
            db.session.add(student_profile)

            course = Course(title=f'Enrollment Course {token}', code=f'ENR-{token}', teacher_id=fixture['target_teacher_id'])
            db.session.add(course)
            db.session.flush()

            db.session.add(CourseEnrollment(student_id=student_profile.id, course_id=course.id))
            db.session.commit()
            lookup_number = student_profile.student_number
            course_code = course.code
            student_email = student_user.email

        client = self._teacher_client(fixture['target_teacher_id'])
        response = client.get(f'/teacher_dashboard?student_number={lookup_number}', follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn(lookup_number.encode('utf-8'), response.data)
        self.assertIn(b'Enrolled Student', response.data)
        self.assertIn(course_code.encode('utf-8'), response.data)
        self.assertIn(student_email.encode('utf-8'), response.data)

    def test_admin_password_reset_success_path(self):
        with app.app_context():
            fixture = self._seed_admin_fixture()

        client = self._admin_client(fixture['actor_admin_id'])
        response = client.post(
            f"/admin/users/{fixture['target_teacher_id']}/password",
            data=self._csrf_payload(
                {
                    'new_password': 'ResetPass123!',
                    'confirm_password': 'ResetPass123!',
                }
            ),
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/users', response.location)

        with app.app_context():
            target_user = db.session.get(User, fixture['target_teacher_id'])
            self.assertTrue(target_user.check_password('ResetPass123!'))


if __name__ == '__main__':
    unittest.main()
