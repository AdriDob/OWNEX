from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from core.investment.models import TradeEvidence

logger = logging.getLogger("orion.investment.attribution")


def _completeness_flag(trades: list[TradeEvidence]) -> str:
    """Classify how much of a group's net P&L rests on complete data.

    A trade carries a complete net figure only when its
    ``net_pnl_completeness`` is COMPLETE; anything else may be gross-only,
    unhedged or unknown. UNKNOWN is returned when there is nothing to judge, so
    an empty group never looks complete.
    """
    if not trades:
        return "UNKNOWN"
    complete = sum(1 for t in trades if t.net_pnl_completeness == "COMPLETE")
    if complete == len(trades):
        return "COMPLETE"
    if complete:
        return "PARTIAL"
    return "INCOMPLETE"


# ---------------------------------------------------------------------------
# Axis descriptors
# ---------------------------------------------------------------------------


class MissingDimensionMode(str):
    """How an absent dimension is reported by the attribution engine."""

    UNAVAILABLE = "unavailable"  # field exists on TradeEvidence but is empty/unknown
    UNKNOWN = "unknown"  # the concept itself is not collected for this record
    EXCLUDED = "excluded"  # group-level computation excluded this dimension


# ---------------------------------------------------------------------------
# Grouping keys
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TradeKey:
    """Immutable key for one trade as seen by the attribution engine.

    Built only from fields that exist on TradeEvidence. No inference.
    """

    strategy_id: str
    exchange: str
    account_id: str
    symbol: str
    asset: str
    side: str
    provenance: str
    currency: str
    period: str

    @classmethod
    def from_trade(cls, t: TradeEvidence, period: str | None = None) -> TradeKey:
        return cls(
            strategy_id=t.strategy_id,
            exchange=cls._display(t.exchange),
            account_id=cls._display(t.account_id),
            symbol=cls._display(t.symbol),
            asset=cls._display(t.asset),
            side=cls._display(t.side),
            provenance=cls._provenance(t),
            currency=cls._currency(t),
            period=period or _period_from_ts(t.created_at),
        )

    @staticmethod
    def _display(value: str) -> str:
        # Empty string means the field was never recorded -> UNAVAILABLE
        return value

    @staticmethod
    def _provenance(t: TradeEvidence) -> str:
        return t.provenance_level.value

    @staticmethod
    def _currency(t: TradeEvidence) -> str:
        return t.currency or "UNKNOWN"


def _period_from_ts(ts: str) -> str:
    if not ts:
        return "UNKNOWN"
    try:
        # Accept common ISO forms and take YYYY-MM
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m")
    except Exception:
        return "UNKNOWN"


# ---------------------------------------------------------------------------
# Per-group metrics
# ---------------------------------------------------------------------------


@dataclass
class TradeGroupMetrics:
    """Metrics for one attribution group (one TradeKey)."""

    key: TradeKey
    total_trades: int = 0
    eligible_trades: int = 0
    excluded_trades: int = 0
    excluded_reasons: dict[str, int] = field(default_factory=dict)
    winning_trades: int = 0
    losing_trades: int = 0
    break_even_trades: int = 0
    gross_pnl_complete: float = 0.0
    net_pnl_complete: float = 0.0
    win_rate_explicit: float = 0.0
    win_rate_definition: str = ""
    expectancy: float = 0.0
    profit_factor: float = 0.0
    roi_pct: float | None = None
    roi_basis: str = ""
    pnl_completeness: str = "UNKNOWN"
    # Trades whose exit leg never filled: open positions with no realized P&L.
    unhedged_trades: int = 0
    provenance_breakdown: dict[str, int] = field(default_factory=dict)
    trade_ids: list[str] = field(default_factory=list)
    currencies_seen: set[str] = field(default_factory=set)
    sample_quality: str = "UNKNOWN"
    missing_dimensions: set[str] = field(default_factory=set)
    currency_mismatch: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API responses, keeping every caveat visible.

        Sets become sorted lists so the payload is stable, and the wording
        fields (``win_rate_definition``, ``roi_basis``) travel with the numbers
        so a client cannot read a provisional figure as final.
        """
        return {
            "key": asdict(self.key),
            "total_trades": self.total_trades,
            "eligible_trades": self.eligible_trades,
            "excluded_trades": self.excluded_trades,
            "excluded_reasons": dict(sorted(self.excluded_reasons.items())),
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "break_even_trades": self.break_even_trades,
            "gross_pnl_complete": self.gross_pnl_complete,
            "net_pnl_complete": self.net_pnl_complete,
            "win_rate_explicit": self.win_rate_explicit,
            "win_rate_definition": self.win_rate_definition,
            "expectancy": self.expectancy,
            "profit_factor": self.profit_factor,
            "roi_pct": self.roi_pct,
            "roi_basis": self.roi_basis,
            "pnl_completeness": self.pnl_completeness,
            "unhedged_trades": self.unhedged_trades,
            "provenance_breakdown": dict(sorted(self.provenance_breakdown.items())),
            "trade_ids": list(self.trade_ids),
            "currencies_seen": sorted(self.currencies_seen),
            "sample_quality": self.sample_quality,
            "missing_dimensions": sorted(self.missing_dimensions),
            "currency_mismatch": self.currency_mismatch,
        }


# ---------------------------------------------------------------------------
# Attribution engine
# ---------------------------------------------------------------------------


class StrategyAttribution:
    """Attribution for investment performance across multiple dimensions.

    Rules:
    - One group per distinct combination of the requested axes.
    - Never infer missing dimensions. Absent account_id/asset appear as
      UNAVAILABLE and are tracked, never invented.
    - Multiple currencies in the same requested group produce a
      currency_mismatch flag and are excluded from net mixing.
    - Provenance levels are reported separately; they are never mixed into a
      single "verified" figure.
    - Duplicate detection is read-only: duplicates are reported, not removed
      from the underlying history.
    - Every result is traceable to its original trade_ids.
    """

    def __init__(self, trades: list[TradeEvidence]) -> None:
        self._trades = list(trades)
        self._by_key: dict[TradeKey, list[TradeEvidence]] = defaultdict(list)
        for t in self._trades:
            key = TradeKey.from_trade(t)
            self._by_key[key].append(t)

    # ── public API ────────────────────────────────────────────────────────

    def by_strategy(self) -> list[TradeGroupMetrics]:
        return self._group_by_axis("strategy_id")

    def by_exchange(self) -> list[TradeGroupMetrics]:
        return self._group_by_axis("exchange")

    def by_account(self) -> list[TradeGroupMetrics]:
        return self._group_by_axis("account_id")

    def by_symbol(self) -> list[TradeGroupMetrics]:
        return self._group_by_axis("symbol")

    def by_asset(self) -> list[TradeGroupMetrics]:
        return self._group_by_axis("asset")

    def by_side(self) -> list[TradeGroupMetrics]:
        return self._group_by_axis("side")

    def by_provenance(self) -> list[TradeGroupMetrics]:
        return self._group_by_axis("provenance")

    def by_currency(self) -> list[TradeGroupMetrics]:
        return self._group_by_axis("currency")

    def by_period(self) -> list[TradeGroupMetrics]:
        return self._group_by_axis("period")

    def by_strategy_and_exchange(self) -> list[TradeGroupMetrics]:
        return self._group_by_axes(["strategy_id", "exchange"])

    def group(self, key: TradeKey) -> TradeGroupMetrics | None:
        matching: list[TradeEvidence] = []
        for k, ts in self._by_key.items():
            if (
                k.strategy_id == key.strategy_id
                and k.exchange == key.exchange
                and k.account_id == key.account_id
                and k.symbol == key.symbol
                and k.asset == key.asset
                and k.side == key.side
                and k.provenance == key.provenance
                and k.currency == key.currency
                and k.period == key.period
            ):
                matching.extend(ts)
        if not matching:
            return None
        return self._compute(matching, key)

    def all_groups(self) -> list[TradeGroupMetrics]:
        out: list[TradeGroupMetrics] = []
        for key, trades in self._by_key.items():
            out.append(self._compute(trades, key))
        return out

    # ── internals ────────────────────────────────────────────────────────

    def _group_by_axis(self, axis: str) -> list[TradeGroupMetrics]:
        """Collapse multiple keys that share the same value for *axis*."""
        buckets: dict[str, list[TradeEvidence]] = defaultdict(list)
        for key, trades in self._by_key.items():
            value = getattr(key, axis)
            buckets[value].append(trades)
        out: list[TradeGroupMetrics] = []
        for value, trades_list in buckets.items():
            merged_trades: list[TradeEvidence] = []
            for chunk in trades_list:
                merged_trades.extend(chunk)
            # Rebuild a representative key for display (axis = value, rest UNAVAILABLE)
            representative = self._representative_key_for_axis(axis, value)
            out.append(self._compute(merged_trades, representative))
        out.sort(key=lambda m: (m.key.strategy_id, m.key.exchange, m.key.symbol))
        return out

    def _group_by_axes(self, axes: list[str]) -> list[TradeGroupMetrics]:
        buckets: dict[tuple[str, ...], list[TradeEvidence]] = defaultdict(list)
        for key, trades in self._by_key.items():
            bucket_key = tuple(getattr(key, a) for a in axes)
            buckets[bucket_key].append(trades)
        out: list[TradeGroupMetrics] = []
        for bucket_key, trades_list in buckets.items():
            merged_trades: list[TradeEvidence] = []
            for chunk in trades_list:
                merged_trades.extend(chunk)
            representative = self._representative_key_for_axes(axes, bucket_key)
            out.append(self._compute(merged_trades, representative))
        out.sort(key=lambda m: (m.key.strategy_id, m.key.exchange, m.key.symbol))
        return out

    @staticmethod
    def _representative_key_for_axis(axis: str, value: str) -> TradeKey:
        return TradeKey(
            strategy_id="ALL" if axis != "strategy_id" else value,
            exchange="ALL" if axis != "exchange" else value,
            account_id="ALL" if axis != "account_id" else value,
            symbol="ALL" if axis != "symbol" else value,
            asset="ALL" if axis != "asset" else value,
            side="ALL" if axis != "side" else value,
            provenance="ALL" if axis != "provenance" else value,
            currency="ALL" if axis != "currency" else value,
            period="ALL" if axis != "period" else value,
        )

    @staticmethod
    def _representative_key_for_axes(axes: list[str], values: tuple[str, ...]) -> TradeKey:
        values_by_axis = dict(zip(axes, values, strict=False))
        return TradeKey(
            strategy_id=values_by_axis.get("strategy_id", "ALL"),
            exchange=values_by_axis.get("exchange", "ALL"),
            account_id=values_by_axis.get("account_id", "ALL"),
            symbol=values_by_axis.get("symbol", "ALL"),
            asset=values_by_axis.get("asset", "ALL"),
            side=values_by_axis.get("side", "ALL"),
            provenance=values_by_axis.get("provenance", "ALL"),
            currency=values_by_axis.get("currency", "ALL"),
            period=values_by_axis.get("period", "ALL"),
        )

    @staticmethod
    def _compute(trades: list[TradeEvidence], key: TradeKey) -> TradeGroupMetrics:
        m = TradeGroupMetrics(key=key)
        if not trades:
            return m

        # Deduplicate for reporting only: a duplicate is a trade with the same
        # meaningful trading payload. We flag it but do not remove anything.
        seen_payload: dict[tuple[Any, ...], int] = defaultdict(int)
        duplicates: list[str] = []
        for t in trades:
            payload = (
                t.strategy_id,
                t.exchange,
                t.account_id,
                t.symbol,
                t.side,
                t.gross_pnl,
                t.fees,
                t.slippage,
                t.net_pnl,
                t.currency,
                t.created_at,
            )
            seen_payload[payload] += 1
            if seen_payload[payload] > 1:
                duplicates.append(t.trade_id)

        m.total_trades = len(trades)
        m.trade_ids = [t.trade_id for t in trades]
        m.currencies_seen = {t.currency or "UNKNOWN" for t in trades}
        if len(m.currencies_seen) > 1:
            m.currency_mismatch = True

        # Missing / unavailable dimensions for this group
        for t in trades[:1]:
            # Use one representative trade to assess missing dimensions at group level
            if not t.exchange:
                m.missing_dimensions.add("exchange")
            if not t.account_id:
                m.missing_dimensions.add("account_id")
            if not t.symbol:
                m.missing_dimensions.add("symbol")
            if not t.side:
                m.missing_dimensions.add("side")
            if not t.asset:
                m.missing_dimensions.add("asset")

        # Provenance breakdown (never mixed)
        prov: dict[str, int] = defaultdict(int)
        for t in trades:
            prov[t.provenance_level.value] += 1
        m.provenance_breakdown = dict(prov)

        # Exclusions
        excluded_reasons: dict[str, int] = defaultdict(int)
        eligible: list[TradeEvidence] = []

        for t in trades:
            reasons: list[str] = []
            if not t.strategy_id:
                reasons.append("missing_strategy_id")
            if not t.symbol:
                reasons.append("missing_symbol")
            if t.currency in ("", None):
                reasons.append("missing_currency")
            if t.net_pnl_completeness == "UNKNOWN" and t.gross_pnl is None:
                reasons.append("no_pnl_data")
            if reasons:
                excluded_reasons["; ".join(reasons)] += 1
                m.excluded_trades += 1
            else:
                eligible.append(t)

        m.excluded_reasons = dict(excluded_reasons)
        m.eligible_trades = len(eligible)

        # Net: only from COMPLETE trades. NEVER from gross alone.
        currencies_in_eligible = {t.currency or "UNKNOWN" for t in eligible}
        complete_trades = [t for t in eligible if t.net_pnl_completeness == "COMPLETE"]
        if len(currencies_in_eligible) > 1:
            m.net_pnl_complete = 0.0
            m.roi_basis = "excluded: currency_mismatch"
        elif not complete_trades:
            m.net_pnl_complete = 0.0
            m.roi_basis = "excluded: no_complete_net"
        else:
            m.net_pnl_complete = round(sum(t.net_pnl_calc for t in complete_trades), 2)
            m.roi_basis = "net_pnl_complete / abs(gross_pnl_complete)"

        # Gross: only from trades that actually carry gross_pnl
        m.gross_pnl_complete = round(sum(t.gross_pnl for t in eligible if t.gross_pnl is not None), 2)

        # Win/loss/break-even only over COMPLETE trades with a known net sign.
        winning: list[TradeEvidence] = []
        losing: list[TradeEvidence] = []
        break_even: list[TradeEvidence] = []

        for t in complete_trades:
            if t.net_pnl_calc > 0:
                winning.append(t)
            elif t.net_pnl_calc < 0:
                losing.append(t)
            else:
                break_even.append(t)

        m.winning_trades = len(winning)
        m.losing_trades = len(losing)
        m.break_even_trades = len(break_even)

        total_with_sign = max(len(winning) + len(losing) + len(break_even), 1)
        m.win_rate_explicit = round(len(winning) / total_with_sign, 4)
        m.win_rate_definition = "wins / (wins + losses + break_even) over COMPLETE-net eligible trades"

        # Expectancy: only over COMPLETE trades with known sign
        if winning or losing:
            prob_win = len(winning) / total_with_sign
            prob_loss = len(losing) / total_with_sign
            avg_win = sum(t.net_pnl_calc for t in winning) / max(len(winning), 1)
            avg_loss = sum(abs(t.net_pnl_calc) for t in losing) / max(len(losing), 1)
            m.expectancy = round(prob_win * avg_win - prob_loss * avg_loss, 2)

        # Profit factor: gross winning / gross losing (absolute), over COMPLETE trades
        gw = sum(t.gross_pnl or 0.0 for t in winning)
        gl = sum(abs(t.gross_pnl or 0.0) for t in losing)
        if gw or gl:
            m.profit_factor = round(gw / max(gl, 0.001), 2)

        # ROI only when both net and gross are non-trivial
        if m.net_pnl_complete and m.gross_pnl_complete:
            m.roi_pct = round(m.net_pnl_complete / abs(m.gross_pnl_complete) * 100, 2)
        else:
            m.roi_pct = None

        # Unhedged rounds: counted, but they contribute no realized figure.
        unhedged = [t for t in eligible if t.net_pnl_completeness == "LEG_UNHEDGED"]
        m.unhedged_trades = len(unhedged)

        # P&L completeness
        m.pnl_completeness = _completeness_flag(eligible)

        # Sample quality
        n = len(eligible)
        if n == 0:
            m.sample_quality = "NO_ELIGIBLE_TRADES"
        elif n < 5:
            m.sample_quality = "SMALL_SAMPLE"
        elif any(t.net_pnl_completeness != "COMPLETE" for t in eligible):
            m.sample_quality = "INCOMPLETE_NET_MIXED"
        else:
            m.sample_quality = "COMPLETE"

        # Duplicate indicator
        if duplicates:
            m.excluded_reasons["duplicate_flag"] = len(duplicates)

        return m


def attribute(trades: list[TradeEvidence]) -> StrategyAttribution:
    return StrategyAttribution(trades)


# Re-export for convenience
__all__ = [
    "StrategyAttribution",
    "TradeGroupMetrics",
    "TradeKey",
    "attribute",
    "MissingDimensionMode",
]
