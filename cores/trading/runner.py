"""Strategy runner — the ONLY path to live execution.

Safety model (explicit human decision, see plan L5b):
- Paper trading needs NO arming (simulates, moves no money).
- Live execution requires explicit arm(strategy_id, purpose=...); the purpose
  string is recorded in the audit trail. Arming is reversible: disarm() anytime.
- Every live signal passes the strategy envelope BEFORE the engine runs:
  kill switch, venue allowlist, leverage ban, daily-loss → auto-disarm.
- Every decision (arm/disarm/refuse/execute/result) appends to an audit JSONL.
- Trading NEVER feeds P(CASH) rankings; only realized P&L feeds Capital.

If any engine is missing, live refuses with a reason (paper still works).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.trading.runner")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _audit_path() -> Path:
    base = os.environ.get("OWNEX_DATA_DIR", "data")
    return Path(base) / "trading" / "audit.jsonl"


@dataclass(slots=True)
class StrategyEnvelope:
    """Hard risk bounds for one strategy. Code-enforced, not advisory."""

    strategy_id: str
    allocated_capital_usd: float = 1000.0
    max_position_pct: float = 5.0
    max_daily_loss_pct: float = 2.0
    venues_allowlist: tuple[str, ...] = ()
    allow_leverage: bool = False
    armed: bool = False
    armed_at: str = ""
    armed_purpose: str = ""


class StrategyRunner:
    """Paper-by-default runner with explicit live arming + audit trail."""

    def __init__(
        self,
        capital_engine: Any | None = None,
        risk_engine: Any | None = None,
        audit_path: str | Path | None = None,
    ) -> None:
        self._capital_engine = capital_engine
        self._risk_engine = risk_engine
        self._audit_path = Path(audit_path) if audit_path else _audit_path()
        self._envelopes: dict[str, StrategyEnvelope] = {}
        self._paper_engine: Any | None = None
        self._live_engine: Any | None = None

    # ── Registration & arming ──

    def register(self, envelope: StrategyEnvelope) -> None:
        self._envelopes[envelope.strategy_id] = envelope
        self._audit("register", envelope.strategy_id, {"envelope": asdict(envelope)})

    def arm(self, strategy_id: str, purpose: str) -> dict[str, Any]:
        """Explicit human activation for live execution. Purpose is mandatory."""
        env = self._envelopes.get(strategy_id)
        if env is None:
            return {"armed": False, "reason": f"unknown strategy: {strategy_id}"}
        if not (purpose or "").strip():
            return {"armed": False, "reason": "purpose is required to arm live trading"}
        if self._capital_engine is None or self._risk_engine is None:
            return {"armed": False, "reason": "live execution unavailable: engines not configured"}
        env.armed = True
        env.armed_at = _now_iso()
        env.armed_purpose = purpose.strip()
        self._live_engine = None  # rebuilt lazily with current engines
        self._audit("arm", strategy_id, {"purpose": env.armed_purpose})
        return {"armed": True, "strategy_id": strategy_id, "armed_at": env.armed_at}

    def disarm(self, strategy_id: str, reason: str = "manual") -> dict[str, Any]:
        env = self._envelopes.get(strategy_id)
        if env is None:
            return {"armed": False, "reason": f"unknown strategy: {strategy_id}"}
        was_armed = env.armed
        env.armed = False
        self._audit("disarm", strategy_id, {"was_armed": was_armed, "reason": reason})
        return {"armed": False, "strategy_id": strategy_id}

    def is_armed(self, strategy_id: str) -> bool:
        env = self._envelopes.get(strategy_id)
        return bool(env and env.armed)

    # ── Execution ──

    async def run_signal(self, strategy_id: str, signal: Any, live: bool = False) -> dict[str, Any]:
        """Run one signal. Paper needs no arming; live requires it + envelope."""
        env = self._envelopes.get(strategy_id)
        if env is None:
            return self._refuse(strategy_id, signal, "unknown strategy")
        if live:
            refusal = self._check_live_allowed(env, signal)
            if refusal is not None:
                return refusal
            engine = self._get_live_engine()
            if engine is None:
                return self._refuse(strategy_id, signal, "live execution unavailable: engines not configured")
            try:
                result = await engine.execute_signal(signal, strategy_id)
            except Exception as exc:
                return self._refuse(strategy_id, signal, f"live engine error: {exc}")
            self._audit(
                "live_result",
                strategy_id,
                {"success": result.success, "error": result.error, "order_id": result.order_id},
            )
            return {"success": result.success, "mode": "live", "error": result.error, "order_id": result.order_id}
        engine = self._get_paper_engine()
        try:
            result = await engine.execute_signal(signal, strategy_id)
        except Exception as exc:
            return self._refuse(strategy_id, signal, f"paper engine error: {exc}")
        self._audit(
            "paper_result",
            strategy_id,
            {"success": result.success, "error": result.error, "order_id": result.order_id},
        )
        return {"success": result.success, "mode": "paper", "error": result.error, "order_id": result.order_id}

    def _check_live_allowed(self, env: StrategyEnvelope, signal: Any) -> dict[str, Any] | None:
        """Envelope enforcement. Returns refusal dict or None when allowed."""
        if not env.armed:
            return self._refuse(env.strategy_id, signal, "strategy not armed (explicit arm() required)")
        if self._kill_active(env.strategy_id):
            return self._refuse(env.strategy_id, signal, "kill switch active")
        venue = str((getattr(signal, "metadata", None) or {}).get("exchange", "") or "").lower()
        if env.venues_allowlist and venue and venue not in [v.lower() for v in env.venues_allowlist]:
            return self._refuse(env.strategy_id, signal, f"venue not allowlisted: {venue or 'unknown'}")
        leverage = (getattr(signal, "metadata", None) or {}).get("leverage", 1)
        try:
            leveraged = float(leverage) > 1.0
        except (TypeError, ValueError):
            leveraged = False
        if leveraged and not env.allow_leverage:
            return self._refuse(env.strategy_id, signal, "leverage not allowed by envelope")
        if self._daily_loss_breached(env):
            self._trigger_max_loss(env)
            return self._refuse(env.strategy_id, signal, "max daily loss breached: auto-disarmed + kill switch")
        return None

    # ── Internals ──

    def _refuse(self, strategy_id: str, signal: Any, reason: str) -> dict[str, Any]:
        self._audit("refuse", strategy_id, {"reason": reason, "signal_id": getattr(signal, "signal_id", "")})
        return {"success": False, "mode": "refused", "error": reason, "order_id": None}

    def _kill_active(self, strategy_id: str) -> bool:
        engine = self._risk_engine
        if engine is None:
            return False
        try:
            from cores.trading.contracts import KillSwitchLevel

            ks = engine.kill_switch
            if ks.is_active(KillSwitchLevel.GLOBAL):
                return True
            return bool(ks.is_active(KillSwitchLevel.STRATEGY, strategy_id))
        except Exception:
            return False

    def _daily_loss_breached(self, env: StrategyEnvelope) -> bool:
        engine = self._risk_engine
        if engine is None:
            return False
        try:
            pnl = Decimal(str(engine.metrics.daily_pnl))
            limit = Decimal(str(env.allocated_capital_usd)) * Decimal(str(env.max_daily_loss_pct)) / Decimal("100")
            return pnl <= -abs(limit)
        except Exception:
            return False

    def _trigger_max_loss(self, env: StrategyEnvelope) -> None:
        engine = self._risk_engine
        if engine is None:
            return
        try:
            from cores.trading.contracts import KillSwitchLevel

            engine.kill_switch.activate(
                KillSwitchLevel.STRATEGY,
                reason=f"max daily loss breached ({env.max_daily_loss_pct}% of ${env.allocated_capital_usd})",
                trigger="strategy_runner",
                affected=[env.strategy_id],
            )
        except Exception as exc:
            logger.warning("Kill switch trigger failed: %s", exc)
        env.armed = False
        self._audit("auto_disarm_max_loss", env.strategy_id, {})

    def _get_paper_engine(self) -> Any:
        if self._paper_engine is None:
            from cores.trading.execution import ExecutionEngine

            self._paper_engine = ExecutionEngine(
                capital_engine=self._capital_engine, risk_engine=self._risk_engine, mode="paper"
            )
        return self._paper_engine

    def _get_live_engine(self) -> Any | None:
        if self._capital_engine is None or self._risk_engine is None:
            return None
        if self._live_engine is None:
            from cores.trading.execution import ExecutionEngine

            self._live_engine = ExecutionEngine(
                capital_engine=self.capital_engine, risk_engine=self._risk_engine, mode="live"
            )
        return self._live_engine

    @property
    def capital_engine(self) -> Any:
        return self._capital_engine

    def _audit(self, action: str, strategy_id: str, detail: dict[str, Any]) -> None:
        record = {
            "ts": _now_iso(),
            "actor": "system",
            "action": action,
            "strategy_id": strategy_id,
            "detail": detail,
        }
        try:
            self._audit_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._audit_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except Exception as exc:
            logger.warning("Audit append failed: %s", exc)


_runner: StrategyRunner | None = None


def get_strategy_runner() -> StrategyRunner:
    """Process singleton (paper-capable; live needs engines + arm)."""
    global _runner
    if _runner is None:
        _runner = StrategyRunner()
    return _runner
