"""Intelligence refresh tasks — scheduler entrypoints (sync, never raise).

Mirrors the ``cores.knowledge.tasks`` pattern: the scheduler resolves
``cores.intelligence.tasks:run_intelligence_refresh`` by dotted path and
calls it with no args. All failures degrade to a summary dict — a dead
feed must never break the scheduler loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.intelligence.tasks")


def _default_cache_dir() -> Path:
    """Data-dir aware default: frozen bundles honor OWNEX_DATA_DIR, dev keeps ./data."""
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[2] / "data"
    return root / "intelligence"


def run_intelligence_refresh() -> dict[str, Any]:
    """Fetch all registered feeds → cache with provenance. Returns a summary.

    Sync entrypoint for the scheduler (runs its own event loop in a worker
    thread, same as other sync handlers). Never raises.
    """
    started = datetime.now(UTC)
    try:
        from cores.intelligence import build_default_intelligence_registry
        from cores.intelligence.provenance import ContentHasher, ProvenanceRecord

        registry = build_default_intelligence_registry(_default_cache_dir())
        fetched = asyncio.run(registry.fetch_all())
        cached = 0
        for source, items in fetched.items():
            for item in items:
                try:
                    prov = ProvenanceRecord(
                        source=item.source.value,
                        item_external_id=item.external_id,
                        content_hash=item.content_hash,
                        raw_payload_hash=ContentHasher.hash_payload(item.raw_payload or {}),
                    )
                    if registry._cache.upsert(item, prov):
                        cached += 1
                except Exception as exc:
                    logger.debug("cache upsert skipped for %s: %s", source, exc)
        summary: dict[str, Any] = {
            "status": "ok",
            "feeds": len(fetched),
            "items_fetched": sum(len(v) for v in fetched.values()),
            "items_cached": cached,
            "per_feed": {k: len(v) for k, v in fetched.items()},
            "started_at": started.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
        }
        logger.info("[INTEL-REFRESH] %s feeds, %s items", summary["feeds"], summary["items_fetched"])
        return summary
    except Exception as exc:  # noqa: BLE001 — scheduler-safe
        logger.warning("intelligence refresh failed (non-fatal): %s", exc)
        return {"status": "error", "error": str(exc), "started_at": started.isoformat()}


def get_intelligence_snapshot_history(limit: int = 7) -> list[dict[str, Any]]:
    """Last N refresh summaries (best-effort, [] when unavailable)."""
    try:
        from cores.intelligence import get_intelligence_registry

        registry = get_intelligence_registry(_default_cache_dir())
        stats = registry.get_cache_stats()
        return [{"cached_items": stats.get("items", 0), "cache_dir": stats.get("cache_dir")}][:limit]
    except Exception:
        return []
