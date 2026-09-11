"""Memecoin paper-trading loop (v1). No funds move, ever.

Cycle: scan (adapter) → hard filters → RugCheck → paper enter → track with
real quotes → staged exits → closed-trade ledger with PnL.

- Sizing: fixed fractional notional per trade (config).
- Costs: fixed round-trip haircut (fee + slippage estimate), documented.
- Kill: daily realized-loss breach activates the STRATEGY kill switch
  (requires human deactivation upstream).
- Persistence: closed trades + open positions via TradingStore (optional;
  without a store the ledger lives only in memory and says so).

Entry/exit math is in SOL notional: value = notional * (price / entry).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger("orion.trading.paper.memecoin")

PAPER_ROUNDTRIP_COST_PCT = 0.01  # ~0.3% fee + ~0.5% slippage per side, conservative


@dataclass(frozen=True, slots=True)
class PaperConfig:
    position_sol: float = 0.1
    max_open_positions: int = 3
    daily_loss_limit_sol: float = 0.5
    max_hold_minutes: float = 120.0
    min_liquidity_usd: float = 10_000.0
    strategy_id: str = "memecoin_v1"


@dataclass(slots=True)
class PaperPosition:
    mint: str
    symbol: str
    entry_sol: float
    entry_price_usd: float
    peak_price_usd: float
    entered_at: float
    remaining_pct: float = 100.0


@dataclass(frozen=True, slots=True)
class PaperTrade:
    mint: str
    symbol: str
    entry_sol: float
    exit_sol: float
    pnl_sol: float
    exit_reason: str
    opened_at: float
    closed_at: float


def paper_metrics(trades: list[PaperTrade]) -> dict[str, Any]:
    """Win-rate / profit-factor / expectancy / max-drawdown from closed trades."""
    n = len(trades)
    if n == 0:
        return {
            "trades": 0,
            "wins": 0,
            "win_rate": None,
            "profit_factor": None,
            "expectancy_sol": None,
            "realized_pnl_sol": 0.0,
            "max_drawdown_sol": 0.0,
            "verdict": "NO_DATA",
        }
    pnls = [t.pnl_sol for t in trades]
    wins = [p for p in pnls if p > 0]
    gross_win = sum(wins)
    gross_loss = -sum(p for p in pnls if p < 0)
    realized = round(sum(pnls), 6)
    equity, peak, max_dd = 0.0, 0.0, 0.0
    for p in pnls:
        equity += p
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    verdict = "NO_EDGE"
    if n >= 20 and gross_loss > 0 and gross_win / gross_loss > 1.2:
        verdict = "EDGE_CANDIDATE"
    return {
        "trades": n,
        "wins": len(wins),
        "win_rate": round(len(wins) / n, 3),
        "profit_factor": round(gross_win / gross_loss, 3) if gross_loss > 0 else None,
        "expectancy_sol": round(realized / n, 6),
        "realized_pnl_sol": realized,
        "max_drawdown_sol": round(max_dd, 6),
        "verdict": verdict,
    }


class MemecoinPaperLoop:
    """Paper loop over an injected adapter (fake in tests, real in prod)."""

    LEDGER_KEY = "memecoin_paper_trades"
    POSITIONS_KEY = "memecoin_paper_positions"

    def __init__(
        self,
        adapter: Any,
        store: Any | None = None,
        kill: Any | None = None,
        config: PaperConfig | None = None,
    ) -> None:
        self.adapter = adapter
        self.store = store
        self.kill = kill
        self.config = config or PaperConfig()
        self._open: dict[str, PaperPosition] = {}
        self._closed: list[PaperTrade] = []
        if store is not None:
            for raw in store.get(self.POSITIONS_KEY) or []:
                try:
                    self._open[raw["mint"]] = PaperPosition(**raw)
                except (TypeError, KeyError):
                    continue
            for raw in store.get(self.LEDGER_KEY) or []:
                try:
                    self._closed.append(PaperTrade(**raw))
                except (TypeError, KeyError):
                    continue

    # ── persistence ──

    def _persist(self) -> None:
        if self.store is None:
            return
        self.store.set(self.POSITIONS_KEY, [asdict(p) for p in self._open.values()])
        self.store.set(self.LEDGER_KEY, [asdict(t) for t in self._closed])

    @property
    def persisted(self) -> bool:
        return self.store is not None

    # ── kill switch ──

    def kill_active(self) -> bool:
        if self.kill is None:
            return False
        from cores.trading.risk import KillSwitchLevel

        return bool(self.kill.is_active(KillSwitchLevel.STRATEGY, self.config.strategy_id))

    def _trip_kill(self, reason: str) -> None:
        if self.kill is None:
            logger.warning("kill condition met but no KillSwitchManager wired: %s", reason)
            return
        from cores.trading.risk import KillSwitchLevel

        self.kill.activate(
            KillSwitchLevel.STRATEGY, reason, trigger="memecoin_paper", affected=[self.config.strategy_id]
        )

    def _today_realized(self, now: float) -> float:
        day = time.strftime("%Y-%m-%d", time.gmtime(now))
        total = 0.0
        for t in self._closed:
            if time.strftime("%Y-%m-%d", time.gmtime(t.closed_at)) == day:
                total += t.pnl_sol
        return total

    # ── cycle ──

    async def scan(self) -> list[dict[str, Any]]:
        """Scan + filter + RugCheck. Returns enterable candidates."""
        from cores.trading.strategies.memecoin_filters import FilterConfig, evaluate_pair

        if self.kill_active():
            return []
        tokens = await self.adapter.scan_new_tokens(self.config.min_liquidity_usd)
        cfg = FilterConfig(min_liquidity_usd=self.config.min_liquidity_usd)
        out = []
        for tok in tokens:
            rug = await self.adapter.get_token_metrics(tok.get("mint", ""))
            verdict = evaluate_pair(tok, rug, cfg, now_ms=int(time.time() * 1000))
            if verdict.passed:
                out.append({**tok, "filter_warnings": list(verdict.warnings)})
        return out

    async def enter(self, candidate: dict[str, Any], now: float | None = None) -> PaperPosition | None:
        """Open a paper position (fixed fractional notional)."""
        if self.kill_active() or len(self._open) >= self.config.max_open_positions:
            return None
        mint = str(candidate.get("mint", ""))
        price = candidate.get("price_usd")
        try:
            price_f = float(price) if price else 0.0
        except (TypeError, ValueError):
            price_f = 0.0
        if not mint or price_f <= 0 or mint in self._open:
            return None
        pos = PaperPosition(
            mint=mint,
            symbol=str(candidate.get("symbol", "?")),
            entry_sol=self.config.position_sol,
            entry_price_usd=price_f,
            peak_price_usd=price_f,
            entered_at=now if now is not None else time.time(),
        )
        self._open[mint] = pos
        self._persist()
        return pos

    async def track(
        self,
        price_fn: Callable[[str], Awaitable[float | None]],
        now: float | None = None,
    ) -> list[PaperTrade]:
        """Price open positions, apply exits, close into the ledger."""
        from cores.trading.strategies.memecoin_exits import ExitConfig, evaluate_exit

        moment = now if now is not None else time.time()
        closed: list[PaperTrade] = []
        cfg = ExitConfig(max_hold_minutes=self.config.max_hold_minutes)
        for mint, pos in list(self._open.items()):
            try:
                price = await price_fn(mint)
            except Exception as exc:
                logger.warning("price_fn failed for %s: %s", mint, exc)
                continue
            if price is None or price <= 0:
                continue
            age_min = (moment - pos.entered_at) / 60.0
            decision = evaluate_exit(pos.entry_price_usd, pos.peak_price_usd, price, age_min, cfg)
            pos.peak_price_usd = decision.new_high
            if decision.action == "hold" or decision.sell_pct <= 0:
                continue
            frac = decision.sell_pct / 100.0 * (pos.remaining_pct / 100.0)
            gross = pos.entry_sol * frac * (price / pos.entry_price_usd)
            net = gross * (1.0 - PAPER_ROUNDTRIP_COST_PCT) - pos.entry_sol * frac
            trade = PaperTrade(
                mint=mint,
                symbol=pos.symbol,
                entry_sol=round(pos.entry_sol * frac, 6),
                exit_sol=round(gross * (1.0 - PAPER_ROUNDTRIP_COST_PCT), 6),
                pnl_sol=round(net, 6),
                exit_reason=f"{decision.action}: {decision.reason}",
                opened_at=pos.entered_at,
                closed_at=moment,
            )
            closed.append(trade)
            self._closed.append(trade)
            pos.remaining_pct = round(pos.remaining_pct * (1.0 - decision.sell_pct / 100.0), 6)
            if pos.remaining_pct <= 0.01:
                del self._open[mint]
        if closed:
            self._persist()
            if self._today_realized(moment) <= -abs(self.config.daily_loss_limit_sol):
                self._trip_kill(f"daily loss limit {self.config.daily_loss_limit_sol} SOL breached")
        return closed

    def metrics(self) -> dict[str, Any]:
        summary = paper_metrics(self._closed)
        summary["open_positions"] = len(self._open)
        summary["kill_active"] = self.kill_active()
        summary["persisted"] = self.persisted
        return summary

    def open_positions(self) -> list[dict[str, Any]]:
        return [asdict(p) for p in self._open.values()]


async def dex_price_usd(mint: str) -> float | None:
    """Live SOL-mint price via DexScreener (keyless). None when unknown."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"https://api.dexscreener.com/tokens/v1/solana/{mint}")
            if resp.status_code != 200:
                return None
            pairs = resp.json()
            if not pairs or not isinstance(pairs[0], dict):
                return None
            return float(pairs[0].get("priceUsd") or 0) or None
    except Exception as exc:
        logger.warning("dex price failed for %s: %s", mint, exc)
        return None


async def run_paper_cycle_once(
    adapter: Any = None,
    store: Any = None,
    kill: Any = None,
    config: PaperConfig | None = None,
    max_new: int = 3,
) -> dict[str, Any]:
    """One autonomous scan → enter → track cycle. Async core (tests inject fakes)."""
    from cores.trading.risk import KillSwitchManager
    from cores.trading.store import TradingStore

    if adapter is None:
        from cores.investment.adapters.memecoin_adapter import MemecoinAdapter

        adapter = MemecoinAdapter()
        await adapter.connect()
    loop = MemecoinPaperLoop(
        adapter=adapter,
        store=store if store is not None else TradingStore(),
        kill=kill if kill is not None else KillSwitchManager(),
        config=config,
    )
    entered, closed = [], []
    if not loop.kill_active():
        try:
            candidates = await loop.scan()
        except Exception as exc:
            logger.warning("paper scan failed (offline?): %s", exc)
            candidates = []
        for candidate in candidates:
            if len(loop.open_positions()) >= loop.config.max_open_positions:
                break
            if len(entered) >= max_new:
                break
            pos = await loop.enter(candidate)
            if pos is not None:
                entered.append(pos.mint)
    try:
        closed = await loop.track(dex_price_usd)
    except Exception as exc:
        logger.warning("paper track failed: %s", exc)
    summary = loop.metrics()
    summary.update({"entered": entered, "closed": [t.mint for t in closed]})
    return summary


def run_memecoin_paper_cycle(max_new: int = 3) -> dict[str, Any]:
    """Scheduler entrypoint: memecoin paper loop, DRY-RUN only, never raises.

    Runs the async cycle on a dedicated thread so it is safe from any caller
    event-loop context. Returns a JSON-serializable summary.
    """
    import threading

    result: dict[str, Any] = {}

    def _target() -> None:
        import asyncio

        try:
            result.update(asyncio.run(run_paper_cycle_once(max_new=max_new)))
        except Exception as exc:  # never break the scheduler
            logger.error("memecoin paper cycle failed: %s", exc)
            result.update({"status": "error", "error": str(exc)})

    worker = threading.Thread(target=_target, name="memecoin-paper", daemon=True)
    worker.start()
    worker.join(timeout=600)
    if worker.is_alive():
        return {"status": "timeout", "entered": [], "closed": []}
    result.setdefault("status", "ok")
    return result
