"""ORION Update Manager — version check, update manifest, download, rollback."""

from __future__ import annotations

from core.update.engine import UpdateManager, check_for_updates

__all__ = ["UpdateManager", "check_for_updates"]
