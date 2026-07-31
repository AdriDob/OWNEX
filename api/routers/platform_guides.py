"""Platform Guides API — Step-by-step assistance for account creation and work submission."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from core.opportunity.guides.platform_guides import (
    format_guide_for_user,
    get_platform_guide,
    list_all_platforms,
)

logger = logging.getLogger("ownex.api.platform_guides")

router = APIRouter(prefix="/api/platform-guides", tags=["platform-guides"])


@router.get("/")
def list_platforms():
    """List all platforms with available guides."""
    platforms = list_all_platforms()
    return {
        "success": True,
        "platforms": platforms,
        "total": len(platforms),
    }


@router.get("/{platform}")
def get_guide(platform: str, guide_type: str = "account"):
    """Get detailed guide for a platform (account creation or work submission)."""
    try:
        guide = get_platform_guide(platform)
        if not guide:
            raise HTTPException(status_code=404, detail=f"Platform '{platform}' not found")

        if guide_type not in ("account", "work"):
            raise HTTPException(status_code=400, detail="guide_type must be 'account' or 'work'")

        formatted = format_guide_for_user(guide, guide_type)
        return {
            "success": True,
            "platform": platform,
            "guide_type": guide_type,
            "guide": formatted,
            "url": guide.url,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get guide for {platform}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/{platform}/account")
def get_account_guide(platform: str):
    """Get account creation guide for a platform."""
    return get_guide(platform, "account")


@router.get("/{platform}/work")
def get_work_guide(platform: str):
    """Get work submission guide for a platform."""
    return get_guide(platform, "work")
