from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger("orion.revenue.metrics")


@dataclass
class BountyMetrics:
    targets_scanned: int = 0
    findings_total: int = 0
    findings_critical: int = 0
    findings_high: int = 0
    findings_medium: int = 0
    findings_low: int = 0
    reports_submitted: int = 0
    reports_accepted: int = 0
    reports_rejected: int = 0
    total_payout: Decimal = Decimal("0")
    avg_cvss: float = 0.0
    top_tools: dict[str, int] = field(default_factory=dict)


@dataclass
class TradingMetrics:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    profit_factor: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    avg_hold_time_hours: float = 0.0


@dataclass
class CombinedMetrics:
    bounty: BountyMetrics = field(default_factory=BountyMetrics)
    trading: TradingMetrics = field(default_factory=TradingMetrics)
    total_revenue: Decimal = Decimal("0")
    revenue_24h: Decimal = Decimal("0")
    revenue_7d: Decimal = Decimal("0")
    revenue_30d: Decimal = Decimal("0")
    estimated_annual: Decimal = Decimal("0")
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class MetricsTracker:
    def __init__(self) -> None:
        self._bounty = BountyMetrics()
        self._trading = TradingMetrics()
        self._revenue_history: list[dict[str, Any]] = []

    @property
    def bounty(self) -> BountyMetrics:
        return self._bounty

    @property
    def trading(self) -> TradingMetrics:
        return self._trading

    def record_finding(self, severity: str, tool: str, cvss: float = 0.0) -> None:
        self._bounty.findings_total += 1
        if severity == "critical":
            self._bounty.findings_critical += 1
        elif severity == "high":
            self._bounty.findings_high += 1
        elif severity == "medium":
            self._bounty.findings_medium += 1
        else:
            self._bounty.findings_low += 1
        self._bounty.top_tools[tool] = self._bounty.top_tools.get(tool, 0) + 1
        total_sev = self._bounty.findings_critical + self._bounty.findings_high + self._bounty.findings_medium
        if total_sev > 0:
            self._bounty.avg_cvss = (self._bounty.avg_cvss * (total_sev - 1) + cvss) / total_sev

    def record_trade(self, pnl: Decimal | None, won: bool | None) -> None:
        """Registra un trade cerrado.

        `pnl` y `won` aceptan None = PNL DESCONOCIDO. Antes ambos eran
        obligatorios y el único caller pasaba `pnl=Decimal("0"), won=True`
        fijo, lo que producia `win_rate = 100%` garantizado y
        `total_pnl = 0` para siempre (auditoría 2026-10-05).

        Con None NO se cuenta como ganar ni como perder: el trade se
        contabiliza en `total_trades` pero no distorsiona el win_rate ni el
        PnL acumulado. Un ratio calculado sobre datos que no existen es
        inventado, y `win_rate=1.0` es exactamente el tipo de cifra que el
        proyecto prohibe.
        """
        self._trading.total_trades += 1
        if won is True:
            self._trading.winning_trades += 1
        elif won is False:
            self._trading.losing_trades += 1
        if pnl is not None:
            self._trading.total_pnl += pnl
        decided = self._trading.winning_trades + self._trading.losing_trades
        if decided > 0:
            self._trading.win_rate = self._trading.winning_trades / decided

    def record_revenue(self, amount: Decimal, category: str, timestamp: datetime | None = None) -> None:
        self._revenue_history.append(
            {
                "amount": amount,
                "category": category,
                "timestamp": (timestamp or datetime.now(UTC)).isoformat(),
            }
        )

    def get_combined(self) -> CombinedMetrics:
        now = datetime.now(UTC)
        revenue_24h = Decimal("0")
        revenue_7d = Decimal("0")
        revenue_30d = Decimal("0")
        total_rev = Decimal("0")
        for entry in self._revenue_history:
            ts = datetime.fromisoformat(entry["timestamp"])
            amt = entry["amount"]
            total_rev += amt
            if (now - ts).days < 1:
                revenue_24h += amt
            if (now - ts).days < 7:
                revenue_7d += amt
            if (now - ts).days < 30:
                revenue_30d += amt

        # Si nadie Alimentó el history local (auditoría 2026-10-05: `record_revenue`
        # tenía 0 callers), Leemos el RevenueLedger canónico para no reportar
        # 0 inventado. `RevenueLedger` es la SSOT de revenue del sistema.
        if not self._revenue_history:
            total_rev = self._revenue_from_ledger()

        estimated_annual = revenue_30d * Decimal("12") if revenue_30d > 0 else Decimal("0")
        return CombinedMetrics(
            bounty=self._bounty,
            trading=self._trading,
            total_revenue=total_rev,
            revenue_24h=revenue_24h,
            revenue_7d=revenue_7d,
            revenue_30d=revenue_30d,
            estimated_annual=estimated_annual,
            updated_at=now,
        )

    @staticmethod
    def _revenue_from_ledger() -> Decimal:
        """Lee el total neto del RevenueLedger (SSOT). Devuelve 0 si falla."""
        try:
            from cores.revenue.ledger import get_revenue_ledger

            summary = get_revenue_ledger().get_summary()
            return Decimal(str(summary.get("total_net_usd", 0) or 0))
        except Exception as exc:
            logger.debug("RevenueLedger unavailable for metrics: %s", exc)
            return Decimal("0")

    def to_dict(self) -> dict[str, Any]:
        cm = self.get_combined()
        return {
            "bounty": {
                "targets_scanned": cm.bounty.targets_scanned,
                "findings_total": cm.bounty.findings_total,
                "findings_by_severity": {
                    "critical": cm.bounty.findings_critical,
                    "high": cm.bounty.findings_high,
                    "medium": cm.bounty.findings_medium,
                    "low": cm.bounty.findings_low,
                },
                "top_tools": cm.bounty.top_tools,
                "avg_cvss": round(cm.bounty.avg_cvss, 2),
            },
            "trading": {
                "total_trades": cm.trading.total_trades,
                "win_rate": round(cm.trading.win_rate * 100, 1),
                "total_pnl": str(cm.trading.total_pnl),
            },
            "revenue": {
                "24h": str(cm.revenue_24h),
                "7d": str(cm.revenue_7d),
                "30d": str(cm.revenue_30d),
                "total": str(cm.total_revenue),
                "estimated_annual": str(cm.estimated_annual),
            },
            "updated_at": cm.updated_at.isoformat(),
        }
