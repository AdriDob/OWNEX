"""Smart Allocator — auto-asigna revenue de bug bounty a estrategias de inversión.

Cada vez que llega un payout de bug bounty, el Smart Allocator:
1. Toma el monto del payout
2. Reserva el emergency reserve (5%)
3. Distribuye el resto entre estrategias según su allocation_pct
4. Respeta límites de riesgo (25% max high-risk, 10% max speculative)
5. Notifica al usuario cuándo se ejecuta una asignación

Se integra con:
- RevenuePipeline (bug bounty payouts)
- InvestmentAllocationController
- NotificationHub (action_required para funding)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from core.investment.allocation import get_allocation_controller
from core.investment.models import (
    StrategyAllocation,
    StrategyProfile,
    get_all_strategies,
    get_strategy,
)

logger = logging.getLogger("orion.investment.smart_allocator")


class SmartAllocator:
    """Automatically allocates bug bounty revenue to investment strategies."""

    def __init__(self) -> None:
        self._allocation = get_allocation_controller()
        self._strategies = get_all_strategies()

    def allocate_payout(
        self,
        payout_amount: float,
        source: str = "",
        platform: str = "",
    ) -> dict[str, Any]:
        """Allocate a bug bounty payout across investment strategies.

        Returns a detailed breakdown of what was allocated where.
        """
        if payout_amount <= 0:
            return {"ok": False, "reason": "Payout amount must be positive"}

        config = self._allocation.config
        total_capital = config.total_capital_usd + payout_amount
        self._allocation.update_capital(total_capital)

        # Calculate reserve
        reserve = payout_amount * (config.emergency_reserve_pct / 100.0)
        remaining = payout_amount - reserve

        # Get active strategies
        active_strategies: list[StrategyProfile] = []
        for _sid, sdef in self._strategies.items():
            if sdef.status.value == "active":
                active_strategies.append(sdef)

        if not active_strategies:
            logger.warning("[SMART_ALLOCATOR] No active strategies — full amount to reserve")
            return {
                "ok": True,
                "payout": payout_amount,
                "allocated": 0.0,
                "reserve": reserve,
                "breakdown": [],
                "note": "No active strategies — amount added to reserve",
            }

        # Calculate risk limits
        max_high_risk = total_capital * (config.max_high_risk_pct / 100.0)
        max_speculative = total_capital * (config.max_speculative_pct / 100.0)

        # Current deployed amounts
        current_deployed: dict[str, float] = {}
        for sid, sa in self._allocation._strategies.items():
            current_deployed[sid] = sa.deployed_usd

        high_risk_deployed = sum(
            current_deployed.get(s.id, 0.0)
            for s in active_strategies
            if s.risk_level.value in ("aggressive", "speculative")
        )
        speculative_deployed = sum(
            current_deployed.get(s.id, 0.0) for s in active_strategies if s.risk_level.value == "speculative"
        )

        # Allocate to each strategy
        breakdown: list[dict[str, Any]] = []
        total_allocated = 0.0

        for sdef in active_strategies:
            if remaining <= 0:
                break

            # Max for this strategy based on its allocation_pct
            max_for_strategy = payout_amount * (sdef.max_allocation_pct / 100.0)

            # Apply risk limits
            if sdef.risk_level.value in ("aggressive", "speculative"):
                high_risk_room = max(0.0, max_high_risk - high_risk_deployed)
                max_for_strategy = min(max_for_strategy, high_risk_room)

            if sdef.risk_level.value == "speculative":
                spec_room = max(0.0, max_speculative - speculative_deployed)
                max_for_strategy = min(max_for_strategy, spec_room)

            # Don't go below min allocation
            if max_for_strategy < config.min_strategy_allocation_usd:
                continue

            # Allocate
            allocate_amount = min(max_for_strategy, remaining)
            if allocate_amount <= 0:
                continue

            # Update strategy allocation
            current = self._allocation._strategies.get(sdef.id)
            if current:
                current.allocated_usd += allocate_amount
                current.available_usd += allocate_amount
            else:
                self._allocation._strategies[sdef.id] = StrategyAllocation(
                    strategy_id=sdef.id,
                    allocated_usd=allocate_amount,
                    available_usd=allocate_amount,
                )

            remaining -= allocate_amount
            total_allocated += allocate_amount

            # Track risk deployment
            if sdef.risk_level.value in ("aggressive", "speculative"):
                high_risk_deployed += allocate_amount
            if sdef.risk_level.value == "speculative":
                speculative_deployed += allocate_amount

            breakdown.append(
                {
                    "strategy_id": sdef.id,
                    "strategy_name": sdef.name,
                    "amount": round(allocate_amount, 2),
                    "risk_level": sdef.risk_level.value,
                    "pct_of_payout": round(allocate_amount / payout_amount * 100, 1),
                }
            )

        # Save state
        self._allocation._save_state()

        result = {
            "ok": True,
            "payout": payout_amount,
            "source": source,
            "platform": platform,
            "allocated": round(total_allocated, 2),
            "reserve": round(reserve, 2),
            "remaining_unallocated": round(remaining, 2),
            "total_capital": round(total_capital, 2),
            "breakdown": breakdown,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        logger.info(
            "[SMART_ALLOCATOR] Payout $%.2f → allocated $%.2f to %d strategies, reserve $%.2f",
            payout_amount,
            total_allocated,
            len(breakdown),
            reserve,
        )

        # Notify about allocation
        self._notify_allocation(result)

        return result

    def _notify_allocation(self, result: dict[str, Any]) -> None:
        """Send notification about the allocation."""
        try:
            from cores.notifications.hub import get_hub

            breakdown_str = "\n".join(
                f"• {b['strategy_name']}: ${b['amount']:.2f} ({b['pct_of_payout']}%)" for b in result["breakdown"]
            )

            get_hub().notify(
                type_="assistant_recommendation",
                title=f"Smart Allocation: ${result['allocated']:.2f} deployed",
                message=(
                    "Payout allocated automatically:\n"
                    f"{breakdown_str}\n"
                    f"\nReserve: ${result['reserve']:.2f}\n"
                    f"Total capital: ${result['total_capital']:.2f}"
                ),
                severity="info",
                priority="low",
                channels=["web"],
                metadata={"allocation_result": result},
            )
        except Exception as e:
            logger.debug("Notification skipped: %s", e)

    def get_allocation_summary(self) -> dict[str, Any]:
        """Get current allocation state across all strategies."""
        config = self._allocation.config
        strategies = {}

        for sid, sa in self._allocation._strategies.items():
            sdef = get_strategy(sid)
            strategies[sid] = {
                "name": sdef.name if sdef else sid,
                "allocated": sa.allocated_usd,
                "deployed": sa.deployed_usd,
                "available": sa.available_usd,
                "pnl": sa.pnl_usd,
                "roi": sa.roi_pct,
            }

        return {
            "total_capital": config.total_capital_usd,
            "emergency_reserve": config.emergency_reserve_amount(),
            "available_for_investment": config.available_for_investment(),
            "strategies": strategies,
        }


def get_smart_allocator() -> SmartAllocator:
    """Get singleton SmartAllocator instance."""
    if not hasattr(get_smart_allocator, "_instance"):
        get_smart_allocator._instance = SmartAllocator()
    return get_smart_allocator._instance
