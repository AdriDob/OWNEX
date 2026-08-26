"""Premium Feature Gates — Ed25519 tier validation for OWNEX open-core.

Checks license tier before executing sponsor-only features.
Uses existing cores/license/validator.py infrastructure.

Tiers:
    free         → base features only
    supporter    → $15/mes — auto-submit, CoderAgent, income targets
    professional → $49/mes — Polymarket, job search, calibration
    enterprise   → $149/mes — multi-tenant, unlimited API
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable

logger = logging.getLogger("ownex.premium")

_TIER_ORDER = {"free": 0, "supporter": 1, "professional": 2, "enterprise": 3}


def _get_current_tier() -> str:
    """Read current tier from Ed25519 license or default to free."""
    try:
        from cores.license import validator as lv

        # Check for tier in license file or env
        import os
        tier_env = os.getenv("OWNEX_TIER", "").lower()
        if tier_env in _TIER_ORDER:
            return tier_env
        license_path = os.path.expanduser("~/.ownex/license.json")
        if os.path.exists(license_path):
            import json
            data = json.loads(open(license_path).read())
            if data.get("valid") and data.get("tier"):
                return data["tier"]
            if data.get("valid"):
                return "supporter"
    except Exception:
        pass
    return "free"


def requires_tier(minimum: str):
    """Decorator: gate a function behind a minimum tier.

    Usage:
        @requires_tier("professional")
        def run_polymarket_sweeper(...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current = _get_current_tier()
            required = _TIER_ORDER.get(minimum, 99)
            actual = _TIER_ORDER.get(current, 0)
            if actual >= required:
                return func(*args, **kwargs)
            raise PermissionError(
                f"'{func.__name__}' requires tier '{minimum}' or higher. "
                f"Current tier: '{current}'. "
                f"Become a sponsor at https://github.com/sponsors/AdriDob"
            )

        return wrapper

    return decorator


def get_tier() -> str:
    """Public helper: what tier is the current installation?"""
    return _get_current_tier()


def is_premium() -> bool:
    return _get_current_tier() != "free"


def tier_status() -> dict[str, Any]:
    """Status dict for frontend/API consumption."""
    tier = _get_current_tier()
    return {
        "tier": tier,
        "is_free": tier == "free",
        "is_premium": tier != "free",
        "available_features": [
            f
            for f, min_tier in {
                "discovery": "free",
                "scanner": "free",
                "workbank": "free",
                "daily_digest": "free",
                "profile_kit": "free",
                "auto_submit": "supporter",
                "coder_autopilot": "supporter",
                "income_targets": "supporter",
                "competition_intel": "supporter",
                "polymarket": "professional",
                "job_search": "professional",
                "calibration": "professional",
                "multi_tenant": "enterprise",
                "unlimited_api": "enterprise",
            }.items()
            if _TIER_ORDER.get(tier, 0) >= _TIER_ORDER.get(min_tier, 99)
        ],
        "locked_features": [
            f
            for f, min_tier in {
                "auto_submit": "supporter",
                "coder_autopilot": "supporter",
                "income_targets": "supporter",
                "polymarket": "professional",
                "job_search": "professional",
                "calibration": "professional",
                "multi_tenant": "enterprise",
                "unlimited_api": "enterprise",
            }.items()
            if _TIER_ORDER.get(tier, 0) < _TIER_ORDER.get(min_tier, 99)
        ],
        "sponsor_url": "https://github.com/sponsors/AdriDob",
        "open_collective_url": "https://opencollective.com/ownex",
        "polar_url": "https://polar.sh/adridob",
    }
