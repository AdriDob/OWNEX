"""Advanced Wealth Maximization Engine — Optimization with correlation, volatility, and rebalancing.

Extends the basic maximizer with:
- Asset correlation analysis
- Volatility-adjusted scoring
- Automated rebalancing recommendations
- Monte Carlo-style projections
"""

from __future__ import annotations

import logging
import random
import statistics
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.capital.maximizer_advanced")

# ── Correlation Matrix ─────────────────────────────────────────────────────

# Placeholder correlation coefficients between asset categories
# In production, these would be computed from historical data
CORRELATION_MATRIX: dict[str, dict[str, float]] = {
    "bug_bounty": {
        "bug_bounty": 1.0,
        "hackerone": 0.7,
        "test_platform": 0.3,
        "crypto": -0.2,
        "firefly": 0.1,
        "takenos": 0.0,
    },
    "hackerone": {
        "bug_bounty": 0.7,
        "hackerone": 1.0,
        "test_platform": 0.4,
        "crypto": -0.1,
        "firefly": 0.2,
        "takenos": 0.0,
    },
    "crypto": {
        "bug_bounty": -0.2,
        "hackerone": -0.1,
        "crypto": 1.0,  # self
        "test_platform": 0.1,
        "firefly": 0.15,
        "takenos": 0.05,
    },
    "firefly": {
        "bug_bounty": 0.1,
        "hackerone": 0.2,
        "crypto": 0.15,
        "firefly": 1.0,
        "test_platform": 0.2,
        "takenos": 0.1,
    },
}


def _compute_correlation_adjusted_score(
    category: str,
    base_score: float,
    portfolio: dict[str, float],
    correlation_matrix: dict[str, dict[str, float]] | None = None,
) -> float:
    """Adjust score based on correlation with other holdings.

    Diversification benefit: negatively correlated assets get score boost.
    Redundancy penalty: highly correlated assets get score reduction.
    """
    corr_matrix = correlation_matrix or CORRELATION_MATRIX
    category_corr = corr_matrix.get(category, {})

    # Compute effective correlation with existing portfolio
    effective_corr = 0.0
    counted = 0
    for other_cat, other_balance in portfolio.items():
        if other_balance > 0 and other_cat in category_corr:
            effective_corr += category_corr[other_cat]
            counted += 1

    if counted > 0:
        effective_corr /= counted

    # Diversification benefit: negatively correlated boost (up to +0.1)
    # Redundancy penalty: positively correlated reduction (down to -0.1)
    correlation_adjustment = (0.1 * (1.0 - effective_corr)) * (1 if effective_corr < 0.5 else -1)

    adjusted = base_score + correlation_adjustment
    return round(max(0.0, min(1.0, adjusted)), 4)


# ── Volatility Adjustment ──────────────────────────────────────────────────


def _compute_volatility_adjusted_score(
    category: str,
    base_score: float,
    historical_returns: list[float] | None = None,
    risk_tolerance: float = 0.5,  # 0.0 = conservative, 1.0 = aggressive
) -> float:
    """Adjust score based on return volatility.

    Higher volatility -> lower score for conservative investors
    Higher volatility -> higher score for aggressive investors
    """
    if historical_returns is None or len(historical_returns) < 2:
        return base_score

    # Compute annualized volatility (simplified)
    returns_series = historical_returns[-30:]  # last 30 periods
    if len(returns_series) < 2:
        return base_score

    stdev = statistics.stdev(returns_series) if len(returns_series) > 1 else 0

    # Annualize (assuming monthly returns)
    annualized_vol = stdev * (12**0.5)

    # Score adjustment based on risk tolerance
    # Conservative: penalize volatility, Aggressive: reward volatility
    volatility_penalty = annualized_vol * (0.5 - risk_tolerance)  # ranges -0.5 to +0.5

    adjusted = base_score + volatility_penalty
    return round(max(0.0, min(1.0, adjusted)), 4)


# ── Rebalancing Recommendations ────────────────────────────────────────────

REBALANCE_THRESHOLD = 0.05  # 5% drift from target


def compute_rebalancing_recommendations(
    current_allocations: dict[str, float],
    target_allocations: dict[str, float],
    total_portfolio: float,
) -> dict[str, dict[str, Any]]:
    """Compute rebalancing trades to return to target allocations.

    Returns per-asset trade recommendations (buy/sell/hold).
    """
    recommendations: dict[str, dict[str, Any]] = {}

    for asset, current_pct in current_allocations.items():
        target_pct = target_allocations.get(asset, 0.0)
        drift = current_pct - target_pct

        # Skip if within threshold
        if abs(drift) < REBALANCE_THRESHOLD:
            recommendations[asset] = {
                "action": "HOLD",
                "current_pct": round(current_pct * 100, 2),
                "target_pct": round(target_pct * 100, 2),
                "drift_pct": round(drift * 100, 2),
                "usd_action": 0.0,
            }
            continue

        # Compute USD amount to trade
        usd_to_trade = drift * total_portfolio

        if usd_to_trade > 0:
            action = "SELL"
        else:
            action = "BUY"
            usd_to_trade = abs(usd_to_trade)

        recommendations[asset] = {
            "action": action,
            "current_pct": round(current_pct * 100, 2),
            "target_pct": round(target_pct * 100, 2),
            "drift_pct": round(drift * 100, 2),
            "usd_amount": round(usd_to_trade, 2),
        }

    return recommendations


# ── Monte Carlo Projections ────────────────────────────────────────────────


def MonteCarloProjection(
    current_portfolio: dict[str, float],
    expected_returns: dict[str, float],
    volatilities: dict[str, float],
    months: int = 12,
    simulations: int = 1000,
    risk_free_rate: float = 0.02,
) -> dict[str, Any]:
    """Run Monte Carlo simulation for portfolio projection.

    Returns percentile-based projections for portfolio value.
    """

    assets = list(current_portfolio.keys())

    # Initialize simulation results
    final_values: list[float] = []

    # Convert to monthly returns and volatilities
    monthly_returns = {a: expected_returns.get(a, 0.0) / 12 for a in assets}
    monthly_vols = {a: volatilities.get(a, 0.0) / (12**0.5) for a in assets}

    for _ in range(simulations):
        # Start with current portfolio value
        portfolio_value = sum(current_portfolio.values())

        # Simulate monthly returns
        for _ in range(months):
            # Generate random return using geometric Brownian motion
            for asset in assets:
                z = random.normalvariate(0, 1)
                monthly_return = monthly_returns[asset] + monthly_vols[asset] * z
                # Apply return proportionally
                weight = current_portfolio[asset] / portfolio_value if portfolio_value > 0 else 0
                portfolio_value *= 1 + monthly_return * weight

        final_values.append(portfolio_value)

    # Compute percentiles
    final_values.sort()
    p5 = final_values[int(0.05 * simulations)]
    p25 = final_values[int(0.25 * simulations)]
    p50 = final_values[int(0.5 * simulations)]  # median
    p75 = final_values[int(0.75 * simulations)]
    p95 = final_values[int(0.95 * simulations)]

    current_total = sum(current_portfolio.values())

    return {
        "current_value": current_total,
        "projections": {
            f"month_{months}": {
                "p5": round(p5, 2),
                "p25": round(p25, 2),
                "p50": round(p50, 2),
                "p75": round(p75, 2),
                "p95": round(p95, 2),
            }
        },
        "probability_of_growth": round(sum(1 for v in final_values if v > current_total) / simulations * 100, 2),
        "probability_of_loss": round(sum(1 for v in final_values if v < current_total * 0.9) / simulations * 100, 2),
        "simulations_run": simulations,
    }


# ── Advanced Maximizer Class ───────────────────────────────────────────────


class AdvancedWealthMaximizer:
    """Advanced wealth maximization with correlation, volatility, and rebalancing."""

    def __init__(self):
        self.correlation_matrix = CORRELATION_MATRIX
        self.history: list[dict[str, Any]] = []

    def compute_advanced_allocation(
        self,
        platform_balances: dict[str, float],
        crypto_summary: dict[str, Any],
        firefly_balances: dict[str, float] | None = None,
        takenos_balance: float = 0.0,
        risk_tolerance: float = 0.5,
    ) -> dict[str, Any]:
        """Compute advanced allocation with all factors considered."""
        from cores.capital.maximizer import compute_allocation_scores

        # Base scores from original maximizer
        base_results = compute_allocation_scores(
            platform_balances=platform_balances,
            crypto_summary=crypto_summary,
            firefly_balances=firefly_balances,
            takenos_balance=takenos_balance,
        )

        # Get portfolio total for rebalancing
        portfolio = {}
        portfolio.update(platform_balances)
        if crypto_summary:
            portfolio["crypto"] = crypto_summary.get("total_usd", 0.0)
        if firefly_balances:
            portfolio["firefly"] = sum(firefly_balances.values())
        portfolio["takenos"] = takenos_balance
        # Advanced adjustments per category
        advanced_results: dict[str, dict[str, Any]] = {}

        # 1. Platform bounty with correlation
        platform_total = sum(platform_balances.values()) if platform_balances else 0.0
        platform_adjusted: dict[str, Any] = {
            "total_balance": round(platform_total, 2),
            "allocations": {},
            "recommendation": "SCALE",
            "score": 0.0,
            "rationale": "",
        }

        remaining_score = 0.0
        for platform, balance in platform_balances.items():
            base_score = base_results["platform_bounty"]["allocations"][platform]["score"]
            corr_adjusted = _compute_correlation_adjusted_score(
                platform, base_score, portfolio, self.correlation_matrix
            )
            vol_adjusted = _compute_volatility_adjusted_score(
                platform, corr_adjusted, historical_returns=[], risk_tolerance=risk_tolerance
            )

            # Determine action
            if balance > 5000 and vol_adjusted > 0.6:
                action = "KEEP"
            elif balance < 1000 and vol_adjusted < 0.3:
                action = "DROP"
            else:
                action = "SCALE"

            platform_adjusted["allocations"][platform] = {
                "balance": round(balance, 2),
                "base_score": base_score,
                "correlation_adjusted_score": corr_adjusted,
                "volatility_adjusted_score": vol_adjusted,
                "action": action,
                "suggested_allocation_pct": round(
                    max(
                        0.05,
                        vol_adjusted
                        / sum(p["volatility_adjusted_score"] for p in platform_adjusted["allocations"].values())
                        * 100,
                    )
                    if platform_adjusted["allocations"]
                    else 0,
                    2,
                ),
            }
            remaining_score += vol_adjusted

        platform_adjusted["score"] = round(remaining_score / len(platform_balances), 4) if platform_balances else 0.0
        platform_adjusted["rationale"] = "Correlation and volatility adjusted allocation"
        advanced_results["platform_bounty"] = platform_adjusted

        # 2. Crypto with volatility adjustment
        crypto_total = crypto_summary.get("total_usd", 0.0) if crypto_summary else 0.0
        crypto_adjusted: dict[str, Any] = {
            "total_balance": round(crypto_total, 2),
            "allocations": {},
            "recommendation": "SCALE",
            "score": 0.0,
            "rationale": "",
        }

        by_coin = crypto_summary.get("by_coin", {}) if crypto_summary else {}
        if by_coin and crypto_total > 0:
            remaining_score = 0.0
            for coin, data in by_coin.items():
                usd_value = data.get("usd_value", 0.0)
                base_score = base_results["crypto_portfolio"]["allocations"][coin]["score"]
                hist_returns = data.get("historical_return_30d", 0)

                corr_adjusted = _compute_correlation_adjusted_score(
                    coin,
                    base_score,
                    {k: v for k, v in portfolio.items() if k != "crypto"},
                    self.correlation_matrix,
                )
                vol_adjusted = _compute_volatility_adjusted_score(
                    coin,
                    corr_adjusted,
                    historical_returns=[hist_returns] if hist_returns else None,
                    risk_tolerance=risk_tolerance,
                )

                # Determine action based on 30-day return and volatility
                hist_return = data.get("historical_return_30d", 0)
                if hist_return and hist_return > 15:
                    action = "KEEP"
                elif hist_return and hist_return < -10:
                    action = "DROP"
                else:
                    action = "SCALE"

                crypto_adjusted["allocations"][coin] = {
                    "usd_value": round(usd_value, 2),
                    "pct_of_portfolio": round(usd_value / crypto_total * 100, 2) if crypto_total > 0 else 0,
                    "base_score": base_score,
                    "correlation_adjusted_score": corr_adjusted,
                    "volatility_adjusted_score": vol_adjusted,
                    "30d_return": round(hist_return, 2) if hist_return else 0.0,
                    "action": action,
                    "suggested_allocation_pct": round(
                        max(
                            0.05,
                            vol_adjusted
                            / sum(c["volatility_adjusted_score"] for c in crypto_adjusted["allocations"].values())
                            * 100,
                        )
                        if crypto_adjusted["allocations"]
                        else 0,
                        2,
                    ),
                }
                remaining_score += vol_adjusted

            crypto_adjusted["score"] = round(remaining_score / len(by_coin), 4) if by_coin else 0.0
            crypto_adjusted["rationale"] = "Volatility and correlation adjusted crypto allocation"
            advanced_results["crypto_portfolio"] = crypto_adjusted
        else:
            advanced_results["crypto_portfolio"] = {
                "total_balance": 0.0,
                "allocations": {},
                "recommendation": "NO_DATA",
                "score": 0.0,
                "rationale": "No crypto data available",
            }

        # 3. Rebalancing analysis
        all_allocations = {}
        all_allocations.update(platform_balances)
        if crypto_summary:
            all_allocations["crypto"] = crypto_summary.get("total_usd", 0.0)
        if firefly_balances:
            all_allocations["firefly"] = sum(firefly_balances.values())
        all_allocations["takenos"] = takenos_balance
        all_total = sum(all_allocations.values())

        # Generate target allocations (equal weight as baseline, or could be optimized)
        n_assets = len(all_allocations)
        target_weight = 1.0 / n_assets if n_assets > 0 else 0

        rebalancing = compute_rebalancing_recommendations(
            current_allocations={k: v / all_total for k, v in all_allocations.items() if all_total > 0},
            target_allocations={k: target_weight for k in all_allocations},
            total_portfolio=all_total,
        )

        advanced_results["_rebalancing"] = rebalancing
        advanced_results["_metadata"] = {
            "risk_tolerance": risk_tolerance,
            "portfolio_total": round(all_total, 2),
            "generated_at": datetime.now(UTC).isoformat(),
            "correlation_matrix_used": "CORRELATION_MATRIX_v1",
        }

        # Store in history
        self.history.append(advanced_results.copy())
        if len(self.history) > 50:
            self.history = self.history[-50:]

        return advanced_results

    def get_rebalancing_report(self) -> dict[str, Any]:
        """Get the latest rebalancing recommendations from history."""
        if not self.history:
            return {"error": "No history available"}
        return self.history[-1].get("_rebalancing", {})


# ── Convenience Functions ─────────────────────────────────────────────────


def get_advanced_maximization_report(
    platform_balances: dict[str, float],
    crypto_summary: dict[str, Any],
    firefly_balances: dict[str, float] | None = None,
    takenos_balance: float = 0.0,
    risk_tolerance: float = 0.5,
) -> dict[str, Any]:
    """Generate advanced wealth maximization report."""
    maximizer = AdvancedWealthMaximizer()
    return maximizer.compute_advanced_allocation(
        platform_balances=platform_balances,
        crypto_summary=crypto_summary,
        firefly_balances=firefly_balances,
        takenos_balance=takenos_balance,
        risk_tolerance=risk_tolerance,
    )


__all__ = [
    "AdvancedWealthMaximizer",
    "get_advanced_maximization_report",
    "MonteCarloProjection",
    "compute_rebalancing_recommendations",
    "_compute_correlation_adjusted_score",
    "_compute_volatility_adjusted_score",
    "CORRELATION_MATRIX",
    "REBALANCE_THRESHOLD",
]
