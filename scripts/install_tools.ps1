# Windows Quick Setup Script
# Run this as Administrator for best results

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "AutoBug Scanning Tools Installer" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Check if Go is installed
Write-Host "[1/5] Checking Go installation..." -ForegroundColor Yellow
try {
    $goVersion = go version
    Write-Host "✓ Go is installed: $goVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Go is not installed!" -ForegroundColor Red
    Write-Host "Please install Go first:" -ForegroundColor Yellow
    Write-Host "  winget install GoLang.Go" -ForegroundColor Yellow
    Write-Host "  OR download from: https://go.dev/dl/" -ForegroundColor Yellow
    exit 1
}

# Setup Go paths
Write-Host ""
Write-Host "[2/5] Setting up Go paths..." -ForegroundColor Yellow
$env:GOPATH = "$env:USERPROFILE\go"
New-Item -ItemType Directory -Force -Path "$env:GOPATH\bin" | Out-Null
$env:Path += ";$env:GOPATH\bin"
Write-Host "✓ Go paths configured" -ForegroundColor Green

# Install scanning tools
Write-Host ""
Write-Host "[3/5] Installing scanning tools..." -ForegroundColor Yellow

$tools = @(
    @{Name="Subfinder"; Package="github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"},
    @{Name="httpx"; Package="github.com/projectdiscovery/httpx/cmd/httpx@latest"},
    @{Name="Nuclei"; Package="github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"},
    @{Name="Naabu"; Package="github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"}
)

foreach ($tool in $tools) {
    Write-Host "  Installing $($tool.Name)..." -NoNewline
    try {
        go install -v $tool.Package 2>&1 | Out-Null
        Write-Host " ✓" -ForegroundColor Green
    } catch {
        Write-Host " ✗" -ForegroundColor Red
        Write-Host "    Error: $_" -ForegroundColor Red
    }
}

# Update templates
Write-Host ""
Write-Host "[4/5] Updating tool templates..." -ForegroundColor Yellow
try {
    Write-Host "  Updating Nuclei templates..." -NoNewline
    nuclei -update-templates -silent 2>&1 | Out-Null
    Write-Host " ✓" -ForegroundColor Green
    
    Write-Host "  Updating Subfinder providers..." -NoNewline
    subfinder -up 2>&1 | Out-Null
    Write-Host " ✓" -ForegroundColor Green
} catch {
    Write-Host " (skipped)" -ForegroundColor Yellow
}

# Verify installation
Write-Host ""
Write-Host "[5/5] Verifying installations..." -ForegroundColor Yellow

$verifyTools = @("subfinder", "httpx", "nuclei", "naabu")
$allInstalled = $true

foreach ($tool in $verifyTools) {
    Write-Host "  Checking $tool..." -NoNewline
    try {
        & $tool -version 2>&1 | Out-Null
        Write-Host " ✓" -ForegroundColor Green
    } catch {
        Write-Host " ✗" -ForegroundColor Red
        $allInstalled = $false
    }
}

Write-Host ""
Write-Host "===================================" -ForegroundColor Cyan
if ($allInstalled) {
    Write-Host "✓ All tools installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Restart your terminal" -ForegroundColor White
    Write-Host "  2. Run: python -m src.cli scan test-tools" -ForegroundColor White
    Write-Host "  3. Start scanning!" -ForegroundColor White
} else {
    Write-Host "⚠ Some tools failed to install" -ForegroundColor Yellow
    Write-Host "Please check the errors above and try manual installation" -ForegroundColor Yellow
}
Write-Host "===================================" -ForegroundColor Cyan
