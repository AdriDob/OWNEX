from __future__ import annotations

import re
from typing import Any

from cores.knowledge.abstracts import KnowledgeEnricher


class KnowledgeEntityEnricher(KnowledgeEnricher):
    def enrich(self, normalized_record: dict[str, Any]) -> dict[str, Any]:
        body = str(normalized_record.get("body", ""))
        metadata = normalized_record.get("metadata", {})
        entities = set(normalized_record.get("canonical_entities", []))

        entities.update(self._extract_cwe_entities(body))
        entities.update(self._extract_cve_entities(body))
        entities.update(self._extract_technology_entities(metadata))

        normalized_record["canonical_entities"] = sorted(entities)
        normalized_record["metadata"] = {
            **metadata,
            "derived_entities": normalized_record["canonical_entities"],
        }
        return normalized_record

    def _extract_cwe_entities(self, body: str) -> set[str]:
        return {match for match in re.findall(r"(CWE-\d{1,6})", body)}

    def _extract_cve_entities(self, body: str) -> set[str]:
        return {match for match in re.findall(r"(CVE-\d{4}-\d{4,})", body)}

    def _extract_technology_entities(self, metadata: dict[str, Any]) -> set[str]:
        techs = metadata.get("technologies", []) or []
        return {str(t).lower() for t in techs if t}
