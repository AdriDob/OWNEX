"""Credentials Vault — Load API keys from ~/.config/ownex/opportunity.env"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpportunityCredentials(BaseSettings):
    """Credentials for all opportunity platforms, loaded from ~/.config/ownex/opportunity.env"""

    model_config = SettingsConfigDict(
        env_file=Path("~/.config/ownex/opportunity.env").expanduser(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ========== FORGE — Open Source Funding ==========
    algora_api_key: str = Field(default="", alias="ALGORA_API_KEY")
    algora_api_url: str = Field(default="https://api.algora.io", alias="ALGORA_API_URL")

    freelancer_api_key: str = Field(default="", alias="FREELANCER_API_KEY")
    freelancer_api_url: str = Field(default="https://www.freelancer.com/api", alias="FREELANCER_API_URL")

    github_token: str = Field(default="", alias="GITHUB_TOKEN")
    github_api_url: str = Field(default="https://api.github.com", alias="GITHUB_API_URL")

    issuehunt_api_key: str = Field(default="", alias="ISSUEHUNT_API_KEY")
    issuehunt_api_url: str = Field(default="https://issuehunt.io/api", alias="ISSUEHUNT_API_URL")

    issuehand_api_key: str = Field(default="", alias="ISSUEHAND_API_KEY")
    issuehand_api_url: str = Field(default="https://issuehunt.io/api", alias="ISSUEHAND_API_URL")

    opire_api_key: str = Field(default="", alias="OPIRE_API_KEY")
    opire_api_url: str = Field(default="https://opire.com/api", alias="OPIRE_API_URL")

    opencollective_api_key: str = Field(default="", alias="OPENCOLLECTIVE_API_KEY")
    opencollective_api_url: str = Field(default="https://opencollective.com/api", alias="OPENCOLLECTIVE_API_URL")

    superteam_api_key: str = Field(default="", alias="SUPERTEAM_API_KEY")
    superteam_api_url: str = Field(default="https://earn.superteam.fun/api", alias="SUPERTEAM_API_URL")

    # ========== PULSE — AI Work / Microtasks ==========
    outlier_api_key: str = Field(default="", alias="OUTLIER_API_KEY")
    outlier_api_url: str = Field(default="https://platform.outlier.ai/api", alias="OUTLIER_API_URL")

    mindrift_api_key: str = Field(default="", alias="MINDRIFT_API_KEY")
    mindrift_api_url: str = Field(default="https://mindrift.com/api", alias="MINDRIFT_API_URL")

    dataannotation_api_key: str = Field(default="", alias="DATAANNOTATION_API_KEY")
    dataannotation_api_url: str = Field(default="https://dataannotation.tech/api", alias="DATAANNOTATION_API_URL")

    remotasks_api_key: str = Field(default="", alias="REMOTASKS_API_KEY")
    remotasks_api_url: str = Field(default="https://remotasks.com/api", alias="REMOTASKS_API_URL")

    freelancer_micro_api_key: str = Field(default="", alias="FREELANCER_MICRO_API_KEY")
    freelancer_micro_api_url: str = Field(default="https://www.freelancer.com/api", alias="FREELANCER_MICRO_API_URL")

    linkedin_client_id: str = Field(default="", alias="LINKEDIN_CLIENT_ID")
    linkedin_client_secret: str = Field(default="", alias="LINKEDIN_CLIENT_SECRET")
    linkedin_redirect_uri: str = Field(
        default="http://localhost:8000/auth/linkedin/callback", alias="LINKEDIN_REDIRECT_URI"
    )

    opyre_micro_api_key: str = Field(default="", alias="OPYRE_MICRO_API_KEY")
    opyre_micro_api_url: str = Field(default="https://opyre.com/api", alias="OPYRE_MICRO_API_URL")

    # ========== VAULT — Bug Bounty Platforms ==========
    hackerone_api_key: str = Field(default="", alias="HACKERONE_API_KEY")
    hackerone_api_url: str = Field(default="https://api.hackerone.com", alias="HACKERONE_API_URL")

    bugcrowd_api_key: str = Field(default="", alias="BUGCROWD_API_KEY")
    bugcrowd_api_url: str = Field(default="https://api.bugcrowd.com", alias="BUGCROWD_API_URL")

    intigriti_api_key: str = Field(default="", alias="INTIGRITI_API_KEY")
    intigriti_api_url: str = Field(default="https://api.intigriti.com", alias="INTIGRITI_API_URL")

    synack_api_key: str = Field(default="", alias="SYNACK_API_KEY")
    synack_api_url: str = Field(default="https://platform.synack.com/api", alias="SYNACK_API_URL")

    yeswehack_api_key: str = Field(default="", alias="YESWEHACK_API_KEY")
    yeswehack_api_url: str = Field(default="https://api.yeswehack.com", alias="YESWEHACK_API_URL")

    immunefi_api_key: str = Field(default="", alias="IMMUNEFI_API_KEY")
    immunefi_api_url: str = Field(default="https://immunefi.com/api", alias="IMMUNEFI_API_URL")

    # ========== ATLAS — Audit Competitions ==========
    code4rena_api_key: str = Field(default="", alias="CODE4RENA_API_KEY")
    code4rena_api_url: str = Field(default="https://code4rena.com/api", alias="CODE4RENA_API_URL")

    cantina_api_key: str = Field(default="", alias="CANTINA_API_KEY")
    cantina_api_url: str = Field(default="https://cantina.xyz/api", alias="CANTINA_API_URL")

    sherlock_api_key: str = Field(default="", alias="SHERLOCK_API_KEY")
    sherlock_api_url: str = Field(default="https://audits.sherlock.xyz/api", alias="SHERLOCK_API_URL")

    codehawks_api_key: str = Field(default="", alias="CODEHAWKS_API_KEY")
    codehawks_api_url: str = Field(default="https://codehawks.cyfrin.io/api", alias="CODEHAWKS_API_URL")

    # ========== GENERAL / AI ==========
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    omniroute_api_key: str = Field(default="", alias="OMNIROUTE_API_KEY")

    fcc_base_url: str = Field(default="http://localhost:8082", alias="FCC_BASE_URL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")


_credentials: OpportunityCredentials | None = None


def get_credentials() -> OpportunityCredentials:
    """Get singleton credentials instance."""
    global _credentials
    if _credentials is None:
        _credentials = OpportunityCredentials()
    return _credentials


def get_platform_credentials(platform: str) -> dict[str, str]:
    """Get credentials dict for a specific platform."""
    creds = get_credentials()

    # Map platform names to credential prefixes
    platform_map = {
        "algora": "algora",
        "freelancer": "freelancer",
        "github": "github",
        "issuehunt": "issuehunt",
        "issuehand": "issuehand",
        "opire": "opire",
        "opencollective": "opencollective",
        "superteam": "superteam",
        "outlier": "outlier",
        "mindrift": "mindrift",
        "dataannotation": "dataannotation",
        "remotasks": "remotasks",
        "freelancer_micro": "freelancer_micro",
        "linkedin": "linkedin",
        "opyre_micro": "opyre_micro",
        "hackerone": "hackerone",
        "bugcrowd": "bugcrowd",
        "intigriti": "intigriti",
        "synack": "synack",
        "yeswehack": "yeswehack",
        "immunefi": "immunefi",
        "code4rena": "code4rena",
        "cantina": "cantina",
        "sherlock": "sherlock",
        "codehawks": "codehawks",
    }

    cred_prefix = platform_map.get(platform.lower(), platform.lower())
    result = {}

    for field_name, _ in creds.model_fields.items():
        if field_name.startswith(cred_prefix + "_"):
            key = field_name[len(cred_prefix) + 1 :]  # Remove prefix + underscore
            value = getattr(creds, field_name)
            if value:
                result[key] = value

    return result


def validate_credentials(platform: str) -> tuple[bool, list[str]]:
    """Check if required credentials exist for a platform. Returns (valid, missing_fields)."""
    creds = get_platform_credentials(platform)

    required = {
        "algora": ["api_key"],
        "freelancer": ["api_key"],
        "github": ["token"],
        "issuehunt": ["api_key"],
        "issuehand": ["api_key"],
        "opire": ["api_key"],
        "opencollective": ["api_key"],
        "superteam": ["api_key"],
        "outlier": ["api_key"],
        "mindrift": ["api_key"],
        "dataannotation": ["api_key"],
        "remotasks": ["api_key"],
        "freelancer_micro": ["api_key"],
        "linkedin": ["client_id", "client_secret"],
        "opyre_micro": ["api_key"],
        "hackerone": ["api_key"],
        "bugcrowd": ["api_key"],
        "intigriti": ["api_key"],
        "synack": ["api_key"],
        "yeswehack": ["api_key"],
        "immunefi": ["api_key"],
        "code4rena": ["api_key"],
        "cantina": ["api_key"],
        "sherlock": ["api_key"],
        "codehawks": ["api_key"],
    }

    missing = []
    for field in required.get(platform.lower(), []):
        if field not in creds or not creds[field]:
            missing.append(field)

    return len(missing) == 0, missing


async def backup_vault() -> dict[str, Any]:
    """Backup the credentials vault to a JSON snapshot.

    Scheduler handler: ``core.credentials.vault.backup_vault``
    """
    import json

    vault_dir = Path("~/.config/ownex").expanduser()
    backup_dir = vault_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    creds = get_credentials()
    snapshot = {}
    for field_name in creds.model_fields:
        value = getattr(creds, field_name)
        if value:
            # Mask sensitive values (show first 4 chars + ..redacted..)
            val_str = str(value)
            if len(val_str) > 8:
                snapshot[field_name] = val_str[:4] + "..redacted.."
            elif val_str:
                snapshot[field_name] = "..redacted.."

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"credentials_{timestamp}.json"
    backup_path.write_text(json.dumps(snapshot, indent=2))

    return {
        "success": True,
        "path": str(backup_path),
        "fields": len(snapshot),
        "timestamp": datetime.now(UTC).isoformat(),
    }


_AUDIT_LOG_PATH = Path("~/.config/ownex/credential_audit.jsonl").expanduser()


def _log_credential_access(action: str, platform: str, field: str = "") -> None:
    """Append an audit entry for a credential operation."""
    import json

    _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "platform": platform,
        "field": field,
    }
    with open(_AUDIT_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_audit_log(limit: int = 100) -> list[dict[str, Any]]:
    """Get recent audit log entries for credential access."""
    import json

    if not _AUDIT_LOG_PATH.exists():
        return []

    entries: list[dict[str, Any]] = []
    try:
        with open(_AUDIT_LOG_PATH) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except OSError:
        return []

    entries.reverse()
    return entries[:limit]


def get_secret_scan_results() -> dict[str, Any]:
    """Scan the codebase for leaked secrets.

    Checks common file types for patterns resembling API keys, tokens,
    and passwords that should not be in version control.
    """
    import re

    secret_patterns: list[tuple[str, str]] = [
        ("GitHub Token", r"ghp_[A-Za-z0-9]{36}"),
        ("GitHub PAT", r"gh[A-Z][A-Za-z0-9]{36}"),
        ("GitLab Token", r"glpat-[A-Za-z0-9\-]{20}"),
        ("Slack Token", r"xox[baprs]-[A-Za-z0-9-]+"),
        ("AWS Access Key", r"AKIA[A-Z0-9]{16}"),
        ("AWS Secret", r"(?i)aws_secret_access_key\s*=.*[A-Za-z0-9/+=]{40}"),
        ("Google API Key", r"AIza[A-Za-z0-9\-_]{35}"),
        ("Generic API Key", r"(?i)api[_-]?key\s*=\s*['\"][A-Za-z0-9]{32,}['\"]"),
        ("Generic Secret", r"(?i)secret\s*=\s*['\"][A-Za-z0-9]{16,}['\"]"),
        ("Private Key", r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
        ("Bearer Token", r"(?i)bearer\s+[A-Za-z0-9\-\._~+\/=]{20,}"),
    ]

    compiled = [(name, re.compile(pattern)) for name, pattern in secret_patterns]
    results: list[dict[str, Any]] = []
    project_root = Path(__file__).resolve().parents[2]

    skip_dirs = {".git", ".venv", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache"}
    skip_exts = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".db", ".sqlite", ".log"}

    for file_path in project_root.rglob("*"):
        if not file_path.is_file():
            continue
        if any(part in skip_dirs for part in file_path.parts):
            continue
        if file_path.suffix.lower() in skip_exts:
            continue
        if file_path.stat().st_size > 1_000_000:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        for name, pattern in compiled:
            for match in pattern.finditer(content):
                rel_path = str(file_path.relative_to(project_root))
                results.append(
                    {
                        "type": name,
                        "file": rel_path,
                        "line": content[: match.start()].count("\n") + 1,
                        "match_preview": match.group()[:20] + "...",
                    }
                )

    return {
        "success": True,
        "total_issues": len(results),
        "issues": results,
        "scanned_at": datetime.now(UTC).isoformat(),
    }


def rotate_credential(platform: str, field: str, new_value: str) -> dict[str, Any]:
    """Rotate a credential (update value and log to audit trail).

    Updates the value in the opportunity.env file and records the action.
    """
    env_path = Path("~/.config/ownex/opportunity.env").expanduser()
    if not env_path.exists():
        return {"success": False, "error": "Credentials file not found"}

    env_content = env_path.read_text(encoding="utf-8")
    env_lines = env_content.splitlines()
    var_name = f"{platform.upper()}_{field.upper()}"
    found = False

    new_lines: list[str] = []
    for line in env_lines:
        stripped = line.strip()
        if stripped.startswith(f"{var_name}="):
            new_lines.append(f"{var_name}={new_value}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        return {"success": False, "error": f"Variable {var_name} not found in credentials file"}

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    _log_credential_access("rotate", platform, field)

    global _credentials
    _credentials = None

    return {
        "success": True,
        "platform": platform,
        "field": field,
        "rotated_at": datetime.now(UTC).isoformat(),
    }
