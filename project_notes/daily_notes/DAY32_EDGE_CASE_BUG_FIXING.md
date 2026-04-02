# Day 32 - Edge-Case Bug Fixing Day

## Goal
Resolve a high-probability runtime edge case observed during regression runs and add guard coverage.

## Edge Case Addressed

### Deprecated UTC timestamp callable on Python 3.14+
- During test runs, SQLAlchemy default callables emitted warnings because multiple models used:
  - `datetime.datetime.utcnow`
- This is deprecated in newer Python versions and can become a future compatibility risk.

## Fix Implemented

### 1) Central UTC helper in models
- Added helper in `models.py`:
  - `_utc_now_naive()`
- Behavior:
  - Reads current time from timezone-aware UTC clock (`datetime.datetime.now(datetime.UTC)`)
  - Converts to timezone-naive value (`replace(tzinfo=None)`) to preserve existing DB storage behavior.

### 2) Replaced deprecated defaults across models
Updated datetime defaults to use `_utc_now_naive` in:
- `AttendanceSession.date`
- `CourseEnrollment.created_at`
- `GradeRecord.created_at`
- `Announcement.created_at`
- `Message.sent_at`
- `StudentCalendarEvent.created_at`
- `PermissionAuditLog.created_at`
- `AdminOperationLog.created_at`

### 3) Added regression test
- Added `UtcTimestampHelperTests` in `tests/test_permissions.py`:
  - validates helper returns a `datetime.datetime`
  - validates returned value is timezone-naive (`tzinfo is None`)

## Validation
- Test command:
  - `c:/Uygulama/qr_attandance_project/.venv/Scripts/python.exe -m unittest tests/test_permissions.py`
- Result:
  - `Ran 83 tests in 4.803s`
  - `OK`

## Outcome
- Deprecated timestamp edge case removed from model defaults.
- Regression suite expanded and green.
- Project ready for Day 33 (Release + rollback rehearsal).
