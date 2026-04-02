# Day 37 (40-Day Plan Day 2): Infrastructure Bootstrap Planning

**Date**: March 30, 2026  
**Program Phase**: Production Operationalization (Days 1-40)  
**Pillar**: 1 - Infrastructure Hardening (Days 1-10)

## Executive Summary

Day 2 focuses on **infrastructure confirmation and decision-making**. The critical gate is Risk #2 validation: confirming production server availability. If not available, activate contingency staging path. Parallel work: TLS certificate issuance and WSGI technology selection.

---

## Day 2 Critical Gate: Infrastructure Provisioning Confirmation

### Gate Description: Risk #2 Mitigation Validation

**Status**: 🔴 AWAITING CONFIRMATION (Same-day verification required)

**Decision Required by EOD**: 
- **Path A (Preferred)**: Production server **confirmed available** → Days 2-10 proceed as planned
- **Path B (Contingency)**: Production server **delayed** → shift Days 1-10 activities to staging, plan swap Days 21-30

### Confirmation Checklist

```
□ Production server provisioned (hardware confirmed)
□ Network connectivity verified (app ↔ db connectivity tested)
□ Disk space confirmed (100+ GB available)
□ CPU cores available (4+ cores for WSGI pool)
□ RAM allocated (8+ GB minimum)
□ SSH/RDP access working
□ Firewall rules approved (app port, db port, monitoring)
□ Infrastructure team sign-off (email or ticket confirming ready)
```

**If ALL boxes checked**: Proceed to WSGI technology decision (Gate A)  
**If ANY box unchecked**: Activate contingency path (Gate B)

---

## Path A: Production Server Confirmed Available

### Objective 1: WSGI Server Technology Decision

**Duration**: 2-3 hours  
**Outcome**: Technology decision documented, team aligned

#### Option 1: Gunicorn (Recommended)
**Pros**:
- Simple, lightweight, production-proven
- Excellent documentation
- Easy integration with Nginx reverse proxy
- Good performance for Flask apps
- Easy worker scaling (pre-fork, threading, async)

**Cons**:
- Requires separate reload mechanism for code updates

**Decision Criteria for Gunicorn**:
- Single production environment (not multi-region)
- Standard Flask deployment patterns acceptable
- Team familiar with Python process management
- Cost-efficient (low resource overhead)

**Recommended Config** (for 4-core server):
```
--workers 5  # (2 * CPU_cores) + 1
--worker-class sync  # for thread-safe Flask app
--max-requests 1000  # graceful reload
--timeout 60  # attendance marking timeout
--bind 127.0.0.1:5000
```

#### Option 2: uWSGI (Alternative)
**Pros**:
- More feature-rich (code hot-reloading, stats, monitoring)
- Good for complex deployment scenarios

**Cons**:
- Steeper learning curve
- Configuration complexity (XML/INI files)
- More resource overhead
- Overkill for single-environment deployment

**Decision Criteria for uWSGI**:
- Multi-environment orchestration needed (staging + prod simultaneously)
- Advanced monitoring required
- Code hot-reload without downtime needed

---

### **RECOMMENDATION**: **Gunicorn** selected for Day 2-10 baseline

**Rationale**:
- Simplicity aligns with 40-day timeline (learn → configure → validate → move on)
- Single production environment (uWSGI features unnecessary)
- WSGI configuration can be versioned in git, no complex INI parsing
- Team can master Gunicorn in 1-2 days vs uWSGI 3-5 days

---

### Objective 2: Infrastructure Baseline Documentation

**Duration**: 1-2 hours  
**Outcome**: Infrastructure template created for Days 3-10 deployment

#### Server Specification Template

```yaml
production_server:
  hostname: "qr-attendance-prod"
  ip_address: "TBD"
  region: "TBD"
  provider: "TBD"  # OnPremise/AWS/Azure/GCP
  
  hardware:
    cpu_cores: 4
    cpu_type: "x86_64"
    ram_gb: 8
    disk_gb: 100
    disk_type: "SSD"  # recommended
    network_interface: "1Gbps"
  
  operating_system:
    name: "Ubuntu 22.04 LTS"  # or Windows Server 20xx / CentOS 8
    kernel: "TBD"
    python_version: "3.11+"
    package_manager: "apt"  # or yum/choco
  
  network_configuration:
    app_port: 5000
    db_host: "TBD"
    db_port: 5432
    monitoring_endpoint: "TBD"
    log_aggregation_endpoint: "TBD"
  
  firewall_rules:
    inbound:
      - port: 443  # HTTPS incoming
        protocol: tcp
        source: "0.0.0.0/0"  # or campus network CIDR
      - port: 22  # SSH
        protocol: tcp
        source: "admin_subnet_CIDR"
    outbound:
      - destination: "db_server"
        port: 5432
        protocol: tcp
      - destination: "log_aggregation"
        port: 514
        protocol: udp

  storage:
    backup_mount: "/backup"  # at least 100GB
    log_mount: "/var/log"
  
  monitoring_agent:
    installed: false  # Days 21-30
    target: "TBD Prometheus/Datadog/CloudWatch"
```

---

### Objective 3: TLS Certificate Issuance Initiation

**Duration**: 0.5-1 hour  
**Outcome**: Certificate process started, expected delivery date documented

#### TLS Strategy Decision

**Option A: Let's Encrypt (Recommended for Day 1-9)**
- Cost: FREE
- Issuance time: ~1-5 minutes (automated)
- Renewal: Every 90 days (can automate with certbot)
- Validation: DNS or HTTP challenge

**Steps**:
1. Register domain (if not done)
2. Install certbot on production server (Day 3)
3. Run certbot certonly (DNS validation preferred)
4. Configure cron for auto-renewal

**Expected Timeline**: 
- Day 2: Domain + DNS setup confirmed
- Day 3: Certbot deployment
- Day 3 evening: Certificate obtained (1-5 minutes)

**Option B: Commercial CA (Self-Signed Fallback)**
- Cost: $10-100/year
- Issuance time: 1-5 business days
- Renewal: Manual

**Fallback**: If Let's Encrypt fails, use self-signed cert for Days 2-10 (staging), upgrade to production cert after Day 10 (no downtime with Nginx reload)

---

#### RECOMMENDATION: **Let's Encrypt** selected

**Rationale**:
- Free, fast, automated
- If certificate delay issue emerges → escalate Day 2, Days 2-9 proceed with self-signed on staging
- No blocker to Days 3-10 progression (self-signed works for internal testing)

**TLS Initiation Checklist Day 2-3**:
```
□ Domain name confirmed
□ DNS CNAME/A record pointing to production server IP
□ Certbot installed on server (Day 3)
□ Certificate obtained (Day 3 evening)
□ Certificate renewal cron scheduled (Day 3 evening)
□ Nginx TLS config created (Day 4)
□ HTTPS accessibility verified (Day 4)
```

---

## Path B: Production Server NOT Available (Contingency)

**If Risk #2 triggered** (server NOT available by Day 2):

### Contingency Staging-First Path

**Scope Shift**:
- Days 2-10 infrastructure work runs on **staging environment** (secondary server or laptop VM)
- Exact same configurations/scripts/runbooks created but for staging
- Post-go-live: Migrate staging config to production (template reuse)

**Timeline Adjustment**:
- Days 11-20: PostgreSQL migration happens on staging
- Days 21-30: CI/CD automation targets staging
- Days 31-37: Security/hardening on staging
- Days 38-39: Wait for production server availability
- Day 39-40: Migrate all staging artifacts to production (compressed timeline, higher risk)

**Risk**:
- Production environment will differ from staging → re-baseline performance
- Compression Days 39-40 high pressure
- Contingency acceptable only if production available by Day 37 (latest)

**Mitigation**: 
- Infrastructure team commits Day 37 deadline (escalate if slipping)
- All configuration as code (infrastructure as templates)
- Dry-run production migration Days 38-39 without cutover

---

## Day 2 Deliverables

### Deliverable 1: Server Configuration Template
**File**: `project_notes/infrastructure/server_specification_template.yaml`  
**Purpose**: Baseline server config, reusable for staging or production  
**Status**: PENDING infrastructure team input

### Deliverable 2: WSGI Technology Decision Document
**File**: `project_notes/infrastructure/WSGI_TECHNOLOGY_DECISION.md`  
**Content**: 
- Gunicorn selected (rationale)
- Configuration template with recommendations
- Deployment instructions (Days 3-5)

### Deliverable 3: TLS Certificate Status
**File**: `project_notes/infrastructure/TLS_CERTIFICATE_STATUS.md`  
**Content**: 
- Let's Encrypt selected (rationale)
- Expected timeline (Day 3 evening delivery if DNS ready Day 2)
- Fallback self-signed procedure

### Deliverable 4: Infrastructure Confirmation Report
**File**: `project_notes/closeout/day2_infrastructure_confirmation_report.json`  
**Content**: 
- Path A or Path B decision documented
- Go/no-go gate status
- Risk #2 mitigation validation results

---

## Day 2 Completion Checklist

### Mandatory Gates (ALL must be PASS for Day 2 closure)

- [ ] **Gate 1 - Server Confirmation**: 
  - Status: Path A (server confirmed) OR Path B (contingency activated)
  - Owner: Infrastructure team
  
- [ ] **Gate 2 - WSGI Decision**:
  - Decision: Gunicorn selected
  - Configuration template created
  - Team alignment confirmed
  
- [ ] **Gate 3 - TLS Initiation**:
  - Certificate issuance process started (Let's Encrypt or commercial)
  - Expected delivery date documented
  - Fallback plan (self-signed) prepared
  
- [ ] **Gate 4 - Day 3 Kickoff Ready**:
  - Server bootstrap plan approved
  - WSGI deployment script template ready
  - TLS installation instructions prepared

---

## Day 3 Preview (Conditional on Path A)

**If Path A (Production Server Ready)**:
- Sunucu SSH/RDP access testing
- Linux baseline setup (package updates, Python 3.11 install)
- Supervisord/systemd service framework setup
- Gunicorn installation and configuration
- Reverse proxy (Nginx) baseline (non-TLS)

**If Path B (Staging-First)**:
- Staging server preparation (VM or secondary hardware)
- Exact same setup as production baseline
- Note: Different IP address, different hostname, but identical config template

---

## Daily Work Summary

**Expected Duration**: 4-6 hours  
**Critical Decision Point**: Infrastructure path A vs B  
**Risk Tracking**: Risk #2 status → Green (server confirmed) OR Yellow (contingency activated)

| Task | Duration | Owner | Status |
|------|----------|-------|--------|
| Server confirmation gate | 1 hour | Infrastructure Lead | AWAITING |
| WSGI technology decision | 2 hours | DevOps / Lead | PENDING |
| TLS initiation | 1 hour | Infrastructure Lead | PENDING |
| Deliverables + Day 3 prep | 1-2 hours | Technical Lead | PENDING |

---

## Artifacts to Produce Today

| Artifact | Format | Purpose |
|----------|--------|---------|
| server_specification_template.yaml | YAML | Infrastructure baseline (reusable) |
| WSGI_TECHNOLOGY_DECISION.md | Markdown | Gunicorn selection + config |
| TLS_CERTIFICATE_STATUS.md | Markdown | Let's Encrypt timeline + fallback |
| day2_infrastructure_confirmation_report.json | JSON | Path A/B decision + gate status |

---

## Decision Log for Day 2

**Decision**: WSGI = Gunicorn  
**Date**: March 30, 2026 (Decision day)  
**Rationale**: Simple, production-proven, aligns with 40-day timeline  
**Alternative Considered**: uWSGI (complex, unnecessary for single-env)  
**Reversibility**: Medium (config can be swapped to uWSGI if needed, but 2-3 day rework)

**Decision**: TLS = Let's Encrypt  
**Date**: March 30, 2026  
**Rationale**: Free, fast, automated; production-grade  
**Contingency**: Self-signed cert (Days 2-3 fallback if DNS delays)  
**Reversibility**: High (cert replaced, zero downtime with Nginx reload)

**Decision Pending**: Path A vs B  
**Depends On**: Infrastructure team server provisioning confirmation  
**Decision Deadline**: EOD March 30, 2026  
**Escalation**: If no confirmation by 5 PM → escalate to CTO for Day 3 decision

---

## Next Steps

### Immediate (Now)
1. Contact infrastructure team → confirm server availability
2. Begin WSGI vs uWSGI analysis → decide Gunicorn
3. Start TLS certificate domain prep

### By End of Day
1. Receive infrastructure team confirmation (Path A or B)
2. Document WSGI decision (Gunicorn selected)
3. Initiate TLS certificate process (or note self-signed fallback)
4. Prepare Day 3 kickoff plan

### By Day 3 Morning
1. Server confirmed ready (or contingency activated)
2. WSGI configuration template prepared
3. TLS deployment instructions ready
4. Begin server bootstrap (OS updates, Python install, Gunicorn install)

---

**Day 2 Status**: 🟡 IN PROGRESS  
**Estimated Completion**: March 30, 2026 (EOD, ~4-6 hours from start)  
**Risk Status**: Risk #2 (Infrastructure Delay) → VALIDATION GATE
