from __future__ import annotations

from typing import Any

from cores.knowledge.abstracts import KnowledgeIndexer


class MemoryKnowledgeIndexer(KnowledgeIndexer):
    def __init__(self) -> None:
        self._index: list[dict[str, Any]] = []

    def index(self, normalized_record: dict[str, Any]) -> None:
        self._index.append(normalized_record)

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        query_lower = query.lower()
        results: list[dict[str, Any]] = []
        for artifact in self._index:
            title = str(artifact.get("title", "")).lower()
            summary = str(artifact.get("summary", "")).lower()
            body = str(artifact.get("body", "")).lower()
            if query_lower in title or query_lower in summary or query_lower in body:
                results.append(artifact)
            if len(results) >= limit:
                break
        return results
