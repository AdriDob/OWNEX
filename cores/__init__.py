"""
Core modules for CATEYE.

Sub-packages:
  contracts/  — Canonical interfaces and base classes
  artifacts/  — Canonical artifact bundles (system-wide data objects)
  intelligence/ — Unification layer (dependency graph, events, cache, anti-drift)
  ... (existing engines remain unchanged)
"""

from __future__ import annotations

from pathlib import Path

# Public constants — consolidated from the former core/__init__.py during
# CORE-CORES consolidation (see .ai/DECISIONS.md). The legacy `core/` tree was
# removed; `cores/` is the single canonical tree: `from cores import OWNEX_DIR`.
__version__ = "7.1.0"

OWNEX_DIR = Path.home() / ".ownex"
