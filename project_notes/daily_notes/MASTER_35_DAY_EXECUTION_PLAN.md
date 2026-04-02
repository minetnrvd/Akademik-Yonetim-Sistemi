# Master 35-Day Execution Plan

Date created: 2026-03-29
Owner: Project team (Student + Teacher + Admin portal)

## Goal

Deliver a production-ready university portal built on the existing QR attendance system with:
- secure role and permission model,
- admin operational tooling,
- migration and backup discipline,
- monitoring and performance readiness,
- controlled go-live and rollback capability.

## Weekly Structure

### Week 1 - Data and Security Foundation
- Day 1: Scope lock, risk list, success metrics
- Day 2: PostgreSQL migration design and index inventory
- Day 3: Versioned migration baseline and rollback rehearsal
- Day 4: Persistent audit log model/table
- Day 5: Admin audit list and filters

### Week 2 - Authorization Hardening
- Day 6: Teacher ownership checks centralization
- Day 7: Student ownership checks centralization
- Day 8: Read/update permission split finalization
- Day 9: Unauthorized flow and log standardization
- Day 10: Security regression sweep and closure

### Week 3 - Admin Operations
- Day 11: Admin user inventory view
- Day 12: Role update flow
- Day 13: Account lock/unlock flow
- Day 14: Teacher-class assignment flow
- Day 15: Admin operation audit coverage

### Week 4 - Test Expansion
- Day 16: Permission helper unit tests expansion
- Day 17: Teacher negative access tests
- Day 18: Student negative access tests
- Day 19: Admin integration tests
- Day 20: Test gap closure

### Week 5 - Production Hardening
- Day 21: Session/cookie hardening review
- Day 22: CSRF and form security sweep
- Day 23: Rate limiting on sensitive routes
- Day 24: Password policy and brute-force protection
- Day 25: Backup and restore drill

### Week 6 - Monitoring and Performance
- Day 26: Error and latency metric instrumentation
- Day 27: Health checks and alert thresholds
- Day 28: Query/index optimization pass
- Day 29: Load test baseline
- Day 30: Performance fix pass and report

### Week 7 - Go-Live and Stabilization
- Day 31: UAT checklist with stakeholders
- Day 32: Edge-case bug fixing day
- Day 33: Release + rollback rehearsal
- Day 34: Controlled production rollout
- Day 35: Post-go-live monitoring and closeout

## Tracking Rule

A day can be marked complete only if:
1. Planned deliverable is produced.
2. Validation checks are green.
3. A short daily summary file is committed to workspace.
