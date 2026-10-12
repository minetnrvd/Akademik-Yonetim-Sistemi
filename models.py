from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

db = SQLAlchemy()


def _utc_now_naive() -> datetime.datetime:
    # Keep DB values timezone-naive while sourcing from timezone-aware UTC clock.
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

# ------------------ MANY-TO-MANY RELATION ------------------
student_classes = db.Table('student_classes',
    db.Column('student_id', db.Integer, db.ForeignKey('students.id')),
    db.Column('class_id', db.Integer, db.ForeignKey('classes.id'))
)

# ------------------ USER MODEL ------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)  # student, teacher, admin
    is_locked = db.Column(db.Boolean, nullable=False, default=False, index=True)
    # Last time the user opened the announcement inbox; newer announcements count as unread.
    announcements_seen_at = db.Column(db.DateTime, nullable=True)
    # Teacher profile (shown on the teacher dashboard, edited on the account page).
    academic_title = db.Column(db.String(60), nullable=True)   # e.g. Prof. Dr.
    faculty = db.Column(db.String(140), nullable=True)
    department = db.Column(db.String(140), nullable=True)
    office = db.Column(db.String(80), nullable=True)
    office_hours = db.Column(db.String(160), nullable=True)
    photo_filename = db.Column(db.String(120), nullable=True)

    # Student profile relationship.
    students = db.relationship('Student', backref='user', lazy=True, foreign_keys='Student.id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ------------------ STUDENT MODEL ------------------
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    student_number = db.Column(db.String(20), nullable=False)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    birth_place = db.Column(db.String(120), nullable=True)
    identity_number = db.Column(db.String(30), nullable=True)
    nationality = db.Column(db.String(80), nullable=True)
    registered_city = db.Column(db.String(120), nullable=True)
    registered_district = db.Column(db.String(120), nullable=True)
    passport_number = db.Column(db.String(40), nullable=True)
    passport_active = db.Column(db.Boolean, default=False)
    passport_issue_date = db.Column(db.Date, nullable=True)
    passport_issue_place = db.Column(db.String(120), nullable=True)
    passport_expiry_date = db.Column(db.Date, nullable=True)
    marital_status = db.Column(db.String(40), nullable=True)
    blood_type = db.Column(db.String(10), nullable=True)
    is_veteran_martyr_relative = db.Column(db.Boolean, default=False)
    is_disabled = db.Column(db.Boolean, default=False)
    disability_type = db.Column(db.String(120), nullable=True)
    disability_rate = db.Column(db.String(20), nullable=True)
    is_employed = db.Column(db.Boolean, default=False)
    is_group_company = db.Column(db.Boolean, default=False)
    company_name = db.Column(db.String(140), nullable=True)
    work_type = db.Column(db.String(80), nullable=True)
    employment_start_date = db.Column(db.Date, nullable=True)
    university_entry_place = db.Column(db.String(120), nullable=True)
    university_entry_type = db.Column(db.String(120), nullable=True)
    university_academic_year = db.Column(db.String(20), nullable=True)
    university_term = db.Column(db.String(20), nullable=True)
    university_faculty = db.Column(db.String(140), nullable=True)
    university_department = db.Column(db.String(140), nullable=True)
    university_scholarship_type = db.Column(db.String(120), nullable=True)
    university_placement_type = db.Column(db.String(120), nullable=True)
    university_score_type = db.Column(db.String(120), nullable=True)
    university_achievement_score = db.Column(db.String(40), nullable=True)
    university_placement_score = db.Column(db.String(40), nullable=True)
    university_preference_order = db.Column(db.String(40), nullable=True)
    highschool_name = db.Column(db.String(160), nullable=True)
    highschool_info = db.Column(db.String(200), nullable=True)
    highschool_graduation_date = db.Column(db.Date, nullable=True)
    # Academic advisor (a teacher), assigned by admin.
    advisor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    # Profile photo (re-encoded JPEG under uploads/student_photos, served through student_photo).
    photo_filename = db.Column(db.String(120), nullable=True)

    advisor = db.relationship('User', foreign_keys=[advisor_id], backref='advisees')

    def advisor_info(self):
        """(advisor User or None, 'student'|'group'|None, group code or None).
        A student's own advisor wins; otherwise the first department group that has one."""
        if self.advisor is not None:
            return self.advisor, 'student', None
        for group in sorted(self.groups, key=lambda g: g.code or ''):
            if group.advisor is not None:
                return group.advisor, 'group', group.code
        return None, None, None

    # Classes taken by the student (many-to-many).
    classes = db.relationship('Class', secondary=student_classes, back_populates='students')

# ------------------ CLASS MODEL ------------------
# Teaching assistants of a class (assigned by the class's teacher).
class_assistants = db.Table('class_assistants',
    db.Column('class_id', db.Integer, db.ForeignKey('classes.id', ondelete='CASCADE'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
)


# Department groups (e.g. CMP, SWE): a student can belong to several.
student_group_members = db.Table('student_group_members',
    db.Column('group_id', db.Integer, db.ForeignKey('student_groups.id', ondelete='CASCADE'), primary_key=True),
    db.Column('student_id', db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), primary_key=True),
)


class StudentGroup(db.Model):
    __tablename__ = 'student_groups'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # e.g. CMP
    name = db.Column(db.String(120), nullable=False)  # e.g. Bilgisayar Mühendisliği
    created_at = db.Column(db.DateTime, default=_utc_now_naive)
    # Department advisor: advises every member that has no advisor of their own.
    advisor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    advisor = db.relationship('User', foreign_keys=[advisor_id])

    students = db.relationship('Student', secondary=student_group_members, lazy=True,
                               backref=db.backref('groups', lazy=True))


class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Fixed class QR code metadata.
    qr_token = db.Column(db.String(20), unique=True, nullable=True)
    qr_filename = db.Column(db.String(200), nullable=True)

    # Students
    students = db.relationship('Student', secondary=student_classes, back_populates='classes')

    # Teacher relationship
    teacher = db.relationship('User', backref='teacher_classes')
    assistants = db.relationship('User', secondary=class_assistants, lazy=True,
                                 backref=db.backref('assisted_classes', lazy=True))

    # Attendance sessions
    sessions = db.relationship('AttendanceSession', backref='class_obj', lazy=True)

# ------------------ ATTENDANCE SESSION ------------------
class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False, index=True)
    date = db.Column(db.DateTime, default=_utc_now_naive, index=True)
    qr_token = db.Column(db.String(20), unique=True, nullable=False)
    qr_filename = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    week = db.Column(db.String(20), nullable=True)
    active = db.Column(db.Boolean, default=False, index=True)
    confirmed = db.Column(db.Boolean, default=False, index=True)

    __table_args__ = (
        db.Index('ix_attendance_sessions_class_active_date', 'class_id', 'active', 'date'),
        db.Index('ix_attendance_sessions_class_confirmed_date', 'class_id', 'confirmed', 'date'),
    )

    # Attendance records
    records = db.relationship('AttendanceRecord', backref='session', lazy=True)

# ------------------ ATTENDANCE RECORD ------------------
class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False, index=True)
    present = db.Column(db.Boolean, default=False, index=True)

    __table_args__ = (
        db.Index('ix_attendance_records_session_present', 'session_id', 'present'),
        db.Index('ix_attendance_records_student_session_present', 'student_id', 'session_id', 'present'),
    )

    student = db.relationship('Student', backref='attendance_records')


# ------------------ UNIVERSITY PORTAL MODELS ------------------
GRADE_POINTS = {
    'AA': 4.0,
    'BA': 3.5,
    'BB': 3.0,
    'CB': 2.5,
    'CC': 2.0,
    'DC': 1.5,
    'DD': 1.0,
    'FD': 0.5,
    'FF': 0.0,
}


class AcademicTerm(db.Model):
    __tablename__ = 'academic_terms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)  # e.g. 2026 Spring
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=False)

    courses = db.relationship('Course', backref='term', lazy=True)


# Two load measures, as at Turkish universities: national credit (kredi, from weekly hours, usually 3-4)
# and ECTS (AKTS, student workload: ~30 per term, typically 5-8 per course). Limits and GPA use ECTS.
DEFAULT_COURSE_CREDIT = 3
DEFAULT_COURSE_ECTS = 6


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True)  # e.g. CENG101
    title = db.Column(db.String(120), nullable=False)
    credit = db.Column(db.Integer, nullable=False, default=DEFAULT_COURSE_CREDIT)  # national credit (kredi)
    ects = db.Column(db.Integer, nullable=False, default=DEFAULT_COURSE_ECTS, server_default="6")  # AKTS
    capacity = db.Column(db.Integer, nullable=False, default=60)
    schedule_slot = db.Column(db.String(80), nullable=True)  # e.g. Mon-09:00-11:00
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey('academic_terms.id'), nullable=True)

    teacher = db.relationship('User', backref='courses_taught')
    enrollments = db.relationship('CourseEnrollment', backref='course', lazy=True, cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', backref='course', lazy=True)


class CourseEnrollment(db.Model):
    __tablename__ = 'course_enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=_utc_now_naive)
    # Official only once the advisor approves the term plan; teacher-side lists show approved rows only.
    approved = db.Column(db.Boolean, nullable=False, default=False, server_default=db.true())

    student = db.relationship('Student', backref='course_enrollments')
    grades = db.relationship('GradeRecord', backref='enrollment', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_id', name='uq_course_enrollment_student_course'),
    )


class TermPlan(db.Model):
    """A student's course selection for the term and its advisor approval state.

    draft/rejected: the student edits and submits; pending: locked, waiting for the advisor;
    approved: the enrollments are official. The advisor may edit at any time.
    """
    __tablename__ = 'term_plans'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, unique=True)
    status = db.Column(db.String(20), nullable=False, default='draft', index=True)
    submitted_at = db.Column(db.DateTime, nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    decided_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    rejection_reason = db.Column(db.String(500), nullable=True)

    student = db.relationship('Student', backref=db.backref('term_plan', uselist=False))
    decided_by = db.relationship('User', foreign_keys=[decided_by_id])


class GradeRecord(db.Model):
    __tablename__ = 'grade_records'
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('course_enrollments.id'), nullable=False)
    assessment_name = db.Column(db.String(120), nullable=False)  # Midterm, Final, Quiz 1 ...
    letter_grade = db.Column(db.String(2), nullable=False)  # AA, BA, ... FF
    grade_point = db.Column(db.Float, nullable=False)
    entered_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # teacher or assistant
    entered_by = db.relationship('User', foreign_keys=[entered_by_id])
    created_at = db.Column(db.DateTime, default=_utc_now_naive)

    @staticmethod
    def point_from_letter(letter_grade: str) -> float:
        return GRADE_POINTS.get((letter_grade or '').upper(), 0.0)


class CourseRegistrationPolicy(db.Model):
    __tablename__ = 'course_registration_policies'
    id = db.Column(db.Integer, primary_key=True)
    add_drop_start = db.Column(db.DateTime, nullable=True)
    add_drop_end = db.Column(db.DateTime, nullable=True)
    min_credits = db.Column(db.Integer, nullable=False, default=0)
    max_credits = db.Column(db.Integer, nullable=False, default=45)
    is_locked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=_utc_now_naive)
    updated_at = db.Column(db.DateTime, default=_utc_now_naive, onupdate=_utc_now_naive)


class CourseEnrollmentAudit(db.Model):
    __tablename__ = 'course_enrollment_audits'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=_utc_now_naive, nullable=False, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False, index=True)
    action = db.Column(db.String(20), nullable=False, index=True)  # add, drop, add_override, drop_override
    detail = db.Column(db.String(240), nullable=True)

    actor_user = db.relationship('User', backref='course_enrollment_audits')
    student = db.relationship('Student', backref='course_enrollment_audits')
    course = db.relationship('Course', backref='enrollment_audits')


class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_role = db.Column(db.String(20), nullable=True)  # student, teacher, all
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('student_groups.id'), nullable=True)  # department group audience
    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now_naive)

    author = db.relationship('User', backref='announcements_authored')
    group = db.relationship('StudentGroup')


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(150), nullable=True)
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, default=_utc_now_naive)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='messages_sent')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='messages_received')


class StudentCalendarEvent(db.Model):
    __tablename__ = 'student_calendar_events'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    title = db.Column(db.String(140), nullable=False)
    event_type = db.Column(db.String(20), nullable=False, default='activity')  # exam or activity
    event_date = db.Column(db.Date, nullable=False, index=True)
    note = db.Column(db.String(240), nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now_naive)

    student = db.relationship('Student', backref='calendar_events')


class UserCalendarEvent(db.Model):
    __tablename__ = 'user_calendar_events'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(140), nullable=False)
    event_type = db.Column(db.String(20), nullable=False, default='activity')
    event_date = db.Column(db.Date, nullable=False, index=True)
    note = db.Column(db.String(240), nullable=True)
    created_at = db.Column(db.DateTime, default=_utc_now_naive)

    user = db.relationship('User', backref='calendar_events')


class PermissionAuditLog(db.Model):
    __tablename__ = 'permission_audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=_utc_now_naive, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    role = db.Column(db.String(20), nullable=True, index=True)
    endpoint = db.Column(db.String(120), nullable=True, index=True)
    permission = db.Column(db.String(120), nullable=True, index=True)
    method = db.Column(db.String(16), nullable=True)
    path = db.Column(db.String(300), nullable=True)
    ip = db.Column(db.String(64), nullable=True)

    user = db.relationship('User', backref='permission_audit_logs')


class AdminOperationLog(db.Model):
    __tablename__ = 'admin_operation_logs'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=_utc_now_naive, nullable=False, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action = db.Column(db.String(60), nullable=False, index=True)
    old_value = db.Column(db.String(60), nullable=True)
    new_value = db.Column(db.String(60), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='ok', index=True)
    detail = db.Column(db.String(240), nullable=True)
    ip = db.Column(db.String(64), nullable=True)

    actor_user = db.relationship('User', foreign_keys=[actor_user_id], backref='admin_operations_as_actor')
    target_user = db.relationship('User', foreign_keys=[target_user_id], backref='admin_operations_as_target')




