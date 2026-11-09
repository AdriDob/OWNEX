"""Copy trading — follow verified traders and replicate their execution.

Deterministic engine with risk controls. Execution defaults to the existing
dry-run / paper executors (safe by default); real execution only when the
TradingConfig explicitly enables REAL mode.

Sources of master trades:
- CEX: replicated through the CCXT adapter family (option 4 — internal
  subaccounts style replication).
- On-chain: Jupiter (Solana) via the existing RealExecutor (option 5).
- Polymarket: signals produced by SmartMoneyCopier in core.polymarket.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

from core.trading.config import TradingConfig
from core.trading.executor import ExecutionEngine, create_executor
from core.trading.models import Order, OrderSide, OrderType, TimeInForce
from core.trading.store import TradingStore

logger = logging.getLogger("catseye.trading.copy")

DEFAULT_EQUITY_USD = Decimal("1000")


@dataclass
class RiskControls:
    """Per-master risk limits (percentages as floats)."""

    max_daily_dd_pct: float = 3.0
    max_total_dd_pct: float = 10.0
    max_open_positions: int = 10
    stop_on_master_dd_pct: float = 15.0
    stop_loss_pct: float = 5.0


@dataclass
class FollowedTrader:
    """A master trader the engine replicates."""

    master_id: str
    name: str
    source: str = "cex"  # cex | onchain | polymarket
    exchange: str = "binance"
    copy_ratio: float = 0.1  # fraction of master notional copied
    max_position_pct: float = 5.0  # % of own equity per position
    allowed_symbols: list[str] = field(default_factory=list)
    risk: RiskControls = field(default_factory=RiskControls)
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["risk"] = asdict(self.risk)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FollowedTrader:
        risk_data = dict(data.get("risk") or {})
        risk = RiskControls(**{k: v for k, v in risk_data.items() if k in RiskControls.__dataclass_fields__})
        allowed = {k: v for k, v in data.items() if k in cls.__dataclass_fields__ and k != "risk"}
        return cls(risk=risk, **allowed)


@dataclass
class MasterTrade:
    """A master's executed trade to replicate."""

    master_id: str
    pair: str
    side: OrderSide
    quantity: Decimal
    price: Decimal | None = None
    master_dd_pct: float | None = None
    source: str = "cex"
    ts: str = ""


@dataclass
class ReplicationResult:
    """Outcome of replicating a master trade."""

    success: bool
    reason: str
    master_trade: dict[str, Any] | None = None
    order: dict[str, Any] | None = None
    size_usd: Decimal = Decimal("0")
    simulated: bool = True


class CopyTradingEngine:
    """Follows traders and replicates their trades under risk controls."""

    def __init__(
        self,
        store: TradingStore | None = None,
        config: TradingConfig | None = None,
        executor: ExecutionEngine | None = None,
        log_decisions: bool = True,
    ) -> None:
        self._store = store or TradingStore()
        self._config = config or TradingConfig()
        self._executor = executor or create_executor(self._config)
        self._log_decisions = log_decisions
        self._lock = threading.RLock()
        self._open_positions: dict[str, list[dict[str, Any]]] = {}
        self._emergency_stop = False

    # ------------------------------------------------------------------ state

    def _status_state(self) -> dict[str, Any]:
        return self._store.get("status") or {}

    def _set_status(self, **fields: Any) -> None:
        state = self._status_state()
        state.update(fields)
        self._store.set("status", state)

    # ---------------------------------------------------------------- masters

    def add_master(self, trader: FollowedTrader) -> FollowedTrader:
        if not trader.master_id or not trader.name:
            raise ValueError("master_id and name are required")
        if trader.copy_ratio <= 0 or trader.copy_ratio > 1:
            raise ValueError("copy_ratio must be in (0, 1]")
        with self._lock:
            if self.get_master(trader.master_id):
                raise ValueError(f"master {trader.master_id} already followed")
            self._store.upsert_item("masters", trader.to_dict(), id_key="master_id")
            self._log("trading:master_added", f"followed trader {trader.name} ({trader.source})", confidence=0.9)
            self._set_status(updated_at=self._store.now_iso())
        return trader

    def remove_master(self, master_id: str) -> bool:
        with self._lock:
            removed = self._store.remove_item("masters", master_id, id_key="master_id")
            if removed:
                self._open_positions.pop(master_id, None)
                self._log("trading:master_removed", f"stopped following {master_id}", confidence=0.9)
                self._set_status(updated_at=self._store.now_iso())
            return removed

    def get_master(self, master_id: str) -> FollowedTrader | None:
        for raw in self._store.get("masters") or []:
            if raw.get("master_id") == master_id:
                return FollowedTrader.from_dict(raw)
        return None

    def set_master_enabled(self, master_id: str, enabled: bool) -> bool:
        """Enable or pause replication for a master; returns False if not found."""
        masters = self._store.get("masters") or []
        updated = False
        for raw in masters:
            if raw.get("master_id") == master_id:
                raw["enabled"] = enabled
                updated = True
        if updated:
            self._store.set("masters", masters)
            self._set_status(updated_at=self._store.now_iso())
        return updated

    def list_masters(self) -> list[FollowedTrader]:
        return [FollowedTrader.from_dict(raw) for raw in self._store.get("masters") or []]

    # ------------------------------------------------------------------ risk

    def _daily_pnl(self) -> Decimal:
        pnl = Decimal("0")
        for value in (self._store.get("daily_pnl") or {}).values():
            try:
                pnl += Decimal(str(value))
            except (TypeError, ValueError):
                continue
        return pnl

    def _equity_usd(self) -> Decimal:
        try:
            balance = self._executor.get_balance("USDC")
            total = getattr(balance, "total", None)
            if total is not None and Decimal(str(total)) > 0:
                return Decimal(str(total))
        except Exception:
            pass
        return DEFAULT_EQUITY_USD

    def daily_dd_pct(self) -> float:
        """Daily drawdown in % of equity (0 when flat/positive)."""
        pnl = self._daily_pnl()
        if pnl >= 0:
            return 0.0
        equity = self._equity_usd()
        if equity <= 0:
            return 0.0
        return abs(float(pnl)) / float(equity) * 100.0

    def risk_breached(self) -> dict[str, Any]:
        """Return the first breached control (empty dict when healthy)."""
        dd = self.daily_dd_pct()
        for master in self.list_masters():
            if not master.enabled:
                continue
            if dd >= master.risk.max_daily_dd_pct:
                return {
                    "control": "max_daily_dd_pct",
                    "master_id": master.master_id,
                    "value": dd,
                    "limit": master.risk.max_daily_dd_pct,
                }
            if len(self._open_positions.get(master.master_id, [])) >= master.risk.max_open_positions:
                return {"control": "max_open_positions", "master_id": master.master_id}
        return {}

    # ----------------------------------------------------------- replication

    def replicate(self, master_id: str, trade: MasterTrade) -> ReplicationResult:
        with self._lock:
            master = self.get_master(master_id)
            if master is None:
                return ReplicationResult(success=False, reason="master not followed")
            if not master.enabled:
                return ReplicationResult(success=False, reason="master disabled")
            if self._emergency_stop:
                return ReplicationResult(success=False, reason="emergency stop active")
            if self.risk_breached():
                return ReplicationResult(success=False, reason="risk control breached")

            if trade.price is None:
                return ReplicationResult(success=False, reason="price required for sizing")

            notional = trade.quantity * trade.price
            size_usd = notional * Decimal(str(master.copy_ratio))
            equity = self._equity_usd()
            max_size = equity * Decimal(str(master.max_position_pct)) / Decimal("100")
            if size_usd > max_size:
                size_usd = max_size
            if trade.pair not in (master.allowed_symbols or []) and master.allowed_symbols:
                return ReplicationResult(success=False, reason=f"symbol {trade.pair} not allowed")

            if trade.master_dd_pct is not None and trade.master_dd_pct > master.risk.stop_on_master_dd_pct:
                return ReplicationResult(success=False, reason="master drawdown beyond stop")

            order = Order(
                id=f"copy_{uuid.uuid4().hex[:12]}",
                side=trade.side,
                order_type=OrderType.MARKET,
                pair=trade.pair.replace("-", "/"),
                quantity=size_usd / trade.price,
                price=trade.price,
                time_in_force=TimeInForce.IOC,
                exchange=master.exchange,
                metadata={"master_id": master_id, "copy": True, "source": trade.source},
            )
            try:
                result = self._executor.execute_order(order)
            except Exception as exc:  # defensive: engine never crashes the pipeline
                logger.exception("copy replication failed for %s", master_id)
                return ReplicationResult(success=False, reason=f"execution error: {exc}")

            if not result.success:
                return ReplicationResult(success=False, reason=result.error or "order rejected")

            open_list = self._open_positions.setdefault(master_id, [])
            open_list.append(
                {
                    "pair": trade.pair,
                    "quantity": str(order.quantity),
                    "price": str(trade.price),
                    "ts": self._store.now_iso(),
                }
            )

            self._log(
                "trading:copy_executed",
                f"replicated {trade.side.name} {trade.pair} for master {master_id}",
                data={"master_id": master_id, "pair": trade.pair, "side": trade.side.name, "size_usd": str(size_usd)},
                confidence=0.95,
                risk_score=master.risk.stop_loss_pct / 100.0,
            )
            self._set_status(updated_at=self._store.now_iso())
            return ReplicationResult(
                success=True,
                reason="replicated",
                master_trade=asdict(trade),
                order=asdict(order),
                size_usd=size_usd,
                simulated=self._config.mode.name != "REAL",
            )

    def record_daily_pnl(self, master_id: str, amount: float) -> None:
        pnl = dict(self._store.get("daily_pnl") or {})
        pnl[master_id] = Decimal(str(pnl.get(master_id, 0))) + Decimal(str(amount))
        self._store.set("daily_pnl", pnl)
        if self.daily_dd_pct() > 0:
            self._log(
                "trading:pnl_updated",
                f"daily pnl for {master_id}: {amount:+.2f}",
                risk_score=min(1.0, self.daily_dd_pct() / 20),
            )

    def open_positions(self) -> dict[str, list[dict[str, Any]]]:
        return {k: list(v) for k, v in self._open_positions.items()}

    # -------------------------------------------------------- emergency stop

    def emergency_stop(self, reason: str) -> dict[str, Any]:
        with self._lock:
            self._emergency_stop = True
            cancelled = 0
            for order in self._executor.get_positions():
                try:
                    res = self._executor.cancel_order(order.id)
                    if res.success:
                        cancelled += 1
                except Exception:
                    continue
            self._open_positions.clear()
            self._set_status(emergency_stop=True, emergency_stop_reason=reason, updated_at=self._store.now_iso())
            self._log("trading:emergency_stop", reason, confidence=0.99, risk_score=1.0)
            return {"cancelled": cancelled, "reason": reason}

    def release_emergency_stop(self) -> None:
        with self._lock:
            self._emergency_stop = False
            self._set_status(emergency_stop=False, updated_at=self._store.now_iso())

    # ----------------------------------------------------------------- status

    def status(self) -> dict[str, Any]:
        state = self._status_state()
        return {
            "mode": self._config.mode.name,
            "emergency_stop": self._emergency_stop or bool(state.get("emergency_stop")),
            "masters": len(self.list_masters()),
            "open_positions": sum(len(v) for v in self._open_positions.values()),
            "daily_pnl_usd": str(self._daily_pnl()),
            "daily_dd_pct": round(self.daily_dd_pct(), 2),
            "equity_usd": str(self._equity_usd()),
            "risk_breached": self.risk_breached(),
            "updated_at": state.get("updated_at"),
        }

    # ---------------------------------------------------------- integration

    def _log(
        self,
        action: str,
        reason: str,
        data: dict[str, Any] | None = None,
        confidence: float = 0.0,
        risk_score: float = 0.0,
    ) -> None:
        if not self._log_decisions:
            return
        try:
            from core.decision_journal.journal import log_decision

            log_decision(
                app_id="trading",
                agent_id="copy_engine",
                action=action,
                reason=reason,
                data_snapshot=data,
                confidence=confidence,
                risk_score=risk_score,
            )
        except Exception:
            logger.debug("decision log skipped (journal unavailable)")


def run_trading_risk_check() -> dict[str, Any]:
    """Scheduler handler: evaluate risk controls and stop if breached."""
    engine = CopyTradingEngine()
    breached = engine.risk_breached()
    if breached and not engine.status()["emergency_stop"]:
        engine.emergency_stop(f"auto stop: {breached['control']}")
        return {"status": "stopped", "reason": breached["control"]}
    return {"status": "ok", "daily_dd_pct": round(engine.daily_dd_pct(), 2), "masters": len(engine.list_masters())}
