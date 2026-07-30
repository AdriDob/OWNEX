"""ReportExecutor — generates structured bug bounty / vulnerability reports.

Stage 6 of the security pipeline. Takes evidence bundles from the
evidence stage and produces formatted reports ready for triage submission.
Includes quality checks before finalisation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cores.cycles.stages import BaseStageExecutor


class ReportExecutor(BaseStageExecutor):
    """Generate structured vulnerability reports from evidence bundles.

    Produces reports in multiple formats (JSON, Markdown, plain text)
    with quality gates ensuring completeness before marking as ready.
    """

    @property
    def name(self) -> str:
        return "report"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self.logger.info("Starting report generation")

        bundles = context.get("bundles", []) or context.get("details", {}).get("bundles", [])
        target = context.get("target", "")
        scope = context.get("scope", {})

        # Fall back to individual bundle if no bundles list
        if not bundles:
            context.get("ready", [])
            context.get("gaps", [])
            bundle_data = context.get("details", {}).get("bundles", [])

            # Single bundle scenario
            single = {
                k: context.get(k)
                for k in ("hypothesis_id", "vulnerability_type", "endpoint",
                          "method", "summary", "poc", "scoring", "report_body")
                if context.get(k)
            }
            if single:
                bundles = [single]
            elif bundle_data:
                bundles = bundle_data

        if not bundles:
            return self._wrap_result(
                "skipped",
                "No evidence bundles available for report generation",
                details={"reason": "Empty evidence bundles from previous stage"},
            )

        try:
            reports: list[dict[str, Any]] = []
            quality_passed = 0
            quality_failed = 0

            for bundle in bundles:
                report = self._generate_report(bundle, target, scope)
                reports.append(report)
                if report.get("quality_check", {}).get("passed", False):
                    quality_passed += 1
                else:
                    quality_failed += 1

            # Generate a comprehensive summary report
            summary_report = self._generate_summary_report(reports, target)

            summary = (
                f"Generated {len(reports)} reports: "
                f"{quality_passed} passed quality check, "
                f"{quality_failed} has quality gaps"
            )

            details: dict[str, Any] = {
                "reports": reports,
                "total_reports": len(reports),
                "quality_passed": quality_passed,
                "quality_failed": quality_failed,
                "summary_report": summary_report,
                "formats": ["json", "markdown"],
                "completed_at": datetime.now(UTC).isoformat(),
            }

            # Persist reports to DB
            self._persist_reports(target, reports)

            self.logger.info(summary)
            return self._wrap_result("completed", summary, details)

        except Exception as exc:
            self.logger.error("Report generation failed: %s", exc)
            return self._wrap_result("failed", f"Report generation failed: {exc}", error=str(exc))

    def _generate_report(
        self, bundle: dict[str, Any], target: str, scope: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a structured report from an evidence bundle."""
        vuln_type = bundle.get("vulnerability_type", "generic")
        endpoint = bundle.get("endpoint", "/")
        method = bundle.get("method", "GET")
        host = bundle.get("host", target)

        # Extract scoring if nested
        scoring = bundle.get("scoring", {})
        if not scoring:
            scoring = {
                "cvss_score": bundle.get("cvss_score", 5.0),
                "cvss_vector": bundle.get("cvss_vector", ""),
                "cwe_id": bundle.get("cwe_id", "CWE-200"),
                "cwe_name": bundle.get("cwe_name", "Information Exposure"),
                "capec_id": bundle.get("capec_id", ""),
            }

        # Extract report body
        report_body = bundle.get("report_body", {})
        poc = bundle.get("poc", {})

        # Build markdown report
        md_report = self._build_markdown_report(
            vuln_type=vuln_type,
            endpoint=endpoint,
            method=method,
            host=host,
            summary=bundle.get("summary", f"{vuln_type} on {method} {endpoint}"),
            description=bundle.get("description", ""),
            scoring=scoring,
            report_body=report_body,
            poc=poc,
        )

        # Build JSON report
        json_report = self._build_json_report(
            vuln_type=vuln_type,
            endpoint=endpoint,
            method=method,
            host=host,
            bundle=bundle,
            scoring=scoring,
            report_body=report_body,
            poc=poc,
        )

        # Quality check
        quality = self._quality_check(md_report, json_report)

        return {
            "vulnerability_type": vuln_type,
            "endpoint": endpoint,
            "method": method,
            "host": host,
            "report_markdown": md_report,
            "report_json": json_report,
            "report_text": self._plain_text_summary(vuln_type, endpoint, method, scoring, report_body),
            "quality_check": quality,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def _build_markdown_report(
        self,
        vuln_type: str,
        endpoint: str,
        method: str,
        host: str,
        summary: str,
        description: str,
        scoring: dict[str, Any],
        report_body: dict[str, Any],
        poc: dict[str, Any],
    ) -> str:
        """Generate a markdown-format bug bounty report."""
        lines = [
            f"# Vulnerability Report: {summary}",
            "",
            f"**Target:** `{host}`",
            f"**Endpoint:** `{method} {endpoint}`",
            f"**Type:** {vuln_type.upper()}",
            "",
            "---",
            "",
            "## Summary",
            "",
            description or summary,
            "",
            "---",
            "",
            "## CVSS Score",
            "",
            f"- **Score:** {scoring.get('cvss_score', 'N/A')}",
            f"- **Vector:** `{scoring.get('cvss_vector', 'N/A')}`",
            f"- **CWE:** {scoring.get('cwe_id', 'N/A')} — {scoring.get('cwe_name', '')}",
            f"- **CAPEC:** {scoring.get('capec_id', 'N/A')}",
            "",
            "---",
            "",
            "## Steps to Reproduce",
            "",
        ]
        for i, step in enumerate(report_body.get("reproduction_steps", []), 1):
            lines.append(f"{i}. {step}")

        lines.extend([
            "",
            "### Preconditions",
            "",
        ])
        for pre in report_body.get("preconditions", []):
            lines.append(f"- {pre}")

        lines.extend([
            "",
            "### Expected Result",
            "",
            report_body.get("expected_result", "N/A"),
            "",
            "### Actual Result",
            "",
            report_body.get("actual_result", "N/A"),
            "",
            "---",
            "",
            "## Business Impact",
            "",
            report_body.get("business_impact", "N/A"),
            "",
            "---",
            "",
            "## Proof of Concept",
            "",
        ])

        if poc.get("curl"):
            lines.extend(["### curl", "", "```bash", poc["curl"], "```", ""])
        if poc.get("python"):
            lines.extend(["### Python", "", "```python", poc["python"], "```", ""])
        if poc.get("javascript"):
            lines.extend(["### JavaScript (fetch)", "", "```javascript", poc["javascript"], "```", ""])

        lines.extend([
            "",
            "---",
            "",
            "## Risk Factors",
            "",
        ])
        for risk in report_body.get("risk_factors", []):
            lines.append(f"- {risk}")

        lines.extend([
            "",
            "---",
            "",
            "*Report generated by Rastro Security Pipeline*",
            f"*Generated at: {datetime.now(UTC).isoformat()}*",
        ])

        return "\n".join(lines)

    def _build_json_report(
        self,
        vuln_type: str,
        endpoint: str,
        method: str,
        host: str,
        bundle: dict[str, Any],
        scoring: dict[str, Any],
        report_body: dict[str, Any],
        poc: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a JSON-format report suitable for API submission."""
        return {
            "vulnerability": {
                "type": vuln_type,
                "endpoint": endpoint,
                "method": method,
                "host": host,
                "summary": bundle.get("summary", ""),
                "description": bundle.get("description", ""),
            },
            "scoring": scoring,
            "evidence": {
                "poc": poc,
                "reproduction_steps": report_body.get("reproduction_steps", []),
                "preconditions": report_body.get("preconditions", []),
                "expected_result": report_body.get("expected_result", ""),
                "actual_result": report_body.get("actual_result", ""),
                "business_impact": report_body.get("business_impact", ""),
                "risk_factors": report_body.get("risk_factors", []),
            },
            "metadata": {
                "generated_at": datetime.now(UTC).isoformat(),
                "pipeline_version": "1.0",
                "source": "rastro_security_cycle",
            },
        }

    def _plain_text_summary(
        self,
        vuln_type: str,
        endpoint: str,
        method: str,
        scoring: dict[str, Any],
        report_body: dict[str, Any],
    ) -> str:
        """Generate a plain-text one-liner summary for logging."""
        return (
            f"[{vuln_type.upper()}] {method} {endpoint} "
            f"| CVSS: {scoring.get('cvss_score', '?')} "
            f"| Impact: {report_body.get('business_impact', 'N/A')[:80]}"
        )

    def _quality_check(self, md_report: str, json_report: dict[str, Any]) -> dict[str, Any]:
        """Run quality checks on the generated report."""
        gaps: list[str] = []

        # Markdown checks
        if len(md_report) < 200:
            gaps.append("Report body too short")
        if "## Summary" not in md_report:
            gaps.append("Missing summary section")
        if "## Steps to Reproduce" not in md_report:
            gaps.append("Missing reproduction steps")
        if "## Proof of Concept" not in md_report:
            gaps.append("Missing PoC section")

        # JSON checks
        if not json_report.get("scoring", {}).get("cvss_score"):
            gaps.append("Missing CVSS score")
        if not json_report.get("scoring", {}).get("cwe_id"):
            gaps.append("Missing CWE identifier")
        if not json_report.get("evidence", {}).get("reproduction_steps"):
            gaps.append("No reproduction steps in evidence")

        passed = len(gaps) <= 1  # Allow 1 gap max
        return {"passed": passed, "gaps": gaps, "gap_count": len(gaps)}

    def _generate_summary_report(
        self, reports: list[dict[str, Any]], target: str
    ) -> dict[str, Any]:
        """Generate a summary report covering all findings."""
        vuln_types: dict[str, int] = {}
        total_cvss = 0.0
        total_quality = 0

        for r in reports:
            vt = r.get("vulnerability_type", "unknown")
            vuln_types[vt] = vuln_types.get(vt, 0) + 1
            scoring = r.get("report_json", {}).get("scoring", {})
            total_cvss += scoring.get("cvss_score", 0) or 0
            if r.get("quality_check", {}).get("passed"):
                total_quality += 1

        return {
            "target": target,
            "total_findings": len(reports),
            "vulnerability_breakdown": vuln_types,
            "average_cvss": round(total_cvss / max(len(reports), 1), 1),
            "quality_pass_rate": f"{round(total_quality / max(len(reports), 1) * 100, 1)}%",
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def _persist_reports(self, target: str, reports: list[dict[str, Any]]) -> None:
        """Save generated reports to the database."""
        try:
            from database import db
            from database.models import Report
            from database.models import Target as TargetModel

            session = db.SessionLocal()
            try:
                (
                    session.query(TargetModel)
                    .filter(TargetModel.name == target)
                    .first()
                )

                for report in reports:
                    vuln_type = report.get("vulnerability_type", "generic")
                    quality = report.get("quality_check", {})
                    report_json = report.get("report_json", {})

                    db_report = Report(
                        target=target,
                        vulnerability=vuln_type,
                        severity=report_json.get("scoring", {}).get("cvss_score", 5.0) >= 7.0 and "high" or "medium",
                        status="draft" if quality.get("passed", False) else "needs_review",
                        evidence_count=1,
                        notes=report.get("report_text", "")[:500],
                    )
                    session.add(db_report)

                session.commit()
                self.logger.info("Persisted %d reports for target %s", len(reports), target)
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        except Exception as exc:
            self.logger.debug("Could not persist reports (non-fatal): %s", exc)
