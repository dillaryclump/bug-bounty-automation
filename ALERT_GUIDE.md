# Alerting System Guide

## Overview

The alerting system sends real-time notifications for security findings via **Discord** and **Slack**. It's fully integrated with the vulnerability scanner to automatically alert on critical findings.

## Key Features

✅ **Multi-Channel Support** - Discord and Slack webhooks  
✅ **Severity-Based Routing** - Critical alerts go to priority channels  
✅ **Smart Batching** - Reduces notification spam  
✅ **Rich Formatting** - Color-coded embeds with full details  
✅ **Alert History** - Database tracking of all alerts  
✅ **Retry Logic** - Automatic retry for failed deliveries  
✅ **Daily/Weekly Reports** - Automated summary digests  

## Quick Start

### 1. Configure Webhooks

Add webhook URLs to your `.env` file:

```bash
# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456/abcdef...

# Slack  
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00/B00/abc123...

# Alert Settings
ALERT_MIN_SEVERITY=high              # critical/high/medium/low/info
ALERT_CRITICAL_CHANNEL=discord       # discord/slack/both
ENABLE_DAILY_SUMMARY=true
DAILY_SUMMARY_TIME=09:00             # UTC time
ENABLE_WEEKLY_DIGEST=true
WEEKLY_DIGEST_DAY=monday
```

### 2. Set Up Webhooks

#### Discord Setup

```powershell
# Get setup instructions
python -m src.cli alert setup-guide
```

**Manual Steps:**
1. Open your Discord server
2. Go to **Server Settings** → **Integrations** → **Webhooks**
3. Click **New Webhook**
4. Name it "AutoBug Security Alerts"
5. Select a channel (e.g., #security-alerts)
6. **Copy Webhook URL**
7. Add to `.env`: `DISCORD_WEBHOOK_URL=<paste_url>`

#### Slack Setup

1. Go to https://api.slack.com/apps
2. Click **Create New App** → **From scratch**
3. Name it "AutoBug", select your workspace
4. Go to **Incoming Webhooks** and activate
5. Click **Add New Webhook to Workspace**
6. Select a channel (e.g., #security-alerts)
7. **Copy Webhook URL**
8. Add to `.env`: `SLACK_WEBHOOK_URL=<paste_url>`

### 3. Test Configuration

```powershell
# Verify configuration
python -m src.cli alert config

# Test webhooks
python -m src.cli alert test
```

Expected output:
```
🧪 Testing Alert Channels

Configured Channels:
  ✅ Discord: https://discord.com/api/webhooks/123...
  ✅ Slack: https://hooks.slack.com/services/T00...

Test Results:
  ✅ Discord: Success
  ✅ Slack: Success
```

## How It Works

### Automatic Alerting Workflow

```
┌─────────────────────────────────────────────────┐
│     Vulnerability Scan Completes                │
│     (New findings detected)                     │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│          Alert Manager                          │
│  • Checks severity threshold                    │
│  • Separates critical from others               │
│  • Routes to appropriate channels               │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────┴──────────┐
        ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  CRITICAL/   │    │  Medium/Low  │
│  HIGH        │    │  Findings    │
│  Findings    │    │              │
└──────┬───────┘    └──────┬───────┘
       │                   │
       ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  Individual  │    │   Batched    │
│  Alerts      │    │   Alert      │
│  (immediate) │    │   (grouped)  │
└──────┬───────┘    └──────┬───────┘
       │                   │
       └────────┬──────────┘
                ▼
       ┌─────────────────┐
       │  Send to        │
       │  Discord/Slack  │
       └─────────────────┘
```

### Alert Types

| Type | Description | When Sent | Format |
|------|-------------|-----------|--------|
| **CRITICAL_FINDING** | Critical severity vuln | Immediately, individual | Rich embed with full details |
| **NEW_VULNERABILITY** | High severity vuln | Immediately, individual | Rich embed with full details |
| **NEW_VULNERABILITY (batch)** | Medium/Low vulns | Batched together | Multiple embeds in one message |
| **DAILY_SUMMARY** | Daily statistics | Configured time (default 09:00 UTC) | Stats table |
| **WEEKLY_DIGEST** | Weekly summary | Configured day | Comprehensive report |
| **SCAN_COMPLETE** | Scan finished | After each scan | Summary of findings |

### Severity Routing

```python
# From config.py
ALERT_MIN_SEVERITY = "high"  # Only alert on high+ findings

# Severity levels (from lowest to highest):
# info → low → medium → high → critical

# Example configurations:
# ALERT_MIN_SEVERITY=critical  # Only critical findings
# ALERT_MIN_SEVERITY=high      # High and critical (recommended)
# ALERT_MIN_SEVERITY=medium    # Medium, high, and critical
```

### Channel Selection

```python
# From config.py
ALERT_CRITICAL_CHANNEL = "discord"  # Where to send critical alerts

# Options:
# "discord" - Send critical to Discord only
# "slack"   - Send critical to Slack only
# "both"    - Send critical to both channels (redundancy)
```

## CLI Commands

### Show Configuration

```powershell
python -m src.cli alert config
```

Displays current alert settings and webhook status.

### Test Alerts

```powershell
python -m src.cli alert test
```

Sends test messages to all configured channels.

### Send Daily Summary

```powershell
# All programs
python -m src.cli alert daily-summary

# Specific program
python -m src.cli alert daily-summary --program 1
```

### Send Weekly Digest

```powershell
# All programs
python -m src.cli alert weekly-digest

# Specific program
python -m src.cli alert weekly-digest --program 1
```

### View Alert History

```powershell
# Last 24 hours
python -m src.cli alert history

# Last week
python -m src.cli alert history --hours 168

# Specific program
python -m src.cli alert history --program 1

# Limit results
python -m src.cli alert history --limit 100
```

### Alert Statistics

```powershell
# Last 7 days
python -m src.cli alert stats

# Last 30 days
python -m src.cli alert stats --days 30

# Specific program
python -m src.cli alert stats --program 1
```

### Retry Failed Alerts

```powershell
python -m src.cli alert retry-failed
```

Automatically retries alerts that failed to send.

## Alert Formats

### Discord Example

**Critical Vulnerability Alert:**

```
🚨 Apache RCE CVE-2021-41773

Matched At: https://old.example.com/

Severity: CRITICAL
Template: cves/2021/CVE-2021-41773.yaml
First Seen: 2 hours ago

Asset: old.example.com

Tags: cve, rce, apache

Reproduction:
```bash
curl -X GET https://old.example.com/cgi-bin/.%2e/%2e%2e/%2e%2e/etc/passwd
```
```

**Daily Summary:**

```
📊 Daily Security Summary

Vulnerability findings from the last 24 hours

Total Vulnerabilities: 23
Critical: 2
High: 8
Medium: 11
Low: 2
Info: 0
```

### Slack Example

Uses Slack Block Kit for rich formatting with the same information, optimized for Slack's UI.

## Real-World Examples

### Example 1: Automated Vulnerability Alerting

```powershell
# Run vulnerability scan
python -m src.cli vuln scan 1

# Output:
# ...scanning...
# ✅ Found 5 vulnerabilities
#    🔴 CRITICAL: 1
#    🟠 HIGH: 2
#    🟡 MEDIUM: 2
#
# 🔔 Phase 7: Sending alerts for new findings
# 🚨 Sending 3 critical/high severity alerts
# 📦 Sending batch alert for 2 other findings
# ✅ Alerts sent successfully
```

**Result:** You receive 3 individual Discord alerts for the critical/high findings, and 1 batched alert for the medium findings.

### Example 2: Daily Monitoring Routine

```powershell
# Morning routine (automated via Task Scheduler)

# 1. Quick recon to detect changes
python -m src.cli scan quick 1

# 2. Scan for vulnerabilities in changed assets
python -m src.cli vuln scan 1

# 3. Send daily summary at 9 AM UTC
python -m src.cli alert daily-summary --program 1
```

**Automation:** Add to Windows Task Scheduler to run daily.

### Example 3: Investigating Alert History

```powershell
# Check what alerts were sent today
python -m src.cli alert history --hours 24

# Output: Table showing all alerts
# ┌────┬──────────────────────┬────────────────────┬─────────┬─────────┐
# │ ID │ Type                 │ Title              │ Channel │ Status  │
# ├────┼──────────────────────┼────────────────────┼─────────┼─────────┤
# │ 42 │ critical_finding     │ Apache RCE         │ discord │ ✅ Sent │
# │ 43 │ new_vulnerability    │ XSS in /search     │ discord │ ✅ Sent │
# │ 44 │ new_vulnerability    │ Exposed .git       │ both    │ ✅ Sent │
# └────┴──────────────────────┴────────────────────┴─────────┴─────────┘

# Get detailed stats
python -m src.cli alert stats --days 7

# Output:
# ┌──────────────────┬───────┐
# │ Metric           │ Count │
# ├──────────────────┼───────┤
# │ Total Alerts     │ 127   │
# │ Successful       │ 125   │
# │ Failed           │ 2     │
# │ Pending          │ 0     │
# └──────────────────┴───────┘

# Retry any failures
python -m src.cli alert retry-failed
```

## Integration with Workflows

### Automatic Alerting During Scans

The vulnerability scanning workflow automatically sends alerts. No additional configuration needed!

```python
# From vulnerability_scan.py
async def vulnerability_scan_flow(program_id: int):
    # ... scanning happens ...
    
    # Step 8: Send alerts for new findings
    if saved_count > 0:
        logger.info("🔔 Phase 7: Sending alerts for new findings")
        await send_vulnerability_alerts_task(program_id, unique_findings)
```

### Manual Alerting via Python

```python
from src.alerting.manager import AlertManager
from src.db.session import db_manager

async def send_custom_alert():
    async with db_manager.get_session() as session:
        async with AlertManager(session) as manager:
            # Get a vulnerability
            vuln = await session.get(Vulnerability, 42)
            
            # Send alert
            await manager.alert_vulnerability(
                vuln,
                alert_type=AlertType.CRITICAL_FINDING
            )
```

## Database Schema

### Alerts Table

```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50),        -- Type of alert
    severity VARCHAR(20),           -- Severity level
    program_id INTEGER,             -- Related program
    vulnerability_id INTEGER,       -- Related vulnerability
    asset_id INTEGER,               -- Related asset
    title VARCHAR(500),             -- Alert title
    message TEXT,                   -- Alert message
    payload JSONB,                  -- Additional data
    channel VARCHAR(50),            -- discord/slack/both
    destination VARCHAR(500),       -- Webhook URL
    sent BOOLEAN,                   -- Was it sent?
    success BOOLEAN,                -- Did it succeed?
    error_message TEXT,             -- Error if failed
    retry_count INTEGER,            -- Retry attempts
    sent_at TIMESTAMP,              -- When sent
    created_at TIMESTAMP            -- When created
);

-- Indexes for performance
CREATE INDEX idx_alert_type_created ON alerts(alert_type, created_at);
CREATE INDEX idx_alert_sent_success ON alerts(sent, success);
CREATE INDEX idx_alert_channel_sent ON alerts(channel, sent_at);
```

### Query Examples

```sql
-- Get alerts sent today
SELECT * FROM alerts 
WHERE sent_at >= CURRENT_DATE;

-- Failed alerts needing retry
SELECT * FROM alerts 
WHERE sent = true 
  AND success = false 
  AND retry_count < 3;

-- Alert statistics by type
SELECT alert_type, COUNT(*) as count
FROM alerts
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY alert_type;

-- Critical findings not alerted
SELECT v.* FROM vulnerabilities v
LEFT JOIN alerts a ON a.vulnerability_id = v.id
WHERE v.severity = 'critical'
  AND a.id IS NULL;
```

## Scheduling Automated Reports

### Windows Task Scheduler

```powershell
# Daily summary at 9 AM
schtasks /create /tn "AutoBug Daily Summary" /tr "python -m src.cli alert daily-summary" /sc daily /st 09:00

# Weekly digest every Monday at 9 AM
schtasks /create /tn "AutoBug Weekly Digest" /tr "python -m src.cli alert weekly-digest" /sc weekly /d MON /st 09:00
```

### Linux Cron

```bash
# Edit crontab
crontab -e

# Daily summary at 9 AM UTC
0 9 * * * cd /path/to/auto_bug_web && python -m src.cli alert daily-summary

# Weekly digest Monday 9 AM UTC
0 9 * * 1 cd /path/to/auto_bug_web && python -m src.cli alert weekly-digest
```

## Troubleshooting

### Alerts Not Sending

**Check webhook configuration:**
```powershell
python -m src.cli alert config
```

**Test webhooks:**
```powershell
python -m src.cli alert test
```

**Check alert history for errors:**
```powershell
python -m src.cli alert history --hours 24
```

### Discord Webhook Errors

- **401 Unauthorized**: Webhook URL is invalid or deleted
- **404 Not Found**: Webhook doesn't exist
- **Rate Limited**: Sending too many messages (wait and retry)

**Solution:** Recreate webhook and update `.env`

### Slack Webhook Errors

- **invalid_payload**: Check message formatting
- **channel_not_found**: Channel was deleted
- **action_prohibited**: App doesn't have permissions

**Solution:** Recreate app and webhook

### Too Many Alerts

**Increase severity threshold:**
```bash
# In .env
ALERT_MIN_SEVERITY=critical  # Only critical findings
```

**Enable batching:**
```bash
# In .env
ALERT_BATCH_WINDOW=900  # 15 minutes (group alerts)
```

### Missing Alerts

**Check alert history:**
```powershell
python -m src.cli alert history --hours 168
```

**Check if filtered by severity:**
```bash
# In .env - lower threshold
ALERT_MIN_SEVERITY=medium  # Include medium severity
```

**Retry failed alerts:**
```powershell
python -m src.cli alert retry-failed
```

## Best Practices

### Recommended Configuration

```bash
# .env recommended settings for production

# Webhooks (configure both for redundancy)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Alert critical to both channels
ALERT_CRITICAL_CHANNEL=both

# Alert on high and critical only
ALERT_MIN_SEVERITY=high

# Enable automated reports
ENABLE_DAILY_SUMMARY=true
DAILY_SUMMARY_TIME=09:00  # Your morning routine time

ENABLE_WEEKLY_DIGEST=true
WEEKLY_DIGEST_DAY=monday
```

### Alert Channel Strategy

**Single Program:**
- Create `#security-alerts` channel
- Send all alerts there

**Multiple Programs:**
- Create per-program channels: `#program1-alerts`, `#program2-alerts`
- Configure multiple webhooks in code

**Team Collaboration:**
- Discord for immediate response (mobile notifications)
- Slack for team discussion and tracking

## Next Steps

- **Phase 5**: Scope monitoring (detect program changes)
- **Phase 6**: Web dashboard (visual alert management)
- **Phase 7**: Fleet management (Axiom distributed scanning)

Happy hunting! 🔔🐛
