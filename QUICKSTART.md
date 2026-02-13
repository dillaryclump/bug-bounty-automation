# AutoBug Quick Start Guide

Get AutoBug up and running in 10 minutes.

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Git

## Installation

### 1. Clone and Setup

```powershell
# Clone repository
git clone <repository-url> auto_bug_web
cd auto_bug_web

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Database

```powershell
# Create PostgreSQL database
psql -U postgres
CREATE DATABASE autobug;
CREATE USER autobug_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE autobug TO autobug_user;
\q
```

### 3. Environment Variables

Create `.env` file:

```env
# Database
DATABASE_URL=postgresql+asyncpg://autobug_user:your_password@localhost:5432/autobug

# API
API_KEY=your-secret-api-key-here-change-this
SECRET_KEY=your-jwt-secret-key-here-change-this

# CORS (optional)
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# Development mode (optional)
DEV_MODE=true
```

### 4. Initialize Database

```powershell
# Run migrations
alembic upgrade head
```

### 5. Create Admin User

```powershell
# Create your first admin user
python -m src.cli.admin create-admin

# Follow the prompts to set username, email, password
```

### 6. Start the Server

```powershell
# Development server with hot reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at:
- **API Docs**: http://localhost:8000/api/docs
- **Dashboard**: http://localhost:8000/
- **Health Check**: http://localhost:8000/health

## First Steps

### 1. Login via API

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

Save the `access_token` from the response.

### 2. Create Your First Program

```bash
curl -X POST http://localhost:8000/api/programs \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "HackerOne VDP",
    "platform": "hackerone",
    "url": "https://hackerone.com/security",
    "is_active": true
  }'
```

### 3. Add Assets

```bash
curl -X POST http://localhost:8000/api/assets \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "program_id": 1,
    "asset_type": "domain",
    "value": "hackerone.com",
    "in_scope": true
  }'
```

### 4. Run a Scan

```bash
curl -X POST http://localhost:8000/api/scans \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "program_id": 1,
    "scan_type": "nuclei",
    "target": "hackerone.com"
  }'
```

### 5. View Results

```bash
# List vulnerabilities
curl http://localhost:8000/api/vulnerabilities \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# View in browser
# Go to http://localhost:8000/vulnerabilities
```

## Common Tasks

### Create Additional Users

```powershell
# Create regular user
python -m src.cli.admin create-user alice alice@example.com

# Create admin user
python -m src.cli.admin create-user bob bob@example.com admin
```

### List All Users

```powershell
python -m src.cli.admin list-users
```

### Reset Password

```powershell
python -m src.cli.admin reset-password username
```

### Export Data

```bash
# Export unreported vulnerabilities to CSV
curl "http://localhost:8000/api/export/vulnerabilities?format=csv&is_reported=false" \
  -H "Authorization: Bearer TOKEN" > unreported.csv

# Export programs to JSON
curl "http://localhost:8000/api/export/programs?format=json" \
  -H "Authorization: Bearer TOKEN" > programs.json
```

### Monitor Real-Time (WebSocket)

```javascript
// In browser console or JS file
const ws = new WebSocket('ws://localhost:8000/api/ws/feed?topics=vulnerabilities,scans');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data);
};
```

## Web Dashboard

Visit http://localhost:8000/ to access the web dashboard:

- **Programs**: Manage bug bounty programs
- **Assets**: View and manage discovered assets
- **Vulnerabilities**: Browse and filter findings
- **Scans**: Track scan progress and history
- **Alerts**: View alert notifications

## API Documentation

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## Configuration

### Prefect (Workflow Engine)

```powershell
# Start Prefect server (optional, for workflows)
prefect server start

# In another terminal, start Prefect agent
prefect agent start -q default
```

### Discord Alerts (Optional)

Add to `.env`:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK
```

### Slack Alerts (Optional)

Add to `.env`:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR_WEBHOOK
```

## Troubleshooting

### Database Connection Error

```powershell
# Verify PostgreSQL is running
psql -U postgres -c "SELECT version();"

# Check database exists
psql -U postgres -l | findstr autobug
```

### Import Errors

```powershell
# Ensure virtual environment is activated
venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Rate Limit Issues

If you're hitting rate limits during testing, edit [src/api/main.py](src/api/main.py#L60):

```python
# Comment out or adjust rate limiting
# app.add_middleware(
#     RateLimitMiddleware,
#     requests_per_minute=60,
#     burst_size=10
# )
```

### Port Already in Use

```powershell
# Use different port
uvicorn src.api.main:app --reload --port 8001
```

## Production Deployment

For production deployment:

1. **Set proper environment variables**
   - Change `SECRET_KEY` to a secure random value
   - Change `API_KEY` to a secure random value
   - Set `DEV_MODE=false`

2. **Use production ASGI server**
   ```powershell
   pip install gunicorn
   gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

3. **Set up reverse proxy** (Nginx, Caddy)

4. **Enable HTTPS**

5. **Configure rate limiting** with Redis for multi-instance setup

6. **Set up monitoring** (Sentry, Datadog, etc.)

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed production deployment instructions.

## Next Steps

- Read [docs/API_EXAMPLES.md](docs/API_EXAMPLES.md) for comprehensive API usage
- See [PHASE7_COMPLETE.md](PHASE7_COMPLETE.md) for advanced features documentation
- Configure workflow automation with Prefect
- Set up alert integrations (Discord, Slack)
- Explore bulk operations for efficient management
- Set up real-time monitoring with WebSocket

## Resources

- **Project Documentation**: See `docs/` folder
- **Phase Completion Docs**: `PHASE*_COMPLETE.md` files
- **API Reference**: http://localhost:8000/api/docs
- **Database Schema**: See `src/db/models.py`

## Getting Help

If you encounter issues:

1. Check the logs in the terminal
2. Verify database connection
3. Ensure all dependencies are installed
4. Check environment variables in `.env`
5. Review API documentation at `/api/docs`

---

**Congratulations!** You now have AutoBug running locally. Happy hunting! 🎯
