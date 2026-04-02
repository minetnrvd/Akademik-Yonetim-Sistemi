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


def _load_baseline(path):
    if not path:
        return {}
    baseline_path = Path(path)
    if not baseline_path.exists():
        return {}
    data = json.loads(baseline_path.read_text(encoding='utf-8'))
    out = {}
    for row in data.get('results', []):
        out[row.get('path')] = row
    return out


def _ensure_seed_data():
    stamp = dt.datetime.now(dt.UTC).strftime('%Y%m%d%H%M%S')

    admin_email = f'load_admin_{stamp}@example.com'
    teacher_email = f'load_teacher_{stamp}@example.com'

    admin_user = User(name='Load Admin', email=admin_email, role='admin', is_locked=False)
    admin_user.set_password('LoadAdmin1!')

    teacher_user = User(name='Load Teacher', email=teacher_email, role='teacher', is_locked=False)
    teacher_user.set_password('LoadTeacher1!')

    db.session.add(admin_user)
    db.session.add(teacher_user)
    db.session.flush()

    load_class = Class(name=f'LOAD_CLASS_{stamp}', teacher_id=teacher_user.id)
    db.session.add(load_class)
    db.session.commit()

    return {
        'admin_user_id': admin_user.id,
        'teacher_user_id': teacher_user.id,
        'created_emails': [admin_email, teacher_email],
    }


def _cleanup_seed_data(created_emails):
    users = User.query.filter(User.email.in_(created_emails)).all()
    for user in users:
        if user.role == 'teacher':
            Class.query.filter_by(teacher_id=user.id).delete()
    User.query.filter(User.email.in_(created_emails)).delete(synchronize_session=False)
    db.session.commit()


def _exercise(client, path, iterations):
    durations = []
    status_counts = {}
    for _ in range(iterations):
        started = time.perf_counter()
        response = client.get(path, follow_redirects=False)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        durations.append(elapsed_ms)
        key = str(response.status_code)
        status_counts[key] = status_counts.get(key, 0) + 1

    errors = sum(v for k, v in status_counts.items() if int(k) >= 400)
    return {
        'path': path,
        'iterations': iterations,
        'avg_ms': round(statistics.mean(durations), 2),
        'p95_ms': round(_percentile(durations, 0.95), 2),
        'max_ms': round(max(durations), 2),
        'error_rate_pct': round((errors / iterations) * 100.0, 2),
        'status_counts': status_counts,
    }


def _delta(row, baseline_row):
    if not baseline_row:
        return {'avg_ms_delta': None, 'p95_ms_delta': None}
    return {
        'avg_ms_delta': round(row['avg_ms'] - float(baseline_row.get('avg_ms', 0.0)), 2),
        'p95_ms_delta': round(row['p95_ms'] - float(baseline_row.get('p95_ms', 0.0)), 2),
    }


def main():
    parser = argparse.ArgumentParser(description='Run a higher-iteration load profile and compare with baseline.')
    parser.add_argument('--iterations', type=int, default=200, help='Requests per endpoint for load profile.')
    parser.add_argument('--baseline', default='', help='Optional baseline JSON path for delta calculations.')
    parser.add_argument('--output-dir', default='project_notes/performance', help='Directory for output JSON.')
    args = parser.parse_args()

    baseline_map = _load_baseline(args.baseline)
    timestamp = dt.datetime.now(dt.UTC).strftime('%Y-%m-%dT%H-%M-%SZ')

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        seed = _ensure_seed_data()
        try:
            rows = []

            with app.test_client() as client:
                rows.append(_exercise(client, '/health', args.iterations))
                rows.append(_exercise(client, '/login', args.iterations))

            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = seed['admin_user_id']
                    sess['role'] = 'admin'
                rows.append(_exercise(client, '/admin/security/request-metrics', args.iterations))

            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = seed['teacher_user_id']
                    sess['role'] = 'teacher'
                rows.append(_exercise(client, '/teacher_dashboard', args.iterations))

            for row in rows:
                row['delta_vs_baseline'] = _delta(row, baseline_map.get(row['path']))

            report = {
                'captured_at_utc': timestamp,
                'iterations': args.iterations,
                'baseline_used': args.baseline or None,
                'results': rows,
            }
        finally:
            _cleanup_seed_data(seed['created_emails'])

    output_file = output_dir / f'load_profile_{timestamp}.json'
    output_file.write_text(json.dumps(report, indent=2), encoding='utf-8')

    print(f'Load profile report saved: {output_file.as_posix()}')
    for row in report['results']:
        d = row['delta_vs_baseline']
        avg_delta = d['avg_ms_delta']
        p95_delta = d['p95_ms_delta']
        print(
            f"{row['path']}: avg={row['avg_ms']}ms p95={row['p95_ms']}ms max={row['max_ms']}ms "
            f"errors={row['error_rate_pct']}% avg_delta={avg_delta} p95_delta={p95_delta}"
        )


if __name__ == '__main__':
    main()
