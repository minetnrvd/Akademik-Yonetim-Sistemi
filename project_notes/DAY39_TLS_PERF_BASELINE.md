# Day 39 (40-Day Plan Day 4): TLS Deployment & Performance Baseline

**Date**: April 1, 2026 (Tuesday)  
**Program Phase**: Production Operationalization (Days 1-40)  
**Pillar**: 1 - Infrastructure Hardening (Days 1-10)  
**Security Focus**: Continue — TLS deployment, verify HTTPS integrity

**Prerequisite**: Day 3 completed; SSH hardening ✅, OS hardening ✅, Gunicorn + Nginx running

---

## Executive Summary

Day 4 focuses on **HTTPS deployment and performance baseline**. Verify Let's Encrypt certificate from Day 3 evening, deploy to production Nginx, and measure application latency under load (100 concurrent clients). Establish performance baseline for SLO monitoring and comparison vs Day 35.

---

## Day 4 Objectives (Sequenced)

### Objective 1: TLS Certificate Deployment (1-2 hours)

**Goal**: Activate HTTPS, verify certificate chain, enforce TLS 1.2+

#### Step 1a: Certificate Status Check

```bash
# Check if Let's Encrypt cert was obtained on Day 3 evening
sudo ls -la /etc/letsencrypt/live/qr-attendance.example.com/

# Expected output:
# total 20
# -rw-r--r-- 1 root root  fullchain.pem  (cert + CA chain)
# -rw-r--r-- 1 root root  privkey.pem    (private key)
# -rw-r--r-- 1 root root  cert.pem       (server cert only)
# -rw-r--r-- 1 root root  chain.pem      (CA chain only)

# If files NOT present: use self-signed fallback (created Day 3)
sudo ls -la /etc/ssl/certs/qr-attendance-selfsigned.crt
```

#### Step 1b: Nginx Configuration Update (If Cert Ready)

```bash
# Nginx config already points to Let's Encrypt cert location (Day 3)
# But now update to CONFIRMED paths

sudo nano /etc/nginx/sites-available/qr-attendance

# Verify:
# ssl_certificate /etc/letsencrypt/live/qr-attendance.example.com/fullchain.pem;
# ssl_certificate_key /etc/letsencrypt/live/qr-attendance.example.com/privkey.pem;

# If using self-signed (fallback):
# ssl_certificate /etc/ssl/certs/qr-attendance-selfsigned.crt;
# ssl_certificate_key /etc/ssl/private/qr-attendance-selfsigned.key;
```

#### Step 1c: Nginx Configuration Validation & Reload

```bash
# Verify syntax (CRITICAL before reload)
sudo nginx -t
# Expected: "nginx: the configuration file /etc/nginx/nginx.conf syntax is ok"

# Reload Nginx (zero-downtime)
sudo systemctl reload nginx

# Verify status
sudo systemctl status nginx
# Expected: "active (running)"
```

#### Step 1d: HTTPS Connectivity Test

```bash
# Test HTTPS from localhost
curl -I https://localhost/health
# Expected: 
# curl: (60) SSL certificate problem: self-signed certificate
# (normal if using self-signed OR Let's Encrypt with hostname mismatch)

# Test with domain name (if DNS resolvable)
curl -I https://qr-attendance.example.com/health
# Expected: HTTP/1.1 200 OK (if cert valid)

# Test HTTP redirect
curl -I http://qr-attendance.example.com/
# Expected: HTTP/1.1 301 Moved Permanently
# Location: https://qr-attendance.example.com/
```

#### Step 1e: Certificate Detailed Inspection

```bash
# Check Let's Encrypt cert (if deployed)
sudo openssl x509 -in /etc/letsencrypt/live/qr-attendance.example.com/fullchain.pem -noout -dates
# Expected:
# notBefore=Mar 31 12:34:56 2026 GMT
# notAfter=Jun 29 12:34:56 2026 GMT  (90 days from issuance)

# Check cert issuer
sudo openssl x509 -in /etc/letsencrypt/live/qr-attendance.example.com/fullchain.pem -noout -issuer
# Expected: issuer=C = US, O = Let's Encrypt, CN = R3

# Check certificate chain (should have Let's Encrypt + ISRG X1 root)
sudo openssl crl2pkcs7 -nocrl -certfile /etc/letsencrypt/live/qr-attendance.example.com/fullchain.pem | openssl pkcs7 -print_certs -noout

# Test TLS handshake (from remote)
openssl s_client -connect qr-attendance.example.com:443 -tls1_2
# Should succeed, show cert details and "Verify return code: 0 (ok)"
```

#### Step 1f: Security Header Verification

```bash
# Test all security headers present
curl -I https://qr-attendance.example.com/health

# Expected headers:
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Content-Security-Policy: ...
# Referrer-Policy: strict-origin-when-cross-origin
```

#### Step 1g: SSL Configuration Grade Check (Optional)

```bash
# Use SSL Labs online tool (if accessible)
# https://www.ssllabs.com/ssltest/analyze.html?d=qr-attendance.example.com

# Or local OpenSSL grade estimate:
echo | openssl s_client -connect qr-attendance.example.com:443 2>&1 | grep "Protocol"
# Expected: Protocol  : TLSv1.3 (or TLSv1.2 minimum)

# Check cipher suite strength
echo | openssl s_client -connect qr-attendance.example.com:443 2>&1 | grep "Cipher"
# Expected: Cipher Suite: TLS_AES_256_GCM_SHA384 (or similar A+ grade)
```

**Security Outcome**: 
- ✅ HTTPS enforced (HTTP redirects)
- ✅ TLS 1.2+ only
- ✅ Strong ciphers
- ✅ Security headers present
- ✅ Certificate chain valid

---

### Objective 2: Performance Baseline Measurement (2-3 hours)

**Goal**: Record p50/p95/p99 latencies for all endpoints; establish SLO baseline for monitoring

#### Step 2a: Create Performance Baseline Script

```bash
# Create performance testing script
cat > /opt/qr-attendance/perf_baseline_day4.py << 'EOF'
#!/usr/bin/env python3
"""
Day 4 Performance Baseline Measurement
Measures latency from production infrastructure
Records: avg, p50, p95, p99, max for each endpoint
"""

import requests
import time
import json
import statistics
from datetime import datetime
import ssl
import sys

# Configuration
BASE_URL = "https://qr-attendance.example.com"  # Production HTTPS

# Endpoints to test
ENDPOINTS = [
    ("/health", "GET", "health check"),
    ("/", "GET", "root/dashboard"),
    ("/login", "GET", "login form"),
]

# Test parameters
NUM_ITERATIONS = 50  # 50 requests per endpoint
CONCURRENT_CLIENTS = 1  # Sequential (single-threaded baseline)
TIMEOUT_SECONDS = 30

# SSL verification (skip if self-signed, True if Let's Encrypt)
VERIFY_SSL = True  # Set to False if using self-signed cert for testing

def measure_endpoint(url, method="GET", name=""):
    """Measure single endpoint latency"""
    print(f"\n{'='*60}")
    print(f"Endpoint: {name}")
    print(f"URL: {method} {url}")
    print(f"Iterations: {NUM_ITERATIONS}")
    print(f"{'='*60}")
    
    latencies = []
    errors = []
    
    for i in range(NUM_ITERATIONS):
        try:
            start = time.time()
            
            if method == "GET":
                response = requests.get(url, timeout=TIMEOUT_SECONDS, verify=VERIFY_SSL)
            elif method == "POST":
                response = requests.post(url, timeout=TIMEOUT_SECONDS, verify=VERIFY_SSL)
            
            elapsed_ms = (time.time() - start) * 1000
            latencies.append(elapsed_ms)
            
            status_ok = response.status_code == 200
            status_symbol = "✅" if status_ok else "❌"
            
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{NUM_ITERATIONS}] {elapsed_ms:.2f}ms {status_symbol}")
            
            if not status_ok:
                errors.append(f"HTTP {response.status_code}")
        
        except requests.exceptions.Timeout:
            print(f"  [{i+1}/{NUM_ITERATIONS}] TIMEOUT (>30s) ❌")
            errors.append("TIMEOUT")
        except Exception as e:
            print(f"  [{i+1}/{NUM_ITERATIONS}] ERROR: {str(e)} ❌")
            errors.append(str(e))
    
    # Calculate statistics
    if latencies:
        stats = {
            "endpoint": name,
            "url": url,
            "iterations": NUM_ITERATIONS,
            "successful": len(latencies),
            "failed": len(errors),
            "avg_ms": statistics.mean(latencies),
            "median_ms": statistics.median(latencies),
            "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)],
            "p99_ms": sorted(latencies)[int(len(latencies) * 0.99)],
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "stdev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0
        }
    else:
        stats = {
            "endpoint": name,
            "url": url,
            "iterations": NUM_ITERATIONS,
            "successful": 0,
            "failed": NUM_ITERATIONS,
            "error": "All requests failed"
        }
    
    print(f"\nResults for {name}:")
    print(f"  Successful: {stats['successful']}/{NUM_ITERATIONS}")
    if 'avg_ms' in stats:
        print(f"  Avg:   {stats['avg_ms']:.2f}ms")
        print(f"  p50:   {stats['median_ms']:.2f}ms")
        print(f"  p95:   {stats['p95_ms']:.2f}ms")
        print(f"  p99:   {stats['p99_ms']:.2f}ms")
        print(f"  Max:   {stats['max_ms']:.2f}ms")
        print(f"  StDev: {stats['stdev_ms']:.2f}ms")
    if errors:
        print(f"  Errors: {errors[:5]}")  # Show first 5 errors
    
    return stats

def main():
    print("\n" + "="*60)
    print("DAY 4: PRODUCTION PERFORMANCE BASELINE MEASUREMENT")
    print("="*60)
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print(f"Base URL: {BASE_URL}")
    print(f"SSL Verification: {VERIFY_SSL}")
    
    # Warmup (2 requests to each endpoint)
    print("\n[WARMUP PHASE] Discarding first 2 requests...")
    for endpoint, method, name in ENDPOINTS:
        url = BASE_URL + endpoint
        try:
            if method == "GET":
                requests.get(url, timeout=TIMEOUT_SECONDS, verify=VERIFY_SSL)
        except:
            pass
    
    # Measure each endpoint
    results = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "base_url": BASE_URL,
        "ssl_verified": VERIFY_SSL,
        "endpoints": []
    }
    
    for endpoint, method, name in ENDPOINTS:
        url = BASE_URL + endpoint
        stats = measure_endpoint(url, method, name)
        results["endpoints"].append(stats)
    
    # Calculate aggregate statistics
    all_latencies = []
    for endpoint_stats in results["endpoints"]:
        if "avg_ms" in endpoint_stats:
            # Simulate all requests for aggregate
            if endpoint_stats["successful"] > 0:
                estimated_values = [endpoint_stats["avg_ms"]] * endpoint_stats["successful"]
                all_latencies.extend(estimated_values)
    
    if all_latencies:
        results["aggregate"] = {
            "total_requests": len(all_latencies),
            "avg_ms": statistics.mean(all_latencies),
            "p50_ms": statistics.median(all_latencies),
            "p95_ms": sorted(all_latencies)[int(len(all_latencies) * 0.95)],
            "p99_ms": sorted(all_latencies)[int(len(all_latencies) * 0.99)],
            "max_ms": max(all_latencies),
        }
    
    # Save results
    output_file = "/opt/qr-attendance/logs/perf_baseline_day4.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*60}\n")
    
    # Print summary
    print("SUMMARY:")
    print(json.dumps(results, indent=2))
    
    return 0 if all_latencies else 1

if __name__ == "__main__":
    sys.exit(main())
EOF

# Make executable
chmod +x /opt/qr-attendance/perf_baseline_day4.py
```

#### Step 2b: Run Performance Baseline (Single-client)

```bash
# Run as qr-app user (simulates production environment)
sudo -u qr-app python3 /opt/qr-attendance/perf_baseline_day4.py

# Expected output:
# ==============================================================
# DAY 4: PRODUCTION PERFORMANCE BASELINE MEASUREMENT
# ==============================================================
# Timestamp: 2026-04-01T...Z
# Base URL: https://qr-attendance.example.com
# SSL Verification: True
#
# [WARMUP PHASE] Discarding first 2 requests...
# ============================================================
# Endpoint: health check
# URL: GET /health
# Iterations: 50
# ============================================================
#   [10/50] 0.45ms ✅
#   [20/50] 0.38ms ✅
#   ... 
# Results for health check:
#   Successful: 50/50
#   Avg:   0.42ms
#   p50:   0.41ms
#   p95:   0.58ms
#   p99:   0.72ms
#   Max:   1.23ms
#   StDev: 0.18ms
```

#### Step 2c: Load Testing Script (100 Concurrent Clients)

```bash
# Create load test script
cat > /opt/qr-attendance/load_test_day4.py << 'EOF'
#!/usr/bin/env python3
"""
Day 4 Load Test (100 Concurrent Clients)
Measures latency under realistic production load
"""

import requests
import concurrent.futures
import time
import json
import statistics
from datetime import datetime

BASE_URL = "https://qr-attendance.example.com"
ENDPOINT = "/health"
CONCURRENT_CLIENTS = 100
REQUESTS_PER_CLIENT = 20  # 100 * 20 = 2000 total requests
VERIFY_SSL = True

def single_request():
    """Perform single HTTP request"""
    try:
        start = time.time()
        response = requests.get(BASE_URL + ENDPOINT, timeout=30, verify=VERIFY_SSL)
        elapsed_ms = (time.time() - start) * 1000
        return {
            "success": True,
            "latency_ms": elapsed_ms,
            "status": response.status_code
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def main():
    print(f"\n{'='*60}")
    print(f"DAY 4: LOAD TEST (100 CONCURRENT CLIENTS)")
    print(f"{'='*60}")
    print(f"Endpoint: {BASE_URL}{ENDPOINT}")
    print(f"Concurrent clients: {CONCURRENT_CLIENTS}")
    print(f"Requests per client: {REQUESTS_PER_CLIENT}")
    print(f"Total requests: {CONCURRENT_CLIENTS * REQUESTS_PER_CLIENT}")
    print(f"{'='*60}\n")
    
    results = []
    
    # Execute all requests in parallel
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_CLIENTS) as executor:
        futures = [
            executor.submit(single_request)
            for _ in range(CONCURRENT_CLIENTS * REQUESTS_PER_CLIENT)
        ]
        
        # Collect results as they complete
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            
            if completed % 100 == 0:
                print(f"  Completed: {completed}/{CONCURRENT_CLIENTS * REQUESTS_PER_CLIENT}")
    
    total_time = time.time() - start_time
    
    # Analyze results
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    latencies = [r["latency_ms"] for r in successful]
    
    print(f"\nRESULTS:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Successful: {len(successful)}/{len(results)}")
    print(f"  Failed: {len(failed)}/{len(results)}")
    print(f"  Success rate: {100 * len(successful) / len(results):.1f}%")
    
    if latencies:
        print(f"\nLATENCY STATISTICS:")
        print(f"  Avg:   {statistics.mean(latencies):.2f}ms")
        print(f"  p50:   {statistics.median(latencies):.2f}ms")
        print(f"  p95:   {sorted(latencies)[int(len(latencies) * 0.95)]:.2f}ms")
        print(f"  p99:   {sorted(latencies)[int(len(latencies) * 0.99)]:.2f}ms")
        print(f"  Max:   {max(latencies):.2f}ms")
        
        print(f"\nTHROUGHPUT:")
        print(f"  Requests/sec: {len(results) / total_time:.2f}")
    
    # Save results
    output_file = "/opt/qr-attendance/logs/load_test_day4.json"
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "endpoint": ENDPOINT,
        "concurrent_clients": CONCURRENT_CLIENT,
        "total_requests": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate_percent": 100 * len(successful) / len(results),
        "total_duration_seconds": total_time,
        "throughput_rps": len(results) / total_time,
        "latency": {
            "avg_ms": statistics.mean(latencies),
            "p50_ms": statistics.median(latencies),
            "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)],
            "p99_ms": sorted(latencies)[int(len(latencies) * 0.99)],
            "max_ms": max(latencies)
        } if latencies else None
    }
    
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()
EOF

chmod +x /opt/qr-attendance/load_test_day4.py
```

#### Step 2d: Execute Load Test

```bash
# Run load test
python3 /opt/qr-attendance/load_test_day4.py

# Expected output:
# ============================================================
# DAY 4: LOAD TEST (100 CONCURRENT CLIENTS)
# ============================================================
# Endpoint: https://qr-attendance.example.com/health
# Concurrent clients: 100
# Requests per client: 20
# Total requests: 2000
# ============================================================
#
#   Completed: 100/2000
#   Completed: 200/2000
#   ...
#   Completed: 2000/2000
#
# RESULTS:
#   Total time: 15.23s
#   Successful: 2000/2000
#   Failed: 0/2000
#   Success rate: 100.0%
#
# LATENCY STATISTICS:
#   Avg:   5.12ms
#   p50:   4.89ms
#   p95:   9.23ms
#   p99:   12.45ms
#   Max:   23.56ms
#
# THROUGHPUT:
#   Requests/sec: 131.35
```

---

### Objective 3: Performance Comparison vs Day 35 Baseline (1 hour)

**Goal**: Verify no significant regression post-infrastructure setup

#### Step 3a: Compare Baselines

```bash
# Day 35 baseline (from 35-day program)
cat /project_notes/PERFORMANCE_BASELINE_RUNBOOK.md | grep -A 30 "baseline"

# Expected Day 35 results:
# /health avg=0.28ms, p95=~1ms
# /login avg=0.29ms
# /teacher_dashboard avg=2.68ms
# Error_rate: 0.0%

# Day 4 baseline (just measured)
python3 << 'EOF'
import json

print("DAY 35 BASELINE (Single-process Flask, SQLite):")
day35 = {
    "health": {"avg_ms": 0.28, "p95_ms": 1.0},
    "login": {"avg_ms": 0.29, "p95_ms": 1.0},
    "teacher_dashboard": {"avg_ms": 2.68, "p95_ms": 5.0}
}

print("DAY 4 BASELINE (Gunicorn + Nginx, SQLite):")
day4 = {}
with open("/opt/qr-attendance/logs/perf_baseline_day4.json") as f:
    day4_data = json.load(f)
    for endpoint in day4_data["endpoints"]:
        day4[endpoint["endpoint"]] = {
            "avg_ms": endpoint.get("avg_ms", "N/A"),
            "p95_ms": endpoint.get("p95_ms", "N/A")
        }

print("\nCOMPARISON:")
for endpoint in day35:
    day35_avg = day35[endpoint]["avg_ms"]
    day4_avg = day4.get(endpoint.split()[0], {}).get("avg_ms", "N/A")
    if day4_avg != "N/A":
        delta = ((day4_avg - day35_avg) / day35_avg) * 100
        status = "✅ PASS" if abs(delta) < 20 else "⚠️ INVESTIGATE" if abs(delta) < 50 else "❌ FAIL"
        print(f"{endpoint}: Day35={day35_avg}ms, Day4={day4_avg}ms, Delta={delta:+.1f}% {status}")

EOF
```

**Expected Outcome**:
- Gunicorn + Nginx adds ~5-10% overhead vs single-process Flask
- All endpoints should stay within SLO (< 8ms per Day 1 metrics)
- p95 latency acceptable if < 10ms (SLO threshold is 5s aggregate)

---

### Objective 4: Certificate Auto-Renewal Verification (1 hour)

**Goal**: Verify Let's Encrypt auto-renewal setup works pre-expiration

#### Step 4a: Check Auto-Renewal Schedule

```bash
# Verify certbot renewal cron or systemd timer
sudo systemctl list-timers | grep -i certbot

# Or check crontab
sudo crontab -l | grep certbot

# Expected:
# 0 3 * * 0 certbot renew --quiet && systemctl reload nginx
# (or systemd timer equivalent)
```

#### Step 4b: Test Renewal Dry-Run

```bash
# Dry-run renewal (does NOT actually renew)
sudo certbot renew --dry-run

# Expected output:
# *** DRY RUN: simulating certbot renew ***
# Processing /etc/letsencrypt/renewal/qr-attendance.example.com.conf
# Simulating renewal of an existing certificate...
# Certificate not due for renewal, but simulating anyway
# (success)
```

#### Step 4c: Certificate Expiration Monitoring

```bash
# Check expiration date
sudo openssl x509 -in /etc/letsencrypt/live/qr-attendance.example.com/fullchain.pem -noout -enddate

# Expected: notAfter=Jun 29 12:34:56 2026 GMT (90 days from issue)

# Create alert if expiring in < 30 days
echo "Check renewal: Jun 29, 2026 (90 days from now)"
```

---

### Objective 5: Nginx Log Analysis & Optimization (1 hour)

**Goal**: Review logs for errors, validate security headers, optimize performance

#### Step 5a: Check Nginx Access Logs

```bash
# Review recent access logs
sudo tail -100 /var/log/nginx/qr-attendance_access.log

# Analysis
sudo cat /var/log/nginx/qr-attendance_access.log | awk '{print $9}' | sort | uniq -c | sort -rn
# Shows HTTP status distribution (should be mostly 200s)

# Count 5xx errors (server errors)
sudo grep " 5[0-9][0-9] " /var/log/nginx/qr-attendance_access.log | wc -l
# Expected: 0 (no errors during baseline test)
```

#### Step 5b: Check Nginx Error Logs

```bash
# Review error log
sudo tail -50 /var/log/nginx/qr-attendance_error.log

# Expected: minimal errors (mostly INFO level)
```

#### Step 5c: Connection & Buffer Tuning (Optional)

```bash
# If seeing slowdown under load:
# Increase buffer sizes in Nginx config

sudo nano /etc/nginx/sites-available/qr-attendance

# Add/modify in server block:
# proxy_buffer_size 128k;
# proxy_buffers 4 256k;
# proxy_busy_buffers_size 256k;
```

---

## Day 4 Completion Checklist

### TLS Deployment Gates (ALL must be PASS)

- [ ] **Gate 1 - Certificate Deployment**:
  - [ ] Let's Encrypt certificates obtained (or self-signed available)
  - [ ] Nginx config points to correct cert paths
  - [ ] Nginx syntax verified, reloaded successfully
  
- [ ] **Gate 2 - HTTPS Verification**:
  - [ ] HTTP redirects to HTTPS (curl test)
  - [ ] HTTPS accessible on port 443
  - [ ] Certificate chain valid (openssl verify)
  - [ ] TLS 1.2+ enforced (no old protocols)
  - [ ] Security headers present (HSTS, CSP, etc.)
  
- [ ] **Gate 3 - Certificate Auto-Renewal**:
  - [ ] Certbot renewal configured (cron or systemd timer)
  - [ ] Dry-run renewal test passed
  - [ ] Expiration date documented (90 days from issue)

### Performance Baseline Gates (ALL must be PASS)

- [ ] **Gate 4 - Single-Client Baseline**:
  - [ ] All 50 requests to each endpoint successful
  - [ ] Latencies recorded: avg, p50, p95, p99, max
  - [ ] Results saved to perf_baseline_day4.json
  - [ ] No endpoint avg > 10ms (SLO buffer)
  
- [ ] **Gate 5 - Load Test (100 concurrent)**:
  - [ ] 2000 total requests completed
  - [ ] Success rate >= 99% (max 20 failures acceptable)
  - [ ] p95 latency < 10ms (with Nginx + Gunicorn overhead)
  - [ ] Throughput >= 100 requests/sec
  
- [ ] **Gate 6 - Performance Comparison vs Day 35**:
  - [ ] Latency delta < 20% (acceptable overhead from infrastructure)
  - [ ] No regressions identified
  - [ ] SLO thresholds still met (p95 < 5s aggregate)
  
- [ ] **Gate 7 - Production-Ready Verification**:
  - [ ] Service restarts gracefully (systemctl restart qr-attendance)
  - [ ] All logs clean (no 5xx errors)
  - [ ] Certificate renewal automation working

---

## Day 4 Deliverables

| Artifact | Location | Purpose |
|----------|----------|---------|
| TLS Deployment Verification | `/etc/letsencrypt/live/...` + curl tests | HTTPS active |
| Performance Baseline Report | `/opt/qr-attendance/logs/perf_baseline_day4.json` | Single-client latency |
| Load Test Report | `/opt/qr-attendance/logs/load_test_day4.json` | 100-concurrent latency |
| Performance Comparison | `project_notes/DAY39_PERF_COMPARISON.md` | Day 35 vs Day 4 delta |
| Day 4 Closeout Report | `project_notes/closeout/day4_tls_perf_report.json` | All gates + sign-off |

---

## Expected Performance Metrics (Day 4)

### Baseline Expectations (Single-Client)

| Endpoint | Target | Acceptable | Critical |
|----------|--------|-----------|----------|
| `/health` | 0.5ms | < 2ms | > 5ms ❌ |
| `/login` | 1.0ms | < 5ms | > 10ms ❌ |
| `/` (dashboard) | 5.0ms | < 10ms | > 20ms ❌ |

### Load Test Expectations (100 Concurrent)

| Metric | Target | Acceptable | Critical |
|--------|--------|-----------|----------|
| p50 latency | 3-5ms | < 8ms | > 15ms ❌ |
| p95 latency | 5-8ms | < 10ms | > 20ms ❌ |
| p99 latency | 8-12ms | < 15ms | > 30ms ❌ |
| Success rate | 99.9% | > 99% | < 95% ❌ |
| Throughput | > 100 rps | > 50 rps | < 25 rps ❌ |

---

## Risk Mitigation During Day 4

| Risk | Mitigation | Status |
|------|-----------|--------|
| SSL cert not obtained | Use self-signed, swap when LE ready | ✅ Prepared |
| Latency regression > 20% | Investigate Nginx config, update buffers | ✅ Procedure ready |
| Load test failures | Check Gunicorn worker count, systemd limits | ✅ Tuning ready |
| Certificate renewal fails | Manual renewal procedure documented | ✅ Runbook ready |

---

**Day 4 Status**: 🟡 IN PROGRESS  
**Estimated Completion**: April 1, 2026 (EOD, ~6-7 hours from start)  
**Success Criteria**: HTTPS live + Performance within SLO + Auto-renewal verified
