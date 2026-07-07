"""DuplicateDetector — finds similar findings in historical data.

Compares a candidate finding against stored findings using multiple signals:
  - endpoint similarity (URL path structure)
  - vulnerability class match
  - parameter fingerprint
  - text similarity of description

Uses DedupTracker from cores.dedup to prevent duplicate history entries.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from cores.dedup import fingerprint_path

logger = logging.getLogger("cateye.analysis.duplicate_detector")

HIGH_RISK_THRESHOLD = 0.7
MEDIUM_RISK_THRESHOLD = 0.4


@dataclass
class DuplicateMatch:
    finding_id: int | str
    similarity: float
    matched_on: list[str]
    program: str
    title: str
    age_days: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": str(self.finding_id),
            "similarity": round(self.similarity, 4),
            "matched_on": self.matched_on,
            "program": self.program or "",
            "title": self.title or "",
            "age_days": self.age_days,
        }


@dataclass
class DuplicateAssessment:
    risk: float
    verdict: str
    matches: list[DuplicateMatch]
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk": round(self.risk, 4),
            "verdict": self.verdict,
            "matches": [m.to_dict() for m in self.matches],
            "recommendation": self.recommendation,
        }


class DuplicateDetector:
    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def load_history(self, findings: list[dict[str, Any]]) -> None:
        from cores.dedup import get_session_tracker

        tracker = get_session_tracker()
        deduped: list[dict[str, Any]] = []
        for f in findings:
            url = f.get("url") or f.get("endpoint") or ""
            method = f.get("method", "")
            fp = fingerprint_path(url, method) if url else str(f.get("id", ""))
            if not tracker.seen(fp):
                deduped.append(f)
        self._history = deduped

    def assess(self, finding: dict[str, Any]) -> DuplicateAssessment:
        if not self._history:
            return DuplicateAssessment(
                risk=0.0,
                verdict="unknown",
                matches=[],
                recommendation="No historical data to compare against",
            )

        matches: list[DuplicateMatch] = []
        for historical in self._history:
            similarity, reasons = self._compare(finding, historical)
            if similarity >= MEDIUM_RISK_THRESHOLD:
                hist_id = historical.get("id", 0)
                matches.append(DuplicateMatch(
                    finding_id=hist_id,
                    similarity=similarity,
                    matched_on=reasons,
                    program=historical.get("program", "") or "",
                    title=historical.get("title", "") or "",
                    age_days=self._age_days(historical),
                ))

        matches.sort(key=lambda m: m.similarity, reverse=True)
        matches = matches[:5]

        if not matches:
            return DuplicateAssessment(
                risk=0.0,
                verdict="clean",
                matches=[],
                recommendation="No similar findings found — likely unique",
            )

        top_risk = matches[0].similarity
        if top_risk >= HIGH_RISK_THRESHOLD:
            verdict = "high"
            recommendation = "DO NOT SUBMIT — very similar to existing finding"
        elif top_risk >= MEDIUM_RISK_THRESHOLD:
            verdict = "medium"
            recommendation = "Consider pivoting to a different attack vector"
        else:
            verdict = "low"
            recommendation = "Low similarity — proceed with caution"

        return DuplicateAssessment(
            risk=top_risk,
            verdict=verdict,
            matches=matches,
            recommendation=recommendation,
        )

    def _compare(self, a: dict[str, Any], b: dict[str, Any]) -> tuple[float, list[str]]:
        reasons: list[str] = []
        scores: list[float] = []

        endpoint_score, endpoint_match = self._compare_endpoints(a, b)
        scores.append(endpoint_score * 0.35)
        if endpoint_match:
            reasons.append(endpoint_match)

        vuln_score, vuln_match = self._compare_vulnerability_class(a, b)
        scores.append(vuln_score * 0.25)
        if vuln_match:
            reasons.append(vuln_match)

        param_score, param_match = self._compare_parameters(a, b)
        scores.append(param_score * 0.20)
        if param_match:
            reasons.append(param_match)

        text_score, text_match = self._compare_text(a, b)
        scores.append(text_score * 0.20)
        if text_match:
            reasons.append(text_match)

        total = sum(scores) / max(0.35 + 0.25 + 0.20 + 0.20, 1)
        return min(1.0, total), reasons

    def _compare_endpoints(self, a: dict[str, Any], b: dict[str, Any]) -> tuple[float, str]:
        url_a = (a.get("url") or a.get("endpoint", "") or "").lower()
        url_b = (b.get("url") or b.get("endpoint", "") or "").lower()
        if not url_a or not url_b:
            return 0.0, ""
        path_a = self._normalize_path(url_a)
        path_b = self._normalize_path(url_b)
        ratio = SequenceMatcher(None, path_a, path_b).ratio()
        if ratio > 0.8:
            return ratio, f"Similar endpoint path ({ratio:.0%})"
        return ratio * 0.5, ""

    def _compare_vulnerability_class(self, a: dict[str, Any], b: dict[str, Any]) -> tuple[float, str]:
        cls_a = (a.get("vulnerability_class") or a.get("type", "") or "").lower()
        cls_b = (b.get("vulnerability_class") or b.get("type", "") or "").lower()
        if cls_a and cls_b and cls_a == cls_b:
            return 1.0, f"Same vulnerability class ({cls_a})"
        if cls_a and cls_b:
            return 0.3, ""
        return 0.0, ""

    def _compare_parameters(self, a: dict[str, Any], b: dict[str, Any]) -> tuple[float, str]:
        params_a = set(k.lower() for k in (a.get("params") or a.get("parameters", {})))
        params_b = set(k.lower() for k in (b.get("params") or b.get("parameters", {})))
        if not params_a or not params_b:
            return 0.0, ""
        intersection = params_a & params_b
        union = params_a | params_b
        jaccard = len(intersection) / max(len(union), 1)
        if jaccard > 0.5:
            return jaccard, f"Overlapping parameters ({jaccard:.0%})"
        return jaccard * 0.3, ""

    def _compare_text(self, a: dict[str, Any], b: dict[str, Any]) -> tuple[float, str]:
        text_a = (a.get("description") or a.get("title", "") or "").lower()
        text_b = (b.get("description") or b.get("title", "") or "").lower()
        if len(text_a) < 20 or len(text_b) < 20:
            return 0.0, ""
        ratio = SequenceMatcher(None, text_a, text_b).ratio()
        if ratio > 0.6:
            return ratio, f"Similar description ({ratio:.0%})"
        return ratio * 0.3, ""

    def _normalize_path(self, url: str) -> str:
        path = re.sub(r"https?://[^/]+", "", url)
        path = re.sub(r"/{2,}", "/", path)
        path = re.sub(r"\d+", "{id}", path)
        path = re.sub(r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}", "{uuid}", path)
        return path.strip("/")

    def _age_days(self, finding: dict[str, Any]) -> int | None:
        try:
            from datetime import datetime, timezone
            created = finding.get("created_at") or finding.get("created", "")
            if created:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                return (datetime.now(timezone.utc) - dt).days
        except (ValueError, TypeError, AttributeError):
            pass
        return None
