# Day 31 UAT Checklist and Stakeholder Signoff

## Scope
This checklist validates core user journeys and security boundaries before release rehearsal.

## Automated Smoke (Script)
- Command:
  - `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe scripts/uat_checklist.py --avg-threshold-ms 8.0`
- Output:
  - `project_notes/uat/uat_smoke_<UTC_TIMESTAMP>.json`

## Manual Stakeholder UAT Steps

### Student Representative
- Login as student and open dashboard.
- Confirm class attendance history is visible.
- Confirm student cannot access teacher dashboard URL.

### Teacher Representative
- Login as teacher and open dashboard.
- Confirm active session cards and class history render.
- Confirm teacher cannot access admin inventory URL.

### Admin Representative
- Login as admin and open user inventory.
- Open class assignment page and submit assignment update.
- Open request metrics and health status pages.

## Security and Reliability Gate
- Health endpoint returns valid JSON snapshot.
- CSRF token field exists on admin mutating forms.
- No unauthorized cross-role page access.
- Teacher dashboard average latency remains below agreed local UAT threshold.

## Signoff Table
| Role | Owner | Date | Status (Pass/Fail) | Notes |
|------|-------|------|--------------------|-------|
| Student Rep |  |  |  |  |
| Teacher Rep |  |  |  |  |
| Admin Rep |  |  |  |  |
| Tech Lead |  |  |  |  |

## Exit Criteria
UAT is considered complete when:
1. Automated smoke checklist pass rate is 100%.
2. Manual stakeholder checks are marked pass.
3. Any discovered defects are either fixed or explicitly deferred with risk acceptance.
