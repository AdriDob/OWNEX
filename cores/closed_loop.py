"""Closed Loop Manager — Automated feedback from payments to profile.

Connects payment detection → trust learning → profile updates → improved recommendations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from cores.direct_work_engine.feedback import LearningRecord, apply_learning
from cores.direct_work_engine.models import OpportunityCategory, UserProfile

from .payment_tracker import get_payment_tracker
from .trust_engine import get_trust_engine

logger = logging.getLogger("ownex.closed_loop")


@dataclass
class ClosedLoopConfig:
    """Configuration for closed-loop automation."""

    auto_learn_from_payments: bool = True
    auto_update_trust: bool = True
    auto_update_profile: bool = True
    min_payment_amount_usd: float = 1.0  # Ignore micro-payments


class ClosedLoopManager:
    """Manages the closed-loop feedback system."""

    def __init__(self, config: ClosedLoopConfig | None = None):
        self.config = config or ClosedLoopConfig()
        self.payment_tracker = get_payment_tracker()
        self.trust_engine = get_trust_engine()
        self._default_profile = self._build_default_profile()

    def _build_default_profile(self) -> UserProfile:
        """Build the default user profile for learning."""
        return UserProfile(
            name="Adriel",
            country="Argentina",
            languages={"es", "en"},
            skills={"python", "go", "unity", "typescript"},
            experience_level="none",
            remote_only=True,
            accepts_ai_tools=True,
            has_portfolio=False,
        )

    def process_payment(self, payment_id: str) -> dict[str, Any]:
        """Process a confirmed payment and trigger learning."""
        payment = self.payment_tracker.confirm_payment(payment_id)
        if not payment:
            return {"success": False, "error": "Payment not found"}

        logger.info(f"[CLOSED_LOOP] Processing payment: {payment.platform} - ${payment.amount_usd}")

        results = {}

        # Update trust metrics
        if self.config.auto_update_trust:
            trust_result = self._update_trust(payment)
            results["trust_updated"] = trust_result

        # Update profile with learning
        if self.config.auto_update_profile:
            learning_result = self._update_profile(payment)
            results["profile_updated"] = learning_result

        return {
            "success": True,
            "payment_id": payment_id,
            "platform": payment.platform,
            "amount_usd": payment.amount_usd,
            "processed_at": datetime.now(UTC).isoformat(),
            **results,
        }

    def _update_trust(self, payment: Any) -> dict[str, Any]:
        """Update trust metrics based on payment."""
        self.trust_engine.record_outcome(
            platform=payment.platform,
            accepted=True,
            paid=True,
            amount_usd=payment.amount_usd,
            time_to_payment_days=None,  # TODO: calculate from detected_at to confirmed_at
        )

        metrics = self.trust_engine.get_platform_trust(payment.platform)
        return {
            "platform": payment.platform,
            "trust_level": metrics.trust_level.value if metrics else "unknown",
            "success_rate": metrics.success_rate if metrics else 0.0,
            "payment_rate": metrics.payment_rate if metrics else 0.0,
        }

    def _update_profile(self, payment: Any) -> dict[str, Any]:
        """Update user profile with learning from payment."""
        # Create learning record
        category = self._infer_category(payment.platform)
        record = LearningRecord(
            platform=payment.platform,
            accepted=True,
            amount=payment.amount_usd,
            category=category,
            time_to_payout_days=None,
        )

        # Apply learning to profile
        apply_learning(self._default_profile, [record])

        return {
            "platform": payment.platform,
            "category": category.value if category else "unknown",
            "amount": payment.amount_usd,
        }

    def _infer_category(self, platform: str) -> OpportunityCategory | None:
        """Infer opportunity category from platform."""
        # Simple mapping - could be enhanced with platform-specific logic
        platform_category_map = {
            "hackerone": OpportunityCategory.BUG_BOUNTY,
            "bugcrowd": OpportunityCategory.BUG_BOUNTY,
            "intigriti": OpportunityCategory.BUG_BOUNTY,
            "opire": OpportunityCategory.DEV_BOUNTY,
            "freelancer": OpportunityCategory.WEB_SCRAPING,  # Default for freelancer
            "github": OpportunityCategory.OPEN_SOURCE,
            "outlier": OpportunityCategory.AI_EVALUATION,
        }
        return platform_category_map.get(platform.lower())

    def process_rejection(self, platform: str, opportunity_id: str, reason: str = "") -> dict[str, Any]:
        """Process a rejection and update trust metrics."""
        logger.info(f"[CLOSED_LOOP] Processing rejection: {platform} - {opportunity_id}")

        if self.config.auto_update_trust:
            self.trust_engine.record_outcome(platform=platform, accepted=False)

        return {
            "success": True,
            "platform": platform,
            "opportunity_id": opportunity_id,
            "reason": reason,
            "processed_at": datetime.now(UTC).isoformat(),
        }

    def get_recommendation_improvement(self) -> dict[str, Any]:
        """Get insights on how recommendations have improved from learning."""
        trust_status = self.trust_engine.get_status()
        payment_status = self.payment_tracker.get_status()

        return {
            "trust_status": trust_status,
            "payment_status": payment_status,
            "learning_active": self.config.auto_learn_from_payments,
            "profile_updates_enabled": self.config.auto_update_profile,
            "trust_updates_enabled": self.config.auto_update_trust,
        }

    def auto_approve_opportunity(self, platform: str, amount_usd: float) -> tuple[bool, str]:
        """Check if an opportunity can be auto-approved based on trust."""
        return self.trust_engine.can_auto_approve(platform, amount_usd)

    def get_status(self) -> dict[str, Any]:
        """Get overall status of the closed-loop system."""
        return {
            "config": {
                "auto_learn_from_payments": self.config.auto_learn_from_payments,
                "auto_update_trust": self.config.auto_update_trust,
                "auto_update_profile": self.config.auto_update_profile,
            },
            "recommendation_improvement": self.get_recommendation_improvement(),
        }


_manager: ClosedLoopManager | None = None


def get_closed_loop_manager() -> ClosedLoopManager:
    """Get the singleton ClosedLoopManager instance."""
    global _manager
    if _manager is None:
        _manager = ClosedLoopManager()
    return _manager
