# TLS Certificate Status & Timeline

**Date**: March 30, 2026  
**Day**: 2 (40-Day Production Plan)  
**Decision**: **Let's Encrypt selected for HTTPS/TLS**

---

## Executive Decision

| Factor | Recommendation | Rationale |
|--------|-----------------|-----------|
| **Certificate Authority** | **Let's Encrypt** | Free, fast, automated, production-grade |
| **Expected Issuance Time** | **~1-5 minutes** (after DNS validation) | Industry-fastest for automated certs |
| **Renewal Automation** | **Certbot** (with cron) | Fully automated, zero-touch |
| **Fallback Option** | **Self-signed cert** (Days 2-3 if blocked) | Can deploy immediately, replaced with LE cert when ready |
| **Integration** | **Nginx-managed** | Standard nginx + LE pattern, excellent community support |

---

## Let's Encrypt Selection Rationale

### Comparison: Let's Encrypt vs Commercial CAs

| Criterion | Let's Encrypt | Commercial CA (DigiCert, Sectigo) |
|-----------|---------------|----------------------------------|
| **Cost** | FREE | $10-300/year |
| **Issuance Time** | ~1-5 min (automated) | 1-5 business days (manual) |
| **Renewals** | Automated (costless) | Manual renewal, costs repeat |
| **Certificate Validity** | 90 days | 1-3 years |
| **Validation Method** | DNS/HTTP challenge (automated) | Phone/email verification (manual) |
| **Production Grade** | YES (used by major sites) | YES (traditional) |
| **90-day Rotation** | Ideal for DevOps automation | Overkill for single cert |
| **Browser Trust** | Full (90%+ of web) | Full |
| **Learning Curve** | Low (certbot is simple) | Low (commercial CAs have web UI) |

**Winner**: Let's Encrypt ✅ (especially for DevOps 40-day ramp — automation > complexity)

---

## Implementation Timeline

### Phase 1: Pre-Certificate (Day 2-3, ~1-2 hours)

**Day 2 (Today) Goals**:
1. ✅ Confirm target domain name
2. ✅ Identify DNS provider (GoDaddy, Cloudflare, etc.)
3. ✅ Prepare DNS access credentials
4. ✅ Plan DNS change (5-minute window during Day 3)

**Prerequisite Data** (needed to proceed):
```
Domain name: ____________  (e.g., qr-attendance.example.com)
DNS provider: ___________  (e.g., Cloudflare)
DNS admin contact: _______  (who can update DNS records)
Production server IP: ____  (for DNS A record)
```

**Day 3 (Tomorrow) Goals**:
1. SSH into production server (or staging if Path B)
2. Install certbot: `apt install certbot python3-certbot-nginx`
3. Update DNS if needed (A record or CNAME pointing to server IP)
4. Run: `certbot certonly --dns-cloudflare -d qr-attendance.example.com`
5. Certificate obtained in ~1-5 minutes ✅

---

### Phase 2: Certificate Deployment (Day 3-4)

**Day 3 Evening**:
- [ ] Certificate obtained from Let's Encrypt
- [ ] Files available at:
  - `/etc/letsencrypt/live/qr-attendance.example.com/fullchain.pem`
  - `/etc/letsencrypt/live/qr-attendance.example.com/privkey.pem`

**Day 4 (Tomorrow Evening)**:
- [ ] Configure Nginx to use TLS certs
- [ ] Test HTTPS access: `curl https://qr-attendance.example.com`
- [ ] Verify certificate validity: `openssl s_client -connect qr-attendance.example.com:443`
- [ ] Test in browser (check for SSL warnings)

---

### Phase 3: Auto-Renewal Setup (Day 4-5)

**Goal**: Ensure certificate auto-renews before 90-day expiration

**Cron Job** (systemd timer or crontab):
```bash
# Renewal command (runs every Sunday at 3 AM)
0 3 * * 0 certbot renew --quiet && systemctl reload nginx

# Add to crontab:
crontab -e
# Paste above line
```

**Verification**:
```bash
# Dry-run renewal (no actual issuance)
sudo certbot renew --dry-run

# Check certificate expiration
sudo openssl x509 -in /etc/letsencrypt/live/qr-attendance.example.com/fullchain.pem -noout -enddate
# Output: notAfter=Jun 28 12:34:56 2026 GMT
```

---

## Deployment Steps (Detailed for Day 3-4)

### Step 1: Pre-Deployment Checklist (Day 2-3, now)

```bash
# Verify production server accessible
ssh ubuntu@qr-attendance-prod  # or RDP if Windows

# Verify Python + Flask already running
python3 --version  # should be 3.11+
pip list | grep -i flask  # should exist

# Verify Nginx not yet installed (we'll install Day 4)
which nginx  # should return nothing (not installed yet)
```

---

### Step 2: certbot Installation (Day 3)

**For Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx
```

**For CentOS/RHEL**:
```bash
sudo yum install certbot python3-certbot-nginx
```

**For Windows** (if applicable):
```
# Windows doesn't have native certbot
# Contingency: use Acme.NET (_recommended_)
# Or use WSL2 for certbot
# Or: pre-generate cert on Linux, copy files to Windows
```

---

### Step 3: DNS Configuration (Day 3, 5-minute window)

**Option A: A Record (Recommended)**
```
Domain: qr-attendance.example.com
Record Type: A
Value: <production_server_ip>  (e.g., 192.168.1.100 or 203.0.113.42)
TTL: 300 (5 minutes, temporary)
```

**Option B: CNAME**
```
Domain: qr-attendance.example.com
Record Type: CNAME
Value: qr-attendance-prod.example.com  (must have corresponding A record)
```

**Step 3a**: Login to DNS provider dashboard  
**Step 3b**: Update/create DNS record  
**Step 3c**: Wait 2-5 minutes for propagation  
**Step 3d**: Test resolution:
```bash
nslookup qr-attendance.example.com
# Should return production server IP
```

---

### Step 4: Certificate Issuance (Day 3, ~1 minute)

```bash
# Interactive mode (asks which domain, validates, issues)
sudo certbot certonly --nginx -d qr-attendance.example.com

# Or: non-interactive if DNS already prepared
sudo certbot certonly --dns-cloudflare -d qr-attendance.example.com -n

# Or: HTTP challenge (alternate, requires port 80 open to internet)
sudo certbot certonly --standalone -d qr-attendance.example.com
```

**Expected Output**:
```
Congratulations! Your certificate and chain have been saved at:
  /etc/letsencrypt/live/qr-attendance.example.com/fullchain.pem
Your key file has been saved at:
  /etc/letsencrypt/live/qr-attendance.example.com/privkey.pem
This certificate expires on [DATE].
```

---

### Step 5: Nginx Configuration (Day 4)

**File**: `/etc/nginx/sites-available/qr-attendance` (created earlier with WSGI decision)

```nginx
upstream gunicorn_qr_attendance {
    server 127.0.0.1:5000;
}

# HTTP → HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name qr-attendance.example.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name qr-attendance.example.com;

    # TLS certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/qr-attendance.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/qr-attendance.example.com/privkey.pem;

    # TLS configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/qr-attendance_access.log combined;
    error_log /var/log/nginx/qr-attendance_error.log;

    # Proxy to Gunicorn
    location / {
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

    # Static files
    location /static/ {
        alias /opt/qr-attendance/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

**Deploy and Test**:
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/qr-attendance /etc/nginx/sites-enabled/qr-attendance

# Check syntax
sudo nginx -t  # should output "syntax is ok"

# Reload Nginx
sudo systemctl reload nginx

# Verify HTTPS working
curl -I https://qr-attendance.example.com  # should return 200 OK

# Check certificate details
openssl s_client -connect qr-attendance.example.com:443 -showcerts

# Browser test: https://qr-attendance.example.com/health
```

---

## Contingency: Self-Signed Certificate (Fallback)

**When to activate**: DNS delays, Let's Encrypt downtime, or other blockers

**Timeline**: 5 minutes (can deploy immediately)

```bash
# Generate self-signed cert valid for 365 days
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/qr-attendance-selfsigned.key \
  -out /etc/ssl/certs/qr-attendance-selfsigned.crt

# Use self-signed in Nginx config (temporary):
ssl_certificate /etc/ssl/certs/qr-attendance-selfsigned.crt;
ssl_certificate_key /etc/ssl/private/qr-attendance-selfsigned.key;

# Reload Nginx
sudo systemctl reload nginx

# Note: browser will show "untrusted certificate" warning 
# (acceptable for internal testing, Days 2-3 only)
```

**Replacement Plan** (when Let's Encrypt cert ready):
1. Obtain Let's Encrypt cert (as outlined above)
2. Update Nginx config (change ssl_certificate path)
3. Reload Nginx (zero downtime)
4. Self-signed cert decommissioned

---

## ACME Client Automation (Alternative to certbot)

**If Days 2-3 need to support Windows production server**:

Use **Posh-ACME** (PowerShell ACME client) instead of certbot:

```powershell
# Install module
Install-Module Posh-ACME

# Get certificate
New-PACertificate -Domain qr-attendance.example.com -AcceptTOS -Contact admin@example.com

# Save cert to PFX (Windows native format)
Export-PACertificate -CertName qr-attendance.example.com -PfxPassWord (ConvertTo-SecureString "password123" -AsPlainText)

# Import PFX to Windows Certificate Store
Import-PfxCertificate -FilePath .\cert.pfx -CertStoreLocation Cert:\LocalMachine\My
```

Then configure IIS or HyperV reverse proxy to use cert.

---

## Certificate Monitoring & Alerts

**Goal**: Never miss renewal deadline

**Implementation** (Days 21-30 with CI/CD automation):
```bash
# Alert if cert expires in < 7 days
openssl x509 -in /etc/letsencrypt/live/qr-attendance.example.com/fullchain.pem -noout -dates | \
  awk -F= '$1=="notAfter" {print $2}' | \
  xargs date -f - +%s | \
  awk '{if ($1 - systime() < 604800) print "ALERT: Certificate expires in less than 7 days"}'
```

---

## Timeline Summary

| Day | Task | Status | Owner |
|-----|------|--------|-------|
| Day 2 (Today) | Collect domain/DNS info | ✅ TODO | Tech Lead |
| Day 3 | Certbot install, cert issuance | TODO | Infra Lead |
| Day 4 | Nginx TLS config, test HTTPS | TODO | Infra Lead |
| Day 4-5 | Auto-renewal setup, verification | TODO | Infra Lead |
| Days 6-10 | Monitor renewal, keep running | TODO | Ops |

---

## Success Criteria (Day 4 Closure)

- [ ] Let's Encrypt certificate obtained (or self-signed fallback deployed)
- [ ] HTTPS accessible: `https://qr-attendance.example.com/health` → 200 OK
- [ ] Browser shows valid certificate (green lock, no warnings)
- [ ] Auto-renewal scheduled (cron job or systemd timer)
- [ ] Certificate expiration monitored (alert if < 30 days until renewal)

---

## Appendix: Troubleshooting

**Q: certbot fails with "DNS challenge failed"**  
A: Check DNS propagation → wait 5-10 min → retry

**Q: "Connection refused on port 443"**  
A: Firewall blocking → update firewall rules → test with telnet

**Q: Browser shows "HSTS error"**  
A: SSL-Labs reports HSTS error → update Nginx HSTS header or HSTS preload

**Q: Certificate auto-renewal not running**  
A: Check cron logs → `sudo journalctl -u certbot` → verify renewal command

---

**Decision Date**: March 30, 2026  
**Expected Cert Issuance**: March 31, 2026 (Day 3 evening, if DNS ready)  
**Certificate Validity**: 90 days (auto-renewed)  
**Review Date**: Day 5 (post-HTTPS verification)
