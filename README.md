# AutoBug - Automated Bug Bounty Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

🐛 A state-of-the-art automated bug bounty reconnaissance and vulnerability scanning platform with persistent state tracking, intelligent change detection, and a modern web interface.

> **⚠️ Important**: This tool is designed for authorized security testing only. Always ensure you have explicit permission before scanning any targets. Unauthorized scanning may be illegal in your jurisdiction.

## 🎯 Project Status

**Current Version**: 1.0.0  
**Status**: Beta - Needs Testing ⚠️  
**Total Lines of Code**: ~16,400+  
**Last Updated**: February 2026

> **⚠️ Testing Status**: This project requires comprehensive testing before production use. Test suites need to be completed and all features should be thoroughly validated in a development environment.

Built with ❤️ for the bug bounty community

## ✨ Features

### Core Capabilities

| Feature | Description | Status |
|---------|-------------|--------|
| 🔍 **Reconnaissance** | Subdomain enumeration, DNS resolution, HTTP probing | ✅ Complete |
| 🛡️ **Vulnerability Scanning** | Nuclei integration with 5,000+ templates | ✅ Complete |
| 📊 **Change Detection** | Intelligent diff engine tracks asset changes | ✅ Complete |
| 🎯 **Scope Monitoring** | Multi-platform scope tracking (HackerOne, Bugcrowd) | ✅ Complete |
| 🔔 **Multi-Channel Alerts** | Discord, Slack, with severity-based routing | ✅ Complete |
| 🌐 **Web Dashboard** | Modern UI with real-time updates | ✅ Complete |
| 🔌 **REST API** | 20+ endpoints with auto-generated documentation | ✅ Complete |
| 🔐 **Authentication** | JWT-based auth with role-based access control | ✅ Complete |
| 💾 **Database** | PostgreSQL with async SQLAlchemy ORM | ✅ Complete |
| 🚀 **Workflow Engine** | Prefect orchestration for complex workflows | ✅ Complete |
| 📦 **Docker Support** | Complete Docker Compose setup | ✅ Complete |
| 📤 **Data Export** | CSV and JSON export functionality | ✅ Complete |

### Scanning Tools Integrated

- **Subfinder** - Fast subdomain enumeration
- **httpx** - HTTP toolkit for probing and metadata collection  
- **Nuclei** - Vulnerability scanner with extensive template library
- **Naabu** - Port scanner for service discovery
- **Interactsh** - Out-of-band interaction detection

### Alerting & Notifications

- 🔔 Real-time alerts for critical findings
- 📊 Daily summary reports
- 📈 Weekly digest reports  
- 🎯 Severity-based routing
- 🔄 Alert batching and deduplication
- 📱 Multiple channels (Discord, Slack)  

## 🚀 Quick Start

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Configure Environment
```powershell
cp .env.example .env
# Edit .env with your settings (database, API keys, webhooks)
```

### 3. Initialize Database
```powershell
python -m src.cli.main init-db
```

### 4. Start Web Dashboard
```powershell
python run_web.py --reload
```

**Access**:
- 🏠 **Dashboard**: http://localhost:8000/dashboard
- 📚 **API Docs**: http://localhost:8000/api/docs
- 💚 **Health**: http://localhost:8000/health

## 🏗️ Architecture

- **The Brain**: Persistent server with PostgreSQL database and Prefect orchestration
- **The API**: FastAPI REST API with async support and background tasks
- **The Dashboard**: Server-side rendered web UI with HTMX for interactivity
- **The Scanners**: Integrated tools (Subfinder, Nuclei, httpx, Naabu)
- **The Diff Engine**: Change detection comparing current vs. historical state
- **The Alerting**: Multi-channel notifications (Discord, Slack)

## 🛠️ Tech Stack

- **Web Framework**: FastAPI 0.109.0 (async)
- **Frontend**: Jinja2 templates + HTMX
- **Orchestration**: Prefect 2.14.21 (workflow management)
- **Database**: PostgreSQL 15+ with asyncpg driver
- **ORM**: SQLAlchemy 2.0 (async)
- **Scanning Tools**: Subfinder, Nuclei, httpx, Naabu
- **CLI**: Typer + Rich
- **Deployment**: Docker Compose ready

## Project Structure

```
auto_bug_web/
├── src/
│   ├── api/              # FastAPI application
│   ├── core/             # Core business logic
│   ├── db/               # Database models and connections
│   ├── scanners/         # Scanner integrations
│   ├── workflows/        # Prefect workflows
│   ├── alerting/         # Alert management
│   └── utils/            # Utilities
├── migrations/           # Alembic database migrations
├── config/              # Configuration files
├── docker/              # Docker configurations
├── scripts/             # Utility scripts
└── tests/               # Test suite
```

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose
- **Go 1.21+** (for scanning tools)

### Quick Start

1. **Install Python dependencies**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Install scanning tools**
   ```powershell
   # Windows
   .\scripts\install_tools.ps1
   
   # Linux/macOS
   chmod +x scripts/install_tools.sh
   ./scripts/install_tools.sh
   ```
   
   See [INSTALL_TOOLS.md](INSTALL_TOOLS.md) for detailed instructions.

3. **Start infrastructure**
   ```powershell
   docker-compose up -d postgres redis
   ```

4. **Initialize database**
   ```powershell
   cp .env.example .env
   # Edit .env with your settings
   
   # Run database migrations
   alembic upgrade head
   ```

5. **Configure alerts (optional)**
   ```powershell
   # Add webhook URLs to .env
   # DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   # SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   
   # Test webhooks
   python -m src.cli alert test
   ```

6. **Add a program and start hunting!**
   ```powershell
   # Test tools installation
   python -m src.cli scan test-tools
   
   # Add your first program
   python -m src.cli add-program -p hackerone -h "example" -n "Example Corp"
   
   # Run reconnaissance
   python -m src.cli scan full 1
   
   # Scan for vulnerabilities
   python -m src.cli vuln scan 1
   
   # View and manage findings
   python -m src.cli vuln list --severity high
   
   # Configure and test alerts
   python -m src.cli alert setup-guide
   python -m src.cli alert test
   ```

## 📚 Documentation

### Core Guides
- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture and design
- **[INSTALL_TOOLS.md](INSTALL_TOOLS.md)** - Scanner tool installation guide
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Production deployment guide

### Feature Guides
- **[RECON_GUIDE.md](RECON_GUIDE.md)** - Reconnaissance pipeline usage
- **[VULN_GUIDE.md](VULN_GUIDE.md)** - Vulnerability scanning guide
- **[ALERT_GUIDE.md](ALERT_GUIDE.md)** - Alert system configuration
- **[SCOPE_GUIDE.md](SCOPE_GUIDE.md)** - Scope monitoring guide
- **[CLI_REFERENCE.md](CLI_REFERENCE.md)** - Command reference
- **[API_GUIDE.md](API_GUIDE.md)** - REST API documentation

### Development History
- [PHASE2_COMPLETE.md](PHASE2_COMPLETE.md) - Reconnaissance system
- [PHASE3_COMPLETE.md](PHASE3_COMPLETE.md) - Vulnerability scanning
- [PHASE4_COMPLETE.md](PHASE4_COMPLETE.md) - Alerting system
- [PHASE5_COMPLETE.md](PHASE5_COMPLETE.md) - Scope monitoring
- [PHASE6_COMPLETE.md](PHASE6_COMPLETE.md) - Web dashboard & API
- [PHASE7_COMPLETE.md](PHASE7_COMPLETE.md) - Authentication & WebSocket

## 🗺️ Development Roadmap

- [x] **Phase 1: Infrastructure setup** ✅
  - Database schema (PostgreSQL + SQLAlchemy)
  - Configuration management (Pydantic)
  - Docker infrastructure
  - Repository pattern

- [x] **Phase 2: Reconnaissance pipeline** ✅
  - Subfinder integration (subdomain enumeration)
  - httpx integration (HTTP probing & metadata)
  - Naabu integration (port scanning)
  - DNS resolution (puredns/builtin)
  - Prefect workflows for orchestration
  - Diff engine (state comparison & change detection)

- [x] **Phase 3: Vulnerability scanning** ✅
  - Nuclei integration with smart targeting
  - Template management (5000+ templates)
  - Interactsh OOB detection
  - Severity-based filtering
  - Deduplication and reporting tracking

- [x] **Phase 4: Alerting system** ✅
  - Discord webhook integration
  - Slack webhook integration
  - Severity-based alert routing
  - Batch and individual alerts
  - Daily/weekly automated reports
  - Alert history and retry logic

- [x] **Phase 5: Scope monitoring** ✅
  - Multi-platform scope parsing (HackerOne, Bugcrowd)
  - API + web scraping dual fetch
  - Checksum-based change detection
  - Asset scope validation
  - Wildcard, CIDR, pattern matching
  - Scope change alerts
  - Historical scope tracking

- [x] **Phase 6: Web dashboard & API** ✅
  - FastAPI REST API with 20+ endpoints
  - Modern web dashboard with HTMX
  - Real-time vulnerability feed
  - Program management UI
  - Auto-generated API documentation

- [x] **Phase 7: Authentication & WebSocket** ✅
  - JWT-based authentication
  - User management system
  - Role-based access control
  - Real-time WebSocket updates
  - Export functionality (CSV/JSON)

- [ ] **Phase 8: Comprehensive Testing** 🚧 **IN PROGRESS - HELP NEEDED**
  - Unit tests for all modules
  - Integration tests for workflows
  - API endpoint testing
  - Database transaction tests
  - Scanner integration tests
  - Security and penetration testing
  - Performance and load testing
  - Documentation validation

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

**🚨 Testing Help Needed**: We're actively looking for contributors to help build comprehensive test suites. This is a great way to contribute!

- **Help with testing** - Write unit/integration tests (Priority!)
- Report bugs by opening an issue
- Suggest features via issues
- Submit PRs for bug fixes or features
- Improve documentation

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with amazing open-source tools from [ProjectDiscovery](https://github.com/projectdiscovery)
- Inspired by the bug bounty community
- Special thanks to all contributors

## ⚖️ Legal Disclaimer

This tool is provided for authorized security testing and bug bounty hunting only. Users are responsible for ensuring they have proper authorization before scanning any targets. The authors assume no liability for misuse or damage caused by this tool. Always comply with applicable laws and bug bounty program rules.

## 🔒 Security

Found a security vulnerability? Please review our [Security Policy](SECURITY.md) for responsible disclosure guidelines.

---

**Made with ❤️ for the bug bounty community**
