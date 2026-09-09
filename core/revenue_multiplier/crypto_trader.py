from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from core.revenue_multiplier.config import ExecutionMode, RevenueMultiplierConfig
from core.revenue_multiplier.models import TradeSignal

logger = logging.getLogger("orion.revenue.crypto")


class CryptoTradingOrchestrator:
    def __init__(self, config: RevenueMultiplierConfig) -> None:
        self._config = config
        self._signals: list[TradeSignal] = []
        self._trades_executed: int = 0
        self._pnl: Decimal = Decimal("0")

    def scan_opportunities(self) -> list[TradeSignal]:
        signals = self._scan_dex_pairs()
        signals.extend(self._scan_new_listings())
        signals.sort(key=lambda s: s.confidence, reverse=True)
        self._signals = signals[: self._config.max_concurrent_trades]
        return self._signals

    def _scan_dex_pairs(self) -> list[TradeSignal]:
        signals: list[TradeSignal] = []
        for pair in self._config.trading_pair_whitelist:
            try:
                price = self._fetch_price(pair)
                if price is None:
                    continue
                signals.append(
                    TradeSignal(
                        pair=pair,
                        side="BUY",
                        confidence=0.5,
                        entry_price=price,
                        stop_loss=price * Decimal("0.95"),
                        take_profit=price * Decimal("1.15"),
                        quantity=self._calculate_quantity(price),
                        reason="Whitelist pair — periodic scan",
                        strategy="passive_scan",
                    )
                )
            except Exception as e:
                logger.warning("Failed to scan %s: %s", pair, e)
        return signals

    def _scan_new_listings(self) -> list[TradeSignal]:
        try:
            return self._fetch_new_pairs()
        except Exception as e:
            logger.debug("New pair scan failed: %s", e)
            return []

    def _fetch_price(self, pair: str) -> Decimal | None:
        try:
            import httpx

            base = pair.split("/")[0]
            resp = httpx.get(
                "https://api.jup.ag/price/v2",
                params={"ids": base},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            price_str = data.get("data", {}).get(base, {}).get("price", "0")
            return Decimal(str(price_str)) if price_str != "0" else None
        except Exception as e:
            logger.debug("Price fetch failed for %s: %s", pair, e)
            return None

    def _fetch_new_pairs(self) -> list[TradeSignal]:
        try:
            import httpx

            resp = httpx.get(
                "https://api.dexscreener.com/latest/dex/search",
                params={"q": "solana"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            signals: list[TradeSignal] = []
            for pair in (data.get("pairs") or [])[:10]:
                if pair.get("chainId") != "solana":
                    continue
                price_usd = pair.get("priceUsd", "0")
                if price_usd == "0":
                    continue
                base = pair.get("baseToken", {}).get("symbol", "UNKNOWN")
                signals.append(
                    TradeSignal(
                        pair=f"{base}/USDC",
                        side="BUY",
                        confidence=0.2,
                        entry_price=Decimal(str(price_usd)),
                        stop_loss=Decimal(str(price_usd)) * Decimal("0.8"),
                        take_profit=Decimal(str(price_usd)) * Decimal("2.0"),
                        quantity=self._calculate_quantity(Decimal(str(price_usd))),
                        reason=f"New pair: {pair.get('pairAddress', '')[:12]}... on DexScreener",
                        strategy="new_pair_sniper",
                    )
                )
            return signals
        except Exception as e:
            logger.debug("DexScreener scan failed: %s", e)
            return []

    def _calculate_quantity(self, price: Decimal) -> Decimal:
        if price == Decimal("0"):
            return Decimal("0")
        max_pos = Decimal(str(self._config.max_position_usd))
        return max_pos / price

    def execute_trade(self, signal: TradeSignal) -> dict[str, Any]:
        if self._config.mode == ExecutionMode.DRY_RUN:
            return self._dry_run_execute(signal)
        if self._config.mode == ExecutionMode.PAPER:
            return self._paper_execute(signal)
        return self._live_execute(signal)

    def _dry_run_execute(self, signal: TradeSignal) -> dict[str, Any]:
        logger.info("[DRY] Would execute: BUY %.4f %s @ %.6f", signal.quantity, signal.pair, signal.entry_price)
        return {"success": True, "simulated": True, "signal": signal}

    def _paper_execute(self, signal: TradeSignal) -> dict[str, Any]:
        from core.trading import Order, OrderSide, OrderType, PaperTradingExecutor, TradingConfig, TradingMode

        cfg = TradingConfig(
            mode=TradingMode.PAPER_TRADING,
            paper_initial_balance_usdc=10000,
            pair=signal.pair,
        )
        executor = PaperTradingExecutor(cfg)
        order = Order(
            id=f"revenue_{signal.pair}",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            pair=signal.pair,
            quantity=signal.quantity,
        )
        result = executor.execute_order(order)
        if result.success:
            self._trades_executed += 1
            logger.info("[PAPER] Executed BUY %.4f %s", signal.quantity, signal.pair)
        return {"success": result.success, "executor_result": result, "signal": signal}

    def _live_execute(self, signal: TradeSignal) -> dict[str, Any]:
        logger.warning("[LIVE] Executing BUY %.4f %s @ %.6f", signal.quantity, signal.pair, signal.entry_price)
        from core.trading import Order, OrderSide, OrderType, TradingConfig, TradingMode
        from core.trading.dex import JupiterClient, SolanaWallet
        from core.trading.executor import RealExecutor

        cfg = TradingConfig(
            mode=TradingMode.REAL,
            rpc_url=self._config.rpc_url,
            jupiter_api_url=self._config.jupiter_api_url,
            slippage_bps=self._config.slippage_bps,
        )
        wallet = SolanaWallet()
        jupiter = JupiterClient(
            rpc_url=self._config.rpc_url,
            jupiter_api_url=self._config.jupiter_api_url,
        )
        executor = RealExecutor(cfg, wallet=wallet, jupiter=jupiter)
        order = Order(
            id=f"revenue_{signal.pair}_{signal.timestamp.timestamp():.0f}",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            pair=signal.pair,
            quantity=signal.quantity,
        )
        result = executor.execute_order(order)
        if result.success:
            self._trades_executed += 1
            logger.warning("[LIVE] Trade executed: %s", signal.pair)
        return {"success": result.success, "executor_result": result, "signal": signal}

    def get_summary(self) -> dict[str, Any]:
        return {
            "signals_pending": len(self._signals),
            "trades_executed": self._trades_executed,
            "pnl": str(self._pnl),
            "mode": self._config.mode.value,
        }
