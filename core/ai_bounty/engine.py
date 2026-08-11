"""AI Bounty Engine — orchestrates the full auto-hunting pipeline."""

from __future__ import annotations

import logging
import time
from typing import Any

from core.ai_bounty.monitor import AIBountyChallenge, AIBountyMonitor
from core.ai_bounty.publisher import AIBountyEventPublisher

_AI_SCAN_TARGETS: dict[str, list[str]] = {
    "imbue": [
        "https://imbue.com",
        "https://api.imbue.com",
    ],
    "anthropic": [
        "https://anthropic.com",
        "https://api.anthropic.com",
    ],
    "openai": [
        "https://openai.com",
        "https://api.openai.com",
        "https://chatgpt.com",
    ],
    "google_ai": [
        "https://ai.google",
        "https://makersuite.google.com",
        "https://generativelanguage.googleapis.com",
    ],
}

logger = logging.getLogger("orion.ai_bounty.engine")

SCORE_WEIGHTS = {
    "expected_payout": 0.3,
    "confidence": 0.25,
    "effort_hours": -0.2,
    "tool_coverage": 0.15,
    "freshness": 0.1,
}


class AIBountyEngine:
    """Orchestrates the AI bounty auto-hunting pipeline.

    Flow:
    1. Discover new challenges (from monitor or manual input)
    2. Scan targets using existing tools
    3. Compile findings into structured reports
    4. Track submission state
    """

    def __init__(self, monitor: AIBountyMonitor | None = None) -> None:
        self._monitor = monitor or AIBountyMonitor()
        self._publisher = AIBountyEventPublisher()
        self._scan_history: dict[str, dict[str, Any]] = {}
        self._report_queue: list[dict[str, Any]] = []

    @property
    def monitor(self) -> AIBountyMonitor:
        return self._monitor

    def discover_all(self) -> list[AIBountyChallenge]:
        """Discover all known AI bounty programs and register base challenges with default targets."""
        challenges: list[AIBountyChallenge] = []
        for program in AIBountyMonitor().get_programs():
            pid = program["platform_id"]
            targets = _AI_SCAN_TARGETS.get(pid, [])
            challenge = self._monitor.register_challenge(
                platform=pid,
                challenge_id=f"{pid}_program",
                title=program["name"],
                url=program["url"],
                targets=targets,
                description=program.get("description", ""),
                severity="medium",
            )
            challenges.append(challenge)
        return challenges

    def scan_challenge(
        self,
        platform: str,
        challenge_id: str,
        targets: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run the existing tool pipeline against challenge targets."""
        challenge = self._monitor.get_challenge(platform, challenge_id)
        if challenge is None:
            return {"error": f"Challenge {platform}/{challenge_id} not found"}

        scan_targets = targets or challenge.targets
        if not scan_targets:
            return {
                "platform": platform,
                "challenge_id": challenge_id,
                "error": "No targets to scan — register targets first",
            }

        start = time.time()
        all_findings: list[dict[str, Any]] = []
        scan_errors: list[str] = []

        for target in scan_targets:
            try:
                result = self._run_scan_on_target(target, challenge.focus_areas)
                all_findings.extend(result.get("findings", []))
                if result.get("error"):
                    scan_errors.append(result["error"])
            except Exception as exc:
                logger.warning("Scan failed for %s target %s: %s", challenge_id, target, exc)
                scan_errors.append(str(exc))

        duration_ms = (time.time() - start) * 1000
        self._monitor.mark_scanned(platform, challenge_id)

        scan_result = {
            "platform": platform,
            "challenge_id": challenge_id,
            "targets": scan_targets,
            "findings": all_findings,
            "total_findings": len(all_findings),
            "scan_duration_ms": duration_ms,
            "errors": scan_errors,
        }
        self._scan_history[f"{platform}:{challenge_id}"] = scan_result

        self._publisher.challenge_scanned(
            platform=platform,
            challenge_id=challenge_id,
            findings_count=len(all_findings),
            scan_duration_ms=duration_ms,
        )

        if all_findings:
            self._auto_queue_reports(platform, challenge_id, all_findings)

        return scan_result

    def _run_scan_on_target(
        self,
        target: str,
        focus_areas: list[str],
    ) -> dict[str, Any]:
        """Run existing tools against a target.

        Uses UnifiedScanner for web targets, with specialized focus.
        Falls back gracefully if tools aren't installed.
        """
        findings: list[dict[str, Any]] = []

        try:
            from cores.tools.pipeline import UnifiedScanner

            scanner = UnifiedScanner()
            deep = bool(focus_areas)
            result = scanner.scan_domain(target, scan_vulns=deep)

            for v in result.get("vulnerabilities", []):
                findings.append(
                    {
                        "target": target,
                        "tool": v.get("source", "pipeline"),
                        "type": v.get("result_type", "vulnerability"),
                        "name": v.get("name", "Unknown"),
                        "severity": v.get("severity", "medium"),
                        "confidence": v.get("confidence", 0.5),
                        "description": v.get("description", ""),
                        "evidence": v.get("evidence", {}),
                    }
                )

            return {"findings": findings, "error": None}
        except ImportError:
            pass
        except Exception as exc:
            return {"findings": findings, "error": str(exc)}

        try:
            from cores.tools.nuclei import NucleiTool

            nuclei = NucleiTool()
            if nuclei.is_available():
                nresult = nuclei.scan([target])
                for r in getattr(nresult, "results", []):
                    findings.append(
                        {
                            "target": target,
                            "tool": "nuclei",
                            "type": r.result_type,
                            "name": r.name,
                            "severity": r.severity,
                            "confidence": r.confidence,
                            "description": r.description,
                            "evidence": r.evidence,
                        }
                    )
        except Exception:
            pass

        return {"findings": findings, "error": None}

    def _auto_queue_reports(
        self,
        platform: str,
        challenge_id: str,
        findings: list[dict[str, Any]],
    ) -> None:
        """Generate structured report drafts from findings."""
        if not findings:
            return

        report_entry = {
            "platform": platform,
            "challenge_id": challenge_id,
            "program": AIBountyMonitor().get_programs(),
            "total_findings": len(findings),
            "high_severity": sum(1 for f in findings if f.get("severity") in ("high", "critical")),
            "medium_severity": sum(1 for f in findings if f.get("severity") == "medium"),
            "low_severity": sum(1 for f in findings if f.get("severity") == "low"),
            "findings": findings,
            "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
        self._report_queue.append(report_entry)

        self._publisher.report_ready(
            platform=platform,
            challenge_id=challenge_id,
            report_id=len(self._report_queue),
            findings_count=len(findings),
            estimated_payout=self._estimate_payout(findings),
        )
        logger.info(
            "Report queued for %s/%s: %d high, %d medium findings",
            platform,
            challenge_id,
            report_entry["high_severity"],
            report_entry["medium_severity"],
        )

    def _estimate_payout(self, findings: list[dict[str, Any]]) -> float:
        """Rough payout estimate based on findings severity."""
        total = 0.0
        for f in findings:
            sev = f.get("severity", "medium")
            if sev == "critical":
                total += 5000
            elif sev == "high":
                total += 1500
            elif sev == "medium":
                total += 500
            else:
                total += 100
        return total

    def assess_opportunity(self, platform: str, challenge_id: str) -> dict[str, Any]:
        """Assess the expected value of pursuing a challenge."""
        challenge = self._monitor.get_challenge(platform, challenge_id)
        if challenge is None:
            return {"error": f"Challenge {platform}/{challenge_id} not found"}

        payout_estimate = 1500.0
        effort_hours = 4.0
        confidence = 0.4

        if challenge.payout_range:
            try:
                parts = challenge.payout_range.replace("$", "").split(" - ")
                if len(parts) == 2:
                    payout_estimate = (float(parts[0]) + float(parts[1])) / 2
            except (ValueError, IndexError):
                pass

        ev = payout_estimate / effort_hours * confidence

        if ev > 100:
            action = "high_priority"
        elif ev > 30:
            action = "worth_pursuing"
        elif ev > 10:
            action = "low_priority"
        else:
            action = "skip"

        result = {
            "platform": platform,
            "challenge_id": challenge_id,
            "title": challenge.title,
            "estimated_payout": payout_estimate,
            "effort_hours": effort_hours,
            "confidence": confidence,
            "expected_value_per_hour": round(ev, 2),
            "recommended_action": action,
        }

        self._publisher.opportunity_assessed(
            platform=platform,
            challenge_id=challenge_id,
            ev=ev,
            effort_hours=effort_hours,
            action=action,
        )
        return result

    def get_pending_reports(self) -> list[dict[str, Any]]:
        return list(self._report_queue)

    def get_scan_history(self, platform: str | None = None) -> list[dict[str, Any]]:
        results = list(self._scan_history.values())
        if platform:
            results = [r for r in results if r.get("platform") == platform]
        return results

    def get_stats(self) -> dict[str, Any]:
        total_findings = sum(r.get("total_findings", 0) for r in self._scan_history.values())
        total_scans = len(self._scan_history)
        total_reports = len(self._report_queue)
        return {
            "total_scans": total_scans,
            "total_findings": total_findings,
            "total_reports_queued": total_reports,
            "avg_findings_per_scan": round(total_findings / total_scans, 1) if total_scans else 0,
        }
