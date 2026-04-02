import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app, db, User, REQUEST_METRICS, _build_health_snapshot


def _reset_metrics():
    REQUEST_METRICS['since_utc'] = dt.datetime.now(dt.UTC).isoformat().replace('+00:00', 'Z')
    REQUEST_METRICS['total_requests'] = 0
    REQUEST_METRICS['error_4xx'] = 0
    REQUEST_METRICS['error_5xx'] = 0
    REQUEST_METRICS['by_endpoint'] = {}


def _seed_bucket(key: str, count: int, avg_ms: float, last_status: int = 200):
    total_ms = float(count) * float(avg_ms)
    REQUEST_METRICS['by_endpoint'][key] = {
        'count': int(count),
        'total_ms': float(total_ms),
        'max_ms': float(avg_ms),
        'min_ms': float(avg_ms),
        'last_status': int(last_status),
        'last_seen_utc': dt.datetime.now(dt.UTC).isoformat().replace('+00:00', 'Z'),
    }


def _add_result(results, name, passed, detail):
    results.append({'name': name, 'passed': bool(passed), 'detail': detail})


def _create_admin_user():
    stamp = dt.datetime.now(dt.UTC).strftime('%Y%m%d%H%M%S')
    email = f'day9_admin_{stamp}@example.com'
    next_user_id = (db.session.query(db.func.max(User.id)).scalar() or 0) + 100
    user = User(id=next_user_id, name='Day9 Admin', email=email, role='admin', is_locked=False)
    user.set_password('Day9Admin1!')
    db.session.add(user)
    db.session.commit()
    return user


def _create_teacher_user():
    stamp = dt.datetime.now(dt.UTC).strftime('%Y%m%d%H%M%S')
    email = f'day9_teacher_{stamp}@example.com'
    next_user_id = (db.session.query(db.func.max(User.id)).scalar() or 0) + 101
    user = User(id=next_user_id, name='Day9 Teacher', email=email, role='teacher', is_locked=False)
    user.set_password('Day9Teacher1!')
    db.session.add(user)
    db.session.commit()
    return user


def _cleanup_users(user_ids):
    if not user_ids:
        return
    User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.session.commit()


def run_validation():
    results = []

    with app.app_context():
        original_warn_error = app.config.get('HEALTH_WARN_ERROR_RATE_PCT', 5)
        original_warn_p95 = app.config.get('HEALTH_WARN_P95_MS', 1000)

        app.config['HEALTH_WARN_ERROR_RATE_PCT'] = 5
        app.config['HEALTH_WARN_P95_MS'] = 1000

        admin_user = _create_admin_user()
        teacher_user = _create_teacher_user()

        try:
            # Scenario 1: Healthy baseline
            _reset_metrics()
            baseline = _build_health_snapshot()
            _add_result(
                results,
                'Baseline health is healthy with empty metrics',
                baseline.get('status') == 'healthy',
                {
                    'status': baseline.get('status'),
                    'reasons': baseline.get('reasons'),
                },
            )

            # Scenario 2: Error-rate alert (degraded)
            _reset_metrics()
            REQUEST_METRICS['total_requests'] = 100
            REQUEST_METRICS['error_5xx'] = 10
            error_alert = _build_health_snapshot()
            _add_result(
                results,
                'Error-rate threshold triggers degraded status',
                error_alert.get('status') == 'degraded' and 'error_rate_threshold_exceeded' in (error_alert.get('reasons') or []),
                {
                    'status': error_alert.get('status'),
                    'error_rate_pct': (error_alert.get('totals') or {}).get('error_rate_pct'),
                    'reasons': error_alert.get('reasons'),
                },
            )

            # Scenario 3: Latency alert (degraded)
            _reset_metrics()
            REQUEST_METRICS['total_requests'] = 50
            _seed_bucket('GET teacher_dashboard', count=25, avg_ms=2200)
            _seed_bucket('GET student_dashboard', count=25, avg_ms=1800)
            latency_alert = _build_health_snapshot()
            _add_result(
                results,
                'Latency threshold triggers degraded status',
                latency_alert.get('status') == 'degraded' and 'latency_threshold_exceeded' in (latency_alert.get('reasons') or []),
                {
                    'status': latency_alert.get('status'),
                    'p95_estimate_ms': (latency_alert.get('latency_ms') or {}).get('p95_estimate'),
                    'reasons': latency_alert.get('reasons'),
                },
            )

            # Scenario 4: Admin dashboard endpoints reachable
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = admin_user.id
                    sess['role'] = 'admin'

                metrics_resp = client.get('/admin/security/request-metrics', follow_redirects=False)
                health_resp = client.get('/admin/security/health-status', follow_redirects=False)
                dash_resp = client.get('/admin/dashboard', follow_redirects=False)

                _add_result(
                    results,
                    'Admin can access monitoring dashboards',
                    metrics_resp.status_code == 200 and health_resp.status_code == 200 and dash_resp.status_code == 200,
                    {
                        'request_metrics_status': metrics_resp.status_code,
                        'health_status_status': health_resp.status_code,
                        'admin_dashboard_status': dash_resp.status_code,
                    },
                )

            # Scenario 5: Non-admin blocked from monitoring dashboards
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = teacher_user.id
                    sess['role'] = 'teacher'

                blocked_resp = client.get('/admin/security/request-metrics', follow_redirects=False)
                _add_result(
                    results,
                    'Non-admin is blocked from request metrics dashboard',
                    blocked_resp.status_code in (302, 403),
                    {'status_code': blocked_resp.status_code},
                )

        finally:
            app.config['HEALTH_WARN_ERROR_RATE_PCT'] = original_warn_error
            app.config['HEALTH_WARN_P95_MS'] = original_warn_p95
            _reset_metrics()
            _cleanup_users([admin_user.id, teacher_user.id])

    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    status = 'approved' if passed == total else 'attention_required'

    return {
        'captured_at_utc': dt.datetime.now(dt.UTC).isoformat().replace('+00:00', 'Z'),
        'status': status,
        'passed': passed,
        'total': total,
        'results': results,
    }


def main():
    parser = argparse.ArgumentParser(description='Day 9 alerting and dashboard validation checks')
    parser.add_argument('--output-dir', default='project_notes/closeout')
    args = parser.parse_args()

    report = run_validation()

    out_dir = ROOT_DIR / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = dt.datetime.now(dt.UTC).strftime('%Y-%m-%dT%H-%M-%SZ')
    out_path = out_dir / f'day9_alerting_validation_{stamp}.json'
    out_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

    print(f'DAY9_ALERTING_REPORT {out_path.as_posix()}')
    print(f'DAY9_ALERTING_STATUS {report["status"]}')
    print(f'DAY9_ALERTING_PASS_RATE {report["passed"]}/{report["total"]}')
    for row in report['results']:
        marker = 'PASS' if row['passed'] else 'FAIL'
        print(f'[{marker}] {row["name"]}')

    if report['status'] != 'approved':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
