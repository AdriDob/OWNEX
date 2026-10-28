"""Memecoin backtester — replay historical snapshots through filters + exits.

Pure CPU, zero network, zero IO. Takes a list of token snapshots at discrete
timepoints, applies the same FilterConfig + ExitConfig as the live paper loop,
and produces BacktestResult with per-trade PnL + aggregated metrics.

This is deterministic: same input always produces same output. Used for
parameter optimization (OAR advisor) and historical validation before going live.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from cores.trading.paper.memecoin_paper import PaperTrade, paper_metrics
from cores.trading.strategies.memecoin_exits import ExitConfig, ExitDecision, evaluate_exit
from cores.trading.strategies.memecoin_filters import FilterConfig, FilterVerdict, evaluate_pair

logger = logging.getLogger("orion.trading.backtest")

# Backtester config defaults match paper loop defaults (SSOT via PaperConfig)
BACKTEST_ROUNDTRIP_COST_PCT = 0.01  # same as paper loop


@dataclass(frozen=True, slots=True)
class Snapshot:
    """One data point for one token at one timepoint."""

    mint: str
    symbol: str
    timestamp: float  # unix seconds
    price_usd: float
    # Pair data (DexScreener shape) — pass-through to evaluate_pair
    pair: dict[str, Any] = field(default_factory=dict)
    # RugCheck data — pass-through to evaluate_pair
    rug: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Parameter knobs that the OAR advisor can tune."""

    position_sol: float = 0.1
    max_open_positions: int = 3
    daily_loss_limit_sol: float = 0.5
    max_hold_minutes: float = 120.0
    min_liquidity_usd: float = 10_000.0
    # Exit knobs (from ExitConfig)
    stop_loss_pct: float = 0.25
    trailing_pct: float = 0.20
    take_profit_tiers: tuple[tuple[float, float], ...] = ((0.5, 0.5), (1.0, 0.3), (2.0, 0.2))

    def to_filter_config(self) -> FilterConfig:
        return FilterConfig(min_liquidity_usd=self.min_liquidity_usd)

    def to_exit_config(self) -> ExitConfig:
        return ExitConfig(
            stop_loss_pct=self.stop_loss_pct,
            trailing_pct=self.trailing_pct,
            take_profit_tiers=self.take_profit_tiers,
            max_hold_minutes=self.max_hold_minutes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_sol": self.position_sol,
            "max_open_positions": self.max_open_positions,
            "daily_loss_limit_sol": self.daily_loss_limit_sol,
            "max_hold_minutes": self.max_hold_minutes,
            "min_liquidity_usd": self.min_liquidity_usd,
            "stop_loss_pct": self.stop_loss_pct,
            "trailing_pct": self.trailing_pct,
            "take_profit_tiers": self.take_profit_tiers,
        }


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Output of a backtest run."""

    config: dict[str, Any]
    total_snapshots: int
    tokens_evaluated: int
    tokens_entered: int
    trades: tuple[PaperTrade, ...]
    metrics: dict[str, Any]
    events: tuple[dict[str, Any], ...]  # timeline of enter/exit/hold events


def _snapshots_to_timeline(snapshots: list[Snapshot]) -> dict[str, list[Snapshot]]:
    """Group snapshots by mint, sort each by timestamp."""
    by_mint: dict[str, list[Snapshot]] = {}
    for s in snapshots:
        by_mint.setdefault(s.mint, []).append(s)
    for mint_list in by_mint.values():
        mint_list.sort(key=lambda s: s.timestamp)
    return by_mint


def _hash_mint(mint: str) -> str:
    """Short readable token id for events."""
    return mint[:8] + "..." + mint[-4:] if len(mint) > 12 else mint


def run_backtest(
    snapshots: list[Snapshot],
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """Replay snapshots through filters + exits. Pure CPU, deterministic.

    The logic mirrors MemecoinPaperLoop.scan() + .enter() + .track() but on
    historical data: each snapshot is evaluated against the filter at its
    timestamp, and open positions are tracked across subsequent snapshots.

    Phases per token timeline:
    1. filter pass (Snapshot.rug + Snapshot.pair) → eligible?
    2. first eligible snapshot → enter at that price
    3. subsequent snapshots → evaluate_exit (SL/TP/trailing/time)
    4. exit triggers → PaperTrade (with haircut)
    """
    cfg = config or BacktestConfig()
    filter_cfg = cfg.to_filter_config()
    exit_cfg = cfg.to_exit_config()
    timeline = _snapshots_to_timeline(snapshots)

    events: list[dict[str, Any]] = []
    closed_trades: list[PaperTrade] = []
    # state: mint → {entry_price, entry_sol, entry_time, peak_price, remaining_pct}
    open_positions: dict[str, dict[str, Any]] = {}
    daily_losses: dict[str, float] = {}  # date_str → realized loss
    tokens_entered = set()

    for mint, mint_snaps in timeline.items():
        for snap in mint_snaps:
            # ── Phase 1: filter ──
            filter_result: FilterVerdict = evaluate_pair(
                snap.pair, snap.rug, filter_cfg, now_ms=int(snap.timestamp * 1000)
            )
            if not filter_result.passed:
                events.append(
                    {
                        "time": snap.timestamp,
                        "mint": _hash_mint(mint),
                        "action": "filtered_out",
                        "reasons": filter_result.reasons,
                    }
                )
                continue

            # ── Phase 2: enter (if not already open) ──
            if mint not in open_positions and len(open_positions) < cfg.max_open_positions:
                entry_sol = cfg.position_sol
                open_positions[mint] = {
                    "entry_price": snap.price_usd,
                    "entry_sol": entry_sol,
                    "entry_time": snap.timestamp,
                    "peak_price": snap.price_usd,
                    "remaining_pct": 100.0,
                    "symbol": snap.symbol,
                }
                tokens_entered.add(mint)
                events.append(
                    {
                        "time": snap.timestamp,
                        "mint": _hash_mint(mint),
                        "action": "enter",
                        "price": snap.price_usd,
                        "entry_sol": entry_sol,
                    }
                )

            # ── Phase 3: evaluate exit (if open) ──
            if mint not in open_positions:
                continue
            pos = open_positions[mint]
            age_min = (snap.timestamp - pos["entry_time"]) / 60.0
            decision: ExitDecision = evaluate_exit(
                pos["entry_price"],
                pos["peak_price"],
                snap.price_usd,
                age_min,
                exit_cfg,
            )
            pos["peak_price"] = decision.new_high

            if decision.action == "hold" or decision.sell_pct <= 0:
                events.append(
                    {
                        "time": snap.timestamp,
                        "mint": _hash_mint(mint),
                        "action": "hold",
                        "reason": decision.reason,
                        "price": snap.price_usd,
                    }
                )
                continue

            # ── Phase 4: execute exit ──
            frac = (decision.sell_pct / 100.0) * (pos["remaining_pct"] / 100.0)
            gross = pos["entry_sol"] * frac * (snap.price_usd / pos["entry_price"])
            net = gross * (1.0 - BACKTEST_ROUNDTRIP_COST_PCT) - pos["entry_sol"] * frac
            trade = PaperTrade(
                mint=mint,
                symbol=pos["symbol"],
                entry_sol=round(pos["entry_sol"] * frac, 6),
                exit_sol=round(gross * (1.0 - BACKTEST_ROUNDTRIP_COST_PCT), 6),
                pnl_sol=round(net, 6),
                exit_reason=f"{decision.action}: {decision.reason}",
                opened_at=pos["entry_time"],
                closed_at=snap.timestamp,
            )
            closed_trades.append(trade)
            pos["remaining_pct"] = round(pos["remaining_pct"] * (1.0 - decision.sell_pct / 100.0), 6)

            # Kill on daily loss limit
            day_str = _date_str(snap.timestamp)
            daily_losses[day_str] = daily_losses.get(day_str, 0.0) + (trade.pnl_sol if trade.pnl_sol < 0 else 0)
            if daily_losses[day_str] <= -abs(cfg.daily_loss_limit_sol):
                events.append(
                    {
                        "time": snap.timestamp,
                        "mint": _hash_mint(mint),
                        "action": "kill_triggered",
                        "reason": f"daily loss limit {cfg.daily_loss_limit_sol} SOL breached",
                    }
                )
                break  # stop processing this token timeline

            events.append(
                {
                    "time": snap.timestamp,
                    "mint": _hash_mint(mint),
                    "action": decision.action,
                    "reason": decision.reason,
                    "pnl_sol": round(net, 6),
                    "price": snap.price_usd,
                }
            )

            if pos["remaining_pct"] <= 0.01:
                del open_positions[mint]

    metrics = paper_metrics(closed_trades)
    metrics["tokens_evaluated"] = len(timeline)
    metrics["tokens_entered"] = len(tokens_entered)
    return BacktestResult(
        config=cfg.to_dict(),
        total_snapshots=len(snapshots),
        tokens_evaluated=len(timeline),
        tokens_entered=len(tokens_entered),
        trades=tuple(closed_trades),
        metrics=metrics,
        events=tuple(events),
    )


def _date_str(ts: float) -> str:
    """Unix timestamp → date string for daily loss tracking."""
    from datetime import UTC, datetime

    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")


def result_to_dict(result: BacktestResult) -> dict[str, Any]:
    """Serialize BacktestResult to JSON-safe dict."""
    return {
        "config": result.config,
        "total_snapshots": result.total_snapshots,
        "tokens_evaluated": result.tokens_evaluated,
        "tokens_entered": result.tokens_entered,
        "trades": [
            {
                "mint": t.mint,
                "symbol": t.symbol,
                "entry_sol": t.entry_sol,
                "exit_sol": t.exit_sol,
                "pnl_sol": t.pnl_sol,
                "exit_reason": t.exit_reason,
                "opened_at": t.opened_at,
                "closed_at": t.closed_at,
            }
            for t in result.trades
        ],
        "metrics": result.metrics,
        "events": list(result.events[-50:]),  # last 50 events for display
    }


# ── Snapshot accumulation ──
# The live paper loop records price snapshots for open positions each cycle.
# Backtests replay accumulated snapshots through the exact same filters+exits.

SNAPSHOTS_KEY = "memecoin_paper_snapshots"  # TradingStore key


def save_snapshot(
    store: Any,
    mint: str,
    symbol: str,
    price_usd: float,
    timestamp: float | None = None,
    pair: dict[str, Any] | None = None,
    rug: dict[str, Any] | None = None,
) -> None:
    """Append one price snapshot to the TradingStore-backed history (snapshot list).

    Cheap append-only: keeps the curve of every token the paper loop tracked so a
    backtest can replay it offline. Never raises (trading store optional).
    """
    import time

    if store is None:
        return
    try:
        snapshots = list(store.get(SNAPSHOTS_KEY) or [])
        snapshots.append(
            {
                "mint": mint,
                "symbol": symbol,
                "timestamp": timestamp if timestamp is not None else time.time(),
                "price_usd": float(price_usd),
                "pair": pair or {},
                "rug": rug,
            }
        )
        store.set(SNAPSHOTS_KEY, snapshots[-2000:])  # cap memory footprint
    except Exception as exc:
        logger.debug("snapshot save skipped: %s", exc)


def load_snapshots(store: Any, limit: int = 2000) -> list[Snapshot]:
    """Load accumulated snapshots from the store into Snapshot instances."""
    if store is None:
        return []
    raw = list(store.get(SNAPSHOTS_KEY) or [])[-limit:]
    out: list[Snapshot] = []
    for entry in raw:
        try:
            out.append(
                Snapshot(
                    mint=str(entry["mint"]),
                    symbol=str(entry.get("symbol", "?")),
                    timestamp=float(entry["timestamp"]),
                    price_usd=float(entry["price_usd"]),
                    pair=dict(entry.get("pair") or {}),
                    rug=entry.get("rug"),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return out


def snapshot_to_dict(sample: Snapshot) -> dict[str, Any]:
    return {
        "mint": sample.mint,
        "symbol": sample.symbol,
        "timestamp": sample.timestamp,
        "price_usd": sample.price_usd,
        "pair": sample.pair,
        "rug": sample.rug,
    }


def parameter_sweep(
    snapshots: list[Snapshot],
    configs: list[BacktestConfig],
) -> list[dict[str, Any]]:
    """Run backtest for each config and return ranked results.

    Deterministic parameter sweep used by the advisor to compare configs.
    Each entry: {config, metrics, trades} sorted by expectancy descending.
    """
    results: list[dict[str, Any]] = []
    for cfg in configs:
        result = run_backtest(snapshots, cfg)
        results.append({"config": cfg.to_dict(), "metrics": result.metrics, "trades": len(result.trades)})
    results.sort(key=lambda r: (r["metrics"].get("trades", 0), r["metrics"].get("expectancy_sol", 0.0)), reverse=True)
    return results
