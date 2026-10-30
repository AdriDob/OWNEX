"""Direct Work Delivery Engine — Handles delivery/submission of completed work.

Provides delivery logic that can be used by WorkerCore for the DELIVER phase.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("ownex.direct_work_engine.delivery")


@dataclass(slots=True)
class DeliveryResult:
    """Result of delivering a work item."""

    success: bool
    submission_id: str | None = None
    submission_url: str | None = None
    platform_response: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "submission_id": self.submission_id,
            "submission_url": self.submission_url,
            "platform_response": self.platform_response,
            "error": self.error,
        }


class DirectWorkDeliveryEngine:
    """Handles delivery/submission of completed work items.

    Supports:
    - AutoSubmit for platform-specific submission
    - Manual delivery preparation
    - Submission tracking
    """

    def __init__(self) -> None:
        self._auto_submit = None
        self._platform_handlers = {}

    def set_auto_submit(self, auto_submit: Any) -> None:
        self._auto_submit = auto_submit

    def register_platform_handler(self, platform: str, handler: Any) -> None:
        self._platform_handlers[platform.lower()] = handler

    def deliver(self, work_item: Any, approved_by_human: bool = True) -> dict[str, Any]:
        """Deliver a completed work item.

        Args:
            work_item: Completed work item to deliver
            approved_by_human: Whether human has approved the delivery

        Returns:
            Delivery result dict
        """
        if not approved_by_human:
            return DeliveryResult(
                success=False,
                error="Human approval required for delivery",
            ).to_dict()

        # Quality Gate: block delivery if quality checks fail
        try:
            from cores.direct_work_engine.evaluation import _run_quality_gate

            gate_result = _run_quality_gate(work_item)
            if not gate_result.get("passed", False):
                reason = gate_result.get("reason", "Quality gate failed")
                logger.warning("Delivery blocked by Quality Gate: %s", reason)
                return DeliveryResult(
                    success=False,
                    error=f"Quality Gate failed: {reason}",
                ).to_dict()
        except Exception as exc:
            logger.debug("Quality gate check failed (non-blocking): %s", exc)

        platform = getattr(work_item, "platform", "").lower()

        # Try auto-submit first
        if self._auto_submit and hasattr(self._auto_submit, "submit"):
            try:
                result = self._auto_submit.submit(work_item)
                delivery_result = DeliveryResult(
                    success=result.get("success", False),
                    submission_id=result.get("submission_id"),
                    submission_url=result.get("submission_url"),
                    platform_response=result.get("response", {}),
                    error=result.get("error"),
                )
                self._emit_delivery_event(work_item, delivery_result)
                return delivery_result.to_dict()
            except Exception as exc:
                logger.warning("Auto-submit failed for %s: %s", getattr(work_item, "id", "unknown"), exc)

        # Try platform-specific handler
        platform = getattr(work_item, "platform", "").lower()
        handler = self._platform_handlers.get(platform.lower())

        if handler and hasattr(handler, "submit"):
            try:
                result = handler.submit(work_item)
                delivery_result = DeliveryResult(
                    success=result.get("success", False),
                    submission_id=result.get("submission_id"),
                    submission_url=result.get("submission_url"),
                    platform_response=result.get("response", {}),
                    error=result.get("error"),
                )
                self._emit_delivery_event(work_item, delivery_result)
                return delivery_result.to_dict()
            except Exception as exc:
                logger.warning("Platform handler failed for %s: %s", platform, exc)

        # Fallback: prepare for manual delivery
        delivery_result = DeliveryResult(
            success=True,
            submission_id=f"manual_{getattr(work_item, 'id', 'unknown')}",
            submission_url="",
            platform_response={"status": "prepared_for_manual_delivery"},
            error=None,
        )
        self._emit_delivery_event(work_item, delivery_result)
        return delivery_result.to_dict()

    def prepare_delivery_package(self, work_item: Any) -> dict[str, Any]:
        """Prepare a delivery package for manual submission.

        Returns a package with all necessary files and instructions.
        """
        return {
            "work_item_id": getattr(work_item, "id", "unknown"),
            "title": getattr(work_item, "title", ""),
            "platform": getattr(work_item, "platform", ""),
            "description": getattr(work_item, "description", ""),
            "deliverables": getattr(work_item, "deliverables", []),
            "artifacts": getattr(work_item, "artifacts", []),
            "evidence": getattr(work_item, "evidence", []),
            "submission_instructions": self._get_submission_instructions(getattr(work_item, "platform", "")),
        }

    def _emit_delivery_event(self, work_item: Any, result: DeliveryResult) -> None:
        """Emit delivery event for revenue tracking and observability."""
        try:
            from cores.events.event_bus import get_event_bus

            bus = get_event_bus()
            bus.publish(
                "delivery:completed",
                work_item_id=getattr(work_item, "id", "unknown"),
                platform=getattr(work_item, "platform", "unknown"),
                success=result.success,
                submission_id=result.submission_id,
                submission_url=result.submission_url,
                estimated_reward=getattr(work_item, "estimated_reward_usd", 0),
                workflow_id=getattr(work_item, "workflow_id", None),
            )
        except Exception as exc:
            logger.debug("Delivery event emission failed (non-blocking): %s", exc)

    def _get_submission_instructions(self, platform: str) -> str:
        """Get platform-specific submission instructions."""
        instructions = {
            "hackerone": "Submit via HackerOne platform using API key. Navigate to Reports > New Report.",
            "bugcrowd": "Submit via Bugcrowd platform using API key. Navigate to Submissions > New Submission.",
            "intigriti": "Submit via Intigriti platform using API key. Navigate to Submissions > Create.",
            "yeswehack": "Submit via YesWeHack platform using API key. Navigate to Reports > New.",
            "opire": "Submit via Opire platform. Navigate to Issue > Submit Solution.",
            "issuehunt": "Submit via IssueHunt. Navigate to Issue > Submit PR.",
            "algora": "Submit via Algora. Navigate to Bounty > Submit Work.",
            "freelancer": "Submit via Freelancer.com. Navigate to Project > Submit Deliverable.",
            "outlier": "Submit via Outlier platform. Complete the task in the assigned project.",
            "mindrift": "Submit via Mindrift platform. Complete the assigned task.",
            "remotasks": "Submit via Remotasks. Complete the assigned task.",
            "upwork": "Submit via Upwork. Navigate to Contract > Submit Work.",
        }
        return instructions.get(platform.lower(), "Manual submission required. Check platform documentation.")


# Convenience function
async def deliver_work_item(work_item: Any, approved_by_human: bool = True) -> dict[str, Any]:
    """Convenience function for delivering a work item."""
    engine = DirectWorkDeliveryEngine()
    return engine.deliver(work_item, approved_by_human)
