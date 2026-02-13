# AutoBug CLI Quick Reference

## Program Management

```powershell
# Add a new program
python -m src.cli add-program -p hackerone -h "program_handle" -n "Program Name"

# List all programs
python -m src.cli list-programs
```

## Reconnaissance Scanning

```powershell
# Full reconnaissance (subdomain enum, DNS, ports, HTTP probing)
python -m src.cli scan full <PROGRAM_ID>

# Quick scan (only check for changes in existing assets)
python -m src.cli scan quick <PROGRAM_ID>

# Test scanner installations
python -m src.cli scan test-tools
```

## Vulnerability Scanning

```powershell
# Smart scan (only new/modified assets)
python -m src.cli vuln scan <PROGRAM_ID>

# Force rescan all assets
python -m src.cli vuln scan <PROGRAM_ID> --force

# Disable OOB detection
python -m src.cli vuln scan <PROGRAM_ID> --no-oob

# List vulnerabilities
python -m src.cli vuln list                           # All
python -m src.cli vuln list --new                     # New only
python -m src.cli vuln list --severity critical       # By severity
python -m src.cli vuln list --severity high --new     # Combined filters

# Show vulnerability details
python -m src.cli vuln show <VULN_ID>

# Mark vulnerabilities as reported
python -m src.cli vuln mark-reported <VULN_ID1,VULN_ID2,...>

# Vulnerability statistics
python -m src.cli vuln stats
```

## Alert Management

```powershell
# Test alert webhooks
python -m src.cli alert test

# Show alert configuration
python -m src.cli alert config

# Send reports
python -m src.cli alert daily-summary [--program <ID>]
python -m src.cli alert weekly-digest [--program <ID>]

# View alert history
python -m src.cli alert history [--hours <N>] [--program <ID>]

# Alert statistics
python -m src.cli alert stats [--days <N>] [--program <ID>]

# Retry failed alerts
python -m src.cli alert retry-failed

# Setup guide
python -m src.cli alert setup-guide
```

## Scope Monitoring

```powershell
# Check program scope for changes
python -m src.cli scope check <PROGRAM_ID>
python -m src.cli scope check <PROGRAM_ID> --token <API_TOKEN>

# Check all programs
python -m src.cli scope check-all
python -m src.cli scope check-all --platform hackerone

# View scope history
python -m src.cli scope history <PROGRAM_ID>
python -m src.cli scope history <PROGRAM_ID> --limit 20

# Validate assets against scope
python -m src.cli scope validate <PROGRAM_ID>
python -m src.cli scope validate <PROGRAM_ID> --details

# Manual scope update (alias for check)
python -m src.cli scope update <PROGRAM_ID>
```

## Common Workflows

### Initial Setup

```powershell
# 1. Add program
python -m src.cli add-program -p hackerone -h "example" -n "Example Corp"

# 2. Configure alerts
code .env  # Add DISCORD_WEBHOOK_URL and/or SLACK_WEBHOOK_URL
python -m src.cli alert test

# 3. Check scope
python -m src.cli scope check 1 --token <API_TOKEN>

# 4. Initial scan
python -m src.cli scan full 1
python -m src.cli vuln scan 1

# 5. Review findings
python -m src.cli vuln list --severity high
python -m src.cli vuln show 1
```

### Daily Monitoring

```powershell
# 1. Check for scope changes
python -m src.cli scope check-all

# 2. Quick reconnaissance
python -m src.cli scan quick 1

# 3. Scan new assets
python -m src.cli vuln scan 1  # Smart scan (new/modified only)

# 4. Review new vulnerabilities
python -m src.cli vuln list --new
```

### Daily Monitoring

```powershell
# Automated script (run via Task Scheduler daily)

# 1. Check for changes
python -m src.cli scan quick 1

# 2. Scan changed assets
python -m src.cli vuln scan 1

# 3. Send summary (optional)
python -m src.cli alert daily-summary --program 1
```

### Manage Findings

```powershell
# 1. List new critical/high findings
python -m src.cli vuln list --new --severity high

# 2. Review details
python -m src.cli vuln show 1
python -m src.cli vuln show 2

# 3. Report to program
# (Submit via their platform)

# 4. Mark as reported
python -m src.cli vuln mark-reported 1,2,3,4
```

## Configuration (.env)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://autobug:password@localhost:5432/autobug_db

# Alerting
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Alert Settings
ALERT_MIN_SEVERITY=high              # critical/high/medium/low/info
ALERT_CRITICAL_CHANNEL=discord       # discord/slack/both
ENABLE_DAILY_SUMMARY=true
DAILY_SUMMARY_TIME=09:00             # UTC

# Scanning
NUCLEI_RATE_LIMIT=150               # Requests per second
MAX_CONCURRENT_SCANS=5
```

## Severity Levels

From lowest to highest:
- `info` - Informational findings
- `low` - Low severity issues
- `medium` - Medium severity vulnerabilities
- `high` - High severity vulnerabilities
- `critical` - Critical security issues

## File Locations

```
logs/              - Application logs
.env               - Configuration (create from .env.example)
migrations/        - Database migrations
src/scanners/      - Scanner integrations
src/workflows/     - Prefect workflows
src/alerting/      - Alert clients
```

## Troubleshooting

### Scanners not working
```powershell
python -m src.cli scan test-tools
# Reinstall if needed: .\scripts\install_tools.ps1
```

### Alerts not sending
```powershell
python -m src.cli alert config    # Check configuration
python -m src.cli alert test      # Test webhooks
python -m src.cli alert history   # Check for errors
```

### Database issues
```powershell
# Check connection
alembic current

# Run migrations
alembic upgrade head
SCOPE_GUIDE.md](SCOPE_GUIDE.md) - Scope monitoring
- [
# Reset database (WARNING: destroys data)
alembic downgrade base
alembic upgrade head
```

### View logs
```powershell
# Real-time log viewing
Get-Content logs/autobug.log -Wait -Tail 50
```

## Documentation

- [QUICKSTART.md](QUICKSTART.md) - Project overview
- [INSTALL_TOOLS.md](INSTALL_TOOLS.md) - Scanner installation
- [RECON_GUIDE.md](RECON_GUIDE.md) - Reconnaissance guide
- [VULN_GUIDE.md](VULN_GUIDE.md) - Vulnerability scanning
- [ALERT_GUIDE.md](ALERT_GUIDE.md) - Alert configuration
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical details

## Getting Help

1. Check relevant guide in docs/
2. Review logs in logs/ directory
3. Test individual components
4. Check .env configuration

## Common Errors

| Error | Solution |
|-------|----------|
| "Tool not found" | Run `.\scripts\install_tools.ps1` |
| "Database connection failed" | Check Docker: `docker-compose ps` |
| "No webhook configured" | Add URLs to .env |
| "Permission denied" | Run PowerShell as Administrator |
| "Alembic error" | Run `alembic upgrade head` |

## Performance Tips

1. Use `scan quick` for daily monitoring (faster)
2. Use `--force` sparingly (scans everything)
3. Adjust `NUCLEI_RATE_LIMIT` if being rate limited
4. Set `ALERT_MIN_SEVERITY=high` to reduce noise
5. Enable batching: `ALERT_BATCH_WINDOW=300`
