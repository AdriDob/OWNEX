"""Payout Advisor — recommends payout methods per platform for Argentina."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Re-export and extend the existing payout_recommender data
from cores.financial.payout_recommender import (
    PlatformPayoutInfo as _PlatformPayoutInfo,
)
from cores.financial.payout_recommender import (
    get_best_methods_for_argentina as _get_best_methods,
)
from cores.financial.payout_recommender import (
    get_platform_payout as _get_platform_payout,
)
from cores.financial.payout_recommender import (
    list_all_payout_infos as _list_all_payout_infos,
)


@dataclass
class PayoutSimulation:
    amount_usd: float
    source_platform: str
    route_steps: list[dict[str, Any]] = field(default_factory=list)
    total_fees_usd: float = 0.0
    total_fees_percent: float = 0.0
    net_amount_usd: float = 0.0
    net_amount_ars: float = 0.0
    estimated_arrival_days: str = "N/A"
    risks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount_usd": self.amount_usd,
            "source_platform": self.source_platform,
            "route_steps": self.route_steps,
            "total_fees_usd": round(self.total_fees_usd, 2),
            "total_fees_percent": round(self.total_fees_percent, 2),
            "net_amount_usd": round(self.net_amount_usd, 2),
            "net_amount_ars": round(self.net_amount_ars, 2),
            "estimated_arrival_days": self.estimated_arrival_days,
            "risks": self.risks,
            "recommendations": self.recommendations,
        }


# Dummy ARS exchange rate — in production, pull from CoinGeckoFeed or external API
_DOLAR_BLUE_RATE = 1350.0


class PayoutAdvisor:
    """Advises on optimal payout strategy per platform."""

    def get_platform_info(self, platform_id: str) -> dict[str, Any] | None:
        raw = _get_platform_payout(platform_id)
        if raw is None:
            return None
        return self._info_to_dict(raw)

    def list_platforms(self) -> list[dict[str, Any]]:
        return _list_all_payout_infos()

    def best_routes_for_argentina(self) -> list[dict[str, Any]]:
        return _get_best_methods()

    def simulate_payout(
        self,
        amount_usd: float,
        source_platform: str,
        preferred_method: str | None = None,
        ars_rate: float = _DOLAR_BLUE_RATE,
    ) -> PayoutSimulation:
        platform_info = _get_platform_payout(source_platform)
        if platform_info is None:
            return PayoutSimulation(
                amount_usd=amount_usd,
                source_platform=source_platform,
                total_fees_usd=0.0,
                net_amount_usd=amount_usd,
                estimated_arrival_days="N/A",
                risks=["Unknown platform"],
                recommendations=[f"No payout data for {source_platform}. Add it to the registry."],
            )

        sim = PayoutSimulation(amount_usd=amount_usd, source_platform=source_platform)
        methods_to_try: list[str] = []

        if preferred_method:
            if preferred_method in [m.id for m in platform_info.methods]:
                methods_to_try = [preferred_method]
            else:
                sim.risks.append(f"Preferred method '{preferred_method}' not available for {source_platform}")

        if not methods_to_try:
            methods_to_try = platform_info.recommended

        route_steps: list[dict[str, Any]] = []
        total_fees = 0.0
        all_risks: list[str] = []

        for method_id in methods_to_try[:2]:
            method = next((m for m in platform_info.methods if m.id == method_id), None)
            if method is None:
                continue

            step_fee = amount_usd * (method.fee_percent / 100.0)
            total_fees += step_fee

            route_steps.append(
                {
                    "method": method_id,
                    "name": method.name,
                    "type": method.type,
                    "fee_percent": method.fee_percent,
                    "fee_usd": round(step_fee, 2),
                    "arrival_days": method.arrival_days,
                    "currencies": method.currencies,
                }
            )

            if method.type == "crypto":
                all_risks.append("Crypto price volatility between receipt and conversion")
            if method.kyc_level == "passport":
                all_risks.append(f"{method.name} requires passport-level KYC")
            if method.fee_percent > 3:
                all_risks.append(f"High fee ({method.fee_percent}%) on {method.name}")

        if not route_steps and not sim.risks:
            all_risks.append(f"No payout methods defined for {source_platform}")

        net_usd = amount_usd - total_fees
        net_ars = net_usd * ars_rate

        sim.route_steps = route_steps
        sim.total_fees_usd = total_fees
        sim.total_fees_percent = round((total_fees / amount_usd * 100) if amount_usd > 0 else 0, 2)
        sim.net_amount_usd = net_usd
        sim.net_amount_ars = net_ars
        sim.estimated_arrival_days = route_steps[0]["arrival_days"] if route_steps else "N/A"
        sim.risks = all_risks

        if route_steps:
            best = route_steps[0]
            sim.recommendations = [
                f"Use {best['name']} — {best['fee_percent']}% fee, arrives in {best['arrival_days']} days",
                f"Net after fees: ${net_usd:.2f} USD ≈ ${net_ars:.2f} ARS (rate: {ars_rate})",
            ]

        if total_fees > amount_usd * 0.1:
            sim.recommendations.append(
                "Consider holding USD instead of converting to ARS if you don't need pesos immediately"
            )

        return sim

    def _info_to_dict(self, info: _PlatformPayoutInfo) -> dict[str, Any]:
        return {
            "platform_id": info.platform_id,
            "platform_name": info.platform_name,
            "methods": [
                {
                    "id": m.id,
                    "name": m.name,
                    "type": m.type,
                    "kyc_level": m.kyc_level,
                    "currencies": m.currencies,
                    "fee_percent": m.fee_percent,
                    "arrival_days": m.arrival_days,
                    "notes": m.notes,
                }
                for m in info.methods
            ],
            "recommended": info.recommended,
            "kyc_required": info.kyc_required,
            "notes": info.notes,
        }
