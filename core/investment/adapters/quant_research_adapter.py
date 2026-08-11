"""VectorBT / Backtrader Quant Research Adapter for OWNEX.

Integration with VectorBT and Backtrader for quantitative research and backtesting.
Based on: https://github.com/polyvectorbt/vectorbt, https://github.com/backtrader/backtrader
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger("orion.investment.quant_research")


class VectorBTAdapter:
    """VectorBT quantitative research and backtesting adapter.

    Provides:
    - High-performance vectorized backtesting
    - Portfolio optimization
    - Signal generation
    - Risk metrics
    - Parameter optimization
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._data_cache: dict[str, pd.DataFrame] = {}

    @property
    def name(self) -> str:
        return "vectorbt"

    async def initialize(self) -> bool:
        """Initialize VectorBT."""
        try:
            import vectorbtpro as vbt

            self._vbt = vbt
            logger.info("VectorBT Pro initialized")
            return True
        except ImportError:
            try:
                import vectorbt as vbt

                self._vbt = vbt
                logger.info("VectorBT initialized")
                return True
            except ImportError:
                logger.error("vectorbt not installed. Run: pip install vectorbt")
                return False

    async def fetch_data(
        self,
        symbols: list[str],
        start: str | None = None,
        end: str | None = None,
        timeframe: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """Fetch historical data using VectorBT's data module."""
        try:
            data = self._vbt.YFData.download(
                symbols,
                start=start,
                end=end,
                interval=timeframe,
                missing_index="drop",
            )
            self._data_cache.update(data.to_dict())
            return data.to_dict()
        except Exception as e:
            logger.error("Data fetch failed: %s", e)
            return {}

    async def run_backtest(
        self,
        entries: pd.Series,
        exits: pd.Series,
        close: pd.Series,
        fees: float = 0.001,
        slippage: float = 0.0005,
        init_cash: float = 10000,
    ) -> dict[str, Any]:
        """Run vectorized backtest."""
        try:
            pf = self._vbt.Portfolio.from_signals(
                close=close,
                entries=entries,
                exits=exits,
                fees=fees,
                slippage=slippage,
                init_cash=init_cash,
                freq="1D",
            )

            return {
                "total_return": pf.total_return(),
                "total_profit": pf.total_profit(),
                "sharpe_ratio": pf.sharpe_ratio(),
                "sortino_ratio": pf.sortino_ratio(),
                "max_drawdown": pf.max_drawdown(),
                "win_rate": pf.win_rate(),
                "profit_factor": pf.profit_factor(),
                "expectancy": pf.expectancy(),
                "trades": pf.trades.records_readable.to_dict("records"),
                "equity_curve": pf.value().to_dict(),
                "drawdowns": pf.drawdowns().to_dict(),
            }
        except Exception as e:
            logger.error("Backtest failed: %s", e)
            return {"error": str(e)}

    async def run_portfolio_backtest(
        self,
        signals: dict[str, tuple[pd.Series, pd.Series]],  # symbol -> (entries, exits)
        close_prices: dict[str, pd.Series],
        **kwargs,
    ) -> dict[str, Any]:
        """Run multi-asset portfolio backtest."""
        try:
            # Combine signals into DataFrames
            all_entries = pd.DataFrame({s: e for s, (e, _) in signals.items()})
            all_exits = pd.DataFrame({s: x for s, (_, x) in signals.items()})
            all_close = pd.DataFrame(close_prices)

            pf = self._vbt.Portfolio.from_signals(
                close=all_close,
                entries=all_entries,
                exits=all_exits,
                **kwargs,
            )

            return {
                "total_return": pf.total_return(),
                "sharpe_ratio": pf.sharpe_ratio(),
                "max_drawdown": pf.max_drawdown(),
                "win_rate": pf.win_rate(),
                "profit_factor": pf.profit_factor(),
                "asset_contributions": pf.asset_contributions().to_dict(),
                "group_contributions": pf.group_contributions().to_dict() if hasattr(pf, "group_contributions") else {},
            }
        except Exception as e:
            logger.error("Portfolio backtest failed: %s", e)
            return {"error": str(e)}

    async def optimize_parameters(
        self,
        param_ranges: dict[str, list[Any]],
        backtest_func,
        metric: str = "sharpe_ratio",
        n_trials: int = 100,
    ) -> dict[str, Any]:
        """Parameter optimization using VectorBT's parameter search."""
        try:
            # Generate parameter combinations
            import itertools

            keys = list(param_ranges.keys())
            values = list(param_ranges.values())
            combinations = list(itertools.product(*values))[:n_trials]

            best_params = None
            best_score = -np.inf
            results = []

            for combo in combinations:
                params = dict(zip(keys, combo, strict=False))
                try:
                    result = await backtest_func(**params)
                    score = result.get(metric, -np.inf)
                    if score > best_score:
                        best_score = score
                        best_params = params
                    results.append({**params, metric: score})
                except Exception:
                    continue

            return {
                "best_params": best_params,
                "best_score": best_score,
                "all_results": results,
            }
        except Exception as e:
            logger.error("Optimization failed: %s", e)
            return {"error": str(e)}

    async def compute_indicators(self, close: pd.Series) -> dict[str, pd.Series]:
        """Compute technical indicators using VectorBT."""
        try:
            indicators = {}

            # RSI
            indicators["rsi"] = self._vbt.RSI.run(close, window=14).rsi

            # MACD
            macd = self._vbt.MACD.run(close)
            indicators["macd"] = macd.macd
            indicators["macd_signal"] = macd.signal
            indicators["macd_hist"] = macd.hist

            # Bollinger Bands
            bb = self._vbt.BBANDS.run(close)
            indicators["bb_upper"] = bb.upper
            indicators["bb_middle"] = bb.middle
            indicators["bb_lower"] = bb.lower

            # Moving Averages
            indicators["sma_20"] = self._vbt.MA.run(close, window=20).ma
            indicators["sma_50"] = self._vbt.MA.run(close, window=50).ma
            indicators["ema_20"] = self._vbt.MA.run(close, window=20, ewm=True).ma

            # ATR
            indicators["atr"] = self._vbt.ATR.run(close).atr

            return indicators
        except Exception as e:
            logger.error("Indicator computation failed: %s", e)
            return {}

    async def risk_metrics(self, returns: pd.Series) -> dict[str, float]:
        """Compute risk metrics."""
        try:
            return {
                "var_95": float(np.percentile(returns.dropna(), 5)),
                "cvar_95": float(returns[returns <= np.percentile(returns.dropna(), 5)].mean()),
                "volatility": float(returns.std() * np.sqrt(252)),
                "skewness": float(returns.skew()),
                "kurtosis": float(returns.kurtosis()),
                "max_drawdown": float((returns.cumsum().expanding().max() - returns.cumsum()).max()),
            }
        except Exception as e:
            logger.error("Risk metrics failed: %s", e)
            return {}


class BacktraderAdapter:
    """Backtrader strategy framework adapter.

    Provides:
    - Event-driven backtesting
    - Strategy development framework
    - Multiple data feeds
    - Live trading support
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._cerebro: Any = None

    @property
    def name(self) -> str:
        return "backtrader"

    async def initialize(self) -> bool:
        """Initialize Backtrader."""
        try:
            import backtrader as bt

            self._bt = bt
            self._cerebro = bt.Cerebro()
            logger.info("Backtrader initialized")
            return True
        except ImportError:
            logger.error("backtrader not installed. Run: pip install backtrader")
            return False

    def add_strategy(self, strategy_class: Any, **params) -> None:
        """Add strategy to cerebro."""
        if self._cerebro:
            self._cerebro.addstrategy(strategy_class, **params)

    def add_data(
        self,
        data: Any,
        name: str = "data",
    ) -> None:
        """Add data feed."""
        if self._cerebro:
            self._cerebro.adddata(data, name=name)

    def set_cash(self, cash: float = 100000) -> None:
        """Set initial cash."""
        if self._cerebro:
            self._cerebro.broker.setcash(cash)

    def set_commission(self, commission: float = 0.001) -> None:
        """Set commission."""
        if self._cerebro:
            self._cerebro.broker.setcommission(commission=commission)

    async def run_backtest(self) -> dict[str, Any]:
        """Run backtest."""
        try:
            if not self._cerebro:
                return {"error": "Not initialized"}

            start_value = self._cerebro.broker.getvalue()
            results = self._cerebro.run()
            end_value = self._cerebro.broker.getvalue()

            return {
                "start_value": start_value,
                "end_value": end_value,
                "return_pct": (end_value - start_value) / start_value * 100,
                "strategies": len(results),
            }
        except Exception as e:
            logger.error("Backtrader backtest failed: %s", e)
            return {"error": str(e)}

    def add_analyzer(self, analyzer_class: Any, name: str, **params) -> None:
        """Add analyzer."""
        if self._cerebro:
            self._cerebro.addanalyzer(analyzer_class, _name=name, **params)

    def get_analyzers(self) -> dict[str, Any]:
        """Get analyzer results."""
        return {}  # Would need to be implemented based on strategy runs


def build_vectorbt_adapter(config: dict[str, Any] | None = None) -> VectorBTAdapter:
    """Factory function to create VectorBT adapter."""
    return VectorBTAdapter(config)


def build_backtrader_adapter(config: dict[str, Any] | None = None) -> BacktraderAdapter:
    """Factory function to create Backtrader adapter."""
    return BacktraderAdapter(config)
