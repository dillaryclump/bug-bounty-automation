#!/bin/bash
# Linux/macOS Quick Setup Script

set -e

echo "==================================="
echo "AutoBug Scanning Tools Installer"
echo "==================================="
echo ""

# Check if Go is installed
echo "[1/5] Checking Go installation..."
if command -v go &> /dev/null; then
    echo "✓ Go is installed: $(go version)"
else
    echo "✗ Go is not installed!"
    echo "Please install Go first:"
    echo "  https://go.dev/dl/"
    exit 1
fi

# Setup Go paths
echo ""
echo "[2/5] Setting up Go paths..."
export GOPATH="$HOME/go"
export PATH="$PATH:$GOPATH/bin"
mkdir -p "$GOPATH/bin"
echo "✓ Go paths configured"

# Install scanning tools
echo ""
echo "[3/5] Installing scanning tools..."

install_tool() {
    echo "  Installing $1..."
    go install -v "$2" || echo "  ✗ Failed to install $1"
}

install_tool "Subfinder" "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
install_tool "httpx" "github.com/projectdiscovery/httpx/cmd/httpx@latest"
install_tool "Nuclei" "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
install_tool "Naabu" "github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"

# Update templates
echo ""
echo "[4/5] Updating tool templates..."
echo "  Updating Nuclei templates..."
nuclei -update-templates -silent || true
echo "  Updating Subfinder providers..."
subfinder -up || true

# Verify installation
echo ""
echo "[5/5] Verifying installations..."
all_installed=true

for tool in subfinder httpx nuclei naabu; do
    echo -n "  Checking $tool..."
    if command -v $tool &> /dev/null; then
        echo " ✓"
    else
        echo " ✗"
        all_installed=false
    fi
done

echo ""
echo "==================================="
if [ "$all_installed" = true ]; then
    echo "✓ All tools installed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Add to your shell RC file:"
    echo "     export PATH=\$PATH:\$HOME/go/bin"
    echo "  2. Restart your terminal"
    echo "  3. Run: python -m src.cli scan test-tools"
else
    echo "⚠ Some tools failed to install"
    echo "Please check the errors above"
fi
echo "==================================="
