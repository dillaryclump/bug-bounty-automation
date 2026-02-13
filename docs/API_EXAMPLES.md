# AutoBug API Examples

Comprehensive API usage examples for all endpoints.

## Table of Contents

1. [Authentication](#authentication)
2. [Programs](#programs)
3. [Assets](#assets)
4. [Vulnerabilities](#vulnerabilities)
5. [Scans](#scans)
6. [Alerts](#alerts)
7. [WebSocket](#websocket)
8. [Export](#export)
9. [Bulk Operations](#bulk-operations)

---

## Authentication

### Register New User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "securepass123",
    "full_name": "Alice Smith",
    "role": "user"
  }'
```

Response:
```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com",
  "full_name": "Alice Smith",
  "role": "user",
  "is_active": true,
  "is_verified": false,
  "created_at": "2026-02-15T10:30:00Z"
}
```

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "securepass123"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### Get Current User

```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1Qi..."
```

### Refresh Access Token

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJ0eXAiOiJKV1Qi..."
  }'
```

### Change Password

```bash
curl -X POST http://localhost:8000/api/auth/me/change-password \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "oldpass123",
    "new_password": "newpass456"
  }'
```

### List Users (Admin Only)

```bash
curl http://localhost:8000/api/auth/users \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

## Programs

### Create Program

```bash
curl -X POST http://localhost:8000/api/programs \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "HackerOne VDP",
    "platform": "hackerone",
    "url": "https://hackerone.com/security",
    "is_active": true,
    "scope_url": "https://hackerone.com/security/policy_scopes"
  }'
```

### List Programs

```bash
# All programs
curl http://localhost:8000/api/programs \
  -H "Authorization: Bearer TOKEN"

# Active programs only
curl "http://localhost:8000/api/programs?is_active=true" \
  -H "Authorization: Bearer TOKEN"

# Pagination
curl "http://localhost:8000/api/programs?skip=0&limit=10" \
  -H "Authorization: Bearer TOKEN"
```

### Get Program

```bash
curl http://localhost:8000/api/programs/1 \
  -H "Authorization: Bearer TOKEN"
```

### Update Program

```bash
curl -X PUT http://localhost:8000/api/programs/1 \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "HackerOne VDP (Updated)",
    "is_active": true
  }'
```

### Delete Program

```bash
curl -X DELETE http://localhost:8000/api/programs/1 \
  -H "Authorization: Bearer TOKEN"
```

---

## Assets

### Create Asset

```bash
curl -X POST http://localhost:8000/api/assets \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "program_id": 1,
    "asset_type": "domain",
    "value": "example.com",
    "in_scope": true,
    "is_alive": true
  }'
```

### List Assets

```bash
# All assets for program
curl "http://localhost:8000/api/assets?program_id=1" \
  -H "Authorization: Bearer TOKEN"

# In-scope only
curl "http://localhost:8000/api/assets?program_id=1&in_scope=true" \
  -H "Authorization: Bearer TOKEN"

# Live assets only
curl "http://localhost:8000/api/assets?is_alive=true" \
  -H "Authorization: Bearer TOKEN"

# Filter by type
curl "http://localhost:8000/api/assets?asset_type=subdomain" \
  -H "Authorization: Bearer TOKEN"
```

### Get Asset

```bash
curl http://localhost:8000/api/assets/1 \
  -H "Authorization: Bearer TOKEN"
```

### Update Asset

```bash
curl -X PUT http://localhost:8000/api/assets/1 \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "in_scope": false,
    "is_alive": false
  }'
```

### Delete Asset

```bash
curl -X DELETE http://localhost:8000/api/assets/1 \
  -H "Authorization: Bearer TOKEN"
```

---

## Vulnerabilities

### Create Vulnerability

```bash
curl -X POST http://localhost:8000/api/vulnerabilities \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_id": 1,
    "template_name": "CVE-2024-1234",
    "severity": "high",
    "host": "example.com",
    "matched_at": "https://example.com/vuln",
    "type": "cve",
    "curl_command": "curl https://example.com/vuln",
    "description": "High severity vulnerability found",
    "is_reported": false
  }'
```

### List Vulnerabilities

```bash
# All vulnerabilities
curl http://localhost:8000/api/vulnerabilities \
  -H "Authorization: Bearer TOKEN"

# Filter by severity
curl "http://localhost:8000/api/vulnerabilities?severity=critical" \
  -H "Authorization: Bearer TOKEN"

# Filter by scan
curl "http://localhost:8000/api/vulnerabilities?scan_id=1" \
  -H "Authorization: Bearer TOKEN"

# Unreported only
curl "http://localhost:8000/api/vulnerabilities?is_reported=false" \
  -H "Authorization: Bearer TOKEN"

# Multiple filters
curl "http://localhost:8000/api/vulnerabilities?severity=high&is_reported=false&type=cve" \
  -H "Authorization: Bearer TOKEN"
```

### Get Vulnerability

```bash
curl http://localhost:8000/api/vulnerabilities/1 \
  -H "Authorization: Bearer TOKEN"
```

### Update Vulnerability (Mark as Reported)

```bash
curl -X PUT http://localhost:8000/api/vulnerabilities/1 \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_reported": true,
    "reported_at": "2026-02-15T14:30:00Z"
  }'
```

### Delete Vulnerability

```bash
curl -X DELETE http://localhost:8000/api/vulnerabilities/1 \
  -H "Authorization: Bearer TOKEN"
```

---

## Scans

### Create Scan

```bash
curl -X POST http://localhost:8000/api/scans \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "program_id": 1,
    "scan_type": "nuclei",
    "target": "example.com",
    "status": "pending"
  }'
```

### List Scans

```bash
# All scans
curl http://localhost:8000/api/scans \
  -H "Authorization: Bearer TOKEN"

# Filter by program
curl "http://localhost:8000/api/scans?program_id=1" \
  -H "Authorization: Bearer TOKEN"

# Filter by status
curl "http://localhost:8000/api/scans?status=completed" \
  -H "Authorization: Bearer TOKEN"

# Filter by scan type
curl "http://localhost:8000/api/scans?scan_type=nuclei" \
  -H "Authorization: Bearer TOKEN"
```

### Get Scan

```bash
curl http://localhost:8000/api/scans/1 \
  -H "Authorization: Bearer TOKEN"
```

### Update Scan

```bash
curl -X PUT http://localhost:8000/api/scans/1 \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "ended_at": "2026-02-15T15:00:00Z",
    "vulnerabilities_found": 5
  }'
```

### Delete Scan

```bash
curl -X DELETE http://localhost:8000/api/scans/1 \
  -H "Authorization: Bearer TOKEN"
```

---

## Alerts

### Create Alert

```bash
curl -X POST http://localhost:8000/api/alerts \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vulnerability_id": 1,
    "alert_type": "discord",
    "status": "sent",
    "message": "Critical vulnerability found on example.com"
  }'
```

### List Alerts

```bash
# All alerts
curl http://localhost:8000/api/alerts \
  -H "Authorization: Bearer TOKEN"

# Filter by status
curl "http://localhost:8000/api/alerts?status=sent" \
  -H "Authorization: Bearer TOKEN"

# Filter by type
curl "http://localhost:8000/api/alerts?alert_type=discord" \
  -H "Authorization: Bearer TOKEN"
```

### Get Alert

```bash
curl http://localhost:8000/api/alerts/1 \
  -H "Authorization: Bearer TOKEN"
```

---

## WebSocket

### JavaScript WebSocket Client

```javascript
// Connect to event feed
const ws = new WebSocket('ws://localhost:8000/api/ws/feed?topics=vulnerabilities,scans');

ws.onopen = () => {
  console.log('Connected to WebSocket');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data);
  
  switch (data.event) {
    case 'new_vulnerability':
      console.log('New vulnerability:', data.data);
      // Update UI
      break;
    
    case 'scan_progress':
      console.log(`Scan ${data.data.scan_id}: ${data.data.progress}%`);
      // Update progress bar
      break;
    
    case 'scope_change':
      console.log('Scope changed:', data.data);
      // Refresh scope list
      break;
    
    case 'alert_sent':
      console.log('Alert sent:', data.data);
      // Show notification
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket closed');
};

// Subscribe to additional topic
ws.send(JSON.stringify({
  action: 'subscribe',
  topic: 'alerts'
}));

// Unsubscribe from topic
ws.send(JSON.stringify({
  action: 'unsubscribe',
  topic: 'scans'
}));

// Ping for keepalive
setInterval(() => {
  ws.send(JSON.stringify({ action: 'ping' }));
}, 30000);
```

### Python WebSocket Client

```python
import asyncio
import websockets
import json

async def listen_to_feed():
    uri = "ws://localhost:8000/api/ws/feed?topics=vulnerabilities,scans"
    
    async with websockets.connect(uri) as websocket:
        # Connection confirmation
        msg = await websocket.recv()
        print(f"Connected: {msg}")
        
        # Listen for events
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                
                event = data["event"]
                payload = data["data"]
                
                if event == "new_vulnerability":
                    print(f"🔴 NEW VULN: {payload['severity']} - {payload['template_name']}")
                    print(f"   Host: {payload['host']}")
                    print(f"   URL: {payload['matched_at']}")
                
                elif event == "scan_progress":
                    print(f"⏳ Scan {payload['scan_id']}: {payload['progress']}%")
                
                elif event == "scope_change":
                    print(f"🎯 Scope changed: {payload['change_type']}")
                
                elif event == "alert_sent":
                    print(f"📢 Alert sent: {payload['message']}")
            
            except websockets.ConnectionClosed:
                print("Connection closed")
                break

asyncio.run(listen_to_feed())
```

### Track Specific Scan

```javascript
const scanId = 123;
const ws = new WebSocket(`ws://localhost:8000/api/ws/scans/${scanId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.event === 'scan_progress') {
    const progress = data.data.progress;
    const status = data.data.status;
    console.log(`Scan progress: ${progress}% - ${status}`);
    
    // Update progress bar
    document.getElementById('progress-bar').style.width = `${progress}%`;
  }
};
```

---

## Export

### Export as JSON

```bash
# Export vulnerabilities
curl "http://localhost:8000/api/export/vulnerabilities?format=json&severity=critical" \
  -H "Authorization: Bearer TOKEN" > critical_vulns.json

# Export programs
curl "http://localhost:8000/api/export/programs?format=json&is_active=true" \
  -H "Authorization: Bearer TOKEN" > active_programs.json

# Export assets
curl "http://localhost:8000/api/export/assets?format=json&in_scope=true&is_alive=true" \
  -H "Authorization: Bearer TOKEN" > live_inscope_assets.json
```

### Export as CSV

```bash
# Export vulnerabilities to CSV
curl "http://localhost:8000/api/export/vulnerabilities?format=csv&is_reported=false" \
  -H "Authorization: Bearer TOKEN" > unreported_vulns.csv

# Export scans to CSV
curl "http://localhost:8000/api/export/scans?format=csv&status=completed" \
  -H "Authorization: Bearer TOKEN" > completed_scans.csv

# Export alerts to CSV
curl "http://localhost:8000/api/export/alerts?format=csv" \
  -H "Authorization: Bearer TOKEN" > all_alerts.csv
```

### Export with Filters

```bash
# Export high/critical vulnerabilities from last 7 days
curl "http://localhost:8000/api/export/vulnerabilities?format=csv&severity=critical,high&is_reported=false" \
  -H "Authorization: Bearer TOKEN" > recent_high_vulns.csv

# Export all in-scope live assets for specific program
curl "http://localhost:8000/api/export/assets?format=json&program_id=1&in_scope=true&is_alive=true" \
  -H "Authorization: Bearer TOKEN" > program1_assets.json
```

---

## Bulk Operations

### Bulk Mark Vulnerabilities as Reported

```bash
curl -X POST http://localhost:8000/api/bulk/vulnerabilities/mark-reported \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
  }'
```

Response:
```json
{
  "success": true,
  "message": "Marked 10 vulnerabilities as reported",
  "updated_count": 10,
  "total_requested": 10
}
```

### Bulk Delete Vulnerabilities

```bash
curl -X DELETE http://localhost:8000/api/bulk/vulnerabilities \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ids": [15, 16, 17, 18, 19, 20]
  }'
```

### Bulk Update Asset Scope

```bash
curl -X POST http://localhost:8000/api/bulk/assets/scope \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ids": [100, 101, 102, 103],
    "in_scope": false
  }'
```

### Bulk Delete Assets

```bash
curl -X DELETE http://localhost:8000/api/bulk/assets \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ids": [200, 201, 202]
  }'
```

### Bulk Update Program Status

```bash
# Deactivate multiple programs
curl -X POST http://localhost:8000/api/bulk/programs/status \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ids": [5, 6, 7],
    "is_active": false
  }'

# Activate multiple programs
curl -X POST http://localhost:8000/api/bulk/programs/status \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ids": [8, 9, 10],
    "is_active": true
  }'
```

### Bulk Delete Programs

```bash
curl -X DELETE http://localhost:8000/api/bulk/programs \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ids": [11, 12]
  }'
```

**Note**: Deleting programs will cascade delete all associated assets, scans, and vulnerabilities.

---

## Error Handling

### Authentication Errors

```json
// 401 Unauthorized - Invalid or expired token
{
  "detail": "Could not validate credentials"
}

// 403 Forbidden - Insufficient permissions
{
  "detail": "Insufficient permissions"
}
```

### Rate Limiting

```bash
# When rate limit exceeded (429 Too Many Requests)
curl http://localhost:8000/api/programs \
  -H "Authorization: Bearer TOKEN"
```

Response:
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "detail": "Too many requests. Please try again in 45 seconds."
}
```

Headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1708012800
Retry-After: 45
```

### Validation Errors

```json
// 422 Unprocessable Entity
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## Best Practices

### Token Management

1. Store tokens securely (not in localStorage for sensitive apps)
2. Refresh access token before expiration
3. Handle 401 errors by refreshing token
4. Logout = discard tokens (server doesn't track them)

### Rate Limiting

1. Check `X-RateLimit-Remaining` header
2. Respect `Retry-After` header when rate limited
3. Implement exponential backoff for retries
4. Use bulk endpoints for multiple operations

### WebSocket

1. Implement reconnection logic
2. Send periodic ping messages (30s recommended)
3. Subscribe only to needed topics
4. Handle connection errors gracefully

### Export

1. Use filters to limit export size
2. Export maximum 10,000 items per request
3. Use CSV for Excel compatibility
4. Use JSON for programmatic processing

---

## Complete Workflows

### New Vulnerability Workflow

```bash
# 1. Scan completes and creates vulnerabilities
# 2. List unreported critical/high vulnerabilities
curl "http://localhost:8000/api/vulnerabilities?is_reported=false&severity=critical,high" \
  -H "Authorization: Bearer TOKEN"

# 3. Export to CSV for review
curl "http://localhost:8000/api/export/vulnerabilities?format=csv&is_reported=false&severity=critical,high" \
  -H "Authorization: Bearer TOKEN" > review.csv

# 4. After reporting, mark as reported in bulk
curl -X POST http://localhost:8000/api/bulk/vulnerabilities/mark-reported \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ids": [1,2,3,4,5]}'
```

### Program Setup Workflow

```bash
# 1. Create program
curl -X POST http://localhost:8000/api/programs \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Example VDP", "platform": "bugcrowd", "url": "https://example.com", "is_active": true}'

# 2. Add assets
curl -X POST http://localhost:8000/api/assets \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"program_id": 1, "asset_type": "domain", "value": "example.com", "in_scope": true}'

# 3. Start scan
curl -X POST http://localhost:8000/api/scans \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"program_id": 1, "scan_type": "nuclei", "target": "example.com"}'

# 4. Monitor via WebSocket
# Connect to ws://localhost:8000/api/ws/scans/1
```

---

For more details, see [PHASE7_COMPLETE.md](../PHASE7_COMPLETE.md)
