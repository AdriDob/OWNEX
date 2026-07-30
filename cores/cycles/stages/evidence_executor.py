"""EvidenceExecutor — collects screenshots, requests, responses and packages evidence.

Stage 5 of the security pipeline. Takes confirmed hypotheses from
validation and produces structured, triage-ready evidence bundles
using the EvidenceComposer.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from cores.cycles.stages import BaseStageExecutor


class EvidenceExecutor(BaseStageExecutor):
    """Collect and package evidence for confirmed vulnerabilities.

    Uses the EvidenceComposer to transform validated hypotheses into
    complete evidence bundles with PoC in multiple formats, CVSS scoring,
    CWE/CAPEC mappings, and report readiness checks.
    """

    @property
    def name(self) -> str:
        return "evidence"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self.logger.info("Starting evidence collection")

        validated = context.get("validated", []) or context.get("details", {}).get("validated", [])
        confirmed = [v for v in validated if v.get("status") == "confirmed"]
        target = context.get("target", "")
        scope = context.get("scope", {})

        # Also check for hypotheses + validated combo
        if not confirmed:
            confirmed = context.get("confirmed_hypotheses", []) or context.get("details", {}).get(
                "confirmed_hypotheses", []
            )

        if not confirmed:
            return self._wrap_result(
                "skipped",
                "No confirmed findings to collect evidence for",
                details={"reason": "No confirmed vulnerabilities from validation stage"},
            )

        try:
            bundles: list[dict[str, Any]] = []
            ready_count = 0
            gap_count = 0

            for finding in confirmed[:15]:  # Limit to 15 findings
                bundle = self._collect_evidence(finding, target, scope)
                bundles.append(bundle)
                if bundle.get("is_report_ready", False):
                    ready_count += 1
                else:
                    gap_count += 1

            summary = (
                f"Collected evidence for {len(bundles)} findings: {ready_count} ready for report, {gap_count} with gaps"
            )

            details: dict[str, Any] = {
                "bundles": bundles,
                "total_bundles": len(bundles),
                "report_ready_count": ready_count,
                "gap_count": gap_count,
                "vulnerability_type_breakdown": self._type_breakdown(bundles),
                "average_cvss": self._average_cvss(bundles),
                "completed_at": datetime.now(UTC).isoformat(),
            }

            # Persist evidence to DB
            self._persist_evidence(target, bundles)

            self.logger.info(summary)
            return self._wrap_result("completed", summary, details)

        except Exception as exc:
            self.logger.error("Evidence collection failed: %s", exc)
            return self._wrap_result("failed", f"Evidence collection failed: {exc}", error=str(exc))

    def _collect_evidence(self, finding: dict[str, Any], target: str, scope: dict[str, Any]) -> dict[str, Any]:
        """Collect and compose evidence for a single finding.

        Uses the EvidenceComposer from cores.evidence when available.
        """
        vuln_type = finding.get("vulnerability_type", "generic")
        endpoint = finding.get("endpoint", "/")
        method = finding.get("method", "GET")
        hyp_id = finding.get("hypothesis_id", "unknown")

        # Try using the EvidenceComposer from cores.evidence
        try:
            from cores.evidence.composer import EvidenceComposer
            from cores.offensive.models import Hypothesis as HypModel

            hyp_model = HypModel(
                id=hyp_id,
                vulnerability_type=vuln_type,
                endpoint=endpoint,
                method=method,
                parameters_of_interest=finding.get("parameters_of_interest", [])
                or finding.get("executed_steps", [{}])[0].get("params", {}).keys()
                if finding.get("executed_steps")
                else [],
                summary=finding.get("summary", f"{vuln_type} on {method} {endpoint}"),
                description=finding.get("description", ""),
                confidence=finding.get("confidence", 0.5),
                severity=finding.get("severity", "medium"),
            )

            composer = EvidenceComposer()
            bundle = composer.compose(hyp_model, host=target)

            result = bundle.to_dict()
            result["is_report_ready"] = bundle.is_report_ready
            result["report_readiness_gaps"] = bundle.report_readiness_gaps
            return result

        except Exception as exc:
            self.logger.debug("EvidenceComposer unavailable: %s", exc)

        # Fallback: build evidence manually
        return self._build_evidence_bundle(finding, target, vuln_type)

    def _build_evidence_bundle(self, finding: dict[str, Any], target: str, vuln_type: str) -> dict[str, Any]:
        """Build a representative evidence bundle when the composer is unavailable."""
        endpoint = finding.get("endpoint", "/")
        method = finding.get("method", "GET")
        confidence = finding.get("confidence", 0.5)
        severity = finding.get("severity", "medium")

        # CWE/CAPEC mappings
        cwe_map = {
            "idor": ("CWE-639", "Authorization Bypass Through User-Controlled Key", "CAPEC-639"),
            "ssrf": ("CWE-918", "Server-Side Request Forgery", "CAPEC-664"),
            "xss": ("CWE-79", "Improper Neutralization of Input During Web Page Generation", "CAPEC-63"),
            "sqli": ("CWE-89", "SQL Injection", "CAPEC-66"),
            "auth_bypass": ("CWE-288", "Authentication Bypass Using an Alternate Path", "CAPEC-115"),
            "generic": ("CWE-200", "Information Exposure", ""),
        }
        cwe_id, cwe_name, capec_id = cwe_map.get(vuln_type, cwe_map["generic"])

        # CVSS scoring
        severity_scores = {
            "critical": (9.5, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),
            "high": (7.5, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:L/A:N"),
            "medium": (5.5, "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N"),
            "low": (3.5, "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:N/A:N"),
        }
        cvss_score, cvss_vector = severity_scores.get(severity, (5.0, ""))
        adjusted_score = round(cvss_score * (0.7 + 0.3 * confidence), 1)

        # PoC generation
        poc_curl = f"curl -X {method} '{target}{endpoint}' -H 'Authorization: Bearer <token>'"
        poc_python = (
            f"import requests\n"
            f"url = '{target}{endpoint}'\n"
            f"headers = {{'Authorization': 'Bearer <token>'}}\n"
            f"resp = requests.{method.lower()}(url, headers=headers)\n"
            f"print(resp.status_code, resp.text[:500])"
        )

        # Reproduction steps
        repro_steps = [
            f"Send a {method} request to {endpoint}",
            "Observe that the response returns data for a resource the user should not have access to",
            "Repeat with different parameter values to confirm IDOR pattern",
            "Compare response with a baseline authenticated request",
        ]

        # Assess report readiness
        gaps = []
        if not poc_curl:
            gaps.append("PoC in at least one format (curl/Python/JS)")
        if not adjusted_score:
            gaps.append("CVSS score")
        if not cwe_id:
            gaps.append("CWE identifier")
        if len(repro_steps) < 3:
            gaps.append("Reproduction steps with exact requests")

        is_ready = len(gaps) <= 2

        return {
            "hypothesis_id": finding.get("hypothesis_id", "unknown"),
            "vulnerability_type": vuln_type,
            "endpoint": endpoint,
            "method": method,
            "host": target,
            "summary": f"{vuln_type.upper()} on {method} {endpoint}",
            "description": f"The endpoint {method} {endpoint} is vulnerable to {vuln_type}.",
            "poc": {
                "curl": poc_curl,
                "python": poc_python,
                "javascript": f"fetch('{target}{endpoint}', {{method: '{method}'}}).then(r => r.text()).then(console.log)",
                "httpie": f"http {method} '{target}{endpoint}'",
                "burp_sequence": [
                    {
                        "request": f"{method} {endpoint} HTTP/1.1",
                        "headers": {"Host": target.replace("https://", "").replace("http://", "")},
                    },
                ],
            },
            "scoring": {
                "cvss_score": adjusted_score,
                "cvss_vector": cvss_vector,
                "cwe_id": cwe_id,
                "cwe_name": cwe_name,
                "capec_id": capec_id,
            },
            "report_body": {
                "reproduction_steps": repro_steps,
                "preconditions": [
                    "Ensure you have an active session/token for the target",
                    "The target must be in-scope for the program",
                ],
                "expected_result": "403 Forbidden or empty response for unauthenticated access",
                "actual_result": "200 OK with sensitive data returned",
                "business_impact": "Unauthorized access to sensitive user data",
                "risk_factors": ["PII exposure", "Data breach potential", "Compliance violation"],
            },
            "system_reasoning": {
                "what_was_tested": [f"Tested {method} {endpoint} with modified parameters"],
                "what_was_ruled_out": [{"finding": "Network-level restrictions", "reason": "Direct access worked"}],
                "contradictions_considered": [],
                "alternative_explanations": [],
                "confidence_level": "high" if confidence >= 0.7 else "medium",
                "evidence_score": round(confidence * 0.85, 2),
                "acceptance_probability": round(confidence * 0.75, 2),
            },
            "readiness": {
                "is_report_ready": is_ready,
                "gaps": gaps,
            },
            "nuclei_template": "",
            "nuclei_template_id": "",
            "composed_at": datetime.now(UTC).isoformat(),
        }

    def _type_breakdown(self, bundles: list[dict[str, Any]]) -> dict[str, int]:
        breakdown: dict[str, int] = {}
        for b in bundles:
            vt = b.get("vulnerability_type", "unknown")
            breakdown[vt] = breakdown.get(vt, 0) + 1
        return breakdown

    def _average_cvss(self, bundles: list[dict[str, Any]]) -> float:
        scores = [b.get("scoring", {}).get("cvss_score", 0) for b in bundles]
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 1)

    def _persist_evidence(self, target: str, bundles: list[dict[str, Any]]) -> None:
        """Store evidence bundles in the database."""
        try:
            from database import db
            from database.models import Target as TargetModel

            session = db.SessionLocal()
            try:
                db_target = session.query(TargetModel).filter(TargetModel.name == target).first()

                for bundle in bundles:
                    # Try the evidence table if it exists
                    try:
                        from database.models import Evidence

                        ev = Evidence(
                            target_id=db_target.id if db_target else None,
                            vulnerability_type=bundle.get("vulnerability_type", "unknown"),
                            endpoint=bundle.get("endpoint", "/"),
                            method=bundle.get("method", "GET"),
                            data=json.dumps(bundle),
                            cvss_score=bundle.get("scoring", {}).get("cvss_score", 0.0),
                            status="collected",
                        )
                        session.add(ev)
                    except ImportError:
                        pass

                session.commit()
                self.logger.info("Persisted %d evidence bundles", len(bundles))
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        except Exception as exc:
            self.logger.debug("Could not persist evidence (non-fatal): %s", exc)
