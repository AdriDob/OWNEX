"""Credentials Vault — Load API keys from ~/.config/ownex/opportunity.env"""

from __future__ import annotations

from datetime import UTC
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
    from datetime import datetime

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
