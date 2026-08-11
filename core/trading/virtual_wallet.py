from __future__ import annotations

import json
import logging
import uuid
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from core.trading.errors import InsufficientBalanceError, WalletPersistenceError
from core.trading.models import Balance

logger = logging.getLogger("orion.trading.wallet")


class DecimalEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, uuid.UUID):
            return str(o)
        return super().default(o)


def decimal_decoder(d: dict[str, Any]) -> dict[str, Any]:
    for k, v in d.items():
        if isinstance(v, str):
            with suppress(Exception):
                d[k] = Decimal(v)
    return d


@dataclass
class LedgerEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    asset: str = ""
    delta: Decimal = Decimal()
    balance_before: Decimal = Decimal()
    balance_after: Decimal = Decimal()
    reason: str = ""
    order_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PerformanceSnapshot:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_fees_paid: Decimal = Decimal()
    total_pnl: Decimal = Decimal()
    peak_balance: Decimal = Decimal()
    current_balance: Decimal = Decimal()
    timestamp: datetime = field(default_factory=datetime.utcnow)


class VirtualWallet:
    def __init__(
        self,
        initial_balances: dict[str, Decimal] | None = None,
        persist_path: str | Path | None = None,
    ) -> None:
        self._balances: dict[str, Balance] = {}
        self._ledger: list[LedgerEntry] = []
        self._persist_path = Path(persist_path) if persist_path else None
        self._performance = PerformanceSnapshot()

        if initial_balances:
            for asset, amount in initial_balances.items():
                self._balances[asset.upper()] = Balance(free=amount)
                self._performance.peak_balance = max(self._performance.peak_balance, amount)

        if self._persist_path and self._persist_path.exists():
            self._load()

    @property
    def balances(self) -> dict[str, Balance]:
        return dict(self._balances)

    @property
    def ledger(self) -> list[LedgerEntry]:
        return list(self._ledger)

    @property
    def performance(self) -> PerformanceSnapshot:
        return self._performance

    def get_balance(self, asset: str) -> Balance:
        return self._balances.get(asset.upper(), Balance())

    def has_enough(self, asset: str, amount: Decimal) -> bool:
        return self.get_balance(asset.upper()).free >= amount

    def reserve(self, asset: str, amount: Decimal, reason: str = "", order_id: str = "") -> None:
        asset = asset.upper()
        bal = self._balances.get(asset, Balance())
        if bal.free < amount:
            raise InsufficientBalanceError(f"Insufficient {asset}: have {bal.free}, need {amount}")
        bal.free -= amount
        bal.locked += amount
        self._balances[asset] = bal
        self._log(asset, -amount, reason, order_id)

    def release(self, asset: str, amount: Decimal, reason: str = "", order_id: str = "") -> None:
        asset = asset.upper()
        bal = self._balances.get(asset, Balance())
        locked = min(bal.locked, amount)
        bal.locked -= locked
        bal.free += locked
        self._balances[asset] = bal
        self._log(asset, locked, reason, order_id)

    def credit(self, asset: str, amount: Decimal, reason: str = "", order_id: str = "") -> None:
        asset = asset.upper()
        bal = self._balances.get(asset, Balance())
        bal.free += amount
        self._balances[asset] = bal
        self._log(asset, amount, reason, order_id)
        total = bal.free + bal.locked
        if total > self._performance.peak_balance:
            self._performance.peak_balance = total

    def debit(self, asset: str, amount: Decimal, reason: str = "", order_id: str = "") -> None:
        asset = asset.upper()
        bal = self._balances.get(asset, Balance())
        if bal.free < amount:
            raise InsufficientBalanceError(f"Insufficient {asset}: have {bal.free}, need {amount}")
        bal.free -= amount
        self._balances[asset] = bal
        self._log(asset, -amount, reason, order_id)

    def reset(self, initial_balances: dict[str, Decimal] | None = None) -> None:
        self._balances.clear()
        self._ledger.clear()
        self._performance = PerformanceSnapshot()
        if initial_balances:
            for asset, amount in initial_balances.items():
                self._balances[asset.upper()] = Balance(free=amount)
                self._performance.peak_balance = max(self._performance.peak_balance, amount)
        logger.info("Virtual wallet reset")
        self._save()

    def record_trade(self, pnl: Decimal, fee: Decimal) -> None:
        self._performance.total_trades += 1
        if pnl > Decimal():
            self._performance.winning_trades += 1
        elif pnl < Decimal():
            self._performance.losing_trades += 1
        self._performance.total_pnl += pnl
        self._performance.total_fees_paid += fee

    def save(self) -> None:
        self._save()

    def _log(self, asset: str, delta: Decimal, reason: str, order_id: str) -> None:
        bal = self._balances.get(asset, Balance())
        total_before = bal.total - delta
        entry = LedgerEntry(
            asset=asset,
            delta=delta,
            balance_before=total_before,
            balance_after=bal.total,
            reason=reason,
            order_id=order_id,
        )
        self._ledger.append(entry)
        logger.debug("Wallet %s: %s %s (%s)", asset, delta, reason, order_id)

    def _save(self) -> None:
        if not self._persist_path:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            data: dict[str, Any] = {
                "balances": {
                    asset: {"free": str(b.free), "locked": str(b.locked)} for asset, b in self._balances.items()
                },
                "performance": asdict(self._performance),
                "ledger": [
                    {k: str(v) if isinstance(v, (Decimal, datetime)) else v for k, v in asdict(e).items()}
                    for e in self._ledger[-1000:]
                ],
                "updated_at": datetime.utcnow().isoformat(),
            }
            self._persist_path.write_text(json.dumps(data, indent=2, cls=DecimalEncoder))
        except Exception as e:
            raise WalletPersistenceError(f"Failed to save wallet: {e}") from e

    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text())
            for asset, bdata in data.get("balances", {}).items():
                self._balances[asset] = Balance(
                    free=Decimal(str(bdata.get("free", "0"))),
                    locked=Decimal(str(bdata.get("locked", "0"))),
                )
            perf = data.get("performance", {})
            self._performance = PerformanceSnapshot(
                total_trades=perf.get("total_trades", 0),
                winning_trades=perf.get("winning_trades", 0),
                losing_trades=perf.get("losing_trades", 0),
                total_fees_paid=Decimal(str(perf.get("total_fees_paid", "0"))),
                total_pnl=Decimal(str(perf.get("total_pnl", "0"))),
                peak_balance=Decimal(str(perf.get("peak_balance", "0"))),
                current_balance=Decimal(str(perf.get("current_balance", "0"))),
            )
            logger.info("Virtual wallet loaded from %s", self._persist_path)
        except Exception as e:
            raise WalletPersistenceError(f"Failed to load wallet: {e}") from e
