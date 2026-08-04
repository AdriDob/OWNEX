"""Credentials Rotation API — Auto-rotation and health monitoring for API keys."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from core.credentials.vault import (
    auto_rotate_all,
    check_rotation_needs,
    get_expiring_credentials,
    record_failed_auth,
    rotate_credential_with_backup,
    set_credential_expiration,
)

router = APIRouter(prefix="/api/credentials", tags=["credentials-rotation"])


@router.post("/rotate/{platform}")
async def rotate_platform_credential(
    platform: str,
    credential_id: str | None = Query(None, description="Optional specific credential ID"),
) -> dict[str, Any]:
    """Force rotation of a platform's credential.

    Creates a backup, attempts auto-refresh if supported, or generates manual alert.

    Args:
        platform: Platform name (e.g., "github", "hackerone")
        credential_id: Optional specific credential ID for platforms with multiple keys

    Returns:
        Rotation result with method used and backup path
    """
    result = await rotate_credential_with_backup(platform, credential_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/rotation-status")
async def get_rotation_status() -> dict[str, Any]:
    """Get rotation status for all configured platforms.

    Returns check results for each platform including:
    - needs_rotation: bool
    - reason: str (if rotation needed)
    - days_until_expiration: int | None
    - failed_auth_count: int
    - last_rotated: str | None
    """
    from core.credentials.vault import _AUTO_REFRESH_PLATFORMS, _MANUAL_ROTATION_PLATFORMS

    all_platforms = list(_AUTO_REFRESH_PLATFORMS | _MANUAL_ROTATION_PLATFORMS)
    status = {}

    for platform in all_platforms:
        status[platform] = check_rotation_needs(platform)

    return {
        "success": True,
        "total_platforms": len(all_platforms),
        "platforms": status,
    }


@router.post("/force-rotate-all")
async def force_rotate_all_credentials() -> dict[str, Any]:
    """Force rotation check for all credentials.

    Checks all platforms and rotates those that need it.
    Auto-refresh platforms will attempt automatic refresh.
    Manual platforms will generate alerts.

    Returns:
        Summary of rotation operations for all platforms
    """
    result = await auto_rotate_all()
    return result


@router.get("/expiring-soon")
async def get_expiring_soon(
    days_threshold: int = Query(7, ge=1, le=365, description="Days threshold for expiration warning"),
) -> dict[str, Any]:
    """Get credentials that will expire within the specified threshold.

    Args:
        days_threshold: Number of days to look ahead (default: 7)

    Returns:
        List of credentials expiring soon with days until expiration
    """
    result = get_expiring_credentials(days_threshold)
    return result


@router.post("/record-failed-auth/{platform}")
async def record_authentication_failure(platform: str) -> dict[str, Any]:
    """Record a failed authentication attempt for a platform.

    Increments the failed auth counter. If threshold is reached,
    rotation will be triggered automatically.

    Args:
        platform: Platform name

    Returns:
        Updated failed auth count and rotation status
    """
    result = record_failed_auth(platform)
    return result


@router.post("/set-expiration/{platform}")
async def set_credential_expiration_date(
    platform: str,
    expiration_date: str = Query(..., description="ISO format date (e.g., 2026-12-31T23:59:59Z)"),
) -> dict[str, Any]:
    """Set the expiration date for a platform's credential.

    Args:
        platform: Platform name
        expiration_date: ISO format date string

    Returns:
        Update result
    """
    result = set_credential_expiration(platform, expiration_date)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/check/{platform}")
async def check_platform_rotation_needs(platform: str) -> dict[str, Any]:
    """Check if a specific platform's credentials need rotation.

    Args:
        platform: Platform name

    Returns:
        Rotation check result for the platform
    """
    result = check_rotation_needs(platform)
    return result
