from __future__ import annotations

import hashlib
from typing import Any

from cores.knowledge.abstracts import KnowledgeDeduplicator


class FingerprintDeduplicator(KnowledgeDeduplicator):
    def fingerprint(self, normalized_record: dict[str, Any]) -> str:
        title = str(normalized_record.get("title", ""))
        body = str(normalized_record.get("body", ""))
        source_id = str(normalized_record.get("metadata", {}).get("source_id", ""))
        cwes = sorted(normalized_record.get("metadata", {}).get("cwe_ids", []))
        cves = sorted(normalized_record.get("metadata", {}).get("cve_ids", []))
        base = f"{title}|{body}|{source_id}|{','.join(cwes)}|{','.join(cves)}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def merge(self, existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        merged = existing.copy()
        merged["summary"] = existing.get("summary") or incoming.get("summary")
        merged["description"] = existing.get("description") or incoming.get("description")
        merged["body"] = existing.get("body") or incoming.get("body")

        existing_meta = merged.get("metadata", {})
        incoming_meta = incoming.get("metadata", {})

        merged_meta = {
            **existing_meta,
            **incoming_meta,
            "tags": sorted(set(existing_meta.get("tags", []) + incoming_meta.get("tags", []))),
            "technologies": sorted(set(existing_meta.get("technologies", []) + incoming_meta.get("technologies", []))),
            "cwe_ids": sorted(set(existing_meta.get("cwe_ids", []) + incoming_meta.get("cwe_ids", []))),
            "cve_ids": sorted(set(existing_meta.get("cve_ids", []) + incoming_meta.get("cve_ids", []))),
            "references": sorted(set(existing_meta.get("references", []) + incoming_meta.get("references", []))),
            "relationships": existing_meta.get("relationships", []) + incoming_meta.get("relationships", []),
            "confidence": max(float(existing_meta.get("confidence", 0.0)), float(incoming_meta.get("confidence", 0.0))),
            "provenance": {**existing_meta.get("provenance", {}), **incoming_meta.get("provenance", {})},
        }

        merged["metadata"] = merged_meta
        merged["dedup_source_ids"] = sorted(set(existing.get("dedup_source_ids", []) + incoming.get("dedup_source_ids", [])))

        merged["version"] = max(int(existing.get("version", 1)), int(incoming.get("version", 1))) + 1
        return merged
