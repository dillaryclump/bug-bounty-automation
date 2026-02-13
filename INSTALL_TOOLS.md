# Installation Guide - Scanning Tools

This guide walks you through installing the scanning tools required for AutoBug.

## Windows Installation

### Step 1: Install Go (Required for all scanners)

```powershell
# Download and install Go
winget install GoLang.Go

# Or download from: https://go.dev/dl/
# Restart your terminal after installation

# Verify installation
go version
```

### Step 2: Install Scanning Tools

```powershell
# Create Go bin directory if it doesn't exist
$env:GOPATH = "$env:USERPROFILE\go"
New-Item -ItemType Directory -Force -Path "$env:GOPATH\bin"

# Add Go bin to PATH (permanent)
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:GOPATH\bin",
    "User"
)

# Install Subfinder (subdomain enumeration)
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# Install httpx (HTTP probing)
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest

# Install Nuclei (vulnerability scanner)
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# Install Naabu (port scanner)
go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest

# Optional: Install puredns (fast DNS resolution)
go install github.com/d3mondev/puredns/v2@latest
```

### Step 3: Update Tool Templates

```powershell
# Update Nuclei templates (vulnerability scanning templates)
nuclei -update-templates

# Update Subfinder providers config
subfinder -up
```

### Step 4: Verify Installation

```powershell
# Test each tool
subfinder -version
httpx -version
nuclei -version
naabu -version

# Or use AutoBug's test command
python -m src.cli scan test-tools
```

## Linux/Ubuntu Installation

```bash
# Install Go
wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin' >> ~/.bashrc
source ~/.bashrc

# Install tools
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
go install github.com/d3mondev/puredns/v2@latest

# Update templates
nuclei -update-templates
subfinder -up
```

## macOS Installation

```bash
# Install Go via Homebrew
brew install go

# Install tools
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
go install github.com/d3mondev/puredns/v2@latest

# Update templates
nuclei -update-templates
subfinder -up
```

## Tool Configuration (Optional)

### Subfinder Configuration

Create `~/.config/subfinder/provider-config.yaml` for API keys:

```yaml
# Free API keys for better subdomain enumeration
virustotal:
  - YOUR_VT_API_KEY
censys:
  - YOUR_CENSYS_ID:YOUR_CENSYS_SECRET
shodan:
  - YOUR_SHODAN_API_KEY
```

### Nuclei Configuration

```powershell
# Set templates directory
$env:NUCLEI_TEMPLATES_PATH = "$env:USERPROFILE\nuclei-templates"

# Configure rate limiting (be respectful!)
$env:NUCLEI_RATE_LIMIT = 150
```

## Troubleshooting

### "Command not found" on Windows

```powershell
# Verify Go bin is in PATH
$env:Path -split ';' | Select-String 'go\\bin'

# If not found, add it:
$env:Path += ";$env:USERPROFILE\go\bin"

# Restart your terminal
```

### Permission Errors (Naabu on Windows)

Naabu requires admin privileges for raw socket access:

```powershell
# Run PowerShell as Administrator, or use:
naabu -p 80,443,8080 -host example.com  # Limited port scanning works without admin
```

### Tools Installing But Not Working

```powershell
# Clear Go cache and reinstall
go clean -cache
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
```

## Next Steps

After installing tools, test them:

```powershell
# Test with AutoBug
python -m src.cli scan test-tools

# Or test individually
subfinder -d example.com
httpx -u https://example.com
nuclei -u https://example.com -t cves/
```

## Performance Tuning

### For Fast Scans
```powershell
# httpx with high concurrency
httpx -l targets.txt -threads 100

# Subfinder with all sources
subfinder -d example.com -all -recursive
```

### For Quiet/Stealth Scans
```powershell
# httpx with delays
httpx -l targets.txt -rate-limit 10

# Nuclei with rate limiting
nuclei -l targets.txt -rate-limit 50
```

## Resource Requirements

- **Disk Space**: ~2 GB (mostly for Nuclei templates)
- **RAM**: 4 GB minimum, 8 GB recommended
- **Network**: High bandwidth for fast scanning
- **CPU**: Multi-core recommended for parallel scanning
