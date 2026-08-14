"""OWNEX Knowledge Bridge — Obsidian vault integration.

Local-first, portable: the Obsidian vault (plain markdown) remains the single
source of truth. OWNEX reads, indexes, searches and generates context; all
writes require explicit authorization.

Modules:
- parser: markdown parsing (frontmatter, wikilinks, tags, embeds, headings)
- index:  VaultManager + SQLite knowledge index (FTS5, incremental)
- search: hybrid search + embeddings (local/ollama) + AI context + actions
- gitops: Git operations, secret scanning, snapshots, safe writes
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cores.knowledge.index import (
    DATA_DIR,
    KnowledgeIndex,
    VaultManager,
    get_knowledge_index,
    load_config,
    save_config,
)
from cores.knowledge.search import EmbeddingProvider, KnowledgeSearcher, LocalHashEmbedder, OllamaEmbedder

__all__ = [
    "DATA_DIR",
    "EmbeddingProvider",
    "KnowledgeIndex",
    "KnowledgeSearcher",
    "LocalHashEmbedder",
    "OllamaEmbedder",
    "VaultManager",
    "get_knowledge_index",
    "load_config",
    "save_config",
    "vault_health",
]


def _connected_index() -> KnowledgeIndex:
    cfg = load_config()
    vault = cfg.get("vault_path") or ""
    if not vault:
        raise ValueError("No vault connected")
    index = get_knowledge_index()
    index.set_vault_root(Path(vault).expanduser().resolve())
    return index


def vault_health() -> dict[str, Any]:
    """Consolidated knowledge dashboard (vault + index + git + backups + security)."""
    cfg = load_config()
    manager = VaultManager(cfg)
    info = manager.verify()
    if not info.connected:
        return {
            "connected": False,
            "vault": vars(info),
            "index": None,
        }
    index = _connected_index()
    stats = index.stats()
    broken = index.broken_links()
    duplicates = index.find_duplicates()
    missing = index.missing_attachments()

    from cores.knowledge.gitops import GitOps, SecretScanner, SnapshotManager

    vault_path = Path(info.vault_path)
    git = GitOps(vault_path)
    git_status = git.status()
    security = SecretScanner(vault_path).scan().to_dict()
    snapshots = SnapshotManager(vault_path)

    last_backup = snapshots.list()
    return {
        "connected": True,
        "vault": {
            "path": info.vault_path,
            "status": info.status,
            "files": info.files,
            "markdown": info.markdown,
            "attachments": info.attachments,
            "last_scan": stats["last_scan"],
            "index_healthy": stats["notes"] == info.markdown and info.markdown > 0,
        },
        "index": stats,
        "health": {
            "broken_links": len(broken),
            "duplicate_notes": len(duplicates),
            "missing_attachments": len(missing),
            "broken_link_items": broken[:20],
            "duplicate_items": duplicates[:10],
            "missing_items": missing[:20],
        },
        "git": git_status,
        "security": security,
        "backups": {
            "count": len(last_backup),
            "last": last_backup[0] if last_backup else None,
        },
    }


def ensure_initialized() -> dict[str, Any]:
    """Idempotent init: verify vault, incremental scan, seed embeddings."""
    cfg = load_config()
    manager = VaultManager(cfg)
    info = manager.verify()
    if not info.connected:
        return {"connected": False, "reason": info.reason}
    index = _connected_index()
    scan = index.scan_incremental()
    embeddings: dict[str, Any] = {"computed": 0, "pending": 0}
    try:
        index.set_embedding("__probe__", "local-hash-v1", [0.0])
        index._conn.execute("DELETE FROM embeddings WHERE note_path = '__probe__'")  # noqa: SLF001
        index._conn.commit()
    except Exception:
        pass
    return {
        "connected": True,
        "vault_path": info.vault_path,
        "scan": scan,
        "index_stats": index.stats(),
        "embeddings": embeddings,
    }
