# AutoBug - Architecture & Development Roadmap

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         THE BRAIN                                │
│                   (Persistent Server)                            │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  PostgreSQL  │  │    Redis     │  │   Prefect    │          │
│  │   (State)    │  │  (Queue)     │  │ (Workflows)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              Diff Engine (Core Logic)                │        │
│  │  - Detects changes in assets over time               │        │
│  │  - Prioritizes new/changed targets                   │        │
│  │  - Skips unchanged assets (resource optimization)    │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   FastAPI    │  │  Alerting    │  │     CLI      │          │
│  │  (API)       │  │   System     │  │   Manager    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        THE MUSCLE                                │
│                   (Ephemeral Fleet)                              │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Scanner  │  │ Scanner  │  │ Scanner  │  │ Scanner  │  ...   │
│  │ Node 1   │  │ Node 2   │  │ Node 3   │  │ Node N   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                   │
│  Tools: Subfinder | httpx | Nuclei | Naabu | puredns            │
│  Fleet Manager: Axiom (DigitalOcean API)                         │
│  Auto-scaling: 10-50 nodes based on workload                     │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Pipeline

```
1. SCOPE MONITOR
   ├─ Poll HackerOne/Bugcrowd APIs (hourly)
   ├─ Detect new programs or scope changes
   └─ Trigger: Full Recon OR Change Detection

2. RECONNAISSANCE
   ├─ Subdomain Enumeration (Subfinder, passive)
   ├─ DNS Resolution (puredns + massdns)
   ├─ Subdomain Permutation (altdns, ripgen)
   ├─ Port Scanning (Naabu top 1000 ports)
   └─ Web Probing (httpx)
        └─ Capture: Status, Length, Title, Tech, Hash

3. DIFF ENGINE ⭐
   ├─ Compare with PostgreSQL state
   ├─ Identify: NEW | MODIFIED | UNCHANGED
   ├─ Record changes in asset_changes table
   └─ Priority Classification:
        ├─ HIGH: New assets, status changes, tech changes
        ├─ MEDIUM: Content changes, IP changes
        └─ LOW: Unchanged (skip scan)

4. VULNERABILITY SCANNING
   ├─ New Assets → Full Nuclei scan
   ├─ Modified Assets → Targeted rescan
   ├─ Unchanged Assets → New templates only
   └─ OOB Detection (Interactsh for RCE/SSRF)

5. ALERTING
   ├─ Critical/High → Discord/Pushover (immediate)
   ├─ Medium → Daily summary (Slack/Email)
   └─ Info → Database only (review later)
```

## Database Schema (Implemented)

### Programs Table
- Stores bug bounty program metadata
- Tracks in-scope and out-of-scope targets
- Last scope check timestamp

### Assets Table
- **The Heart of the System**
- Stores discovered assets (subdomains, IPs)
- HTTP metadata (status, length, title, tech stack)
- Response hash for change detection
- First seen / Last seen timestamps

### AssetChanges Table
- **The Diff Engine's Memory**
- Records every change detected
- Field-level granularity (what changed)
- Old value vs new value comparison
- Alert status tracking

### Vulnerabilities Table
- Nuclei findings
- Severity classification
- Request/response evidence
- Deduplication logic
- False positive marking

### Ports & Scans Tables
- Service discovery
- Job tracking

## Technology Stack Decisions

### Why Prefect over Airflow?
- ✅ Modern, Python-native
- ✅ Better async support
- ✅ Simpler deployment
- ✅ Built-in retry logic
- ✅ Rich UI for monitoring

### Why PostgreSQL over MongoDB?
- ✅ ACID transactions critical for state consistency
- ✅ Complex queries (JOINs for correlation)
- ✅ Strong typing with SQLAlchemy
- ✅ Better for time-series data (asset history)

### Why FastAPI over Flask?
- ✅ Async/await native
- ✅ Automatic API docs (OpenAPI)
- ✅ Pydantic validation built-in
- ✅ WebSocket support (real-time updates)

## Scanning Tool Integration Plan

### Passive Reconnaissance
```python
# Subfinder (Go binary)
subfinder -d target.com -all -json -o output.json

# Output parsing → PostgreSQL assets table
```

### Active Reconnaissance
```python
# puredns (masscan wrapper)
puredns resolve domains.txt -r resolvers.txt -w resolved.txt

# httpx (HTTP probing)
httpx -l resolved.txt -json -status-code -content-length -title -tech-detect
```

### Vulnerability Scanning
```python
# Nuclei
nuclei -l targets.txt -severity critical,high -json -o findings.json

# With rate limiting
nuclei -rate-limit 150 -bulk-size 50 -c 25
```

## Resource Estimation

### Single Program (Medium Size)
- **Subdomains**: ~1,000
- **Scan Time**: 15-30 minutes (with 10-node fleet)
- **Storage**: ~500 MB/month (including historical data)
- **Cost**: ~$2-5/month (DO droplets ephemeral)

### Multi-Program Setup (10 programs)
- **Assets**: ~10,000 subdomains
- **Daily Scans**: 2-4 hours
- **Storage**: ~5 GB/month
- **Cost**: ~$50-100/month

## Optimization Strategies

### 1. The Diff Engine (Implemented)
Saves 70-90% of scanning resources by:
- Skipping unchanged assets
- Targeted rescans for modified assets
- Full scans only for new discoveries

### 2. Fleet Auto-scaling
```python
if new_assets > 1000:
    fleet_size = 50  # Maximum
elif new_assets > 100:
    fleet_size = 20  # Medium
else:
    fleet_size = 5   # Minimum
```

### 3. Smart Scheduling
- **Hourly**: Scope monitor (API calls only)
- **Every 6 hours**: Quick recon (passive only)
- **Daily**: Full recon + vulnerability scan
- **Weekly**: Deep scan (all ports, permutations)

## Security Considerations

### API Key Management
- Store in environment variables (never commit)
- Use separate keys per service
- Rotate regularly

### Rate Limiting
- Respect program rules
- Built-in delays in scanners
- Monitor for blocks/bans

### Data Privacy
- Don't store sensitive findings in plain text
- Encrypt database at rest
- Secure webhook URLs

## Monitoring & Logging

### Application Logs
- Rich console output (development)
- Structured JSON logs (production)
- Log rotation (daily, max 30 days)

### Metrics to Track
- Assets discovered per day
- Scan duration
- Vulnerability count by severity
- False positive rate
- API call usage

## Development Phases

### ✅ Phase 1: Foundation (COMPLETE)
- [x] Database schema
- [x] Configuration system
- [x] Diff Engine
- [x] Repository pattern
- [x] Docker setup
- [x] CLI tool

### 🔄 Phase 2: Reconnaissance (NEXT)
- [ ] Subfinder integration
- [ ] DNS resolution workflow
- [ ] httpx integration
- [ ] Port scanning
- [ ] Screenshot capture

### ⏳ Phase 3: Vulnerability Scanning
- [ ] Nuclei integration
- [ ] Template management
- [ ] Interactsh OOB detection
- [ ] Result parsing & deduplication

### ⏳ Phase 4: Automation
- [ ] Prefect workflows
- [ ] Scheduling system
- [ ] Error handling & retries
- [ ] Progress tracking

### ⏳ Phase 5: Alerting
- [ ] Discord webhooks
- [ ] Pushover integration
- [ ] Severity-based routing
- [ ] Daily reports

### ⏳ Phase 6: Fleet Management
- [ ] Axiom integration
- [ ] DigitalOcean API
- [ ] Auto-scaling logic
- [ ] Cost tracking

### ⏳ Phase 7: Web Interface
- [ ] FastAPI backend
- [ ] Asset dashboard
- [ ] Vulnerability tracker
- [ ] Real-time updates

## Testing Strategy

### Unit Tests
```python
# Example: Test Diff Engine
async def test_diff_engine_new_asset():
    asset, is_new, changes = await diff.compare_and_update(...)
    assert is_new == True
    assert len(changes) == 0
```

### Integration Tests
- Database operations
- Scanner tool execution
- API endpoints

### End-to-End Tests
- Full scan workflow
- Alert delivery
- Fleet management

## Next Immediate Steps

1. **Create Scanner Wrapper Classes**
   ```
   src/scanners/subfinder.py
   src/scanners/httpx_scanner.py
   src/scanners/nuclei.py
   ```

2. **Build First Prefect Flow**
   ```python
   @flow(name="reconnaissance")
   async def recon_flow(program_id: int):
       # 1. Enumerate subdomains
       # 2. Resolve DNS
       # 3. Probe HTTP
       # 4. Run diff engine
       # 5. Return new/changed assets
   ```

3. **Implement Basic Alerting**
   ```python
   async def send_discord_alert(vuln: Vulnerability):
       webhook.send(f"🚨 {vuln.severity}: {vuln.name}")
   ```

## Performance Targets

- **Subdomain enumeration**: 1,000 domains in < 2 minutes
- **DNS resolution**: 10,000 domains in < 5 minutes
- **HTTP probing**: 1,000 URLs in < 3 minutes
- **Nuclei scan**: 100 targets (all templates) in < 10 minutes
- **Diff engine**: 1,000 assets compared in < 1 second

## Success Metrics

- **Coverage**: % of in-scope assets discovered
- **Speed**: Time from asset discovery to vuln detection
- **Accuracy**: False positive rate < 5%
- **Cost Efficiency**: $ per vulnerability found
- **Uptime**: > 99% availability

---

**Ready to continue with Phase 2?** Let's build the scanner integrations! 🚀
