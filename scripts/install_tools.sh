#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# ORION Tool Installer — single command to install every tool in the stack.
# Detects OS, installs missing tools, updates existing ones, validates PATH.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0
INSTALLED=()
MISSING=()
UPDATED=()

log_ok()  { echo -e "  ${GREEN}✓${NC} $1"; ((PASS++)); }
log_fail(){ echo -e "  ${RED}✗${NC} $1"; ((FAIL++)); }
log_warn(){ echo -e "  ${YELLOW}⚠${NC} $1"; ((WARN++)); }
log_info(){ echo -e "  ${CYAN}→${NC} $1"; }

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║        ORION — Tool Installation Script          ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── OS Detection ──────────────────────────────────────────────────────────
OS="linux"
case "$(uname -s)" in
    Linux) OS="linux" ;;
    Darwin) OS="macos" ;;
    *) log_warn "Unknown OS, assuming Linux-like" ;;
esac
log_info "Detected OS: $OS"

# ── Go installer —────────────────────────────────────────────────────────
ensure_go() {
    if command -v go &>/dev/null; then
        log_ok "Go $(go version | grep -oP 'go\d+\.\d+' || echo 'found')"
        return 0
    fi
    log_info "Installing Go..."
    local VER="1.22.5"
    local TAR="go${VER}.linux-amd64.tar.gz"
    if [ "$OS" = "macos" ]; then
        TAR="go${VER}.darwin-amd64.tar.gz"
        [ "$(uname -m)" = "arm64" ] && TAR="go${VER}.darwin-arm64.tar.gz"
    fi
    wget -q "https://go.dev/dl/${TAR}" -O "/tmp/${TAR}"
    sudo tar -C /usr/local -xzf "/tmp/${TAR}"
    export PATH=$PATH:/usr/local/go/bin
    if command -v go &>/dev/null; then
        log_ok "Go installed"
    else
        log_fail "Go installation failed"
    fi
}

# ── Tool installer —───────────────────────────────────────────────────────
install_go_tool() {
    local name=$1
    local pkg=$2
    if command -v "$name" &>/dev/null; then
        local old_ver
        old_ver=$("$name" -version 2>/dev/null | head -1 || "$name" --version 2>/dev/null | head -1 || echo "installed")
        log_ok "$name ($old_ver)"
        # Update
        log_info "Updating $name..."
        go install -v "${pkg}@latest" 2>/dev/null && UPDATED+=("$name") || log_warn "$name update skipped"
        return 0
    fi
    log_info "Installing $name from $pkg..."
    go install -v "${pkg}@latest" 2>/dev/null
    if command -v "$name" &>/dev/null; then
        log_ok "$name installed"
        INSTALLED+=("$name")
    else
        log_fail "$name not found in PATH after install"
        MISSING+=("$name")
    fi
}

# ── Tools ──────────────────────────────────────────────────────────────────
TOOLS_GO=(
    "subfinder:github.com/projectdiscovery/subfinder/v2/cmd/subfinder"
    "httpx:github.com/projectdiscovery/httpx/cmd/httpx"
    "nuclei:github.com/projectdiscovery/nuclei/v3/cmd/nuclei"
    "katana:github.com/projectdiscovery/katana/cmd/katana"
    "ffuf:github.com/ffuf/ffuf/v2"
    "gau:github.com/lc/gau/v2/cmd/gau"
    "waybackurls:github.com/tomnomnom/waybackurls"
    "hakrawler:github.com/hakluke/hakrawler"
    "naabu:github.com/projectdiscovery/naabu/v2/cmd/naabu"
    "dnsx:github.com/projectdiscovery/dnsx/cmd/dnsx"
    "uncover:github.com/projectdiscovery/uncover/cmd/uncover"
    "subzy:github.com/PentestPad/subzy"
    "dalfox:github.com/hahwul/dalfox/v2"
    "kxss:github.com/tomnomnom/hacks/kxss"
    "gf:github.com/tomnomnom/gf"
    "uro:github.com/s0md3v/uro"
    "trufflehog:github.com/trufflesecurity/trufflehog/v3"
    "interactsh:github.com/projectdiscovery/interactsh/cmd/interactsh-client"
)

ensure_go
go_version=$(go version | grep -oP 'go\d+\.\d+' || echo "go?")
echo -e "\n  Go $go_version | Installing ${#TOOLS_GO[@]} tools...\n"

for entry in "${TOOLS_GO[@]}"; do
    name="${entry%%:*}"
    pkg="${entry#*:}"
    install_go_tool "$name" "$pkg"
done

# ── Non-Go tools ──────────────────────────────────────────────────────────
if command -v apt-get &>/dev/null; then
    log_info "Installing system packages (wpscan, cmseek)..."
    sudo apt-get install -y -qq ruby-rubygems 2>/dev/null || true
    sudo gem install wpscan 2>/dev/null && log_ok "wpscan installed" || log_warn "wpscan install failed"
    pip3 install cmseek 2>/dev/null && log_ok "cmseek installed" || log_warn "cmseek install failed"
    pip3 install git-dumper 2>/dev/null && log_ok "git-dumper installed" || log_warn "git-dumper install failed"
fi

# ── Nuclei templates ──────────────────────────────────────────────────────
if command -v nuclei &>/dev/null; then
    log_info "Updating nuclei templates..."
    nuclei -update-templates 2>/dev/null && log_ok "Nuclei templates updated" || log_warn "Template update failed"
fi

# ── PATH check ────────────────────────────────────────────────────────────
GOBIN="$(go env GOPATH 2>/dev/null)/bin"
if [ -d "$GOBIN" ]; then
    case ":$PATH:" in
        *":$GOBIN:"*) ;;
        *) log_warn "$GOBIN not in PATH. Add: export PATH=\$PATH:$GOBIN" ;;
    esac
fi

# ── Report ────────────────────────────────────────────────────────────────
echo -e "\n${CYAN}  ╔══════════════════════════════════════════════════╗"
echo "  ║              INSTALLATION REPORT                ║"
echo "  ╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Passed:  $PASS"
echo "  Failed:  $FAIL"
echo "  Warnings: $WARN"
echo ""
echo "  Newly installed: ${INSTALLED[*]:-none}"
echo "  Updated:         ${UPDATED[*]:-none}"
echo "  Missing:         ${MISSING[*]:-none}"
echo ""

# ── Verification table ────────────────────────────────────────────────────
echo -e "  ${CYAN}Tool              Status         Version${NC}"
echo "  ──────────────────────────────────────────"
for t in subfinder httpx nuclei katana ffuf gau naabu dnsx uncover dalfox trufflehog; do
    if command -v "$t" &>/dev/null; then
        ver=$("$t" -version 2>/dev/null | head -1 || "$t" --version 2>/dev/null | head -1 || echo "installed")
        printf "  %-16s ${GREEN}%-14s${NC} %s\n" "$t" "✓ available" "${ver:0:40}"
    else
        printf "  %-16s ${RED}%-14s${NC} %s\n" "$t" "✗ missing" ""
    fi
done

echo ""
if [ "$FAIL" -eq 0 ] && [ "$WARN" -lt 3 ]; then
    echo -e "  ${GREEN}ORION tool stack ready.${NC}"
elif [ "$FAIL" -gt 0 ]; then
    echo -e "  ${YELLOW}Some tools failed. Manual install may be needed.${NC}"
fi
echo ""
