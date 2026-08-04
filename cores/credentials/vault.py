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
    nvidia_api_key: str = Field(default="", alias="NVIDIA_API_KEY")
    nim_api_key: str = Field(default="", alias="NIM_API_KEY")
    omniroute_api_key: str = Field(default="", alias="OMNIROUTE_API_KEY")

    fcc_base_url: str = Field(default="http://localhost:8082", alias="FCC_BASE_URL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")


_credentials: OpportunityCredentials | None = None


def get_credentials(force_refresh: bool = False) -> OpportunityCredentials:
    """Get singleton credentials instance."""
    global _credentials
    if _credentials is None or force_refresh:
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


# ========== Credential Rotation System ==========

_ROTATION_CONFIG_PATH = Path("~/.config/ownex/credential_rotation.json").expanduser()
_DEFAULT_MAX_AGE_DAYS = 90
_DEFAULT_WARNING_DAYS = 7
_DEFAULT_FAILED_AUTH_THRESHOLD = 3

# Platforms with auto-refresh capability (tokens that can be refreshed programmatically)
_AUTO_REFRESH_PLATFORMS = {
    "github",  # GitHub tokens can be refreshed via API
}

# Platforms requiring manual rotation (user must update the key manually)
_MANUAL_ROTATION_PLATFORMS = {
    "hackerone",
    "bugcrowd",
    "intigriti",
    "synack",
    "yeswehack",
    "immunefi",
    "code4rena",
    "cantina",
    "sherlock",
    "codehawks",
    "algora",
    "freelancer",
    "issuehunt",
    "issuehand",
    "opire",
    "opencollective",
    "superteam",
    "outlier",
    "mindrift",
    "dataannotation",
    "remotasks",
}


def _load_rotation_config() -> dict[str, Any]:
    """Load rotation configuration from JSON file."""
    import json

    if not _ROTATION_CONFIG_PATH.exists():
        return {
            "max_age_days": _DEFAULT_MAX_AGE_DAYS,
            "warning_days": _DEFAULT_WARNING_DAYS,
            "failed_auth_threshold": _DEFAULT_FAILED_AUTH_THRESHOLD,
            "platforms": {},
        }

    try:
        return json.loads(_ROTATION_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "max_age_days": _DEFAULT_MAX_AGE_DAYS,
            "warning_days": _DEFAULT_WARNING_DAYS,
            "failed_auth_threshold": _DEFAULT_FAILED_AUTH_THRESHOLD,
            "platforms": {},
        }


def _save_rotation_config(config: dict[str, Any]) -> None:
    """Save rotation configuration to JSON file."""
    import json

    _ROTATION_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ROTATION_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _get_platform_rotation_state(platform: str) -> dict[str, Any]:
    """Get rotation state for a specific platform."""
    config = _load_rotation_config()
    return config.get("platforms", {}).get(
        platform,
        {
            "last_rotated": None,
            "failed_auth_count": 0,
            "expiration_date": None,
        },
    )


def _update_platform_rotation_state(platform: str, state: dict[str, Any]) -> None:
    """Update rotation state for a specific platform."""
    config = _load_rotation_config()
    if "platforms" not in config:
        config["platforms"] = {}
    config["platforms"][platform] = state
    _save_rotation_config(config)


def check_rotation_needs(platform: str) -> dict[str, Any]:
    """Check if a platform's credentials need rotation.

    Returns:
        dict with keys:
        - needs_rotation: bool
        - reason: str (if needs_rotation is True)
        - days_until_expiration: int | None
        - failed_auth_count: int
        - last_rotated: str | None
    """
    state = _get_platform_rotation_state(platform)
    config = _load_rotation_config()

    max_age_days = config.get("max_age_days", _DEFAULT_MAX_AGE_DAYS)
    warning_days = config.get("warning_days", _DEFAULT_WARNING_DAYS)
    failed_threshold = config.get("failed_auth_threshold", _DEFAULT_FAILED_AUTH_THRESHOLD)

    now = datetime.now(UTC)
    needs_rotation = False
    reason = ""
    days_until_expiration = None

    # Check failed auth count
    if state.get("failed_auth_count", 0) >= failed_threshold:
        needs_rotation = True
        reason = f"Failed auth count ({state['failed_auth_count']}) exceeds threshold ({failed_threshold})"

    # Check age
    if not needs_rotation and state.get("last_rotated"):
        last_rotated = datetime.fromisoformat(state["last_rotated"])
        age_days = (now - last_rotated).days
        if age_days >= max_age_days:
            needs_rotation = True
            reason = f"Credential age ({age_days} days) exceeds maximum ({max_age_days} days)"
        elif age_days >= (max_age_days - warning_days):
            days_until_expiration = max_age_days - age_days

    # Check explicit expiration date
    if not needs_rotation and state.get("expiration_date"):
        expiration = datetime.fromisoformat(state["expiration_date"])
        days_until = (expiration - now).days
        if days_until <= 0:
            needs_rotation = True
            reason = f"Credential expired on {state['expiration_date']}"
        elif days_until <= warning_days:
            days_until_expiration = days_until

    return {
        "needs_rotation": needs_rotation,
        "reason": reason if needs_rotation else None,
        "days_until_expiration": days_until_expiration,
        "failed_auth_count": state.get("failed_auth_count", 0),
        "last_rotated": state.get("last_rotated"),
        "expiration_date": state.get("expiration_date"),
    }


async def rotate_credential_with_backup(platform: str, credential_id: str | None = None) -> dict[str, Any]:
    """Rotate a credential with backup and event bus logging.

    Args:
        platform: Platform name (e.g., "github", "hackerone")
        credential_id: Optional specific credential ID (for platforms with multiple keys)

    Returns:
        dict with rotation result
    """
    # Create backup before rotation
    backup_result = await backup_vault()
    if not backup_result.get("success"):
        return {
            "success": False,
            "error": f"Backup failed: {backup_result.get('error')}",
        }

    # Determine if platform supports auto-refresh
    supports_auto_refresh = platform.lower() in _AUTO_REFRESH_PLATFORMS
    requires_manual = platform.lower() in _MANUAL_ROTATION_PLATFORMS

    if supports_auto_refresh:
        # For auto-refresh platforms, attempt automatic refresh
        try:
            refresh_result = await _auto_refresh_credential(platform, credential_id)
            if refresh_result.get("success"):
                # Update rotation state
                state = _get_platform_rotation_state(platform)
                state["last_rotated"] = datetime.now(UTC).isoformat()
                state["failed_auth_count"] = 0
                _update_platform_rotation_state(platform, state)

                # Publish to event bus
                _publish_rotation_event(platform, "auto_refreshed", credential_id)

                return {
                    "success": True,
                    "platform": platform,
                    "credential_id": credential_id,
                    "method": "auto_refresh",
                    "rotated_at": datetime.now(UTC).isoformat(),
                    "backup_path": backup_result.get("path"),
                }
            else:
                return {
                    "success": False,
                    "error": f"Auto-refresh failed: {refresh_result.get('error')}",
                    "platform": platform,
                    "requires_manual": True,
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Auto-refresh error: {str(e)}",
                "platform": platform,
                "requires_manual": True,
            }
    elif requires_manual:
        # For manual platforms, generate alert
        state = _get_platform_rotation_state(platform)
        state["last_rotated"] = datetime.now(UTC).isoformat()
        state["failed_auth_count"] = 0
        _update_platform_rotation_state(platform, state)

        # Publish alert event
        _publish_rotation_event(platform, "manual_rotation_required", credential_id)

        return {
            "success": True,
            "platform": platform,
            "credential_id": credential_id,
            "method": "manual_alert",
            "message": "Manual rotation required. Please update the credential in opportunity.env",
            "rotated_at": datetime.now(UTC).isoformat(),
            "backup_path": backup_result.get("path"),
        }
    else:
        return {
            "success": False,
            "error": f"Platform {platform} not configured for rotation",
        }


async def _auto_refresh_credential(platform: str, credential_id: str | None) -> dict[str, Any]:
    """Attempt to auto-refresh a credential for platforms that support it.

    This is a placeholder implementation. Actual refresh logic depends on the platform's API.
    """
    # GitHub-specific refresh logic (example)
    if platform.lower() == "github":
        # In a real implementation, this would call GitHub's API to refresh the token
        # For now, we simulate success
        return {
            "success": True,
            "message": "GitHub token auto-refreshed (simulated)",
        }

    return {
        "success": False,
        "error": f"Auto-refresh not implemented for platform {platform}",
    }


def _publish_rotation_event(platform: str, action: str, credential_id: str | None) -> None:
    """Publish a credential rotation event to the event bus."""
    try:
        from cores.events.event_bus import get_event_bus

        bus = get_event_bus()
        bus.publish(
            "credential:rotated",
            platform=platform,
            action=action,
            credential_id=credential_id,
            timestamp=datetime.now(UTC).isoformat(),
        )
    except Exception:
        # Event bus failure should not block rotation
        pass


async def auto_rotate_all() -> dict[str, Any]:
    """Check and rotate all credentials that need rotation.

    Returns:
        dict with rotation results for all platforms
    """
    results = {}
    all_platforms = list(_AUTO_REFRESH_PLATFORMS | _MANUAL_ROTATION_PLATFORMS)

    for platform in all_platforms:
        check = check_rotation_needs(platform)
        if check["needs_rotation"]:
            result = await rotate_credential_with_backup(platform)
            results[platform] = result
        else:
            results[platform] = {
                "success": True,
                "action": "skipped",
                "reason": "Rotation not needed",
                "check": check,
            }

    return {
        "success": True,
        "total_platforms": len(all_platforms),
        "rotated": sum(1 for r in results.values() if r.get("action") not in ["skipped"]),
        "results": results,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def record_failed_auth(platform: str) -> dict[str, Any]:
    """Record a failed authentication attempt for a platform.

    This increments the failed auth counter and triggers rotation if threshold is reached.
    """
    state = _get_platform_rotation_state(platform)
    state["failed_auth_count"] = state.get("failed_auth_count", 0) + 1
    _update_platform_rotation_state(platform, state)

    config = _load_rotation_config()
    threshold = config.get("failed_auth_threshold", _DEFAULT_FAILED_AUTH_THRESHOLD)

    result = {
        "success": True,
        "platform": platform,
        "failed_auth_count": state["failed_auth_count"],
        "threshold": threshold,
    }

    if state["failed_auth_count"] >= threshold:
        result["rotation_required"] = True
        result["message"] = f"Failed auth count ({state['failed_auth_count']}) reached threshold ({threshold})"

    return result


def set_credential_expiration(platform: str, expiration_date: str) -> dict[str, Any]:
    """Set the expiration date for a platform's credential.

    Args:
        platform: Platform name
        expiration_date: ISO format date string (e.g., "2026-12-31T23:59:59Z")

    Returns:
        dict with update result
    """
    try:
        # Validate date format
        datetime.fromisoformat(expiration_date)
    except ValueError:
        return {
            "success": False,
            "error": "Invalid expiration date format. Use ISO format (e.g., 2026-12-31T23:59:59Z)",
        }

    state = _get_platform_rotation_state(platform)
    state["expiration_date"] = expiration_date
    _update_platform_rotation_state(platform, state)

    return {
        "success": True,
        "platform": platform,
        "expiration_date": expiration_date,
    }


def get_expiring_credentials(days_threshold: int = 7) -> dict[str, Any]:
    """Get credentials that will expire within the specified threshold.

    Args:
        days_threshold: Number of days to look ahead (default: 7)

    Returns:
        dict with list of expiring credentials
    """
    expiring = []
    all_platforms = list(_AUTO_REFRESH_PLATFORMS | _MANUAL_ROTATION_PLATFORMS)

    for platform in all_platforms:
        check = check_rotation_needs(platform)
        if check["days_until_expiration"] is not None and check["days_until_expiration"] <= days_threshold:
            expiring.append(
                {
                    "platform": platform,
                    "days_until_expiration": check["days_until_expiration"],
                    "expiration_date": check.get("expiration_date"),
                    "last_rotated": check.get("last_rotated"),
                }
            )

    return {
        "success": True,
        "threshold_days": days_threshold,
        "expiring_count": len(expiring),
        "credentials": expiring,
        "timestamp": datetime.now(UTC).isoformat(),
    }
