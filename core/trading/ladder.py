"""Patrimonial Ladder Engine — Manages the patrimonial ladder progression.

Handles:
- Current level detection based on net worth
- Progress tracking toward next level
- Capital gates validation
- Level advancement with human approval
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.trading.contracts import (
    LADDER_LEVELS,
    CapitalGates,
    LadderLevel,
    PatrimonialLevel,
    PatrimonyConfig,
)

logger = logging.getLogger("ownex.trading.ladder")


@dataclass(slots=True)
class LadderSnapshot:
    """Current ladder state snapshot."""

    current_level: PatrimonialLevel
    level_name: str
    net_worth: Decimal
    level_min: Decimal
    level_max: Decimal | None
    progress_pct: Decimal
    progress_to_next: Decimal
    next_level: PatrimonialLevel | None
    next_level_name: str | None
    next_level_min: Decimal | None
    amount_to_next: Decimal | None
    capital_gates: CapitalGates
    months_at_current_level: int
    can_advance: bool


class PatrimonialLadderEngine:
    """Manages the patrimonial ladder progression."""

    def __init__(self, config: PatrimonyConfig | None = None):
        self.config = config or PatrimonyConfig()
        self._levels = {level.level: level for level in LADDER_LEVELS}
        self._level_order = [level.level for level in LADDER_LEVELS]
        logger.info("PatrimonialLadderEngine initialized")

    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # LEVEL DETECTION & PROGRESS
    # ══════════════════════════════════════════════════════════════════════════════════════════════════

    def get_level_for_net_worth(self, net_worth: Decimal) -> PatrimonialLevel:
        """Determine the patrimonial level for a given net worth."""
        for level in reversed(LADDER_LEVELS):
            if net_worth >= level.min_net_worth:
                return level.level
        return PatrimonialLevel.LEVEL_0_VALIDATION

    def get_level_info(self, level: PatrimonialLevel) -> LadderLevel:
        """Get level definition."""
        return self._levels[level]

    def calculate_progress(
        self,
        net_worth: Decimal,
        current_level: PatrimonialLevel | None = None,
    ) -> tuple[Decimal, Decimal | None, Decimal | None]:
        """
        Calculate progress within current level.

        Returns: (progress_pct, amount_to_next, next_level_min)
        """
        if current_level is None:
            current_level = self.get_level_for_net_worth(net_worth)

        level_info = self._levels[current_level]
        level_min = level_info.min_net_worth
        level_max = level_info.max_net_worth

        if level_max is None:
            # Top level - no upper bound
            return Decimal("100"), None, None

        level_range = level_max - level_min
        if level_range <= 0:
            return Decimal("100"), None, None

        progress = net_worth - level_min
        progress_pct = (progress / level_range) * Decimal("100")
        progress_pct = max(Decimal("0"), min(Decimal("100"), progress_pct))

        amount_to_next = level_max - net_worth

        return progress_pct, amount_to_next, level_info.max_net_worth

    def get_ladder_snapshot(self, net_worth: Decimal, months_at_level: int = 0) -> LadderSnapshot:
        """Get complete ladder state snapshot."""
        current_level = self.get_level_for_net_worth(net_worth)
        level_info = self._levels[current_level]

        progress_pct, amount_to_next, next_level_min = self.calculate_progress(net_worth, current_level)

        # Determine next level
        current_idx = self._level_order.index(current_level)
        next_level = self._level_order[current_idx + 1] if current_idx + 1 < len(self._level_order) else None
        next_level_name = self._levels[next_level].name if next_level else None

        # Calculate months at current level
        months_at_level = months_at_level

        # Check capital gates
        capital_gates = self.check_capital_gates(net_worth, months_at_level)

        can_advance = capital_gates.can_advance

        # Determine next level
        current_idx = self._level_order.index(current_level)
        next_level = self._level_order[current_idx + 1] if current_idx + 1 < len(self._level_order) else None
        next_level_name = self._levels[next_level].name if next_level else None

        return LadderSnapshot(
            current_level=current_level,
            level_name=self._levels[current_level].name,
            net_worth=net_worth,
            level_min=self._levels[current_level].min_net_worth,
            level_max=self._levels[current_level].max_net_worth,
            progress_pct=progress_pct,
            progress_to_next=progress_pct,
            next_level=next_level,
            next_level_name=next_level_name,
            next_level_min=next_level_min,
            amount_to_next=amount_to_next,
            capital_gates=capital_gates,
            months_at_current_level=months_at_level,
            can_advance=can_advance,
        )

    # ═════════════════════════════════════════════════════════════════════════════════════════════════════
    # CAPITAL GATES
    # ════════════════════════════════════════════════════════════════════════════════════════════════════

    def check_capital_gates(
        self,
        net_worth: Decimal,
        months_at_level: int,
        drawdown_pct: Decimal = Decimal("0"),
        liquidity_usd: Decimal = Decimal("0"),
        monthly_revenue_usd: Decimal = Decimal("0"),
        current_leverage: Decimal = Decimal("1"),
        max_position_pct: Decimal = Decimal("0"),
    ) -> CapitalGates:
        """Check if all capital gates are satisfied for current level."""
        current_level = self.get_level_for_net_worth(net_worth)
        level_info = self._levels[current_level]

        blocking_reasons = []
        warnings = []

        # Check drawdown
        if drawdown_pct > level_info.min_drawdown_pct:
            blocking_reasons.append(f"Drawdown {drawdown_pct:.1%} exceeds limit {level_info.min_drawdown_pct:.1%}")

        # Check liquidity
        if liquidity_usd < level_info.min_liquidity_usd:
            blocking_reasons.append(
                f"Liquidity ${liquidity_usd:,.0f} below minimum ${level_info.min_liquidity_usd:,.0f}"
            )

        # Check monthly revenue
        if monthly_revenue_usd < level_info.min_monthly_revenue_usd:
            blocking_reasons.append(
                f"Monthly revenue ${monthly_revenue_usd:,.0f} below minimum ${level_info.min_monthly_revenue_usd:,.0f}"
            )

        # Check leverage
        if current_leverage > level_info.max_leverage:
            blocking_reasons.append(f"Leverage {current_leverage:.1f}x exceeds limit {level_info.max_leverage:.1f}x")

        # Check months at level
        if months_at_level < level_info.required_months_at_level:
            blocking_reasons.append(
                f"Only {months_at_level} months at level, minimum {level_info.required_months_at_level}"
            )

        # Warnings (non-blocking)
        if drawdown_pct > level_info.min_drawdown_pct * Decimal("0.8"):
            warnings.append(f"Drawdown approaching limit ({drawdown_pct:.1%} / {level_info.min_drawdown_pct:.1%})")

        if liquidity_usd < level_info.min_liquidity_usd * Decimal("1.5"):
            warnings.append(
                f"Liquidity buffer thin (${liquidity_usd:,.0f} / ${level_info.min_liquidity_usd * Decimal('1.5'):,.0f})"
            )

        if monthly_revenue_usd < level_info.min_monthly_revenue_usd * Decimal("1.2"):
            warnings.append(
                f"Revenue close to minimum ({monthly_revenue_usd:,.0f} / {level_info.min_monthly_revenue_usd * Decimal('1.2'):,.0f})"
            )

        # Next level info
        current_idx = self._level_order.index(current_level)
        next_level = self._level_order[current_idx + 1] if current_idx + 1 < len(self._level_order) else None

        return CapitalGates(
            level=current_level,
            can_advance=len(blocking_reasons) == 0,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
            next_level=next_level,
            progress_pct=Decimal("0"),
        )

    # ══════════════════════════════════════════════════════════════════════════════════════════════════════
    # LEVEL ADVANCEMENT
    # ═════════════════════════════════════════════════════════════════════════════════════════════════════

    def can_advance_level(
        self,
        net_worth: Decimal,
        months_at_level: int,
        drawdown_pct: Decimal = Decimal("0"),
        liquidity_usd: Decimal = Decimal("0"),
        monthly_revenue_usd: Decimal = Decimal("0"),
        current_leverage: Decimal = Decimal("1"),
        max_position_pct: Decimal = Decimal("0"),
        human_approved: bool = False,
    ) -> tuple[bool, list[str]]:
        """Check if can advance to next level."""
        current_level = self.get_level_for_net_worth(net_worth)

        # Check if already at max level
        current_idx = self._level_order.index(self.get_level_for_net_worth(net_worth))
        if current_idx + 1 >= len(self._level_order):
            return False, ["Already at maximum level"]

        # Check net worth qualifies for next level
        next_level = self._level_order[current_idx + 1]
        next_level_info = self._levels[next_level]
        if net_worth < next_level_info.min_net_worth:
            return False, [
                f"Net worth ${net_worth:,.0f} below next level minimum ${next_level_info.min_net_worth:,.0f}"
            ]

        # Check capital gates
        gates = self.check_capital_gates(
            net_worth, months_at_level, drawdown_pct, Decimal("0"), monthly_revenue_usd, Decimal("1"), Decimal("0")
        )

        if not gates.can_advance:
            return False, gates.blocking_reasons

        # Check human approval requirement
        if self.config.require_human_approval_to_advance and not human_approved:
            return False, ["Human approval required to advance level"]

        return True, []

    def advance_level(
        self,
        net_worth: Decimal,
        months_at_level: int,
        drawdown_pct: Decimal = Decimal("0"),
        liquidity_usd: Decimal = Decimal("0"),
        monthly_revenue_usd: Decimal = Decimal("0"),
        current_leverage: Decimal = Decimal("1"),
        max_position_pct: Decimal = Decimal("0"),
        human_approved: bool = False,
    ) -> tuple[bool, PatrimonialLevel | None, list[str]]:
        """Attempt to advance to next level."""
        can_advance, reasons = self.can_advance_level(
            net_worth,
            months_at_level,
            drawdown_pct,
            liquidity_usd,
            monthly_revenue_usd,
            current_leverage,
            Decimal("0"),
            human_approved,
        )

        if not can_advance:
            return False, None, reasons

        current_level = self.get_level_for_net_worth(net_worth)
        current_idx = self._level_order.index(current_level)
        next_level = self._level_order[current_idx + 1]

        logger.info(f"Advanced from {current_level.value} to {next_level.value}")
        return True, next_level, []

    # ═════════════════════════════════════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════

    def get_all_levels(self) -> list[LadderLevel]:
        """Get all ladder levels in order."""
        return list(LADDER_LEVELS)

    def get_level_summary(self, level: PatrimonialLevel) -> dict[str, Any]:
        """Get human-readable level summary."""
        info = self._levels[level]
        return {
            "level": level.value,
            "name": info.name,
            "range": f"${info.min_net_worth:,.0f}" + (f" - ${info.max_net_worth:,.0f}" if info.max_net_worth else "+"),
            "description": info.description,
            "gates": {
                "max_drawdown": f"{info.min_drawdown_pct:.0%}",
                "min_liquidity": f"${info.min_liquidity_usd:,.0f}",
                "min_monthly_revenue": f"${info.min_monthly_revenue_usd:,.0f}",
                "max_leverage": f"{info.max_leverage:.1f}x",
                "max_position_pct": f"{info.max_single_position_pct:.0%}",
                "min_months": info.required_months_at_level,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

_ladder_engine: PatrimonialLadderEngine | None = None


def get_ladder_engine(config: PatrimonyConfig | None = None) -> PatrimonialLadderEngine:
    """Get the global ladder engine singleton."""
    global _ladder_engine
    if _ladder_engine is None:
        _ladder_engine = PatrimonialLadderEngine(config)
    return _ladder_engine
