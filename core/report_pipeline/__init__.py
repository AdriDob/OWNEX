from __future__ import annotations

"""Report Pipeline — finding → evidence → report → manual submit.
Generates complete markdown reports with evidence, ready for manual platform submission.
Top 7 daily, top 15 weekly. Always manual submit with edit/download option.
"""
# ruff: noqa: E402
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from database import db
from database.models import Evidence, Finding, Report, Target, Verdict
from database.models_economic import BountyTier, Program

logger = logging.getLogger("ownex.report_pipeline")
REPORTS_DIR = Path("reports/generated")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
PLATFORM_URLS = {
    "hackerone": "https://hackerone.com/reports/new",
    "bugcrowd": "https://bugcrowd.com/submissions/new",
    "intigriti": "https://app.intigriti.com/submit",
    "yeswehack": "https://www.yeswehack.com/programs",
    "hackenproof": "https://hackenproof.com/reports/new",
    "synack": "https://platform.synack.com/submissions",
    "immunefi": "https://immunefi.com/submit",
    "zerodium": "https://zerodium.com/submit",
}


@dataclass
class ReportCandidate:
    """A finding eligible for reporting."""

    finding_id: int
    title: str
    severity: str
    vulnerability_type: str
    target_name: str
    target_domain: str
    program_name: str
    platform: str
    platform_url: str
    cvss_score: float
    evh: float
    confidence: float
    estimated_reward: float
    score: float
    discovered_at: str
    evidence: dict[str, Any] = field(default_factory=dict)
    endpoints: list[dict[str, Any]] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    steps_to_reproduce: list[str] = field(default_factory=list)
    impact_analysis: str = ""
    remediation: str = ""
    references: list[str] = field(default_factory=list)


@dataclass
class GeneratedReport:
    """A complete report ready for submission."""

    candidate: ReportCandidate
    stage: str  # draft, ready, submitted
    file_path: str
    markdown: str
    json_data: dict[str, Any]
    created_at: str
    edited_at: str | None = None


class ReportPipeline:
    """End-to-end report pipeline: find eligible findings → generate → edit → submit manually."""

    def __init__(self) -> None:
        self._reports: dict[int, GeneratedReport] = {}

    def get_eligible_findings(self) -> list[ReportCandidate]:
        """Find all confirmed findings with evidence (via verdicts), not yet reported."""
        session = db.SessionLocal()
        try:
            # Get findings with confirmed verdicts that have evidence
            findings = (
                session.query(Finding).filter(Finding.status == "confirmed").order_by(Finding.created_at.desc()).all()
            )
            candidates = []
            for f in findings:
                # Check if already has a report
                existing_report = session.query(Report).filter(Report.finding_ids.contains(str(f.id))).first()
                if existing_report:
                    continue
                # Get evidence via verdicts
                verdicts = (
                    session.query(Verdict)
                    .filter(Verdict.hot_path_id == f.id)
                    .filter(Verdict.status == "confirmed")
                    .all()
                )
                if not verdicts:
                    continue
                # Collect evidence
                evidence_data = {}
                for v in verdicts:
                    if v.evidence_links:
                        try:
                            ev_ids = (
                                json.loads(v.evidence_links) if isinstance(v.evidence_links, str) else v.evidence_links
                            )
                            for ev_id in ev_ids:
                                ev = session.query(Evidence).filter(Evidence.id == ev_id).first()
                                if ev:
                                    evidence_data[f"evidence_{ev.id}"] = {
                                        "url": ev.request_url,
                                        "method": ev.request_method,
                                        "status": ev.response_status,
                                        "body_diff": float(ev.body_diff_ratio) if ev.body_diff_ratio else 0,
                                        "curl": ev.curl_command,
                                    }
                        except Exception:
                            pass
                    if v.validation_report:
                        try:
                            vr = json.loads(v.validation_report)
                            evidence_data["passed_rules"] = vr.get("passed_rules", [])
                            evidence_data["failed_rules"] = vr.get("failed_rules", [])
                            evidence_data["details"] = vr.get("details", "")
                        except Exception:
                            pass
                if not evidence_data:
                    continue
                # Get target and program info
                target = session.query(Target).filter(Target.id == f.target_id).first()
                program = session.query(Program).filter(Program.id == target.program_id).first() if target else None
                candidate = ReportCandidate(
                    finding_id=f.id,
                    title=f.title or f"Finding #{f.id}",
                    severity=f.severity or "medium",
                    vulnerability_type=f.vulnerability_type or "unknown",
                    target_name=target.name if target else f"Target #{f.target_id}",
                    target_domain=target.domain if target else "",
                    program_name=program.name if program else "Unknown Program",
                    platform=program.platform if program else "hackerone",
                    platform_url=program.program_url if program else "",
                    cvss_score=f.cvss_score or 0.0,
                    evh=self._calc_evh(f, program),
                    confidence=self._get_confidence(f, verdicts),
                    estimated_reward=self._estimate_reward(f, program),
                    score=f.score or 0.0,
                    discovered_at=f.created_at.isoformat() if f.created_at else "",
                    evidence=evidence_data,
                    endpoints=self._get_endpoints(f, session),
                    screenshots=self._get_screenshots(f),
                    steps_to_reproduce=evidence_data.get("steps", ["See evidence for reproduction steps"]),
                    impact_analysis=evidence_data.get("details", "Impact analysis pending"),
                    remediation=evidence_data.get("remediation", "Remediation guidance pending"),
                    references=evidence_data.get("references", []),
                )
                candidates.append(candidate)
            return candidates
        finally:
            session.close()

    def get_daily_top(self, limit: int = 7) -> list[ReportCandidate]:
        """Top N eligible findings from last 24h, ranked by score * EVH."""
        candidates = self.get_eligible_findings()
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        daily = [c for c in candidates if datetime.fromisoformat(c.discovered_at.replace("Z", "+00:00")) > cutoff]
        daily.sort(key=lambda c: c.score * max(c.evh, 1), reverse=True)
        return daily[:limit]

    def get_weekly_top(self, limit: int = 15) -> list[ReportCandidate]:
        """Top N eligible findings from last 168h."""
        candidates = self.get_eligible_findings()
        cutoff = datetime.now(UTC) - timedelta(hours=168)
        weekly = [c for c in candidates if datetime.fromisoformat(c.discovered_at.replace("Z", "+00:00")) > cutoff]
        weekly.sort(key=lambda c: c.score * max(c.evh, 1), reverse=True)
        return weekly[:limit]

    def generate_report(self, candidate: ReportCandidate) -> GeneratedReport:
        """Generate complete markdown + JSON report for a candidate."""
        now = datetime.now(UTC).isoformat()
        markdown = self._render_markdown(candidate)
        json_data = self._to_json(candidate)
        # Save to file
        filename = f"report_{candidate.finding_id}_{now[:10]}.md"
        filepath = REPORTS_DIR / filename
        filepath.write_text(markdown, encoding="utf-8")
        report = GeneratedReport(
            candidate=candidate,
            stage="draft",
            file_path=str(filepath),
            markdown=markdown,
            json_data=json_data,
            created_at=now,
        )
        self._reports[candidate.finding_id] = report
        return report

    def mark_ready(self, finding_id: int, edited_markdown: str | None = None) -> GeneratedReport | None:
        """Mark report as ready for manual submission (after user edits)."""
        report = self._reports.get(finding_id)
        if not report:
            return None
        if edited_markdown is not None:
            report.markdown = edited_markdown
            report.file_path = str(REPORTS_DIR / f"report_{finding_id}_edited.md")
            Path(report.file_path).write_text(edited_markdown, encoding="utf-8")
            report.edited_at = datetime.now(UTC).isoformat()
        report.stage = "ready"
        return report

    def get_ready_reports(self) -> list[GeneratedReport]:
        """All reports marked ready for manual submission."""
        return [r for r in self._reports.values() if r.stage == "ready"]

    def get_submission_url(self, platform: str, program_url: str = "") -> str:
        """Get the platform submission URL for manual submit button."""
        platform = platform.lower().strip()
        if platform in PLATFORM_URLS:
            return PLATFORM_URLS[platform]
        if program_url:
            return program_url
        return "https://hackerone.com/reports/new"

    # ── Helpers ─────────────────────────────────────────────────────────
    def _calc_evh(self, finding: Finding, program: Program | None) -> float:
        """Expected Value per Hour: (reward * probability) / effort."""
        reward = self._estimate_reward(finding, program)
        prob = finding.confidence or 0.5
        effort = max(finding.estimated_effort_hours or 2.0, 0.5)
        return round((reward * prob) / effort, 2)

    def _estimate_reward(self, finding: Finding, program: Program | None) -> float:
        """Estimate reward based on severity + program tiers."""
        if not program:
            base = {"critical": 5000, "high": 2000, "medium": 500, "low": 100, "info": 50}
            return base.get(finding.severity, 100)
        session = db.SessionLocal()
        try:
            tiers = session.query(BountyTier).filter(BountyTier.program_id == program.id).all()
            if tiers:
                max_tier = max(tiers, key=lambda t: t.max_reward or 0)
                sev_mult = {"critical": 1.0, "high": 0.7, "medium": 0.3, "low": 0.1, "info": 0.05}
                return round((max_tier.max_reward or 0) * sev_mult.get(finding.severity, 0.1), 2)
        finally:
            session.close()
        return 0.0

    def _get_confidence(self, finding: Finding, verdicts: list[Verdict]) -> float:
        """Calculate confidence from verdicts."""
        if not verdicts:
            return finding.confidence or 0.5
        confidences = []
        for v in verdicts:
            try:
                conf = json.loads(v.confidence) if v.confidence else {}
                if isinstance(conf, dict) and "overall" in conf:
                    confidences.append(conf["overall"])
                elif isinstance(conf, (int, float)):
                    confidences.append(conf)
            except Exception:
                pass
        return round(sum(confidences) / len(confidences), 2) if confidences else (finding.confidence or 0.5)

    def _get_endpoints(self, finding: Finding, session) -> list[dict[str, Any]]:
        """Get related endpoints."""
        from database.models import Endpoint

        endpoints = session.query(Endpoint).filter(Endpoint.id == finding.endpoint_id).all()
        return [{"url": e.url, "method": e.method, "params": e.params} for e in endpoints]

    def _get_screenshots(self, finding: Finding) -> list[str]:
        """Get screenshot paths."""
        if finding.screenshots:
            try:
                return json.loads(finding.screenshots)
            except json.JSONDecodeError:
                pass
        return []

    def _render_markdown(self, c: ReportCandidate) -> str:
        """Render complete bug bounty report markdown."""
        sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "🔵"}
        emoji = sev_emoji.get(c.severity.lower(), "⚪")
        lines = [
            f"# {emoji} {c.title}",
            "",
            "---",
            "",
            "## 📋 Executive Summary",
            "",
            f"**Finding ID:** `{c.finding_id}`  ",
            f"**Severity:** {c.severity.upper()}  ",
            f"**Vulnerability Type:** {c.vulnerability_type}  ",
            f"**Target:** {c.target_name} (`{c.target_domain}`)  ",
            f"**Program:** {c.program_name} ({c.platform})  ",
            f"**CVSS Score:** {c.cvss_score:.1f}  ",
            f"**Confidence:** {c.confidence * 100:.0f}%  ",
            f"**Estimated Reward:** ${c.estimated_reward:,.2f}  ",
            f"**EVH (Expected $/hr):** ${c.evh:,.2f}  ",
            f"**Discovered:** {c.discovered_at[:19].replace('T', ' ')} UTC  ",
            f"**Report Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC  ",
            "",
            "---",
            "",
            "## 🎯 Vulnerability Details",
            "",
            "### Description",
            "",
            c.evidence.get("description", "No description provided."),
            "",
            "### Impact Analysis",
            "",
            c.impact_analysis,
            "",
            "### Steps to Reproduce",
            "",
        ]
        for i, step in enumerate(c.steps_to_reproduce, 1):
            lines.append(f"{i}. {step}")
        lines.extend(
            [
                "",
                "### Proof of Concept",
                "",
                "```",
                c.evidence.get("poc", "See evidence attachments"),
                "```",
                "",
            ]
        )
        if c.endpoints:
            lines.extend(["### Affected Endpoints", ""])
            for ep in c.endpoints:
                lines.append(
                    f"- **{ep.get('method', 'GET')}** `{ep.get('url', '')}` — Params: {ep.get('params', '{}')}"
                )
        if c.screenshots:
            lines.extend(["", "### Screenshots", ""])
            for ss in c.screenshots:
                lines.append(f"![Evidence]({ss})")
        lines.extend(
            [
                "",
                "---",
                "",
                "## 🔧 Remediation",
                "",
                c.remediation,
                "",
                "---",
                "",
                "## 📚 References",
                "",
            ]
        )
        for ref in c.references:
            lines.append(f"- {ref}")
        if not c.references:
            lines.append("- No additional references provided.")
        lines.extend(
            [
                "",
                "---",
                "",
                "## 📊 Evidence Package (JSON)",
                "",
                "```json",
                json.dumps(self._to_json(c), indent=2),
                "```",
                "",
                "---",
                "",
                f"*Report generated by ORION Report Pipeline — Finding #{c.finding_id}*",
                f"*Platform: {c.platform} | Program: {c.program_name}*",
                f"*Submit manually at: {self.get_submission_url(c.platform, c.platform_url)}*",
            ]
        )
        return "\n".join(lines)

    def _to_json(self, c: ReportCandidate) -> dict[str, Any]:
        """Full report as JSON for platform API submission."""
        return {
            "finding_id": c.finding_id,
            "title": c.title,
            "severity": c.severity,
            "vulnerability_type": c.vulnerability_type,
            "target": {"name": c.target_name, "domain": c.target_domain},
            "program": {"name": c.program_name, "platform": c.platform, "url": c.platform_url},
            "cvss": c.cvss_score,
            "confidence": c.confidence,
            "estimated_reward": c.estimated_reward,
            "evh": c.evh,
            "score": c.score,
            "discovered_at": c.discovered_at,
            "evidence": c.evidence,
            "endpoints": c.endpoints,
            "screenshots": c.screenshots,
            "steps_to_reproduce": c.steps_to_reproduce,
            "impact_analysis": c.impact_analysis,
            "remediation": c.remediation,
            "references": c.references,
        }


_PIPELINE: ReportPipeline | None = None


def get_pipeline() -> ReportPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = ReportPipeline()
    return _PIPELINE
