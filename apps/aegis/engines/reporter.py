"""Reporter Engine — generates professional security reports."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from apps.aegis.models import AegisTarget, ScanReport, ScanResult, VulnFinding
from core.database.manager import get_db_manager

logger = logging.getLogger("orion.aegis.engines.reporter")


class ReporterEngine:
    """Generates security reports in markdown, HTML, or PDF format."""

    async def generate(self, target_id: int, format: str = "markdown") -> dict[str, Any]:
        """Generate a security report for a target."""
        db = get_db_manager().get_session("aegis")
        try:
            target = db.query(AegisTarget).filter(AegisTarget.id == target_id).first()
            if not target:
                return {"error": "target not found"}

            findings = db.query(VulnFinding).filter(VulnFinding.target_id == target_id).all()
            scans = db.query(ScanResult).filter(ScanResult.target_id == target_id).all()

            sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
            for f in findings:
                sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1

            if format == "html":
                content = self._render_html(target, findings, scans, sev_counts)
            else:
                content = self._render_markdown(target, findings, scans, sev_counts)

            report = ScanReport(
                target_id=target_id,
                title=f"Security Report — {target.name}",
                format=format,
                content=content,
                findings_summary=f"{len(findings)} findings ({sev_counts['critical']} critical, {sev_counts['high']} high)",
                severity_counts=str(sev_counts),
            )
            db.add(report)
            db.commit()
            db.refresh(report)

            return {
                "id": report.id,
                "title": report.title,
                "format": format,
                "findings_count": len(findings),
                "severity_counts": sev_counts,
            }
        except Exception as exc:
            db.rollback()
            logger.error("Report generation failed: %s", exc)
            return {"error": str(exc)}
        finally:
            db.close()

    def _render_markdown(self, target: AegisTarget, findings: list, scans: list, sev_counts: dict) -> str:
        lines = [
            f"# Security Report: {target.name}",
            f"**Target**: {target.domain or target.name}",
            f"**Date**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Status**: {target.status}",
            "",
            "## Summary",
            f"- Total findings: {len(findings)}",
            f"- Critical: {sev_counts['critical']}",
            f"- High: {sev_counts['high']}",
            f"- Medium: {sev_counts['medium']}",
            f"- Low: {sev_counts['low']}",
            f"- Scans executed: {len(scans)}",
            "",
            "## Findings",
        ]
        for f in findings:
            lines.extend(
                [
                    f"### {f.title}",
                    f"- **Severity**: {f.severity}",
                    f"- **Status**: {f.status}",
                    f"- **CVE**: {f.cve or 'N/A'}",
                    f"- **CWE**: {f.cwe or 'N/A'}",
                    f"- **CVSS**: {f.cvss or 'N/A'}",
                    "",
                    f"{f.description or ''}",
                    "",
                    f"**Impact**: {f.impact or 'N/A'}",
                    "",
                    f"**Remediation**: {f.remediation or 'N/A'}",
                    "",
                    f"**PoC**: {f.poc or 'N/A'}",
                    "",
                    "---",
                    "",
                ]
            )
        return "\n".join(lines)

    def _render_html(self, target: AegisTarget, findings: list, scans: list, sev_counts: dict) -> str:
        md = self._render_markdown(target, findings, scans, sev_counts)
        import markdown as md_lib

        return md_lib.markdown(md, extensions=["extra", "codehilite"])
