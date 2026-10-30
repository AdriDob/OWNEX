"""Freqtrade Adapter — Adapter for Freqtrade trading engine.

Integrates with Freqtrade via REST API and optionally Docker.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import httpx

from core.trading.adapters.base import EngineAdapter, EngineConfig, HealthCheckResult
from core.trading.contracts import (
    BacktestResult,
    Decimal,
    EngineCapability,
    ExperimentRecord,
    MarketData,
    OptimizationResult,
    Order,
    PaperTradingResult,
    PerformanceMetrics,
    Position,
    PositionSide,
    Signal,
    StrategyStatus,
    ValidationPhase,
)

logger = logging.getLogger("ownex.trading.freqtrade")


class FreqtradeAdapter(EngineAdapter):
    """Freqtrade adapter for strategy execution and backtesting."""

    ENGINE_ID = "freqtrade"
    ENGINE_NAME = "Freqtrade"
    ENGINE_VERSION = "2024.1"
    SUPPORTED_CAPABILITIES = [
        EngineCapability.BACKTEST,
        EngineCapability.PAPER_TRADING,
        EngineCapability.LIVE_TRADING,
        EngineCapability.OPTIMIZATION,
        EngineCapability.SPOT_SUPPORT,
        EngineCapability.FUTURES_SUPPORT,
        EngineCapability.MULTI_EXCHANGE,
        EngineCapability.STRATEGY_API,
        EngineCapability.REST_API,
        EngineCapability.WEBSOCKET,
    ]
    SUPPORTED_EXCHANGES = ["binance", "bybit", "kraken", "coinbase", "gate", "kucoin", "okx"]
    SUPPORTED_MARKETS = ["spot", "futures"]
    DOCKER_IMAGE = "freqtradeorg/freqtrade:stable"

    def __init__(self, config: EngineConfig):
        super().__init__(config)
        self.api_url = config.config.get("api_url", "http://localhost:8080/api/v1")
        self.api_username = config.config.get("api_username", "")
        self.api_password = config.config.get("api_password", "")
        self._client: httpx.AsyncClient | None = None
        self._process: asyncio.subprocess.Process | None = None

    # ════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════

    async def install(self) -> bool:
        """Install Freqtrade via Docker or pip."""
        try:
            # Try Docker first
            result = await asyncio.create_subprocess_exec(
                "docker",
                "pull",
                self.DOCKER_IMAGE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.wait()
            if result.returncode == 0:
                logger.info(f"Freqtrade Docker image pulled: {self.DOCKER_IMAGE}")
                return True

            # Fallback to pip
            logger.warning("Docker not available, trying pip install")
            result = await asyncio.create_subprocess_exec(
                "pip",
                "install",
                "freqtrade",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.wait()
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Freqtrade installation failed: {e}")
            return False

    async def uninstall(self) -> bool:
        """Uninstall Freqtrade."""
        try:
            await self.shutdown()
            # Remove Docker image if used
            await asyncio.create_subprocess_exec(
                "docker",
                "rmi",
                self.DOCKER_IMAGE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            logger.error(f"Freqtrade uninstall failed: {e}")
            return False

    async def initialize(self) -> bool:
        """Initialize Freqtrade configuration."""
        try:
            # Create config directory
            config_dir = Path(self.data_dir) / "freqtrade"
            config_dir.mkdir(parents=True, exist_ok=True)

            # Create default config
            config_file = config_dir / "config.json"
            if not config_file.exists():
                default_config = {
                    "max_open_trades": 3,
                    "stake_currency": "USDT",
                    "stake_amount": "unlimited",
                    "tradable_balance_ratio": 0.99,
                    "fiat_display_currency": "USD",
                    "dry_run": self.dry_run,
                    "cancel_open_orders_on_exit": False,
                    "trading_mode": "spot",
                    "margin_mode": "isolated",
                    "unfilledtimeout": {"entry": 10, "exit": 10},
                    "entry_pricing": {"price_side": "same", "use_order_book": True},
                    "exit_pricing": {"price_side": "same", "use_order_book": True},
                    "exchange": {
                        "name": "binance",
                        "key": "",
                        "secret": "",
                        "password": "",
                        "ccxt_config": {},
                        "ccxt_async_config": {},
                    },
                    "pairlists": [{"method": "VolumePairList", "number_assets": 50}],
                    "telegram": {"enabled": False},
                    "api_server": {
                        "enabled": True,
                        "listen_ip_address": "0.0.0.0",
                        "listen_port": 8080,
                        "verbosity": "info",
                        "username": self.api_username,
                        "password": self.api_password,
                    },
                }
                config_file.write_text(json.dumps(default_config, indent=2))

            # Create strategies directory
            strategies_dir = config_dir / "strategies"
            strategies_dir.mkdir(parents=True, exist_ok=True)

            # Create sample strategy if none exists
            sample_strategy = strategies_dir / "SampleStrategy.py"
            if not sample_strategy.exists():
                sample_strategy.write_text(self._get_sample_strategy())

            self._initialized = True
            logger.info(f"Freqtrade initialized at {config_dir}")
            return True
        except Exception as e:
            logger.error(f"Freqtrade initialization failed: {e}")
            return False

    async def shutdown(self) -> bool:
        """Shutdown Freqtrade."""
        try:
            if self._client:
                await self._client.aclose()
                self._client = None
            if self._process:
                self._process.terminate()
                await self._process.wait()
                self._process = None
            logger.info("Freqtrade shutdown complete")
            return True
        except Exception as e:
            logger.error(f"Freqtrade shutdown failed: {e}")
            return False

    # ═════════════════════════════════════════════════════════════════════════
    # HEALTH CHECK
    # ════════════════════════════════════════════════════════════════════════

    async def health_check(self) -> HealthCheckResult:
        """Check Freqtrade API health."""
        try:
            if not self._client:
                self._client = httpx.AsyncClient(
                    base_url=self.api_url,
                    timeout=10,
                    auth=(self.api_username, self.api_password) if self.api_username else None,
                )
            start = asyncio.get_event_loop().time()
            resp = await self._client.get("/ping")
            latency = (asyncio.get_event_loop().time() - start) * 1000
            healthy = resp.status_code == 200
            return HealthCheckResult(
                healthy=healthy,
                latency_ms=latency if healthy else None,
                error=None if healthy else f"HTTP {resp.status_code}",
            )
        except Exception as e:
            return HealthCheckResult(healthy=False, error=str(e))

    # ════════════════════════════════════════════════════════════════════════
    # STRATEGY MANAGEMENT
    # ════════════════════════════════════════════════════════════════════════

    async def load_strategy(self, strategy_id: str, strategy_config: dict) -> bool:
        """Load a strategy into Freqtrade."""
        try:
            strategy_file = Path(self.data_dir) / "freqtrade" / "strategies" / f"{strategy_id}.py"
            strategy_file.write_text(strategy_config.get("code", self._get_sample_strategy()))

            # Reload config via API
            if self._client:
                await self._client.post("/strategy/reload")
            return True
        except Exception as e:
            logger.error(f"Failed to load strategy {strategy_id}: {e}")
            return False

    async def unload_strategy(self, strategy_id: str) -> bool:
        """Unload a strategy (remove file)."""
        try:
            strategy_file = Path(self.data_dir) / "freqtrade" / "strategies" / f"{strategy_id}.py"
            if strategy_file.exists():
                strategy_file.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to unload strategy {strategy_id}: {e}")
            return False

    async def get_strategy_status(self, strategy_id: str) -> StrategyStatus:
        """Get strategy status from Freqtrade."""
        try:
            if not self._client:
                return StrategyStatus.DISCOVERED
            resp = await self._client.get(f"/strategy/{strategy_id}")
            if resp.status_code == 200:
                data = resp.json()
                state = data.get("state", "unknown")
                if state == "running":
                    return StrategyStatus.LIVE
                elif state == "stopped":
                    return StrategyStatus.PAUSED
            return StrategyStatus.DISCOVERED
        except Exception:
            return StrategyStatus.DISCOVERED

    async def list_strategies(self) -> list[str]:
        """List available strategies."""
        try:
            strategies_dir = Path(self.data_dir) / "freqtrade" / "strategies"
            if not strategies_dir.exists():
                return []
            return [f.stem for f in strategies_dir.glob("*.py") if not f.name.startswith("_")]
        except Exception:
            return []

    # ═════════════════════════════════════════════════════════════════════════
    # VALIDATION PIPELINE
    # ════════════════════════════════════════════════════════════════════════

    async def backtest(
        self,
        strategy_id: str,
        market_data: MarketData,
        parameters: dict,
        execution_config: dict,
    ) -> BacktestResult:
        """Run backtest via Freqtrade CLI."""
        try:
            config_dir = Path(self.data_dir) / "freqtrade"
            cmd = [
                "freqtrade",
                "backtesting",
                "--config",
                str(config_dir / "config.json"),
                "--strategy",
                strategy_id,
                "--timerange",
                execution_config.get("timerange", "20240101-"),
                "--export",
                "trades",
                "--export-filename",
                f"backtest_{strategy_id}",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(config_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                # Parse results
                result_file = config_dir / "backtest_results" / f"backtest_{strategy_id}.json"
                if result_file.exists():
                    data = json.loads(result_file.read_text())
                    return self._parse_backtest_result(data, strategy_id)

            return BacktestResult(
                strategy_id=strategy_id,
                engine_id=self.ENGINE_ID,
                phase=ValidationPhase.PHASE_1_BACKTEST,
                success=False,
                error=stderr.decode() if stderr else "Unknown error",
            )
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return BacktestResult(
                strategy_id=strategy_id,
                engine_id=self.ENGINE_ID,
                phase=ValidationPhase.PHASE_1_BACKTEST,
                success=False,
                error=str(e),
            )

    async def optimize(
        self,
        strategy_id: str,
        param_space: dict,
        market_data: MarketData,
        optimization_metric: str = "sharpe",
        n_trials: int = 100,
    ) -> OptimizationResult:
        """Run hyperopt optimization."""
        try:
            config_dir = Path(self.data_dir) / "freqtrade"
            cmd = [
                "freqtrade",
                "hyperopt",
                "--config",
                str(config_dir / "config.json"),
                "--strategy",
                strategy_id,
                "--spaces",
                "buy",
                "sell",
                "roi",
                "stoploss",
                "--epochs",
                str(n_trials),
                "--print-json",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(config_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                # Parse best parameters from output
                return OptimizationResult(
                    strategy_id=strategy_id,
                    engine_id=self.ENGINE_ID,
                    best_params={},  # Parse from stdout
                    best_metrics=None,
                    all_trials=[],
                    param_space=param_space,
                    optimization_metric=optimization_metric,
                    n_trials=n_trials,
                    success=True,
                )

            return OptimizationResult(
                strategy_id=strategy_id,
                engine_id=self.ENGINE_ID,
                success=False,
                error=stderr.decode(),
            )
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return OptimizationResult(
                strategy_id=strategy_id,
                engine_id=self.ENGINE_ID,
                success=False,
                error=str(e),
            )

    async def walk_forward(
        self,
        strategy_id: str,
        market_data: MarketData,
        windows: int = 12,
        step_size: int = 1,
    ) -> list[BacktestResult]:
        """Run walk-forward analysis (Freqtrade doesn't have native support)."""
        logger.warning("Walk-forward not natively supported in Freqtrade adapter")
        return []

    async def monte_carlo(
        self,
        strategy_id: str,
        backtest_result: BacktestResult,
        n_simulations: int = 1000,
    ) -> dict:
        """Run Monte Carlo simulation."""
        logger.warning("Monte Carlo not natively supported in Freqtrade adapter")
        return {"supported": False}

    async def stress_test(
        self,
        strategy_id: str,
        market_data: MarketData,
        scenarios: list[dict],
    ) -> dict:
        """Run stress tests."""
        logger.warning("Stress test not natively supported in Freqtrade adapter")
        return {"supported": False}

    # ════════════════════════════════════════════════════════════════════════
    # PAPER & LIVE TRADING
    # ════════════════════════════════════════════════════════════════════════

    async def start_paper_trading(self, strategy_id: str) -> bool:
        """Start paper trading (dry-run) for a strategy."""
        try:
            if not self._client:
                return False
            resp = await self._client.post(f"/strategy/{strategy_id}/start", json={"dry_run": True})
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to start paper trading: {e}")
            return False

    async def stop_paper_trading(self, strategy_id: str) -> PaperTradingResult:
        """Stop paper trading and return results."""
        try:
            if not self._client:
                return PaperTradingResult(strategy_id=strategy_id, engine_id=self.ENGINE_ID, success=False)
            await self._client.post(f"/strategy/{strategy_id}/stop")
            # Get final stats
            resp = await self._client.get(f"/strategy/{strategy_id}/stats")
            if resp.status_code == 200:
                data = resp.json()
                return PaperTradingResult(
                    strategy_id=strategy_id,
                    engine_id=self.ENGINE_ID,
                    metrics=self._parse_performance(data),
                    success=True,
                )
        except Exception as e:
            logger.error(f"Paper trading stop failed: {e}")
        return PaperTradingResult(strategy_id=strategy_id, engine_id=self.ENGINE_ID, success=False)

    async def get_paper_trading_status(self, strategy_id: str) -> dict:
        """Get paper trading status."""
        try:
            if not self._client:
                return {}
            resp = await self._client.get(f"/strategy/{strategy_id}/stats")
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    async def start_live_trading(self, strategy_id: str, capital_allocation: Decimal) -> bool:
        """Start live trading for a strategy."""
        try:
            if not self._client:
                return False
            resp = await self._client.post(f"/strategy/{strategy_id}/start", json={"dry_run": False})
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to start live trading: {e}")
            return False

    async def stop_live_trading(self, strategy_id: str, reason: str = "user requested") -> bool:
        """Stop live trading for a strategy."""
        try:
            if not self._client:
                return False
            await self._client.post(f"/strategy/{strategy_id}/stop")
            return True
        except Exception as e:
            logger.error(f"Failed to stop live trading: {e}")
            return False

    # ═════════════════════════════════════════════════════════════════════════
    # REAL-TIME DATA
    # ════════════════════════════════════════════════════════════════════════

    async def get_signals(self, strategy_id: str) -> list[Signal]:
        """Get current signals from Freqtrade."""
        try:
            if not self._client:
                return []
            resp = await self._client.get(f"/strategy/{strategy_id}/signals")
            if resp.status_code == 200:
                data = resp.json()
                return [Signal(**s) for s in data.get("signals", [])]
        except Exception:
            pass
        return []

    async def get_orders(self, strategy_id: str) -> list[Order]:
        """Get current orders."""
        try:
            if not self._client:
                return []
            resp = await self._client.get("/trades", params={"strategy": strategy_id})
            if resp.status_code == 200:
                data = resp.json()
                return [Order(**t) for t in data.get("trades", [])]
        except Exception:
            pass
        return []

    async def get_positions(self, strategy_id: str) -> list[Position]:
        """Get current positions."""
        try:
            if not self._client:
                return []
            resp = await self._client.get("/trades", params={"strategy": strategy_id, "open": True})
            if resp.status_code == 200:
                data = resp.json()
                positions = []
                for t in data.get("trades", []):
                    pos = Position(
                        strategy_id=strategy_id,
                        symbol=t.get("pair", ""),
                        side=PositionSide.LONG if t.get("is_short", False) is False else PositionSide.SHORT,
                        entry_price=Decimal(str(t.get("open_rate", 0))),
                        current_price=Decimal(str(t.get("current_rate", 0))),
                        size=Decimal(str(t.get("amount", 0))),
                        unrealized_pnl=Decimal(str(t.get("profit_abs", 0))),
                        exchange="binance",
                    )
                    positions.append(pos)
                return positions
        except Exception:
            pass
        return []

    async def get_performance(self, strategy_id: str) -> PerformanceMetrics:
        """Get performance metrics."""
        try:
            if not self._client:
                return PerformanceMetrics(strategy_id=strategy_id, phase=ValidationPhase.PHASE_1_BACKTEST)
            resp = await self._client.get(f"/strategy/{strategy_id}/stats")
            if resp.status_code == 200:
                data = resp.json()
                return self._parse_performance(data)
        except Exception:
            pass
        return PerformanceMetrics(strategy_id=strategy_id, phase=ValidationPhase.PHASE_1_BACKTEST)

    async def get_logs(self, strategy_id: str, limit: int = 100) -> list[dict]:
        """Get recent logs."""
        try:
            if not self._client:
                return []
            resp = await self._client.get("/logs", params={"strategy": strategy_id, "limit": limit})
            if resp.status_code == 200:
                return resp.json().get("logs", [])
        except Exception:
            pass
        return []

    # ════════════════════════════════════════════════════════════════════════
    # EXPERIMENT TRACKING
    # ════════════════════════════════════════════════════════════════════════

    async def record_experiment(self, experiment: ExperimentRecord) -> str:
        """Record experiment for reproducibility."""
        exp_dir = Path(self.data_dir) / "experiments"
        exp_dir.mkdir(parents=True, exist_ok=True)
        exp_file = exp_dir / f"{experiment.experiment_id}.json"
        exp_file.write_text(
            json.dumps(
                {
                    "experiment_id": experiment.experiment_id,
                    "strategy_id": experiment.strategy_id,
                    "engine_id": experiment.engine_id,
                    "phase": experiment.phase.value,
                    "dataset_hash": experiment.dataset_hash,
                    "parameters": experiment.parameters,
                    "parameters_hash": experiment.parameters_hash,
                    "metrics": experiment.metrics.to_dict() if experiment.metrics else None,
                    "code_commit": experiment.code_commit,
                    "dataset_version": experiment.dataset_version,
                    "random_seed": experiment.random_seed,
                    "execution_config": experiment.execution_config,
                    "environment": experiment.environment,
                    "result": experiment.result,
                    "notes": experiment.notes,
                    "created_at": experiment.created_at,
                },
                indent=2,
            )
        )
        return experiment.experiment_id

    async def get_experiments(self, strategy_id: str) -> list[ExperimentRecord]:
        """Get all experiments for a strategy."""
        exp_dir = Path(self.data_dir) / "experiments"
        if not exp_dir.exists():
            return []
        experiments = []
        for exp_file in exp_dir.glob("*.json"):
            try:
                data = json.loads(exp_file.read_text())
                if data.get("strategy_id") == strategy_id:
                    experiments.append(ExperimentRecord(**data))
            except Exception:
                pass
        return experiments

    # ════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ════════════════════════════════════════════════════════════════════════

    def _get_sample_strategy(self) -> str:
        """Return a sample Freqtrade strategy."""
        return '''"""
Sample Freqtrade Strategy for testing.
"""
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class SampleStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False
    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10
    trailing_stop = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=21)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema_fast"] > dataframe["ema_slow"]) &
            (dataframe["rsi"] < 70),
            "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema_fast"] < dataframe["ema_slow"]),
            "exit_long"] = 1
        return dataframe
'''

    def _parse_backtest_result(self, data: dict, strategy_id: str) -> BacktestResult:
        """Parse Freqtrade backtest results."""
        metrics = PerformanceMetrics(
            strategy_id=strategy_id,
            phase=ValidationPhase.PHASE_1_BACKTEST,
        )
        return BacktestResult(
            strategy_id=strategy_id,
            engine_id=self.ENGINE_ID,
            metrics=metrics,
            success=True,
        )

    def _parse_performance(self, data: dict) -> PerformanceMetrics:
        """Parse Freqtrade performance data."""
        return PerformanceMetrics(
            strategy_id="",
            phase=ValidationPhase.PHASE_1_BACKTEST,
            total_return=Decimal(str(data.get("profit_total", 0))),
            win_rate=Decimal(str(data.get("winrate", 0))),
            number_of_trades=int(data.get("trade_count", 0)),
            profit_factor=Decimal(str(data.get("profit_factor", 0))),
            sharpe=Decimal(str(data.get("sharpe", 0))),
            max_drawdown=Decimal(str(data.get("max_drawdown", 0))),
        )


def build_freqtrade_adapter(config: EngineConfig) -> FreqtradeAdapter:
    """Factory function to create Freqtrade adapter."""
    return FreqtradeAdapter(config)
