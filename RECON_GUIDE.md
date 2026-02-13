# Reconnaissance Pipeline - Usage Guide

## Quick Start

### 1. Install Scanning Tools

**Windows:**
```powershell
.\scripts\install_tools.ps1
```

**Linux/macOS:**
```bash
chmod +x scripts/install_tools.sh
./scripts/install_tools.sh
```

### 2. Verify Tools Installation

```powershell
python -m src.cli scan test-tools
```

You should see:
```
✅ Subfinder: Installed
✅ httpx: Installed
✅ Naabu: Installed
✅ puredns: Installed (or warning if not installed)
```

### 3. Add Your First Program

```powershell
python -m src.cli add-program `
  --platform hackerone `
  --handle "example-program" `
  --name "Example Corp Bug Bounty"
```

### 4. Run Your First Scan!

```powershell
# Full reconnaissance (subdomain enum + HTTP probing)
python -m src.cli scan full 1

# Quick scan (just probe known assets)
python -m src.cli scan quick 1
```

## Understanding the Workflow

The reconnaissance pipeline follows this process:

```
1. SUBDOMAIN ENUMERATION (Subfinder)
   ├─ Passive sources (40+ providers)
   ├─ No direct contact with target
   └─ Fast discovery of subdomains
   
2. DNS RESOLUTION (puredns/builtin)
   ├─ Filter out dead domains
   ├─ Get IP addresses
   └─ Wildcard detection
   
3. PORT SCANNING (Naabu)
   ├─ Scan top 1000 ports
   ├─ Service detection
   └─ Find non-standard web ports
   
4. HTTP PROBING (httpx)
   ├─ Status codes
   ├─ Content length
   ├─ Page titles
   ├─ Technology detection
   └─ Response hashes
   
5. DIFF ENGINE ANALYSIS ⭐
   ├─ Compare with previous scans
   ├─ Detect changes
   ├─ Prioritize targets
   └─ Update database
```

## Real-World Examples

### Example 1: Scan a New Program

```powershell
# Add the program
python -m src.cli add-program `
  -p hackerone `
  -h "verizon" `
  -n "Verizon Media"

# List programs to get the ID
python -m src.cli list-programs

# Run full reconnaissance
python -m src.cli scan full 1
```

**Expected Output:**
```
🚀 Starting reconnaissance for program ID: 1
📋 Scope: 1 root domain(s)

🔍 Phase 1: Subdomain Enumeration
✅ Found 847 total subdomains

🌐 Phase 2: DNS Resolution
✅ 623 domains are alive

🔍 Phase 3: Port Scanning
✅ Discovered ports on 98 hosts

🌐 Phase 4: HTTP Probing
✅ 412 endpoints responded

🎯 Phase 5: Diff Engine Analysis

====================================================
📊 RECONNAISSANCE COMPLETE!
====================================================
⏱️  Duration: 324.5 seconds
🆕 New Assets: 412
🔄 Modified Assets: 0
✔️  Unchanged Assets: 0
📝 Total Changes: 0
====================================================
```

### Example 2: Daily Change Detection

Run this daily to detect changes:

```powershell
# Quick scan (fast, probes existing assets only)
python -m src.cli scan quick 1
```

**Expected Output (with changes detected):**
```
⚡ Quick scan for program ID: 1
📋 Probing 412 known assets

🔄 Status change: api.example.com (403 → 200)
🔧 Tech stack change: admin.example.com
  Added: {'django'}
  Removed: {'flask'}

✅ Quick scan complete!
Modified Assets: 2
Total Changes: 3
```

## The Diff Engine in Action

The Diff Engine is what makes this platform special. Here's what it detects:

### Change 1: HTTP Status Change
```
Old: 403 Forbidden
New: 200 OK
🚨 HIGH PRIORITY - Access control may have changed!
```

### Change 2: Technology Stack Change
```
Old: ['php', 'apache']
New: ['nodejs', 'express']
🔧 RESCAN NEEDED - Different vulnerabilities apply!
```

### Change 3: Content Length Change
```
Old: 5,432 bytes
New: 125,678 bytes
📏 INVESTIGATE - Significant new content added
```

### Change 4: New Subdomain Discovery
```
New: dev-staging.example.com
🆕 HIGH PRIORITY - Previously unknown asset!
```

## Advanced Usage

### Custom Scope Scanning

Update a program's scope:

```python
# Via Python
from src.db.session import db_manager
from src.db.repositories import ProgramRepository

async def update_scope():
    async with db_manager.get_session() as session:
        repo = ProgramRepository(session)
        await repo.update_scope(
            program_id=1,
            in_scope=["example.com", "*.example.net"],
            out_of_scope=["test.example.com"],
        )
```

### Scheduling Scans

Use with Windows Task Scheduler or Linux cron:

```powershell
# Windows Task Scheduler
# Run daily at 2 AM
schtasks /create /tn "AutoBug Daily Scan" /tr "python -m src.cli scan full 1" /sc daily /st 02:00
```

```bash
# Linux cron
# Run daily at 2 AM
0 2 * * * cd /path/to/auto_bug_web && python -m src.cli scan full 1
```

### Combining with Prefect

For production use, schedule via Prefect:

```python
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
from src.workflows.reconnaissance import reconnaissance_flow

# Deploy with schedule
deployment = Deployment.build_from_flow(
    flow=reconnaissance_flow,
    name="daily-recon",
    parameters={"program_id": 1},
    schedule=CronSchedule(cron="0 2 * * *"),  # 2 AM daily
)
deployment.apply()
```

## Performance Tuning

### For Maximum Speed

Edit [src/workflows/reconnaissance.py](src/workflows/reconnaissance.py):

```python
# Increase httpx threads
probe_results = await probe_http_task(alive_domains, threads=100)

# Parallel subdomain enumeration
# Use asyncio.gather() to scan multiple root domains simultaneously
```

### For Stealth/Rate Limiting

```python
# Reduce concurrency in httpx scanner
scanner = HttpxScanner()
await scanner.probe(targets, threads=10, timeout=30)  # Slower, more polite
```

## Troubleshooting

### "No subdomains found"

```powershell
# Test Subfinder manually
subfinder -d example.com -all

# Check API keys in ~/.config/subfinder/provider-config.yaml
```

### "DNS resolution failed"

```powershell
# Check if puredns is installed
puredns version

# Fallback DNS resolution is automatic if puredns is missing
```

### "Port scanning failed"

```powershell
# Naabu requires admin on Windows for raw sockets
# Run PowerShell as Administrator, or:

# Use limited port scanning (works without admin)
python -m src.cli scan full 1  # Still works, just slower port scanning
```

## Next Steps

- **Phase 3**: Integrate Nuclei for vulnerability scanning
- **Phase 4**: Add alerting (Discord/Slack webhooks)
- **Phase 5**: Build web dashboard for visualization
- **Phase 6**: Add Axiom fleet management for distributed scanning

## Understanding the Database

After scans, check your database:

```sql
-- See all discovered assets
SELECT value, http_status, content_length, technologies 
FROM assets 
WHERE program_id = 1 AND is_alive = true;

-- See detected changes
SELECT a.value, ac.field_name, ac.old_value, ac.new_value, ac.detected_at
FROM asset_changes ac
JOIN assets a ON a.id = ac.asset_id
WHERE a.program_id = 1
ORDER BY ac.detected_at DESC;

-- See new assets
SELECT value, first_seen, http_status, page_title
FROM assets
WHERE program_id = 1
AND first_seen > NOW() - INTERVAL '24 hours';
```

Happy hunting! 🐛🔍
