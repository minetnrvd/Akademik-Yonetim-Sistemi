import io
import os
import secrets
import unittest

from app import app, db
from models import (AdminOperationLog, Course, CourseEnrollment, CourseEnrollmentAudit, CourseRegistrationPolicy,
                    Message, PermissionAuditLog, Student, StudentGroup, TermPlan, User)

_CREATED = {'users': [], 'groups': []}


def _user(role):
    token = secrets.token_hex(4)
    # Explicit id far above the sequence: other tests insert fixed ids and must not collide with ours.
    next_id = (db.session.query(db.func.max(User.id)).scalar() or 0) + 500
    user = User(id=next_id, name=f'{role.title()} {token}', email=f'{role}.{token}@example.com', role=role)
    user.set_password('x' * 12)
    db.session.add(user)
    db.session.commit()
    _CREATED['users'].append(user.id)
    return user


def _student():
    user = _user('student')
    student = Student(id=user.id, student_number=f'T{secrets.token_hex(3)}')
    db.session.add(student)
    db.session.commit()
    return student


def _client(user_id, role):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess.update({'user_id': user_id, 'role': role, '_csrf_token': 'tok'})
    return client


def _cleanup_created():
    """Remove what these tests created so auto-increment ids never collide with other tests' fixed ids."""
    with app.app_context():
        for group in StudentGroup.query.filter(StudentGroup.code.like('G%')).all():
            if any(s.id in _CREATED['users'] for s in group.students) or group.advisor_id in _CREATED['users']:
                group.students = []
                db.session.delete(group)
        db.session.commit()
        ids = _CREATED['users']
        from app import _remove_profile_photo_file
        for owner in (Student.query.filter(Student.id.in_(ids), Student.photo_filename.isnot(None)).all()
                      + User.query.filter(User.id.in_(ids), User.photo_filename.isnot(None)).all()):
            _remove_profile_photo_file(owner.photo_filename)
        CourseEnrollmentAudit.query.filter(CourseEnrollmentAudit.actor_user_id.in_(ids)).delete(synchronize_session=False)
        CourseEnrollment.query.filter(CourseEnrollment.student_id.in_(ids)).delete(synchronize_session=False)
        TermPlan.query.filter(TermPlan.student_id.in_(ids)).delete(synchronize_session=False)
        Message.query.filter(Message.sender_id.in_(ids) | Message.recipient_id.in_(ids)).delete(synchronize_session=False)
        Course.query.filter(Course.teacher_id.in_(ids)).delete(synchronize_session=False)
        AdminOperationLog.query.filter(
            AdminOperationLog.actor_user_id.in_(ids) | AdminOperationLog.target_user_id.in_(ids)
        ).delete(synchronize_session=False)
        PermissionAuditLog.query.filter(PermissionAuditLog.user_id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        for user_id in _CREATED['users']:
            student = db.session.get(Student, user_id)
            if student:
                db.session.delete(student)
        db.session.commit()
        for user_id in _CREATED['users']:
            user = db.session.get(User, user_id)
            if user:
                db.session.delete(user)
        db.session.commit()
    _CREATED['users'].clear()


class _CleanTestCase(unittest.TestCase):
    def setUp(self):
        self.addCleanup(_cleanup_created)


class AdvisorTests(_CleanTestCase):
    def test_department_advisor_applies_and_individual_overrides(self):
        with app.app_context():
            dept_teacher, own_teacher, other_teacher = _user('teacher'), _user('teacher'), _user('teacher')
            admin = _user('admin')
            group = StudentGroup(code=f'G{secrets.token_hex(3)}'.upper(), name='Dept')
            member, override, outsider = _student(), _student(), _student()
            group.students.extend([member, override])
            db.session.add(group)
            db.session.commit()
            ids = dict(g=group.id, m=member.id, o=override.id, out=outsider.id,
                       d=dept_teacher.id, own=own_teacher.id, other=other_teacher.id, admin=admin.id)

        admin_client = _client(ids['admin'], 'admin')
        admin_client.post('/admin/groups', data={'csrf_token': 'tok', 'action': 'set_advisor',
                                                 'group_id': ids['g'], 'advisor_id': ids['d']})
        admin_client.post(f"/admin/users/{ids['o']}/advisor", data={'csrf_token': 'tok', 'advisor_id': ids['own']})

        with app.app_context():
            self.assertEqual(db.session.get(Student, ids['m']).advisor_info()[0].id, ids['d'])
            self.assertEqual(db.session.get(Student, ids['o']).advisor_info()[0].id, ids['own'])
            self.assertIsNone(db.session.get(Student, ids['out']).advisor_info()[0])

        dept_client = _client(ids['d'], 'teacher')
        self.assertEqual(dept_client.get(f"/teacher/advisees/{ids['m']}").status_code, 200)
        self.assertEqual(dept_client.get(f"/teacher/advisees/{ids['o']}").status_code, 302)
        self.assertEqual(_client(ids['other'], 'teacher').get(f"/teacher/advisees/{ids['m']}").status_code, 302)
        self.assertEqual(_client(ids['own'], 'teacher').get(f"/teacher/advisees/{ids['o']}").status_code, 200)

        # Clearing the individual advisor falls back to the department advisor.
        admin_client.post(f"/admin/users/{ids['o']}/advisor", data={'csrf_token': 'tok', 'advisor_id': ''})
        with app.app_context():
            self.assertEqual(db.session.get(Student, ids['o']).advisor_info()[0].id, ids['d'])
        self.assertIn(b'Teacher', dept_client.get('/teacher/advisees').data)

    def test_non_teacher_cannot_be_advisor(self):
        with app.app_context():
            student, other_student, admin = _student(), _user('student'), _user('admin')
            ids = (student.id, other_student.id, admin.id)
        _client(ids[2], 'admin').post(f'/admin/users/{ids[0]}/advisor', data={'csrf_token': 'tok', 'advisor_id': ids[1]})
        with app.app_context():
            self.assertIsNone(db.session.get(Student, ids[0]).advisor_id)


class AdvisorSearchTests(_CleanTestCase):
    def test_advisee_list_has_search_data(self):
        with app.app_context():
            teacher, student = _user('teacher'), _student()
            student.advisor_id = teacher.id
            db.session.commit()
            tid, number = teacher.id, student.student_number
        html = _client(tid, 'teacher').get('/teacher/advisees').get_data(as_text=True)
        self.assertIn('id="advisee-search"', html)
        self.assertIn(number, html)


class ViewAsStudentTests(_CleanTestCase):
    def test_teacher_sees_any_student_page_read_only(self):
        with app.app_context():
            teacher, student = _user('teacher'), _student()
            tid, sid, name = teacher.id, student.id, student.user.name
        client = _client(tid, 'teacher')
        # Any student (not only own advisees) can be opened.
        response = client.post(f'/teacher/students/{sid}/view', data={'csrf_token': 'tok'})
        self.assertEqual(response.status_code, 302)
        page = client.get('/student/term-courses')
        self.assertEqual(page.status_code, 200)
        self.assertIn(name, page.get_data(as_text=True))
        self.assertEqual(client.get('/student/transcript').status_code, 200)
        # Mutations and side-effect GETs are blocked while viewing.
        before = client.post('/student/term-courses/update', data={'csrf_token': 'tok', 'action': 'add', 'course_id': '1'})
        self.assertEqual(before.status_code, 302)
        self.assertTrue(before.headers['Location'].endswith('/student/term-courses'))
        self.assertEqual(client.post('/student_dashboard', data={'csrf_token': 'tok'}).status_code, 302)
        # Student pages sit under the teacher's own top navigation, with a side menu.
        html = page.get_data(as_text=True)
        self.assertIn('va-sidebar', html)
        self.assertIn('/teacher/advisees', html)
        self.assertIn('va-back', html)
        self.assertNotIn('/student/absence" class="pv-navlink"', html)
        # Following a teacher link in the top navigation leaves the student view.
        self.assertEqual(client.get('/teacher/advisees').status_code, 200)
        self.assertEqual(client.get('/student/transcript').status_code, 302)
        # Exit restores the teacher session.
        client.post(f'/teacher/students/{sid}/view', data={'csrf_token': 'tok'})
        client.post('/view-as/exit', data={'csrf_token': 'tok'})
        self.assertEqual(client.get('/teacher/advisees').status_code, 200)

    def test_student_cannot_start_view_as(self):
        with app.app_context():
            a, b = _student(), _student()
            aid, bid = a.id, b.id
        response = _client(aid, 'student').post(f'/teacher/students/{bid}/view', data={'csrf_token': 'tok'})
        self.assertNotEqual(response.status_code, 200)
        with _client(aid, 'student') as c:
            c.post(f'/teacher/students/{bid}/view', data={'csrf_token': 'tok'})
            from flask import session
            self.assertIsNone(session.get('view_as_origin'))


class AdvisorCourseEditTests(_CleanTestCase):
    def _setup(self):
        with app.app_context():
            advisor, other, student = _user('teacher'), _user('teacher'), _student()
            student.advisor_id = advisor.id
            course = Course(code=f'T{secrets.token_hex(4)}'.upper(), title='Test Course', credit=3, capacity=60,
                            teacher_id=advisor.id)
            db.session.add(course)
            db.session.commit()
            return advisor.id, other.id, student.id, course.id

    def _enrolled(self, student_id, course_id):
        with app.app_context():
            return CourseEnrollment.query.filter_by(student_id=student_id, course_id=course_id).first() is not None

    def test_advisor_edits_own_advisee_courses_others_cannot(self):
        advisor_id, other_id, student_id, course_id = self._setup()
        form = {'csrf_token': 'tok', 'action': 'add', 'course_id': str(course_id)}

        other = _client(other_id, 'teacher')
        other.post(f'/teacher/students/{student_id}/view', data={'csrf_token': 'tok'})
        banner = other.get('/student/term-courses').get_data(as_text=True)
        self.assertIn('view-as-banner', banner)
        other.post('/student/term-courses/update', data=form)
        self.assertFalse(self._enrolled(student_id, course_id))

        advisor = _client(advisor_id, 'teacher')
        advisor.post(f'/teacher/students/{student_id}/view', data={'csrf_token': 'tok'})
        page = advisor.get('/student/term-courses').get_data(as_text=True)
        self.assertNotIn('view-as-banner', page)
        advisor.post('/student/term-courses/update', data=form)
        self.assertTrue(self._enrolled(student_id, course_id))
        with app.app_context():
            audit = CourseEnrollmentAudit.query.filter_by(student_id=student_id, course_id=course_id).first()
            self.assertEqual(audit.actor_user_id, advisor_id)
            self.assertIn('advisor', audit.detail)
        advisor.post('/student/term-courses/update', data={**form, 'action': 'drop'})
        self.assertFalse(self._enrolled(student_id, course_id))

    def test_finance_pages_hidden_from_teachers(self):
        advisor_id, _, student_id, _ = self._setup()
        advisor = _client(advisor_id, 'teacher')
        advisor.post(f'/teacher/students/{student_id}/view', data={'csrf_token': 'tok'})
        html = advisor.get('/student/term-courses').get_data(as_text=True)
        self.assertIn('va-sidebar', html)
        self.assertNotIn('/student/payment', html)
        self.assertNotIn('/student/current-account', html)
        response = advisor.get('/student/payment')
        self.assertNotEqual(response.status_code, 200)


class StudentSummaryAndPhotoTests(_CleanTestCase):
    def _png(self):
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (30, 20), (200, 30, 30)).save(buf, 'PNG')
        buf.seek(0)
        return buf

    def test_summary_card_and_photo_flow(self):
        with app.app_context():
            teacher, other_student, student = _user('teacher'), _student(), _student()
            student.student_number = 'K20240362'
            student.university_academic_year = '2025-2026'
            student.university_term = 'Güz'
            student.university_department = 'Bilgisayar Mühendisliği'
            db.session.commit()
            tid, oid, sid = teacher.id, other_student.id, student.id
            email = student.user.email

        teacher = _client(tid, 'teacher')
        teacher.post(f'/teacher/students/{sid}/view', data={'csrf_token': 'tok'})
        html = teacher.get('/student/term-courses').get_data(as_text=True)
        self.assertTrue('Year 2' in html or '2. sınıf' in html)
        for expected in ('K20240362', email, 'Bilgisayar Mühendisliği', '2025-2026 · Güz', 'va-initials'):
            self.assertIn(expected, html)
        self.assertEqual(teacher.get(f'/student-photo/{sid}').status_code, 404)  # no photo yet

        owner = _client(sid, 'student')
        bad = owner.post('/student/account', data={'csrf_token': 'tok', 'action': 'upload_photo',
                                                   'photo': (io.BytesIO(b'not an image'), 'x.png')},
                         content_type='multipart/form-data')
        self.assertEqual(bad.status_code, 302)
        with app.app_context():
            self.assertIsNone(db.session.get(Student, sid).photo_filename)

        owner.post('/student/account', data={'csrf_token': 'tok', 'action': 'upload_photo',
                                             'photo': (self._png(), 'me.png')}, content_type='multipart/form-data')
        with app.app_context():
            self.assertTrue(db.session.get(Student, sid).photo_filename)
        self.assertEqual(owner.get(f'/student-photo/{sid}').status_code, 200)
        self.assertEqual(owner.get(f'/student-photo/{sid}').mimetype, 'image/jpeg')
        self.assertEqual(teacher.get(f'/student-photo/{sid}').status_code, 200)
        self.assertEqual(_client(oid, 'student').get(f'/student-photo/{sid}').status_code, 404)
        self.assertIn('va-photo" src', teacher.get('/student/term-courses').get_data(as_text=True))


class TeacherProfileTests(_CleanTestCase):
    def _png(self):
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (40, 40), (20, 90, 160)).save(buf, 'PNG')
        buf.seek(0)
        return buf

    def test_teacher_edits_profile_and_dashboard_shows_it(self):
        with app.app_context():
            teacher, student = _user('teacher'), _student()
            student.advisor_id = teacher.id
            db.session.commit()
            tid, sid = teacher.id, student.id
        client = _client(tid, 'teacher')
        client.post('/teacher/account', data={
            'csrf_token': 'tok', 'action': 'update_profile', 'academic_title': 'Prof. Dr.',
            'faculty': 'Mühendislik', 'department': 'Bilgisayar', 'office': 'B-214',
            'office_hours': 'Sal 10:00-12:00'})
        html = client.get('/teacher_dashboard').get_data(as_text=True)
        for expected in ('Prof. Dr.', 'Mühendislik', 'Bilgisayar', 'B-214', 'Sal 10:00-12:00', 'tp-initials'):
            self.assertIn(expected, html)
        self.assertIn('<strong>1</strong><span>', html)  # one advisee

        # Photo: bad file rejected, real image stored and visible to other signed-in users.
        client.post('/teacher/account', data={'csrf_token': 'tok', 'action': 'upload_photo',
                                              'photo': (io.BytesIO(b'nope'), 'x.png')}, content_type='multipart/form-data')
        self.assertEqual(client.get(f'/teacher-photo/{tid}').status_code, 404)
        client.post('/teacher/account', data={'csrf_token': 'tok', 'action': 'upload_photo',
                                              'photo': (self._png(), 'me.png')}, content_type='multipart/form-data')
        self.assertEqual(client.get(f'/teacher-photo/{tid}').status_code, 200)
        self.assertEqual(_client(sid, 'student').get(f'/teacher-photo/{tid}').status_code, 200)
        self.assertIn('tp-photo" src', client.get('/teacher_dashboard').get_data(as_text=True))
        account = client.get('/teacher/account').get_data(as_text=True)
        self.assertIn('name="action" value="remove_photo"', account)  # remove button submits its own action
        self.assertEqual(account.count('name="action" value="upload_photo"'), 1)
        client.post('/teacher/account', data={'csrf_token': 'tok', 'action': 'remove_photo'})
        self.assertEqual(client.get(f'/teacher-photo/{tid}').status_code, 404)

    def test_students_cannot_update_teacher_profile(self):
        with app.app_context():
            student = _student()
            sid = student.id
        response = _client(sid, 'student').post('/teacher/account', data={
            'csrf_token': 'tok', 'action': 'update_profile', 'academic_title': 'Hacker'})
        self.assertNotEqual(response.status_code, 200)
        with app.app_context():
            self.assertIsNone(db.session.get(User, sid).academic_title)


class SharedAccountPageTests(_CleanTestCase):
    def test_every_role_uses_the_shared_account_template(self):
        expectations = {
            'admin': ('/admin/account', False, False, False),
            'registrar': ('/registrar/account', False, False, False),
            'assistant': ('/assistant/account', False, False, False),
            'teacher': ('/teacher/account', True, True, True),
            'student': ('/student/account', False, True, False),
        }
        with app.app_context():
            users = {role: (_student() if role == 'student' else _user(role)) for role in expectations}
            ids = {role: user.id for role, user in users.items()}
        for role, (path, profile, photo, deletable) in expectations.items():
            html = _client(ids[role], role).get(path).get_data(as_text=True)
            self.assertIn('acc-grid', html, role)
            self.assertIn('name="action" value="change_password"', html, role)
            self.assertEqual('name="action" value="update_profile"' in html, profile, role)
            self.assertEqual('name="action" value="upload_photo"' in html, photo, role)
            self.assertEqual('name="action" value="delete_account"' in html, deletable, role)

    def test_staff_password_change_still_works_through_shared_page(self):
        with app.app_context():
            admin = _user('admin')
            admin_id = admin.id
        client = _client(admin_id, 'admin')
        new_password = 'Another-Pass-2026!'
        client.post('/admin/account', data={'csrf_token': 'tok', 'action': 'change_password',
                                            'current_password': 'x' * 12, 'new_password': new_password,
                                            'new_password_confirm': new_password})
        with app.app_context():
            self.assertTrue(db.session.get(User, admin_id).check_password(new_password))


class TermPlanApprovalTests(_CleanTestCase):
    def setUp(self):
        super().setUp()
        with app.app_context():
            policy = CourseRegistrationPolicy.query.first()
            if not policy:
                policy = CourseRegistrationPolicy(min_credits=0, max_credits=30, is_locked=False)
                db.session.add(policy)
            saved = (policy.is_locked, policy.add_drop_start, policy.add_drop_end, policy.min_credits, policy.max_credits)
            policy.is_locked, policy.add_drop_start, policy.add_drop_end, policy.min_credits, policy.max_credits = False, None, None, 0, 45
            db.session.commit()
            policy_id = policy.id

        def _restore():
            with app.app_context():
                pol = db.session.get(CourseRegistrationPolicy, policy_id)
                pol.is_locked, pol.add_drop_start, pol.add_drop_end, pol.min_credits, pol.max_credits = saved
                db.session.commit()
        self.addCleanup(_restore)

    def _setup(self, with_advisor=True):
        with app.app_context():
            advisor, student = _user('teacher'), _student()
            if with_advisor:
                student.advisor_id = advisor.id
            course = Course(code=f'T{secrets.token_hex(4)}'.upper(), title='Plan Course', credit=3, capacity=60,
                            teacher_id=advisor.id)
            db.session.add(course)
            db.session.commit()
            return advisor.id, student.id, course.id

    def _plan_status(self, student_id):
        with app.app_context():
            plan = TermPlan.query.filter_by(student_id=student_id).first()
            return plan.status if plan else 'draft'

    def _approved(self, student_id, course_id):
        with app.app_context():
            return CourseEnrollment.query.filter_by(student_id=student_id, course_id=course_id).one().approved

    def _add(self, client, course_id, action='add'):
        client.post('/student/term-courses/update', data={'csrf_token': 'tok', 'action': action, 'course_id': str(course_id)})

    def test_student_without_advisor_cannot_register(self):
        _, student_id, course_id = self._setup(with_advisor=False)
        self._add(_client(student_id, 'student'), course_id)
        with app.app_context():
            self.assertIsNone(CourseEnrollment.query.filter_by(student_id=student_id).first())

    def test_submit_locks_plan_and_approval_makes_courses_official(self):
        advisor_id, student_id, course_id = self._setup()
        student = _client(student_id, 'student')
        self._add(student, course_id)
        self.assertFalse(self._approved(student_id, course_id))

        # Not approved yet: hidden from the teacher's course roster.
        advisor = _client(advisor_id, 'teacher')
        with app.app_context():
            number = db.session.get(Student, student_id).student_number
        self.assertNotIn(number, advisor.get(f'/teacher/course-roster?course_id={course_id}').get_data(as_text=True))

        student.post('/student/term-plan/submit', data={'csrf_token': 'tok'})
        self.assertEqual(self._plan_status(student_id), 'pending')
        self._add(student, course_id, 'drop')  # locked now
        with app.app_context():
            self.assertIsNotNone(CourseEnrollment.query.filter_by(student_id=student_id, course_id=course_id).first())

        self.assertIn('Plan Course', advisor.get('/announcements?box=approvals').get_data(as_text=True))
        advisor.post(f'/teacher/term-plans/{student_id}/decision', data={'csrf_token': 'tok', 'action': 'approve'})
        self.assertEqual(self._plan_status(student_id), 'approved')
        self.assertTrue(self._approved(student_id, course_id))
        with app.app_context():
            self.assertEqual(Message.query.filter_by(recipient_id=student_id, sender_id=advisor_id).count(), 1)
        self.assertIn(number, advisor.get(f'/teacher/course-roster?course_id={course_id}').get_data(as_text=True))

    def test_reject_requires_reason_and_reopens_plan(self):
        advisor_id, student_id, course_id = self._setup()
        student = _client(student_id, 'student')
        self._add(student, course_id)
        student.post('/student/term-plan/submit', data={'csrf_token': 'tok'})

        advisor = _client(advisor_id, 'teacher')
        url = f'/teacher/term-plans/{student_id}/decision'
        advisor.post(url, data={'csrf_token': 'tok', 'action': 'reject', 'reason': '  '})
        self.assertEqual(self._plan_status(student_id), 'pending')
        advisor.post(url, data={'csrf_token': 'tok', 'action': 'reject', 'reason': 'CMP205 al'})
        self.assertEqual(self._plan_status(student_id), 'rejected')
        with app.app_context():
            self.assertIn('CMP205 al', Message.query.filter_by(recipient_id=student_id).one().body)
        self.assertIn('CMP205 al', student.get('/student/term-courses').get_data(as_text=True))

        # A rejected plan is editable again.
        self._add(student, course_id, 'drop')
        with app.app_context():
            self.assertIsNone(CourseEnrollment.query.filter_by(student_id=student_id).first())

    def test_other_teacher_cannot_decide(self):
        advisor_id, student_id, course_id = self._setup()
        with app.app_context():
            other_id = _user('teacher').id
        student = _client(student_id, 'student')
        self._add(student, course_id)
        student.post('/student/term-plan/submit', data={'csrf_token': 'tok'})
        other = _client(other_id, 'teacher')
        other.post(f'/teacher/term-plans/{student_id}/decision', data={'csrf_token': 'tok', 'action': 'approve'})
        self.assertEqual(self._plan_status(student_id), 'pending')
        self.assertNotIn('Plan Course', other.get('/announcements?box=approvals').get_data(as_text=True))

    def test_courses_over_the_ects_limit_cannot_be_added(self):
        _, student_id, course_id = self._setup()
        with app.app_context():
            CourseRegistrationPolicy.query.first().max_credits = 5  # sample course is 6 ECTS
            db.session.commit()
        student = _client(student_id, 'student')
        page = student.get('/student/term-courses').get_data(as_text=True)
        self.assertIn('pill-limit', page)
        self.assertIn('tc-limit', page)
        self._add(student, course_id)
        with app.app_context():
            self.assertIsNone(CourseEnrollment.query.filter_by(student_id=student_id).first())

    def test_advisor_approves_from_student_view_and_returns_to_inbox(self):
        advisor_id, student_id, course_id = self._setup()
        with app.app_context():
            other_id = _user('teacher').id
        student = _client(student_id, 'student')
        self._add(student, course_id)
        student.post('/student/term-plan/submit', data={'csrf_token': 'tok'})

        other = _client(other_id, 'teacher')  # not the advisor: read-only view, cannot approve
        other.post(f'/teacher/students/{student_id}/view', data={'csrf_token': 'tok'})
        other.post('/view-as/term-plan/approve', data={'csrf_token': 'tok'})
        self.assertEqual(self._plan_status(student_id), 'pending')

        advisor = _client(advisor_id, 'teacher')
        advisor.post(f'/teacher/students/{student_id}/view', data={'csrf_token': 'tok'})
        self.assertIn('/view-as/term-plan/approve', advisor.get('/student/term-courses').get_data(as_text=True))
        response = advisor.post('/view-as/term-plan/approve', data={'csrf_token': 'tok'})
        self.assertIn('/announcements?box=approvals', response.headers['Location'])
        self.assertEqual(self._plan_status(student_id), 'approved')
        self.assertTrue(self._approved(student_id, course_id))
        with advisor.session_transaction() as sess:
            self.assertEqual((sess['user_id'], sess['role']), (advisor_id, 'teacher'))
            self.assertNotIn('view_as_origin', sess)
