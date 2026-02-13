# AutoBug API Usage Guide

## Quick Start

### 1. Start the Server
```bash
python run_web.py --reload
```

Server will be available at:
- **Dashboard**: http://localhost:8000/dashboard
- **API**: http://localhost:8000/api/
- **Docs**: http://localhost:8000/api/docs

### 2. Optional: Configure Authentication
Set an API key in your `.env` file:
```bash
API_KEY=your-secret-key-here
```

Then include it in requests:
```bash
curl -H "X-API-Key: your-secret-key-here" http://localhost:8000/api/programs
```

## API Endpoints

### Programs

**List all programs**:
```bash
curl http://localhost:8000/api/programs

# With filters
curl "http://localhost:8000/api/programs?platform=hackerone&is_active=true"
```

**Get program details**:
```bash
curl http://localhost:8000/api/programs/1
```

**Create a program**:
```bash
curl -X POST http://localhost:8000/api/programs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example Corp",
    "platform": "hackerone",
    "url": "https://hackerone.com/example-corp",
    "is_active": true
  }'
```

**Update a program**:
```bash
curl -X PATCH http://localhost:8000/api/programs/1 \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

**Delete a program**:
```bash
curl -X DELETE http://localhost:8000/api/programs/1
```

### Assets

**List assets**:
```bash
# All assets
curl http://localhost:8000/api/assets

# Filter by program
curl "http://localhost:8000/api/assets?program_id=1"

# Only alive, in-scope assets
curl "http://localhost:8000/api/assets?is_alive=true&in_scope=true"

# Assets with vulnerabilities
curl "http://localhost:8000/api/assets?has_vulnerabilities=true"
```

**Get asset details**:
```bash
curl http://localhost:8000/api/assets/1
```

### Vulnerabilities

**List vulnerabilities**:
```bash
# All vulnerabilities
curl http://localhost:8000/api/vulnerabilities

# Filter by severity
curl "http://localhost:8000/api/vulnerabilities?severity=critical"

# Unreported only
curl "http://localhost:8000/api/vulnerabilities?is_reported=false"

# New vulnerabilities in last 24h
curl "http://localhost:8000/api/vulnerabilities?new_only=true"

# For specific program
curl "http://localhost:8000/api/vulnerabilities?program_id=1"
```

**Get vulnerability details**:
```bash
curl http://localhost:8000/api/vulnerabilities/1
```

**Mark vulnerabilities as reported**:
```bash
curl -X POST http://localhost:8000/api/vulnerabilities/mark-reported \
  -H "Content-Type: application/json" \
  -d '{"vulnerability_ids": [1, 2, 3]}'
```

### Scans

**List scans**:
```bash
# All scans
curl http://localhost:8000/api/scans

# Filter by program
curl "http://localhost:8000/api/scans?program_id=1"

# Filter by status
curl "http://localhost:8000/api/scans?status=RUNNING"
```

**Get scan details**:
```bash
curl http://localhost:8000/api/scans/1
```

**Trigger a scan** (async, returns 202 Accepted):
```bash
# Full reconnaissance scan
curl -X POST http://localhost:8000/api/scans \
  -H "Content-Type: application/json" \
  -d '{
    "program_id": 1,
    "scan_type": "RECON_FULL"
  }'

# Quick reconnaissance scan
curl -X POST http://localhost:8000/api/scans \
  -H "Content-Type: application/json" \
  -d '{
    "program_id": 1,
    "scan_type": "RECON_QUICK"
  }'

# Vulnerability scan
curl -X POST http://localhost:8000/api/scans \
  -H "Content-Type: application/json" \
  -d '{
    "program_id": 1,
    "scan_type": "VULN_SCAN"
  }'

# Force scan even if recently scanned
curl -X POST http://localhost:8000/api/scans \
  -H "Content-Type: application/json" \
  -d '{
    "program_id": 1,
    "scan_type": "RECON_FULL",
    "force": true
  }'
```

### Alerts

**List alerts**:
```bash
# All alerts
curl http://localhost:8000/api/alerts

# Filter by channel
curl "http://localhost:8000/api/alerts?channel=discord"

# Filter by type
curl "http://localhost:8000/api/alerts?alert_type=new_vulnerability"

# Only failed alerts
curl "http://localhost:8000/api/alerts?sent_successfully=false"
```

**Get alert statistics**:
```bash
curl http://localhost:8000/api/alerts/stats
```

**Retry failed alerts**:
```bash
curl -X POST http://localhost:8000/api/alerts/retry-failed
```

**Test webhook**:
```bash
curl -X POST http://localhost:8000/api/alerts/test \
  -H "Content-Type: application/json" \
  -d '{"channel": "discord"}'
```

### Scope Monitoring

**Get scope history**:
```bash
# For a specific program
curl "http://localhost:8000/api/scope/history?program_id=1"

# Limit results
curl "http://localhost:8000/api/scope/history?program_id=1&limit=10"
```

**Trigger scope check** (async, returns 202 Accepted):
```bash
curl -X POST http://localhost:8000/api/scope/check \
  -H "Content-Type: application/json" \
  -d '{"program_id": 1}'
```

**Validate assets against scope**:
```bash
curl -X POST http://localhost:8000/api/scope/validate \
  -H "Content-Type: application/json" \
  -d '{
    "program_id": 1,
    "asset_values": ["example.com", "test.example.com", "192.168.1.1"]
  }'
```

### Statistics

**Dashboard statistics**:
```bash
curl http://localhost:8000/api/stats/dashboard
```

Response includes:
- Total programs and active programs
- Total assets, alive assets, in-scope assets, new assets (24h)
- Total vulnerabilities, new vulnerabilities (24h), by severity, unreported count
- Total scans, scans (24h), running scans
- Alerts sent (24h), failed alerts
- Scope changes (24h)
- Last scan, last vulnerability, last scope check timestamps

**Program-specific statistics**:
```bash
curl http://localhost:8000/api/stats/programs/1
```

Response includes:
- Asset breakdown by type
- Vulnerability breakdown by severity
- Scan history
- Recent findings (24h)

## Response Format

All successful API responses follow this format:

```json
{
  "success": true,
  "data": { ... },
  "message": "Success"
}
```

List endpoints include pagination info:
```json
{
  "success": true,
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 50
  }
}
```

Error responses:
```json
{
  "success": false,
  "error": "Error message",
  "details": "Additional error details"
}
```

## Query Parameters

### Common Filters
- `program_id` - Filter by program ID
- `limit` - Limit results (default: 100)
- `offset` - Offset for pagination (default: 0)

### Asset Filters
- `asset_type` - domain, subdomain, url, ip
- `is_alive` - true/false
- `in_scope` - true/false
- `has_vulnerabilities` - true/false

### Vulnerability Filters
- `severity` - critical, high, medium, low, info
- `is_reported` - true/false
- `new_only` - true (last 24h)

### Scan Filters
- `status` - PENDING, RUNNING, COMPLETED, FAILED, CANCELLED

### Alert Filters
- `channel` - discord, slack
- `alert_type` - new_asset, new_vulnerability, scope_change, scan_complete, scan_failed
- `sent_successfully` - true/false

## Authentication

### Development Mode (No Auth)
By default, authentication is disabled for development. All requests work without headers.

### API Key Authentication
1. Set environment variable:
   ```bash
   export API_KEY=your-secret-key
   ```

2. Include in requests:
   ```bash
   curl -H "X-API-Key: your-secret-key" http://localhost:8000/api/programs
   ```

### Future: JWT Authentication
Structure is in place for JWT implementation. Will support:
- User login with username/password
- Token issuance
- Token refresh
- Role-based access control

## Rate Limiting

Currently no rate limiting is enforced. For production, consider implementing:
- Per-IP rate limiting
- Per-user rate limiting
- Burst protection

## Examples with Python

### Using `requests` library:

```python
import requests

BASE_URL = "http://localhost:8000/api"
API_KEY = "your-secret-key"  # Optional

headers = {"X-API-Key": API_KEY} if API_KEY else {}

# List programs
response = requests.get(f"{BASE_URL}/programs", headers=headers)
programs = response.json()["data"]["items"]

# Trigger scan
response = requests.post(
    f"{BASE_URL}/scans",
    headers=headers,
    json={"program_id": 1, "scan_type": "RECON_FULL"}
)
print(f"Scan triggered: {response.status_code}")

# Get dashboard stats
response = requests.get(f"{BASE_URL}/stats/dashboard", headers=headers)
stats = response.json()["data"]
print(f"Total vulnerabilities: {stats['total_vulnerabilities']}")
print(f"Critical: {stats['critical_count']}")
```

### Using `httpx` (async):

```python
import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # List vulnerabilities
        response = await client.get(
            "http://localhost:8000/api/vulnerabilities",
            params={"severity": "critical", "is_reported": False}
        )
        vulns = response.json()["data"]["items"]
        
        # Mark as reported
        vuln_ids = [v["id"] for v in vulns]
        response = await client.post(
            "http://localhost:8000/api/vulnerabilities/mark-reported",
            json={"vulnerability_ids": vuln_ids}
        )
        print(f"Marked {len(vuln_ids)} vulnerabilities as reported")

asyncio.run(main())
```

## WebSocket/SSE (Future)

Planned for real-time updates:

```javascript
// Server-Sent Events for scan progress
const eventSource = new EventSource('/api/scans/1/progress');
eventSource.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  console.log(`Scan progress: ${progress.percent}%`);
};

// WebSocket for real-time vulnerability feed
const ws = new WebSocket('ws://localhost:8000/api/feed');
ws.onmessage = (event) => {
  const vuln = JSON.parse(event.data);
  console.log(`New vulnerability: ${vuln.severity} - ${vuln.template_name}`);
};
```

## HTMX Integration (Web UI)

The web dashboard uses HTMX for dynamic updates:

```html
<!-- Auto-refresh table every 10s -->
<div hx-get="/api/scans" hx-trigger="every 10s" hx-swap="innerHTML">
  <!-- Table content -->
</div>

<!-- Trigger scan on button click -->
<button hx-post="/api/scans" 
        hx-vals='{"program_id": 1, "scan_type": "RECON_FULL"}'
        hx-swap="none">
  Scan
</button>
```

## Support

- **API Documentation**: http://localhost:8000/api/docs (interactive Swagger UI)
- **Alternative Docs**: http://localhost:8000/api/redoc (ReDoc UI)
- **Health Check**: http://localhost:8000/health

## Best Practices

1. **Always check `success` field** in responses
2. **Use pagination** for large datasets (limit/offset)
3. **Handle 202 Accepted** for async operations (scans, scope checks)
4. **Poll status endpoints** for long-running operations
5. **Use filters** to reduce response size
6. **Cache static data** (program lists, etc.)
7. **Implement retries** for network errors
8. **Use batch operations** (mark-reported) when possible
