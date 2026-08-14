"""Knowledge Bridge — scheduled tasks.

Runs the daily vault sync: incremental index, health snapshot, embedding
backfill. Tolerant to any failure (never crashes the scheduler).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.knowledge.index import DATA_DIR, load_config

_HEALTH_LOG = Path(DATA_DIR) / "knowledge_health.jsonl"


def _append_snapshot(snapshot: dict[str, Any]) -> None:
    _HEALTH_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now(UTC).isoformat(), **snapshot}
    with _HEALTH_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def run_knowledge_sync() -> dict[str, Any]:
    """Daily vault sync job: incremental scan + health snapshot + embeddings."""
    cfg = load_config()
    vault = cfg.get("vault_path") or ""
    if not vault:
        return {"ok": False, "reason": "no_vault_connected", "snapshot": None}

    from cores.knowledge import vault_health
    from cores.knowledge.index import get_knowledge_index
    from cores.knowledge.search import KnowledgeSearcher

    vault_path = Path(vault).expanduser().resolve()
    index = get_knowledge_index()
    index.set_vault_root(vault_path)
    scan = index.scan_incremental()
    try:
        searcher = KnowledgeSearcher(index)
        emb = searcher.ensure_embeddings(limit=150)
    except Exception:
        emb = {"computed": 0, "skipped": "embedding failure"}
    health = vault_health()
    snapshot = {
        "ok": True,
        "scan": scan,
        "embeddings": emb,
        "health": health.get("health", {}),
        "index": health.get("index", {}),
        "git": health.get("git", {}).get("is_repo", False),
        "security_clean": health.get("security", {}).get("clean", None),
    }
    _append_snapshot(snapshot)
    return snapshot


def get_knowledge_snapshot_history(limit: int = 7) -> list[dict[str, Any]]:
    """Last N health snapshots (oldest first)."""
    if not _HEALTH_LOG.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in _HEALTH_LOG.read_text(encoding="utf-8").splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries[-limit:]
