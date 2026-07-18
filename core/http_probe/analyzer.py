"""Analyzer — response analysis, evidence extraction, and confidence scoring."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from core.http_probe.probes import HttpResponse, ProbeResult

logger = logging.getLogger("cateye.http_probe.analyzer")

# ── Evidence extraction patterns ──────────────────────────────

SQL_ERROR_RE = re.compile(
    r"(sql\s+syntax|mysql|ORA-\d{5}|PostgreSQL|SQLite|unclosed quotation|"
    r"quoted string not properly terminated|Syntax error.*sql|Microsoft.*ODBC|"
    r"JET Database Engine|mysql_fetch|pg_query|sqlite3)",
    re.IGNORECASE,
)

INTERNAL_HOST_RE = re.compile(
    r"(localhost|127\.0\.0\.1|0\.0\.0\.0|169\.254\.169\.254|10\.\d+\.\d+|172\.16\.\d+|192\.168\.\d+)"
)

CLOUD_METADATA_RE = re.compile(r"(ami-id|instance-id|instance-type|local-ipv4|public-keys|iam-security-credentials)")

XSS_CANARY_RE = re.compile(r"<script>[^<]*</script>")


@dataclass
class AnalysisResult:
    """Structured analysis result with evidence, confidence, and PoC data."""

    hypothesis_id: str = ""
    vulnerability_type: str = ""
    endpoint: str = ""
    method: str = ""
    status: str = "unknown"  # confirmed / rejected / unknown
    confidence: float = 0.0
    evidence_items: list[dict[str, Any]] = field(default_factory=list)
    indicators: list[str] = field(default_factory=list)
    snippets: list[str] = field(default_factory=list)
    probe_results: list[ProbeResult] = field(default_factory=list)

    # PoC data for EvidenceComposer
    poc_data: dict[str, Any] = field(default_factory=dict)
    request_response_pairs: list[dict[str, Any]] = field(default_factory=list)

    # Scoring
    severity: str = "medium"
    cvss_estimate: float = 0.0
    cwe_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "vulnerability_type": self.vulnerability_type,
            "endpoint": self.endpoint,
            "method": self.method,
            "status": self.status,
            "confidence": round(self.confidence, 3),
            "evidence_items": self.evidence_items,
            "indicators": self.indicators,
            "snippets": self.snippets[:10],
            "probe_results_count": len(self.probe_results),
            "poc_data": self.poc_data,
            "request_response_pairs_count": len(self.request_response_pairs),
            "severity": self.severity,
            "cvss_estimate": self.cvss_estimate,
            "cwe_id": self.cwe_id,
        }


class Analyzer:
    """Analyzes probe results, extracts evidence, and computes confidence scores.

    Works with raw HttpResponse objects or with ProbeResult objects from the probes.
    """

    # ── CWE mapping ──────────────────────────────────────────────

    CWE_MAP: dict[str, tuple[str, str]] = {
        "idor": ("CWE-639", "Authorization Bypass Through User-Controlled Key"),
        "ssrf": ("CWE-918", "Server-Side Request Forgery"),
        "xss": ("CWE-79", "Improper Neutralization of Input During Web Page Generation"),
        "sqli": ("CWE-89", "SQL Injection"),
        "auth_bypass": ("CWE-288", "Authentication Bypass Using an Alternate Path or Channel"),
    }

    CVSS_MAP: dict[str, float] = {
        "idor": 7.5,
        "ssrf": 8.6,
        "xss": 6.1,
        "sqli": 9.8,
        "auth_bypass": 8.0,
    }

    SEVERITY_MAP: dict[str, str] = {
        "idor": "high",
        "ssrf": "high",
        "xss": "medium",
        "sqli": "critical",
        "auth_bypass": "high",
    }

    def analyze(
        self,
        probe_results: list[ProbeResult],
        hypothesis_id: str = "",
        vulnerability_type: str = "",
    ) -> AnalysisResult:
        """Analyze a set of probe results and produce a single analysis.

        This is the main entry point for the analyzer.
        """
        result = AnalysisResult(
            hypothesis_id=hypothesis_id,
            vulnerability_type=vulnerability_type,
            probe_results=probe_results,
        )

        if not probe_results:
            result.status = "unknown"
            result.indicators.append("No probe results to analyze")
            return result

        # Extract endpoint from first result
        result.endpoint = probe_results[0].endpoint
        result.method = probe_results[0].method

        # Aggregate evidence from all probe results
        for pr in probe_results:
            result.request_response_pairs.append(self._build_rr_pair(pr))

            if pr.baseline_response and pr.probe_response:
                self._extract_evidence_from_pair(pr, result)

            if pr.evidence_snippets:
                result.snippets.extend(pr.evidence_snippets)
            if pr.indicators:
                result.indicators.extend(pr.indicators)

        # Aggregate confidence
        confirmed = [pr for pr in probe_results if pr.status == "confirmed"]
        unknown = [pr for pr in probe_results if pr.status == "unknown"]

        if confirmed:
            max_conf = max(pr.confidence for pr in confirmed)
            result.confidence = max_conf
            result.status = "confirmed"
        elif unknown:
            max_conf = max(pr.confidence for pr in unknown)
            result.confidence = max_conf * 0.5  # Discount unknowns
            result.status = "unknown"
        else:
            result.confidence = 0.0
            result.status = "rejected"

        # Enrich with CWE, CVSS, severity
        vuln = vulnerability_type or (probe_results[0].vulnerability_type if probe_results else "")
        result.vulnerability_type = vuln
        if vuln in self.CWE_MAP:
            cwe_id, _ = self.CWE_MAP[vuln]
            result.cwe_id = cwe_id
        result.cvss_estimate = self.CVSS_MAP.get(vuln, 5.0)
        result.severity = self.SEVERITY_MAP.get(vuln, "medium")

        # Build PoC data
        result.poc_data = self._build_poc_data(result)

        # Deduplicate evidence
        result.evidence_items = self._deduplicate_evidence(result.evidence_items)
        result.indicators = list(dict.fromkeys(result.indicators))  # preserve order, dedup
        result.snippets = list(dict.fromkeys(result.snippets))[:10]

        logger.info(
            "[%s] Analysis complete: status=%s confidence=%.3f evidence=%d indicators=%d",
            vuln.upper(),
            result.status,
            result.confidence,
            len(result.evidence_items),
            len(result.indicators),
        )

        return result

    def extract_evidence_from_pair(
        self, baseline: HttpResponse, probe: HttpResponse, payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract evidence items from a baseline/probe response pair.

        Used by ProbeEngine for per-request analysis.
        """
        items: list[dict[str, Any]] = []

        # Status code change
        if baseline.status_code != probe.status_code:
            items.append(
                {
                    "type": "status_change",
                    "severity": "medium",
                    "detail": f"Status changed from {baseline.status_code} to {probe.status_code}",
                    "baseline_status": baseline.status_code,
                    "probe_status": probe.status_code,
                }
            )

        # SQL errors
        sql_errors = SQL_ERROR_RE.findall(probe.body)
        baseline_sql = SQL_ERROR_RE.findall(baseline.body)
        new_errors = [e for e in sql_errors if e not in baseline_sql]
        if new_errors:
            items.append(
                {
                    "type": "sql_error",
                    "severity": "critical",
                    "detail": f"SQL error messages found in response: {', '.join(new_errors[:3])}",
                    "errors": new_errors[:5],
                }
            )

        # Internal host leakage
        internal = INTERNAL_HOST_RE.findall(probe.body)
        if internal:
            items.append(
                {
                    "type": "internal_leakage",
                    "severity": "critical",
                    "detail": f"Internal hosts detected in response: {', '.join(internal[:3])}",
                }
            )

        # Cloud metadata
        metadata = CLOUD_METADATA_RE.findall(probe.body)
        if metadata:
            items.append(
                {
                    "type": "cloud_metadata",
                    "severity": "critical",
                    "detail": f"Cloud metadata detected: {', '.join(metadata[:3])}",
                }
            )

        # XSS reflection
        xss_matches = XSS_CANARY_RE.findall(probe.body)
        if xss_matches:
            items.append(
                {
                    "type": "xss_reflection",
                    "severity": "high",
                    "detail": "Unescaped script tag reflected in response",
                }
            )

        # Response body differences (content length)
        if probe.status_code == 200 and baseline.status_code == 200:
            ratio = len(probe.body) / max(len(baseline.body), 1)
            if ratio > 2.0:
                items.append(
                    {
                        "type": "content_increase",
                        "severity": "medium",
                        "detail": f"Response body {ratio:.1f}x larger than baseline (possible data leakage)",
                    }
                )
            elif ratio < 0.3:
                items.append(
                    {
                        "type": "content_decrease",
                        "severity": "low",
                        "detail": f"Response body {ratio:.1f}x smaller than baseline",
                    }
                )

        # Body contains payload reflection
        for _param, val in payload.items():
            if isinstance(val, str) and val in probe.body and val not in baseline.body:
                items.append(
                    {
                        "type": "payload_reflection",
                        "severity": "high",
                        "detail": "Payload value reflected in response body",
                    }
                )

        return items

    def _build_rr_pair(self, pr: ProbeResult) -> dict[str, Any]:
        """Build a request/response pair for PoC generation."""
        pair: dict[str, Any] = {
            "probe_name": pr.probe_name,
            "payload": pr.payload_used,
            "headers": pr.headers_used,
        }
        if pr.baseline_response:
            pair["baseline"] = {
                "url": pr.baseline_response.url,
                "status": pr.baseline_response.status_code,
                "body_length": len(pr.baseline_response.body),
            }
        if pr.probe_response:
            pair["probe"] = {
                "url": pr.probe_response.url,
                "status": pr.probe_response.status_code,
                "body_length": len(pr.probe_response.body),
                "body_snippet": pr.probe_response.body[:500],
            }
        return pair

    def _extract_evidence_from_pair(self, pr: ProbeResult, result: AnalysisResult) -> None:
        """Extract evidence from a probe's baseline/probe pair into the analysis result."""
        if not pr.baseline_response or not pr.probe_response:
            return
        items = self.extract_evidence_from_pair(
            pr.baseline_response,
            pr.probe_response,
            pr.payload_used,
        )
        for item in items:
            item["probe_name"] = pr.probe_name
        result.evidence_items.extend(items)

    def _build_poc_data(self, result: AnalysisResult) -> dict[str, Any]:
        """Build PoC data structure for EvidenceComposer consumption."""
        vuln = result.vulnerability_type
        endpoint = result.endpoint

        best_pair = None
        for pair in result.request_response_pairs:
            probe_info = pair.get("probe", {})
            if probe_info.get("status") in (200, 301, 302):
                best_pair = pair
                break
        if not best_pair and result.request_response_pairs:
            best_pair = result.request_response_pairs[0]

        poc: dict[str, Any] = {
            "method": result.method,
            "endpoint": endpoint,
            "vulnerability_type": vuln,
            "confidence": result.confidence,
            "status": result.status,
        }

        if best_pair:
            poc["best_probe"] = {
                "name": best_pair.get("probe_name", ""),
                "payload": best_pair.get("payload", {}),
                "baseline_status": best_pair.get("baseline", {}).get("status"),
                "probe_status": best_pair.get("probe", {}).get("status"),
            }

        if vuln in self.CWE_MAP:
            cwe_id, cwe_name = self.CWE_MAP[vuln]
            poc["cwe"] = {"id": cwe_id, "name": cwe_name}

        poc["cvss_estimate"] = result.cvss_estimate
        poc["evidence_count"] = len(result.evidence_items)

        return poc

    def _deduplicate_evidence(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate evidence items."""
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for item in items:
            key = f"{item.get('type')}:{item.get('detail', '')[:80]}"
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped
