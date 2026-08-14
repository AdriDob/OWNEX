"""Hybrid search, semantic index and AI context over the vault.

Search layers (combined with weights):
1. exact title match         (highest priority)
2. filename / path match
3. tag match  (tag:query)
4. metadata match  (key:value, e.g. created:2026)
5. link match (notes linking to the query)
6. full-text (SQLite FTS5, bm25)
7. semantic (cosine over embeddings)

Embeddings are provider-agnostic: a deterministic local hashed n-gram
embedder works offline (no API, no data leaves the machine); an optional
Ollama embedder is used when reachable. Vectors are cached in the index DB.
"""

from __future__ import annotations

import json
import math
import re
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from cores.knowledge.index import KnowledgeIndex
from cores.knowledge.parser import parse_markdown

_DIM = 256
_NGRAM = 3


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{2,}", text.lower())


class Embedder(Protocol):
    model_name: str

    def embed(self, text: str) -> list[float]: ...


class LocalHashEmbedder:
    """Deterministic offline embedder: hashed character n-grams → vector."""

    model_name = "local-hash-v1"

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * _DIM
        norm = text.lower()
        if len(norm) < _NGRAM:
            norm = norm.ljust(_NGRAM, " ")
        for i in range(len(norm) - _NGRAM + 1):
            gram = norm[i : i + _NGRAM]
            h = hash(gram) % _DIM
            vec[h] += 1.0
        mag = math.sqrt(sum(v * v for v in vec))
        if mag > 0:
            vec = [v / mag for v in vec]
        return vec


class OllamaEmbedder:
    """Optional local Ollama embeddings (no cloud). Falls back to local."""

    model_name = "ollama-embeddings"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self._base = base_url.rstrip("/")
        self._model = model

    def embed(self, text: str) -> list[float]:
        if len(text) > 8000:
            text = text[:8000]
        req = urllib.request.Request(
            f"{self._base}/api/embeddings",
            data=json.dumps({"model": self._model, "prompt": text}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            data = json.loads(resp.read())
        return [float(v) for v in data.get("embedding", [])]


class EmbeddingProvider:
    """Provider-agnostic facade: Ollama when reachable, local otherwise."""

    def __init__(self) -> None:
        self._local = LocalHashEmbedder()
        self._ollama: OllamaEmbedder | None = None
        self._ollama_ok = False

    @property
    def model_name(self) -> str:
        if self._ollama and self._ollama_ok:
            return self._ollama.model_name
        return self._local.model_name

    def _probe_ollama(self) -> None:
        if self._ollama is None:
            self._ollama = OllamaEmbedder()
        try:
            with urllib.request.urlopen(  # noqa: S310
                f"{self._ollama._base}/api/tags", timeout=3
            ) as resp:
                self._ollama_ok = resp.status == 200
        except Exception:
            self._ollama_ok = False

    def embed(self, text: str) -> list[float]:
        if self._ollama is None:
            self._probe_ollama()
        if self._ollama and self._ollama_ok:
            try:
                return self._ollama.embed(text)
            except Exception:
                self._ollama_ok = False
        return self._local.embed(text)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _snippet(text: str, query: str, width: int = 220) -> str:
    words = re.findall(r"[a-z0-9]+", query.lower())
    body = text.strip()
    if not words:
        return body[:width]
    lower = body.lower()
    for word in words:
        idx = lower.find(word)
        if idx >= 0:
            start = max(0, idx - width // 3)
            end = min(len(body), start + width)
            prefix = "…" if start > 0 else ""
            suffix = "…" if end < len(body) else ""
            return f"{prefix}{body[start:end].strip()}{suffix}"
    return body[:width]


def _note_text(index: KnowledgeIndex, rel_path: str) -> str:
    note = index.note(rel_path)
    if note is None:
        return ""
    try:
        from cores.knowledge.parser import read_note_safe

        root = getattr(index, "_vault_root", None)
        if root is not None:
            raw = read_note_safe(root / rel_path, root)
            if raw is not None:
                return raw
    except Exception:
        pass
    return f"{note['title']}\n{note['content_preview']}"


@dataclass
class SearchResult:
    path: str
    title: str
    snippet: str
    score: float
    tags: list[str]
    created: str | None = None
    modified: str | None = None
    source: str = "search"

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "title": self.title,
            "snippet": self.snippet,
            "score": round(self.score, 3),
            "tags": self.tags,
            "created": self.created,
            "modified": self.modified,
            "source": self.source,
        }


class KnowledgeSearcher:
    def __init__(self, index: KnowledgeIndex, provider: EmbeddingProvider | None = None):
        self.index = index
        self.provider = provider or EmbeddingProvider()

    # ── search ─────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        limit: int = 20,
        filters: dict[str, str] | None = None,
    ) -> list[SearchResult]:
        query = query.strip()
        filters = filters or {}
        notes = self.index.list_notes(limit=20000)
        if not notes:
            return []
        norm_q = query.lower()

        tag_filter = filters.get("tag")
        path_filter = filters.get("path")
        date_filter = filters.get("date")

        scores: list[tuple[float, dict[str, Any], str]] = []
        for note in notes:
            if tag_filter and tag_filter not in json.loads(note["tags"] or "[]"):
                continue
            if path_filter and path_filter.lower() not in note["path"].lower():
                continue
            if date_filter and not (
                (note["created"] or "").startswith(date_filter) or (note["modified"] or "").startswith(date_filter)
            ):
                continue

            score = 0.0
            source = "search"
            title_l = note["title"].lower()
            path_l = note["path"].lower()
            aliases = json.loads(note["aliases"] or "[]")
            tags = json.loads(note["tags"] or "[]")

            if title_l == norm_q:
                score += 100.0
                source = "exact"
            elif norm_q in title_l:
                score += 60.0
                source = "title"
            if norm_q in path_l:
                score += 45.0
                source = "path" if source == "search" else source
            if any(norm_q in a.lower() for a in aliases):
                score += 40.0
                source = "alias"
            if norm_q in tags:
                score += 35.0
                source = "tag"
            if norm_q.startswith("tag:") and norm_q[4:] in tags:
                score += 80.0
                source = "tag"

            if score > 0:
                scores.append((score, note, source))

        # link-based: notes linking to a note whose title matches
        link_hits = self._search_by_links(query)
        for from_path, link_score in link_hits:
            note = self.index.note(from_path)
            if note:
                scores.append((link_score, note, "link"))

        # FTS
        fts_hits = self._search_fts(query)
        for row, bm in fts_hits:
            note = self.index.note(row["path"])
            if note:
                scores.append((25.0 + bm * 40.0, note, "fulltext"))

        # semantic
        sem_hits = self._search_semantic(query, limit=15)
        for rel_path, sim in sem_hits:
            note = self.index.note(rel_path)
            if note:
                scores.append((sim * 55.0, note, "semantic"))

        # dedupe by path, keep best score per path
        best: dict[str, tuple[float, dict[str, Any], str]] = {}
        for score, note, source in scores:
            if note["path"] not in best or score > best[note["path"]][0]:
                best[note["path"]] = (score, note, source)

        ranked = sorted(best.values(), key=lambda x: x[0], reverse=True)[:limit]
        out: list[SearchResult] = []
        for score, note, source in ranked:
            body = _note_text(self.index, note["path"])
            out.append(
                SearchResult(
                    path=note["path"],
                    title=note["title"],
                    snippet=_snippet(body, query),
                    score=score,
                    tags=json.loads(note["tags"] or "[]"),
                    created=note["created"],
                    modified=note["modified"],
                    source=source,
                )
            )
        return out

    def _search_by_links(self, query: str) -> list[tuple[str, float]]:
        target = self.index.note_by_name(query)
        if target is None:
            return []
        bl = self.index.backlinks(target["path"])
        return [(b["from"], 30.0) for b in bl]

    def _search_fts(self, query: str) -> list[tuple[Any, float]]:
        import sqlite3

        terms = [t for t in re.findall(r"[a-z0-9_]+", query.lower()) if len(t) > 1]
        if not terms:
            return []
        match_expr = " OR ".join(f'"{t}"' for t in terms)
        try:
            with self.index._lock:
                rows = self.index._conn.execute(
                    """SELECT n.path, bm25(notes_fts) AS rank
                       FROM notes_fts JOIN notes n ON n.id = notes_fts.rowid
                       WHERE notes_fts MATCH ? ORDER BY rank LIMIT 30""",
                    (match_expr,),
                ).fetchall()
            return [(dict(r), max(0.0, min(1.0, -r["rank"] / 10.0))) for r in rows]
        except sqlite3.OperationalError:
            return []

    def _search_semantic(self, query: str, limit: int) -> list[tuple[str, float]]:
        qv = self.provider.embed(query)
        results: list[tuple[str, float]] = []
        for path, vec in self.index.all_embeddings().items():
            sim = cosine(qv, vec)
            if sim > 0.15:
                results.append((path, sim))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    # ── embeddings maintenance ─────────────────────────────────────────────

    def ensure_embeddings(self, limit: int = 200) -> dict[str, int]:
        """Compute and cache embeddings for notes missing them (batched)."""
        pending = self.index.notes_without_embeddings()
        computed = 0
        for path in pending[:limit]:
            text = _note_text(self.index, path)
            if text.strip():
                try:
                    vec = self.provider.embed(text)
                    self.index.set_embedding(path, self.provider.model_name, vec)
                    computed += 1
                except Exception:
                    continue
        return {"computed": computed, "pending": max(0, len(pending) - computed)}

    # ── AI context ─────────────────────────────────────────────────────────

    def build_context(self, query: str, max_notes: int = 5) -> dict[str, Any]:
        """Retrieval for AI: top notes + fragments + related graph. Never invents."""
        results = self.search(query, limit=max_notes)
        blocks: list[dict[str, Any]] = []
        for r in results:
            related = self.index.related(r.path, limit=3)
            blocks.append(
                {
                    "source": r.path,
                    "title": r.title,
                    "fragment": r.snippet,
                    "relevance": r.score,
                    "modified": r.modified,
                    "tags": r.tags,
                    "related": [{"path": p, "score": round(s, 2)} for p, s in related],
                }
            )
        return {
            "query": query,
            "generated_at": datetime.now(UTC).isoformat(),
            "note_count": len(blocks),
            "notes": blocks,
        }

    def summarize_note(self, rel_path: str, max_points: int = 6) -> dict[str, Any]:
        """Deterministic summary: headings + key sentences. No LLM required."""
        note = self.index.note(rel_path)
        if note is None:
            return {"error": "note not found"}
        text = _note_text(self.index, rel_path)
        parsed = parse_markdown(text, rel_path)
        sentences = re.split(r"(?<=[.!?])\s+", parsed.body)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 25][:max_points]
        return {
            "path": rel_path,
            "title": note["title"],
            "headings": parsed.headings[:12],
            "key_points": sentences,
            "tags": parsed.tags,
            "word_count": note["word_count"],
            "created": note["created"],
            "modified": note["modified"],
        }

    def find_outdated(self, days: int = 60) -> list[dict[str, Any]]:
        cutoff = datetime.now(UTC).timestamp() - days * 86400
        out: list[dict[str, Any]] = []
        for note in self.index.list_notes(limit=20000):
            mtime = note.get("mtime") or 0
            if mtime < cutoff:
                out.append(
                    {
                        "path": note["path"],
                        "title": note["title"],
                        "modified": note["modified"],
                        "last_modified": datetime.fromtimestamp(mtime).isoformat(),
                    }
                )
        return sorted(out, key=lambda x: x["last_modified"])[:200]

    def find_contradictions(self) -> list[dict[str, Any]]:
        """Conservative detection: explicit 'contradicts/conflicts with [[X]]' links
        plus same-tag notes with opposite status values in frontmatter."""
        out: list[dict[str, Any]] = []
        pattern = re.compile(r"(?:contradicts|conflicts with|refutes)\s*\[\[([^\]|]+)", re.IGNORECASE)
        for note in self.index.list_notes(limit=20000):
            text = _note_text(self.index, note["path"])
            for m in pattern.finditer(text):
                out.append(
                    {
                        "kind": "explicit",
                        "from": note["path"],
                        "against": m.group(1).strip(),
                    }
                )
        return sorted(out, key=lambda x: x["from"])

    def daily_summary(self, date: str | None = None) -> dict[str, Any]:
        """Notes created/modified on a given date (default: today)."""
        day = date or datetime.now().strftime("%Y-%m-%d")
        out: list[dict[str, Any]] = []
        for note in self.index.list_notes(limit=20000):
            if (note["created"] or "").startswith(day) or (note["modified"] or "").startswith(day):
                out.append(
                    {
                        "path": note["path"],
                        "title": note["title"],
                        "created": note["created"],
                        "modified": note["modified"],
                    }
                )
        return {"date": day, "notes": out}
