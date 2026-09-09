"""Rastro Full Auto Integration — conecta todos los módulos automáticos.

Este es el orquestador final que conecta:
1. Auto-Discovery → encuentra targets
2. Auto-AI-Worker → procesa tareas (Pulse, Forge)
3. Auto-Submission → envía a plataformas
4. Smart-Allocator → asigna revenue
5. Risk-Guardian → protege drawdown
6. Auto-Tax → registra ingresos
7. Auto-Optimizer → aprende y mejora
8. Auto-Email → gestiona comunicaciones
9. Auto-Withdraw → mueve fondos
10. Action-Required → notifica al usuario

Flujo completo:
  Discovery → AI Worker → Submission → Payout → Tax Record → Smart Allocate → Risk Guardian
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("orion.full_auto")


class RastroFullAuto:
    """Full autonomous income system — all modules connected."""

    async def process_opportunity(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        """Process an opportunity end-to-end through the full pipeline."""
        result = {
            "opportunity_id": opportunity.get("id"),
            "platform": opportunity.get("platform"),
            "type": opportunity.get("type"),
            "started_at": datetime.now(UTC).isoformat(),
        }

        try:
            # Step 1: AI Worker processes the opportunity
            from core.ai_worker import get_ai_worker

            worker = get_ai_worker()
            ai_result = await worker.auto_process_pulse_task(opportunity)
            result["ai_processing"] = ai_result

            # Step 2: Auto-Submit the result
            from core.auto_submission import get_submission_engine

            submission = get_submission_engine()
            sub_result = await submission.submit_bug_bounty(
                platform=opportunity.get("platform", ""),
                title=opportunity.get("title", "Finding"),
                description=str(ai_result),
                severity=opportunity.get("severity", "medium"),
            )
            result["submission"] = sub_result

            # Step 3: Record for tax tracking
            if sub_result.get("success"):
                from core.auto_tax import get_tax_tracker

                tax = get_tax_tracker()
                tax.record_income(
                    amount=opportunity.get("estimated_reward", 0),
                    currency="USD",
                    source=opportunity.get("type", "unknown"),
                    platform=opportunity.get("platform", "unknown"),
                )

            # Step 4: Record result for optimization
            from core.auto_optimizer import get_optimizer

            optimizer = get_optimizer()
            optimizer.record_result(
                {
                    "platform": opportunity.get("platform"),
                    "source": opportunity.get("type"),
                    "success": sub_result.get("success"),
                    "revenue": opportunity.get("estimated_reward", 0),
                }
            )

        except Exception as e:
            result["error"] = str(e)
            logger.error("[FULL_AUTO] Error processing opportunity: %s", e)

        result["completed_at"] = datetime.now(UTC).isoformat()
        return result

    async def run_full_cycle(self) -> dict[str, Any]:
        """Run a full autonomous cycle."""
        cycle_result = {
            "started_at": datetime.now(UTC).isoformat(),
            "steps": {},
        }

        try:
            # Step 1: Run startup checks
            from cores.startup_checks import run_all_checks

            checks = run_all_checks()
            cycle_result["steps"]["startup_checks"] = checks

            # Step 2: Risk guardian check
            from core.investment.risk_guardian import get_risk_guardian

            guardian = get_risk_guardian()
            risk = guardian.check_all_strategies()
            cycle_result["steps"]["risk_guardian"] = risk

            # Step 3: Tax tracking summary
            from core.auto_tax import get_tax_tracker

            tax = get_tax_tracker()
            monthly = tax.get_monthly_summary()
            cycle_result["steps"]["tax_summary"] = monthly

            # Step 4: Optimization analysis
            from core.auto_optimizer import get_optimizer

            optimizer = get_optimizer()
            analysis = optimizer.analyze_performance(30)
            cycle_result["steps"]["optimization"] = analysis

            # Step 5: Smart allocation summary
            from core.investment.smart_allocator import get_smart_allocator

            allocator = get_smart_allocator()
            alloc_summary = allocator.get_allocation_summary()
            cycle_result["steps"]["allocation"] = alloc_summary

            # Step 6: Submission stats
            from core.auto_submission import get_submission_engine

            submission = get_submission_engine()
            sub_stats = submission.tracker.get_stats()
            cycle_result["steps"]["submissions"] = sub_stats

        except Exception as e:
            cycle_result["error"] = str(e)
            logger.error("[FULL_AUTO] Cycle error: %s", e)

        cycle_result["completed_at"] = datetime.now(UTC).isoformat()
        return cycle_result

    async def on_payout_received(
        self,
        amount: float,
        platform: str,
        source: str,
    ) -> dict[str, Any]:
        """Handle a payout event — full pipeline."""
        result = {
            "amount": amount,
            "platform": platform,
            "source": source,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Step 1: Record income for tax
        from core.auto_tax import get_tax_tracker

        tax = get_tax_tracker()
        tax.record_income(amount, "USD", source, platform)
        result["tax_recorded"] = True

        # Step 2: Smart allocation
        from core.investment.smart_allocator import get_smart_allocator

        allocator = get_smart_allocator()
        alloc_result = allocator.allocate_payout(amount, source, platform)
        result["allocation"] = alloc_result

        # Step 3: Notify via action required (low priority — info only)
        try:
            from cores.notifications.hub import get_hub

            get_hub().notify(
                type="assistant_recommendation",
                title=f"Payout received: ${amount:.2f} from {platform}",
                message=f"Allocated: ${alloc_result.get('allocated', 0):.2f} to strategies",
                severity="success",
                priority="low",
                channels=["web"],
            )
        except Exception:
            pass

        return result

    async def on_action_required(
        self,
        title: str,
        reason: str,
        steps: list[str],
        platform: str,
    ) -> dict[str, Any]:
        """Send an action-required notification to the user."""
        from cores.notifications.action_required import notify_action_required

        action = notify_action_required(
            title=title,
            reason=reason,
            impact=f"Action required for {platform}",
            steps=steps,
            ui_path="/reports/action-required",
            category="action",
            priority="high",
            channels=["web", "desktop"],
            subject_id=platform,
            subject_type="platform",
        )

        return {"notified": True, "action_id": action.id}


_full_auto: RastroFullAuto | None = None


def get_full_auto() -> RastroFullAuto:
    """Get singleton RastroFullAuto."""
    global _full_auto
    if _full_auto is None:
        _full_auto = RastroFullAuto()
    return _full_auto
