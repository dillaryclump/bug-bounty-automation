# Vulnerability Scanning Guide

## Overview

The vulnerability scanning module uses **Nuclei** - an industry-standard scanner with 5000+ vulnerability templates. It's integrated with the **Diff Engine** to intelligently prioritize scanning based on changes.

## Key Features

✅ **Smart Targeting** - Automatically scans new/changed assets only  
✅ **OOB Detection** - Detects blind vulnerabilities with Interactsh  
✅ **Severity Filtering** - Focus on critical/high findings  
✅ **Deduplication** - Prevents duplicate reports  
✅ **Database Integration** - All findings stored for analysis  
✅ **Template Management** - 5000+ regularly updated templates  

## Quick Start

### 1. Ensure Nuclei is Installed

```powershell
# Should already be installed from recon setup
nuclei -version

# Update templates
nuclei -update-templates
```

### 2. Run Vulnerability Scan

```powershell
# Scan program (only scans new/changed assets)
python -m src.cli vuln scan 1

# Force rescan all assets
python -m src.cli vuln scan 1 --force

# Disable OOB detection (faster, less thorough)
python -m src.cli vuln scan 1 --no-oob
```

### 3. View Results

```powershell
# List all vulnerabilities
python -m src.cli vuln list

# Show new vulnerabilities only
python -m src.cli vuln list --new

# Filter by severity
python -m src.cli vuln list --severity critical

# Show details of specific vulnerability
python -m src.cli vuln show 1

# View statistics
python -m src.cli vuln stats
```

## How It Works

### The Smart Scanning Logic

```
┌─────────────────────────────────────────┐
│          Diff Engine Analysis            │
│   (Determines what needs scanning)       │
└────────────┬────────────────────────────┘
             │
             ▼
    ┌────────────────────┐
    │  Asset Categories  │
    └────────────────────┘
             │
    ┌────────┴──────────┐
    │                   │
    ▼                   ▼
┌─────────┐      ┌──────────────┐
│   NEW   │      │   MODIFIED   │
│ ASSETS  │      │   ASSETS     │
└────┬────┘      └──────┬───────┘
     │                  │
     ▼                  ▼
┌─────────────┐  ┌──────────────────┐
│  FULL SCAN  │  │  TARGETED SCAN   │
│ All templates│  │ Based on changes │
└──────┬──────┘  └────────┬─────────┘
       │                  │
       └────────┬─────────┘
                ▼
       ┌─────────────────┐
       │  Save to DB     │
       │  Deduplicate    │
       └─────────────────┘
```

### Example: What Gets Scanned

**Scenario 1: New Subdomain Discovered**
```
Asset: dev.example.com (NEW)
Action: Full Nuclei scan with all templates
Reason: Never scanned before, maximum coverage needed
Templates: All 5000+ templates
Duration: ~10-15 minutes per target
```

**Scenario 2: Technology Stack Changed**
```
Asset: api.example.com (MODIFIED)
Old Tech: Flask + Python
New Tech: Express + Node.js
Action: Targeted scan with Node.js specific templates
Templates: CVEs for Node.js, Express vulnerabilities
Duration: ~2-5 minutes per target
```

**Scenario 3: Status Code Changed**
```
Asset: admin.example.com (MODIFIED)
Old Status: 403 Forbidden
New Status: 200 OK
Action: Scan for exposures and misconfigurations
Templates: Exposures, default logins, panels
Duration: ~2-3 minutes per target
```

**Scenario 4: No Changes**
```
Asset: www.example.com (UNCHANGED)
Action: Skip (unless --force flag used)
Reason: Nothing changed, saves resources
```

## OOB Detection with Interactsh

**Out-of-Band (OOB)** detection catches vulnerabilities where the server doesn't directly respond but makes external requests.

### What OOB Detects

- **Blind SSRF** - Server makes request to external URL
- **Blind RCE** - Command execution without output
- **Blind XXE** - XML entity expansion
- **DNS Exfiltration** - Data extraction via DNS

### How It Works

```
1. Interactsh Setup
   ├─ Register unique domain (abc123.interact.sh)
   └─ Domain ready for monitoring

2. Nuclei Scanning
   ├─ Inject Interactsh URL into payloads
   ├─ Example: curl http://abc123.interact.sh
   └─ Server executes payload

3. Server Makes External Request
   ├─ Blind SSRF attempts to fetch Interactsh URL
   └─ DNS query or HTTP request to abc123.interact.sh

4. Interactsh Detects Interaction
   ├─ Logs the incoming request
   ├─ Captures headers, IP, timing
   └─ Reports back to scanner

5. Vulnerability Confirmed!
   └─ Blind SSRF exists even though no direct response
```

### Testing OOB Detection

```powershell
# Test Interactsh connectivity
python -m src.scanners.interactsh

# Output:
# ✅ Registered: abc123def456.interact.sh
# HTTP Payload: http://abc123def456.interact.sh
# DNS Payload: abc123def456.interact.sh
#
# Waiting 10 seconds for interactions...
# Try: curl http://abc123def456.interact.sh
```

In another terminal:
```powershell
curl http://abc123def456.interact.sh
```

Back in first terminal:
```
🎯 Received 1 interactions!
HTTP: 1 interactions
```

## Nuclei Template Categories

| Category | Description | Use Case |
|----------|-------------|----------|
| **cves/** | Known CVEs | Critical vulnerabilities |
| **exposures/** | Exposed files/configs | Sensitive data leaks |
| **vulnerabilities/** | Common web vulns | SQLi, XSS, etc. |
| **misconfiguration/** | Server misconfigs | Default configs |
| **default-logins/** | Default credentials | Admin panels |
| **takeovers/** | Subdomain takeovers | DNS misconfigurations |
| **technologies/** | Tech detection | Fingerprinting |

## Real-World Examples

### Example 1: Full Scan After Reconnaissance

```powershell
# 1. Run reconnaissance
python -m src.cli scan full 1

# Output: Found 412 new assets

# 2. Run vulnerability scan
python -m src.cli vuln scan 1

# Output:
# 🎯 Scan targets identified:
#    New assets: 412
#    Modified assets: 0
#
# 🆕 Phase 3a: Scanning 412 NEW assets
# ✅ Found 47 vulnerabilities
#
# Severity Breakdown:
#    🔴 CRITICAL: 2
#    🟠 HIGH: 8
#    🟡 MEDIUM: 23
#    🔵 LOW: 14
```

### Example 2: Daily Change Detection + Vuln Scan

```powershell
# Morning routine (automated)

# 1. Quick recon (check for changes)
python -m src.cli scan quick 1

# Output: 
# Modified Assets: 3
# Changes: Status change, tech stack update

# 2. Scan the changed assets
python -m src.cli vuln scan 1

# Output:
# 🔄 Phase 3b: Scanning 3 MODIFIED assets
# ✅ Found 2 new vulnerabilities
```

### Example 3: Managing Findings

```powershell
# List critical/high findings
python -m src.cli vuln list --severity critical --new

# Output:
# ┌────┬──────────┬────────────────────────────┬──────────────┐
# │ ID │ Severity │ Name                        │ Asset        │
# ├────┼──────────┼────────────────────────────┼──────────────┤
# │ 1  │ CRITICAL │ Apache RCE CVE-2021-41773  │ old.example  │
# │ 2  │ CRITICAL │ Exposed .git directory     │ dev.example  │
# │ 5  │ HIGH     │ Admin Panel Exposure       │ admin.example│
# └────┴──────────┴────────────────────────────┴──────────────┘

# Show details
python -m src.cli vuln show 1

# Output:
# Vulnerability #1
# ==================================================================
# Name: Apache RCE CVE-2021-41773
# Severity: [CRITICAL]
# Template: cves/2021/CVE-2021-41773.yaml
# Matched At: https://old.example.com/
# Tags: cve, rce, apache
# 
# Curl Command:
#   curl -X GET https://old.example.com/cgi-bin/.%2e/...
# ==================================================================

# Mark as reported (after submitting to program)
python -m src.cli vuln mark-reported 1,2,5
```

## Performance & Optimization

### Scan Duration Expectations

| Scenario | Assets | Duration | Templates Used |
|----------|--------|----------|----------------|
| New program (full scan) | 100 | 15-30 min | All (5000+) |
| Daily change detection | 5 modified | 1-3 min | Targeted (~500) |
| Weekly rescan | 500 | 2-4 hours | Medium+ severity |
| Force rescan all | 1000 | 4-8 hours | All templates |

### Rate Limiting

Nuclei is configured with sensible defaults:
- **150 requests/second** - Fast but respectful
- **5 second timeout** - Per request
- **2 retries** - For network issues
- **30 max errors** - Before skipping host

Adjust in [src/scanners/nuclei.py](src/scanners/nuclei.py):
```python
await scanner.scan(
    targets,
    rate_limit=100,  # Slower, more polite
    timeout=10,      # Longer timeout
)
```

## Integration with Full Workflow

### Complete Bug Hunting Workflow

```powershell
# Step 1: Add program
python -m src.cli add-program -p hackerone -h "program" -n "Program Name"

# Step 2: Initial reconnaissance
python -m src.cli scan full 1

# Step 3: Vulnerability scan (NEW assets)
python -m src.cli vuln scan 1

# Step 4: Review findings
python -m src.cli vuln list --new --severity high

# Step 5: Daily monitoring
# (Run these daily via Task Scheduler/cron)
python -m src.cli scan quick 1    # Check for changes
python -m src.cli vuln scan 1     # Scan changed assets

# Step 6: Manage findings
python -m src.cli vuln show 1     # Review details
python -m src.cli vuln mark-reported 1,2,3  # After reporting
```

## Database Queries

Interesting queries for analysis:

```sql
-- Top vulnerabilities by template
SELECT template_id, COUNT(*) as count
FROM vulnerabilities
GROUP BY template_id
ORDER BY count DESC
LIMIT 10;

-- Assets with most vulnerabilities
SELECT a.value, COUNT(v.id) as vuln_count
FROM assets a
JOIN vulnerabilities v ON v.asset_id = a.id
GROUP BY a.value
ORDER BY vuln_count DESC;

-- Critical findings not yet reported
SELECT v.name, v.matched_at, v.first_seen
FROM vulnerabilities v
WHERE v.severity = 'critical'
  AND v.reported = false
ORDER BY v.first_seen DESC;

-- Vulnerability discovery timeline
SELECT DATE(first_seen) as date, COUNT(*) as found
FROM vulnerabilities
GROUP BY DATE(first_seen)
ORDER BY date DESC;
```

## Troubleshooting

### No Vulnerabilities Found

This is often good news! But if unexpected:

```powershell
# 1. Check if Nuclei is working
nuclei -u https://example.com -t exposures/

# 2. Verify templates are updated
nuclei -update-templates

# 3. Check template stats
python
>>> from src.scanners.nuclei import NucleiScanner
>>> scanner = NucleiScanner()
>>> await scanner.get_template_stats()
```

### Scan Taking Too Long

```powershell
# Use force flag sparingly
python -m src.cli vuln scan 1  # Smart (only new/changed)
python -m src.cli vuln scan 1 --force  # Slow (all assets)

# Or scan specific severity
# Edit workflow to use:
severity=["critical", "high"]  # Skip medium/low/info
```

### OOB Detection Not Working

```powershell
# Test Interactsh separately
python -m src.scanners.interactsh

# Disable OOB if issues
python -m src.cli vuln scan 1 --no-oob
```

## Next Steps

- **Phase 4**: Build alerting system (get notified of critical findings)
- **Phase 5**: Web dashboard (visualize vulnerabilities)
- **Phase 6**: Automated reporting (generate reports for submissions)

Happy bug hunting! 🐛🔍
