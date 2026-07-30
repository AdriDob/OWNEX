"""Revenue Pipeline — finding → evidence → report → platform → payout.

Connects the existing components into an end-to-end revenue workflow:
  - cores.platforms.* (platform connectors)
  - database.models.Report + SubmissionRecord (persistence)
  - cores.financial.events (event publication)
  - ledger (payout tracking)

Pipeline flow:
  1. Compose evidence bundle for a finding
  2. Create/update Report record in DB
  3. Select platform adapter, format report, submit
  4. Track submission status in SubmissionRecord
  5. Sync payouts from platforms
  6. Publish revenue events through EventBus
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from database.db import SessionLocal
from database.models import Finding, Report, SubmissionRecord
from database.models_economic import PayoutRecord, RevenueEvent

logger = logging.getLogger("ownex.revenue.pipeline")

REVENUE_SUBMISSION_STATUSES = [
    "draft",
    "submitted",
    "under_review",
    "triaged",
    "resolved",
    "bounty_paid",
    "rejected",
    "informative",
    "duplicate",
    "closed",
]


@dataclass
class PipelineResult:
    success: bool
    submission_id: int | None = None
    report_id: int | None = None
    external_id: str = ""
    url: str = ""
    status: str = ""
    payout_id: int | None = None
    amount: float = 0.0
    currency: str = "USD"
    error: str = ""


class RevenuePipeline:
    """Orchestrates end-to-end revenue workflow."""

    def __init__(self) -> None:
        self._event_bus = None

    # ── Event publishing ────────────────────────────────────────

    def _get_event_bus(self) -> Any:
        if self._event_bus is None:
            from cores.events.event_bus import get_core_event_bus

            self._event_bus = get_core_event_bus()
        return self._event_bus

    def _publish(self, event_type: str, **payload: Any) -> None:
        try:
            bus = self._get_event_bus()
            bus.publish(event_type, **payload)
        except Exception as exc:
            logger.warning("[REVENUE] Failed to publish %s: %s", event_type, exc)

    # ── Submission pipeline ─────────────────────────────────────

    def submit_report(
        self,
        finding_id: int,
        platform_id: str,
        program: str = "",
        evidence: dict[str, Any] | None = None,
        api_key: str = "",
    ) -> PipelineResult:
        """Submit a finding as a report to a bug bounty platform.

        Flow: find finding → create/update Report → submit via platform → record SubmissionRecord
        """
        db = SessionLocal()
        try:
            finding = db.query(Finding).filter(Finding.id == finding_id).first()
            if not finding:
                return PipelineResult(success=False, error=f"Finding {finding_id} not found")

            vuln_type = (
                evidence.get("vulnerability_type", "") if evidence else (finding.vulnerability_type or "generic")
            )
            summary = evidence.get("summary", "") if evidence else (finding.description or "")[:200]
            cvss = evidence.get("cvss_score", 0.0) if evidence else 0.0
            target_name = evidence.get("target", "") if evidence else ""

            report = Report(
                finding_ids=json.dumps([finding_id]),
                program=program,
                target=target_name,
                vulnerability=vuln_type,
                severity=_cvss_to_severity(cvss),
                status="draft",
                content=json.dumps(evidence) if evidence else "",
                evidence_count=1 if evidence else 0,
                estimated_reward=0.0,
                confirmed_reward=0.0,
            )
            db.add(report)
            db.flush()

            platform = self._get_platform(platform_id)
            if platform is None:
                db.rollback()
                return PipelineResult(
                    success=False,
                    error=f"Platform '{platform_id}' not found or not supported",
                    report_id=report.id,
                )

            report_data = self._build_report_data(finding, evidence, report, program)
            result = platform.submit(report_data, api_key)

            submission = SubmissionRecord(
                report_id=report.id,
                platform=platform_id,
                external_id=result.external_id if result.success else "",
                status="submitted" if result.success else "failed",
                extra_data=json.dumps(
                    {
                        "evidence_summary": summary[:100],
                        "vuln_type": vuln_type,
                        "submission_error": result.error if not result.success else "",
                    }
                ),
            )
            db.add(submission)
            db.flush()

            if result.success:
                report.status = "submitted"
                db.flush()

                self._publish(
                    "revenue:report_submitted",
                    report_id=report.id,
                    finding_id=finding_id,
                    platform=platform_id,
                    program=program,
                    external_id=result.external_id,
                )

            else:
                self._publish(
                    "revenue:submission_failed",
                    report_id=report.id,
                    finding_id=finding_id,
                    platform=platform_id,
                    error=result.error,
                )

            _record_revenue_event(
                db,
                "report_submitted" if result.success else "submission_failed",
                report_id=report.id,
                finding_id=finding_id,
                platform=platform_id,
                program=program,
                amount=0.0,
                metadata={"external_id": result.external_id, "error": result.error if not result.success else ""},
            )

            db.commit()
            return PipelineResult(
                success=result.success,
                submission_id=submission.id,
                report_id=report.id,
                external_id=result.external_id,
                url=result.url,
                status=submission.status,
                error=result.error,
            )

        except Exception as exc:
            db.rollback()
            logger.exception("[REVENUE] submit_report failed")
            return PipelineResult(success=False, error=str(exc))
        finally:
            db.close()

    def check_submission_status(self, submission_id: int, api_key: str = "") -> PipelineResult:
        """Check external status of a submission on its platform."""
        db = SessionLocal()
        try:
            submission: SubmissionRecord | None = (
                db.query(SubmissionRecord).filter(SubmissionRecord.id == submission_id).first()
            )
            if not submission:
                return PipelineResult(success=False, error=f"Submission {submission_id} not found")
            if not submission.external_id:
                return PipelineResult(
                    success=False,
                    error="Submission has no external ID (was submit successful?)",
                    submission_id=submission_id,
                )

            platform = self._get_platform(submission.platform)
            if platform is None:
                return PipelineResult(
                    success=False,
                    error=f"Platform '{submission.platform}' not available",
                    submission_id=submission_id,
                )

            external_status = platform.check_status(submission.external_id, api_key)

            if external_status and external_status != submission.status:
                submission.status = external_status
                submission.last_update = datetime.now(timezone.utc)
                db.flush()

                self._publish(
                    "revenue:status_changed",
                    submission_id=submission_id,
                    report_id=submission.report_id,
                    platform=submission.platform,
                    previous_status=submission.status,
                    new_status=external_status,
                )

                _record_revenue_event(
                    db,
                    "status_changed",
                    report_id=submission.report_id,
                    platform=submission.platform,
                    metadata={"previous": submission.status, "new": external_status},
                )

            db.commit()
            return PipelineResult(
                success=True,
                submission_id=submission.id,
                status=external_status or submission.status,
            )

        except Exception as exc:
            db.rollback()
            logger.exception("[REVENUE] check_submission_status failed")
            return PipelineResult(success=False, error=str(exc))
        finally:
            db.close()

    # ── Payout sync ─────────────────────────────────────────────

    def sync_platform_payouts(self, platform_id: str, api_key: str = "") -> list[PipelineResult]:
        """Sync earnings from a platform and record payouts."""
        db = SessionLocal()
        try:
            platform = self._get_platform(platform_id)
            if platform is None:
                return [PipelineResult(success=False, error=f"Platform '{platform_id}' not available")]

            sync_result = platform.sync_earnings(api_key)
            if not sync_result.success:
                self._publish("revenue:sync_failed", platform=platform_id, error=sync_result.error)
                return [PipelineResult(success=False, error=sync_result.error)]

            results: list[PipelineResult] = []
            for payout in sync_result.payouts or []:
                result = self._record_payout(
                    db=db,
                    platform=platform_id,
                    amount=payout.get("amount", 0.0),
                    currency=payout.get("currency", "USD"),
                    external_id=payout.get("external_id", ""),
                    program=payout.get("program", ""),
                    submission_record_id=payout.get("submission_id"),
                )
                results.append(result)

            db.commit()

            self._publish(
                "revenue:sync_completed",
                platform=platform_id,
                payouts_count=len(sync_result.payouts or []),
                total_earned=sync_result.total_earned,
            )

            return results

        except Exception as exc:
            db.rollback()
            logger.exception("[REVENUE] sync_platform_payouts failed")
            return [PipelineResult(success=False, error=str(exc))]
        finally:
            db.close()

    def record_payout(
        self,
        platform: str,
        amount: float,
        currency: str = "USD",
        program: str = "",
        external_id: str = "",
        submission_record_id: int | None = None,
    ) -> PipelineResult:
        """Record a single payout manually."""
        db = SessionLocal()
        try:
            result = self._record_payout(db, platform, amount, currency, program, external_id, submission_record_id)
            db.commit()
            return result
        except Exception as exc:
            db.rollback()
            logger.exception("[REVENUE] record_payout failed")
            return PipelineResult(success=False, error=str(exc))
        finally:
            db.close()

    def _record_payout(
        self,
        db: Any,
        platform: str,
        amount: float,
        currency: str = "USD",
        program: str = "",
        external_id: str = "",
        submission_record_id: int | None = None,
    ) -> PipelineResult:
        payout = PayoutRecord(
            platform=platform,
            amount=amount,
            currency=currency,
            program=program,
            external_id=external_id,
            submission_record_id=submission_record_id,
            status="confirmed",
            paid_at=datetime.now(timezone.utc),
        )
        db.add(payout)
        db.flush()

        _record_revenue_event(
            db,
            "payout_recorded",
            platform=platform,
            amount=amount,
            currency=currency,
            program=program,
            payout_id=payout.id,
            metadata={"external_id": external_id},
        )

        self._publish(
            "financial:payout_received",
            platform=platform,
            amount=amount,
            currency=currency,
            payout_id=payout.id,
        )

        return PipelineResult(
            success=True,
            payout_id=payout.id,
            amount=amount,
            currency=currency,
        )

    # ── Revenue summary ─────────────────────────────────────────

    def revenue_summary(self) -> dict[str, Any]:
        """Aggregate revenue statistics across all platforms."""
        db = SessionLocal()
        try:
            total_earned = db.query(PayoutRecord).filter(PayoutRecord.status == "confirmed").count()
            total_amount = (
                db.query(PayoutRecord)
                .filter(PayoutRecord.status == "confirmed")
                .with_entities(PayoutRecord.amount)
                .all()
            )
            total_sum = sum(r.amount for r in total_amount) if total_amount else 0.0

            by_platform: dict[str, Any] = {}
            platforms = db.query(PayoutRecord.platform).filter(PayoutRecord.status == "confirmed").distinct().all()
            for (pid,) in platforms:
                platform_payouts = (
                    db.query(PayoutRecord)
                    .filter(PayoutRecord.platform == pid, PayoutRecord.status == "confirmed")
                    .all()
                )
                by_platform[pid] = {
                    "count": len(platform_payouts),
                    "total": sum(p.amount for p in platform_payouts),
                    "currency": platform_payouts[0].currency if platform_payouts else "USD",
                }

            pending_payouts = db.query(PayoutRecord).filter(PayoutRecord.status == "pending").count()
            pending_amount = (
                db.query(PayoutRecord).filter(PayoutRecord.status == "pending").with_entities(PayoutRecord.amount).all()
            )
            pending_sum = sum(r.amount for r in pending_amount) if pending_amount else 0.0

            active_submissions = (
                db.query(SubmissionRecord)
                .filter(SubmissionRecord.status.in_(["submitted", "under_review", "triaged"]))
                .count()
            )

            return {
                "total_payouts": total_earned,
                "total_earned": round(total_sum, 2),
                "pending_payouts": pending_payouts,
                "pending_amount": round(pending_sum, 2),
                "active_submissions": active_submissions,
                "by_platform": by_platform,
            }

        except Exception as exc:
            logger.exception("[REVENUE] revenue_summary failed")
            return {"error": str(exc)}
        finally:
            db.close()

    def list_submissions(
        self,
        status: str | None = None,
        platform: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List submission records with optional filters."""
        db = SessionLocal()
        try:
            query = db.query(SubmissionRecord)
            if status:
                query = query.filter(SubmissionRecord.status == status)
            if platform:
                query = query.filter(SubmissionRecord.platform == platform)
            query = query.order_by(SubmissionRecord.submitted_at.desc()).limit(limit)

            results: list[dict[str, Any]] = []
            for sub in query.all():
                results.append(
                    {
                        "id": sub.id,
                        "report_id": sub.report_id,
                        "platform": sub.platform,
                        "external_id": sub.external_id,
                        "status": sub.status,
                        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else "",
                        "last_update": sub.last_update.isoformat() if sub.last_update else "",
                    }
                )
            return results

        except Exception:
            logger.exception("[REVENUE] list_submissions failed")
            return []
        finally:
            db.close()

    # ── Helpers ─────────────────────────────────────────────────

    def _get_platform(self, platform_id: str) -> Any:
        try:
            from cores.platforms import get_platform

            return get_platform(platform_id)
        except Exception as exc:
            logger.warning("[REVENUE] Cannot load platform %s: %s", platform_id, exc)
            return None

    def _build_report_data(
        self,
        finding: Any,
        evidence: dict[str, Any] | None,
        report: Any,
        program: str,
    ) -> dict[str, Any]:
        bundle = evidence or _finding_to_evidence(finding)
        return {
            "program": program or "",
            "vulnerability": finding.vulnerability_type or "generic",
            "severity": finding.severity or "medium",
            "content": bundle,
            "finding_id": finding.id,
            "report_id": report.id,
        }


# ── Module-level helpers ───────────────────────────────────────


def _cvss_to_severity(cvss: float) -> str:
    if cvss >= 9.0:
        return "critical"
    if cvss >= 7.0:
        return "high"
    if cvss >= 4.0:
        return "medium"
    return "low"


def _finding_to_evidence(finding: Any) -> dict[str, Any]:
    return {
        "vulnerability_type": finding.vulnerability_type or "generic",
        "summary": (finding.description or "")[:500],
        "severity": finding.severity or "medium",
        "cvss_score": 0.0,
        "description": finding.description or "",
    }


def register_revenue_capabilities() -> None:
    """Register Revenue Pipeline capabilities in the CapabilityRegistry."""
    try:
        from core.capabilities.registry import get_capability_registry

        reg = get_capability_registry()
        reg.register(
            "submit_report",
            "revenue",
            {"platforms": "hackerone,bugcrowd,intigriti,yeswehack,synack"},
            description="Submit finding as report to a bug bounty platform",
        )
        reg.register(
            "check_submission",
            "revenue",
            {},
            description="Check external status of a submitted report",
        )
        reg.register(
            "sync_payouts",
            "revenue",
            {"platforms": "hackerone,bugcrowd,intigriti,yeswehack,synack"},
            description="Sync earnings from bug bounty platforms",
        )
        reg.register(
            "record_payout",
            "revenue",
            {},
            description="Record a confirmed or pending payout",
        )
        reg.register(
            "revenue_summary",
            "revenue",
            {},
            description="Aggregate revenue statistics across platforms",
        )
    except Exception as exc:
        logger.warning("[REVENUE] Failed to register capabilities: %s", exc)


def _record_revenue_event(
    db: Any,
    event_type: str,
    **kwargs: Any,
) -> None:
    """Persist a revenue event for audit trail."""
    try:
        metadata = kwargs.pop("metadata", None) or {}
        ev = RevenueEvent(
            event_type=event_type,
            payload=json.dumps({**kwargs, "metadata": metadata}, default=str),
        )
        db.add(ev)
    except Exception as exc:
        logger.warning("[REVENUE] Failed to record event %s: %s", event_type, exc)
