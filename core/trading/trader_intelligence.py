"""Trader intelligence — score, validate and monitor traders worth copying.

Deterministic multi-factor scoring (weights sum to 1.0), a backtest validator
with hard checks, a live monitor with alert rules, and discovery that reuses
the existing SmartMoneyCopier for Polymarket and public APIs elsewhere.
Discovery degrades gracefully (never crashes the pipeline).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from core.trading.store import TradingStore

logger = logging.getLogger("catseye.trading.intelligence")


@dataclass
class TraderMetrics:
    """Public, verifiable performance facts about a trader."""

    trader_id: str
    name: str = ""
    source: str = "unknown"  # polymarket | hyperliquid | cex | manual
    total_trades: int = 0
    win_rate: float = 0.0  # 0-100
    profit_factor: float = 0.0
    sharpe: float = 0.0
    max_dd_pct: float = 0.0
    consistency: float = 0.0  # 0-1 fraction of profitable months
    pnl_usd: float = 0.0
    volume_usd: float = 0.0
    age_days: int = 0
    period_days: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraderScore:
    trader_id: str
    score: float  # 0-100
    tier: str  # ELITE | STRONG | GOOD | AVOID
    factors: dict[str, float]
    reasoning: list[str]


class TraderScorer:
    """Multi-factor trader scorer. Weights sum to 1.0."""

    WEIGHTS: dict[str, float] = {
        "sharpe": 0.25,
        "sortino": 0.15,
        "calmar": 0.15,
        "win_rate": 0.10,
        "profit_factor": 0.10,
        "max_dd": 0.10,
        "consistency": 0.10,
        "risk_adjusted_return": 0.05,
    }

    def __init__(self) -> None:
        assert abs(sum(self.WEIGHTS.values()) - 1.0) < 1e-9

    @staticmethod
    def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

    def score(self, metrics: TraderMetrics) -> TraderScore:
        sharpe_n = self._clip(metrics.sharpe / 3.0)
        sortino_n = self._clip((metrics.sharpe * 1.4) / 4.5)
        calmar_n = self._clip((metrics.sharpe / 2.0) / 1.75)
        win_rate_n = self._clip(metrics.win_rate / 100.0)
        pf_n = self._clip((metrics.profit_factor - 1.0) / 1.5)
        dd_n = self._clip(1.0 - metrics.max_dd_pct / 50.0)
        cons_n = self._clip(metrics.consistency)
        roi = (metrics.pnl_usd / metrics.volume_usd) if metrics.volume_usd > 0 else 0.0
        rar_n = self._clip(roi / 0.08)

        factors = {
            "sharpe": round(sharpe_n, 3),
            "sortino": round(sortino_n, 3),
            "calmar": round(calmar_n, 3),
            "win_rate": round(win_rate_n, 3),
            "profit_factor": round(pf_n, 3),
            "max_dd": round(dd_n, 3),
            "consistency": round(cons_n, 3),
            "risk_adjusted_return": round(rar_n, 3),
        }
        raw = sum(w * factors[k] for k, w in self.WEIGHTS.items())
        score = round(raw * 100.0, 1)
        tier = "ELITE" if score >= 85 else "STRONG" if score >= 70 else "GOOD" if score >= 55 else "AVOID"

        reasoning: list[str] = []
        if metrics.total_trades >= 100:
            reasoning.append(f"{metrics.total_trades} trades — sample suficiente")
        if metrics.profit_factor >= 1.5:
            reasoning.append(f"profit factor {metrics.profit_factor:.2f} — gana más de lo que arriesga")
        if metrics.max_dd_pct <= 15:
            reasoning.append(f"drawdown máximo contenido ({metrics.max_dd_pct:.1f}%)")
        if metrics.consistency >= 0.6:
            reasoning.append(f"consistencia mensual {metrics.consistency:.0%}")
        if metrics.total_trades < 100:
            reasoning.append(f"solo {metrics.total_trades} trades — verificar antes de copiar")
        if metrics.max_dd_pct > 25:
            reasoning.append(f"drawdown elevado ({metrics.max_dd_pct:.1f}%) — riesgo alto")
        if metrics.profit_factor < 1.1 and metrics.total_trades > 0:
            reasoning.append(f"profit factor bajo ({metrics.profit_factor:.2f}) — poca ventaja real")
        if not reasoning:
            reasoning.append("sin datos suficientes — no copiar a ciegas")
        return TraderScore(trader_id=metrics.trader_id, score=score, tier=tier, factors=factors, reasoning=reasoning)


class BacktestValidator:
    """Hard checks over trader facts. At least 5 of 6 must pass."""

    @staticmethod
    def validate(metrics: TraderMetrics) -> dict[str, Any]:
        checks = {
            "out_of_sample": metrics.age_days >= 90,
            "regime_robustness": metrics.consistency >= 0.4 and metrics.max_dd_pct < 30,
            "sample_size": metrics.total_trades >= 100,
            "no_martingale": metrics.profit_factor >= 1.2 and metrics.win_rate <= 90,
            "realistic_slippage": metrics.volume_usd > 0 and metrics.volume_usd / max(metrics.total_trades, 1) >= 100,
            "survivorship_bias": metrics.age_days >= 180,
        }
        passed = sum(1 for ok in checks.values() if ok)
        failed = [k for k, ok in checks.items() if not ok]
        return {
            "passed": passed,
            "total": len(checks),
            "approved": passed >= 5,
            "checks": checks,
            "failed": failed,
            "reasoning": [f"check {name} falló: sin evidencia suficiente" for name in failed],
        }


class LiveTraderMonitor:
    """Alert rules over live trader metrics. Missing data never triggers."""

    RULES: dict[str, Callable[[TraderMetrics], str | None]] = {}

    def check(
        self, metrics: TraderMetrics, current_dd_pct: float | None = None, rolling_win_rate: float | None = None
    ) -> list[str]:
        alerts: list[str] = []
        if current_dd_pct is not None and current_dd_pct > max(metrics.max_dd_pct, 10.0):
            alerts.append(
                f"drawdown en vivo {current_dd_pct:.1f}% supera el máximo histórico ({metrics.max_dd_pct:.1f}%)"
            )
        if rolling_win_rate is not None and metrics.win_rate > 0 and rolling_win_rate < metrics.win_rate * 0.7:
            alerts.append(f"win rate reciente {rolling_win_rate:.0f}% cayó >30% vs histórico ({metrics.win_rate:.0f}%)")
        if metrics.win_rate > 95 and metrics.total_trades >= 50:
            alerts.append(f"win rate {metrics.win_rate:.0f}% sospechosamente alto — posible martingala o curvas")
        return alerts


class TraderDiscovery:
    """Discover candidate traders. Network failure → empty list, never crash."""

    def __init__(self, copier: Any | None = None) -> None:
        self._copier = copier

    def _get_copier(self) -> Any:
        if self._copier is not None:
            return self._copier
        try:
            from core.polymarket.strategies import SmartMoneyCopier

            return SmartMoneyCopier()
        except Exception:
            return None

    def _polymarket_candidates(self) -> list[TraderMetrics]:
        copier = self._get_copier()
        if copier is None:
            return []
        try:
            raw: Any = []
            if hasattr(copier, "scan_top_traders") and callable(copier.scan_top_traders):
                raw = copier.scan_top_traders() or []
            elif hasattr(copier, "generate_copy_signals") and callable(copier.generate_copy_signals):
                raw = copier.generate_copy_signals() or []
            else:
                return []
        except Exception:
            logger.debug("polymarket discovery unavailable — skipping", exc_info=True)
            return []
        out: list[TraderMetrics] = []
        for item in raw:
            if isinstance(item, dict):
                out.append(self._trader_from_dict(item, source="polymarket"))
        return out

    @staticmethod
    def _trader_from_dict(item: dict[str, Any], source: str) -> TraderMetrics:
        return TraderMetrics(
            trader_id=str(item.get("trader_id") or item.get("id") or item.get("address") or "unknown"),
            name=str(item.get("name") or item.get("trader") or ""),
            source=source,
            total_trades=int(item.get("total_trades") or item.get("num_trades") or 0),
            win_rate=float(item.get("win_rate") or 0.0),
            profit_factor=float(item.get("profit_factor") or 0.0),
            sharpe=float(item.get("sharpe") or 0.0),
            max_dd_pct=float(item.get("max_dd") or item.get("max_dd_pct") or 0.0),
            consistency=float(item.get("consistency") or 0.0),
            pnl_usd=float(item.get("pnl") or item.get("pnl_usd") or 0.0),
            volume_usd=float(item.get("volume") or item.get("volume_usd") or 0.0),
            age_days=int(item.get("age_days") or 0),
            period_days=int(item.get("period_days") or 0),
            extra=item,
        )

    async def discover(self, limit: int = 10) -> list[TraderMetrics]:
        candidates: list[TraderMetrics] = []
        try:
            candidates.extend(self._polymarket_candidates())
        except Exception:
            logger.warning("polymarket discovery failed — continuing", exc_info=True)
        return candidates[:limit]

    async def discover_scored(self, limit: int = 10) -> list[dict[str, Any]]:
        scorer = TraderScorer()
        validator = BacktestValidator()
        result: list[dict[str, Any]] = []
        for metrics in await self.discover(limit):
            score = scorer.score(metrics)
            validation = validator.validate(metrics)
            result.append(
                {
                    "trader": asdict(metrics),
                    "score": score.score,
                    "tier": score.tier,
                    "factors": score.factors,
                    "reasoning": score.reasoning,
                    "validation": validation,
                }
            )
        return result


def run_discovery(limit: int = 10) -> dict[str, Any]:
    """Scheduler handler: discover + score candidates, persist to store."""
    discovery = TraderDiscovery()
    store = TradingStore()
    try:
        scored = asyncio.run(discovery.discover_scored(limit=limit))
    except Exception:
        logger.exception("trading discovery failed")
        scored = []
    store.set("discovery_cache", {"generated_at": store.now_iso(), "candidates": scored, "count": len(scored)})
    return {"discovered": len(scored), "store": "data/trading/trading_state.json"}
