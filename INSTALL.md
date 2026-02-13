# AutoBug Installation & Setup Guide

This guide will walk you through the complete setup process for AutoBug.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [First Run](#first-run)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **OS**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+ recommended)
- **Python**: 3.11 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 10GB free space
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7+

### Required Software

1. **Python 3.11+**
   ```bash
   python --version  # Should show 3.11 or higher
   ```

2. **PostgreSQL 15+**
   ```bash
   psql --version
   ```

3. **Redis 7+**
   ```bash
   redis-cli --version
   ```

4. **Go 1.21+** (for scanning tools)
   ```bash
   go version
   ```

5. **Git**
   ```bash
   git --version
   ```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/auto_bug_web.git
cd auto_bug_web
```

### 2. Set Up Python Environment

#### Using venv (recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Using conda (alternative)
```bash
conda create -n autobug python=3.11
conda activate autobug
pip install -r requirements.txt
```

### 3. Install Scanning Tools

AutoBug relies on several Go-based security tools.

#### Automated Installation

**Windows (PowerShell):**
```powershell
.\scripts\install_tools.ps1
```

**Linux/macOS:**
```bash
chmod +x scripts/install_tools.sh
./scripts/install_tools.sh
```

#### Manual Installation

If automated scripts fail, install tools manually:

```bash
# Subfinder - Subdomain enumeration
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# httpx - HTTP toolkit
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest

# Nuclei - Vulnerability scanner
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# Naabu - Port scanner
go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest

# Update Nuclei templates
nuclei -update-templates
```

Verify installation:
```bash
subfinder -version
httpx -version
nuclei -version
naabu -version
```

### 4. Set Up Database

#### Option A: Docker (Recommended)

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Verify they're running
docker-compose ps
```

#### Option B: Manual Setup

**PostgreSQL:**
```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database and user
CREATE DATABASE autobug_db;
CREATE USER autobug WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE autobug_db TO autobug;
\q
```

**Redis:**
```bash
# Start Redis (varies by OS)
# Ubuntu/Debian:
sudo systemctl start redis

# macOS:
brew services start redis

# Windows: run redis-server.exe
```

## Configuration

### 1. Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your favorite editor
nano .env  # or code .env, vim .env, etc.
```

### 2. Essential Configuration

Edit `.env` with your settings:

```bash
# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Database (update password!)
DATABASE_URL=postgresql+asyncpg://autobug:your_secure_password@localhost:5432/autobug_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Prefect (if using Docker Compose, use http://prefect-server:4200/api)
PREFECT_API_URL=http://localhost:4200/api
```

### 3. Optional: Alert Configuration

Add webhook URLs for alerts:

```bash
# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 4. Optional: Bug Bounty Platform APIs

```bash
# HackerOne (format: username:api_token)
HACKERONE_API_TOKEN=your_username:your_api_token

# Bugcrowd
BUGCROWD_API_TOKEN=your_api_token
```

### 5. Database Migration

Run database migrations to create tables:

```bash
alembic upgrade head
```

You should see output like:
```
INFO  [alembic.runtime.migration] Running upgrade -> 004
INFO  [alembic.runtime.migration] Running upgrade 004 -> 005
```

## First Run

### 1. Verify Installation

Test that all tools are properly installed:

```bash
python -m src.cli scan test-tools
```

Expected output:
```
✓ subfinder found
✓ httpx found
✓ nuclei found
✓ naabu found
All scanning tools are properly installed!
```

### 2. Start the Web Server

```bash
python run_web.py --reload
```

Access the dashboard at:
- 🏠 Dashboard: http://localhost:8000/dashboard
- 📚 API Docs: http://localhost:8000/api/docs
- 💚 Health: http://localhost:8000/health

### 3. Create Your First User (if authentication is enabled)

```bash
python -m src.cli.admin create-user
# Follow the prompts
```

### 4. Add Your First Program

```bash
python -m src.cli add-program -p hackerone -h "example" -n "Example Corp"
```

### 5. Run Reconnaissance

```bash
# Replace '1' with your program ID
python -m src.cli scan full 1
```

### 6. Scan for Vulnerabilities

```bash
python -m src.cli vuln scan 1
```

### 7. View Results

```bash
# Via CLI
python -m src.cli vuln list --severity high

# Via Web Dashboard
# Visit http://localhost:8000/dashboard
```

## Troubleshooting

### Database Connection Issues

**Error**: `could not connect to server`

**Solution**:
1. Verify PostgreSQL is running: `pg_isready`
2. Check your DATABASE_URL in `.env`
3. Ensure user has correct permissions

### Tool Not Found

**Error**: `subfinder: command not found`

**Solution**:
1. Verify Go is installed: `go version`
2. Check GOPATH is in PATH: `echo $PATH` (Linux/Mac) or `$env:PATH` (Windows)
3. Re-run installation script
4. Try manual installation

### Redis Connection Failed

**Error**: `Error connecting to Redis`

**Solution**:
1. Check Redis is running: `redis-cli ping` (should return PONG)
2. Verify REDIS_URL in `.env`
3. Start Redis if not running

### Permission Denied (Linux/macOS)

**Error**: `Permission denied` when running scanners

**Solution**:
```bash
# Some scanners need elevated privileges for raw sockets
sudo setcap cap_net_raw,cap_net_admin,cap_net_bind_service+eip $(which naabu)
```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
1. Ensure you're in the project root directory
2. Virtual environment is activated
3. Dependencies are installed: `pip install -r requirements.txt`

### Port Already in Use

**Error**: `Address already in use: 8000`

**Solution**:
```bash
# Find and kill process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS:
lsof -ti:8000 | xargs kill -9

# Or use a different port:
python run_web.py --port 8080
```

## Next Steps

- Read the [QUICKSTART.md](QUICKSTART.md) guide
- Configure alerts in [ALERT_GUIDE.md](ALERT_GUIDE.md)
- Learn about reconnaissance in [RECON_GUIDE.md](RECON_GUIDE.md)
- Explore the API at http://localhost:8000/api/docs

## Getting Help

- 📖 Check the [documentation](README.md#documentation)
- 🐛 [Report a bug](https://github.com/YOUR_USERNAME/auto_bug_web/issues/new?template=bug_report.md)
- 💡 [Request a feature](https://github.com/YOUR_USERNAME/auto_bug_web/issues/new?template=feature_request.md)
- 💬 Join discussions on GitHub

## Production Deployment

For production deployment, see [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md).

**Important Production Notes:**
- Use strong passwords and rotate them regularly
- Enable HTTPS/TLS
- Set `ENVIRONMENT=production` in `.env`
- Use a firewall to restrict database access
- Regular backups of PostgreSQL data
- Monitor logs and set up proper alerting
- Keep all dependencies updated
