from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from core.investment.allocation import RevenueAllocationController, get_allocation_controller
from core.investment.metrics import InvestmentMetrics, get_investment_metrics
from core.investment.models import (
    InvestmentSnapshot,
    StrategyProfile,
    get_strategy,
)

logger = logging.getLogger("orion.investment.manager")


def _data_dir() -> Path:
    return Path.home() / ".orion" / "investment"


def _state_file() -> Path:
    return _data_dir() / "manager_state.json"


class InvestmentManager:
    """Central investment orchestrator.

    Manages risk, allocation, strategy lifecycle, and performance tracking
    across all investment strategies. Enforces the 25% high-risk max rule.
    """

    def __init__(
        self,
        allocation_controller: RevenueAllocationController | None = None,
        metrics: InvestmentMetrics | None = None,
    ) -> None:
        self._allocation = allocation_controller or get_allocation_controller()
        self._metrics = metrics or get_investment_metrics()
        self._lock = Lock()
        self._active_strategies: dict[str, dict[str, Any]] = {}
        self._paused_strategies: set[str] = set()
        self._global_paused = False
        self._drawdown_protection = True
        self._max_consecutive_losses = 5
        self._pause_on_drawdown_pct = 15.0
        _data_dir().mkdir(parents=True, exist_ok=True)
        self._load_state()

    @property
    def allocation(self) -> RevenueAllocationController:
        return self._allocation

    @property
    def metrics(self) -> InvestmentMetrics:
        return self._metrics

    @property
    def is_paused(self) -> bool:
        return self._global_paused

    @property
    def drawdown_protection(self) -> bool:
        return self._drawdown_protection

    def pause_all(self) -> None:
        with self._lock:
            self._global_paused = True
            self._save_state()
            logger.warning("INVESTMENT PAUSED — all strategies halted")

    def resume_all(self) -> None:
        with self._lock:
            self._global_paused = False
            self._save_state()
            logger.info("Investment resumed")

    def pause_strategy(self, strategy_id: str) -> bool:
        with self._lock:
            if strategy_id not in self._active_strategies:
                return False
            self._paused_strategies.add(strategy_id)
            self._save_state()
            logger.info("Strategy paused: %s", strategy_id)
            return True

    def resume_strategy(self, strategy_id: str) -> bool:
        with self._lock:
            self._paused_strategies.discard(strategy_id)
            self._save_state()
            logger.info("Strategy resumed: %s", strategy_id)
            return True

    def is_strategy_paused(self, strategy_id: str) -> bool:
        return strategy_id in self._paused_strategies or self._global_paused

    def can_deploy(self, strategy_id: str, amount: float) -> dict[str, Any]:
        if self._global_paused:
            return {"allowed": False, "reason": "Global pause active"}

        if self.is_strategy_paused(strategy_id):
            return {"allowed": False, "reason": "Strategy paused"}

        sdef = get_strategy(strategy_id)
        if not sdef:
            return {"allowed": False, "reason": "Unknown strategy"}

        risk_check = self._check_risk_limits(sdef)
        if not risk_check["allowed"]:
            return risk_check

        alloc = self._allocation.get_strategy_allocation(strategy_id)
        if not alloc or alloc.available_usd < amount:
            return {
                "allowed": False,
                "reason": f"Insufficient available capital. Have ${alloc.available_usd:.2f}, need ${amount:.2f}"
                if alloc
                else "No allocation for strategy",
            }

        exposure = self._allocation.get_high_risk_exposure()
        if sdef.risk_level.value in ("aggressive", "speculative") and not exposure["within_limit"]:
            return {"allowed": False, "reason": "High-risk allocation limit reached"}

        return {"allowed": True, "reason": "OK"}

    def deploy(self, strategy_id: str, amount: float) -> dict[str, Any]:
        check = self.can_deploy(strategy_id, amount)
        if not check["allowed"]:
            return {"success": False, "error": check["reason"]}

        success = self._allocation.deploy_capital(strategy_id, amount)
        if success:
            if strategy_id not in self._active_strategies:
                self._active_strategies[strategy_id] = {
                    "strategy_id": strategy_id,
                    "deployed_at": datetime.now(UTC).isoformat(),
                    "total_deployed": 0.0,
                    "total_withdrawn": 0.0,
                }
            self._active_strategies[strategy_id]["total_deployed"] += amount
            self._save_state()

            self._publish_event("capital_deployed", strategy_id, amount, f"Deployed ${amount:.2f} to {strategy_id}")

            return {"success": True, "strategy_id": strategy_id, "amount": amount}
        return {"success": False, "error": "Failed to deploy capital"}

    def record_trade_result(
        self,
        strategy_id: str,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        pnl: float,
        pnl_pct: float,
        fee: float = 0.0,
        duration_hours: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._metrics.record_trade(
            strategy_id=strategy_id,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            pnl=pnl,
            pnl_pct=pnl_pct,
            fee=fee,
            duration_hours=duration_hours,
            metadata=metadata,
        )

        self._allocation.record_pnl(strategy_id, pnl)

        self._publish_event(
            "trade_completed",
            strategy_id,
            pnl,
            f"{side.upper()} {symbol}: ${pnl:.2f} ({pnl_pct:+.2f}%)",
            metadata={"symbol": symbol, "side": side, "pnl_pct": pnl_pct},
        )

        sdef = get_strategy(strategy_id)
        if sdef and self._drawdown_protection:
            risk = self._metrics.get_strategy_metrics(strategy_id)
            if risk.should_pause:
                self.pause_strategy(strategy_id)
                logger.warning(
                    "Strategy %s auto-paused: %d consecutive losses, drawdown %.1f%%",
                    strategy_id,
                    risk.consecutive_losses,
                    risk.current_drawdown_pct,
                )
                return {"paused": True, "reason": "Risk limit reached"}

        return {"paused": False}

    def snapshot(self) -> InvestmentSnapshot:
        snap = self._allocation.snapshot()
        self._metrics.record_daily_snapshot(snap)
        return snap

    def risk_report(self) -> dict[str, Any]:
        all_metrics = self._metrics.get_all_strategy_metrics()
        exposure = self._allocation.get_high_risk_exposure()
        snap = self._allocation.snapshot()

        return {
            "global_paused": self._global_paused,
            "drawdown_protection": self._drawdown_protection,
            "paused_strategies": sorted(self._paused_strategies),
            "high_risk_exposure": exposure,
            "snapshot": snap.to_dict(),
            "strategies": {
                sid: {
                    "paused": sid in self._paused_strategies,
                    "risk_metrics": {
                        "sharpe": m.sharpe_ratio,
                        "win_rate": m.win_rate,
                        "profit_factor": m.profit_factor,
                        "drawdown_pct": m.current_drawdown_pct,
                        "max_drawdown_pct": m.max_drawdown_pct,
                        "is_drawdown": m.is_drawdown,
                        "should_pause": m.should_pause,
                        "is_healthy": m.is_healthy,
                        "total_trades": m.total_trades,
                        "consecutive_losses": m.consecutive_losses,
                    },
                    "allocation": (
                        self._allocation.get_strategy_allocation(sid).__dict__
                        if self._allocation.get_strategy_allocation(sid)
                        else {}
                    ),
                }
                for sid, m in all_metrics.items()
            },
            "consolidated_metrics": self._metrics.consolidated_metrics(),
            "pnl_chart": self._metrics.pnl_chart_data(days=30),
        }

    def update_config(self, **kwargs: Any) -> None:
        with self._lock:
            if "drawdown_protection" in kwargs:
                self._drawdown_protection = bool(kwargs["drawdown_protection"])
            if "max_consecutive_losses" in kwargs:
                self._max_consecutive_losses = int(kwargs["max_consecutive_losses"])
            if "pause_on_drawdown_pct" in kwargs:
                self._pause_on_drawdown_pct = float(kwargs["pause_on_drawdown_pct"])
            if "max_high_risk_pct" in kwargs:
                self._allocation.config.max_high_risk_pct = float(kwargs["max_high_risk_pct"])
            self._save_state()

    def activate_max_revenue_mode(self) -> dict[str, Any]:
        """Activate maximum revenue generation across all strategies.

        Deploys available capital proportionally to active strategies
        with risk-managed limits.
        """
        snap = self.snapshot()
        deployable = snap.available
        if deployable <= 0:
            return {"success": False, "reason": "No deployable capital available"}

        alloc_per_strategy = deployable / max(len(self._active_strategies) or 1, 1)
        results: list[dict[str, Any]] = []

        for sid in list(self._active_strategies.keys())[:3]:
            if self.is_strategy_paused(sid):
                continue
            result = self.deploy(sid, alloc_per_strategy * 0.5)
            results.append(result)

        return {
            "success": True,
            "deployed": deployable,
            "strategies_activated": len(results),
            "results": results,
        }

    def _simple_max_revenue_mode(self) -> dict[str, Any]:
        snap = self.snapshot()
        if snap.available <= 0:
            return {"success": False, "reason": "No deployable capital"}
        logger.info("Max revenue mode: $%.2f available for deployment", snap.available)
        return {"success": True, "available": snap.available}

    def _check_risk_limits(self, sdef: StrategyProfile) -> dict[str, Any]:
        risk = self._metrics.get_strategy_metrics(sdef.id)
        if risk.should_pause:
            return {"allowed": False, "reason": f"Strategy in drawdown: {risk.current_drawdown_pct:.1f}%"}
        if risk.current_drawdown_pct >= self._pause_on_drawdown_pct:
            return {"allowed": False, "reason": f"Drawdown limit reached: {risk.current_drawdown_pct:.1f}%"}
        return {"allowed": True, "reason": "OK"}

    def _publish_event(
        self, event_type: str, strategy_id: str, amount: float, description: str, metadata: dict[str, Any] | None = None
    ) -> None:
        try:
            from cores.events.event_bus import get_core_event_bus

            bus = get_core_event_bus()
            bus.publish(
                f"investment:{event_type}",
                strategy_id=strategy_id,
                amount=amount,
                description=description,
                metadata=metadata or {},
            )
        except Exception:
            pass

    def _load_state(self) -> None:
        if not _state_file().exists():
            return
        try:
            data = json.loads(_state_file().read_text())
            self._active_strategies = data.get("active_strategies", {})
            self._paused_strategies = set(data.get("paused_strategies", []))
            self._global_paused = data.get("global_paused", False)
            self._drawdown_protection = data.get("drawdown_protection", True)
            self._max_consecutive_losses = data.get("max_consecutive_losses", 5)
            self._pause_on_drawdown_pct = data.get("pause_on_drawdown_pct", 15.0)
            logger.debug("Loaded investment manager state")
        except Exception as e:
            logger.warning("Failed to load manager state: %s", e)

    def _save_state(self) -> None:
        try:
            _state_file().write_text(
                json.dumps(
                    {
                        "active_strategies": self._active_strategies,
                        "paused_strategies": sorted(self._paused_strategies),
                        "global_paused": self._global_paused,
                        "drawdown_protection": self._drawdown_protection,
                        "max_consecutive_losses": self._max_consecutive_losses,
                        "pause_on_drawdown_pct": self._pause_on_drawdown_pct,
                        "updated_at": datetime.now(UTC).isoformat(),
                    },
                    indent=2,
                )
            )
        except Exception as e:
            logger.warning("Failed to save manager state: %s", e)


_INSTANCE: InvestmentManager | None = None


def get_investment_manager() -> InvestmentManager:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = InvestmentManager()
    return _INSTANCE


def reset_investment_manager() -> None:
    global _INSTANCE
    _INSTANCE = None
