# AutoBug Quick Reference Card

Quick reference for the most commonly used AutoBug commands.

## 🚀 Getting Started

```bash
# Start infrastructure
docker-compose up -d postgres redis

# Initialize database
alembic upgrade head

# Start web server
python run_web.py --reload

# Access dashboard
http://localhost:8000/dashboard
```

## 📋 Program Management

```bash
# Add a program
python -m src.cli add-program -p hackerone -h "program-handle" -n "Program Name"

# List all programs
python -m src.cli list-programs

# Update program
python -m src.cli update-program <id> --name "New Name"

# Delete program
python -m src.cli delete-program <id>
```

## 🔍 Reconnaissance

```bash
# Full reconnaissance scan
python -m src.cli scan full <program_id>

# Subdomain enumeration only
python -m src.cli scan subdomains <program_id>

# HTTP probing only
python -m src.cli scan http <program_id>

# Port scanning only
python -m src.cli scan ports <program_id>

# Test tool installation
python -m src.cli scan test-tools
```

## 🛡️ Vulnerability Scanning

```bash
# Scan for vulnerabilities
python -m src.cli vuln scan <program_id>

# Scan with specific severity
python -m src.cli vuln scan <program_id> --severity critical

# List vulnerabilities
python -m src.cli vuln list

# Filter by severity
python -m src.cli vuln list --severity high

# Mark as reported
python -m src.cli vuln mark-reported <vuln_id>

# Show vulnerability details
python -m src.cli vuln show <vuln_id>
```

## 📊 Scope Monitoring

```bash
# Fetch program scope
python -m src.cli scope fetch <program_id>

# Check for scope changes
python -m src.cli scope check <program_id>

# View scope history
python -m src.cli scope history <program_id>

# Validate asset against scope
python -m src.cli scope validate <program_id> example.com
```

## 🔔 Alerts

```bash
# Test alert configuration
python -m src.cli alert test

# Send test alert to Discord
python -m src.cli alert test --channel discord

# Send test alert to Slack
python -m src.cli alert test --channel slack

# View recent alerts
python -m src.cli alert list

# Configure alerts (interactive)
python -m src.cli alert setup-guide
```

## 🌐 Web Dashboard

```bash
# Start with auto-reload (development)
python run_web.py --reload

# Start on different port
python run_web.py --port 8080

# Start in production mode
ENVIRONMENT=production python run_web.py
```

### Dashboard URLs
- 🏠 **Main Dashboard**: http://localhost:8000/dashboard
- 📊 **Programs**: http://localhost:8000/programs
- 🔍 **Assets**: http://localhost:8000/assets
- 🛡️ **Vulnerabilities**: http://localhost:8000/vulnerabilities
- 🔔 **Alerts**: http://localhost:8000/alerts
- 📚 **API Docs**: http://localhost:8000/api/docs
- 📖 **ReDoc**: http://localhost:8000/api/redoc

## 🔌 API Examples

### Authentication
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# Get token for subsequent requests
export TOKEN="your_access_token"
```

### Programs
```bash
# List all programs
curl http://localhost:8000/api/programs \
  -H "Authorization: Bearer $TOKEN"

# Get program details
curl http://localhost:8000/api/programs/1 \
  -H "Authorization: Bearer $TOKEN"

# Create program
curl -X POST http://localhost:8000/api/programs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Example Corp","platform":"hackerone","handle":"example"}'
```

### Scans
```bash
# Start reconnaissance scan
curl -X POST http://localhost:8000/api/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"program_id":1,"scan_type":"full"}'

# Get scan status
curl http://localhost:8000/api/scans/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Vulnerabilities
```bash
# List vulnerabilities
curl http://localhost:8000/api/vulnerabilities \
  -H "Authorization: Bearer $TOKEN"

# Filter by severity
curl "http://localhost:8000/api/vulnerabilities?severity=critical" \
  -H "Authorization: Bearer $TOKEN"

# Export to CSV
curl "http://localhost:8000/api/export/vulnerabilities?format=csv" \
  -H "Authorization: Bearer $TOKEN" > vulnerabilities.csv
```

## 👥 User Management

```bash
# Create user (interactive)
python -m src.cli.admin create-user

# Create user (non-interactive)
python -m src.cli.admin create-user username email@example.com

# Create admin user
python -m src.cli.admin create-user username email@example.com admin

# List users
python -m src.cli.admin list-users

# Delete user
python -m src.cli.admin delete-user <user_id>
```

## 🗄️ Database

```bash
# Create migration
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

## 🐳 Docker

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart specific service
docker-compose restart app

# Rebuild and start
docker-compose up -d --build

# Remove all data (⚠️ destructive)
docker-compose down -v
```

## 🔧 Maintenance

```bash
# Update Nuclei templates
nuclei -update-templates

# Check scanning tools
python -m src.cli scan test-tools

# View application logs
tail -f logs/autobug.log

# Clear Redis cache
redis-cli FLUSHDB
```

## 📤 Export & Backup

```bash
# Export vulnerabilities to JSON
curl "http://localhost:8000/api/export/vulnerabilities?format=json" \
  -H "Authorization: Bearer $TOKEN" > vulns.json

# Export to CSV
curl "http://localhost:8000/api/export/vulnerabilities?format=csv" \
  -H "Authorization: Bearer $TOKEN" > vulns.csv

# Backup database
pg_dump autobug_db > backup_$(date +%Y%m%d).sql

# Restore database
psql autobug_db < backup_20260212.sql
```

## 🔍 Troubleshooting

```bash
# Check service health
curl http://localhost:8000/health

# Test database connection
python -c "from src.db.session import get_db; print('DB OK')"

# Test Redis connection
redis-cli ping

# Check Prefect server
curl http://localhost:4200/api/health

# View detailed errors
tail -f logs/autobug.log
```

## 📊 Statistics

```bash
# Get dashboard statistics (API)
curl http://localhost:8000/api/stats \
  -H "Authorization: Bearer $TOKEN"

# Get program statistics
curl http://localhost:8000/api/stats/programs/1 \
  -H "Authorization: Bearer $TOKEN"
```

## Environment Variables

```bash
# Development mode
export ENVIRONMENT=development
export DEBUG=true

# Production mode
export ENVIRONMENT=production
export DEBUG=false

# Custom database
export DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Custom API port
export API_PORT=8080
```

## 🔗 Useful Links

- **Documentation**: See README.md
- **API Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health
- **GitHub Issues**: Report bugs and request features

## 💡 Pro Tips

1. **Always test in development** before production
2. **Use environment variables** for secrets
3. **Run reconnaissance regularly** to catch new assets
4. **Set up alerts** to catch critical findings immediately
5. **Review scope changes** before scanning
6. **Export data regularly** for backup
7. **Update templates** weekly with `nuclei -update-templates`
8. **Monitor logs** for errors and issues

---

**Need more help?** Check the full documentation in the repository.
