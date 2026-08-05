"""Freqtrade Strategy Runner Adapter for OWNEX.

Integration with Freqtrade - the open-source crypto trading bot framework.
Based on: https://github.com/freqtrade/freqtrade
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.investment.freqtrade")


class FreqtradeAdapter:
    """Freqtrade strategy runner and backtesting adapter.

    Provides:
    - Strategy execution (dry-run/live)
    - Backtesting engine
    - Hyperopt optimization
    - Performance analytics
    - Pair management
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._freqtrade_dir = Path(self._config.get("freqtrade_dir", "freqtrade_user"))
        self._config_file = self._freqtrade_dir / "config.json"
        self._strategies_dir = self._freqtrade_dir / "strategies"
        self._data_dir = self._freqtrade_dir / "data"

    @property
    def name(self) -> str:
        return "freqtrade"

    def _ensure_dirs(self) -> None:
        """Ensure required directories exist."""
        self._freqtrade_dir.mkdir(parents=True, exist_ok=True)
        self._strategies_dir.mkdir(parents=True, exist_ok=True)
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def _get_default_config(self) -> dict[str, Any]:
        """Generate default Freqtrade configuration."""
        return {
            "stake_currency": "USDT",
            "stake_amount": 100,
            "tradable_balance_ratio": 0.99,
            "fiat_display_currency": "USD",
            "dry_run": True,
            "dry_run_wallet": 1000,
            "cancel_open_orders_on_exit": False,
            "unfilledtimeout": {
                "entry": 10,
                "exit": 30,
                "unit": "minutes",
            },
            "entry_pricing": {
                "price_side": "same",
                "use_order_book": True,
                "order_book_top": 1,
                "price_last_balance": 0.0,
                "check_depth_of_market": {
                    "enabled": False,
                    "bids_to_ask_delta": 1,
                },
            },
            "exit_pricing": {
                "price_side": "same",
                "use_order_book": True,
                "order_book_top": 1,
            },
            "exchange": {
                "name": "binance",
                "key": "${BINANCE_API_KEY}",
                "secret": "${BINANCE_API_SECRET}",
                "ccxt_config": {"enableRateLimit": True},
                "ccxt_async_config": {"enableRateLimit": True},
                "pair_whitelist": [
                    "BTC/USDT",
                    "ETH/USDT",
                    "BNB/USDT",
                    "SOL/USDT",
                ],
                "pair_blacklist": [],
            },
            "pairlists": [
                {"method": "StaticPairList"},
            ],
            "telegram": {
                "enabled": False,
            },
            "api_server": {
                "enabled": True,
                "listen_ip_address": "127.0.0.1",
                "listen_port": 8080,
                "verbosity": "error",
                "enable_openapi": False,
                "jwt_secret_key": "somethingrandom",
            },
            "bot_name": "ownex-freqtrade",
            "initial_state": "running",
            "force_entry_enable": False,
            "internals": {
                "process_throttle_secs": 5,
            },
        }

    async def initialize(self) -> bool:
        """Initialize Freqtrade environment."""
        try:
            self._ensure_dirs()

            # Write default config if not exists
            if not self._config_file.exists():
                config = self._get_default_config()
                config.update(self._config.get("overrides", {}))
                self._config_file.write_text(json.dumps(config, indent=2))

            # Download sample data if needed
            await self._download_data()

            logger.info("Freqtrade initialized at %s", self._freqtrade_dir)
            return True
        except Exception as e:
            logger.error("Freqtrade initialization failed: %s", e)
            return False

    async def _download_data(self) -> None:
        """Download historical data for backtesting."""
        try:
            import subprocess

            pairs = self._config.get("pairs", ["BTC/USDT", "ETH/USDT"])
            timerange = self._config.get("timerange", "20240101-")

            for pair in pairs:
                cmd = [
                    "freqtrade",
                    "download-data",
                    "--pairs",
                    pair,
                    "--timerange",
                    timerange,
                    "--timeframe",
                    "5m",
                    "--config",
                    str(self._config_file),
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    logger.warning("Data download failed for %s: %s", pair, result.stderr)
        except Exception as e:
            logger.warning("Data download error: %s", e)

    async def run_backtest(
        self,
        strategy: str,
        pairs: list[str] | None = None,
        timerange: str | None = None,
        timeframe: str = "5m",
    ) -> dict[str, Any]:
        """Run backtest for a strategy."""
        try:
            import subprocess

            pairs = pairs or self._config.get("pairs", ["BTC/USDT"])
            timerange = timerange or self._config.get("timerange", "20240101-")

            cmd = [
                "freqtrade",
                "backtesting",
                "--strategy",
                strategy,
                "--config",
                str(self._config_file),
                "--pairs",
                *pairs,
                "--timerange",
                timerange,
                "--timeframe",
                timeframe,
                "--export",
                "trades",
                "--export-filename",
                f"backtest_{strategy}",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            # Parse results
            return self._parse_backtest_result(result.stdout, result.stderr, result.returncode)
        except Exception as e:
            logger.error("Backtest failed: %s", e)
            return {"error": str(e)}

    def _parse_backtest_result(self, stdout: str, stderr: str, returncode: int) -> dict[str, Any]:
        """Parse backtest output."""
        if returncode != 0:
            return {"success": False, "error": stderr}

        # Try to extract key metrics from output
        result = {"success": True, "raw_output": stdout}

        # Look for summary table
        if "BACKTESTING REPORT" in stdout:
            lines = stdout.split("\n")
            for line in lines:
                if "Profit" in line and "%" in line:
                    result["profit_pct"] = line.strip()
                if "Total/Daily" in line:
                    result["daily_profit"] = line.strip()
                if "Max Drawdown" in line:
                    result["max_drawdown"] = line.strip()
                if "Sharpe" in line:
                    result["sharpe"] = line.strip()

        return result

    async def run_hyperopt(
        self,
        strategy: str,
        epochs: int = 100,
        spaces: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run hyperopt optimization."""
        try:
            import subprocess

            spaces = spaces or ["buy", "sell", "roi", "stoploss", "trailing"]

            cmd = [
                "freqtrade",
                "hyperopt",
                "--strategy",
                strategy,
                "--config",
                str(self._config_file),
                "--epochs",
                str(epochs),
                "--spaces",
                *spaces,
                "--hyperopt-loss",
                "SharpeHyperOptLoss",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

            return {
                "success": result.returncode == 0,
                "stdout": stdout if (stdout := result.stdout) else "",
                "stderr": result.stderr,
            }
        except Exception as e:
            logger.error("Hyperopt failed: %s", e)
            return {"error": str(e)}

    async def list_strategies(self) -> list[dict[str, Any]]:
        """List available strategies."""
        strategies = []
        for py_file in self._strategies_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            strategies.append(
                {
                    "name": py_file.stem,
                    "file": py_file.name,
                    "path": str(py_file),
                }
            )
        return strategies

    async def create_strategy_template(self, name: str, template: str = "sample") -> bool:
        """Create a new strategy from template."""
        try:
            import subprocess

            cmd = [
                "freqtrade",
                "new-strategy",
                "--strategy",
                name,
                "--template",
                template,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                # Move to our strategies dir
                src = Path(f"user_data/strategies/{name}.py")
                if src.exists():
                    dst = self._strategies_dir / f"{name}.py"
                    src.rename(dst)
            return result.returncode == 0
        except Exception as e:
            logger.error("Strategy creation failed: %s", e)
            return False

    async def get_performance(self) -> dict[str, Any]:
        """Get performance metrics from live/dry-run."""
        try:
            import subprocess

            cmd = [
                "freqtrade",
                "show-performance",
                "--config",
                str(self._config_file),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
            }
        except Exception as e:
            logger.error("Performance fetch failed: %s", e)
            return {"error": str(e)}

    async def start_bot(self, strategy: str, dry_run: bool = True) -> dict[str, Any]:
        """Start the trading bot."""
        try:
            import subprocess

            cmd = [
                "freqtrade",
                "trade",
                "--strategy",
                strategy,
                "--config",
                str(self._config_file),
            ]
            if dry_run:
                cmd.append("--dry-run")

            # Run in background
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            return {
                "success": True,
                "pid": process.pid,
                "message": f"Bot started with strategy {strategy}",
            }
        except Exception as e:
            logger.error("Bot start failed: %s", e)
            return {"error": str(e)}


def build_freqtrade_adapter(config: dict[str, Any] | None = None) -> FreqtradeAdapter:
    """Factory function to create Freqtrade adapter."""
    return FreqtradeAdapter(config)
