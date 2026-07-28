"""OWNEX Version API — /api/version endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from core.system.version_engine import VersionEngine

router = APIRouter(prefix="/api/version", tags=["version"])
ve = VersionEngine()


@router.get("")
async def get_version() -> dict:
    """Return the current platform version and sync status."""
    info = ve.info()
    info["in_sync"] = info["pyproject"] == info["version"] and info["frontend"] == info["version"]
    return info
