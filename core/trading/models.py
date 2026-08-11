from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
from typing import Any


class OrderSide(Enum):
    BUY = auto()
    SELL = auto()


class OrderType(Enum):
    MARKET = auto()
    LIMIT = auto()
    STOP_LOSS = auto()
    TAKE_PROFIT = auto()


class OrderStatus(Enum):
    PENDING = auto()
    OPEN = auto()
    FILLED = auto()
    PARTIALLY_FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()
    EXPIRED = auto()


class TimeInForce(Enum):
    GTC = auto()
    IOC = auto()
    FOK = auto()


@dataclass
class Order:
    id: str
    side: OrderSide
    order_type: OrderType
    pair: str
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None
    time_in_force: TimeInForce = TimeInForce.GTC
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal("0")
    avg_fill_price: Decimal | None = None
    fee: Decimal = Decimal("0")
    fee_asset: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    exchange: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED

    @property
    def notional(self) -> Decimal | None:
        if self.avg_fill_price and self.filled_quantity:
            return self.avg_fill_price * self.filled_quantity
        return None


@dataclass
class Position:
    id: str
    pair: str
    side: OrderSide
    entry_price: Decimal
    quantity: Decimal
    current_price: Decimal
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    opened_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: datetime | None = None
    exchange: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_open(self) -> bool:
        return self.closed_at is None

    @property
    def pnl_percent(self) -> Decimal:
        if self.entry_price == Decimal():
            return Decimal()
        if self.side == OrderSide.BUY:
            return ((self.current_price - self.entry_price) / self.entry_price) * Decimal("100")
        return ((self.entry_price - self.current_price) / self.entry_price) * Decimal("100")


@dataclass
class Trade:
    id: str
    order_id: str
    side: OrderSide
    pair: str
    quantity: Decimal
    price: Decimal
    fee: Decimal
    fee_asset: str
    total: Decimal
    executed_at: datetime = field(default_factory=datetime.utcnow)
    exchange: str = ""

    @property
    def notional(self) -> Decimal:
        return self.price * self.quantity


@dataclass
class Balance:
    free: Decimal = Decimal("0")
    locked: Decimal = Decimal("0")

    @property
    def total(self) -> Decimal:
        return self.free + self.locked


@dataclass
class WalletSnapshot:
    balances: dict[str, Balance] = field(default_factory=dict)
    total_usd: Decimal = Decimal("0")
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionReport:
    order: Order
    trades: list[Trade] = field(default_factory=list)
    simulated: bool = False
    mode: str = ""
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def filled_notional(self) -> Decimal:
        result = Decimal()
        for t in self.trades:
            result += t.notional
        return result

    @property
    def total_fees(self) -> Decimal:
        result = Decimal()
        for t in self.trades:
            result += t.fee
        return result


@dataclass
class ExecutionResult:
    success: bool
    report: ExecutionReport | None = None
    error: str | None = None
