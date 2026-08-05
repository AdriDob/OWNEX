"""Hummingbot Adapter for OWNEX.

Integration with Hummingbot - open-source market making and arbitrage bot.
Based on: https://github.com/hummingbot/hummingbot
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.investment.hummingbot")


class HummingbotAdapter:
    """Hummingbot market making and arbitrage adapter.

    Provides:
    - Market making strategies
    - Arbitrage strategies (cross-exchange, triangular)
    - Liquidity mining
    - Perpetual trading
    - Strategy creation and management
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._hummingbot_dir = Path(self._config.get("hummingbot_dir", "hummingbot_user"))
        self._conf_dir = self._hummingbot_dir / "conf"
        self._scripts_dir = self._hummingbot_dir / "scripts"
        self._logs_dir = self._hummingbot_dir / "logs"
        self._data_dir = self._hummingbot_dir / "data"

    @property
    def name(self) -> str:
        return "hummingbot"

    def _ensure_dirs(self) -> None:
        for d in [self._hummingbot_dir, self._conf_dir, self._scripts_dir, self._logs_dir, self._data_dir]:
            d.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> bool:
        """Initialize Hummingbot environment."""
        try:
            self._ensure_dirs()

            # Create default configs for connectors
            await self._create_default_connectors()

            logger.info("Hummingbot initialized at %s", self._hummingbot_dir)
            return True
        except Exception as e:
            logger.error("Hummingbot initialization failed: %s", e)
            return False

    async def _create_default_connectors(self) -> None:
        """Create default exchange connector configs."""
        exchanges = ["binance", "coinbase_pro", "kraken", "bybit", "gate_io"]
        for exchange in exchanges:
            config_file = self._conf_dir / f"{exchange}.yml"
            if not config_file.exists():
                config_content = f"""# {exchange} connector configuration
connector: {exchange}
api_key: ""
api_secret: ""
"""
                if exchange in ["binance", "bybit", "gate_io"]:
                    config_content += 'api_passphrase: ""\n'
                config_file.write_text(config_content)

    async def list_strategies(self) -> list[dict[str, Any]]:
        """List available strategies."""
        strategies = []
        strategy_dir = Path("hummingbot/strategy")
        if strategy_dir.exists():
            for py_file in strategy_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                strategies.append(
                    {
                        "name": py_file.stem,
                        "file": py_file.name,
                    }
                )
        return strategies

    async def create_strategy_config(
        self,
        strategy_name: str,
        config: dict[str, Any],
    ) -> bool:
        """Create a strategy configuration file."""
        try:
            config_file = self._conf_dir / f"{strategy_name}.yml"
            import yaml

            config_file.write_text(yaml.dump(config, default_flow_style=False))
            return True
        except Exception as e:
            logger.error("Strategy config creation failed: %s", e)
            return False

    # Market Making Strategies
    async def create_pure_market_making_config(
        self,
        exchange: str,
        market: str,
        bid_spread: float = 0.01,
        ask_spread: float = 0.01,
        order_amount: float = 100,
        order_refresh_time: float = 15.0,
        max_order_age: float = 30.0,
    ) -> dict[str, Any]:
        """Create pure market making strategy config."""
        return {
            "strategy": "pure_market_making",
            "exchange": exchange,
            "market": market,
            "bid_spread": bid_spread,
            "ask_spread": ask_spread,
            "order_amount": order_amount,
            "order_refresh_time": order_refresh_time,
            "max_order_age": max_order_age,
            "order_levels": 1,
            "level_distances": [0],
            "level_amounts": [1],
            "inventory_skew_enabled": False,
            "inventory_target_base_pct": 50,
            "inventory_range_multiplier": 1,
            "filled_order_delay": 60,
            "hanging_orders_enabled": False,
            "hanging_orders_cancel_pct": 0.2,
        }

    async def create_cross_exchange_arbitrage_config(
        self,
        exchange_1: str,
        exchange_2: str,
        market: str,
        min_profitability: float = 0.003,
    ) -> dict[str, Any]:
        """Create cross-exchange arbitrage config."""
        return {
            "strategy": "cross_exchange_market_making",
            "exchange_1": exchange_1,
            "exchange_2": exchange_2,
            "market": market,
            "min_profitability": min_profitability,
            "order_amount": 100,
            "order_refresh_time": 15.0,
        }

    async def create_perpetual_market_making_config(
        self,
        exchange: str,
        market: str,
        leverage: int = 10,
        bid_spread: float = 0.01,
        ask_spread: float = 0.01,
    ) -> dict[str, Any]:
        """Create perpetual market making config."""
        return {
            "strategy": "perpetual_market_making",
            "exchange": exchange,
            "market": market,
            "leverage": leverage,
            "bid_spread": bid_spread,
            "ask_spread": ask_spread,
            "order_amount": 100,
            "order_refresh_time": 15.0,
        }

    # Arbitrage
    async def create_triangular_arbitrage_config(
        self,
        exchange: str,
        markets: list[str],
        min_profitability: float = 0.002,
    ) -> dict[str, Any]:
        """Create triangular arbitrage config."""
        return {
            "strategy": "triangular_arbitrage",
            "exchange": exchange,
            "markets": markets,
            "min_profitability": min_profitability,
            "order_amount": 100,
        }

    # Run strategies
    async def run_strategy(self, strategy_name: str) -> dict[str, Any]:
        """Run a Hummingbot strategy."""
        try:
            cmd = [
                "hummingbot",
                "start",
                "--config",
                str(self._conf_dir / f"{strategy_name}.yml"),
            ]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return {
                "success": True,
                "pid": process.pid,
            }
        except Exception as e:
            logger.error("Strategy run failed: %s", e)
            return {"error": str(e)}

    async def get_status(self) -> dict[str, Any]:
        """Get Hummingbot status."""
        try:
            # Check for running processes
            result = subprocess.run(["pgrep", "-f", "hummingbot"], capture_output=True, text=True)
            running = result.returncode == 0

            return {
                "running": running,
                "pids": result.stdout.strip().split() if running else [],
                "config_dir": str(self._conf_dir),
            }
        except Exception as e:
            logger.error("Status check failed: %s", e)
            return {"error": str(e)}

    async def stop_all(self) -> bool:
        """Stop all Hummingbot processes."""
        try:
            subprocess.run(["pkill", "-f", "hummingbot"])
            return True
        except Exception as e:
            logger.error("Stop failed: %s", e)
            return False

    # Liquidity Mining
    async def create_liquidity_mining_config(
        self,
        exchange: str,
        market: str,
        reward_token: str,
        target_volume: float,
    ) -> dict[str, Any]:
        """Create liquidity mining config."""
        return {
            "strategy": "liquidity_mining",
            "exchange": exchange,
            "market": market,
            "reward_token": reward_token,
            "target_volume": target_volume,
        }

    # Avellaneda Market Making (advanced)
    async def create_avellaneda_config(
        self,
        exchange: str,
        market: str,
        risk_factor: float = 0.1,
        order_amount: float = 100,
    ) -> dict[str, Any]:
        """Create Avellaneda-Stoikov market making config."""
        return {
            "strategy": "avellaneda_market_making",
            "exchange": exchange,
            "market": market,
            "risk_factor": risk_factor,
            "order_amount": order_amount,
            "order_refresh_time": 15.0,
            "spread_factor": 1.0,
        }


def build_hummingbot_adapter(config: dict[str, Any] | None = None) -> HummingbotAdapter:
    """Factory function to create Hummingbot adapter."""
    return HummingbotAdapter(config)
