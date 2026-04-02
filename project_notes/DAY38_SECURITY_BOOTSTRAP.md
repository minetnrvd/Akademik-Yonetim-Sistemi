# Day 38 (40-Day Plan Day 3): Infrastructure Security Bootstrap

**Date**: March 31, 2026  
**Program Phase**: Production Operationalization (Days 1-40)  
**Pillar**: 1 - Infrastructure Hardening (Days 1-10)  
**Security Focus**: Yes — All configurations prioritize security first

**Prerequisite**: Day 2 completed; Path A (production server ready) OR Path B (staging) confirmed

---

## Executive Summary

Day 3 transitions from planning to **secure infrastructure bootstrap**. Focus: OS-level security hardening, Python environment isolation, user privilege separation, audit logging, and firewall configuration. No shortcuts — every step prioritizes future-proof security over speed.

---

## Security-First Philosophy

> "Everything is easy to get in, hard to get out. Configure once correctly rather than fix breaches later."

### Guiding Principles:
1. **Least Privilege**: Each process, user, and service has minimum required permissions
2. **Immutability**: Configuration versioned in git; runtime state read-only where possible
3. **Auditability**: Every privileged action logged; tampering detected
4. **Segmentation**: App, DB, monitoring on separate credentials/subnets
5. **Defense in Depth**: Multiple layers (firewall, file perms, selinux, apparmor)

---

## Day 3 Objectives (Sequenced)

### Objective 1: SSH Hardening & Secure Server Access (1-2 hours)

**Goal**: Lock down SSH before any app deployment

#### Step 1a: SSH Key-Based Authentication Only

```bash
# On local machine (generates keypair)
ssh-keygen -t ed25519 -f ~/.ssh/qr-attendance-prod -C "qr-attendance-prod"
# Output: private key ~/.ssh/qr-attendance-prod (NEVER share)
#         public key ~/.ssh/qr-attendance-prod.pub (upload to server)

# On production server (authorized_keys)
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cat >> ~/.ssh/authorized_keys << 'EOF'
ssh-ed25519 AAAAC3NzaC1lZDI1... (public key content from above)
EOF
chmod 600 ~/.ssh/authorized_keys
```

#### Step 1b: Disable Password Authentication

```bash
# Edit /etc/ssh/sshd_config
sudo sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# Disable root login
sudo sed -i 's/^#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/^PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Disable empty password login
sudo sed -i 's/^#PermitEmptyPasswords/PermitEmptyPasswords no/' /etc/ssh/sshd_config

# Limit authentication attempts
echo "MaxAuthTries 3" | sudo tee -a /etc/ssh/sshd_config
echo "MaxSessions 5" | sudo tee -a /etc/ssh/sshd_config

# Verify syntax
sudo sshd -t  # should output no errors

# Reload SSH daemon (test first — keep existing connection!)
sudo systemctl reload ssh
```

#### Step 1c: SSH Access Verification

```bash
# From local machine, test key-based login
ssh -i ~/.ssh/qr-attendance-prod ubuntu@qr-attendance-prod

# Once verified, disable password auth permanently
# (already done above)

# If blocked: never close first connection; open new terminal to debug
```

**Security Outcome**: 
- ✅ SSH keys only (ed25519, strong)
- ✅ No password login allowed
- ✅ No root SSH access
- ✅ Max 3 auth attempts (brute-force protection)

---

### Objective 2: OS-Level Security Hardening (2-3 hours)

**Goal**: Baseline OS security before any application code deployed

#### Step 2a: System Updates

```bash
sudo apt update
sudo apt upgrade -y  # All security patches
sudo apt autoremove -y  # Remove unused packages
```

#### Step 2b: Install Security Tools

```bash
# Firewall
sudo apt install -y ufw

# Fail2ban (prevent brute-force)
sudo apt install -y fail2ban

# Audit logging
sudo apt install -y auditd

# ClamAV (antivirus for compliance)
sudo apt install -y clamav clamav-daemon

# Aide (file integrity monitoring)
sudo apt install -y aide aide-common
```

#### Step 2c: Firewall Configuration

```bash
# Enable UFW (but don't start yet — configure first)
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (CRITICAL — lock yourself out otherwise!)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS (reverse proxy)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow database access (if same machine; otherwise restrict to db subnet)
# sudo ufw allow from db_network to any port 5432

# Verify rules before enabling
sudo ufw show added

# Enable firewall
sudo ufw enable
```

#### Step 2d: Audit Logging (auditd)

```bash
# Enable audit daemon
sudo systemctl enable auditd
sudo systemctl start auditd

# Add audit rules (log all system calls for critical apps)
sudo cat >> /etc/audit/rules.d/prod-qr-attendance.rules << 'EOF'
# Monitor /opt/qr-attendance (app directory) for changes
-w /opt/qr-attendance/ -p wa -k app_changes

# Monitor /etc/gunicorn* for config changes
-w /etc/gunicorn -p wa -k gunicorn_config

# Monitor sudo usage
-a always,exit -F arch=b64 -S execve -k sudo_exec

# Monitor SSH login attempts
-w /var/log/auth.log -p wa -k auth_changes
EOF

# Reload audit rules
sudo service auditd restart

# Test: query logs
sudo ausearch -k app_changes
```

#### Step 2e: Fail2ban Configuration (Brute-Force Protection)

```bash
# Copy default config
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Edit /etc/fail2ban/jail.local
sudo cat >> /etc/fail2ban/jail.local << 'EOF'
[ssh]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3  # Ban after 3 failed attempts
findtime = 600  # Within 10 minutes
bantime = 3600  # Ban for 1 hour

[recidive]
enabled = true
filter = recidive
action = iptables-multiport[name=recidive, port=ssh, protocol=tcp]
logpath = /var/log/fail2ban.log
bantime = 604800  # Ban for 7 days if repeat offender
findtime = 86400  # Within 24 hours
maxretry = 2
EOF

# Start Fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Verify active jails
sudo fail2ban-client status
```

**Security Outcome**:
- ✅ All packages patched
- ✅ UFW firewall operational (default-deny)
- ✅ Audit logging enabled (all app changes tracked)
- ✅ Fail2ban protecting SSH (3-strike lockout)

---

### Objective 3: Application User & Directory Permissions (1 hour)

**Goal**: Run Flask app as non-root user with minimum privileges

#### Step 3a: Create Application User

```bash
# Create dedicated user for Flask app
sudo useradd -r -s /bin/bash -d /opt/qr-attendance -m qr-app

# Verify user created
id qr-app

# Set secure shell (restricted)
sudo usermod -s /usr/sbin/nologin qr-app  # No interactive shell

# Verify
sudo su - qr-app  # Should fail: "This account is currently not available"
```

#### Step 3b: Create Application Directory Structure

```bash
# Create app directory (owned by qr-app)
sudo mkdir -p /opt/qr-attendance/{app,config,data,logs,venv}
sudo chown -R qr-app:qr-app /opt/qr-attendance/
sudo chmod 750 /opt/qr-attendance/  # User + group read/execute, others none

# Create symbolic link to code (from deployment location)
sudo mkdir -p /srv/qr-attendance-releases/v1.0
sudo chown -R qr-app:qr-app /srv/qr-attendance-releases/
```

#### Step 3c: Copy Flask Application Code (Secure)

```bash
# Copy code from current working directory to /opt/qr-attendance
sudo cp -r app.py models.py /opt/qr-attendance/app/
sudo cp -r templates/ /opt/qr-attendance/app/
sudo cp -r static/ /opt/qr-attendance/app/

# Set ownership and permissions
sudo chown -R qr-app:qr-app /opt/qr-attendance/app/
sudo chmod 750 /opt/qr-attendance/app/  # User can read/write, group read, others none
sudo chmod 644 /opt/qr-attendance/app/*.py  # Code readable but not writable by others
```

#### Step 3d: Virtual Environment Setup (Isolated)

```bash
# Create venv as qr-app user
sudo -u qr-app python3 -m venv /opt/qr-attendance/venv

# Activate and install dependencies
source /opt/qr-attendance/venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install flask flask-sqlalchemy gunicorn python-dotenv pytest
pip freeze > /opt/qr-attendance/requirements.txt

# Verify installed
pip list

# Lock down venv
sudo chmod 750 /opt/qr-attendance/venv/
sudo chmod 644 /opt/qr-attendance/venv/pyvenv.cfg
```

**Security Outcome**:
- ✅ Flask app runs as non-root (qr-app)
- ✅ App user cannot login interactively
- ✅ Directory permissions: 750 (user rwx, group r-x, others none)
- ✅ Virtual environment isolated (system Python untouched)

---

### Objective 4: Environment Variables & Secrets Management (1 hour)

**Goal**: Secure credential storage (never in code/git)

#### Step 4a: Create Environment Configuration

```bash
# Create .env file (NEVER commit to git)
sudo cat > /opt/qr-attendance/.env << 'EOF'
# Flask
FLASK_ENV=production
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
DEBUG=False

# Database (PostgreSQL, even if using SQLite for now)
DATABASE_URL=sqlite:////data/attendance.db
# DATABASE_URL=postgresql://user:password@localhost:5432/qr_attendance

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME=3600

# Logging
LOG_LEVEL=INFO
EOF

# Set permissions: readable only by qr-app
sudo chown qr-app:qr-app /opt/qr-attendance/.env
sudo chmod 600 /opt/qr-attendance/.env  # User read/write only
```

#### Step 4b: Secrets Scanning Pre-Deploy

```bash
# Install git-secrets (if git available)
sudo apt install -y git

# Add secret patterns
git config --global secrets.patterns "['\"]SECRET_KEY['\"][\\s:=]+['\"][^'\"]+['\"]"
git config --global secrets.patterns "password[\\s:=]+"

# Scan code directory
cd /opt/qr-attendance/app/
git secrets --scan  # Should find nothing

# If found: remediate before proceeding
```

**Security Outcome**:
- ✅ .env file exists with strong SECRET_KEY
- ✅ .env permissions: 600 (user only)
- ✅ No secrets in git history
- ✅ SESSION_COOKIE flags set for HTTPS

---

### Objective 5: Python Dependency Security Audit (1 hour)

**Goal**: Identify and mitigate CVE risks in dependencies

#### Step 5a: Dependency Scanning

```bash
# Install safety (CVE checker for Python)
pip install safety

# Scan requirements.txt
safety check --file requirements.txt --json > /tmp/safety_report.json

# Review findings
cat /tmp/safety_report.json | python3 -m json.tool

# This will report:
# - Known vulnerabilities in installed packages
# - Severity (low, medium, high, critical)
# - Remediation (update to X version)
```

#### Step 5b: License Compliance Check

```bash
# Install pip-audit (more comprehensive than safety)
pip install pip-audit

# Scan for CVEs and licenses
pip-audit --desc  # Detailed output

# Output like:
# Found 0 packages with known vulnerabilities
# All licenses are compatible
```

#### Step 5c: Pinned Dependencies

```bash
# Use specific versions (not floating ~= or >=)
# Already in requirements.txt format:
cat /opt/qr-attendance/requirements.txt

# Example:
# flask==2.3.2
# gunicorn==20.1.0
# pytest==7.3.1

# This prevents unexpected breaking changes
```

**Security Outcome**:
- ✅ All dependencies scanned for CVEs
- ✅ No known vulnerabilities (or mitigated)
- ✅ Pinned versions (reproducible, no surprises)
- ✅ License compliance verified

---

### Objective 6: Gunicorn Security Configuration (1 hour)

**Goal**: Hardened WSGI server with minimal attack surface

#### Step 6a: Create Secure gunicorn.conf.py

```bash
# Create configuration file
sudo cat > /opt/qr-attendance/gunicorn.conf.py << 'EOF'
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:5000"  # Localhost only (Nginx reverse proxy handles external)
backlog = 2048

# Worker processes
workers = 5  # (2 * CPU_cores) + 1
worker_class = "sync"
worker_connections = 100  # Low connections per worker (security)

# Timeouts (graceful shutdown)
timeout = 60
keepalive = 2

# Request limits (prevent abuse)
limit_request_line = 4094  # Standard HTTP line limit
limit_request_fields = 100  # Typical request has ~30-40 headers
limit_request_field_size = 8190  # Standard header size

# Maximum requests before worker restart (memory leak cleanup)
max_requests = 1000
max_requests_jitter = 50

# Logging (structured)
accesslog = "/opt/qr-attendance/logs/access.log"
errorlog = "/opt/qr-attendance/logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming (monitoring/debugging)
proc_name = "qr-attendance-app"

# Security: disable daemon mode (managed by systemd)
daemon = False

# Preload app for worker efficiency
preload_app = True

# Security: close worker connections gracefully
graceful_timeout = 30

# Listen backlog (queue for incoming connections)
backlog = 2048
EOF

# Set permissions
sudo chown qr-app:qr-app /opt/qr-attendance/gunicorn.conf.py
sudo chmod 640 /opt/qr-attendance/gunicorn.conf.py
```

#### Step 6b: Create Startup Script (with security flags)

```bash
# Create wrapper script
sudo cat > /opt/qr-attendance/run.sh << 'EOF'
#!/bin/bash
set -euo pipefail  # Fail fast on errors

# Load environment
export $(cat /opt/qr-attendance/.env | grep -v '^#' | xargs)

# Change to app directory
cd /opt/qr-attendance/app

# Start Gunicorn with security flags
exec /opt/qr-attendance/venv/bin/gunicorn \
  --config /opt/qr-attendance/gunicorn.conf.py \
  --user qr-app \
  --group qr-app \
  --chdir /opt/qr-attendance/app \
  app:app
EOF

# Make executable, set permissions
sudo chmod 750 /opt/qr-attendance/run.sh
sudo chown qr-app:qr-app /opt/qr-attendance/run.sh
```

**Security Outcome**:
- ✅ Gunicorn listens localhost only (no external exposure)
- ✅ Worker count limited (prevents resource exhaustion)
- ✅ Request size limits enforced (prevents buffer overflow)
- ✅ Logging enabled for audit trail
- ✅ Worker restart on memory thresholds (leak prevention)

---

### Objective 7: Systemd Service Hardening (1 hour)

**Goal**: Secure service startup, isolation, and monitoring

#### Step 7a: Create Hardened systemd Service

```bash
# Create service file
sudo cat > /etc/systemd/system/qr-attendance.service << 'EOF'
[Unit]
Description=QR Attendance Flask Application (Production)
After=network.target postgresql.service
Wants=postgresql.service
Documentation=https://qr-attendance.example.com/docs

[Service]
# Process isolation
Type=notify
User=qr-app
Group=qr-app
WorkingDirectory=/opt/qr-attendance

# Startup
ExecStart=/opt/qr-attendance/run.sh
Restart=on-failure
RestartSec=10

# Security: read-only filesystem except for logs
ProtectSystem=strict
ProtectHome=yes
NoNewPrivileges=yes
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictRealtime=yes
RestrictNamespaces=yes
LockPersonality=yes

# Resource limits
LimitNOFILE=65535
LimitNPROC=512  # Max 512 processes per user
MemoryLimit=512M  # Max 512 MB RAM
CPUQuota=80%  # Max 80% CPU

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=qr-attendance

# Environment
EnvironmentFile=/opt/qr-attendance/.env

# Security: only allow specific capabilities
AmbientCapabilities=
CapabilityBoundingSet=

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable qr-attendance

# Verify service file syntax
sudo systemd-analyze verify /etc/systemd/system/qr-attendance.service
```

#### Step 7b: Test Service Startup

```bash
# Start service
sudo systemctl start qr-attendance

# Check status
sudo systemctl status qr-attendance

# Check logs
sudo journalctl -u qr-attendance -f  # Follow logs

# Verify process running as qr-app
ps aux | grep qr-attendance  # Should show "qr-app" user

# Verify listening on localhost:5000
sudo ss -tulpn | grep 5000  # Should show 127.0.0.1:5000
```

**Security Outcome**:
- ✅ Service runs as non-root (qr-app)
- ✅ Filesystem hardened (read-only except logs)
- ✅ Resource limits enforced (no runaway processes)
- ✅ Auto-restart on crash (resilient)
- ✅ Journalctl logging enabled (audit trail)

---

### Objective 8: Nginx Reverse Proxy Hardening (1 hour)

**Goal**: Secure HTTPS termination, request filtering, headers

#### Step 8a: Install and Harden Nginx

```bash
sudo apt install -y nginx

# Create Nginx config (from Day 2 TLS document, enhanced)
sudo cat > /etc/nginx/sites-available/qr-attendance << 'EOF'
upstream gunicorn_qr_attendance {
    server 127.0.0.1:5000 fail_timeout=5s max_fails=3;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;

# HTTP → HTTPS redirect
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name qr-attendance.example.com;
    
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;
    server_name qr-attendance.example.com;

    # TLS certificates (Let's Encrypt — Day 3 afternoon)
    ssl_certificate /etc/letsencrypt/live/qr-attendance.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/qr-attendance.example.com/privkey.pem;

    # TLS hardening
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5:!3DES;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'" always;

    # Logging
    access_log /var/log/nginx/qr-attendance_access.log combined buffer=32k flush=5s;
    error_log /var/log/nginx/qr-attendance_error.log warn;

    # Hide Nginx version
    server_tokens off;

    # Request size limits
    client_max_body_size 10M;
    client_body_buffer_size 128k;
    client_body_timeout 12;
    client_header_timeout 12;
    keepalive_timeout 15;
    send_timeout 10;

    # Rate limiting on sensitive endpoints
    location /login {
        limit_req zone=login_limit burst=10 nodelay;
        proxy_pass http://gunicorn_qr_attendance;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        limit_req zone=api_limit burst=50 nodelay;
        proxy_pass http://gunicorn_qr_attendance;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static/ {
        alias /opt/qr-attendance/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/qr-attendance /etc/nginx/sites-enabled/

# Test syntax
sudo nginx -t

# Reload (or start if first time)
sudo systemctl enable nginx
sudo systemctl reload nginx
```

**Security Outcome**:
- ✅ HTTPS enforced (HTTP redirects to HTTPS)
- ✅ TLS 1.2+ only (TLS 1.0/1.1 disabled)
- ✅ Strong ciphers enforced
- ✅ Security headers set (HSTS, CSP, X-Frame-Options)
- ✅ Rate limiting (5req/min login, 100req/min API)
- ✅ Nginx version hidden

---

## Day 3 Completion Checklist

### Security Gates (ALL must be PASS)

- [ ] **Gate 1 - SSH Hardening**:
  - [ ] Key-based auth only (ed25519)
  - [ ] Password login disabled
  - [ ] Root login disabled
  - [ ] Fail2ban active (3-strike lockout)

- [ ] **Gate 2 - OS Hardening**:
  - [ ] UFW firewall enabled (port 22, 80, 443 only)
  - [ ] Auditd logging active
  - [ ] All packages patched
  - [ ] ClamAV + AIDE installed

- [ ] **Gate 3 - Application User**:
  - [ ] qr-app user created (nologin shell)
  - [ ] /opt/qr-attendance owned by qr-app (750 permissions)
  - [ ] Python venv isolated in /opt/qr-attendance/venv

- [ ] **Gate 4 - Secrets Management**:
  - [ ] .env file created (600 permissions)
  - [ ] SECRET_KEY generated (32+ bytes)
  - [ ] No secrets in code/git
  - [ ] Safety + pip-audit passed (0 CVEs)

- [ ] **Gate 5 - Gunicorn Hardening**:
  - [ ] gunicorn.conf.py deployed (request limits, timeouts)
  - [ ] run.sh created (secure startup)
  - [ ] Listens 127.0.0.1:5000 only (no ext exposure)
  - [ ] Systemd service hardened (ProtectSystem=strict, MemoryLimit)

- [ ] **Gate 6 - Service Startup**:
  - [ ] systemd service active
  - [ ] Process running as qr-app (not root)
  - [ ] systemctl restart works (graceful)
  - [ ] journalctl logs showing (audit trail)

- [ ] **Gate 7 - Nginx Security**:
  - [ ] Nginx running on 0.0.0.0:80 and 0.0.0.0:443
  - [ ] HTTP → HTTPS redirect working
  - [ ] TLS certificates placeholder URL (Let's Encrypt pending)
  - [ ] Rate limiting active (curl test)
  - [ ] Security headers present (curl -i to verify)

- [ ] **Gate 8 - Integration Test**:
  - [ ] curl http://qr-attendance.example.com → redirects to https
  - [ ] curl https://qr-attendance.example.com/health → responds (once TLS cert ready)
  - [ ] Request logged in nginx access.log
  - [ ] Security headers present in response

---

## Day 3 Deliverables

| Artifact | Location | Purpose |
|----------|----------|---------|
| SSH Hardening Document | `project_notes/infrastructure/SSH_HARDENING.md` | Key-auth, fail2ban setup |
| OS Hardening Checklist | `project_notes/infrastructure/OS_HARDENING_CHECKLIST.md` | UFW, audit, packages |
| gunicorn.conf.py | `/opt/qr-attendance/gunicorn.conf.py` | Secure WSGI config |
| systemd Service File | `/etc/systemd/system/qr-attendance.service` | Hardened service startup |
| Nginx Config | `/etc/nginx/sites-available/qr-attendance` | Reverse proxy + TLS |
| Environment Config | `/opt/qr-attendance/.env` | Secrets management |
| Day 3 Closeout Report | `project_notes/closeout/day3_security_bootstrap_report.json` | All gates + sign-off |

---

## Security Verification Commands (Day 3 Afternoon)

```bash
# SSH security check
ssh -i ~/.ssh/qr-attendance-prod ubuntu@qr-attendance-prod "sudo sshd -T | grep -E 'passwordauth|pubkeyauth|permitempty|permitrootlogin'"
# Expected: passwordauthentication no, pubkeyauthentication yes, permitemptypasswords no, permitylogin no

# Firewall check
sudo ufw status
# Expected: 22, 80, 443 allowed; rest denied

# Process check
ps aux | grep qr-app
# Expected: qr-app user running gunicorn

# Port check
sudo ss -tulpn | grep LISTEN
# Expected: 127.0.0.1:5000 (app), 0.0.0.0:80 nginx, 0.0.0.0:443 nginx

# Service log check
sudo journalctl -u qr-attendance -n 20
# Expected: no errors, app initialized

# CVE check
pip-audit
# Expected: 0 vulnerabilities
```

---

## Risk Mitigation Summary (Day 3)

| Risk | Mitigation | Status |
|------|-----------|--------|
| Unauthorized SSH access | Key-based auth + fail2ban | ✅ |
| Privilege escalation | Non-root app user + SELinux-ready | ✅ |
| Network exposure | UFW firewall + Nginx reverse proxy | ✅ |
| Secrets leak | .env file (600 perms) + git-secrets | ✅ |
| Dependency CVEs | pip-audit + pinned versions | ✅ |
| DDoS / brute-force | Rate limiting + fail2ban | ✅ |
| Configuration drift | Immutable venv + versioned configs | ✅ |
| Audit trail loss | Auditd + journalctl logging | ✅ |

---

## Next Steps (Day 4 Preview)

- **If TLS cert ready (Let's Encrypt Day 3 evening)**: Deploy cert, test HTTPS
- **If TLS cert pending**: Use self-signed cert for testing, swap when LE ready
- **Baseline performance measurement** (load test 100 concurrent requests)
- **Day 4 objective**: Performance validation + TLS verification

---

**Day 3 Status**: 🟡 IN PROGRESS  
**Estimated Completion**: March 31, 2026 (EOD, ~7-8 hours from start)  
**Security Focus**: 100% — All configurations prioritize security first, no shortcuts
