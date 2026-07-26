from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field

logger = logging.getLogger("orion.atlas.engines.optimizer")

try:
    import riskfolio as rp

    HAS_RISKFOLIO = True
except ImportError:
    HAS_RISKFOLIO = False
    logger.warning("riskfolio-lib not available, optimizer disabled")


@dataclass
class OptimizationResult:
    weights: dict[str, float] = field(default_factory=dict)
    expected_return: float = 0.0
    expected_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    method: str = ""


class PortfolioOptimizer:
    def optimize(
        self,
        symbols: list[str],
        expected_returns: list[float],
        covariance: list[list[float]],
        risk_free_rate: float = 0.05,
        method: str = "max_sharpe",
    ) -> OptimizationResult:
        if not HAS_RISKFOLIO or len(symbols) < 2:
            return self._fallback_equal_weight(symbols)

        try:
            import numpy as np
            import pandas as pd

            obj_map = {
                "max_sharpe": "Sharpe",
                "min_vol": "MinRisk",
                "max_return": "MaxRet",
            }
            obj = obj_map.get(method, "Sharpe")

            returns = pd.DataFrame(np.random.randn(252, len(symbols)), columns=symbols)
            portfolio = rp.Portfolio(returns=returns)

            portfolio.mu = pd.Series(expected_returns, index=symbols)
            portfolio.cov = pd.DataFrame(covariance, index=symbols, columns=symbols)
            portfolio.lb = 0.0
            portfolio.ub = 1.0

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                w = portfolio.optimization(model="Classic", rm="MV", obj=obj, rf=risk_free_rate, hist=False)

            weights_list = w["weights"].to_dict()
            weights = {str(k): round(float(v), 6) for k, v in weights_list.items() if float(v) > 0.001}

            if not weights:
                return self._fallback_equal_weight(symbols)

            w_vec = np.array([weights.get(s, 0.0) for s in symbols])
            ret = float(np.dot(w_vec, expected_returns))
            vol = float(np.sqrt(np.dot(w_vec, np.dot(covariance, w_vec))))
            sharpe = (ret - risk_free_rate) / vol if vol > 1e-10 else 0.0

            return OptimizationResult(
                weights=weights,
                expected_return=round(ret, 6),
                expected_volatility=round(vol, 6),
                sharpe_ratio=round(sharpe, 4),
                method=method,
            )
        except Exception as e:
            logger.warning("Riskfolio optimization failed: %s", e)
            return self._fallback_equal_weight(symbols)

    def _fallback_equal_weight(self, symbols: list[str]) -> OptimizationResult:
        n = len(symbols)
        if n == 0:
            return OptimizationResult(method="equal_weight_fallback")
        w = 1.0 / n
        return OptimizationResult(
            weights={s: round(w, 4) for s in symbols},
            method="equal_weight_fallback",
        )
