from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from cores.knowledge.abstracts import KnowledgeNormalizer
from cores.knowledge.models import CanonicalKnowledgeArtifact, KnowledgeContentType, KnowledgeMetadata


class GenericKnowledgeNormalizer(KnowledgeNormalizer):
    def normalize(self, parsed_payload: dict[str, Any]) -> dict[str, Any]:
        metadata = parsed_payload.get("metadata", {}) or {}
        metadata_obj = KnowledgeMetadata(
            source=str(parsed_payload.get("source", "unknown")),
            source_id=str(parsed_payload.get("source_id", "unknown")),
            source_type=str(parsed_payload.get("content_type", "other")),
            source_url=metadata.get("source_url") if isinstance(metadata, dict) else None,
            published_at=metadata.get("published_at"),
            version=metadata.get("version"),
            tags=list(parsed_payload.get("tags", [])) or list(metadata.get("tags", [])) or [],
            technologies=list(parsed_payload.get("technologies", [])) or list(metadata.get("technologies", [])) or [],
            cwe_ids=list(parsed_payload.get("cwe_ids", [])) or self._extract_cwe_ids(parsed_payload),
            cve_ids=list(parsed_payload.get("cve_ids", [])) or self._extract_cve_ids(parsed_payload),
            severity=str(parsed_payload.get("severity", "medium")),
            confidence=float(metadata.get("confidence", 0.0) or 0.0),
            references=list(parsed_payload.get("references", [])) or list(metadata.get("references", [])) or [],
            relationships=list(parsed_payload.get("relationships", [])) or [],
            provenance={
                "ingested_at": metadata.get("ingested_at"),
                "raw_source": metadata.get("raw_source"),
            },
            extra={**(metadata if isinstance(metadata, dict) else {})},
        )

        body = str(parsed_payload.get("body", ""))
        title = str(parsed_payload.get("title", "untitled"))
        summary = parsed_payload.get("summary") or self._build_summary(title, body)

        artifact = CanonicalKnowledgeArtifact(
            artifact_id="",
            title=title,
            summary=summary,
            description=parsed_payload.get("description"),
            content_type=KnowledgeContentType(parsed_payload.get("content_type", "other")),
            body=body,
            canonical_entities=[],
            metadata=metadata_obj,
            version=1,
            fingerprint=self._compute_fingerprint(title, body, metadata_obj),
            dedup_source_ids=[metadata_obj.source_id],
        )

        return {
            "artifact_id": artifact.artifact_id,
            "title": artifact.title,
            "summary": artifact.summary,
            "description": artifact.description,
            "content_type": artifact.content_type.value,
            "body": artifact.body,
            "canonical_entities": artifact.canonical_entities,
            "metadata": artifact.metadata.__dict__,
            "created_at": artifact.created_at,
            "updated_at": artifact.updated_at,
            "version": artifact.version,
            "fingerprint": artifact.fingerprint,
            "dedup_source_ids": artifact.dedup_source_ids,
        }

    def _compute_fingerprint(self, title: str, body: str, metadata: KnowledgeMetadata) -> str:
        base = f"{title}|{body}|{','.join(sorted(metadata.cwe_ids))}|{','.join(sorted(metadata.cve_ids))}|{metadata.source_id}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def _extract_cwe_ids(self, payload: dict[str, Any]) -> list[str]:
        text = " ".join(str(payload.get(k, "")) for k in ("title", "summary", "body"))
        return sorted(set(re.findall(r"CWE-\d{1,6}", text)))

    def _extract_cve_ids(self, payload: dict[str, Any]) -> list[str]:
        text = " ".join(str(payload.get(k, "")) for k in ("title", "summary", "body"))
        return sorted(set(re.findall(r"CVE-\d{4}-\d{4,}", text)))

    def _build_summary(self, title: str, body: str) -> str:
        summary = title
        if len(summary) < 10 and body:
            summary = body[:160].strip().replace("\n", " ")
        return summary
