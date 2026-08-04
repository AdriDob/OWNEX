from __future__ import annotations

"""ORION Update Manager — version check, update manifest, download, rollback."""
# ruff: noqa: E402

from core.update.engine import UpdateManager, check_for_updates

__all__ = ["UpdateManager", "check_for_updates"]
