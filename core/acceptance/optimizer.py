"""Acceptance Intelligence — report optimizer.

Suggests concrete improvements to increase acceptance probability
based on learned patterns from past submissions.
"""

from __future__ import annotations

import logging
from typing import Any

from core.acceptance.analyzer import AcceptanceAnalyzer
from core.acceptance.models import OptimizerSuggestion

logger = logging.getLogger("orion.core.acceptance.optimizer")


class AcceptanceOptimizer:
    """Generates report improvement suggestions based on acceptance patterns."""

    def __init__(self, analyzer: AcceptanceAnalyzer | None = None) -> None:
        self._analyzer = analyzer or AcceptanceAnalyzer()

    def optimize(
        self,
        report: dict[str, Any],
        platform: str = "hackerone",
    ) -> list[OptimizerSuggestion]:
        """Generate improvement suggestions for a report.

        Combines universal best practices with platform-specific patterns.
        """
        _aliases = {"h1": "hackerone", "bc": "bugcrowd", "inti": "intigriti"}
        platform_lower = _aliases.get(platform.lower(), platform.lower())
        profile = self._analyzer.get_profile(platform_lower)

        suggestions: list[OptimizerSuggestion] = []

        # 1. Universal checks
        suggestions.extend(self._check_title(report))
        suggestions.extend(self._check_description(report))
        suggestions.extend(self._check_reproduction(report))
        suggestions.extend(self._check_poc(report))
        suggestions.extend(self._check_evidence(report))
        suggestions.extend(self._check_impact(report))
        suggestions.extend(self._check_classification(report))

        # 2. Platform-specific checks
        suggestions.extend(self._platform_checks(report, platform_lower))

        # 3. Pattern-based suggestions (if we have history)
        if profile and profile.total_submissions >= 5:
            suggestions.extend(self._pattern_based_suggestions(report, profile))

        return suggestions

    def _check_title(self, report: dict[str, Any]) -> list[OptimizerSuggestion]:
        title = report.get("title", "") or ""
        if not title:
            return [
                OptimizerSuggestion(
                    field="title",
                    current="No title",
                    suggestion="Add a title describing the vulnerability and affected endpoint",
                    reason="Title is the first thing triagers see",
                    impact="high",
                    expected_boost=0.10,
                )
            ]
        if len(title.split()) < 4:
            return [
                OptimizerSuggestion(
                    field="title",
                    current=f"'{title}' ({len(title.split())} words)",
                    suggestion="Make the title more descriptive: 'Vulnerability Type in Endpoint allows Impact'",
                    reason="Descriptive titles help triagers route and prioritize",
                    impact="medium",
                    expected_boost=0.05,
                )
            ]
        return []

    def _check_description(self, report: dict[str, Any]) -> list[OptimizerSuggestion]:
        desc = report.get("description", "") or ""
        if not desc:
            return [
                OptimizerSuggestion(
                    field="description",
                    current="Missing",
                    suggestion="Write a technical description explaining the vulnerability mechanism",
                    reason="Triagers need to understand the root cause",
                    impact="high",
                    expected_boost=0.20,
                )
            ]
        suggestions = []
        if len(desc) < 150:
            suggestions.append(
                OptimizerSuggestion(
                    field="description",
                    current=f"{len(desc)} chars",
                    suggestion="Expand the description to 200+ characters with request flow and technical details",
                    reason="Detailed descriptions improve acceptance by 40%+ on average",
                    impact="high",
                    expected_boost=0.15,
                )
            )
        weak_terms = ["maybe", "might", "possibly", "could be", "seems like", "i think"]
        found_weak = [t for t in weak_terms if t in desc.lower()]
        if found_weak:
            suggestions.append(
                OptimizerSuggestion(
                    field="description",
                    current=f"Weak language: {', '.join(found_weak)}",
                    suggestion="Replace speculative language with confident assertions backed by evidence",
                    reason="Triagers penalize reports that sound uncertain",
                    impact="medium",
                    expected_boost=0.08,
                )
            )
        return suggestions

    def _check_reproduction(self, report: dict[str, Any]) -> list[OptimizerSuggestion]:
        steps = report.get("reproduction_steps", []) or report.get("test_instructions", [])
        if not steps:
            return [
                OptimizerSuggestion(
                    field="reproduction_steps",
                    current="Missing",
                    suggestion="Add 3-5 numbered steps to reproduce the vulnerability",
                    reason="Clear reproduction is the #1 factor in report acceptance",
                    impact="high",
                    expected_boost=0.25,
                )
            ]
        if len(steps) < 3:
            return [
                OptimizerSuggestion(
                    field="reproduction_steps",
                    current=f"{len(steps)} steps",
                    suggestion="Add more detail — aim for at least 3 specific, numbered steps",
                    reason="More steps = easier reproduction = higher acceptance",
                    impact="high",
                    expected_boost=0.10,
                )
            ]
        avg_len = sum(len(s) for s in steps) / max(len(steps), 1)
        if avg_len < 30:
            return [
                OptimizerSuggestion(
                    field="reproduction_steps",
                    current=f"Avg {avg_len:.0f} chars/step",
                    suggestion="Make each step more specific: include URLs, parameters, and expected values",
                    reason="Vague steps are the most common rejection reason",
                    impact="medium",
                    expected_boost=0.08,
                )
            ]
        return []

    def _check_poc(self, report: dict[str, Any]) -> list[OptimizerSuggestion]:
        poc = report.get("poc")
        has_curl = bool(poc.get("curl", "")) if isinstance(poc, dict) else bool(poc)
        has_python = bool(report.get("python_script"))
        if not has_curl and not has_python:
            return [
                OptimizerSuggestion(
                    field="poc",
                    current="Missing",
                    suggestion="Include at least a curl command as proof of concept",
                    reason="Working PoCs dramatically increase acceptance probability",
                    impact="high",
                    expected_boost=0.20,
                )
            ]
        if not has_curl:
            return [
                OptimizerSuggestion(
                    field="poc",
                    current="Python only",
                    suggestion="Add a curl command — it's the universal PoC format",
                    reason="Triagers prefer curl because it's trivially reproducible",
                    impact="medium",
                    expected_boost=0.08,
                )
            ]
        return []

    def _check_evidence(self, report: dict[str, Any]) -> list[OptimizerSuggestion]:
        evidence = report.get("evidence", [])
        if not evidence:
            return [
                OptimizerSuggestion(
                    field="evidence",
                    current="None",
                    suggestion="Attach at least one piece of evidence (screenshot, HAR, response data)",
                    reason="Evidence makes your report verifiable and credible",
                    impact="high",
                    expected_boost=0.15,
                )
            ]
        if len(evidence) == 1:
            return [
                OptimizerSuggestion(
                    field="evidence",
                    current="1 item",
                    suggestion="Add more evidence: include request/response pairs alongside screenshots",
                    reason="Multiple evidence types help triagers understand the full scope",
                    impact="low",
                    expected_boost=0.05,
                )
            ]
        return []

    def _check_impact(self, report: dict[str, Any]) -> list[OptimizerSuggestion]:
        impact = report.get("impact", "") or report.get("business_impact", "")
        if not impact:
            return [
                OptimizerSuggestion(
                    field="impact",
                    current="Missing",
                    suggestion="Explain the business impact: what data is at risk, what an attacker can do",
                    reason="Business impact drives severity and payout decisions",
                    impact="high",
                    expected_boost=0.15,
                )
            ]
        if len(impact) < 50:
            return [
                OptimizerSuggestion(
                    field="impact",
                    current=f"{len(impact)} chars",
                    suggestion="Elaborate with specific scenarios of what an attacker could achieve",
                    reason="Concrete impact scenarios are more convincing",
                    impact="medium",
                    expected_boost=0.08,
                )
            ]
        return []

    def _check_classification(self, report: dict[str, Any]) -> list[OptimizerSuggestion]:
        suggestions = []
        if not report.get("vulnerability_type"):
            suggestions.append(
                OptimizerSuggestion(
                    field="vulnerability_type",
                    current="Missing",
                    suggestion="Specify the vulnerability type (IDOR, SSRF, XSS, SQLi, etc.)",
                    reason="Helps triagers route reports correctly",
                    impact="medium",
                    expected_boost=0.08,
                )
            )
        if not report.get("severity"):
            suggestions.append(
                OptimizerSuggestion(
                    field="severity",
                    current="Missing",
                    suggestion="Assign a severity level based on CVSS scoring",
                    reason="Shows professional methodology",
                    impact="medium",
                    expected_boost=0.05,
                )
            )
        cvss = float(report.get("cvss_score", 0) or 0)
        if cvss <= 0:
            suggestions.append(
                OptimizerSuggestion(
                    field="cvss_score",
                    current="Not scored",
                    suggestion="Include a CVSS v3.1 score and vector string",
                    reason="Standardized scoring helps triagers assess priority",
                    impact="medium",
                    expected_boost=0.05,
                )
            )
        if not report.get("cwe_id") and not report.get("cwe"):
            suggestions.append(
                OptimizerSuggestion(
                    field="cwe_id",
                    current="Missing",
                    suggestion="Include the CWE identifier for the vulnerability class",
                    reason="Standard classification aids automated processing",
                    impact="low",
                    expected_boost=0.03,
                )
            )
        return suggestions

    def _platform_checks(self, report: dict[str, Any], platform: str) -> list[OptimizerSuggestion]:
        suggestions = []
        if platform in ("hackerone", "h1") and not report.get("asset_type") and not report.get("asset_type_name"):
            suggestions.append(
                OptimizerSuggestion(
                    field="asset_type",
                    current="Missing",
                    suggestion="Specify the asset type (URL, API, Mobile, Source Code)",
                    reason="HackerOne requires asset type for proper report routing",
                    impact="medium",
                    expected_boost=0.05,
                )
            )
        if platform in ("intigriti", "inti"):
            tags = report.get("tags", [])
            if not tags:
                suggestions.append(
                    OptimizerSuggestion(
                        field="tags",
                        current="Missing",
                        suggestion="Add relevant tags for classification (e.g., ['xss', 'stored'])",
                        reason="Intigriti uses tags for automated routing",
                        impact="medium",
                        expected_boost=0.05,
                    )
                )
        return suggestions

    def _pattern_based_suggestions(self, report: dict[str, Any], profile: Any) -> list[OptimizerSuggestion]:
        """Generate suggestions based on learned acceptance patterns."""
        suggestions: list[OptimizerSuggestion] = []

        vuln_type = (report.get("vulnerability_type") or "").lower()
        severity = (report.get("severity") or "").lower()

        # Suggest best vulnerability type to report
        if profile.by_type:
            best_type = max(
                ((vt, s["rate"]) for vt, s in profile.by_type.items() if s["total"] >= 3),
                key=lambda x: x[1],
                default=None,
            )
            if best_type and vuln_type and vuln_type != best_type[0]:
                rate = best_type[1]
                current_type_rate = profile.by_type.get(vuln_type, {}).get("rate", 0)
                if rate > current_type_rate + 0.1:  # Meaningful difference
                    suggestions.append(
                        OptimizerSuggestion(
                            field="vulnerability_type",
                            current=f"{vuln_type} ({current_type_rate:.0%} acceptance)",
                            suggestion=f"Reports of type '{best_type[0]}' have {rate:.0%} acceptance on {profile.platform} vs {current_type_rate:.0%} for '{vuln_type}'",
                            reason="Historical data shows different acceptance rates by vulnerability type",
                            impact="medium",
                            expected_boost=rate - current_type_rate,
                        )
                    )

        # Suggest best severity for this type
        if vuln_type in profile.by_type:
            type_stats = profile.by_type[vuln_type]
            if type_stats["total"] >= 5 and profile.by_severity:
                best_sev = max(
                    ((s, st["rate"]) for s, st in profile.by_severity.items() if st["total"] >= 2),
                    key=lambda x: x[1],
                    default=None,
                )
                if best_sev and severity and severity != best_sev[0]:
                    suggestions.append(
                        OptimizerSuggestion(
                            field="severity",
                            current=severity,
                            suggestion=f"'{best_sev[0]}' severity reports have {best_sev[1]:.0%} acceptance on {profile.platform}",
                            reason="Severity level affects acceptance probability on this platform",
                            impact="low",
                            expected_boost=best_sev[1] - profile.by_severity.get(severity, {}).get("rate", 0),
                        )
                    )

        return suggestions
