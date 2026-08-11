"""Fees Calculator — estimates fees across different payout methods and routes."""

from __future__ import annotations

from typing import Any


class FeesCalculator:
    """Calculates and compares fees across payout methods and routes."""

    def estimate(
        self,
        amount_usd: float,
        method_type: str = "wallet",
        fee_percent: float = 0.0,
        fee_fixed: float = 0.0,
        currency: str = "USD",
    ) -> dict[str, Any]:
        percentage_fee = amount_usd * (fee_percent / 100.0)
        total_fee = percentage_fee + fee_fixed
        net = amount_usd - total_fee

        return {
            "input": {
                "amount": amount_usd,
                "currency": currency,
                "method_type": method_type,
            },
            "fees": {
                "percentage": round(percentage_fee, 2),
                "fixed": round(fee_fixed, 2),
                "total": round(total_fee, 2),
                "total_percent": round((total_fee / amount_usd * 100) if amount_usd > 0 else 0, 2),
            },
            "net": {
                "amount": round(net, 2),
                "currency": currency,
                "percent_lost": round((total_fee / amount_usd * 100) if amount_usd > 0 else 0, 2),
            },
        }

    def compare_methods(
        self,
        amount_usd: float,
        methods: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for method in methods:
            est = self.estimate(
                amount_usd=amount_usd,
                method_type=method.get("type", "wallet"),
                fee_percent=method.get("fee_percent", 0.0),
                fee_fixed=method.get("fee_fixed", 0.0),
                currency=method.get("currency", "USD"),
            )
            results.append(
                {
                    "method_id": method.get("id", "unknown"),
                    "method_name": method.get("name", "Unknown"),
                    **est,
                }
            )

        results.sort(key=lambda r: r["fees"]["total"])
        return results
