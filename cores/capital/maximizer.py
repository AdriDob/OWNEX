"""Wealth Maximization Engine — Optimization of capital allocation across OWNEX ecosystems.

Provides allocation recommendations (KEEP/DROP/SCALE) for:
- Platform bounty balances (bug bounty, hackerone, etc.)
- Crypto portfolio (BTC, ETH, SOL, tokens)
- Firefly III external accounting
- Takenos virtual wallet

Uses Sharpe-ratio-inspired scoring with risk-adjusted returns.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.capital.maximizer")


# ── Scoring Weights ────────────────────────────────────────────────────────

# Base weights for different asset categories
ASSET_WEIGHTS = {
    "bug_bounty": 0.25,  # High velocity, variable
    "hackerone": 0.20,  # Stable premium
    "test_platform": 0.10,  # Low frequency
    "crypto": 0.30,  # Growth-oriented
    "firefly": 0.10,  # Established assets
    "takenos": 0.05,  # Virtual/utility
}

# Risk adjustments per category
RISK_ADJUSTMENTS = {
    "bug_bounty": 0.8,  # Higher risk, variable income
    "hackerone": 0.9,  # Lower risk, stable
    "test_platform": 0.7,  # Variable risk
    "crypto": 1.2,  # High volatility
    "firefly": 0.5,  # Lower risk, traditional
    "takenos": 0.3,  # Very low risk
}

# Minimum allocation floor (percentage of portfolio)
MIN_ALLOCATION = 0.05  # 5% minimum per category


# ── Scoring Functions ─────────────────────────────────────────────────────


def _compute_category_score(
    category: str,
    balance: float,
    historical_returns: float | None = None,
    risk_factor: float | None = None,
) -> float:
    """Compute a score for a capital category.

    Higher score = better allocation candidate.
    Score combines:
    - Balance size (logarithmic, diminishing returns)
    - Historical performance (if available)
    - Risk adjustment
    - Velocity/liquidity factors
    """
    base_weight = ASSET_WEIGHTS.get(category, 0.1)
    risk_adj = RISK_ADJUSTMENTS.get(category, 0.5)

    # Balance score: log-based to avoid overallocation to large balances
    balance_score = min(1.0, (balance / 100000) ** 0.5) if balance > 0 else 0.0

    # Historical return factor (if provided)
    return_score = 1.0
    if historical_returns is not None:
        # Normalize to roughly 0-1 range; assume annualized %
        return_score = max(0.0, min(1.0, (historical_returns + 5) / 20))

    # Risk penalty/reward
    risk_factor = risk_factor or risk_adj
    risk_penalty = risk_factor  # lower risk factor = less penalty

    # Final score
    score = base_weight * balance_score * return_score * risk_penalty
    return round(min(1.0, score), 4)


def compute_allocation_scores(
    platform_balances: dict[str, float],
    crypto_summary: dict[str, Any],
    firefly_balances: dict[str, float] | None = None,
    takenos_balance: float = 0.0,
) -> dict[str, dict[str, Any]]:
    """Compute KEEP/DROP/SCALE recommendations for all capital categories.

    Returns per-category recommendations with scores and rationale.
    """
    results: dict[str, dict[str, Any]] = {}

    # 1. Platform bounty balances
    platform_total = sum(platform_balances.values()) if platform_balances else 0.0
    platform_rec: dict[str, Any] = {
        "total_balance": round(platform_total, 2),
        "allocations": {},
        "recommendation": "SCALE",
        "score": 0.0,
        "rationale": "",
    }

    # Distribute platform allocation across sub-platforms
    if platform_total > 0:
        remaining_score = 0.0
        for platform, balance in platform_balances.items():
            score = _compute_category_score(
                platform,
                balance,
                historical_returns=_get_historical_return(platform),
            )
            remaining_score += score

            # Determine action
            if balance > 5000 and score > 0.6:
                action = "KEEP"  # Established platform, maintain
            elif balance < 1000 and score < 0.3:
                action = "DROP"  # Underperforming, consider exiting
            else:
                action = "SCALE"  # Growth opportunity

            platform_rec["allocations"][platform] = {
                "balance": round(balance, 2),
                "score": round(score, 4),
                "action": action,
                "suggested_allocation_pct": round(max(MIN_ALLOCATION, score / remaining_score * 100) if remaining_score > 0 else 0, 2),
            }

        platform_rec["score"] = round(remaining_score / len(platform_balances), 4) if platform_balances else 0.0
    else:
        platform_rec["rationale"] = "No platform balances detected"

    results["platform_bounty"] = platform_rec

    # 2. Crypto portfolio
    crypto_total = crypto_summary.get("total_usd", 0.0) if crypto_summary else 0.0
    crypto_rec: dict[str, Any] = {
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
            balance_pct = usd_value / crypto_total if crypto_total > 0 else 0.0

            score = _compute_category_score(
                coin,
                usd_value,
                historical_returns=data.get("historical_return_30d"),
            )
            remaining_score += score

            # Determine action based on 30-day performance
            hist_return = data.get("historical_return_30d", 0)
            if hist_return and hist_return > 15:
                action = "KEEP"  # Strong performer
            elif hist_return and hist_return < -10:
                action = "DROP"  # Underperforming
            else:
                action = "SCALE"  # Hold/accumulate

            crypto_rec["allocations"][coin] = {
                "usd_value": round(usd_value, 2),
                "pct_of_portfolio": round(balance_pct * 100, 2),
                "score": round(score, 4),
                "30d_return": round(hist_return, 2) if hist_return else 0.0,
                "action": action,
                "suggested_allocation_pct": round(max(MIN_ALLOCATION, score / remaining_score * 100) if remaining_score > 0 else 0, 2),
            }

        crypto_rec["score"] = round(remaining_score / len(by_coin), 4) if by_coin else 0.0
    else:
        crypto_rec["rationale"] = "No crypto data available"

    results["crypto_portfolio"] = crypto_rec

    # 3. Firefly III balances
    if firefly_balances:
        firefly_total = sum(firefly_balances.values())
        firefly_rec: dict[str, Any] = {
            "total_balance": round(firefly_total, 2),
            "allocations": {},
            "recommendation": "KEEP",
            "score": 0.5,
            "rationale": "Established external accounting, maintain current allocation",
        }
        for account, balance in firefly_balances.items():
            firefly_rec["allocations"][account] = {
                "balance": round(balance, 2),
                "score": 0.5,
                "action": "KEEP",
                "suggested_allocation_pct": round(MIN_ALLOCATION * 100, 2),
            }
        results["firefly_accounts"] = firefly_rec
    else:
        results["firefly_accounts"] = {
            "total_balance": 0.0,
            "allocations": {},
            "recommendation": "NO_DATA",
            "score": 0.0,
            "rationale": "Firefly III not configured",
        }

    # 4. Takenos wallet
    takenos_rec: dict[str, Any] = {
        "total_balance": round(takenos_balance, 2),
        "allocations": {},
        "recommendation": "KEEP",
        "score": 0.8,
        "rationale": "Virtual wallet within ecosystem, maintain for operations",
    }
    if takenos_balance > 0:
        takenos_rec["allocations"]["takenos"] = {
            "balance": round(takenos_balance, 2),
            "score": 0.8,
            "action": "KEEP",
            "suggested_allocation_pct": round(MIN_ALLOCATION * 100, 2),
        }
    results["takenos_wallet"] = takenos_rec

    # 5. Compute overall portfolio score and recommendation
    all_scores = [r["score"] for r in results.values() if isinstance(r.get("score"), (int, float))]
    overall_score = round(sum(all_scores) / len(all_scores), 4) if all_scores else 0.0

    # Overall recommendation based on weighted analysis
    total_portfolio = platform_total + crypto_total + (sum(firefly_balances.values()) if firefly_balances else 0.0) + takenos_balance

    if overall_score > 0.6 and total_portfolio > 10_000:
        overall_rec = "SCALE"  # Growing portfolio, increase allocation
    elif overall_score < 0.3 and total_portfolio > 0:
        overall_rec = "DROP"  # Shrinking/underperforming, reassess
    else:
        overall_rec = "KEEP"  # Maintain current strategy

    results["_metadata"] = {
        "overall_score": overall_score,
        "total_portfolio_value": round(total_portfolio, 2),
        "overall_recommendation": overall_rec,
        "generated_at": datetime.now(UTC).isoformat(),
    }

    return results


def _get_historical_return(platform: str) -> float | None:
    """Get historical return for a platform (placeholder for real implementation)."""
    # This would integrate with the platform history/earnings data
    # For now, return None to use default scoring
    return None


# ── Convenience Functions ─────────────────────────────────────────────────


def get_maximization_report(
    platform_balances: dict[str, float],
    crypto_summary: dict[str, Any],
    firefly_balances: dict[str, float] | None = None,
    takenos_balance: float = 0.0,
) -> dict[str, Any]:
    """Generate a full wealth maximization report.

    Convenience wrapper that formats the output for display/export.
    """
    scores = compute_allocation_scores(
        platform_balances=platform_balances,
        crypto_summary=crypto_summary,
        firefly_balances=firefly_balances,
        takenos_balance=takenos_balance,
    )

    # Format readable report
    report: dict[str, Any] = {
        "summary": {
            "total_portfolio_value": scores["_metadata"]["total_portfolio_value"],
            "overall_score": scores["_metadata"]["overall_score"],
            "overall_recommendation": scores["_metadata"]["overall_recommendation"],
        },
        "categories": {},
        "generated_at": scores["_metadata"]["generated_at"],
    }

    # Add category details (excluding metadata)
    for category, data in scores.items():
        if category == "_metadata":
            continue
        report["categories"][category] = {
            "total_balance": data["total_balance"],
            "recommendation": data["recommendation"],
            "score": data["score"],
            "action_plan": {k: v["action"] for k, v in data.get("allocations", {}).items()},
        }

    return report


# ── Singleton instance ─────────────────────────────────────────────────────

maximizer = None  # Will be initialized on demand


def get_maximizer() -> Any:
    """Get or create the maximizer singleton."""
    global maximizer
    if maximizer is None:
        maximizer = WealthMaximizer()
    return maximizer


class WealthMaximizer:
    """Singleton class for wealth maximization operations."""

    def __init__(self):
        self.history: list[dict[str, Any]] = []
        self.last_generation: str | None = None

    def generate_report(
        self,
        platform_balances: dict[str, float],
        crypto_summary: dict[str, Any],
        firefly_balances: dict[str, float] | None = None,
        takenos_balance: float = 0.0,
    ) -> dict[str, Any]:
        """Generate a wealth maximization report and store it in history."""
        report = get_maximization_report(
            platform_balances=platform_balances,
            crypto_summary=crypto_summary,
            firefly_balances=firefly_balances,
            takenos_balance=takenos_balance,
        )
        self.history.append(report.copy())
        self.last_generation = report["_metadata"]["generated_at"] if "_metadata" in report else None
        # Keep history manageable
        if len(self.history) > 50:
            self.history = self.history[-50:]
        return report

    def get_trend_analysis(self, category: str, months: int = 3) -> dict[str, Any]:
        """Analyze trend for a capital category over recent months."""
        # Placeholder - would integrate with historical data
        return {
            "category": category,
            "months_analyzed": months,
            "trend": "stable",  # improving, declining, stable
            "average_score": 0.5,
            "recommendation": "MONITOR",
        }


__all__ = [
    "compute_allocation_scores",
    "get_maximization_report",
    "WealthMaximizer",
    "get_maximizer",
    "MIN_ALLOCATION",
    "ASSET_WEIGHTS",
    "RISK_ADJUSTMENTS",
]
