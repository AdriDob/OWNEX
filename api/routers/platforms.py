"""Platforms API — aggregated status of all bug bounty platforms."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from cores.identity_vault import get_identity_vault

logger = logging.getLogger("ownex.platforms.api")

router = APIRouter(prefix="/api/platforms", tags=["platforms"])

PLATFORM_META = {
    "hackerone": {"name": "HackerOne", "color": "hackerone"},
    "bugcrowd": {"name": "Bugcrowd", "color": "bugcrowd"},
    "intigriti": {"name": "Intigriti", "color": "intigriti"},
    "synack": {"name": "Synack", "color": "synack"},
    "yeswehack": {"name": "YesWeHack", "color": "yeswehack"},
    "immunefi": {"name": "Immunefi", "color": "immunefi"},
    "code4rena": {"name": "Code4rena", "color": "code4rena"},
    "huntr": {"name": "Huntr", "color": "huntr"},
}

DEFAULT_PLATFORMS = ["hackerone", "bugcrowd", "intigriti", "synack", "yeswehack"]


@router.get("/status")
def platform_status():
    """Get connection status of all bug bounty platforms."""
    vault = get_identity_vault()
    accounts = vault.list_accounts()
    vault_map = {a["provider_name"].lower(): a for a in accounts}

    platforms = []
    for pid in DEFAULT_PLATFORMS:
        meta = PLATFORM_META.get(pid, {"name": pid.capitalize(), "color": "default"})
        v = vault_map.get(pid, {})
        platforms.append(
            {
                "name": meta["name"],
                "provider": pid,
                "connected": v.get("has_credentials", False),
                "username": v.get("email", "").split("@")[0] if v.get("email") else "",
                "email": v.get("email", ""),
                "earnings": 0,
                "pending": 0,
                "last_sync": v.get("last_checked", ""),
            }
        )

    return {"platforms": platforms}
