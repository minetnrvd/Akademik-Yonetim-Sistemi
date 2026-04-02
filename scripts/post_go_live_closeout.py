import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app, REQUEST_METRICS


def _load_json_safe(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception:
        return None


def _latest_json(pattern: str, base_dir: Path):
    files = sorted(base_dir.glob(pattern))
    if not files:
        return None, None
    latest = files[-1]
    return latest, _load_json_safe(latest)


def _health_snapshot():
    with app.test_client() as client:
        response = client.get('/health', follow_redirects=False)
        payload = response.get_json(silent=True) or {}
    return {
        'status_code': response.status_code,
        'payload': payload,
    }


def _metrics_snapshot():
    by_endpoint = REQUEST_METRICS.get('by_endpoint') or {}
    endpoint_rows = []
    for key, value in by_endpoint.items():
        count = int(value.get('count', 0) or 0)
        total_ms = float(value.get('total_ms', 0.0) or 0.0)
        avg_ms = (total_ms / count) if count > 0 else 0.0
        endpoint_rows.append(
            {
                'endpoint': key,
                'count': count,
                'avg_ms': round(avg_ms, 2),
                # Per-request latency history is not retained in REQUEST_METRICS buckets,
                # so p95 cannot be computed here without external telemetry storage.
                'p95_ms': None,
                'max_ms': float(value.get('max_ms', 0.0) or 0.0),
            }
        )
    endpoint_rows.sort(key=lambda r: r['count'], reverse=True)

    return {
        'since_utc': REQUEST_METRICS.get('since_utc'),
        'total_requests': REQUEST_METRICS.get('total_requests', 0),
        'error_4xx': REQUEST_METRICS.get('error_4xx', 0),
        'error_5xx': REQUEST_METRICS.get('error_5xx', 0),
        'top_endpoints': endpoint_rows[:10],
    }


def _step(name, passed, detail):
    return {
        'name': name,
        'passed': bool(passed),
        'detail': detail,
    }


def main():
    parser = argparse.ArgumentParser(description='Build Day 35 post-go-live monitoring closeout report.')
    parser.add_argument('--output-dir', default='project_notes/closeout', help='Output directory for closeout report')
    args = parser.parse_args()

    out_dir = ROOT_DIR / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    release_dir = ROOT_DIR / 'project_notes' / 'release'
    rollout_dir = ROOT_DIR / 'project_notes' / 'rollout'
    uat_dir = ROOT_DIR / 'project_notes' / 'uat'
    perf_dir = ROOT_DIR / 'project_notes' / 'performance'

    rehearsal_path, rehearsal_data = _latest_json('release_rollback_rehearsal_*.json', release_dir)
    rollout_path, rollout_data = _latest_json('controlled_rollout_*.json', rollout_dir)
    uat_path, uat_data = _latest_json('uat_smoke_*.json', uat_dir)
    baseline_path, baseline_data = _latest_json('baseline_*.json', perf_dir)
    load_path, load_data = _latest_json('load_profile_*.json', perf_dir)

    health = _health_snapshot()
    metrics = _metrics_snapshot()

    steps = []
    steps.append(
        _step(
            'Day 33 rehearsal report is approved',
            bool(rehearsal_data and rehearsal_data.get('status') == 'ok'),
            {'path': str(rehearsal_path) if rehearsal_path else None, 'status': rehearsal_data.get('status') if rehearsal_data else None},
        )
    )
    steps.append(
        _step(
            'Day 34 controlled rollout report is approved',
            bool(rollout_data and rollout_data.get('status') == 'approved'),
            {'path': str(rollout_path) if rollout_path else None, 'status': rollout_data.get('status') if rollout_data else None},
        )
    )

    uat_pass = False
    uat_detail = {'path': str(uat_path) if uat_path else None, 'passed': None, 'total': None}
    if uat_data:
        result_rows = uat_data.get('results') or []
        passed_count = sum(1 for row in result_rows if row.get('passed'))
        total = len(result_rows)
        uat_pass = total > 0 and passed_count == total
        uat_detail.update({'passed': passed_count, 'total': total})
    steps.append(_step('Latest UAT smoke pass rate is 100%', uat_pass, uat_detail))

    health_payload = health.get('payload') or {}
    health_pass = health.get('status_code') in (200, 503) and isinstance(health_payload, dict) and bool(health_payload.get('status'))
    steps.append(
        _step(
            'Health endpoint returns valid status payload',
            health_pass,
            {
                'status_code': health.get('status_code'),
                'status': health_payload.get('status'),
                'database_ok': health_payload.get('database_ok'),
            },
        )
    )

    perf_pass = bool(baseline_data and load_data)
    steps.append(
        _step(
            'Performance baseline and load profile artifacts exist',
            perf_pass,
            {
                'baseline_path': str(baseline_path) if baseline_path else None,
                'load_profile_path': str(load_path) if load_path else None,
            },
        )
    )

    all_passed = all(step['passed'] for step in steps)
    report = {
        'captured_at_utc': dt.datetime.now(dt.UTC).isoformat().replace('+00:00', 'Z'),
        'status': 'closed' if all_passed else 'attention_required',
        'steps': steps,
        'health_snapshot': {
            'status_code': health.get('status_code'),
            'status': health_payload.get('status'),
            'reasons': health_payload.get('reasons'),
            'totals': health_payload.get('totals'),
            'latency_ms': health_payload.get('latency_ms'),
        },
        'metrics_snapshot': metrics,
        'artifact_index': {
            'rehearsal_report': str(rehearsal_path) if rehearsal_path else None,
            'rollout_report': str(rollout_path) if rollout_path else None,
            'uat_report': str(uat_path) if uat_path else None,
            'baseline_report': str(baseline_path) if baseline_path else None,
            'load_profile_report': str(load_path) if load_path else None,
        },
        'next_action': (
            'Close Day 35 and archive artifacts.' if all_passed else 'Investigate failing checks and rerun closeout script.'
        ),
    }

    stamp = dt.datetime.now(dt.UTC).strftime('%Y-%m-%dT%H-%M-%SZ')
    out_path = out_dir / f'post_go_live_closeout_{stamp}.json'
    out_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

    print(f'POST_GO_LIVE_CLOSEOUT_REPORT {out_path.as_posix()}')
    print(f'POST_GO_LIVE_CLOSEOUT_STATUS {report["status"]}')
    for s in steps:
        marker = 'PASS' if s['passed'] else 'FAIL'
        print(f"[{marker}] {s['name']}")

    if report['status'] != 'closed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
