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

from app import app, db, User, Class


def _percentile(values, p):
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    sorted_values = sorted(values)
    idx = (len(sorted_values) - 1) * p
    lower = int(idx)
    upper = min(lower + 1, len(sorted_values) - 1)
    if lower == upper:
        return float(sorted_values[lower])
    weight = idx - lower
    return float(sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight)


def _ensure_seed_data():
    stamp = dt.datetime.now(dt.UTC).strftime('%Y%m%d%H%M%S')

    admin_email = f'perf_admin_{stamp}@example.com'
    teacher_email = f'perf_teacher_{stamp}@example.com'

    admin_user = User(name='Perf Admin', email=admin_email, role='admin', is_locked=False)
    admin_user.set_password('PerfAdmin1!')

    teacher_user = User(name='Perf Teacher', email=teacher_email, role='teacher', is_locked=False)
    teacher_user.set_password('PerfTeacher1!')

    db.session.add(admin_user)
    db.session.add(teacher_user)
    db.session.flush()

    perf_class = Class(name=f'PERF_CLASS_{stamp}', teacher_id=teacher_user.id)
    db.session.add(perf_class)
    db.session.commit()

    return {
        'admin_user_id': admin_user.id,
        'teacher_user_id': teacher_user.id,
        'created_emails': [admin_email, teacher_email],
        'class_id': perf_class.id,
    }


def _cleanup_seed_data(created_emails):
    users = User.query.filter(User.email.in_(created_emails)).all()
    for user in users:
        if user.role == 'teacher':
            Class.query.filter_by(teacher_id=user.id).delete()
    User.query.filter(User.email.in_(created_emails)).delete(synchronize_session=False)
    db.session.commit()


def _hit_endpoint(client, path, warmup, iterations):
    total = warmup + iterations
    durations = []
    status_buckets = {}

    for i in range(total):
        started = time.perf_counter()
        response = client.get(path, follow_redirects=False)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if i >= warmup:
            durations.append(elapsed_ms)
            status_key = str(response.status_code)
            status_buckets[status_key] = status_buckets.get(status_key, 0) + 1

    errors = sum(count for code, count in status_buckets.items() if int(code) >= 400)
    return {
        'path': path,
        'iterations': iterations,
        'avg_ms': round(statistics.mean(durations), 2) if durations else 0.0,
        'p50_ms': round(_percentile(durations, 0.50), 2),
        'p95_ms': round(_percentile(durations, 0.95), 2),
        'max_ms': round(max(durations), 2) if durations else 0.0,
        'error_rate_pct': round((errors / iterations) * 100.0, 2) if iterations else 0.0,
        'status_counts': status_buckets,
    }


def main():
    parser = argparse.ArgumentParser(description='Collect local HTTP baseline metrics using Flask test client.')
    parser.add_argument('--warmup', type=int, default=5, help='Warmup requests per endpoint.')
    parser.add_argument('--iterations', type=int, default=40, help='Measured requests per endpoint.')
    parser.add_argument('--output-dir', default='project_notes/performance', help='Directory for JSON output.')
    args = parser.parse_args()

    timestamp = dt.datetime.now(dt.UTC).strftime('%Y-%m-%dT%H-%M-%SZ')
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        seed = _ensure_seed_data()
        try:
            endpoints = []

            # Public endpoints
            with app.test_client() as client:
                endpoints.append(_hit_endpoint(client, '/health', args.warmup, args.iterations))
                endpoints.append(_hit_endpoint(client, '/login', args.warmup, args.iterations))

            # Admin endpoint (authenticated session)
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = seed['admin_user_id']
                    sess['role'] = 'admin'
                endpoints.append(_hit_endpoint(client, '/admin/security/request-metrics', args.warmup, args.iterations))

            # Teacher endpoint (authenticated session)
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = seed['teacher_user_id']
                    sess['role'] = 'teacher'
                endpoints.append(_hit_endpoint(client, '/teacher_dashboard', args.warmup, args.iterations))

            report = {
                'captured_at_utc': timestamp,
                'warmup': args.warmup,
                'iterations': args.iterations,
                'python_env': 'local-test-client',
                'results': endpoints,
            }
        finally:
            _cleanup_seed_data(seed['created_emails'])

    output_file = output_dir / f'baseline_{timestamp}.json'
    output_file.write_text(json.dumps(report, indent=2), encoding='utf-8')

    print(f'Baseline report saved: {output_file.as_posix()}')
    for row in report['results']:
        print(
            f"{row['path']}: avg={row['avg_ms']}ms p50={row['p50_ms']}ms p95={row['p95_ms']}ms "
            f"max={row['max_ms']}ms errors={row['error_rate_pct']}%"
        )


if __name__ == '__main__':
    main()
