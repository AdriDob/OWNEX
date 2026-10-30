"""Paper Trading Ledger — registers hypothetical bets, tracks CLV and PnL.

Pure Python, no external deps. JSONL storage (append-only, survives restarts).
Reuses KellyProvider from Odyssey for sizing. Pure functions, testable.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger("ownex.betting.paper_ledger")


@dataclass(slots=True, frozen=True)
class PaperBet:
    """A recorded paper bet with all metadata for settlement."""

    id: str
    market_id: str
    sport: str
    event: str
    selection: str
    odds: Decimal
    stake: Decimal
    kelly_fraction: float
    edge_bps: int
    placed_at: str
    kelly_fraction_used: float
    status: str = "open"  # open, won, lost, push, void
    settled_at: str | None = None
    settled_odds: Decimal | None = None
    result: str | None = None  # won, lost, push, void
    pnl: Decimal | None = None
    clv_bps: int | None = None  # Closing Line Value in basis points


@dataclass(slots=True, frozen=True)
class PaperBetMetrics:
    """Aggregated metrics for paper ledger."""

    total_bets: int
    open_bets: int
    settled_bets: int
    won: int
    lost: int
    pushes: int
    total_staked: Decimal
    total_pnl: Decimal
    roi_pct: float
    win_rate: float
    avg_clv_bps: float | None
    profit_factor: float | None
    max_drawdown_pct: float
    verdict: str  # EDGE_CANDIDATE | NO_EDGE | INSUFFICIENT_DATA


class PaperLedger:
    """Paper trading ledger with CLV tracking and Kelly sizing."""

    def __init__(self, store_path: str | None = None) -> None:
        base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
        self.store_path = base / "betting" / "paper_ledger.jsonl"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._bets_cache: list[PaperBet] | None = None

    # ── Write ──

    def record_bet(
        self,
        market_id: str,
        sport: str,
        event: str,
        selection: str,
        odds: float,
        stake: float,
        kelly_fraction: float,
        edge_bps: int,
        kelly_fraction_used: float,
    ) -> PaperBet:
        """Record a new paper bet. Returns the created bet."""
        bet = PaperBet(
            id=f"bet_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}",
            market_id=market_id,
            sport=sport,
            event=event,
            selection=selection,
            odds=Decimal(str(odds)),
            stake=Decimal(str(stake)),
            kelly_fraction=kelly_fraction,
            edge_bps=edge_bps,
            placed_at=datetime.now(UTC).isoformat(),
            kelly_fraction_used=kelly_fraction_used,
        )
        self._append(bet)
        return bet

    def _append(self, bet: PaperBet) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(bet), ensure_ascii=False, default=str) + "\n")

    # ── Settle ──

    def settle_bet(self, bet_id: str, result: str, settled_odds: Decimal | None = None) -> PaperBet | None:
        """Settle a bet: result in {won, lost, push, void}. Returns new bet instance."""
        bets = self._load_all_bets()
        bet = next((b for b in bets if b.id == bet_id), None)
        if not bet:
            return None

        # Create new bet with updated fields (frozen dataclass)
        settled_odds = Decimal(str(settled_odds)) if settled_odds is not None else None

        # Calculate PnL
        if result == "won":
            pnl = bet.stake * (bet.odds - Decimal("1"))
        elif result == "lost":
            pnl = -bet.stake
        else:  # push, void
            pnl = Decimal("0")

        # CLV: compare bet odds to closing line
        clv_bps = None
        if settled_odds is not None and bet.odds > 0:
            clv_bps = int(((Decimal(str(settled_odds)) - bet.odds) / bet.odds) * 10000)

        new_bet = PaperBet(
            id=bet.id,
            market_id=bet.market_id,
            sport=bet.sport,
            event=bet.event,
            selection=bet.selection,
            odds=bet.odds,
            stake=bet.stake,
            kelly_fraction=bet.kelly_fraction,
            edge_bps=bet.edge_bps,
            placed_at=bet.placed_at,
            kelly_fraction_used=bet.kelly_fraction_used,
            status=result,
            settled_at=datetime.now(UTC).isoformat(),
            settled_odds=Decimal(str(settled_odds)) if settled_odds is not None else None,
            result=result,
            pnl=pnl,
            clv_bps=clv_bps,
        )

        # Rewrite file
        bets = [b if b.id != bet_id else new_bet for b in self._load_all_bets()]
        self._rewrite_all(bets)
        return new_bet

    def _load_all_bets(self) -> list[PaperBet]:
        """Load all bets from JSONL."""
        if not self.store_path.exists():
            return []
        bets: list[PaperBet] = []
        try:
            with open(self.store_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        bet = PaperBet(
                            id=data["id"],
                            market_id=data["market_id"],
                            sport=data["sport"],
                            event=data["event"],
                            selection=data["selection"],
                            odds=Decimal(str(data["odds"])),
                            stake=Decimal(str(data["stake"])),
                            kelly_fraction=data["kelly_fraction"],
                            edge_bps=data["edge_bps"],
                            placed_at=data["placed_at"],
                            kelly_fraction_used=data["kelly_fraction_used"],
                            status=data.get("status", "open"),
                            settled_at=data.get("settled_at"),
                            settled_odds=Decimal(str(data["settled_odds"])) if data.get("settled_odds") else None,
                            result=data.get("result"),
                            pnl=Decimal(str(data["pnl"])) if data.get("pnl") is not None else None,
                            clv_bps=data.get("clv_bps"),
                        )
                        bets.append(bet)
                    except (json.JSONDecodeError, KeyError, ValueError) as exc:
                        logger.warning("paper_ledger: corrupt line ignored: %s", exc)
        except OSError as exc:
            logger.warning("paper_ledger: store unreadable: %s", exc)
        return bets

    def _rewrite_all(self, bets: list[PaperBet]) -> None:
        """Rewrite entire JSONL file from current bets."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "w", encoding="utf-8") as fh:
            for bet in bets:
                fh.write(json.dumps(asdict(bet), ensure_ascii=False, default=str) + "\n")

    # ── Accessors ──

    def get_bet(self, bet_id: str) -> PaperBet | None:
        for b in self._load_all_bets():
            if b.id == bet_id:
                return b
        return None

    def get_open_bets(self) -> list[PaperBet]:
        return [b for b in self._load_all_bets() if b.status == "open"]

    def get_settled_bets(self) -> list[PaperBet]:
        return [b for b in self._load_all_bets() if b.status in ("won", "lost", "push", "void")]

    def __len__(self) -> int:
        return len(self._load_all_bets())

    def __iter__(self):
        return iter(self._load_all_bets())

    # ── Metrics ──

    def metrics(self) -> dict:
        """Compute aggregated metrics for the ledger."""
        bets = self._load_all_bets()
        if not bets:
            return PaperBetMetrics(
                total_bets=0,
                open_bets=0,
                settled_bets=0,
                won=0,
                lost=0,
                pushes=0,
                total_staked=Decimal("0"),
                total_pnl=Decimal("0"),
                roi_pct=0.0,
                win_rate=0.0,
                avg_clv_bps=None,
                profit_factor=None,
                max_drawdown_pct=0.0,
                verdict="INSUFFICIENT_DATA",
            ).__dict__

        settled = [b for b in self if b.status in ("won", "lost", "push", "void")]
        open_bets = [b for b in self if b.status == "open"]
        won = [b for b in settled if b.result == "won"]
        lost = [b for b in settled if b.result == "lost"]
        pushes = [b for b in settled if b.result == "push"]

        total_staked = sum((b.stake for b in settled), Decimal("0"))
        total_pnl = sum((b.pnl or Decimal("0") for b in settled), Decimal("0"))

        roi_pct = float(total_pnl / total_staked * 100) if total_staked > 0 else 0.0
        win_rate = len(won) / len(settled) if settled else 0.0

        # CLV
        clv_values = [b.clv_bps for b in settled if b.clv_bps is not None]
        avg_clv = sum(clv_values) / len(clv_values) if clv_values else None
        # avg_clv is used for logging/debugging only
        _ = avg_clv

        # Profit factor
        gross_profit = sum(b.pnl or Decimal("0") for b in won)
        gross_loss = abs(sum(b.pnl or Decimal("0") for b in lost))
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else None

        # Max drawdown
        running = Decimal("0")
        peak = Decimal("0")
        max_dd = Decimal("0")
        for b in settled:
            running += b.pnl or Decimal("0")
            if running > peak:
                peak = running
            dd = peak - running
            if dd > max_dd:
                max_dd = dd
        max_drawdown_pct = float(max_dd / max(peak, Decimal("1")) * 100) if peak > 0 else 0.0

        # Verdict
        if len(settled) < 30:
            verdict = "INSUFFICIENT_DATA"
        elif float(settled[0].clv_bps or 0) > 0 and len(won) / len(settled) > 0.55:
            verdict = "EDGE_CANDIDATE"
        else:
            verdict = "NO_EDGE"

        return PaperBetMetrics(
            total_bets=len(self),
            open_bets=len(open_bets),
            settled_bets=len(settled),
            won=len(won),
            lost=len(lost),
            pushes=len(pushes),
            total_staked=total_staked,
            total_pnl=total_pnl,
            roi_pct=round(roi_pct, 2),
            win_rate=round(win_rate, 4),
            avg_clv_bps=round(sum(clv_values) / len(clv_values), 1) if clv_values else None,
            profit_factor=round(profit_factor, 2) if profit_factor else None,
            max_drawdown_pct=round(max_drawdown_pct, 2),
            verdict=verdict,
        ).__dict__

    # ── Singleton ──


_singleton: PaperLedger | None = None


def get_paper_ledger(store_path: str | None = None) -> PaperLedger:
    global _singleton
    if _singleton is None:
        _singleton = PaperLedger()
    return _singleton


def reset_paper_ledger() -> None:
    global _singleton
    _singleton = None
