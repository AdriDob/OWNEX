"""Risk Guardian — protección automática de drawdown para inversiones.

Monitorea continuamente las estrategias de inversión y:
1. Pausa estrategias que exceden max_drawdown_pct
2. Pausa estrategias con consecutive_losses >= threshold
3. Auto-resume cuando condiciones mejoran (drawdown recovery)
4. Notifica al usuario de acciones tomadas
5. Nunca arriesga más del 25% en high-risk (enforced)

Se ejecuta periódicamente via LifeScheduler.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from core.investment.manager import InvestmentManager
from core.investment.metrics import get_investment_metrics
from core.investment.models import StrategyStatus, get_all_strategies

logger = logging.getLogger("orion.investment.risk_guardian")


class RiskGuardian:
    """Monitors and protects investment strategies from excessive losses."""

    def __init__(self) -> None:
        self._manager = InvestmentManager()
        self._metrics = get_investment_metrics()
        self._strategies = get_all_strategies()

    def check_all_strategies(self) -> dict[str, Any]:
        """Run risk checks on all active strategies."""
        results = {
            "checked": 0,
            "paused": [],
            "resumed": [],
            "warnings": [],
            "healthy": [],
            "timestamp": datetime.now(UTC).isoformat(),
        }

        for sid, sdef in self._strategies.items():
            if sdef.status == StrategyStatus.STOPPED:
                continue

            results["checked"] += 1

            # Get strategy metrics
            metrics = self._metrics.get_strategy_metrics(sid)

            # Check if should pause
            if metrics.should_pause and not self._manager.is_strategy_paused(sid):
                self._pause_strategy(sid, metrics, results)

            # Check if should resume (recovered from drawdown)
            elif self._manager.is_strategy_paused(sid) and not metrics.should_pause:
                self._resume_strategy(sid, metrics, results)

            # Check warning threshold (80% of max drawdown)
            elif (
                metrics.max_drawdown_pct > 0
                and metrics.current_drawdown_pct >= metrics.max_drawdown_pct * 0.8
                and not self._manager.is_strategy_paused(sid)
            ):
                results["warnings"].append(
                    {
                        "strategy_id": sid,
                        "name": sdef.name,
                        "drawdown_pct": metrics.current_drawdown_pct,
                        "max_drawdown_pct": metrics.max_drawdown_pct,
                        "message": f"Approaching max drawdown ({metrics.current_drawdown_pct:.1f}% / {metrics.max_drawdown_pct:.1f}%)",
                    }
                )

            else:
                results["healthy"].append(
                    {
                        "strategy_id": sid,
                        "name": sdef.name,
                        "drawdown_pct": metrics.current_drawdown_pct,
                        "consecutive_losses": metrics.consecutive_losses,
                    }
                )

        if results["paused"] or results["resumed"]:
            logger.warning(
                "[RISK_GUARDIAN] Paused: %d, Resumed: %d, Warnings: %d",
                len(results["paused"]),
                len(results["resumed"]),
                len(results["warnings"]),
            )

        return results

    def _pause_strategy(self, sid: str, metrics: Any, results: dict[str, Any]) -> None:
        """Pause a strategy and notify."""
        reason = []
        if metrics.max_drawdown_pct > 0 and metrics.current_drawdown_pct >= metrics.max_drawdown_pct * 0.9:
            reason.append(f"drawdown {metrics.current_drawdown_pct:.1f}% >= max {metrics.max_drawdown_pct:.1f}%")
        if metrics.consecutive_losses >= 5:
            reason.append(f"{metrics.consecutive_losses} consecutive losses")

        self._manager.pause_strategy(sid)
        results["paused"].append(
            {
                "strategy_id": sid,
                "name": self._strategies.get(sid, {}).name if sid in self._strategies else sid,
                "reason": "; ".join(reason),
                "drawdown_pct": metrics.current_drawdown_pct,
                "consecutive_losses": metrics.consecutive_losses,
            }
        )

        # Notify
        try:
            from cores.notifications.action_required import notify_action_required

            sdef = self._strategies.get(sid)
            notify_action_required(
                title=f"Strategy paused: {sdef.name if sdef else sid}",
                reason=f"Auto-paused due to: {'; '.join(reason)}",
                impact="Strategy halted — no new trades until manually resumed or conditions improve",
                steps=[
                    "Go to Investment Hub > Strategies",
                    f"Review {sdef.name if sdef else sid} performance",
                    "If issue resolved, click 'Resume'",
                    "Or adjust risk parameters if needed",
                ],
                ui_path="/investments?tab=strategies",
                category="approval",
                priority="high",
                channels=["web", "desktop"],
                subject_id=sid,
                subject_type="strategy",
            )
        except Exception as e:
            logger.debug("Notification skipped: %s", e)

    def _resume_strategy(self, sid: str, metrics: Any, results: dict[str, Any]) -> None:
        """Resume a strategy and notify."""
        self._manager.resume_strategy(sid)
        results["resumed"].append(
            {
                "strategy_id": sid,
                "name": self._strategies.get(sid, {}).name if sid in self._strategies else sid,
                "reason": "Drawdown recovered",
                "drawdown_pct": metrics.current_drawdown_pct,
            }
        )

        # Notify
        try:
            from cores.notifications.hub import get_hub

            sdef = self._strategies.get(sid)
            get_hub().notify(
                type_="assistant_recommendation",
                title=f"Strategy resumed: {sdef.name if sdef else sid}",
                message=f"Drawdown recovered to {metrics.current_drawdown_pct:.1f}% — strategy auto-resumed",
                severity="success",
                priority="low",
                channels=["web"],
            )
        except Exception:
            pass

    def get_risk_report(self) -> dict[str, Any]:
        """Get comprehensive risk report for all strategies."""
        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "global_paused": self._manager.is_paused,
            "drawdown_protection": self._manager.drawdown_protection,
            "strategies": [],
            "summary": {
                "total": 0,
                "active": 0,
                "paused": 0,
                "in_drawdown": 0,
            },
        }

        for sid, sdef in self._strategies.items():
            if sdef.status == StrategyStatus.STOPPED:
                continue

            metrics = self._metrics.get_strategy_metrics(sid)
            is_paused = self._manager.is_strategy_paused(sid)
            in_drawdown = metrics.current_drawdown_pct > 0 and metrics.is_drawdown

            report["strategies"].append(
                {
                    "id": sid,
                    "name": sdef.name,
                    "risk_level": sdef.risk_level.value,
                    "status": "paused" if is_paused else "active",
                    "drawdown_pct": metrics.current_drawdown_pct,
                    "max_drawdown_pct": metrics.max_drawdown_pct,
                    "consecutive_losses": metrics.consecutive_losses,
                    "win_rate": metrics.win_rate,
                    "total_trades": metrics.total_trades,
                    "sharpe_ratio": metrics.sharpe_ratio,
                    "in_drawdown": in_drawdown,
                    "should_pause": metrics.should_pause,
                    "is_healthy": metrics.is_healthy,
                }
            )

            report["summary"]["total"] += 1
            if is_paused:
                report["summary"]["paused"] += 1
            else:
                report["summary"]["active"] += 1
            if in_drawdown:
                report["summary"]["in_drawdown"] += 1

        return report


def get_risk_guardian() -> RiskGuardian:
    """Get singleton RiskGuardian instance."""
    if not hasattr(get_risk_guardian, "_instance"):
        get_risk_guardian._instance = RiskGuardian()
    return get_risk_guardian._instance
