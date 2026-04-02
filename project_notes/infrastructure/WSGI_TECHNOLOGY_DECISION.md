# WSGI Technology Decision Document

**Date**: March 30, 2026  
**Day**: 2 (40-Day Production Plan)  
**Decision**: **Gunicorn selected as production WSGI server**

---

## Executive Decision

| Factor | Recommendation | Rationale |
|--------|-----------------|-----------|
| **WSGI Server** | **Gunicorn** | Simple, lightweight, production-proven, 40-day timeline friendly |
| **Python Worker Type** | **sync** | Flask app is thread-safe, standard patterns |
| **Number of Workers** | **5** (for 4-core server) | Formula: (2 × CPU_cores) + 1 |
| **Reverse Proxy** | **Nginx** (paired with Gunicorn) | Standard production stack, good performance |
| **Service Manager** | **systemd** (Linux) or **nssm** (Windows) | Native init system, auto-restart on crash |
| **Configuration Management** | **Git-versioned gunicorn.conf.py** | Infrastructure as code, auditable |

---

## Comparison Matrix: Gunicorn vs uWSGI

| Criterion | Gunicorn | uWSGI | Winner |
|-----------|----------|-------|--------|
| **Setup Complexity** | Low (simple CLI) | High (XML/INI config) | Gunicorn ✅ |
| **Learning Curve** | 1-2 days | 3-5 days | Gunicorn ✅ |
| **Production Maturity** | Excellent (used by Heroku, DjangoPeople) | Excellent (enterprise deployments) | Tie |
| **Performance** | Excellent (lightweight) | Excellent (feature-rich) | Tie |
| **Documentation** | Excellent (community friendly) | Good (feature-heavy) | Gunicorn ✅ |
| **Code Hot-Reload** | Requires reload mechanism | Built-in | uWSGI ✅ |
| **Monitoring/Stats** | Basic (external tools) | Advanced (built-in) | uWSGI ✅ |
| **Resource Overhead** | Low | Medium | Gunicorn ✅ |
| **Fit for 40-day Timeline** | Excellent | Good | Gunicorn ✅ |
| **Multi-environment Scaling** | Requires load-balancer | Better for complex setups | uWSGI ✅ |

**Score: Gunicorn 5/9, uWSGI 2/9, Tie 2/9 → Gunicorn Winner** ✅

---

## Why Gunicorn for This Project

### 1. **Simplicity Aligns with Timeline**
- **Day 1-10 focus**: Get infrastructure running, not mastering complex deployment orchestration
- **Gunicorn learning curve**: 1-2 days (by Day 3, team is productive)
- **uWSGI learning curve**: 3-5 days (lost 1-3 days on timeline)
- **Decision impact**: Days 2-5 can proceed immediately, no learning blockers

### 2. **Single Production Environment**
- No multi-region, no active-active HA in scope (40-day Phase 1 definition)
- Gunicorn excels in single-environment deployments
- uWSGI's advanced features (hot-reload, multi-environment) unnecessary waste

### 3. **Standard Flask Deployment Pattern**
- Every Flask deployment guide defaults to Gunicorn + Nginx
- Team finds examples, Stack Overflow answers, debug guidance easily
- uWSGI requires specialized knowledge, fewer practitioners

### 4. **Git-Versioned Configuration**
- Gunicorn config as Python file (`gunicorn.conf.py`) → git-friendly
- uWSGI config as XML/INI → parsing quirks, environment variable expansion complexity
- Infrastructure-as-code principle: version control + audit trail

### 5. **Production Battles Proven**
- Used by Heroku (largest PaaS provider)
- Used by DjangoPeople (millions of active Flask apps)
- Failure modes well-documented, debugging guidance abundant

---

## Gunicorn Configuration Recommendation

### Recommended Deployment Config

```python
# gunicorn.conf.py (production baseline)

import multiprocessing

# Server socket
bind = "127.0.0.1:5000"  # localhost only, reverse proxy handles external
backlog = 2048

# Worker processes
workers = 5  # (2 * CPU_cores) + 1 for 4-core server
worker_class = "sync"  # Thread-safe Flask, standard
worker_connections = 1000

# Maximum requests before graceful worker restart
max_requests = 1000
max_requests_jitter = 100

# Timeouts
timeout = 60  # 60-second timeout (for attendance marking delays)
keepalive = 2

# Logging
accesslog = "-"  # stdout (systemd captures to journalctl)
errorlog = "-"  # stderr
loglevel = "info"  # info level for production

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Process naming
proc_name = "qr-attendance-app"

# Server mechanics
daemon = False  # managed by systemd, not daemonized
preload_app = True  # preload Flask app (faster worker spin-up)
```

### Deployment Command (after installation)

```bash
# Install gunicorn
pip install gunicorn

# Run with config file
gunicorn app:app --config gunicorn.conf.py

# Or run with CLI args (if config file not available)
gunicorn app:app \
  --bind 127.0.0.1:5000 \
  --workers 5 \
  --worker-class sync \
  --max-requests 1000 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

---

## Performance Profile (Based on Gunicorn + Nginx + Flask)

### Measured Baseline (from Day 35)

| Endpoint | Latency (avg) | Latency (p95) | Source |
|----------|---------------|---------------|--------|
| `/health` | 0.28 ms | ~1 ms | perf_baseline.py |
| `/login` | 0.29 ms | ~1 ms | perf_baseline.py |
| `/teacher_dashboard` | 2.68 ms | ~5 ms | perf_baseline.py |
| Aggregate | ~1.0 ms | ~5 ms | perf_baseline.py |

### Expected Performance with Gunicorn + Nginx (Production)

**Assumption**: Add reverse proxy + network overhead

| Endpoint | Expected Latency (p95) | Target SLO |
|----------|------------------------|------------|
| `/health` | ~5 ms | < 100 ms |
| `/login` | ~5 ms | < 500 ms |
| `/teacher_dashboard` | ~10 ms | < 2000 ms |
| Aggregate | ~10 ms | < 5000 ms |

**Assessment**: Should achieve SLO targets with room to spare ✅

---

## Migration Path (if switching from uWSGI later)

**Reversibility**: Medium effort, low risk

**If Day 3-5 reveals Gunicorn insufficient** (unlikely):
1. Stop Gunicorn workers
2. Install uWSGI (`pip install uwsgi`)
3. Create uWSGI config (3-4 hours)
4. Update systemd service file (30 minutes)
5. Re-test performance (2 hours)
6. Total rework: ~6-8 hours (could slip Days 5-6 if needed, acceptable risk)

**Reversibility trigger**: If latency p95 > 10 ms or error rate > 1% under load test (Days 3-5), escalate to uWSGI evaluation

---

## Systemd Service Integration (Linux)

**File**: `/etc/systemd/system/qr-attendance.service`

```ini
[Unit]
Description=QR Attendance Flask Application
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/qr-attendance
ExecStart=/opt/qr-attendance/venv/bin/gunicorn app:app --config gunicorn.conf.py
Restart=always
RestartSec=10

# Resource limits
LimitNOFILE=65535
LimitNPROC=65535

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=qr-attendance

# Environment
EnvironmentFile=/opt/qr-attendance/.env

[Install]
WantedBy=multi-user.target
```

**Commands**:
```bash
# Enable service auto-start on reboot
sudo systemctl enable qr-attendance

# Start service
sudo systemctl start qr-attendance

# Check status
sudo systemctl status qr-attendance

# View logs
sudo journalctl -u qr-attendance -f  # live tail
```

---

## Nginx Reverse Proxy Configuration (Paired with Gunicorn)

**File**: `/etc/nginx/sites-available/qr-attendance`

```nginx
upstream gunicorn_qr_attendance {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name qr-attendance.example.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name qr-attendance.example.com;
    
    # TLS certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/qr-attendance.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/qr-attendance.example.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /var/log/nginx/qr-attendance_access.log;
    error_log /var/log/nginx/qr-attendance_error.log;
    
    # Proxy to Gunicorn
    location / {
        proxy_pass http://gunicorn_qr_attendance;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts (match Gunicorn)
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files (if any)
    location /static/ {
        alias /opt/qr-attendance/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## Decision Document Sign-Off

| Role | Name | Review Date | Status |
|------|------|-------------|--------|
| Technical Lead | [TBD] | March 30, 2026 | Ready for review |
| DevOps Lead | [TBD] | March 30, 2026 | Ready for review |
| Infrastructure Lead | [TBD] | March 30, 2026 | Ready for review |

---

## Implementation Timeline (Days 3-5)

| Day | Task | Duration | Owner |
|-----|------|----------|-------|
| Day 3 | OS baseline setup, Python install | 2-3 hrs | Infra |
| Day 3 | Gunicorn installation | 0.5 hr | Infra |
| Day 4 | gunicorn.conf.py deployment | 1 hr | Infra |
| Day 4 | Systemd service setup | 1 hr | Infra |
| Day 4 | Nginx reverse proxy config | 1-2 hrs | Infra |
| Day 5 | Load test (100 concurrent requests) | 1 hr | Perf |
| Day 5 | Baseline performance measurement | 1 hr | Perf |
| Day 5 | Day 5 closure report | 0.5 hr | Lead |

---

## Appendix: FAQ

**Q: Why not use Nginx Unit?**  
A: Nginx Unit is bleeding-edge; Gunicorn is battle-tested. Timeline risk too high.

**Q: Why not use FastAPI instead of Flask?**  
A: App already built on Flask; Days 2-10 are operations, not refactoring.

**Q: Can we use Gunicorn async workers?**  
A: Possible, but requires Flask app changes (async/await patterns). Skip for Phase 1.

**Q: What if we need hot-reload in production?**  
A: Blue-green deployment with Nginx traffic switch (implemented Days 21-30 with CI/CD).

**Q: How do we handle graceful shutdown?**  
A: Gunicorn handles SIGTERM gracefully (systemd default). Existing requests finish, new requests rejected. ~30-second drain.

---

**Decision Date**: March 30, 2026  
**Effective**: Day 3 deployment  
**Review Date**: Day 5 (post-load-test)  
**Reversibility**: Medium (can switch to uWSGI if needed, ~6-8 hour rework)
