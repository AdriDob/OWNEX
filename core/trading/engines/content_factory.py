from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx

from core.trading.adapters.base import EngineAdapter, EngineConfig, HealthCheckResult
from core.trading.contracts import (
    BacktestResult,
    EngineCapability,
    ExperimentRecord,
    MarketData,
    OptimizationResult,
    Order,
    PaperTradingResult,
    PerformanceMetrics,
    Signal,
    StrategyStatus,
    ValidationPhase,
)

logger = logging.getLogger("ownex.trading.content_factory")


@dataclass
class ContentPiece:
    """A piece of generated content."""

    piece_id: str = field(default_factory=lambda: f"cp_{os.urandom(6).hex()}")
    topic: str = ""
    script: str = ""
    video_path: str | None = None
    thumbnail_path: str | None = None
    status: str = "draft"  # draft, generated, published, failed
    platform: str = "youtube"
    channel_id: str | None = None
    scheduled_at: str | None = None
    published_at: str | None = None
    metrics: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class ChannelConfig:
    """Configuration for a content channel."""

    channel_id: str
    name: str
    platform: str  # youtube, tiktok, instagram, rumble, odysee
    api_credentials: dict = field(default_factory=dict)
    upload_schedule: list[dict] = field(default_factory=list)  # cron-like schedules
    niche: str = ""
    target_audience: str = ""
    language: str = "es"
    upload_defaults: dict = field(default_factory=dict)


class ContentFactoryEngine(EngineAdapter):
    """Content Factory Engine — wraps MoneyPrinterTurbo for content automation."""

    ENGINE_ID = "content_factory"
    ENGINE_NAME = "Content Factory (MoneyPrinterTurbo)"
    ENGINE_VERSION = "1.0.0"
    SUPPORTED_CAPABILITIES = [
        EngineCapability.CONTENT_GENERATION,
        EngineCapability.SCHEDULING,
        EngineCapability.ANALYTICS,
        EngineCapability.MONETIZATION,
    ]
    SUPPORTED_EXCHANGES = ["youtube", "tiktok", "instagram", "rumble", "odysee"]
    SUPPORTED_MARKETS = ["content"]
    DOCKER_IMAGE = "moneypy/content-factory:latest"

    def __init__(self, config: EngineConfig):
        super().__init__(config)
        self.mp_config = config.config.get("moneypainter", {})
        self.mp_dir = Path(self.data_dir) / "content_factory"
        self.mp_dir.mkdir(parents=True, exist_ok=True)
        self._channels: dict[str, ChannelConfig] = {}
        self._content_queue: list[ContentPiece] = []
        self._client = httpx.AsyncClient(timeout=30.0)

    # ════════════════════════════════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ════════════════════════════════════════════════════════════════════════════════════════════════════

    async def install(self) -> bool:
        """Install MoneyPrinterTurbo via Docker or local installation."""
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
                logger.info(f"MoneyPrinterTurbo Docker image pulled: {self.DOCKER_IMAGE}")
                return True

            # Fallback: check if locally installed
            result = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                "import moneypainter",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.wait()
            if result.returncode == 0:
                logger.info("MoneyPrinterTurbo already available locally")
                return True

            logger.warning("MoneyPrinterTurbo not available - engine will run in mock mode")
            return True  # Allow mock mode for development

        except Exception as e:
            logger.error(f"Content Factory installation failed: {e}")
            return False

    async def uninstall(self) -> bool:
        """Uninstall Content Factory."""
        try:
            await self.shutdown()
            await asyncio.create_subprocess_exec(
                "docker",
                "rmi",
                self.DOCKER_IMAGE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            logger.error(f"Content Factory uninstall failed: {e}")
            return False

    async def initialize(self) -> bool:
        """Initialize Content Factory configuration."""
        try:
            # Create directories
            self.mp_dir.mkdir(parents=True, exist_ok=True)
            (self.mp_dir / "scripts").mkdir(parents=True, exist_ok=True)
            (self.mp_dir / "videos").mkdir(parents=True, exist_ok=True)
            (self.mp_dir / "thumbnails").mkdir(parents=True, exist_ok=True)
            (self.mp_dir / "analytics").mkdir(parents=True, exist_ok=True)

            # Load channel configs
            config_file = self.mp_dir / "channels.json"
            if config_file.exists():
                with open(config_file) as f:
                    data = json.load(f)
                    for ch_data in data.get("channels", []):
                        ch = ChannelConfig(**ch_data)
                        self._channels[ch.channel_id] = ch

            self._initialized = True
            logger.info(f"Content Factory initialized at {self.mp_dir}")
            return True
        except Exception as e:
            logger.error(f"Content Factory initialization failed: {e}")
            return False

    async def shutdown(self) -> bool:
        """Shutdown Content Factory."""
        try:
            # Stop any running processes
            await self._client.aclose()
            logger.info("Content Factory shutdown complete")
            return True
        except Exception as e:
            logger.error(f"Content Factory shutdown failed: {e}")
            return False

    # ════════════════════════════════════════════════════════════════════════════════════════════════════
    # HEALTH CHECK
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════

    async def health_check(self) -> HealthCheckResult:
        """Check Content Factory health."""
        try:
            start = asyncio.get_event_loop().time()
            # Check if MoneyPrinterTurbo is available
            healthy = True
            error = None
            try:
                result = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-c",
                    "import moneypainter; print('ok')",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(result.wait(), timeout=5.0)
                if result.returncode != 0:
                    healthy = False
                    error = "MoneyPrinterTurbo not available"
            except Exception as e:
                healthy = False
                error = f"Health check failed: {e}"

            latency = (asyncio.get_event_loop().time() - start) * 1000
            return HealthCheckResult(
                healthy=healthy,
                latency_ms=latency if healthy else None,
                error=error,
            )
        except Exception as e:
            return HealthCheckResult(healthy=False, error=str(e))

    # ═════════════════════════════════════════════════════════════════════════════════════════════════════
    # CHANNEL MANAGEMENT
    # ═════════════════════════════════════════════════════════════════════════════════════════════════════

    def register_channel(self, channel: ChannelConfig) -> None:
        """Register a content channel."""
        self._channels[channel.channel_id] = channel
        self._save_channels()

    def unregister_channel(self, channel_id: str) -> bool:
        """Unregister a channel."""
        if channel_id in self._channels:
            del self._channels[channel_id]
            self._save_channels()
            return True
        return False

    def get_channel(self, channel_id: str) -> ChannelConfig | None:
        return self._channels.get(channel_id)

    def list_channels(self) -> list[ChannelConfig]:
        return list(self._channels.values())

    def _save_channels(self) -> None:
        config_file = self.mp_dir / "channels.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "channels": [
                {
                    "channel_id": ch.channel_id,
                    "name": ch.name,
                    "platform": ch.platform,
                    "api_credentials": ch.api_credentials,
                    "upload_schedule": ch.upload_schedule,
                    "niche": ch.niche,
                    "target_audience": ch.target_audience,
                    "language": ch.language,
                    "upload_defaults": ch.upload_defaults,
                }
                for ch in self._channels.values()
            ]
        }
        config_file.write_text(json.dumps(data, indent=2))

    # ══════════════════════════════════════════════════════════════════════════════════════════════════════
    # STRATEGY MANAGEMENT (Abstract methods)
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════

    async def load_strategy(self, strategy_id: str, strategy_config: dict) -> bool:
        """Load a strategy configuration into the engine."""
        try:
            strategy_file = self.mp_dir / "strategies" / f"{strategy_id}.json"
            strategy_file.parent.mkdir(parents=True, exist_ok=True)
            strategy_file.write_text(json.dumps(strategy_config, indent=2))
            logger.info(f"Loaded strategy: {strategy_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to load strategy {strategy_id}: {e}")
            return False

    async def unload_strategy(self, strategy_id: str) -> bool:
        """Unload a strategy from the engine."""
        try:
            strategy_file = self.mp_dir / "strategies" / f"{strategy_id}.json"
            if strategy_file.exists():
                strategy_file.unlink()
            logger.info(f"Unloaded strategy: {strategy_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload strategy {strategy_id}: {e}")
            return False

    async def get_strategy_status(self, strategy_id: str) -> StrategyStatus:
        """Get the status of a strategy in this engine."""
        try:
            strategy_file = self.mp_dir / "strategies" / f"{strategy_id}.json"
            if not strategy_file.exists():
                return StrategyStatus.DISCOVERED

            # Check if strategy is running
            # In a real implementation, this would check actual process status
            return StrategyStatus.INSTALLED
        except Exception:
            return StrategyStatus.DISCOVERED

    async def list_strategies(self) -> list[str]:
        """List all loaded strategies."""
        try:
            strategies_dir = self.mp_dir / "strategies"
            if not strategies_dir.exists():
                return []
            return [f.stem for f in strategies_dir.glob("*.py")]
        except Exception:
            return []

    # ═════════════════════════════════════════════════════════════════════════════════════════════════════
    # VALIDATION PIPELINE
    # ═════════════════════════════════════════════════════════════════════════════════════════════════════

    async def backtest(
        self,
        strategy_id: str,
        market_data: MarketData,
        parameters: dict,
        execution_config: dict,
    ) -> BacktestResult:
        """Run backtest for content strategy."""
        try:
            config_dir = self.mp_dir
            cmd = [
                sys.executable,
                "-m",
                "moneypainter",
                "backtest",
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
            config_dir = Path(self.data_dir) / "content_factory"
            cmd = [
                sys.executable,
                "-m",
                "moneypainter",
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
        """Run walk-forward analysis (MoneyPrinterTurbo doesn't have native support)."""
        logger.warning("Walk-forward not natively supported in MoneyPrinterTurbo adapter")
        return []

    async def monte_carlo(
        self,
        strategy_id: str,
        backtest_result: BacktestResult,
        n_simulations: int = 1000,
    ) -> dict:
        """Run Monte Carlo simulation."""
        logger.warning("Monte Carlo not natively supported in MoneyPrinterTurbo adapter")
        return {"supported": False}

    async def stress_test(
        self,
        strategy_id: str,
        market_data: MarketData,
        scenarios: list[dict],
    ) -> dict:
        """Run stress tests."""
        logger.warning("Stress test not natively supported in MoneyPrinterTurbo adapter")
        return {"supported": False}

    # ═════════════════════════════════════════════════════════════════════════════════════════════════════
    # PAPER & LIVE TRADING (Content Publishing)
    # ════════════════════════════════════════════════════════════════════════════════════════════════════

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

    # ════════════════════════════════════════════════════════════════════════════════════════════════════
    # REAL-TIME DATA
    # ════════════════════════════════════════════════════════════════════════════════════════════════════

    async def get_signals(self, strategy_id: str) -> list[Signal]:
        """Get current signals from Content Factory."""
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

    async def get_orders(self, strategy_id: str) -> list:
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

    async def get_positions(self, strategy_id: str) -> list:
        """Get current positions."""
        try:
            if not self._client:
                return []
            resp = await self._client.get("/trades", params={"strategy": strategy_id, "open": True})
            if resp.status_code == 200:
                data = resp.json()
                positions = []
                for t in data.get("trades", []):
                    pos = {
                        "strategy_id": strategy_id,
                        "symbol": t.get("pair", ""),
                        "side": "long" if t.get("is_short", False) is False else "short",
                        "entry_price": Decimal(str(t.get("open_rate", 0))),
                        "current_price": Decimal(str(t.get("current_rate", 0))),
                        "size": Decimal(str(t.get("amount", 0))),
                        "unrealized_pnl": Decimal(str(t.get("profit_abs", 0))),
                        "exchange": "youtube",
                    }
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

    # ════════════════════════════════════════════════════════════════════════════════════════════════════
    # EXPERIMENT TRACKING
    # ════════════════════════════════════════════════════════════════════════════════════════════════════

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


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
# FACTORY
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════


def build_content_factory_adapter(config: EngineConfig) -> ContentFactoryEngine:
    """Factory function to create ContentFactoryEngine."""
    return ContentFactoryEngine(config)
