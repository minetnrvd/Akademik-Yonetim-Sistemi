# SSH Hardening Runbook

**Date**: March 31, 2026  
**Day**: 3 (40-Day Production Plan)  
**Focus**: Secure remote access, eliminate password vulnerability

---

## Executive Summary

SSH is the primary attack vector. **Zero-tolerance policy**: 
- No password authentication
- No root login
- Key-based ed25519 only
- Max 3 failed attempts before lockout
- Audit all connections

---

## Phase 1: Generate SSH Keypair (Local Machine)

### Step 1: Create ed25519 Key (Strongest)

```bash
# On your LOCAL machine (not on server)
ssh-keygen -t ed25519 -f ~/.ssh/qr-attendance-prod -C "qr-attendance-prod" -N ""

# Output:
# Generating public/private ed25519 key pair.
# Your identification has been saved in /home/user/.ssh/qr-attendance-prod
# Your public key has been saved in /home/user/.ssh/qr-attendance-prod.pub
# The key fingerprint is: SHA256:... qr-attendance-prod
```

### Step 2: Validate Generated Keys

```bash
# List keys
ls -la ~/.ssh/qr-attendance-prod*

# Permissions check (must be 600)
ls -l ~/.ssh/qr-attendance-prod  # Should be: -rw------- (600)
ls -l ~/.ssh/qr-attendance-prod.pub  # Should be: -rw-r--r-- (644)

# View public key
cat ~/.ssh/qr-attendance-prod.pub
# Output: ssh-ed25519 AAAAC3NzaC1lZDI1... qr-attendance-prod

# Backup private key (SECURELY)
# - Store in password-protected safe
# - Never commit to git
# - Never email unencrypted
```

### Step 3: Add Key to SSH Config (Optional, for convenience)

```bash
# Create SSH config for easier connection
cat >> ~/.ssh/config << 'EOF'
Host qr-attendance-prod
    HostName qr-attendance.example.com
    User ubuntu
    IdentityFile ~/.ssh/qr-attendance-prod
    AddKeysToAgent yes
    IdentitiesOnly yes
EOF

# Now you can connect with:
# ssh qr-attendance-prod  (instead of full command)
```

---

## Phase 2: Deploy Public Key to Server (First SSH)

**PROCEDURE**: Connect with temp password/OOB, deploy public key, disable password

### Step 2a: Initial SSH Connection (Temporary)

```bash
# Connect with temporary password (provided by infrastructure team)
ssh -i ~/.ssh/qr-attendance-prod ubuntu@qr-attendance.example.com

# Or if password auth still enabled (temporary only):
ssh ubuntu@qr-attendance.example.com
# Enter password provided by infra team
```

### Step 2b: Deploy Public Key

```bash
# Once connected to server, create .ssh directory
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add your public key to authorized_keys
cat >> ~/.ssh/authorized_keys << 'EOF'
ssh-ed25519 AAAAC3NzaC1lZDI1... qr-attendance-prod
EOF

# Set permissions (critical)
chmod 600 ~/.ssh/authorized_keys

# Verify
cat ~/.ssh/authorized_keys  # Should show your key
```

### Step 2c: Test New SSH Connection

**IMPORTANT**: Keep first connection open; test new key in second terminal

```bash
# Terminal 1: Keep original connection alive
# (do not close yet)

# Terminal 2: Test new key-based connection
ssh -i ~/.ssh/qr-attendance-prod ubuntu@qr-attendance.example.com

# If successful:
# - Login succeeded without password ✅
# - Return to Terminal 1, close it
```

---

## Phase 3: Disable Password Authentication

### Step 3a: Edit SSH Configuration

```bash
# SSH config file
sudo nano /etc/ssh/sshd_config

# Find and modify these lines:

# OLD:
#PasswordAuthentication yes

# NEW:
PasswordAuthentication no

# OLD:
#PubkeyAuthentication yes

# NEW:
PubkeyAuthentication yes

# OLD:
#PermitRootLogin prohibit-password

# NEW:
PermitRootLogin no

# OLD:
#PermitEmptyPasswords no

# NEW:
PermitEmptyPasswords no

# NEW (add these if not present):
MaxAuthTries 3
MaxSessions 5
```

### Step 3b: Add Security Settings

```bash
# Append security settings
sudo tee -a /etc/ssh/sshd_config << 'EOF'

# Security hardening
Protocol 2
AddressFamily any
ListenAddress 0.0.0.0
ListenAddress ::

# Authentication
PubkeyAuthentication yes
PasswordAuthentication no
PermitRootLogin no
PermitEmptyPasswords no
ChallengeResponseAuthentication no
UsePAM yes

# Security limits
MaxAuthTries 3
MaxSessions 5
MaxStartups 10:30:60

# Timeouts
ClientAliveInterval 300
ClientAliveCountMax 3

# Logging
SyslogFacility AUTH
LogLevel VERBOSE

# Session settings
TCPKeepAlive yes
X11Forwarding no
PrintMotd no
PrintLastLog yes
EOF
```

### Step 3c: Verify Configuration Syntax

```bash
# Critical: syntax check before reload
sudo sshd -t

# Output should be empty (no errors)
# If errors: fix immediately before proceeding
```

### Step 3d: Reload SSH Daemon

```bash
# Reload SSH (does not disconnect existing connections)
sudo systemctl reload ssh

# Or if using older system:
sudo service ssh restart
```

### Step 3e: Verify Changes Took Effect

```bash
# Check that password auth is disabled
sudo sshd -T | grep passwordauth

# Output: passwordauthentication no ✅

# Check pubkey auth still enabled
sudo sshd -T | grep pubkeyauthentication

# Output: pubkeyauthentication yes ✅
```

---

## Phase 4: Fail2ban Setup (Brute-Force Protection)

### Step 4a: Install Fail2ban

```bash
sudo apt install -y fail2ban

# Start service
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Verify running
sudo systemctl status fail2ban
```

### Step 4b: Configure SSH Jail

```bash
# Create local config (overrides defaults)
sudo nano /etc/fail2ban/jail.local

# Paste:
cat << 'EOF' | sudo tee /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600  # 1 hour ban
findtime = 600  # Within 10 minutes
maxretry = 3    # 3 failed attempts triggers ban
destemail = admin@example.com
sendername = Fail2Ban
action = %(action_mwl)s  # Email alert + auto-unban

[ssh]
enabled = true
port = 22
logpath = /var/log/auth.log
backend = systemd  # Use journal if available

[recidive]
enabled = true
logpath = /var/log/fail2ban.log
action = %(action_mwl)s
bantime = 604800  # 7 days for repeat offenders
findtime = 86400  # Within 24 hours
maxretry = 2
EOF
```

### Step 4c: Test Fail2ban

```bash
# Reload fail2ban
sudo systemctl restart fail2ban

# Check active jails
sudo fail2ban-client status

# Output:
# |- Number of jail:      1
# `- Jail list:    ssh

# Check SSH jail details
sudo fail2ban-client status ssh

# Output:
# |- Filter name (File): sshd
# |- Number of actions:  1
# |- jail is currently idle
# `- Actions: iptables-blocktype
```

### Step 4d: Simulate Failed Attempts (Test)

```bash
# From DIFFERENT machine, attempt SSH with wrong key
ssh -i ~/.ssh/wrong_key ubuntu@qr-attendance.example.com

# Repeat 3 times (3rd attempt should be blocked)

# Check fail2ban logs
sudo tail -f /var/log/fail2ban.log

# Expected:
# Ban 203.0.113.45 (source IP)
# [ssh] Increase ban time to 7200
```

---

## Phase 5: SSH Monitoring & Audit

### Step 5a: Enable SSH Audit Logging

```bash
# SSH logs go to /var/log/auth.log
# But we want persistent, structured logging

# Edit sshd_config for verbose logging
sudo sed -i 's/^#LogLevel INFO/LogLevel VERBOSE/' /etc/ssh/sshd_config
sudo systemctl reload ssh

# Tail logs to verify
sudo tail -f /var/log/auth.log

# Example output:
# sshd[1234]: Connection from 203.0.113.45 port 54321
# sshd[1234]: Received publickey for ubuntu from 203.0.113.45
# sshd[1234]: Accepted publickey for ubuntu from 203.0.113.45
```

### Step 5b: Configure Auditd for SSH Monitoring

```bash
# Audit all SSH configuration changes
sudo cat >> /etc/audit/rules.d/ssh.rules << 'EOF'
-w /etc/ssh/ -p wa -k ssh_config_change
-w /home -p wa -k ssh_key_changes
-a always,exit -F arch=b64 -S execve -F path=/usr/sbin/sshd -k ssh_daemon_start
EOF

# Reload auditd
sudo service auditd restart

# Query SSH events
sudo ausearch -k ssh_config_change
```

### Step 5c: Create SSH Access Alert Script (Optional, for ops team)

```bash
#!/bin/bash
# /usr/local/bin/ssh-alert.sh
# Monitor SSH access and alert on suspicious patterns

failed_attempts=$(grep "Failed password" /var/log/auth.log | wc -l)
failed_pubkey=$(grep "Accepted publickey" /var/log/auth.log | wc -l)
root_attempts=$(grep "root" /var/log/auth.log | grep "Failed" | wc -l)

if [ $failed_attempts -gt 10 ]; then
    echo "ALERT: High failed SSH attempts: $failed_attempts" | mail -s "SSH Alert" admin@example.com
fi

if [ $root_attempts -gt 0 ]; then
    echo "ALERT: Root login attempt detected" | mail -s "Critical SSH Alert" admin@example.com
fi
```

---

## SSH Hardening Verification Checklist

- [ ] **Key Generation**:
  - [ ] ed25519 key generated locally
  - [ ] Private key permissions: 600
  - [ ] Public key deployed to server ~/.ssh/authorized_keys

- [ ] **SSH Configuration**:
  - [ ] PasswordAuthentication = no
  - [ ] PubkeyAuthentication = yes
  - [ ] PermitRootLogin = no
  - [ ] PermitEmptyPasswords = no
  - [ ] MaxAuthTries = 3
  - [ ] sshd_config syntax verified (sshd -t)

- [ ] **SSH Service**:
  - [ ] SSH reloaded (systemctl reload ssh)
  - [ ] Key-based login works
  - [ ] Password login blocked
  - [ ] Root login blocked

- [ ] **Brute-Force Protection**:
  - [ ] Fail2ban installed
  - [ ] SSH jail configured
  - [ ] Ban on 3 failures for 1 hour
  - [ ] Recidive (7-day ban) configured
  - [ ] Logs monitored

- [ ] **Audit & Monitoring**:
  - [ ] auth.log being written
  - [ ] auditd tracking SSH changes
  - [ ] SSH verbose logging enabled

---

## Troubleshooting

### Q: "Permission denied (publickey)"

A: Check:
1. Private key permissions: `chmod 600 ~/.ssh/qr-attendance-prod`
2. Public key on server: `cat ~/.ssh/authorized_keys` should contain your key
3. Server SSH config: `sudo sshd -T | grep pubkeyauthentication` should be `yes`

### Q: "Locked out after reload"

A: If you can't connect after sshd_config changes:
1. Use console/OOB access (KVM, EC2 console, etc.)
2. Revert changes: `sudo cp /etc/ssh/sshd_config.bak /etc/ssh/sshd_config`
3. Reload: `sudo systemctl reload ssh`
4. Verify: `sudo sshd -t`
5. Retry changes more carefully

### Q: "Fail2ban keeps banning me"

A: If you're testing and keep getting blocked:
1. Use different IP address for testing
2. Wait ban timeout (default 1 hour)
3. Or unban manually: `sudo fail2ban-client set ssh unbanip 203.0.113.45`

---

## Security Lifecycle

**Weekly**: Review fail2ban logs for attack patterns  
**Monthly**: Rotate SSH keys (generate new pair, deploy, revoke old)  
**Quarterly**: Security audit (check sshd_config against latest best practices)  
**Annually**: Penetration test (ethical hacker attempts SSH break-in)

---

**SSH Hardening Status**: SECURITY-FIRST, ZERO-TOLERANCE
