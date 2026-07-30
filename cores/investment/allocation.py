from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from core.investment.models import (
    AllocationConfig,
    InvestmentSnapshot,
    StrategyAllocation,
    StrategyProfile,
    get_strategy,
)

logger = logging.getLogger("orion.investment.allocation")


def _data_dir() -> Path:
    return Path.home() / ".orion" / "investment"


def _allocation_file() -> Path:
    return _data_dir() / "allocation_state.json"


class RevenueAllocationController:
    """Controls revenue allocation from bug bounty payouts to investment strategies.

    Implements the 25% max rule: no more than 25% of total capital goes to
    high-risk/speculative strategies. Allocation is dynamic based on actual
    payouts received via the RevenuePipeline.
    """

    def __init__(self, config: AllocationConfig | None = None) -> None:
        self._config = config or AllocationConfig()
        self._lock = Lock()
        self._strategies: dict[str, StrategyAllocation] = {}
        self._event_history: list[dict[str, Any]] = []
        _data_dir().mkdir(parents=True, exist_ok=True)
        self._load_state()

    @property
    def config(self) -> AllocationConfig:
        return self._config

    def update_capital(self, total_usd: float) -> None:
        with self._lock:
            self._config.total_capital_usd = total_usd
            self._save_state()
            logger.info("Total capital updated: $%.2f", total_usd)

    def allocate_payout(self, payout_amount: float, source: str = "") -> dict[str, Any]:
        """Allocate a bug bounty payout across investment strategies.

        Returns allocation breakdown showing how much went to each strategy,
        how much to reserve, and how much is available for deployment.
        """
        with self._lock:
            from core.investment.models import STRATEGY_REGISTRY

            max_high_risk = self._config.max_high_risk_amount()
            max_spec = self._config.max_speculative_amount()

            strategies: list[StrategyProfile] = []
            for sid in list(self._strategies.keys()) or [s.id for s in STRATEGY_REGISTRY]:
                sdef = get_strategy(sid)
                if sdef:
                    strategies.append(sdef)

            high_risk_current = sum(
                sa.deployed_usd
                for sa in self._strategies.values()
                for s in strategies
                if sa.strategy_id == s.id and s.risk_level.value in ("aggressive", "speculative")
            )

            speculative_current = sum(
                sa.deployed_usd
                for sa in self._strategies.values()
                for s in strategies
                if sa.strategy_id == s.id and s.risk_level.value == "speculative"
            )

            allocation: dict[str, float] = {}
            remaining = payout_amount

            reserve = payout_amount * (self._config.emergency_reserve_pct / 100.0)
            remaining -= reserve

            for sdef in strategies:
                if remaining <= 0:
                    break
                max_for_strategy = payout_amount * (sdef.max_allocation_pct / 100.0)

                if sdef.risk_level.value in ("aggressive", "speculative"):
                    high_risk_room = max(0.0, max_high_risk - high_risk_current)
                    max_for_strategy = min(max_for_strategy, high_risk_room)

                if sdef.risk_level.value == "speculative":
                    spec_room = max(0.0, max_spec - speculative_current)
                    max_for_strategy = min(max_for_strategy, spec_room)

                alloc = min(max_for_strategy, remaining)
                if alloc < self._config.min_strategy_allocation_usd:
                    continue

                allocation[sdef.id] = alloc
                remaining -= alloc

                sa = self._strategies.get(sdef.id)
                if sa:
                    sa.allocated_usd += alloc
                    sa.available_usd += alloc
                else:
                    self._strategies[sdef.id] = StrategyAllocation(
                        strategy_id=sdef.id,
                        allocated_usd=alloc,
                        available_usd=alloc,
                    )

            if s := self._strategies.get("emergency_reserve"):
                s.allocated_usd += reserve
                s.available_usd += reserve
            else:
                self._strategies["emergency_reserve"] = StrategyAllocation(
                    strategy_id="emergency_reserve",
                    allocated_usd=reserve,
                    available_usd=reserve,
                )

            unallocated = remaining
            if unallocated > 0 and (s := self._strategies.get("emergency_reserve")):
                s.allocated_usd += unallocated
                s.available_usd += unallocated

            self._event_history.append(
                {
                    "type": "payout_allocated",
                    "amount": payout_amount,
                    "source": source,
                    "allocation": allocation,
                    "reserve": reserve,
                    "unallocated": unallocated,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
            self._save_state()

            logger.info(
                "Allocated $%.2f payout: strategies=%s reserve=$%.2f unallocated=$%.2f",
                payout_amount,
                allocation,
                reserve,
                unallocated,
            )
            return {
                "allocated": allocation,
                "reserve": round(reserve, 2),
                "unallocated": round(unallocated, 2),
                "total": round(payout_amount, 2),
            }

    def snapshot(self) -> InvestmentSnapshot:
        with self._lock:
            total_capital = self._config.total_capital_usd
            deployed = sum(s.deployed_usd for s in self._strategies.values())
            available = sum(s.available_usd for s in self._strategies.values())
            total_pnl = sum(s.pnl_usd for s in self._strategies.values())

            return InvestmentSnapshot(
                total_capital=total_capital,
                deployed=deployed,
                available=available,
                total_pnl=total_pnl,
                total_pnl_pct=round(total_pnl / max(total_capital, 1) * 100, 2),
                strategies=dict(self._strategies),
            )

    def deploy_capital(self, strategy_id: str, amount: float) -> bool:
        with self._lock:
            sa = self._strategies.get(strategy_id)
            if not sa or sa.available_usd < amount:
                return False
            sa.deployed_usd += amount
            sa.available_usd -= amount
            sa.last_rebalanced = datetime.now(UTC).isoformat()
            self._save_state()
            return True

    def record_pnl(self, strategy_id: str, pnl: float) -> None:
        with self._lock:
            sa = self._strategies.get(strategy_id)
            if not sa:
                return
            sa.pnl_usd += pnl
            base = sa.allocated_usd - sa.pnl_usd + pnl
            sa.pnl_pct = round(sa.pnl_usd / max(base, 1) * 100, 2)
            sa.roi_pct = round((sa.pnl_usd / max(sa.allocated_usd, 1)) * 100, 2)
            self._save_state()

    def get_strategy_allocation(self, strategy_id: str) -> StrategyAllocation | None:
        with self._lock:
            return self._strategies.get(strategy_id)

    def get_high_risk_exposure(self) -> dict[str, Any]:
        total = self._config.total_capital_usd
        high_risk = sum(
            sa.deployed_usd
            for sid, sa in self._strategies.items()
            if (s := get_strategy(sid)) and s.risk_level.value in ("aggressive", "speculative")
        )
        return {
            "total_capital": total,
            "high_risk_deployed": high_risk,
            "high_risk_pct": round(high_risk / max(total, 1) * 100, 1),
            "max_allowed_pct": self._config.max_high_risk_pct,
            "max_allowed_amount": self._config.max_high_risk_amount(),
            "headroom": max(0.0, self._config.max_high_risk_amount() - high_risk),
            "within_limit": high_risk <= self._config.max_high_risk_amount(),
        }

    def get_event_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return sorted(self._event_history, key=lambda e: e.get("timestamp", ""), reverse=True)[:limit]

    def _load_state(self) -> None:
        if not _allocation_file().exists():
            return
        try:
            data = json.loads(_allocation_file().read_text())
            if "total_capital_usd" in data:
                self._config.total_capital_usd = data["total_capital_usd"]
            self._strategies = {}
            for sid, sdata in data.get("strategies", {}).items():
                self._strategies[sid] = StrategyAllocation(**sdata)
            self._event_history = data.get("events", [])
            logger.debug("Loaded allocation state: $%.2f capital", self._config.total_capital_usd)
        except Exception as e:
            logger.warning("Failed to load allocation state: %s", e)

    def _save_state(self) -> None:
        try:
            _allocation_file().write_text(
                json.dumps(
                    {
                        "total_capital_usd": self._config.total_capital_usd,
                        "strategies": {k: v.__dict__ for k, v in self._strategies.items()},
                        "events": self._event_history[-500:],
                        "updated_at": datetime.now(UTC).isoformat(),
                    },
                    indent=2,
                    default=str,
                )
            )
        except Exception as e:
            logger.warning("Failed to save allocation state: %s", e)


_INSTANCE: RevenueAllocationController | None = None


def get_allocation_controller() -> RevenueAllocationController:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = RevenueAllocationController()
    return _INSTANCE


def reset_allocation_controller() -> None:
    global _INSTANCE
    _INSTANCE = None
