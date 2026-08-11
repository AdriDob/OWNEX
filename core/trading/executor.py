from __future__ import annotations

import abc
import logging
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Protocol

from core.trading.config import TradingConfig, TradingMode
from core.trading.dex.jupiter import SOL_MINT, USDC_MINT, JupiterClient
from core.trading.dex.solana_wallet import SolanaWallet
from core.trading.errors import SecurityViolationError
from core.trading.metrics import PerformanceMetrics, TradeRecord, calculate_performance
from core.trading.models import (
    Balance,
    ExecutionReport,
    ExecutionResult,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Trade,
    WalletSnapshot,
)
from core.trading.virtual_wallet import VirtualWallet

logger = logging.getLogger("orion.trading.executor")

COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_CYAN = "\033[96m"
COLOR_RESET = "\033[0m"


class LogStyle(Enum):
    REAL = auto()
    DRY_RUN = auto()
    PAPER = auto()


STYLE_PREFIX: dict[LogStyle, str] = {
    LogStyle.REAL: f"{COLOR_RED}[LIVE]{COLOR_RESET}",
    LogStyle.DRY_RUN: f"{COLOR_YELLOW}[DRY]{COLOR_RESET}",
    LogStyle.PAPER: f"{COLOR_CYAN}[PAPER]{COLOR_RESET}",
}


def mode_style(style: LogStyle, msg: str) -> str:
    return f"{STYLE_PREFIX[style]} {msg}"


class PriceFeed(Protocol):
    def get_price(self, pair: str) -> Decimal: ...
    def get_balances(self, assets: list[str]) -> dict[str, Balance]: ...


class ExecutionEngine(abc.ABC):
    def __init__(self, config: TradingConfig) -> None:
        self.config = config
        self._orders: dict[str, Order] = {}
        self._positions: dict[str, Position] = {}
        self._trades: list[Trade] = []

    @abc.abstractmethod
    def execute_order(self, order: Order) -> ExecutionResult: ...

    @abc.abstractmethod
    def cancel_order(self, order_id: str) -> ExecutionResult: ...

    @abc.abstractmethod
    def get_order_status(self, order_id: str) -> Order | None: ...

    @abc.abstractmethod
    def get_balance(self, asset: str) -> Balance: ...

    @abc.abstractmethod
    def get_positions(self) -> list[Position]: ...

    @abc.abstractmethod
    def get_open_orders(self) -> list[Order]: ...

    def get_trades(self) -> list[Trade]:
        return list(self._trades)

    def get_performance(self, initial_balance: Decimal | None = None) -> PerformanceMetrics:
        records = [
            TradeRecord(
                pair=t.pair,
                side=t.side.name,
                entry_price=t.price,
                exit_price=t.price,
                quantity=t.quantity,
                pnl=Decimal(),
                pnl_percent=Decimal(),
                fee=t.fee,
                entry_time=t.executed_at,
                exit_time=t.executed_at,
            )
            for t in self._trades
        ]
        return calculate_performance(records, initial_balance=initial_balance)

    def _generate_order_id(self) -> str:
        return f"ord_{uuid.uuid4().hex[:16]}"

    def _log_trade(self, style: LogStyle, order: Order, result: ExecutionResult) -> None:
        if not result.report:
            return
        r = result.report
        ts = r.timestamp.strftime("%H:%M:%S.%f")[:12]
        base = f"{ts} | {order.side.name:4} | {order.pair:12} | Qty: {order.quantity:>12}"
        if order.price:
            base += f" @ {order.price:>12}"
        if r.filled_notional:
            base += f" | ${r.filled_notional:>12}"
        if r.total_fees:
            base += f" | Fee: {r.total_fees}"
        logger.info(mode_style(style, base))

    def _log_balance(self, style: LogStyle, balances: dict[str, Balance]) -> None:
        parts = [f"{asset}: {b.free:.4f}" for asset, b in sorted(balances.items()) if b.total > 0]
        if parts:
            logger.info(mode_style(style, f"Balance | {' | '.join(parts)}"))

    def _snapshot_to_dict(self, snap: WalletSnapshot) -> dict[str, Any]:
        return {
            "balances": {k: {"free": str(v.free), "locked": str(v.locked)} for k, v in snap.balances.items()},
            "total_usd": str(snap.total_usd),
            "timestamp": snap.timestamp.isoformat(),
        }


class RealExecutor(ExecutionEngine):
    def __init__(
        self,
        config: TradingConfig,
        wallet: SolanaWallet | None = None,
        jupiter: JupiterClient | None = None,
    ) -> None:
        super().__init__(config)
        self._log_guard(config)
        self._wallet = wallet or SolanaWallet()
        self._jupiter = jupiter or JupiterClient(
            rpc_url=config.rpc_url,
            helius_api_key=config.helius_api_key,
            jupiter_api_url=config.jupiter_api_url,
        )
        if not self._wallet.is_loaded:
            logger.error(mode_style(LogStyle.REAL, "No wallet configured — trades will fail"))
        logger.warning(
            mode_style(LogStyle.REAL, f"REAL mode ACTIVE — wallet: {self._wallet.address or 'NOT CONFIGURED'}")
        )

    def _log_guard(self, config: TradingConfig) -> None:
        if config.is_simulation:
            raise SecurityViolationError(
                "RealExecutor instantiated in simulation mode. This would broadcast real transactions."
            )

    def execute_order(self, order: Order) -> ExecutionResult:
        order.id = self._generate_order_id()
        logger.warning(
            mode_style(LogStyle.REAL, f"EXECUTING ORDER {order.id}: {order.side.name} {order.quantity} {order.pair}")
        )

        if not self._wallet.is_loaded:
            return ExecutionResult(success=False, error="Wallet not configured")

        if not self._wallet.address:
            return ExecutionResult(success=False, error="Wallet address not available")

        try:
            pair = order.pair
            base, quote = pair.split("/") if "/" in pair else (pair, "USDC")
            input_mint, output_mint = self._resolve_mints(base, quote, order.side)

            amount = self._amount_to_lamports(order.quantity, input_mint)
            if amount <= 0:
                return ExecutionResult(success=False, error="Invalid amount")

            quote_result = self._jupiter.quote(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                slippage_bps=int(self.config.default_slippage_pct * 100),
            )
            if not quote_result:
                return ExecutionResult(success=False, error="Failed to get Jupiter quote")

            tx_b64 = self._jupiter.build_swap_tx(
                quote=quote_result,
                wallet_address=self._wallet.address,
            )
            if not tx_b64:
                return ExecutionResult(success=False, error="Failed to build swap transaction")

            signed_tx = self._wallet.sign_and_serialize(tx_b64)
            if not signed_tx:
                return ExecutionResult(success=False, error="Failed to sign transaction")

            sig = self._jupiter.send_transaction(signed_tx)
            if not sig:
                return ExecutionResult(success=False, error="Transaction failed on chain")

            out_amount_dec = Decimal(str(quote_result.out_amount)) / Decimal(10 ** self._decimals(output_mint))
            in_amount_dec = Decimal(str(quote_result.in_amount)) / Decimal(10 ** self._decimals(input_mint))

            order.status = OrderStatus.FILLED
            order.filled_quantity = out_amount_dec if order.side == OrderSide.BUY else in_amount_dec
            fill_price = (
                Decimal(str(quote_result.out_amount)) / Decimal(str(quote_result.in_amount))
                if quote_result.in_amount
                else Decimal()
            )
            order.avg_fill_price = fill_price

            trade = Trade(
                id=f"trade_{uuid.uuid4().hex[:12]}",
                order_id=order.id,
                side=order.side,
                pair=pair,
                quantity=order.filled_quantity,
                price=fill_price if fill_price else Decimal(),
                fee=Decimal("0"),
                fee_asset=quote,
                total=Decimal(str(quote_result.in_amount)) / Decimal(10 ** self._decimals(input_mint)),
                executed_at=datetime.now(UTC),
                exchange="jupiter",
            )

            self._orders[order.id] = order
            self._trades.append(trade)

            report = ExecutionReport(
                order=order,
                trades=[trade],
                simulated=False,
                mode="REAL",
                message=f"Executed: {sig[:16]}... on Jupiter",
            )
            result = ExecutionResult(success=True, report=report)
            self._log_trade(LogStyle.REAL, order, result)
            return result

        except Exception as e:
            logger.exception("Real execution failed for order %s", order.id)
            order.status = OrderStatus.REJECTED
            return ExecutionResult(success=False, error=str(e))

    def _resolve_mints(self, base: str, quote: str, side: OrderSide) -> tuple[str, str]:
        mint_map = {
            "SOL": SOL_MINT,
            "USDC": USDC_MINT,
            "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        }
        base_mint = mint_map.get(base.upper(), base)
        quote_mint = mint_map.get(quote.upper(), quote)
        if side == OrderSide.BUY:
            return quote_mint, base_mint
        return base_mint, quote_mint

    def _amount_to_lamports(self, quantity: Decimal, mint: str) -> int:
        decimals = self._decimals(mint)
        return int(Decimal(str(quantity)) * Decimal(10**decimals))

    def _decimals(self, mint: str) -> int:
        decimals: dict[str, int] = {
            SOL_MINT: 9,
            USDC_MINT: 6,
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": 6,
        }
        return decimals.get(mint, 6)

    def cancel_order(self, order_id: str) -> ExecutionResult:
        logger.warning(mode_style(LogStyle.REAL, "Solana transactions cannot be cancelled once sent"))
        return ExecutionResult(success=False, error="Solana transactions are final")

    def get_order_status(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def get_balance(self, asset: str) -> Balance:
        if not self._wallet.address:
            return Balance()
        try:
            mint = self._resolve_mints(asset, "USDC", OrderSide.BUY)[0]
            amount = self._jupiter.get_token_balance(self._wallet.address, mint)
            decimals = self._decimals(mint)
            return Balance(free=Decimal(str(amount)) / Decimal(10**decimals))
        except Exception as e:
            logger.error("Failed to get balance for %s: %s", asset, e)
            return Balance()

    def get_balances(self) -> dict[str, Balance]:
        if not self._wallet.address:
            return {}
        result: dict[str, Balance] = {}
        for asset in ("SOL", "USDC"):
            result[asset] = self.get_balance(asset)
        return result

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def get_open_orders(self) -> list[Order]:
        return [o for o in self._orders.values() if o.status == OrderStatus.OPEN]


class DryRunExecutor(ExecutionEngine):
    def __init__(self, config: TradingConfig) -> None:
        super().__init__(config)
        logger.warning(mode_style(LogStyle.DRY_RUN, "Dry Run mode ACTIVE — no real trades will execute"))
        self._setup_pnl()

    def _setup_pnl(self) -> None:
        self._hypothetical_pnl: dict[str, Decimal] = {}

    def execute_order(self, order: Order) -> ExecutionResult:
        order.id = self._generate_order_id()
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_fill_price = order.price or Decimal("100")

        simulated_fee = order.notional * Decimal(str(self.config.default_fee_pct)) if order.notional else Decimal()
        simulated_fee = simulated_fee or Decimal("0.01")

        trades = [
            Trade(
                id=f"trade_{uuid.uuid4().hex[:12]}",
                order_id=order.id,
                side=order.side,
                pair=order.pair,
                quantity=order.quantity,
                price=order.avg_fill_price,
                fee=simulated_fee,
                fee_asset=order.pair.split("/")[1],
                total=order.quantity * order.avg_fill_price + simulated_fee,
                executed_at=datetime.now(UTC),
                exchange="dry_run",
            )
        ]

        self._orders[order.id] = order
        self._trades.extend(trades)
        self._track_hypothetical_pnl(order, trades)

        report = ExecutionReport(
            order=order,
            trades=trades,
            simulated=True,
            mode="DRY_RUN",
            message=f"Simulated fill: {order.quantity} {order.pair} @ {order.avg_fill_price}",
        )
        result = ExecutionResult(success=True, report=report)

        self._log_trade(LogStyle.DRY_RUN, order, result)
        return result

    def _track_hypothetical_pnl(self, order: Order, trades: list[Trade]) -> None:
        for t in trades:
            if order.side == OrderSide.BUY:
                self._hypothetical_pnl[t.pair] = -t.total
            else:
                self._hypothetical_pnl[t.pair] = self._hypothetical_pnl.get(t.pair, Decimal()) + t.total

    def cancel_order(self, order_id: str) -> ExecutionResult:
        order = self._orders.get(order_id)
        if order and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.CANCELLED
            return ExecutionResult(
                success=True,
                report=ExecutionReport(order=order, simulated=True, mode="DRY_RUN", message="Cancelled (dry run)"),
            )
        return ExecutionResult(success=False, error="Order not found or not cancellable")

    def get_order_status(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def get_balance(self, asset: str) -> Balance:
        return Balance()

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def get_open_orders(self) -> list[Order]:
        return [o for o in self._orders.values() if o.status == OrderStatus.OPEN]

    def get_hypothetical_pnl(self) -> dict[str, Decimal]:
        return dict(self._hypothetical_pnl)


class PaperTradingExecutor(ExecutionEngine):
    def __init__(
        self,
        config: TradingConfig,
        wallet: VirtualWallet | None = None,
        price_feed: PriceFeed | None = None,
    ) -> None:
        super().__init__(config)
        initial = {
            "USDC": Decimal(str(config.paper_initial_balance_usdc)),
            "SOL": Decimal(str(config.paper_initial_balance_sol)),
        }
        self._wallet = wallet or VirtualWallet(
            initial_balances=initial,
            persist_path=config.paper_wallet_path,
        )
        self._price_feed = price_feed
        logger.warning(
            mode_style(
                LogStyle.PAPER, f"Paper Trading mode ACTIVE — virtual balance: ${config.paper_initial_balance_usdc}"
            )
        )

    @property
    def wallet(self) -> VirtualWallet:
        return self._wallet

    def execute_order(self, order: Order) -> ExecutionResult:
        order.id = self._generate_order_id()

        try:
            result = self._simulate_execution(order)
        except Exception as e:
            order.status = OrderStatus.REJECTED
            return ExecutionResult(success=False, error=str(e))

        self._orders[order.id] = order
        if result.report:
            self._trades.extend(result.report.trades)
        self._wallet.save()

        self._log_trade(LogStyle.PAPER, order, result)
        self._log_balance(LogStyle.PAPER, self._wallet.balances)
        return result

    def _simulate_execution(self, order: Order) -> ExecutionResult:
        pair = order.pair
        base, quote = pair.split("/") if "/" in pair else (pair, "USDC")

        current_price = self._resolve_price(pair)

        slippage = Decimal(str(self.config.paper_slippage_pct)) * current_price
        fill_delay = self.config.paper_latency_ms / 1000.0

        if order.order_type == OrderType.MARKET:
            fill_price = current_price + slippage if order.side == OrderSide.BUY else current_price - slippage
        elif order.order_type == OrderType.LIMIT and order.price:
            if order.side == OrderSide.BUY and order.price < current_price:
                return self._reject_order(order, f"Limit buy {order.price} below market {current_price}")
            if order.side == OrderSide.SELL and order.price > current_price:
                return self._reject_order(order, f"Limit sell {order.price} above market {current_price}")
            fill_price = order.price
        else:
            fill_price = current_price

        if order.side == OrderSide.BUY:
            needed_quote = order.quantity * fill_price
            if not self._wallet.has_enough(quote, needed_quote):
                return self._reject_order(order, f"Insufficient {quote}: need {needed_quote}")
            self._wallet.debit(quote, needed_quote, reason=f"buy {pair}", order_id=order.id)
            self._wallet.credit(base, order.quantity, reason=f"buy {pair}", order_id=order.id)
        else:
            if not self._wallet.has_enough(base, order.quantity):
                return self._reject_order(order, f"Insufficient {base}: need {order.quantity}")
            self._wallet.debit(base, order.quantity, reason=f"sell {pair}", order_id=order.id)
            proceeds = order.quantity * fill_price
            self._wallet.credit(quote, proceeds, reason=f"sell {pair}", order_id=order.id)

        fee_asset = quote
        fee_amount = fill_price * order.quantity * Decimal(str(self.config.paper_fee_pct))
        self._wallet.debit(fee_asset, fee_amount, reason=f"fee {pair}", order_id=order.id)

        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_fill_price = fill_price

        time.sleep(fill_delay)

        trade = Trade(
            id=f"trade_{uuid.uuid4().hex[:12]}",
            order_id=order.id,
            side=order.side,
            pair=pair,
            quantity=order.quantity,
            price=fill_price,
            fee=fee_amount,
            fee_asset=fee_asset,
            total=fill_price * order.quantity + fee_amount,
            executed_at=datetime.now(UTC),
            exchange="paper",
        )

        report = ExecutionReport(
            order=order,
            trades=[trade],
            simulated=True,
            mode="PAPER_TRADING",
            message=f"Simulated fill: {order.quantity} {pair} @ {fill_price} (slippage: {slippage})",
        )
        return ExecutionResult(success=True, report=report)

    def _resolve_price(self, pair: str) -> Decimal:
        if self._price_feed:
            try:
                return self._price_feed.get_price(pair)
            except Exception:
                pass
        return Decimal("100")

    def _reject_order(self, order: Order, reason: str) -> ExecutionResult:
        order.status = OrderStatus.REJECTED
        return ExecutionResult(
            success=False,
            report=ExecutionReport(order=order, simulated=True, mode="PAPER_TRADING", message=reason),
            error=reason,
        )

    def cancel_order(self, order_id: str) -> ExecutionResult:
        order = self._orders.get(order_id)
        if order and order.status in (OrderStatus.PENDING, OrderStatus.OPEN):
            order.status = OrderStatus.CANCELLED
            return ExecutionResult(
                success=True,
                report=ExecutionReport(order=order, simulated=True, mode="PAPER_TRADING", message="Cancelled"),
            )
        return ExecutionResult(success=False, error="Order not found or not cancellable")

    def get_order_status(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def get_balance(self, asset: str) -> Balance:
        return self._wallet.get_balance(asset)

    def get_balances(self) -> dict[str, Balance]:
        return self._wallet.balances

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def get_open_orders(self) -> list[Order]:
        return [o for o in self._orders.values() if o.status == OrderStatus.OPEN]

    def get_performance(self, initial_balance: Decimal | None = None) -> PerformanceMetrics:
        initial = initial_balance or Decimal(str(self.config.paper_initial_balance_usdc))
        return calculate_performance(self._trades_to_records(), initial_balance=initial)

    def _trades_to_records(self) -> list[TradeRecord]:
        records: list[TradeRecord] = []
        i = 0
        while i + 1 < len(self._trades):
            buy = self._trades[i]
            sell = self._trades[i + 1]
            if buy.side == OrderSide.BUY and sell.side == OrderSide.SELL and buy.pair == sell.pair:
                pnl = (sell.price - buy.price) * buy.quantity - buy.fee - sell.fee
                pnl_pct = ((sell.price - buy.price) / buy.price) * Decimal("100")
                duration = (sell.executed_at - buy.executed_at).total_seconds()
                records.append(
                    TradeRecord(
                        pair=buy.pair,
                        side="BUY→SELL",
                        entry_price=buy.price,
                        exit_price=sell.price,
                        quantity=buy.quantity,
                        pnl=pnl,
                        pnl_percent=pnl_pct,
                        fee=buy.fee + sell.fee,
                        entry_time=buy.executed_at,
                        exit_time=sell.executed_at,
                        duration_seconds=duration,
                    )
                )
            i += 2
        return records

    def reset_wallet(self) -> None:
        initial = {
            "USDC": Decimal(str(self.config.paper_initial_balance_usdc)),
            "SOL": Decimal(str(self.config.paper_initial_balance_sol)),
        }
        self._wallet.reset(initial)
        self._orders.clear()
        self._positions.clear()
        self._trades.clear()
        logger.warning(mode_style(LogStyle.PAPER, "Paper wallet reset to initial state"))


def create_executor(config: TradingConfig, **kwargs: Any) -> ExecutionEngine:
    mode = config.mode
    if mode == TradingMode.REAL:
        logger.warning("Initializing REAL executor — trades will be broadcast!")
        return RealExecutor(config)
    if mode == TradingMode.DRY_RUN:
        logger.warning("Initializing DRY RUN executor — no real trades")
        return DryRunExecutor(config)
    if mode == TradingMode.PAPER_TRADING:
        logger.warning("Initializing PAPER TRADING executor — virtual balance")
        return PaperTradingExecutor(config, **kwargs)
    raise ValueError(f"Unknown trading mode: {mode}")
