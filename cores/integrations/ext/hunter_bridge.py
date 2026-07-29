"""Hunter Bridge — bridges external open-source bug bounty toolkits into Rastro.

Integrates three high-value open-source projects built with Claude Code:

1. claude-bug-bounty (shuvonsec) — 20 vuln class autonomous hunting pipeline
2. web3-bug-bounty-hunting-ai-skills — 18 smart contract skills from 2,749 Immunefi reports
3. bounty-hunter-mcp (L-ubu) — MCP server with route extraction, SSRF callback, CVSS
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.core.integrations.ext.hunter_bridge")

# ── Detection paths ──────────────────────────────────────────────────

HUNTER_REPO_DIR = Path.home() / ".orion" / "tools" / "claude-bug-bounty"
WEB3_SKILLS_DIR = Path.home() / ".orion" / "tools" / "web3-bug-bounty-skills"
MCP_HUNTER_DIR = Path.home() / ".orion" / "tools" / "bounty-hunter-mcp"

HUNTER_GIT_URL = "https://github.com/shuvonsec/claude-bug-bounty.git"
WEB3_GIT_URL = "https://github.com/freloque/web3-bug-bounty-hunting-ai-skills.git"
MCP_HUNTER_GIT_URL = "https://github.com/L-ubu/bounty-hunter-mcp.git"

# ── Vuln class mapping: claude-bug-bounty → Rastro ──────────────────

HUNTER_TO_RASTRO_VULN = {
    "idor": "idor",
    "bola": "idor",
    "auth-bypass": "auth_bypass",
    "ssrf": "ssrf",
    "xss": "xss",
    "sqli": "sqli",
    "rce": "rce",
    "ssti": "ssti",
    "xxe": "xxe",
    "graphql": "graphql",
    "oauth": "oauth",
    "business-logic": "business_logic",
    "race-condition": "race_condition",
    "file-upload": "file_upload",
    "llm-injection": "llm_injection",
    "subdomain-takeover": "subdomain_takeover",
    "cache-poisoning": "cache_poisoning",
    "http-smuggling": "http_smuggling",
    "mfa-bypass": "mfa_bypass",
    "account-takeover": "account_takeover",
    "cloud-exposure": "cloud_exposure",
    "saml-attack": "saml_attack",
}

RASTRO_TO_HUNTER_VULN = {v: k for k, v in HUNTER_TO_RASTRO_VULN.items()}

# ── Web3 vuln classes ──────────────────────────────────────────────

WEB3_VULN_CLASSES = [
    "access-control",
    "reentrancy",
    "oracle-manipulation",
    "flash-loan",
    "integer-overflow",
    "front-running",
    "signature-replay",
    "permit2-abuse",
    "cross-chain-bridge",
    "governance-attack",
]


# ── Status checks ──────────────────────────────────────────────────


def _check_git_repo(path: Path, git_url: str) -> dict[str, Any]:
    """Check if a tool is installed (cloned and exists)."""
    if not path.exists():
        return {"installed": False, "path": str(path), "version": None}

    version = None
    if (path / ".git" / "HEAD").exists():
        try:
            result = subprocess.run(
                ["git", "-C", str(path), "log", "--oneline", "-1"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
        except Exception:
            pass

    return {"installed": True, "path": str(path), "version": version or "unknown"}


def check_hunter() -> dict[str, Any]:
    """Check if claude-bug-bounty is installed."""
    info = _check_git_repo(HUNTER_REPO_DIR, HUNTER_GIT_URL)
    if info["installed"]:
        has_engine = (HUNTER_REPO_DIR / "engine.py").exists()
        info["has_engine"] = has_engine
        info["vuln_classes"] = len(HUNTER_TO_RASTRO_VULN)
    return info


def check_web3_skills() -> dict[str, Any]:
    """Check if web3 bug bounty skills are installed."""
    info = _check_git_repo(WEB3_SKILLS_DIR, WEB3_GIT_URL)
    if info["installed"]:
        md_files = list(WEB3_SKILLS_DIR.glob("*.md"))
        info["skill_files"] = len(md_files)
        info["vuln_classes"] = len(WEB3_VULN_CLASSES)
    return info


def check_mcp_hunter() -> dict[str, Any]:
    """Check if bounty-hunter-mcp is installed."""
    info = _check_git_repo(MCP_HUNTER_DIR, MCP_HUNTER_GIT_URL)
    if info["installed"]:
        has_server = (MCP_HUNTER_DIR / "bounty_hunter" / "server.py").exists()
        info["has_server"] = has_server
    return info


# ── Install helpers ────────────────────────────────────────────────


def install_hunter() -> dict[str, Any]:
    """Clone and setup claude-bug-bounty."""
    try:
        HUNTER_REPO_DIR.parent.mkdir(parents=True, exist_ok=True)
        if HUNTER_REPO_DIR.exists():
            return {"status": "already_installed", "path": str(HUNTER_REPO_DIR)}
        subprocess.run(
            ["git", "clone", "--depth=1", HUNTER_GIT_URL, str(HUNTER_REPO_DIR)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {"status": "installed", "path": str(HUNTER_REPO_DIR)}
    except subprocess.CalledProcessError as exc:
        return {"status": "error", "error": exc.stderr}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def install_web3_skills() -> dict[str, Any]:
    """Clone web3 bug bounty skills."""
    try:
        WEB3_SKILLS_DIR.parent.mkdir(parents=True, exist_ok=True)
        if WEB3_SKILLS_DIR.exists():
            return {"status": "already_installed", "path": str(WEB3_SKILLS_DIR)}
        subprocess.run(
            ["git", "clone", "--depth=1", WEB3_GIT_URL, str(WEB3_SKILLS_DIR)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {"status": "installed", "path": str(WEB3_SKILLS_DIR)}
    except subprocess.CalledProcessError as exc:
        return {"status": "error", "error": exc.stderr}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ── Execution bridges ──────────────────────────────────────────────


def run_hunter_scan(domain: str, vuln_classes: list[str] | None = None) -> dict[str, Any]:
    """Run claude-bug-bounty scan on a target domain.

    Delegates to the standalone ``bughunter`` CLI if installed,
    otherwise returns instructions.
    """
    info = check_hunter()
    if not info["installed"]:
        return {"status": "not_installed", "hint": f"Run: git clone {HUNTER_GIT_URL} {HUNTER_REPO_DIR}"}

    # Check for standalone CLI
    bughunter = shutil.which("bughunter") or shutil.which("python3")
    if not bughunter:
        return {
            "status": "no_cli",
            "hint": "Install bughunter CLI: cd claude-bug-bounty && ./install.sh --agent standalone",
        }

    try:
        cmd = (
            [bughunter, "bughunter", domain]
            if "bughunter" in str(bughunter)
            else ["python3", str(HUNTER_REPO_DIR / "engine.py"), domain]
        )
        if vuln_classes:
            cmd.extend(["--vuln-types", ",".join(vuln_classes)])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-1000:],
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "domain": domain, "timeout_seconds": 600}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def get_web3_skill_path(vuln_class: str) -> str | None:
    """Get path to web3 skill file for a given vuln class."""
    info = check_web3_skills()
    if not info["installed"]:
        return None

    mapping = {
        "access-control": "02-bug-classes.md",
        "reentrancy": "02-bug-classes.md",
        "oracle-manipulation": "02-bug-classes.md",
        "flash-loan": "02-bug-classes.md",
        "integer-overflow": "02-bug-classes.md",
        "front-running": "02-bug-classes.md",
        "signature-replay": "02-bug-classes.md",
        "permit2-abuse": "02-bug-classes.md",
        "cross-chain-bridge": "02-bug-classes.md",
        "governance-attack": "02-bug-classes.md",
    }
    filename = mapping.get(vuln_class, "02-bug-classes.md")
    path = WEB3_SKILLS_DIR / filename
    return str(path) if path.exists() else None


def get_web3_poc_template(vuln_class: str) -> str | None:
    """Get Foundry PoC template for a web3 vuln class."""
    info = check_web3_skills()
    if not info["installed"]:
        return None

    path = WEB3_SKILLS_DIR / "04-poc-and-foundry.md"
    if not path.exists():
        return None
    return str(path)


# ── All-in-one status ──────────────────────────────────────────────


def status_summary() -> dict[str, Any]:
    """Return status of all hunter integrations."""
    return {
        "claude_bug_bounty": check_hunter(),
        "web3_bug_bounty_skills": check_web3_skills(),
        "bounty_hunter_mcp": check_mcp_hunter(),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
