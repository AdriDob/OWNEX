"""API Router — OWNEX Knowledge Bridge (Obsidian vault).

Exposes the knowledge layer: vault connection, index health, hybrid search,
AI context, vault actions (git/snapshots/security) and scheduled sync.
Every mutation requires explicit authorization.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from cores.knowledge import (
    VaultManager,
    ensure_initialized,
    load_config,
    vault_health,
)
from cores.knowledge.gitops import GitOps, SecretScanner, SnapshotManager
from cores.knowledge.index import get_knowledge_index
from cores.knowledge.search import KnowledgeSearcher
from cores.knowledge.tasks import get_knowledge_snapshot_history

logger = logging.getLogger("api.knowledge_bridge")

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _require_index() -> Any:
    cfg = load_config()
    vault = cfg.get("vault_path") or ""
    if not vault:
        raise HTTPException(status_code=409, detail="No vault connected")
    index = get_knowledge_index()
    index.set_vault_root(Path(vault).expanduser().resolve())
    return index


def _require_vault() -> Path:
    """Return the connected vault root or raise 409."""
    cfg = load_config()
    vault = cfg.get("vault_path") or ""
    if not vault:
        raise HTTPException(status_code=409, detail="No vault connected")
    path = Path(vault).expanduser().resolve()
    get_knowledge_index().set_vault_root(path)
    return path


@router.get("/")
async def knowledge_status() -> dict[str, Any]:
    """Vault connection status + config (vault path, provider, last scan)."""
    cfg = load_config()
    manager = VaultManager(cfg)
    info = manager.verify()
    return {
        "connected": info.connected,
        "vault_path": info.vault_path,
        "status": info.status,
        "provider": cfg.get("embedding_provider", "local"),
        "last_scan": None if not info.connected else get_knowledge_index().stats()["last_scan"],
    }


@router.post("/connect")
async def knowledge_connect(path: str) -> dict[str, Any]:
    """Connect to an Obsidian vault (local path)."""
    manager = VaultManager(load_config())
    info = manager.set_vault(path)
    if not info.connected:
        raise HTTPException(status_code=400, detail=info.reason)
    index = get_knowledge_index()
    index.set_vault_root(Path(info.vault_path).expanduser().resolve())
    scan = index.scan_incremental()
    return {"connected": True, "vault": info.vault_path, "status": info.status, "scan": scan}


@router.post("/disconnect")
async def knowledge_disconnect() -> dict[str, Any]:
    """Disconnect the vault (index data is preserved)."""
    manager = VaultManager(load_config())
    info = manager.clear_vault()
    return {"connected": False, "vault": info.vault_path}


@router.post("/scan")
async def knowledge_scan(full: bool = False) -> dict[str, Any]:
    """Incremental (default) or full re-index of the vault."""
    index = _require_index()
    result = index.full_reindex() if full else index.scan_incremental()
    return {"ok": True, "full": full, **result, "stats": index.stats()}


@router.post("/initialize")
async def knowledge_initialize() -> dict[str, Any]:
    """Idempotent init: verify vault, scan, seed embeddings."""
    return ensure_initialized()


@router.get("/search")
async def knowledge_search(q: str, limit: int = 10) -> dict[str, Any]:
    """Hybrid search: FTS5 + tags + links + semantic (local embeddings)."""
    index = _require_index()
    searcher = KnowledgeSearcher(index)
    results = searcher.search(q, limit=limit)
    return {
        "query": q,
        "results": [r.to_dict() for r in results],
        "provider": "hybrid",
    }


@router.get("/note")
async def knowledge_note(path: str) -> dict[str, Any]:
    """Get a note by vault-relative path."""
    index = _require_index()
    note = index.note(path)
    if not note:
        raise HTTPException(status_code=404, detail=f"Note not found: {path}")
    return note


@router.get("/context")
async def knowledge_context(q: str, max_notes: int = 5) -> dict[str, Any]:
    """AI-ready context for a query: top notes, backlinks, related notes."""
    index = _require_index()
    searcher = KnowledgeSearcher(index)
    return searcher.build_context(q, max_notes=max_notes)


@router.get("/health")
async def knowledge_health() -> dict[str, Any]:
    """Consolidated knowledge dashboard (vault + index + git + backups + security)."""
    return vault_health()


@router.get("/history")
async def knowledge_history(limit: int = 7) -> dict[str, Any]:
    """Last health snapshots recorded by the daily sync job."""
    return {"snapshots": get_knowledge_snapshot_history(limit=limit)}


@router.post("/sync")
async def knowledge_sync() -> dict[str, Any]:
    """Run the daily sync (scan + embeddings + snapshot) on demand."""
    from cores.knowledge.tasks import run_knowledge_sync

    return run_knowledge_sync()


@router.get("/git/status")
async def git_status() -> dict[str, Any]:
    """Git state of the vault (repo?, branch, dirty files, last commit)."""
    vault = _require_vault()
    git = GitOps(vault)
    return git.status()


@router.post("/git/commit")
async def git_commit(message: str, authorized: bool = False) -> dict[str, Any]:
    """Commit vault changes. Requires explicit authorization."""
    vault = _require_vault()
    git = GitOps(vault)
    if not authorized:
        pending = git.diff()
        raise HTTPException(status_code=403, detail={"authorization_required": True, "pending": pending})
    result = git.commit(message)
    return result.to_dict()


@router.get("/security/scan")
async def security_scan() -> dict[str, Any]:
    """Scan the vault for leaked secrets (API keys, credentials)."""
    vault = _require_vault()
    return SecretScanner(vault).scan().to_dict()


@router.get("/snapshots")
async def snapshots_list() -> dict[str, Any]:
    """List local vault backups (rotated, keep 10)."""
    vault = _require_vault()
    return {"snapshots": SnapshotManager(vault).list()}


@router.post("/snapshots")
async def snapshots_create(authorized: bool = False) -> dict[str, Any]:
    """Create a local vault backup. Requires explicit authorization."""
    vault = _require_vault()
    if not authorized:
        raise HTTPException(status_code=403, detail={"authorization_required": True})
    return SnapshotManager(vault).create()
