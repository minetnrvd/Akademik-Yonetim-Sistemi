import argparse
import datetime as dt
import json
import statistics
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app, db, User, Student, Class
from models import student_classes


def _make_user(name, email, role, password, user_id=None):
    user = User(id=user_id, name=name, email=email, role=role, is_locked=False)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user


def _seed_data():
    stamp = dt.datetime.now(dt.UTC).strftime('%Y%m%d%H%M%S')
    next_user_id = (db.session.query(db.func.max(User.id)).scalar() or 0) + 100

    admin = _make_user('UAT Admin', f'uat_admin_{stamp}@example.com', 'admin', 'UATAdmin1!', user_id=next_user_id)
    teacher = _make_user('UAT Teacher', f'uat_teacher_{stamp}@example.com', 'teacher', 'UATTeacher1!', user_id=next_user_id + 1)
    student_user = _make_user('UAT Student', f'uat_student_{stamp}@example.com', 'student', 'UATStudent1!', user_id=next_user_id + 2)

    student = Student(id=student_user.id, student_number=f'UAT{stamp[-6:]}')
    db.session.add(student)
    db.session.flush()

    cls = Class(name=f'UAT_CLASS_{stamp}', teacher_id=teacher.id)
    db.session.add(cls)
    db.session.flush()

    student.classes.append(cls)
    db.session.commit()

    return {
        'created_emails': [admin.email, teacher.email, student_user.email],
        'admin_id': admin.id,
        'teacher_id': teacher.id,
        'student_id': student_user.id,
    }


def _cleanup_data(emails):
    users = User.query.filter(User.email.in_(emails)).all()
    user_ids = [u.id for u in users]
    class_ids = [cls.id for cls in Class.query.filter(Class.teacher_id.in_(user_ids)).all()]

    if user_ids:
        db.session.execute(student_classes.delete().where(student_classes.c.student_id.in_(user_ids)))
    if class_ids:
        db.session.execute(student_classes.delete().where(student_classes.c.class_id.in_(class_ids)))
        Class.query.filter(Class.id.in_(class_ids)).delete(synchronize_session=False)

    if user_ids:
        Student.query.filter(Student.id.in_(user_ids)).delete(synchronize_session=False)

    User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.session.commit()


def _measure_avg_ms(client, path, attempts=12):
    samples = []
    for _ in range(attempts):
        started = time.perf_counter()
        client.get(path, follow_redirects=False)
        samples.append((time.perf_counter() - started) * 1000.0)
    return round(statistics.mean(samples), 2)


def _add(results, name, passed, details):
    results.append({'name': name, 'passed': bool(passed), 'details': details})


def run_uat(avg_threshold_ms):
    results = []

    with app.app_context():
        seed = _seed_data()
        try:
            with app.test_client() as client:
                response = client.get('/health', follow_redirects=False)
                payload = response.get_json(silent=True) or {}
                _add(
                    results,
                    'Health endpoint responds with snapshot',
                    response.status_code in (200, 503) and isinstance(payload, dict) and 'status' in payload,
                    f"status_code={response.status_code}, keys={list(payload.keys())[:5]}",
                )

                response = client.get('/login', follow_redirects=False)
                _add(
                    results,
                    'Login page is reachable',
                    response.status_code == 200,
                    f'status_code={response.status_code}',
                )

            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = seed['admin_id']
                    sess['role'] = 'admin'

                response = client.get('/admin/users', follow_redirects=False)
                _add(
                    results,
                    'Admin can open user inventory',
                    response.status_code == 200,
                    f'status_code={response.status_code}',
                )

                response = client.get('/admin/security/request-metrics', follow_redirects=False)
                _add(
                    results,
                    'Admin can open request metrics page',
                    response.status_code == 200,
                    f'status_code={response.status_code}',
                )

                response = client.get('/admin/class-assignments', follow_redirects=False)
                has_csrf_field = b'name="csrf_token"' in response.data
                _add(
                    results,
                    'Admin assignment form contains CSRF token field',
                    response.status_code == 200 and has_csrf_field,
                    f'status_code={response.status_code}, csrf_field={has_csrf_field}',
                )

            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = seed['teacher_id']
                    sess['role'] = 'teacher'

                response = client.get('/teacher_dashboard', follow_redirects=False)
                _add(
                    results,
                    'Teacher can open dashboard',
                    response.status_code == 200,
                    f'status_code={response.status_code}',
                )

                response = client.get('/admin/users', follow_redirects=False)
                _add(
                    results,
                    'Teacher is blocked from admin inventory',
                    response.status_code in (302, 403),
                    f'status_code={response.status_code}',
                )

                avg_ms = _measure_avg_ms(client, '/teacher_dashboard')
                _add(
                    results,
                    'Teacher dashboard average latency within threshold',
                    avg_ms <= avg_threshold_ms,
                    f'avg_ms={avg_ms}, threshold_ms={avg_threshold_ms}',
                )

            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = seed['student_id']
                    sess['role'] = 'student'

                response = client.get('/student_dashboard', follow_redirects=False)
                _add(
                    results,
                    'Student can open dashboard',
                    response.status_code == 200,
                    f'status_code={response.status_code}',
                )

                response = client.get('/teacher_dashboard', follow_redirects=False)
                _add(
                    results,
                    'Student is blocked from teacher dashboard',
                    response.status_code in (302, 403),
                    f'status_code={response.status_code}',
                )

        finally:
            _cleanup_data(seed['created_emails'])

    passed_count = sum(1 for item in results if item['passed'])
    total = len(results)
    return {
        'captured_at_utc': dt.datetime.now(dt.UTC).isoformat().replace('+00:00', 'Z'),
        'passed': passed_count,
        'total': total,
        'pass_rate_pct': round((passed_count / total) * 100.0, 2) if total else 0.0,
        'results': results,
    }


def main():
    parser = argparse.ArgumentParser(description='Run Day 31 UAT smoke checklist and emit JSON report.')
    parser.add_argument('--avg-threshold-ms', type=float, default=8.0, help='Max allowed average ms for teacher dashboard smoke check.')
    parser.add_argument('--output-dir', default='project_notes/uat', help='Directory for generated UAT reports.')
    args = parser.parse_args()

    report = run_uat(args.avg_threshold_ms)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = dt.datetime.now(dt.UTC).strftime('%Y-%m-%dT%H-%M-%SZ')
    out_file = out_dir / f'uat_smoke_{stamp}.json'
    out_file.write_text(json.dumps(report, indent=2), encoding='utf-8')

    print(f'UAT smoke report saved: {out_file.as_posix()}')
    print(f"Pass rate: {report['passed']}/{report['total']} ({report['pass_rate_pct']}%)")
    for item in report['results']:
        marker = 'PASS' if item['passed'] else 'FAIL'
        print(f"[{marker}] {item['name']} - {item['details']}")


if __name__ == '__main__':
    main()
