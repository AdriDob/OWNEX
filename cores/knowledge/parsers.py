from __future__ import annotations

import logging
from typing import Any

from cores.knowledge.abstracts import KnowledgeParser

logger = logging.getLogger("cateye.knowledge.parsers")


class GenericKnowledgeParser(KnowledgeParser):
    def parse(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(raw_payload, dict):
            raise ValueError("Knowledge payload must be a dict")

        parsed = {
            "source": raw_payload.get("source") or raw_payload.get("source_name") or "unknown",
            "source_id": raw_payload.get("source_id") or raw_payload.get("id") or "unknown",
            "title": raw_payload.get("title") or raw_payload.get("name") or "untitled",
            "summary": raw_payload.get("summary"),
            "description": raw_payload.get("description"),
            "body": raw_payload.get("body") or raw_payload.get("content") or "",
            "content_type": raw_payload.get("content_type") or raw_payload.get("type") or "other",
            "metadata": raw_payload.get("metadata") or {},
            "tags": raw_payload.get("tags") or [],
            "technologies": raw_payload.get("technologies") or [],
            "cwe_ids": raw_payload.get("cwe_ids") or raw_payload.get("cwes") or [],
            "cve_ids": raw_payload.get("cve_ids") or raw_payload.get("cves") or [],
            "severity": raw_payload.get("severity"),
            "references": raw_payload.get("references") or [],
            "relationships": raw_payload.get("relationships") or [],
        }

        if isinstance(parsed["metadata"], str):
            parsed["metadata"] = {"raw": parsed["metadata"]}

        return parsed
