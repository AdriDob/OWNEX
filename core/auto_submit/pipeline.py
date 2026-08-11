"""AutoSubmitPipeline — automatic submission of confirmed findings.

Triggers on finding:status_changed → confirmed, runs Quality Gate + Acceptance
prediction, and auto-submits elite-quality findings to the appropriate platform.
"""

from __future__ import annotations

import logging
from typing import Any

from core.reports.quality.classifier import QualityClassifier
from core.reports.quality.scorer import QualityScorer
from cores.events.types import Events
from database import db, models

logger = logging.getLogger("orion.core.auto_submit")

_ELITE_THRESHOLD = 85.0
_REVIEW_THRESHOLD = 60.0


def get_revenue_pipeline():
    from core.revenue.pipeline import RevenuePipeline

    return RevenuePipeline()


def get_vault():
    from cores.identity_vault import get_identity_vault

    return get_identity_vault()


def get_acceptance_learner():
    from core.reports.acceptance.learner import AcceptanceLearner

    return AcceptanceLearner()


def get_bus():
    from cores.events.event_bus import get_event_bus

    return get_event_bus()


class AutoSubmitPipeline:
    """Auto-submits confirmed findings that pass Quality Gate."""

    def __init__(
        self,
        elite_threshold: float = _ELITE_THRESHOLD,
        review_threshold: float = _REVIEW_THRESHOLD,
    ):
        self.elite_threshold = elite_threshold
        self.review_threshold = review_threshold

    def process_finding(self, finding_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Alias for on_finding_confirmed — kept for API compatibility."""
        return self.on_finding_confirmed(finding_id, payload)

    def on_finding_confirmed(self, finding_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Handle a confirmed finding. Run quality gate and decide action."""
        session = db.SessionLocal()
        try:
            finding = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
            if not finding:
                return {"action": "error", "reason": f"Finding {finding_id} not found"}

            scorer = QualityScorer()
            quality_score = scorer.score(finding_id)
            total = quality_score.score

            classifier = QualityClassifier()
            classification = classifier.classify(quality_score)

            platform = self._detect_platform(finding)

            if total >= self.elite_threshold and classification.passed:
                return self._auto_submit(finding, platform, quality_score, payload)
            if total >= self.review_threshold:
                return self._queue_for_review(finding, platform, total, classification)
            return {
                "action": "skip",
                "score": total,
                "platform": platform,
                "finding_id": finding_id,
                "reason": f"Quality {total:.1f} below review threshold {self.review_threshold}",
            }
        finally:
            session.close()

    def _detect_platform(self, finding: models.Finding) -> str:
        """Determine target platform from finding's target."""
        if not finding.target_id:
            return "hackerone"
        session = db.SessionLocal()
        try:
            target = session.query(models.Target).filter(models.Target.id == finding.target_id).first()
            if target and target.name and "_" in target.name:
                parts = target.name.split("_", 1)
                known = {"hackerone", "bugcrowd", "intigriti", "yeswehack", "immunefi"}
                if parts[0] in known:
                    return parts[0]
        finally:
            session.close()
        return "hackerone"

    def _get_api_key(self, platform: str) -> str:
        """Retrieve API key for a platform from IdentityVault."""
        vault_key = f"api_key_{platform}"
        try:
            vault = get_vault()
            key = vault.get(vault_key)
            if key:
                return key
        except Exception as exc:
            logger.warning("Vault lookup failed for %s: %s", vault_key, exc)
        import os

        env_key = f"{platform.upper()}_API_KEY"
        return os.environ.get(env_key, "")

    def _auto_submit(
        self,
        finding: models.Finding,
        platform: str,
        quality_score: Any,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Auto-submit an elite-quality finding."""
        finding_id = finding.id
        logger.info("[AUTO-SUBMIT] Elite finding %s → auto-submitting to %s", finding_id, platform)

        api_key = self._get_api_key(platform)
        if not api_key:
            logger.warning("[AUTO-SUBMIT] No API key for %s, queueing for review", platform)
            return self._queue_for_review(finding, platform, quality_score.score, None)

        target_name = ""
        program = ""
        if finding.target_id:
            session = db.SessionLocal()
            try:
                target = session.query(models.Target).filter(models.Target.id == finding.target_id).first()
                if target:
                    target_name = target.name or target.domain or ""
                    if target.name and "_" in target.name:
                        program = target.name.split("_", 1)[1] if "_" in target.name else target.name
            finally:
                session.close()

        evidence_dict = {
            "vulnerability_type": finding.vulnerability_type or "generic",
            "summary": (finding.description or "")[:500],
            "severity": finding.severity or "medium",
            "target": target_name,
            "cvss_score": 0.0,
        }

        pipeline = get_revenue_pipeline()
        result = pipeline.submit_report(
            finding_id=finding_id,
            platform_id=platform,
            program=program,
            evidence=evidence_dict,
            api_key=api_key,
        )

        if result.success:
            logger.info(
                "[AUTO-SUBMIT] Finding %s submitted to %s (ext_id=%s)",
                finding_id,
                platform,
                result.submission_id,
            )
        else:
            logger.warning(
                "[AUTO-SUBMIT] Submission failed for finding %s: %s",
                finding_id,
                result.error,
            )

        bus = get_bus()
        event_type = Events.AUTO_SUBMIT_EXECUTED if result.success else Events.AUTO_SUBMIT_FAILED
        bus.publish(
            event_type,
            finding_id=finding_id,
            platform=platform,
            score=quality_score.score,
            success=result.success,
            submission_id=result.submission_id if result.success else None,
            error=result.error if not result.success else None,
        )

        return {
            "action": "auto_submitted" if result.success else "submit_failed",
            "score": quality_score.score,
            "platform": platform,
            "finding_id": finding_id,
            "submission_id": result.submission_id if result.success else None,
            "error": result.error if not result.success else None,
        }

    def _queue_for_review(
        self,
        finding: models.Finding,
        platform: str,
        score: float,
        classification: Any,
    ) -> dict[str, Any]:
        """Queue a finding for human review."""
        logger.info("[AUTO-SUBMIT] Finding %s score=%.1f → queued for review", finding.id, score)

        bus = get_bus()
        bus.publish(
            Events.AUTO_SUBMIT_QUEUED,
            finding_id=finding.id,
            platform=platform,
            score=score,
            title=finding.title,
        )

        return {
            "action": "queued_for_review",
            "score": score,
            "platform": platform,
            "finding_id": finding.id,
        }


_PIPELINE: AutoSubmitPipeline | None = None


def get_auto_submit_pipeline() -> AutoSubmitPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = AutoSubmitPipeline()
    return _PIPELINE


def process_finding(finding_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Module-level wrapper — delegates to AutoSubmitPipeline.on_finding_confirmed."""
    return get_auto_submit_pipeline().on_finding_confirmed(finding_id, payload)
