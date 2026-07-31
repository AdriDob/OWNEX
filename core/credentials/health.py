"""Credentials health — check secrets status and availability."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from core.credentials.vault import get_credentials, validate_credentials

logger = logging.getLogger("ownex.credentials.health")

PLATFORMS = [
    "algora",
    "freelancer",
    "github",
    "issuehunt",
    "opire",
    "opencollective",
    "superteam",
    "outlier",
    "mindrift",
    "dataannotation",
    "remotasks",
    "freelancer_micro",
    "linkedin",
    "opyre_micro",
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
]


async def check_secrets_health() -> dict[str, Any]:
    """Check health of all credential secrets.

    Scheduler handler: ``core.credentials.health:check_secrets_health``
    """
    try:
        creds = get_credentials()
        total_fields = len(creds.model_fields)
        populated = sum(1 for f in creds.model_fields if getattr(creds, f))

        platform_health: dict[str, Any] = {}
        populated_platforms = 0
        for platform in PLATFORMS:
            valid, missing = validate_credentials(platform)
            platform_health[platform] = {
                "valid": valid,
                "missing": missing,
            }
            if valid:
                populated_platforms += 1

        return {
            "success": True,
            "total_fields": total_fields,
            "populated_fields": populated,
            "total_platforms": len(PLATFORMS),
            "populated_platforms": populated_platforms,
            "coverage_pct": round((populated_platforms / len(PLATFORMS)) * 100, 1) if PLATFORMS else 0,
            "platforms": platform_health,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error(f"Secret health check failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat(),
        }
