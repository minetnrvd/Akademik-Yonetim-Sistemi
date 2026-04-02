# Day 01 - Scope Lock and Risk Baseline

Date: 2026-03-29
Status: Completed
Related plan: MASTER_35_DAY_EXECUTION_PLAN.md

## 1) Scope Lock

### In Scope (this 35-day cycle)
1. Role + permission hardening for student/teacher/admin
2. Persistent audit logging and admin visibility
3. Migration discipline and PostgreSQL transition path
4. Admin operational controls (role management, lock/unlock, assignment)
5. Security hardening (CSRF/session/cookie/rate limit/password policy)
6. Test expansion (unit + negative + integration)
7. Monitoring/performance/load readiness
8. Controlled release + rollback + go-live stabilization

### Out of Scope (for now)
1. Mobile native applications
2. Parent/guardian portal
3. External SIS/LMS integrations
4. Advanced analytics dashboards beyond operational KPIs

## 2) Risk Baseline

### High Risks
1. Authorization bypass in mixed GET/POST handlers
2. Permission drift (endpoint added without permission mapping)
3. Data loss risk during DB transition if rollback is weak
4. Audit logs not persistent across process restarts

### Medium Risks
1. Performance bottlenecks on attendance/history pages
2. Incomplete test coverage for negative role scenarios
3. Operational blind spots without alert thresholds

### Low Risks
1. Minor i18n key misses on new admin pages
2. UI consistency drift on newly added forms

## 3) Success Metrics

### Security Metrics
1. Zero known authorization bypass in tested critical flows
2. 100% teacher/student write endpoints mapped to explicit permissions
3. Denied permission events visible in admin audit report

### Quality Metrics
1. Green checks for app compile and permission tests
2. Negative access tests for student/teacher/admin all passing
3. Documented rollback process validated at least once

### Operations Metrics
1. Backup and restore drill successful
2. Health endpoint and baseline alerts active
3. Load test executed with documented baseline response times

## 4) Day 01 Exit Gate

Day 01 is complete because:
1. Scope boundaries are explicitly defined.
2. Risk list is prioritized.
3. Success metrics are measurable.
4. Master plan is documented in workspace.

## 5) Next Day Input (Day 02)

1. Build PostgreSQL migration checklist.
2. Inventory all current tables, foreign keys, and index candidates.
3. Produce rollback-safe migration strategy document.
