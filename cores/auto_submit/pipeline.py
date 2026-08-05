"""AutoSubmitPipeline — automatic submission of confirmed findings.

Triggers on finding:status_changed → confirmed, runs Quality Gate + Acceptance
prediction, and auto-submits elite-quality findings to the appropriate platform.

Elite Quality Gate:
- severity: critical/high
- confidence: > 0.85
- evidence_complete: true
- reproduction_steps: clear and reproducible
- quality_score: > 85.0
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.reports.quality.classifier import QualityClassifier
from core.reports.quality.scorer import QualityScorer
from cores.events.types import Events
from cores.settings.service import get_setting
from database import db, models

logger = logging.getLogger("orion.core.auto_submit")

_ELITE_THRESHOLD = 85.0
_REVIEW_THRESHOLD = 60.0
_MAX_SUBMISSIONS_PER_HOUR = 5


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


def _get_elite_thresholds() -> dict[str, Any]:
    """Load elite thresholds from settings."""
    raw = get_setting("CATEYE.auto_submit.elite_thresholds", None)
    if raw:
        try:
            if isinstance(raw, str):
                raw = json.loads(raw)
            return raw
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to parse elite thresholds, using defaults: %s", e)
    return {
        "min_severity": "high",
        "min_confidence": 0.85,
        "require_evidence_complete": True,
        "require_reproduction_steps": True,
        "min_quality_score": 85.0,
        "max_submissions_per_hour": 5,
        "auto_approve_elite": True,
    }


def _check_rate_limit(max_per_hour: int = _MAX_SUBMISSIONS_PER_HOUR) -> tuple[bool, str]:
    """Check if rate limit would be exceeded."""
    session = db.SessionLocal()
    try:
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
        recent_count = (
            session.query(models.SubmissionRecord)
            .filter(
                models.SubmissionRecord.created_at >= one_hour_ago,
                models.SubmissionRecord.status.in_(["submitted", "auto_submitted"]),
            )
            .count()
        )
        if recent_count >= max_per_hour:
            # Notify user about rate limit
            try:
                from cores.notifications.action_required import notify_action_required

                notify_action_required(
                    title="Submission rate limit reached",
                    reason=f"Auto-submission rate limit reached ({recent_count}/{max_per_hour} per hour)",
                    impact="Elite findings queued, waiting for rate limit to reset",
                    steps=[
                        "Wait 1 hour for rate limit to reset",
                        "Or go to Settings > Auto-Submit to increase the limit",
                        f"Queue has {recent_count} submissions waiting",
                    ],
                    ui_path="/operations/scheduler",
                    category="config",
                    priority="medium",
                    channels=["web", "desktop"],
                    subject_id="rate_limit",
                    subject_type="system",
                )
            except Exception:
                pass
            return False, f"Rate limit exceeded: {recent_count}/{max_per_hour} submissions in last hour"
        return True, ""
    finally:
        session.close()


def _get_confidence_score(finding_id: int) -> float:
    """Extract confidence score from verdict."""
    session = db.SessionLocal()
    try:
        finding = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not finding or not finding.endpoint_id:
            return 0.0

        verdict = (
            session.query(models.Verdict)
            .filter(models.Verdict.endpoint_id == finding.endpoint_id)
            .order_by(models.Verdict.id.desc())
            .first()
        )
        if not verdict or not verdict.confidence:
            return 0.0

        try:
            conf_data = json.loads(verdict.confidence) if isinstance(verdict.confidence, str) else verdict.confidence
            if isinstance(conf_data, dict):
                return float(conf_data.get("score", 0.0))
            return float(conf_data)
        except (json.JSONDecodeError, TypeError, ValueError):
            return 0.0
    finally:
        session.close()


def _get_evidence_count(finding_id: int) -> int:
    """Count evidence records for a finding."""
    session = db.SessionLocal()
    try:
        finding = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not finding or not finding.endpoint_id:
            return 0

        verdicts = session.query(models.Verdict).filter(models.Verdict.endpoint_id == finding.endpoint_id).all()
        if not verdicts:
            return 0

        verdict_ids = [v.id for v in verdicts]
        return session.query(models.Evidence).filter(models.Evidence.verdict_id.in_(verdict_ids)).count()
    finally:
        session.close()


def _check_reproduction_steps(finding_id: int) -> bool:
    """Check if finding has clear reproduction steps."""
    session = db.SessionLocal()
    try:
        finding = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not finding:
            return False

        # Check description for reproduction indicators
        desc = finding.description or ""
        notes = finding.notes or ""
        combined = (desc + " " + notes).lower()

        # Look for reproduction keywords
        repro_keywords = ["steps to reproduce", "reproduction", "steps:", "1.", "first,", "to reproduce"]
        has_keyword = any(keyword in combined for keyword in repro_keywords)

        # Check minimum length
        has_length = len(desc) > 100 or len(notes) > 50

        return has_keyword or has_length
    finally:
        session.close()


def _check_elite_gate(finding: models.Finding, quality_score: float) -> tuple[bool, str]:
    """Check if finding passes elite quality gate."""
    thresholds = _get_elite_thresholds()

    # Check severity
    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    finding_severity_level = severity_order.get(finding.severity or "medium", 2)
    min_severity_level = severity_order.get(thresholds.get("min_severity", "high"), 3)
    if finding_severity_level < min_severity_level:
        return False, f"Severity {finding.severity} below minimum {thresholds.get('min_severity')}"

    # Check confidence
    confidence = _get_confidence_score(finding.id)
    min_confidence = thresholds.get("min_confidence", 0.85)
    if confidence < min_confidence:
        return False, f"Confidence {confidence:.2f} below minimum {min_confidence}"

    # Check quality score
    min_quality = thresholds.get("min_quality_score", 85.0)
    if quality_score < min_quality:
        return False, f"Quality score {quality_score} below minimum {min_quality}"

    # Check evidence
    if thresholds.get("require_evidence_complete", True):
        evidence_count = _get_evidence_count(finding.id)
        if evidence_count < 2:
            return False, f"Insufficient evidence: {evidence_count} records"

    # Check reproduction steps
    if thresholds.get("require_reproduction_steps", True):
        has_repro = _check_reproduction_steps(finding.id)
        if not has_repro:
            return False, "Missing clear reproduction steps"

    return True, "Passes elite gate"


class AutoSubmitPipeline:
    """Auto-submits confirmed findings that pass Quality Gate."""

    def __init__(
        self,
        elite_threshold: float = _ELITE_THRESHOLD,
        review_threshold: float = _REVIEW_THRESHOLD,
    ):
        self.elite_threshold = elite_threshold
        self.review_threshold = review_threshold

    def on_finding_confirmed(self, finding_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Handle a confirmed finding. Run quality gate and decide action.

        Payload options:
        - manual_approval: True if manually approved via API
        - elite_bypass: True if bypassing global approval check for elite findings
        """
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

            # Check elite gate
            passes_elite, elite_reason = _check_elite_gate(finding, total)
            thresholds = _get_elite_thresholds()

            # Log submission attempt
            logger.info(
                "[AUTO-SUBMIT] Finding %s: score=%.1f, severity=%s, passes_elite=%s, reason=%s",
                finding_id,
                total,
                finding.severity,
                passes_elite,
                elite_reason,
            )

            # Check for manual approval or elite bypass
            is_manual = payload and payload.get("manual_approval", False)
            is_elite_bypass = payload and payload.get("elite_bypass", False)
            auto_approve_elite = thresholds.get("auto_approve_elite", True)

            # Check global approval setting
            never_submit = get_setting("CATEYE.never_submit_without_approval", True)

            # Auto-submit if:
            # 1. Manual approval (always submit)
            # 2. Elite bypass (bypass global check)
            # 3. Passes elite gate AND auto_approve_elite AND not blocked by global setting
            should_auto_submit = False
            submit_reason = ""

            if is_manual:
                should_auto_submit = True
                submit_reason = "manual_approval"
            elif is_elite_bypass and passes_elite:
                should_auto_submit = True
                submit_reason = "elite_bypass"
            elif passes_elite and auto_approve_elite and not never_submit:
                should_auto_submit = True
                submit_reason = "elite_auto_approve"
            elif passes_elite and auto_approve_elite and never_submit:
                # Elite finding but global approval blocks it
                logger.warning(
                    "[AUTO-SUBMIT] Elite finding %s blocked by global approval setting (never_submit_without_approval=True)",
                    finding_id,
                )
                return self._queue_for_review(finding, platform, total, classification, "blocked_by_global_setting")

            if should_auto_submit:
                # Check rate limit
                max_per_hour = thresholds.get("max_submissions_per_hour", _MAX_SUBMISSIONS_PER_HOUR)
                within_limit, rate_msg = _check_rate_limit(max_per_hour)
                if not within_limit:
                    logger.warning("[AUTO-SUBMIT] Rate limit for finding %s: %s", finding_id, rate_msg)
                    return self._queue_for_review(finding, platform, total, classification, f"rate_limit: {rate_msg}")

                logger.info(
                    "[AUTO-SUBMIT] Auto-submitting finding %s (reason: %s, score: %.1f)",
                    finding_id,
                    submit_reason,
                    total,
                )
                return self._auto_submit(finding, platform, quality_score, payload, submit_reason)

            # Queue for review if above review threshold
            if total >= self.review_threshold:
                return self._queue_for_review(finding, platform, total, classification, "below_elite_threshold")

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
        submit_reason: str = "auto",
    ) -> dict[str, Any]:
        """Auto-submit an elite-quality finding."""
        finding_id = finding.id
        logger.info(
            "[AUTO-SUBMIT] Elite finding %s → auto-submitting to %s (reason: %s)",
            finding_id,
            platform,
            submit_reason,
        )

        api_key = self._get_api_key(platform)
        if not api_key:
            logger.warning("[AUTO-SUBMIT] No API key for %s, queueing for review", platform)
            # Notify user about missing API key
            try:
                from cores.notifications.action_required import notify_credentials_missing

                notify_credentials_missing(
                    platform=platform,
                    credential_name=f"{platform.upper()}_API_KEY",
                    impact=f"Finding #{finding_id} ready for submission but no API key configured",
                )
            except Exception:
                pass
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
            submit_reason=submit_reason,
        )

        return {
            "action": "auto_submitted" if result.success else "submit_failed",
            "score": quality_score.score,
            "platform": platform,
            "finding_id": finding_id,
            "submission_id": result.submission_id if result.success else None,
            "error": result.error if not result.success else None,
            "submit_reason": submit_reason,
        }

    def _queue_for_review(
        self,
        finding: models.Finding,
        platform: str,
        score: float,
        classification: Any,
        queue_reason: str = "below_elite_threshold",
    ) -> dict[str, Any]:
        """Queue a finding for human review."""
        logger.info(
            "[AUTO-SUBMIT] Finding %s score=%.1f → queued for review (reason: %s)",
            finding.id,
            score,
            queue_reason,
        )

        bus = get_bus()
        bus.publish(
            Events.AUTO_SUBMIT_QUEUED,
            finding_id=finding.id,
            platform=platform,
            score=score,
            title=finding.title,
            queue_reason=queue_reason,
        )

        return {
            "action": "queued_for_review",
            "score": score,
            "platform": platform,
            "finding_id": finding.id,
            "queue_reason": queue_reason,
        }


_PIPELINE: AutoSubmitPipeline | None = None


def get_auto_submit_pipeline() -> AutoSubmitPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = AutoSubmitPipeline()
    return _PIPELINE
