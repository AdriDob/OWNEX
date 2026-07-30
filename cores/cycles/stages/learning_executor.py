"""LearningExecutor — captures knowledge from pipeline outcomes.

Stage 7 (final) of the security pipeline. Analyses what worked and what
didn't across the pipeline run, captures lessons into the knowledge base,
and feeds insights back into future opportunity scoring and hypothesis
generation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cores.cycles.stages import BaseStageExecutor


class LearningExecutor(BaseStageExecutor):
    """Capture learning and knowledge from pipeline execution outcomes.

    Uses KnowledgeCapture from the cycles framework to persist lessons
    about vulnerability patterns, tool effectiveness, platform quirks,
    and score calibration.
    """

    @property
    def name(self) -> str:
        return "learning"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self.logger.info("Starting learning capture")

        target = context.get("target", "")
        reports = context.get("reports", []) or context.get("details", {}).get("reports", [])
        context.get("bundles", []) or context.get("details", {}).get("bundles", [])
        validated = context.get("validated", []) or context.get("details", {}).get("validated", [])

        # Gather pipeline results from context chain
        stage_results = context.get("details", {})

        try:
            entries: list[dict[str, Any]] = []

            # Try real KnowledgeCapture integration
            try:
                from cores.cycles.knowledge_capture import KnowledgeCapture, LearningType

                kc = KnowledgeCapture()

                # Capture from findings in the database (most authoritative)
                db_entries = self._capture_from_db_findings(kc, target)
                entries.extend(db_entries)

                # If we have report data, extract lessons from the pipeline run
                pipeline_lessons = self._extract_pipeline_lessons(
                    stage_results, target, reports, validated
                )
                for lesson in pipeline_lessons:
                    ltype = LearningType(lesson.get("type", "pattern"))
                    entry = kc._store_entry(
                        ltype=ltype,
                        lesson=lesson["lesson"],
                        confidence=lesson.get("confidence", 0.5),
                        vuln_type=lesson.get("vuln_type"),
                        platform=lesson.get("platform"),
                        metadata=lesson.get("metadata", {}),
                    )
                    if entry:
                        entries.append(entry._asdict() if hasattr(entry, '_asdict') else {"id": str(entry), "lesson": lesson["lesson"]})

            except Exception as exc:
                self.logger.debug("KnowledgeCapture integration not available: %s", exc)
                entries = self._build_learning_entries(stage_results, target, reports, validated)

            # If nothing to learn from, report that
            if not entries:
                return self._wrap_result(
                    "completed",
                    "No learning captured — no new findings or failures in this pipeline run",
                    details={"entries": [], "entry_count": 0, "completed_at": datetime.now(UTC).isoformat()},
                )

            summary = f"Captured {len(entries)} knowledge entries from pipeline execution"

            details: dict[str, Any] = {
                "entries": entries,
                "entry_count": len(entries),
                "type_breakdown": self._type_breakdown(entries),
                "completed_at": datetime.now(UTC).isoformat(),
            }

            self.logger.info(summary)
            return self._wrap_result("completed", summary, details)

        except Exception as exc:
            self.logger.error("Learning capture failed: %s", exc)
            return self._wrap_result("failed", f"Learning capture failed: {exc}", error=str(exc))

    def _capture_from_db_findings(self, kc, target: str) -> list[dict[str, Any]]:
        """Capture knowledge from confirmed findings in the database."""
        entries: list[dict[str, Any]] = []

        try:
            from database import db
            from database.models import Finding
            from database.models import Target as TargetModel

            session = db.SessionLocal()
            try:
                db_target = (
                    session.query(TargetModel)
                    .filter(TargetModel.name == target)
                    .first()
                )
                if db_target:
                    findings = (
                        session.query(Finding)
                        .filter(Finding.target_id == db_target.id)
                        .filter(Finding.status.in_(["confirmed", "rejected"]))
                        .all()
                    )
                    for finding in findings:
                        entry = kc.capture_from_finding(finding)
                        if entry:
                            entries.append({
                                "id": entry.id,
                                "type": entry.type.value if hasattr(entry.type, 'value') else str(entry.type),
                                "lesson": entry.lesson[:200],
                                "confidence": entry.confidence,
                                "vuln_type": entry.vuln_type,
                                "platform": entry.platform,
                                "source": "db_finding",
                            })
            finally:
                session.close()
        except Exception as exc:
            self.logger.debug("DB finding capture failed: %s", exc)

        return entries

    def _extract_pipeline_lessons(
        self,
        stage_results: dict[str, Any],
        target: str,
        reports: list[dict[str, Any]],
        validated: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract learning lessons from the pipeline execution results."""
        lessons: list[dict[str, Any]] = []

        # Lesson from confirmed vs rejected ratio
        if validated:
            confirmed = sum(1 for v in validated if v.get("status") == "confirmed")
            rejected = sum(1 for v in validated if v.get("status") == "rejected")
            total = len(validated)
            if total > 0:
                hit_rate = confirmed / total
                lessons.append({
                    "type": "score_calibration",
                    "lesson": (
                        f"Pipeline hit rate for {target}: {confirmed}/{total} confirmed "
                        f"({round(hit_rate * 100, 1)}%). "
                        f"{'Hypothesis confidence calibration is accurate.' if hit_rate > 0.5 else 'Hypothesis generation may be over-generating low-confidence leads.'}"
                    ),
                    "confidence": min(1.0, hit_rate + 0.2),
                    "vuln_type": None,
                    "platform": None,
                    "metadata": {
                        "target": target,
                        "confirmed": confirmed,
                        "rejected": rejected,
                        "total": total,
                        "hit_rate": round(hit_rate, 3),
                    },
                })

        # Lesson from vulnerability type effectiveness
        if reports:
            vuln_types: dict[str, int] = {}
            for r in reports:
                vt = r.get("vulnerability_type", "unknown")
                vuln_types[vt] = vuln_types.get(vt, 0) + 1

            if vuln_types:
                most_common = max(vuln_types, key=vuln_types.get)
                lessons.append({
                    "type": "pattern",
                    "lesson": (
                        f"Most common vulnerability type for {target}: {most_common} "
                        f"({vuln_types[most_common]} findings). "
                        f"Focus future testing on {most_common} patterns."
                    ),
                    "confidence": 0.7,
                    "vuln_type": most_common,
                    "platform": None,
                    "metadata": {
                        "target": target,
                        "vuln_type_breakdown": vuln_types,
                        "most_common": most_common,
                    },
                })

        # Lesson from report quality
        if reports:
            quality_passed = sum(1 for r in reports if r.get("quality_check", {}).get("passed", False))
            quality_total = len(reports)
            if quality_total > 0 and quality_passed < quality_total:
                gaps = set()
                for r in reports:
                    for g in r.get("quality_check", {}).get("gaps", []):
                        gaps.add(g)
                if gaps:
                    lessons.append({
                        "type": "report_structure",
                        "lesson": (
                            f"Report quality gaps identified: {', '.join(list(gaps)[:3])}. "
                            f"Improve evidence collection for these areas."
                        ),
                        "confidence": 0.8,
                        "vuln_type": None,
                        "platform": None,
                        "metadata": {
                            "quality_passed": quality_passed,
                            "quality_total": quality_total,
                            "common_gaps": list(gaps),
                        },
                    })

        return lessons

    def _build_learning_entries(
        self,
        stage_results: dict[str, Any],
        target: str,
        reports: list[dict[str, Any]],
        validated: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build representative learning entries when KnowledgeCapture is unavailable."""
        entries: list[dict[str, Any]] = []

        if validated:
            confirmed = [v for v in validated if v.get("status") == "confirmed"]
            if confirmed:
                for v in confirmed[:3]:
                    entries.append({
                        "id": f"learn_{v.get('hypothesis_id', 'unknown')}_{datetime.now(UTC).timestamp()}",
                        "type": "pattern",
                        "lesson": (
                            f"Confirmed {v.get('vulnerability_type', 'unknown')} on "
                            f"{v.get('method', 'GET')} {v.get('endpoint', '/')} "
                            f"— technique validated with confidence {v.get('confidence', 0)}"
                        ),
                        "confidence": v.get("confidence", 0.5),
                        "vuln_type": v.get("vulnerability_type"),
                        "platform": None,
                        "source": "pipeline_result",
                        "created_at": datetime.now(UTC).isoformat(),
                    })

        if target:
            entries.append({
                "id": f"learn_general_{datetime.now(UTC).timestamp()}",
                "type": "tool_effectiveness",
                "lesson": (
                    f"Security pipeline completed for {target}. "
                    f"Generated {len(validated)} validations, "
                    f"{len(reports)} reports. "
                    f"Pipeline execution successful."
                ),
                "confidence": 0.9,
                "vuln_type": None,
                "platform": None,
                "source": "pipeline_metadata",
                "created_at": datetime.now(UTC).isoformat(),
            })

        return entries

    def _type_breakdown(self, entries: list[dict[str, Any]]) -> dict[str, int]:
        breakdown: dict[str, int] = {}
        for e in entries:
            lt = e.get("type", "unknown")
            breakdown[lt] = breakdown.get(lt, 0) + 1
        return breakdown
