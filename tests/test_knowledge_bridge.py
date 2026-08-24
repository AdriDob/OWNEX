"""Knowledge Bridge tests — vault connect, index, search, API, gitops, tasks."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from cores.knowledge import load_config, save_config
from cores.knowledge.gitops import SecretScanner
from cores.knowledge.index import KnowledgeIndex, VaultManager
from cores.knowledge.parser import parse_markdown
from cores.knowledge.search import KnowledgeSearcher
from cores.knowledge.tasks import get_knowledge_snapshot_history, run_knowledge_sync


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    (root / "Notes").mkdir(parents=True)
    (root / "assets").mkdir()
    (root / "Notes" / "Home.md").write_text(
        """---
title: Home
tags: [home, hub]
---
# Home

Welcome to the vault. See [[Bug Bounty]] and [[IDOR Checklist]].

- first note
- second note
""",
        encoding="utf-8",
    )
    (root / "Notes" / "Bug Bounty.md").write_text(
        """---
tags: [security, h1]
---
# Bug Bounty

Platform: HackerOne. Methodology for [[IDOR Checklist]].

Check for [[IDOR Checklist|IDOR]] on every endpoint.
""",
        encoding="utf-8",
    )
    (root / "Notes" / "IDOR Checklist.md").write_text(
        "# IDOR Checklist\n\nTest IDs with PUT /resource/{id} and compare ACL.\n",
        encoding="utf-8",
    )
    (root / "Notes" / "Orphan.md").write_text("# Orphan\n\nNo links anywhere.\n", encoding="utf-8")
    (root / "Notes" / "Dup A.md").write_text("# Dup A\n\nSame content.\n", encoding="utf-8")
    (root / "Notes" / "Dup B.md").write_text("# Dup A\n\nSame content.\n", encoding="utf-8")
    return root


@pytest.fixture()
def cfg(tmp_path: Path, vault: Path) -> Iterator[dict]:
    c = load_config()
    c["vault_path"] = str(vault)
    save_config(c)
    yield c
    # restore to disconnected state so other suites are not affected
    c2 = load_config()
    c2["vault_path"] = ""
    save_config(c2)


@pytest.fixture()
def index(tmp_path: Path, vault: Path, cfg: dict) -> Iterator[KnowledgeIndex]:
    idx = KnowledgeIndex(db_path=tmp_path / "test_kb.sqlite", vault_root=vault)
    idx.full_reindex()
    yield idx
    idx.close()


def _search(searcher: KnowledgeSearcher, q: str) -> list[str]:
    return [r.path for r in searcher.search(q, limit=5)]


# ── parser ────────────────────────────────────────────────────────────────


def test_parse_markdown_frontmatter_and_links() -> None:
    md = parse_markdown("# T\n\n[[A]] and [[B|label]] and ![[img.png]] #tag here\n", rel_path="Notes/T.md")
    assert md.title == "T"
    assert "A" in md.links
    assert "B" in md.links
    assert md.embeds == ["img.png"]
    assert "tag" in md.tags


# ── index ─────────────────────────────────────────────────────────────────


def test_full_reindex_counts(vault: Path, index: KnowledgeIndex) -> None:
    stats = index.stats()
    assert stats["notes"] == 6
    assert stats["distinct_tags"] >= 3


def test_incremental_scan_detects_new_note(vault: Path, index: KnowledgeIndex) -> None:
    (vault / "Notes" / "New.md").write_text("# New note\n", encoding="utf-8")
    result = index.scan_incremental()
    assert result["added"] == 1
    assert index.note("Notes/New.md") is not None


def test_incremental_scan_detects_changed_note(vault: Path, index: KnowledgeIndex) -> None:
    (vault / "Notes" / "Home.md").write_text("# Home changed\n", encoding="utf-8")
    result = index.scan_incremental()
    assert result["updated"] >= 1


def test_incremental_scan_detects_deletion(vault: Path, index: KnowledgeIndex) -> None:
    (vault / "Notes" / "Orphan.md").unlink()
    result = index.scan_incremental()
    assert result["removed"] == 1


def test_broken_links(vault: Path, index: KnowledgeIndex) -> None:
    (vault / "Notes" / "Broken.md").write_text("# Broken\n\n[[Does Not Exist]]\n", encoding="utf-8")
    index.scan_incremental()
    broken = index.broken_links()
    assert any("Does Not Exist" in b["to"] for b in broken)


def test_find_duplicates(vault: Path, index: KnowledgeIndex) -> None:
    dups = index.find_duplicates()
    assert any("Dup A" in d["paths"][0] for d in dups)


def test_backlinks_and_related(vault: Path, index: KnowledgeIndex) -> None:
    bl = index.backlinks("Notes/IDOR Checklist.md")
    assert len(bl) >= 2
    related = index.related("Notes/Bug Bounty.md")
    assert len(related) >= 1


def test_symlink_outside_vault_not_indexed(tmp_path: Path, index: KnowledgeIndex) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("# outside\n", encoding="utf-8")
    idx = KnowledgeIndex(db_path=tmp_path / "x.sqlite", vault_root=tmp_path / "empty")
    idx.set_vault_root(tmp_path / "empty")
    assert idx._allowed(tmp_path) is False
    idx.close()


# ── VaultManager ──────────────────────────────────────────────────────────


def test_vault_manager_connect_verify_clear(cfg: dict, vault: Path) -> None:
    manager = VaultManager(cfg)
    info = manager.verify()
    assert info.connected is True
    assert info.markdown == 6
    cleared = manager.clear_vault()
    assert cleared.connected is False
    assert load_config()["vault_path"] == ""


def test_vault_manager_rejects_non_vault(tmp_path: Path) -> None:
    cfg2 = {"vault_path": str(tmp_path)}
    info = VaultManager(cfg2).verify()
    assert info.connected is False


# ── search ────────────────────────────────────────────────────────────────


def test_lexical_search_fts(index: KnowledgeIndex) -> None:
    searcher = KnowledgeSearcher(index)
    hits = _search(searcher, "IDOR")
    assert hits[0] == "Notes/IDOR Checklist.md"
    assert hits[1] == "Notes/Bug Bounty.md"
    assert _search(searcher, "hackerone") == ["Notes/Bug Bounty.md"]


def test_search_tags(index: KnowledgeIndex) -> None:
    searcher = KnowledgeSearcher(index)
    assert _search(searcher, "home") == ["Notes/Home.md"]


def test_search_returns_nothing_for_garbage(index: KnowledgeIndex) -> None:
    searcher = KnowledgeSearcher(index)
    assert _search(searcher, "zzzzqqqq") == []


def test_semantic_search_local(vault: Path, index: KnowledgeIndex) -> None:
    from cores.knowledge.search import LocalHashEmbedder

    # Pin the same (deterministic) embedder on both sides of the similarity
    # check. With the default EmbeddingProvider facade on a host running
    # Ollama, the query gets embedded with nomic-embed-text while the test
    # stores a local-hash vector — cosine across vector spaces is noise.
    embedder = LocalHashEmbedder()
    target = embedder.embed("payout bounty methodology")
    index.set_embedding("Notes/Bug Bounty.md", "local-hash-v1", target)
    searcher = KnowledgeSearcher(index, provider=embedder)
    hits = searcher.search("payout", limit=5)  # only reachable via semantic path
    assert any("Bug Bounty" in r.path for r in hits)


def test_build_context(index: KnowledgeIndex) -> None:
    searcher = KnowledgeSearcher(index)
    ctx = searcher.build_context("IDOR", max_notes=3)
    assert ctx["note_count"] >= 1
    assert any("IDOR Checklist" in n["source"] for n in ctx["notes"])


# ── gitops: secrets + snapshots + writes ──────────────────────────────────


def test_secret_scanner_detects_and_ignores(tmp_path: Path) -> None:
    root = tmp_path / "v"
    root.mkdir()
    (root / "leak.md").write_text("password: hunter2\naws_key = AKIAIOSFODNN7EXAMPLE\n", encoding="utf-8")
    (root / "ok.md").write_text("# fine\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("secret inside git dir\n", encoding="utf-8")
    result = SecretScanner(root).scan()
    assert not result.clean
    assert all(f.file.startswith("leak.md") for f in result.findings)
    assert not any(f.file.startswith(".git/") for f in result.findings)


def test_safe_writer_requires_auth(tmp_path: Path) -> None:
    from cores.knowledge.gitops import SafeWriter, SnapshotManager

    root = tmp_path / "v"
    root.mkdir()
    writer = SafeWriter(root, SnapshotManager(root))
    denied = writer.write("Notes/a.md", "# x\n")
    assert denied["ok"] is False
    assert denied["authorization_required"] is True
    allowed = writer.write("Notes/a.md", "# x\n", authorized=True)
    assert allowed["ok"] is True
    assert allowed["action"] == "create"


def test_snapshot_manager_rotate(tmp_path: Path) -> None:
    from cores.knowledge.gitops import SnapshotManager

    root = tmp_path / "v"
    root.mkdir()
    (root / "f.md").write_text("# data\n", encoding="utf-8")
    sm = SnapshotManager(root, backup_dir=tmp_path / "backups")
    # simulate older snapshots with distinct names (1s-granularity names would collide)
    for i in range(7):
        sm._snapshot_path(ts=f"2026-01-01_00000{i}").write_bytes(b"old")
    result = sm.create(keep=5)
    assert result["ok"] is True
    assert len(sm.list()) == 5


# ── tasks / sync ──────────────────────────────────────────────────────────


def test_run_knowledge_sync_without_vault() -> None:
    save_config({"vault_path": ""})
    result = run_knowledge_sync()
    assert result["ok"] is False


def test_run_knowledge_sync_with_vault(cfg: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cores.knowledge.index import KnowledgeIndex

    monkeypatch.setattr("cores.knowledge.tasks._HEALTH_LOG", tmp_path / "health.jsonl")
    idx = KnowledgeIndex(db_path=tmp_path / "sync.sqlite", vault_root=Path(cfg["vault_path"]))
    monkeypatch.setattr("cores.knowledge.index.get_knowledge_index", lambda: idx)
    result = run_knowledge_sync()
    assert result["ok"] is True
    assert result["scan"]["added"] == 6
    history = get_knowledge_snapshot_history()
    assert history and history[-1]["ok"] is True
    idx.close()


# ── scheduler jobs ─────────────────────────────────────────────────────────


def test_knowledge_jobs_registered() -> None:
    from core.scheduler.jobs import get_all_jobs

    jobs = get_all_jobs()
    assert "knowledge" in jobs
    ids = [j.job_id for j in jobs["knowledge"]]
    assert "knowledge_sync_daily" in ids
    handler = next(j.handler for j in jobs["knowledge"] if j.job_id == "knowledge_sync_daily")
    assert handler == "cores.knowledge.tasks:run_knowledge_sync"


# ── API ────────────────────────────────────────────────────────────────────


def test_api_router_mounted() -> None:
    import api.main  # noqa: F401
    from api.main import app

    paths = app.openapi()["paths"]
    assert "/api/knowledge/" in paths
    assert "/api/knowledge/health" in paths
    assert "/api/knowledge/search" in paths


def _authed_client(device_id: str):
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"device_id": device_id})
    if resp.status_code == 200 and "data" in resp.json():
        client.headers.update({"Authorization": f"Bearer {resp.json()['data']['token']}"})
    csrf = resp.cookies.get("csrf_token") or resp.cookies.get("csrf")
    if csrf:
        client.headers.update({"X-CSRF-Token": csrf})
    return client


def test_api_status_disconnected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cores.knowledge.index.load_config", lambda: {"vault_path": ""})
    client = _authed_client("pytest-kb-disconnected")
    resp = client.get("/api/knowledge/")
    assert resp.status_code == 200
    assert resp.json()["connected"] is False


def test_api_full_flow(cfg: dict, vault: Path) -> None:
    client = _authed_client("pytest-kb-flow")
    resp = client.get("/api/knowledge/")
    assert resp.status_code == 200
    assert resp.json()["connected"] is True
    search = client.get("/api/knowledge/search", params={"q": "IDOR"})
    assert search.status_code == 200
    paths = [r["path"] for r in search.json()["results"]]
    assert paths[0] == "Notes/IDOR Checklist.md"
    health = client.get("/api/knowledge/health")
    assert health.status_code == 200
    assert health.json()["connected"] is True
    assert health.json()["index"]["notes"] == 6
