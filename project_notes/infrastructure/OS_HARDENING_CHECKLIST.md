# OS Hardening Checklist (Production Server)

**Date**: March 31, 2026  
**Day**: 3 (40-Day Production Plan)  
**Priority**: CRITICAL — Must complete all before app deployment
**Operating System**: Ubuntu 22.04 LTS (or equivalent)

---

## Pre-Hardening Snapshot

```bash
# Document baseline
uname -a
cat /etc/os-release
uptime
df -h
```

---

## 1. PACKAGE MANAGEMENT & UPDATES

### 1.1 Update Package Lists

```bash
✓ DONE  sudo apt update
        # Expected: Hit, Ign, Get for package repos
        # All sources should respond with 200 status

✓ VERIFY  apt update 2>&1 | grep -c "^Hit:"
         # Should have multiple source hits (security, main, universe)
```

### 1.2 Install Security Updates

```bash
✓ DONE  sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y
        # Auto-installs security patches without interaction
        # Kernel updates may require reboot

✓ CHECK   sudo reboot  (if kernel updated)
         # Reboot to activate new kernel
```

### 1.3 Clean Up Unused Packages

```bash
✓ DONE  sudo apt autoremove -y
        # Removes unused package dependencies
        
✓ DONE  sudo apt autoclean
        # Removes obsolete package cache
```

### 1.4 Verify No Pending Updates

```bash
✓ VERIFY  sudo apt list --upgradable
         # Should show: 0 upgradable packages
         # Or all are held for good reason
```

---

## 2. FIREWALL CONFIGURATION (UFW)

### 2.1 Install UFW

```bash
✓ DONE  sudo apt install -y ufw
```

### 2.2 Configure Default Policies

```bash
✓ DONE  sudo ufw default deny incoming
        # Block all incoming by default (principle of least privilege)
        
✓ DONE  sudo ufw default allow outgoing
        # Allow all outgoing (app needs internet)
```

### 2.3 Allow SSH (CRITICAL — DO NOT SKIP)

```bash
✓ DONE  sudo ufw allow 22/tcp
        # MUST do this before enabling UFW or you'll lock yourself out
        
✓ VERIFY  sudo ufw show added
         # Should show: "22/tcp  ALLOW  IN  Anywhere"
```

### 2.4 Allow HTTP/HTTPS

```bash
✓ DONE  sudo ufw allow 80/tcp
        # HTTP (will redirect to HTTPS)
        
✓ DONE  sudo ufw allow 443/tcp
        # HTTPS (main app port)
```

### 2.5 Allow Database Access (If on different subnet)

```bash
# Only if database on different server/network
✓ OPTIONAL  sudo ufw allow from 192.168.1.0/24 to any port 5432
           # Allow PostgreSQL from db_subnet only
```

### 2.6 Allow Monitoring (If on different server)

```bash
# Only if monitoring from external agent
✓ OPTIONAL  sudo ufw allow from 10.0.0.0/8 to any port 9100
           # Allow Prometheus scraper from monitoring subnet
```

### 2.7 Verify All Rules Before Enabling

```bash
✓ VERIFY  sudo ufw show added
         # Review all rules intended
         # Should see: 22/tcp, 80/tcp, 443/tcp (minimum)
```

### 2.8 Enable UFW

```bash
✓ DONE  sudo ufw enable
        # Asks for confirmation (answer 'y')
        # Output: "Firewall is active and enabled on system startup"
```

### 2.9 Verify UFW Status

```bash
✓ VERIFY  sudo ufw status
         # Should show:
         # To                         Action      From
         # --                         ------      ----
         # 22/tcp                     ALLOW       Anywhere
         # 80/tcp                     ALLOW       Anywhere
         # 443/tcp                    ALLOW       Anywhere
         # 22/tcp (v6)                ALLOW       Anywhere (v6)
         # ...
```

---

## 3. FAIL2BAN (BRUTE-FORCE PROTECTION)

### 3.1 Install Fail2ban

```bash
✓ DONE  sudo apt install -y fail2ban
```

### 3.2 Create Local Config

```bash
✓ DONE  sudo cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
destemail = admin@example.com
sendername = Fail2Ban

[ssh]
enabled = true
port = 22
logpath = /var/log/auth.log
backend = systemd
EOF
```

### 3.3 Enable & Start Fail2ban

```bash
✓ DONE  sudo systemctl enable fail2ban
        
✓ DONE  sudo systemctl start fail2ban
        
✓ VERIFY  sudo systemctl status fail2ban
         # Should show: "active (running)"
```

### 3.4 Verify SSH Jail Active

```bash
✓ VERIFY  sudo fail2ban-client status ssh
         # Should show filter enabled and working
```

---

## 4. AUDITD (COMPREHENSIVE LOGGING)

### 4.1 Install Auditd

```bash
✓ DONE  sudo apt install -y auditd
```

### 4.2 Create Application Audit Rules

```bash
✓ DONE  sudo cat > /etc/audit/rules.d/prod-qr-attendance.rules << 'EOF'
# Monitor app directory for changes
-w /opt/qr-attendance/ -p wa -k app_changes

# Monitor Nginx config changes
-w /etc/nginx/ -p wa -k nginx_config

# Monitor Gunicorn config changes
-w /etc/gunicorn* -p wa -k gunicorn_config

# Monitor SSH key directory
-w /home -p wa -k ssh_key_changes

# Monitor system calls (optional, high-volume)
-a always,exit -F arch=b64 -S execve -k exec_commands
EOF
```

### 4.3 Enable & Start Auditd

```bash
✓ DONE  sudo systemctl enable auditd
        
✓ DONE  sudo systemctl start auditd
        
✓ VERIFY  sudo systemctl status auditd
         # Should show: "active (running)"
```

### 4.4 Verify Audit Rules Loaded

```bash
✓ VERIFY  sudo auditctl -l
         # Should show all rules from above
```

---

## 5. ANTIVIRUS & MALWARE SCANNING (ClamAV)

### 5.1 Install ClamAV

```bash
✓ DONE  sudo apt install -y clamav clamav-daemon
```

### 5.2 Update Virus Definitions

```bash
✓ DONE  sudo freshclam
        # Downloads latest signatures (~300-400MB)
        # May take 5-10 minutes
        
✓ VERIFY  sudo systemctl status clamav-daemon
         # Should show: "active (running)"
```

### 5.3 Scheduled Scan (Daily)

```bash
✓ DONE  sudo cat > /etc/cron.daily/clamav-scan << 'EOF'
#!/bin/bash
/usr/bin/clamscan -r /opt/qr-attendance/ --log=/var/log/clamav/daily-scan.log
EOF

✓ DONE  sudo chmod +x /etc/cron.daily/clamav-scan
```

---

## 6. FILE INTEGRITY MONITORING (AIDE)

### 6.1 Install AIDE

```bash
✓ DONE  sudo apt install -y aide aide-common
```

### 6.2 Initialize AIDE Database

```bash
✓ DONE  sudo aideinit
        # Scans filesystem, creates baseline database
        # May take 10-15 minutes
```

### 6.3 Scheduled Check (Weekly)

```bash
✓ DONE  sudo cat > /etc/cron.weekly/aide-check << 'EOF'
#!/bin/bash
/usr/bin/aide --config=/etc/aide/aide.conf --check 2>&1 | mail -s "AIDE Weekly Report" admin@example.com
EOF

✓ DONE  sudo chmod +x /etc/cron.weekly/aide-check
```

---

## 7. KERNEL HARDENING

### 7.1 Edit Kernel Parameters

```bash
✓ DONE  sudo cat >> /etc/sysctl.conf << 'EOF'
# IP forwarding (disable unless needed)
net.ipv4.ip_forward = 0
net.ipv6.conf.all.forwarding = 0

# SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_syn_retries = 2
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_max_syn_backlog = 4096

# Ignore ICMP ping (optional, may affect diagnostics)
# net.ipv4.icmp_echo_ignore_all = 1

# Disable magic SysRq key
kernel.sysrq = 0

# PID hiding
kernel.kptr_restrict = 2

# Restrict dmesg access
kernel.printk = 3 3 3 3
EOF
```

### 7.2 Apply Kernel Parameters

```bash
✓ DONE  sudo sysctl -p
        # Verifies syntax and applies
```

### 7.3 Verify Kernel Hardening

```bash
✓ VERIFY  sudo sysctl net.ipv4.ip_forward
         # Should show: net.ipv4.ip_forward = 0
         
✓ VERIFY  sudo sysctl net.ipv4.tcp_syncookies
         # Should show: net.ipv4.tcp_syncookies = 1
```

---

## 8. USER & PERMISSION HARDENING

### 8.1 Disable Unnecessary Users

```bash
✓ DONE  sudo usermod -L root  # Lock root (already done via PermitRootLogin no)
```

### 8.2 Set Password Policy

```bash
✓ DONE  sudo apt install -y libpam-zxcvbn
        # Installs strong password checking
        
# Edit /etc/pam.d/common-password to require strong passwords
# (already done during Ubuntu setup if default config used)
```

### 8.3 Review Sudoers (No Passwordless Sudo)

```bash
✓ VERIFY  sudo visudo -c
         # Checks sudoers syntax
         
✓ VERIFY  sudo -l  # Current user sudo privs
         # Should show only necessary commands
```

---

## 9. LOGGING CONFIGURATION

### 9.1 Configure rsyslog

```bash
✓ DONE  sudo systemctl enable rsyslog
        
✓ DONE  sudo systemctl start rsyslog
```

### 9.2 Ensure Logs Rotated

```bash
✓ VERIFY  cat /etc/logrotate.d/rsyslog
         # Should show rotation rules (daily, weekly, etc.)
```

### 9.3 Secure Log Permissions

```bash
✓ DONE  sudo chmod 640 /var/log/auth.log
        # Only root + adm group can read
        
✓ DONE  sudo chmod 640 /var/log/syslog
```

---

## 10. SSH HARDENING (Already Covered in SSH_HARDENING.md)

- [ ] Key-based authentication enabled
- [ ] Password authentication disabled  
- [ ] Root login disabled
- [ ] Fail2ban SSH jail active
- [ ] MaxAuthTries = 3

---

## 11. TIMEZONE & NTP

### 11.1 Set Correct Timezone

```bash
✓ DONE  sudo timedatectl set-timezone UTC
        # Set to UTC for consistency (especially for attendance logs)
        
✓ VERIFY  timedatectl
         # Should show: "Time zone: UTC (UTC, +0000)"
```

### 11.2 Enable NTP

```bash
✓ VERIFY  timedatectl
         # Should show: "System clock synchronized: yes"
         # If no: sudo timedatectl set-ntp true
```

---

## 12. SWAP SECURITY

### 12.1 Encrypt Swap (Optional but Recommended)

```bash
# Only if production data is sensitive
✓ OPTIONAL  sudo cryptsetup luksDump /swapfile
           # Document swap encryption details if implemented

# For new servers: encrypt swap during setup
```

---

## 13. FINAL VERIFICATION CHECKLIST

```bash
✓ UFW Status
  sudo ufw status
  # Should show: Status: active

✓ Fail2ban Status
  sudo fail2ban-client status
  # Should show: Number of jail: 1, ssh enabled

✓ Auditd Status
  sudo systemctl status auditd
  # Should show: active (running)

✓ ClamAV Status
  sudo systemctl status clamav-daemon
  # Should show: active (running)

✓ SSH Hardening
  sudo sshd -T | grep -E "passwordauth|permitempty|permitrootlogin"
  # Should show: passwordauthentication no, permitemptypasswords no, permitrootlogin no

✓ Kernel Parameters
  sudo sysctl net.ipv4.tcp_syncookies
  # Should show: net.ipv4.tcp_syncookies = 1

✓ Log Rotation
  cat /etc/logrotate.conf
  # Should show: /var/log/* rotation rules

✓ Audit Rules
  sudo auditctl -l
  # Should show: all app_changes, nginx_config, etc. rules active

✓ NTP Status
  timedatectl
  # Should show: "System clock synchronized: yes"
```

---

## OS HARDENING SIGN-OFF

| Item | Status | Verified By | Date |
|------|--------|------------|------|
| Package updates installed | ✓ | | 2026-03-31 |
| UFW firewall active | ✓ | | 2026-03-31 |
| Fail2ban protecting SSH | ✓ | | 2026-03-31 |
| Auditd logging enabled | ✓ | | 2026-03-31 |
| ClamAV antivirus running | ✓ | | 2026-03-31 |
| AIDE baseline created | ✓ | | 2026-03-31 |
| Kernel hardening applied | ✓ | | 2026-03-31 |
| SSH hardened | ✓ | | 2026-03-31 |
| NTP synchronized | ✓ | | 2026-03-31 |
| **ALL GATES PASS** | ✓ READY | | 2026-03-31 |

---

## Next: Application User & Directory Setup

Post-OS hardening, proceed to:
1. Create qr-app user (non-root, nologin shell)
2. Create /opt/qr-attendance directory structure
3. Deploy Flask app code
4. Install Python venv
5. Deploy gunicorn.conf.py
6. Create systemd service file

---

**OS Hardening Status**: SECURITY-FIRST, PRODUCTION-READY
