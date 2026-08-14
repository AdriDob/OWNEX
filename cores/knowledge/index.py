"""Knowledge Index for Obsidian vaults.

The vault (a plain folder of .md files) is the single source of truth.
OWNEX builds a SQLite index (notes, links, tags, FTS5, embeddings cache) on
top of it — the index is disposable and can always be rebuilt from the vault.

Design:
- notes keyed by normalized relative path
- incremental scans (mtime/size/sha256 diff) — never re-indexes the whole
  vault on every change
- batch upserts in single transactions (scales to 50k notes)
- all writes go through a lock (background watcher + API threads)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.knowledge.parser import ParsedNote, is_attachment, parse_markdown, read_note_safe

logger = logging.getLogger("ownex.knowledge")

DATA_DIR = Path(os.getenv("OWNEX_DATA_DIR", "data"))
CONFIG_PATH = DATA_DIR / "knowledge" / "config.json"
DB_PATH = DATA_DIR / "knowledge" / "knowledge.db"

ENV_VAULT = "OBSIDIAN_VAULT_PATH"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    aliases TEXT NOT NULL DEFAULT '[]',
    tags TEXT NOT NULL DEFAULT '[]',
    created TEXT, modified TEXT, updated TEXT,
    mtime REAL NOT NULL DEFAULT 0,
    size INTEGER NOT NULL DEFAULT 0,
    sha256 TEXT NOT NULL DEFAULT '',
    word_count INTEGER NOT NULL DEFAULT 0,
    content_preview TEXT NOT NULL DEFAULT '',
    frontmatter_keys TEXT NOT NULL DEFAULT '[]',
    indexed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY,
    from_path TEXT NOT NULL,
    to_path TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'link'
);
CREATE INDEX IF NOT EXISTS idx_links_to ON links(to_path);
CREATE INDEX IF NOT EXISTS idx_links_from ON links(from_path);
CREATE TABLE IF NOT EXISTS tags (
    note_path TEXT NOT NULL,
    tag TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
CREATE TABLE IF NOT EXISTS embeddings (
    note_path TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    vector TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title, body, tokenize='porter unicode61'
);
CREATE TABLE IF NOT EXISTS scan_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_DEFAULT_CONFIG: dict[str, Any] = {
    "vault_path": "",
    "watcher_interval_minutes": 10,
    "backup_keep": 10,
    "backup_dir": "",
}


def _sha256_text(text: str | bytes) -> str:
    data = text if isinstance(text, bytes) else text.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _norm(value: str) -> str:
    return re.sub(r"[\s_\-/]+", "", value).lower()


def load_config() -> dict[str, Any]:
    cfg = dict(_DEFAULT_CONFIG)
    try:
        if CONFIG_PATH.exists():
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                cfg.update(loaded)
    except Exception:
        pass
    if ENV_VAULT in os.environ:
        cfg["vault_path"] = os.environ[ENV_VAULT]
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


@dataclass
class VaultInfo:
    connected: bool
    vault_path: str = ""
    status: str = "DISCONNECTED"
    files: int = 0
    markdown: int = 0
    attachments: int = 0
    last_scan: str | None = None
    index_healthy: bool = False
    reason: str = ""


class VaultManager:
    """Resolves and validates the Obsidian vault path (env > config > UI)."""

    def __init__(self, cfg: dict[str, Any] | None = None):
        self.cfg = cfg or load_config()

    @property
    def vault_path(self) -> Path | None:
        raw = self.cfg.get("vault_path") or ""
        if not raw:
            return None
        return Path(raw).expanduser().resolve()

    def set_vault(self, path: str) -> VaultInfo:
        resolved = str(Path(path).expanduser().resolve())
        self.cfg["vault_path"] = resolved
        save_config(self.cfg)
        return self.verify()

    def clear_vault(self) -> VaultInfo:
        self.cfg["vault_path"] = ""
        save_config(self.cfg)
        return VaultInfo(connected=False, status="DISCONNECTED")

    def verify(self) -> VaultInfo:
        vp = self.vault_path
        if vp is None:
            return VaultInfo(connected=False, status="DISCONNECTED", reason="No vault path configured")
        if not vp.exists():
            return VaultInfo(connected=False, vault_path=str(vp), status="ERROR", reason="Path does not exist")
        if not vp.is_dir():
            return VaultInfo(connected=False, vault_path=str(vp), status="ERROR", reason="Path is not a directory")
        md_count = 0
        total = 0
        attachments = 0
        try:
            for f in vp.rglob("*"):
                if f.is_file():
                    total += 1
                    if f.suffix.lower() == ".md":
                        md_count += 1
                    elif is_attachment(f.name):
                        attachments += 1
        except OSError as e:
            return VaultInfo(connected=False, vault_path=str(vp), status="ERROR", reason=str(e))
        if md_count == 0:
            return VaultInfo(
                connected=False,
                vault_path=str(vp),
                status="ERROR",
                reason="No markdown files found (is this an Obsidian vault?)",
            )
        return VaultInfo(
            connected=True,
            vault_path=str(vp),
            status="CONNECTED",
            files=total,
            markdown=md_count,
            attachments=attachments,
        )


class KnowledgeIndex:
    """SQLite-backed index over the vault. Rebuildable at any time."""

    def __init__(self, db_path: Path | None = None, vault_root: Path | None = None):
        self._db_path = Path(db_path or DB_PATH)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._vault_root = vault_root
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ── lifecycle ──────────────────────────────────────────────────────────

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def set_vault_root(self, root: Path) -> None:
        self._vault_root = root.resolve()

    def _allowed(self, path: Path) -> bool:
        if self._vault_root is None:
            return True
        root = self._vault_root.resolve()
        resolved = path.resolve()
        if resolved == root:
            return True
        return root in resolved.parents and not resolved.is_symlink()

    # ── scanning ───────────────────────────────────────────────────────────

    def _walk(self) -> list[tuple[Path, float, int, str]]:
        """List all markdown files with their fingerprint (mtime, size, sha)."""
        root = self._vault_root
        if root is None or not root.exists():
            return []
        out: list[tuple[Path, float, int, str]] = []
        for f in sorted(root.rglob("*.md")):
            if f.is_symlink() or not self._allowed(f):
                continue
            try:
                stat = f.stat()
                digest = _sha256_text(f.read_bytes())
            except OSError:
                continue
            out.append((f, stat.st_mtime, stat.st_size, digest))
        return out

    def full_reindex(self) -> dict[str, int]:
        with self._lock:
            self._conn.execute("DELETE FROM notes")
            self._conn.execute("DELETE FROM links")
            self._conn.execute("DELETE FROM tags")
            self._conn.execute("DELETE FROM notes_fts")
            self._conn.commit()
        stats = self.scan_incremental()
        self._set_meta("last_scan", _now_iso())
        return stats

    def scan_incremental(self) -> dict[str, int]:
        """Only parse files whose fingerprint changed. Returns add/update/remove counts."""
        if self._vault_root is None or not self._vault_root.exists():
            return {"added": 0, "updated": 0, "removed": 0}

        with self._lock:
            known = {
                row["path"]: (row["mtime"], row["size"], row["sha256"])
                for row in self._conn.execute("SELECT path, mtime, size, sha256 FROM notes")
            }

        added: list[tuple[Path, float, int, str]] = []
        updated: list[tuple[Path, float, int, str]] = []
        for f, mtime, size, digest in self._walk():
            rel = str(f.relative_to(self._vault_root)).replace("\\", "/")
            prev = known.get(rel)
            if prev is None:
                added.append((f, mtime, size, digest))
            elif prev[2] != digest or prev[0] != mtime:
                updated.append((f, mtime, size, digest))

        removed_paths = [rel for rel in known if not (self._vault_root / rel).exists()]

        with self._lock:
            for rel in removed_paths:
                self._remove_note_locked(rel)
            for f, mtime, size, digest in added:
                self._index_file_locked(f, mtime, size, digest)
            for f, mtime, size, digest in updated:
                self._index_file_locked(f, mtime, size, digest)
            self._conn.commit()

        if added or updated or removed_paths:
            self._set_meta("last_scan", _now_iso())
        return {"added": len(added), "updated": len(updated), "removed": len(removed_paths)}

    # ── note upsert ────────────────────────────────────────────────────────

    def _index_file_locked(self, f: Path, mtime: float, size: int, digest: str) -> None:
        if self._vault_root is None:
            return
        rel = str(f.relative_to(self._vault_root)).replace("\\", "/")
        raw = read_note_safe(f, self._vault_root)
        if raw is None:
            return
        parsed = parse_markdown(raw, rel)
        self._upsert_note_locked(parsed, mtime, size, digest, raw)

    def _upsert_note_locked(self, parsed: ParsedNote, mtime: float, size: int, digest: str, raw: str) -> None:
        existing = self._conn.execute("SELECT id FROM notes WHERE path = ?", (parsed.path,)).fetchone()
        self._conn.execute(
            """INSERT OR REPLACE INTO notes
               (id, path, title, aliases, tags, created, modified, updated,
                mtime, size, sha256, word_count, content_preview, frontmatter_keys, indexed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                existing["id"] if existing else None,
                parsed.path,
                parsed.title,
                json.dumps(parsed.aliases),
                json.dumps(parsed.tags),
                parsed.created,
                parsed.modified,
                parsed.updated,
                mtime,
                size,
                digest,
                parsed.word_count,
                raw[:300].replace("\n", " "),
                json.dumps(sorted(parsed.frontmatter.keys())),
                _now_iso(),
            ),
        )
        # capture the note id immediately: last_insert_rowid is invalidated by the
        # links/tags inserts below and would collide with existing FTS rowids.
        note_id = existing["id"] if existing else self._conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self._conn.execute("DELETE FROM links WHERE from_path = ?", (parsed.path,))
        for target in parsed.links:
            self._conn.execute(
                "INSERT INTO links (from_path, to_path, kind) VALUES (?, ?, 'link')",
                (parsed.path, target),
            )
        for target in parsed.embeds:
            self._conn.execute(
                "INSERT INTO links (from_path, to_path, kind) VALUES (?, ?, 'embed')",
                (parsed.path, target),
            )
        for url in parsed.markdown_links:
            self._conn.execute(
                "INSERT INTO links (from_path, to_path, kind) VALUES (?, ?, 'markdown')",
                (parsed.path, url),
            )
        self._conn.execute("DELETE FROM tags WHERE note_path = ?", (parsed.path,))
        for tag in parsed.tags:
            self._conn.execute("INSERT INTO tags (note_path, tag) VALUES (?, ?)", (parsed.path, tag))
        self._conn.execute("DELETE FROM notes_fts WHERE rowid = ?", (note_id,))
        self._conn.execute("INSERT INTO notes_fts (rowid, title, body) VALUES (?, ?, ?)", (note_id, parsed.title, raw))

    def _remove_note_locked(self, rel: str) -> None:
        row = self._conn.execute("SELECT id FROM notes WHERE path = ?", (rel,)).fetchone()
        self._conn.execute("DELETE FROM notes WHERE path = ?", (rel,))
        self._conn.execute("DELETE FROM links WHERE from_path = ? OR to_path = ?", (rel, rel))
        self._conn.execute("DELETE FROM tags WHERE note_path = ?", (rel,))
        self._conn.execute("DELETE FROM embeddings WHERE note_path = ?", (rel,))
        if row:
            self._conn.execute("DELETE FROM notes_fts WHERE rowid = ?", (row["id"],))

    # ── queries ────────────────────────────────────────────────────────────

    def note(self, rel_path: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM notes WHERE path = ?", (rel_path,)).fetchone()
            return dict(row) if row else None

    def note_by_name(self, name: str) -> dict[str, Any] | None:
        """Find a note by title/alias/stem (Obsidian-style resolution)."""
        with self._lock:
            for row in self._conn.execute(
                "SELECT * FROM notes WHERE title = ? OR path = ? OR path LIKE ?",
                (name, name, f"%/{name}.md"),
            ):
                return dict(row)
            norm = _norm(name)
            for row in self._conn.execute("SELECT * FROM notes"):
                note = dict(row)
                aliases = json.loads(note.get("aliases") or "[]")
                if norm in {_norm(a) for a in aliases} or _norm(note["title"]) == norm:
                    return note
        return None

    def list_notes(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM notes ORDER BY title LIMIT ? OFFSET ?", (limit, offset)).fetchall()
            return [dict(r) for r in rows]

    def outgoing_links(self, rel_path: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT to_path, kind FROM links WHERE from_path = ?", (rel_path,)).fetchall()
            return [dict(r) for r in rows]

    def backlinks(self, rel_path: str) -> list[dict[str, Any]]:
        """Notes that link to this note (wikilink targets resolved by name)."""
        note = self.note(rel_path)
        if note is None:
            return []
        names = {_norm(note["title"]), _norm(Path(note["path"]).stem)}
        names.update(_norm(a) for a in json.loads(note.get("aliases") or "[]"))
        with self._lock:
            rows = self._conn.execute("SELECT DISTINCT from_path, to_path, kind FROM links").fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            target = _norm(Path(row["to_path"]).stem)
            if target in names:
                out.append({"from": row["from_path"], "kind": row["kind"]})
        return sorted(out, key=lambda x: x["from"])

    def related(self, rel_path: str, limit: int = 12) -> list[tuple[str, float]]:
        """Related notes by shared tags + shared links + backlinks."""
        note = self.note(rel_path)
        if note is None:
            return []
        tags = set(json.loads(note.get("tags") or "[]"))
        out_links = {Path(link["to_path"]).stem for link in self.outgoing_links(rel_path)}
        with self._lock:
            tag_rows = self._conn.execute("SELECT DISTINCT note_path, tag FROM tags").fetchall()
            link_rows = self._conn.execute("SELECT DISTINCT from_path, to_path FROM links").fetchall()
        scores: dict[str, float] = {}
        for row in tag_rows:
            if row["note_path"] == rel_path:
                continue
            if row["tag"] in tags:
                scores[row["note_path"]] = scores.get(row["note_path"], 0.0) + 1.5
        for row in link_rows:
            if row["from_path"] == rel_path:
                continue
            if Path(row["to_path"]).stem in out_links:
                scores[row["from_path"]] = scores.get(row["from_path"], 0.0) + 2.0
            if row["to_path"] == rel_path:
                scores[row["from_path"]] = scores.get(row["from_path"], 0.0) + 3.0
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        return ranked

    def broken_links(self) -> list[dict[str, Any]]:
        """Wikilinks pointing to notes that do not exist."""
        stems = set()
        aliases = set()
        with self._lock:
            for row in self._conn.execute("SELECT path, title, aliases FROM notes"):
                stems.add(_norm(Path(row["path"]).stem))
                stems.add(_norm(row["title"]))
                aliases.update(_norm(a) for a in json.loads(row["aliases"] or "[]"))
            rows = self._conn.execute("SELECT from_path, to_path FROM links WHERE kind = 'link'").fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            target = _norm(Path(row["to_path"]).stem)
            if target and target not in stems and target not in aliases:
                out.append({"from": row["from_path"], "to": row["to_path"]})
        return sorted(out, key=lambda x: (x["from"], x["to"]))

    def missing_attachments(self) -> list[dict[str, Any]]:
        if self._vault_root is None:
            return []
        out: list[dict[str, Any]] = []
        with self._lock:
            rows = self._conn.execute("SELECT from_path, to_path FROM links WHERE kind = 'embed'").fetchall()
        for row in rows:
            candidates = [row["to_path"], row["to_path"].lstrip("./")]
            found = False
            for cand in candidates:
                rel = self._vault_root / cand
                if rel.exists() or (self._vault_root / Path(cand).name).exists():
                    found = True
                    break
            if not found:
                out.append({"from": row["from_path"], "attachment": row["to_path"]})
        return sorted(out, key=lambda x: (x["from"], x["attachment"]))

    def find_duplicates(self) -> list[dict[str, Any]]:
        """Near-duplicate notes (same normalized body hash, different paths)."""
        groups: dict[str, list[str]] = {}
        with self._lock:
            rows = self._conn.execute("SELECT path, title, sha256 FROM notes").fetchall()
        for row in rows:
            groups.setdefault(row["sha256"], []).append(row["path"])
        out = []
        for paths in groups.values():
            if len(paths) > 1:
                out.append({"paths": sorted(paths)})
        return sorted(out, key=lambda g: len(g["paths"]), reverse=True)

    # ── embeddings cache ───────────────────────────────────────────────────

    def set_embedding(self, note_path: str, model: str, vector: list[float]) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO embeddings (note_path, model, vector) VALUES (?, ?, ?)",
                (note_path, model, json.dumps(vector)),
            )
            self._conn.commit()

    def get_embedding(self, note_path: str) -> list[float] | None:
        with self._lock:
            row = self._conn.execute("SELECT vector FROM embeddings WHERE note_path = ?", (note_path,)).fetchone()
            return json.loads(row["vector"]) if row else None

    def all_embeddings(self) -> dict[str, list[float]]:
        with self._lock:
            rows = self._conn.execute("SELECT note_path, vector FROM embeddings").fetchall()
        return {r["note_path"]: json.loads(r["vector"]) for r in rows}

    def notes_without_embeddings(self) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT path FROM notes WHERE path NOT IN (SELECT note_path FROM embeddings)"
            ).fetchall()
            return [r["path"] for r in rows]

    # ── stats / health ─────────────────────────────────────────────────────

    def _set_meta(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute("INSERT OR REPLACE INTO scan_meta (key, value) VALUES (?, ?)", (key, value))
            self._conn.commit()

    def _get_meta(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute("SELECT value FROM scan_meta WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else None

    def stats(self) -> dict[str, Any]:
        with self._lock:
            notes = self._conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            tags = self._conn.execute("SELECT COUNT(DISTINCT tag) FROM tags").fetchone()[0]
            links = self._conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        last_scan = self._get_meta("last_scan")
        return {
            "notes": notes,
            "distinct_tags": tags,
            "links": links,
            "last_scan": last_scan,
        }


def get_knowledge_index() -> KnowledgeIndex:
    global _knowledge_index
    if _knowledge_index is None:
        _knowledge_index = KnowledgeIndex()
    return _knowledge_index


def reset_knowledge_index() -> None:
    global _knowledge_index
    if _knowledge_index is not None:
        _knowledge_index.close()
        _knowledge_index = None


_knowledge_index: KnowledgeIndex | None = None
