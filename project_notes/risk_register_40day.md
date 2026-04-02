# 40-Day Production Plan: Risk Register

**Date**: March 30, 2026  
**Program Phase**: Production Operationalization (Days 1-40)  
**Owner**: Technical Lead

---

## Risk Assessment Framework

Each risk scored by: **Likelihood (1-5) × Impact (1-5) = Risk Score (1-25)**

- **Critical**: Score ≥ 16 (immediate mitigation required)
- **High**: Score 12-15 (mitigation plan in place before next gate)
- **Medium**: Score 6-11 (monitoring, contingency identified)
- **Low**: Score ≤ 5 (document, track)

---

## Identified Risks (Ranked by Score)

### 🔴 CRITICAL RISKS

#### Risk #1: Data Loss During SQLite → PostgreSQL Migration
**Score**: 5 × 5 = **25** | **Severity**: CRITICAL  
**Phase**: Days 11-20 (Database Migration)

**Description**:
SQLite → PostgreSQL migration with 35 days+ of production data (users, classes, attendance) introduces risk of data corruption, incomplete transfer, or silent failures.

**Likelihood** (5/5): 
- Schema mismatch (data types, constraints, defaults)
- Transaction rollback leaves inconsistent state
- Encoding issues (special chars in Turkish school names)

**Impact** (5/5):
- Complete data loss → system unusable
- Partial data loss → attendance records corrupted
- Regulatory/compliance violation (attendance integrity required for university)

**Mitigation Plan**:
1. **Pre-Migration (Days 12-13)**: Create comprehensive schema diff tool
   - Export SQLite schema, auto-generate PostgreSQL DDL
   - Validate column-by-column mapping (type coercion rules)
   - Test on empty database (zero-data migration)
   
2. **Rehearsal Cycle (Days 14-16)**:
   - Run migration on BACKUP of production data (not live)
   - Verify row counts: `SELECT COUNT(*) FROM User` must match pre/post
   - Checksum validation: `SHA256(CAST(* AS TEXT))` on key tables
   - Rollback test: restore from backup, verify PostgreSQL state cleared
   
3. **Go-Live (Day 17)**:
   - Atomic transaction: BEGIN → migrate → validate checksums → COMMIT
   - If validation fails: automatic ROLLBACK to SQLite
   - Post-migration verification: 15-minute silent period, monitor logs for errors
   
4. **Contingency (Days 18-20)**:
   - Maintain SQLite backup for 72 hours post-migration
   - Keep manual restore procedure documented
   - Automated daily validation checks (cross-DB count match)

**Acceptance Criteria**:
- [ ] Migration runs on sample data with 100% checksum match
- [ ] Rollback verified (PostgreSQL cleared, SQLite restored identical)
- [ ] Zero data loss validated across 3 rehearsal cycles
- [ ] Production data migration completes in < 30 minutes
- [ ] Post-migration validation runs automatically, alerts on mismatch

**Owner**: Database admin  
**Review Date**: Day 15 (mid-rehearsal checkpoint)

---

#### Risk #2: Infrastructure Provisioning Delay / Unavailability
**Score**: 4 × 5 = **20** | **Severity**: CRITICAL  
**Phase**: Days 1-10 (Infrastructure Hardening)

**Description**:
Production server may not be available within Days 1-10, delaying all downstream phases (DB migration, CI/CD setup depend on target infrastructure).

**Likelihood** (4/5):
- Server procurement lead time (if cloud: approval delay)
- Network setup (firewall rules, DNS propagation)
- TLS certificate issuance (validation delays)

**Impact** (5/5):
- All Days 11-30 phases blocked (cascading delays)
- Timeline unrecoverable (40-day constraint)
- Production launch postponed indefinitely

**Mitigation Plan**:
1. **Day 1**: Confirm server availability status immediately
   - Contact infrastructure team (same-day confirmation)
   - If not available: activate contingency (parallel staging environment)
   
2. **Pre-Infrastructure Setup (Days 2-5)**:
   - Prepare infrastructure configuration code (Terraform/Ansible)
   - Deploy to staging/test environment (parallel to procurement)
   - Validate WSGI, reverse proxy, TLS on staging
   
3. **Contingency Path (if needed)**:
   - Use staging environment as temporary production (not ideal)
   - Re-baseline performance metrics (staging != production hardware)
   - Plan infrastructure swap for Days 21-30 (zero-downtime)

4. **Rollforward**:
   - If production available Days 11-15 (instead of Day 1), shift Days 1-10 activities to Days 11-15
   - Compress scope to critical-path tasks only

**Acceptance Criteria**:
- [ ] Production server confirmed available, hardware specs verified (by Day 2)
- [ ] Network connectivity test passed (app ↔ db ↔ monitoring)
- [ ] TLS certificate obtained (or self-signed for staging, production cert by Day 9)
- [ ] If contingency: staging deployment documented, performance delta accepted

**Owner**: Infrastructure lead  
**Review Date**: Day 2 morning

---

#### Risk #3: CI/CD Pipeline Complexity Exceeds Scope
**Score**: 4 × 4 = **16** | **Severity**: CRITICAL  
**Phase**: Days 21-30 (Automation & Observability)

**Description**:
Designing and implementing full CI/CD pipeline (test, lint, build, staging deploy, production gates) is complex; Days 21-30 may be insufficient if gates become over-engineered.

**Likelihood** (4/5):
- Requirements expansion (approval workflows, multiple reviewers)
- Tool integration complexity (git → build → deploy → monitor)
- Unforeseen pipeline failures during rehearsal

**Impact** (4/5):
- Pipeline not production-ready by Day 30 → manual deploys post-go-live (risk)
- Security gates weak → vulnerability slips to production
- Deployment frequency reduced (bottleneck)

**Mitigation Plan**:
1. **MVP Definition (Day 21)**:
   - Minimal gates: test-pass + UAT-pass + health-check
   - Deploy target: single production environment (no canary yet)
   - Operator approval: single sign-off (no committee)
   
2. **Phase 1 (Days 22-25)**:
   - Implement core gates (test, health)
   - Integration with Git webhook (commit → auto-trigger)
   - Staging deployment working end-to-end
   
3. **Phase 2 (Days 26-29)**:
   - Add monitoring metrics export
   - Add alerting integration
   - Production gate test (canary flow dry-run)
   
4. **Phase 3 (Days 29-30)**:
   - Post-go-live improvements (not in 40-day scope)

**Acceptance Criteria**:
- [ ] Minimal pipeline (test + health) deployed and tested
- [ ] Staging deployment automated (no manual steps in critical path)
- [ ] Production gates defined (even if monitoring integration deferred post-go-live)
- [ ] 2+ successful full-flow rehearsals (commit → production) completed

**Owner**: DevOps lead  
**Review Date**: Day 25 (checkpoint before monitoring integration)

---

### 🟠 HIGH RISKS

#### Risk #4: TLS Certificate / HTTPS Setup Blocked
**Score**: 3 × 5 = **15** | **Severity**: HIGH  
**Phase**: Days 1-10 (Infrastructure Hardening)

**Description**:
HTTPS required for production. Certificate issuance (Let's Encrypt ~24h, commercial ~3-5d) or DNS/domain configuration could delay Days 1-10 infrastructure closure.

**Likelihood** (3/5):
- Domain ownership verification delays
- DNS propagation (48-72h in worst case)
- Certificate authority hiccups

**Impact** (5/5):
- Cannot deploy to production (browser warnings, API SSL failures)
- Attendance system unusable on HTTPS-enforcing campuses

**Mitigation Plan**:
1. **Day 1**: Initiate certificate request (same-day)
   - If Let's Encrypt: start automation (certbot)
   - If commercial: submit with domain admin approval
   
2. **Parallel Path (Days 2-5)**:
   - Deploy staging with self-signed cert (for testing)
   - Validate Nginx/reverse-proxy TLS config on staging
   - Production cert integration ready (testable, just swap cert file)
   
3. **Fallback**: If cert delays beyond Day 10
   - Deploy on IP:port (not recommended but functional)
   - Plan cert swap for Days 11-15 (zero-downtime reload)

**Acceptance Criteria**:
- [ ] Certificate available (production-valid) by Day 8
- [ ] HTTPS working end-to-end (browser, API client, health check)
- [ ] Cert auto-renewal automation tested (ctab entry for Let's Encrypt)

**Owner**: Infrastructure lead  
**Review Date**: Day 3

---

#### Risk #5: Performance Regression Post-Database Migration
**Score**: 3 × 4 = **12** | **Severity**: HIGH  
**Phase**: Days 11-20 (Database Migration)

**Description**:
PostgreSQL may have different query performance characteristics than SQLite (different optimizer, index behavior). Queries fast on SQLite may slow on PostgreSQL under load.

**Likelihood** (3/5):
- Missing indexes on PostgreSQL (SQLite implicit indexes not auto-copied)
- Normalization changes (joins now required instead of denormalized tables)
- Connection pool saturation (PostgreSQL pooling different from SQLite WAL)

**Impact** (4/5):
- Latency spike post-go-live (SLO violation)
- Teacher dashboard unusable during peak attendance marking
- User experience regression

**Mitigation Plan**:
1. **Pre-Migration (Days 12-13)**:
   - Query analysis: extract slow-query log from SQLite
   - Identify N+1 query patterns (ORM generates inefficient JOIN)
   - Auto-create indexes on foreign keys (SQLAlchemy relationship columns)
   
2. **Rehearsal (Days 14-16)**:
   - Run loadtest on PostgreSQL (same query patterns, 100 concurrent clients)
   - Record p95 latency, error rate, connection pool usage
   - Compare vs SQLite baseline (Day 35 performance report)
   - If regression > 20%: add indexes, re-baseline
   
3. **Go-Live (Day 17)**:
   - Deploy with index set from rehearsal
   - Monitor latency metrics in real-time
   - If p95 latency > 8ms: alert → rollback to SQLite
   
4. **Post-Migration (Days 18-20)**:
   - Continue monitoring, gather post-cutover metrics
   - Add missing indexes if identified in production logs
   - Update performance baseline for Phase 2 optimization work

**Acceptance Criteria**:
- [ ] PostgreSQL latency ≤ 10% regression vs SQLite baseline
- [ ] Connection pool utilization < 80% during load test
- [ ] All indexes created and query plans verified
- [ ] Post-go-live monitoring stable for 24 hours within SLO

**Owner**: Database admin / Performance engineer  
**Review Date**: Day 16 (post-loadtest)

---

#### Risk #6: Monitoring Integration Incomplete or Misconfigured
**Score**: 3 × 4 = **12** | **Severity**: HIGH  
**Phase**: Days 21-30 (Automation & Observability)

**Description**:
Integrating with external monitoring system (Prometheus, Datadog, CloudWatch) complex; configuration errors could result in metrics not being collected or alerts never firing.

**Likelihood** (3/5):
- Firewall/network configuration (monitoring → app port blocked)
- Credential setup (API keys, service accounts)
- Metric naming conflicts (existing vs new cluster)

**Impact** (4/5):
- Blind production environment (no latency/error visibility)
- Cannot detect SLO violations (unaware of issues until user complaints)
- Debugging production issues without logs impossible

**Mitigation Plan**:
1. **Planning (Days 21-22)**:
   - Confirm monitoring target system (Prometheus/Datadog/CloudWatch)
   - Get API credentials, network access, port allowlists
   - Design metric schema (namespace, labels, cardinality limits)
   
2. **Implementation (Days 23-27)**:
   - Deploy monitoring agent/exporter on app server
   - Instrument 5 key metrics (latency, errors, uptime, db-conn, disk)
   - Test telemetry collection end-to-end (manual curl to exporter)
   - Create 3-5 test alerts (latency spike, error rate, disk warning)
   
3. **Validation (Days 28-30)**:
   - Synthetic load: trigger alert conditions, verify notification fires
   - Dashboard creation: latency histogram, error breakdown, health status
   - Runbook linking: alert→owner→escalation→runbook automated
   
4. **Contingency**:
   - If external monitoring unavailable: local Prometheus on app server (degraded)
   - Metrics still collected and queryable, alerting manual (not ideal)

**Acceptance Criteria**:
- [ ] At least 5 metrics actively exported and queryable
- [ ] 2+ alerts tested and firing correctly
- [ ] Dashboard shows SLO metrics (latency p95, error rate, uptime)
- [ ] Runbook links verified (alert click → remediation steps)

**Owner**: Observability engineer  
**Review Date**: Day 28

---

### 🟡 MEDIUM RISKS

#### Risk #7: Canary Rollout Plan Not Tested Before Production
**Score**: 2 × 4 = **8** | **Severity**: MEDIUM  
**Phase**: Days 31-37 (Security & Operations Hardening)

**Description**:
Canary rollout (gradual traffic shift 5% → 25% → 50% → 100%) requires load-balancer / traffic-router configuration. If untested, rollout could fail and cascade to full outage.

**Likelihood** (2/5):
- Rollout decision scripting complex (go/no-go logic)
- Traffic shifting misconfigured (users see errors during transition)

**Impact** (4/5):
- Production outage during go-live (impact all users)
- Confidence undermined (fallback to big-bang approach)

**Mitigation Plan**:
1. **Planning (Days 31-33)**:
   - Document canary decision criteria (error rate, latency thresholds)
   - Design traffic-shift implementation (DNS, load-balancer, or feature flag)
   - Define rollback trigger (if p95 > 10s or error rate > 5% → instant rollback)
   
2. **Staging Rehearsal (Days 34-36)**:
   - Simulate canary on staging servers (two instances, traffic shift)
   - Slow-roll traffic: 5% for 5min → measure → 25% for 5min → measure
   - Trigger rollback scenario (inject high latency, observe automatic rollback)
   - Document exact kubectl/nginx/script commands for production
   
3. **Production (Days 38-40)**:
   - Execute exact commands from rehearsal
   - Monitor metrics every 5 minutes, rollback if threshold breached
   - Document decisions and outcomes for post-go-live review

**Acceptance Criteria**:
- [ ] Canary plan documented (script, decision criteria, rollback triggers)
- [ ] Staging rehearsal passed (traffic shifted 5→25→50→100%, then rolled back)
- [ ] Production commands prepared and tested in dry-run (no actual cutover)
- [ ] Team trained on manual intervention (if automation fails)

**Owner**: DevOps / Deployment lead  
**Review Date**: Day 36

---

#### Risk #8: Backup/Restore Procedure Fails Under Pressure
**Score**: 2 × 4 = **8** | **Severity**: MEDIUM  
**Phase**: Days 6-10 & 31-37 (Infrastructure & Operations)

**Description**:
Backup/restore tested in lab but never under production load/time pressure. Real restore could fail due to:
- Incomplete backup (interrupted, corrupted)
- Restore hangs (large database, I/O limits)
- Version mismatch (PostgreSQL 14 backup, PostgreSQL 12 restore)

**Likelihood** (2/5):
- Manual backup script errors under load
- Network interruption during backup
- Operator error during restore (wrong server, wrong version)

**Impact** (4/5):
- Cannot recover from data corruption or ransomware
- RTO (Recovery Time Objective) exceeded, business impact
- Regulatory non-compliance (audit failure)

**Mitigation Plan**:
1. **Days 6-10**: Test backup/restore cycle 3× (at least once with large dataset)
   - Backup from production → verify checksum
   - Restore to staging → verify identical (row count, hash)
   - Measure backup time, restore time, disk space required
   - Document retention policy (7d daily, 4w weekly, 12m monthly)
   
2. **Days 31-37**: Run operational incident tatbikatı
   - Scenario 1: Database corruption detected → restore backup → verify
   - Scenario 2: Ransomware deletes files → activate immutable backup
   - Scenario 3: Wrong deployment → rollback from backup point-in-time
   - Time each exercise, document actual recovery time
   
3. **Post-Go-Live**:
   - Daily automated backup verification (restore to staging, checksum)
   - Weekly operational drill (random team member performs restore)
   - Alert on backup failures (success rate monitored)

**Acceptance Criteria**:
- [ ] Backup/restore tested 3+ times with production-sized dataset
- [ ] RTO measured and < 1 hour (for full database recovery)
- [ ] Restore time predictable (±10% variance)
- [ ] Retention policy documented and automated

**Owner**: Database admin / Infrastructure lead  
**Review Date**: Day 10 (post Pillar 1), Day 37 (post tatbikatı)

---

#### Risk #9: Secret Scanning Finds Hardcoded Credentials in Git History
**Score**: 2 × 4 = **8** | **Severity**: MEDIUM  
**Phase**: Days 31-37 (Security & Operations)

**Description**:
Secret scan (git-secrets, TruffleHog) may find hardcoded database passwords, API keys in old commits. Remediation (rewrite git history) could introduce regressions.

**Likelihood** (2/5):
- Developer accidentally committed .env file or credentials in code
- Old commits contain passwords (legacy code not yet deleted)

**Impact** (4/5):
- Credentials leaked → attacker access to production database
- Secret rotation required immediately (expensive, risky)
- Regulatory violation (PCI-DSS, data protection)

**Mitigation Plan**:
1. **Pre-Scan (Days 31-32)**:
   - Run git-secrets locally (identify known secrets before full scan)
   - Review flagged commits manually (false positives, legitimate hardcoding)
   - Rotate any real secrets immediately (DB password, API keys)
   
2. **Git History Cleanup (if needed, Days 32-33)**:
   - Use git-filter-branch or BFG to remove secrets from history
   - Force-push cleaned history to origin (requires team coordination)
   - Verify all team members re-clone repository
   
3. **Prevention (Days 34-37)**:
   - Install pre-commit hook (blocks secret commits going forward)
   - Document secret management policy: all secrets in environment variables
   - Add ci-pipeline secret-check gate (catches new secrets in PRs)

**Acceptance Criteria**:
- [ ] Full git history scanned (0 critical secrets found)
- [ ] Any found secrets rotated and invalidated
- [ ] Pre-commit hook installed and tested
- [ ] CI/CD pipeline includes secret-check gate

**Owner**: Security engineer / DevOps  
**Review Date**: Day 33

---

### 🟢 LOW RISKS

#### Risk #10: Team Availability / Knowledge Gaps
**Score**: 2 × 3 = **6** | **Severity**: LOW  
**Phase**: Days 1-40 (All phases)

**Description**:
Key team members unavailable (sick, vacation) during critical windows (Days 11-20, 38-40). Knowledge concentrated in single person (e.g., only one DB admin).

**Likelihood** (2/5):
- 10% chance per person per week unavailable
- Multiple DBAs or DevOps engineers could mitigate

**Impact** (3/5):
- Delay in current phase (backfill, ramp-up)
- Risk of error (less experienced person takes action)

**Mitigation Plan**:
1. **Days 1-5**: Cross-train at least 2 people per critical skill
   - Database backup/restore procedures
   - CI/CD pipeline operation
   - Incident response runbook
   
2. **Days 1-40**: Maintain documented runbooks (step-by-step, no tribal knowledge)
   
3. **Staffing**: Ensure 2+ people on-call during Days 11-20 and Days 38-40

**Acceptance Criteria**:
- [ ] At least 2 people trained per critical task
- [ ] All runbooks tested with team non-expert
- [ ] On-call schedule published for critical windows

**Owner**: Project manager / Team lead  
**Review Date**: Day 5 (cross-training checkpoint)

---

#### Risk #11: Performance Baseline Delta Post-Infrastructure
**Score**: 2 × 3 = **6** | **Severity**: LOW  
**Phase**: Days 1-10 & 21-30

**Description**:
Infrastructure migration (WSGI, reverse proxy) might introduce latency overhead vs single-process Flask dev server. Day 1 baseline may show regression vs Day 35 (SQLite single-process) baseline.

**Likelihood** (2/5):
- Production WSGI setup adds layer (app ↔ WSGI ↔ nginx)
- But: reverse proxy also caches, optimizes

**Impact** (3/5):
- Latency slightly higher, but likely still within SLO (< 8ms)
- Minimal user impact if explained

**Mitigation Plan**:
1. **Post-Infrastructure (Days 10-11)**:
   - Measure baseline on production environment (WSGI + reverse proxy)
   - Compare vs Day 35 SQLite baseline (should be within ±5%)
   - If >= 10% regression: profile and optimize (caching, connection pooling)
   
2. **Post-Migration (Days 21-22)**:
   - Re-baseline with PostgreSQL
   - Accept small regression (PostgreSQL joins vs SQLite flattened data)
   - Update performance SLO if needed

**Acceptance Criteria**:
- [ ] Infrastructure latency baseline measured (should be ≤ 5% regression vs Day 35)
- [ ] Any regression explained and documented
- [ ] SLO threshold updated if needed

**Owner**: Performance engineer  
**Review Date**: Day 11 (post-infrastructure), Day 22 (post-migration)

---

#### Risk #12: Documentation Debt Accumulates
**Score**: 1 × 3 = **3** | **Severity**: LOW  
**Phase**: Days 1-40 (All phases)

**Description**:
Rapid sprints through 40-day plan may result in incomplete documentation:
- Runbooks missing troubleshooting steps
- Configuration not versioned in git
- Incident response procedures untested

**Likelihood** (1/5):
- Structured daily deliverables enforce docs
- Agent creating machine-readable artifacts

**Impact** (3/5):
- Operations team confused post-go-live
- Escalations slow due to missing runbooks

**Mitigation Plan**:
1. **Each Phase**: Allocate 1 day for documentation pass
   - Pillar 1 (Days 1-10): Doc day = Day 10
   - Pillar 2 (Days 11-20): Doc day = Day 20
   - Pillar 3 (Days 21-30): Doc day = Day 30
   - Pillar 4 (Days 31-37): Doc day = Day 37
   - Pillar 5 (Days 38-40): Final doc = Day 40
   
2. **Standards**:
   - Runbook template (goal, prerequisites, steps, rollback, troubleshooting)
   - Configuration in version control (git)
   - Decision logs (why this choice)

**Acceptance Criteria**:
- [ ] All runbooks reviewed and tested (someone other than writer)
- [ ] Configuration versioned in git
- [ ] Tribal knowledge captured in docs

**Owner**: Technical writer / Team lead  
**Review Date**: Each phase-end doc day

---

## Risk Tracking Matrix

| # | Risk | Phase | Score | Status | Owner | Review |
|---|------|-------|-------|--------|-------|--------|
| 1 | Data Loss Migration | Days 11-20 | 25 🔴 | Mitigated | DB Admin | Day 15 |
| 2 | Infra Provisioning Delay | Days 1-10 | 20 🔴 | Mitigated | Infra Lead | Day 2 |
| 3 | CI/CD Scope Creep | Days 21-30 | 16 🔴 | Mitigated | DevOps | Day 25 |
| 4 | TLS Certificate Delay | Days 1-10 | 15 🟠 | Mitigated | Infra Lead | Day 3 |
| 5 | Performance Regression | Days 11-20 | 12 🟠 | Mitigated | Perf Eng | Day 16 |
| 6 | Monitoring Integration | Days 21-30 | 12 🟠 | Mitigated | Observability | Day 28 |
| 7 | Canary Untested | Days 31-37 | 8 🟡 | Mitigated | DevOps | Day 36 |
| 8 | Backup/Restore Fails | Days 6-40 | 8 🟡 | Mitigated | DB Admin | Day 10, 37 |
| 9 | Secrets in Git | Days 31-37 | 8 🟡 | Mitigated | Security | Day 33 |
| 10 | Team Availability | Days 1-40 | 6 🟢 | Monitored | PM | Day 5 |
| 11 | Latency Regression | Days 1-40 | 6 🟢 | Monitored | Perf Eng | Day 11, 22 |
| 12 | Documentation Debt | Days 1-40 | 3 🟢 | Monitored | Tech Writer | Phase-end |

---

## Weekly Risk Reviews

**Every Friday** (Days 5, 12, 19, 26, 33, 40):
- Review active risk status
- Move risks from "mitigated" → "closed" if acceptance criteria met
- Re-score any risks with updated information
- Escalate "critical" risks that haven't achieved mitigation gates

**Decision Gate**:
If any critical risk remains unmitigated at phase-end → **escalate to executive review** (may delay progression to next phase)

---

## Appendix: Risk Escalation Path

**Critical Risk Detection** (Score ≥ 16):
1. Notify project manager (same-day)
2. Activate assigned mitigation task force
3. Daily stand-up on risk (progress, blockers, timeline impact)
4. If unresolved by phase-end deadline → executive escalation

**High Risk Detection** (Score 12-15):
1. Include in daily stand-up briefing
2. Weekly review with risk owner
3. Contingency plan activated if likelihood increases

**Medium/Low Risks**:
1. Tracked in weekly review
2. Escalate only if score increases or likelihood changes

---

**Date Prepared**: March 30, 2026  
**Next Update**: Day 5 (Friday, April 4, 2026)
