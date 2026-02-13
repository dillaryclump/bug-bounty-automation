# Scope Monitoring Guide

Complete guide to using AutoBug's scope monitoring system for tracking bug bounty program scope changes.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [CLI Commands](#cli-commands)
5. [Workflow Integration](#workflow-integration)
6. [Supported Platforms](#supported-platforms)
7. [Scope Validation](#scope-validation)
8. [Alert Integration](#alert-integration)
9. [Best Practices](#best-practices)

## Overview

The scope monitoring system automatically:

- Fetches program scope from bug bounty platforms
- Detects scope additions, removals, and modifications
- Validates discovered assets against current scope
- Sends alerts when scope changes
- Maintains historical scope snapshots

### Key Features

✅ **Multi-Platform Support**: HackerOne, Bugcrowd  
✅ **Dual Fetch Methods**: API + web scraping fallback  
✅ **Change Detection**: Additions, removals, modifications  
✅ **Asset Validation**: Wildcard, domain, IP, CIDR matching  
✅ **Alert Integration**: Discord and Slack notifications  
✅ **Historical Tracking**: Complete scope change history  

## Quick Start

### 1. Check Program Scope

```bash
# Check a single program's scope
python -m src.cli scope check 1

# With API token for faster/more reliable fetching
python -m src.cli scope check 1 --token YOUR_API_TOKEN
```

### 2. View Scope History

```bash
# Show last 10 scope checks
python -m src.cli scope history 1

# Show last 20
python -m src.cli scope history 1 --limit 20
```

### 3. Validate Assets

```bash
# Validate all program assets against current scope
python -m src.cli scope validate 1

# Show detailed validation results
python -m src.cli scope validate 1 --details
```

### 4. Monitor All Programs

```bash
# Check all active programs
python -m src.cli scope check-all

# Filter by platform
python -m src.cli scope check-all --platform hackerone
```

## Architecture

### Components

```
src/scope/
├── base.py         # Abstract parser + factory pattern
├── hackerone.py    # HackerOne-specific parser
├── bugcrowd.py     # Bugcrowd-specific parser
├── comparator.py   # Scope change detection
└── validator.py    # Asset scope validation
```

### Data Flow

```
┌─────────────────┐
│ Fetch Scope     │  API or web scraping
│ (Parser)        │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Compare with    │  Detect additions/removals
│ Previous        │  modifications
│ (Comparator)    │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Save Snapshot   │  Store in scope_history
│ (Database)      │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Send Alerts     │  Discord/Slack if changed
│ (Alert Manager) │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Validate Assets │  Check discovered assets
│ (Validator)     │  against new scope
└─────────────────┘
```

## CLI Commands

### `scope check <program_id>`

Check program scope for changes.

**Options:**
- `--token TEXT`: API token for platform authentication

**Example:**
```bash
python -m src.cli scope check 1 --token sk_live_abc123...
```

**Output:**
- Program name
- Change summary (additions/removals/modifications)
- Detailed change list
- Asset validation results

### `scope check-all`

Check all active programs for scope changes.

**Options:**
- `--platform TEXT`: Filter by platform (hackerone/bugcrowd)
- `--token TEXT`: API token

**Example:**
```bash
python -m src.cli scope check-all --platform hackerone
```

**Output:**
- Table with all programs
- Change status for each
- Summary statistics

### `scope history <program_id>`

View scope change history for a program.

**Options:**
- `--limit INTEGER`: Number of entries to show (default: 10)

**Example:**
```bash
python -m src.cli scope history 1 --limit 20
```

**Output:**
- Historical scope checks
- Timestamp, in/out counts
- Number of changes per check
- Data source (api/web_scrape)

### `scope validate <program_id>`

Validate all program assets against current scope.

**Options:**
- `--details`: Show detailed validation results

**Example:**
```bash
python -m src.cli scope validate 1 --details
```

**Output:**
- Total assets validated
- In-scope count
- Out-of-scope count
- Detailed validation reasons (if --details)

## Workflow Integration

### Direct Python Usage

```python
from src.workflows.scope_monitoring import (
    monitor_program_scope_flow,
    monitor_all_programs_scope_flow,
)

# Monitor single program
result = await monitor_program_scope_flow(
    program_id=1,
    api_token="YOUR_TOKEN",  # Optional
)

# Monitor all programs
results = await monitor_all_programs_scope_flow(
    platform="hackerone",  # Optional filter
    api_token="YOUR_TOKEN",  # Optional
)
```

### Prefect Scheduling

```python
from prefect import flow
from prefect.deployments import Deployment
from src.workflows.scope_monitoring import monitor_all_programs_scope_flow

# Create deployment
deployment = Deployment.build_from_flow(
    flow=monitor_all_programs_scope_flow,
    name="daily-scope-check",
    schedule={"cron": "0 2 * * *"},  # Daily at 2 AM
    parameters={"platform": None, "api_token": None},
)

# Apply deployment
deployment.apply()
```

## Supported Platforms

### HackerOne

**Features:**
- GraphQL API support (with token)
- HTML scraping fallback
- Structured scope parsing
- Asset categorization

**API Token:**
```bash
export HACKERONE_API_TOKEN="your_token_here"
python -m src.cli scope check 1 --token $HACKERONE_API_TOKEN
```

**Scope Format:**
- Wildcards: `*.example.com`
- Domains: `example.com`
- Subdomains: `api.example.com`
- IPs: `192.168.1.1`
- CIDR: `192.168.1.0/24`

### Bugcrowd

**Features:**
- REST API support (with token)
- HTML scraping fallback
- Target table parsing
- Mobile app ID support

**API Token:**
```bash
export BUGCROWD_API_TOKEN="your_token_here"
python -m src.cli scope check 1 --token $BUGCROWD_API_TOKEN
```

**Scope Format:**
- Same as HackerOne, plus:
- App IDs: `com.example.app`

## Scope Validation

The validator checks if discovered assets match program scope.

### Matching Rules

**1. Exact Match**
```
Scope: example.com
Asset: example.com → ✓ In scope
```

**2. Wildcard Match**
```
Scope: *.example.com
Asset: api.example.com → ✓ In scope
Asset: test.api.example.com → ✓ In scope
Asset: example.com → ✗ Out of scope
```

**3. Subdomain Match**
```
Scope: example.com
Asset: api.example.com → ✓ In scope (subdomain)
```

**4. CIDR Match**
```
Scope: 192.168.1.0/24
Asset: 192.168.1.50 → ✓ In scope
Asset: 192.168.2.1 → ✗ Out of scope
```

**5. Exclusion Priority**
```
In-Scope: *.example.com
Out-of-Scope: admin.example.com
Asset: admin.example.com → ✗ Out of scope (exclusion wins)
```

### Programmatic Validation

```python
from src.scope import ScopeValidator, ScopeData

# Create scope data
scope = ScopeData(
    in_scope=["*.example.com", "test.com"],
    out_of_scope=["admin.example.com"],
    platform="hackerone",
    program_handle="example",
    program_name="Example Program",
    program_url="https://hackerone.com/example",
)

# Create validator
validator = ScopeValidator(scope)

# Validate single asset
result = validator.validate("api.example.com")
print(result.in_scope)  # True
print(result.reason)    # "Matches in-scope pattern"
print(result.matched_rule)  # "*.example.com"

# Validate batch
assets = ["api.example.com", "admin.example.com", "other.com"]
results = validator.validate_batch(assets)

# Filter to in-scope only
in_scope = validator.filter_in_scope(assets)
```

## Alert Integration

Scope changes automatically trigger alerts via Discord/Slack.

### Alert Format

**Discord Embed:**
```
🎯 Scope Change: Example Program

Program scope has been updated: 3 added, 1 removed

Program: Example Program
Platform: HACKERONE

Changes:
  Added: 3
  Removed: 1
  Modified: 0

Details:
+ [in_scope] api.example.com
+ [in_scope] *.staging.example.com
+ [out_of_scope] old.example.com
- [in_scope] deprecated.example.com
```

**Slack Message:**
Similar format using Slack Block Kit.

### Alert Conditions

Alerts are sent when:
- ✅ Scope items are added
- ✅ Scope items are removed
- ✅ Items move between in-scope and out-of-scope

Alerts are NOT sent when:
- ❌ First scope check (baseline establishment)
- ❌ No changes detected
- ❌ Checksums match (duplicate check)

### Configuring Alerts

```bash
# Set webhook URLs in config
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Check scope (alerts sent automatically if changes detected)
python -m src.cli scope check 1
```

## Best Practices

### 1. Regular Monitoring

```bash
# Set up daily cron job
0 2 * * * cd /path/to/autobug && python -m src.cli scope check-all
```

### 2. Use API Tokens

- More reliable than scraping
- Faster response times
- Less likely to break with UI changes
- Required for private programs

### 3. Validate After Reconnaissance

```python
# After discovering assets
from src.scope import ScopeValidator

# Get latest scope
scope = await get_latest_scope(program_id)

# Filter discovered assets to in-scope only
validator = ScopeValidator(scope)
in_scope_assets = validator.filter_in_scope(discovered_assets)

# Only scan in-scope assets
for asset in in_scope_assets:
    await scan_asset(asset)
```

### 4. Monitor Scope History

```bash
# Check for trends
python -m src.cli scope history 1 --limit 30

# Look for:
# - Programs expanding scope (more opportunities)
# - Programs reducing scope (pause scanning)
# - Frequent changes (unstable program)
```

### 5. Handle Rate Limits

```python
# Add delays between checks
import asyncio

for program_id in program_ids:
    await monitor_program_scope_flow(program_id)
    await asyncio.sleep(60)  # 1 minute between checks
```

### 6. Database Maintenance

```sql
-- Clean old scope history (keep last 90 days)
DELETE FROM scope_history 
WHERE checked_at < NOW() - INTERVAL '90 days';

-- Keep at least 10 records per program
DELETE FROM scope_history 
WHERE id NOT IN (
    SELECT id FROM (
        SELECT id, 
               ROW_NUMBER() OVER (
                   PARTITION BY program_id 
                   ORDER BY checked_at DESC
               ) as rn
        FROM scope_history
    ) t 
    WHERE t.rn <= 10
)
AND checked_at < NOW() - INTERVAL '90 days';
```

## Troubleshooting

### Scope Not Fetched

**Symptoms:** Empty scope or errors

**Solutions:**
1. Try with API token: `--token YOUR_TOKEN`
2. Check program URL is accessible
3. Verify program handle is correct
4. Check logs: `tail -f logs/autobug.log`

### Assets Not Validating

**Symptoms:** All assets marked out-of-scope

**Solutions:**
1. Check scope was fetched: `scope history <id>`
2. Verify scope format (wildcards, domains)
3. Run with `--details` to see matching logic
4. Check for out-of-scope exclusions

### Alerts Not Sending

**Symptoms:** Scope changed but no alert

**Solutions:**
1. Check webhook URLs configured
2. Verify not first scope check (baseline)
3. Check alert logs in database
4. Test webhooks: `python -m src.cli alert test-webhook`

### Frequent False Changes

**Symptoms:** Alerts every check despite no real changes

**Solutions:**
1. Check for dynamic content in scope
2. Normalize scope items (lowercase, strip whitespace)
3. Review parser logic for platform
4. Check if platform randomizes order

## Advanced Usage

### Custom Parser

```python
from src.scope.base import BaseScopeParser, ScopeData, ScopeParserFactory

class CustomParser(BaseScopeParser):
    async def fetch_scope(self, program_handle: str) -> ScopeData:
        # Custom fetching logic
        ...
    
    def parse_scope_item(self, item: str) -> Dict:
        # Custom parsing logic
        ...

# Register parser
ScopeParserFactory.register("custom_platform", CustomParser)

# Use parser
async with ScopeParserFactory.create("custom_platform") as parser:
    scope = await parser.fetch_scope("program_handle")
```

### Custom Validation Logic

```python
from src.scope import ScopeValidator

class CustomValidator(ScopeValidator):
    def validate(self, asset: str) -> ValidationResult:
        # Add custom logic
        if asset.startswith("internal."):
            return ValidationResult(
                asset=asset,
                in_scope=False,
                reason="Internal domains excluded",
            )
        
        return super().validate(asset)
```

## Integration Examples

### With Reconnaissance

```python
# After subdomain enumeration
from src.scope import ScopeValidator

async def filter_discovered_subdomains(program_id: int, subdomains: List[str]):
    # Get latest scope
    async with get_session() as session:
        scope_history = await get_latest_scope_history(session, program_id)
    
    scope_data = reconstruct_scope_data(scope_history)
    validator = ScopeValidator(scope_data)
    
    # Filter to in-scope
    in_scope = validator.filter_in_scope(subdomains)
    
    return in_scope
```

### With Vulnerability Scanning

```python
# Before scanning
from src.scope import ScopeValidator

async def scan_if_in_scope(program_id: int, target: str):
    # Validate target
    scope = await get_program_scope(program_id)
    validator = ScopeValidator(scope)
    
    validation = validator.validate(target)
    
    if not validation.in_scope:
        logger.warning(f"Skipping {target}: {validation.reason}")
        return None
    
    # Target is in scope - proceed with scan
    return await run_nuclei_scan(target)
```

---

**Next Steps:**
- Set up automated daily scope checks
- Configure webhook alerts
- Integrate scope validation into reconnaissance
- Monitor scope history for trends

For more information, see:
- [CLI Reference](CLI_REFERENCE.md)
- [Alert Guide](ALERT_GUIDE.md)
- [Phase 5 Technical Summary](PHASE5_COMPLETE.md)
