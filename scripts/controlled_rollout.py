import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app


def _run_command(command, cwd):
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        shell=False,
    )
    output = (completed.stdout or '') + (completed.stderr or '')
    return completed.returncode, output.strip()


def _find_latest_rehearsal_report(release_dir: Path):
    candidates = sorted(release_dir.glob('release_rollback_rehearsal_*.json'))
    if not candidates:
        return None, None
    latest = candidates[-1]
    try:
        raw = latest.read_text(encoding='utf-8-sig')
        data = json.loads(raw)
    except Exception:
        return latest, None
    return latest, data


def _health_gate_check():
    with app.test_client() as client:
        response = client.get('/health', follow_redirects=False)
        payload = response.get_json(silent=True) or {}

    latency_block = payload.get('latency_ms') if isinstance(payload.get('latency_ms'), dict) else {}
    p95_value = latency_block.get('p95')
    if p95_value is None:
        p95_value = latency_block.get('p95_estimate')

    passed = response.status_code in (200, 503) and isinstance(payload, dict) and 'status' in payload
    detail = {
        'status_code': response.status_code,
        'status': payload.get('status'),
        'database_ok': payload.get('database_ok'),
        'error_rate_pct': (payload.get('totals') or {}).get('error_rate_pct') if isinstance(payload.get('totals'), dict) else None,
        'p95_ms': p95_value,
    }
    return passed, detail


def _parse_backup_dir(output: str):
    match = re.search(r'BACKUP_OK\s+(.+)', output)
    return match.group(1).strip() if match else None


def _parse_uat_pass_rate(output: str):
    match = re.search(r'Pass rate:\s*(\d+)/(\d+)', output)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def _add_step(steps, name, passed, detail):
    steps.append({
        'name': name,
        'passed': bool(passed),
        'detail': detail,
    })


def main():
    parser = argparse.ArgumentParser(description='Day 34 controlled rollout gate runner.')
    parser.add_argument('--phase', choices=['canary', 'pilot', 'full'], default='canary')
    parser.add_argument('--include-qr-assets', action='store_true')
    parser.add_argument('--uat-avg-threshold-ms', type=float, default=8.0)
    parser.add_argument('--output-dir', default='project_notes/rollout')
    args = parser.parse_args()

    python_exe = ROOT_DIR / '.venv' / 'Scripts' / 'python.exe'
    backup_script = ROOT_DIR / 'scripts' / 'backup_restore_drill.ps1'
    uat_script = ROOT_DIR / 'scripts' / 'uat_checklist.py'
    test_module = 'tests/test_permissions.py'

    output_dir = ROOT_DIR / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {
        'captured_at_utc': dt.datetime.now(dt.UTC).isoformat().replace('+00:00', 'Z'),
        'phase': args.phase,
        'status': 'running',
        'steps': [],
    }

    try:
        release_dir = ROOT_DIR / 'project_notes' / 'release'
        rehearsal_path, rehearsal_data = _find_latest_rehearsal_report(release_dir)
        rehearsal_ok = bool(rehearsal_data and rehearsal_data.get('status') == 'ok')
        _add_step(
            report['steps'],
            'Latest release+rollback rehearsal is successful',
            rehearsal_ok,
            {
                'report_path': str(rehearsal_path) if rehearsal_path else None,
                'report_status': rehearsal_data.get('status') if rehearsal_data else None,
            },
        )

        backup_cmd = [
            'powershell',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            str(backup_script),
            '-Mode',
            'backup',
            '-ProjectRoot',
            str(ROOT_DIR),
        ]
        if args.include_qr_assets:
            backup_cmd.append('-IncludeQrAssets')

        backup_code, backup_output = _run_command(backup_cmd, ROOT_DIR)
        backup_dir = _parse_backup_dir(backup_output)
        backup_ok = backup_code == 0 and bool(backup_dir)
        _add_step(
            report['steps'],
            'Backup snapshot before rollout',
            backup_ok,
            {
                'exit_code': backup_code,
                'backup_dir': backup_dir,
                'output_tail': backup_output[-500:],
            },
        )

        test_cmd = [str(python_exe), '-m', 'unittest', test_module]
        test_code, test_output = _run_command(test_cmd, ROOT_DIR)
        tests_ok = test_code == 0
        _add_step(
            report['steps'],
            'Regression suite is green',
            tests_ok,
            {
                'exit_code': test_code,
                'output_tail': test_output[-1200:],
            },
        )

        uat_cmd = [
            str(python_exe),
            str(uat_script),
            '--avg-threshold-ms',
            str(args.uat_avg_threshold_ms),
        ]
        uat_code, uat_output = _run_command(uat_cmd, ROOT_DIR)
        passed_count, total_count = _parse_uat_pass_rate(uat_output)
        uat_ok = uat_code == 0 and passed_count is not None and total_count is not None and passed_count == total_count
        _add_step(
            report['steps'],
            'UAT smoke is fully passing',
            uat_ok,
            {
                'exit_code': uat_code,
                'passed': passed_count,
                'total': total_count,
                'output_tail': uat_output[-1200:],
            },
        )

        health_ok, health_detail = _health_gate_check()
        _add_step(report['steps'], 'Health gate returns valid snapshot', health_ok, health_detail)

        all_passed = all(step['passed'] for step in report['steps'])
        report['status'] = 'approved' if all_passed else 'blocked'
        report['recommended_next_action'] = (
            f"Proceed with {args.phase} rollout window and monitor health/metrics dashboards."
            if all_passed
            else 'Do not promote rollout. Resolve failing gates and rerun controlled rollout script.'
        )
    except Exception as exc:
        report['status'] = 'blocked'
        report['error'] = str(exc)

    report['finished_at_utc'] = dt.datetime.now(dt.UTC).isoformat().replace('+00:00', 'Z')

    stamp = dt.datetime.now(dt.UTC).strftime('%Y-%m-%dT%H-%M-%SZ')
    out_path = output_dir / f'controlled_rollout_{stamp}.json'
    out_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

    print(f'CONTROLLED_ROLLOUT_REPORT {out_path.as_posix()}')
    print(f'CONTROLLED_ROLLOUT_STATUS {report["status"]}')
    for step in report['steps']:
        marker = 'PASS' if step['passed'] else 'FAIL'
        print(f"[{marker}] {step['name']}")

    if report['status'] != 'approved':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
