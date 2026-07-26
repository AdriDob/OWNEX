"""Platform Registry — compares payout platforms side by side."""

from __future__ import annotations

from typing import Any

from cores.financial.payout_recommender import list_all_payout_infos

# Extended comparison data for each platform
_PLATFORM_DETAILS: dict[str, dict[str, Any]] = {
    "hackerone": {
        "payout_methods": ["Payoneer", "Bank Transfer", "Crypto (some programs)"],
        "min_payout": 100,
        "payout_frequency": "Per report, upon acceptance",
        "payout_time_avg_days": "7-14 after acceptance",
        "fee_to_receiver": "Payoneer: 2%, Bank: varies",
        "tax_forms": ["W-8BEN (mandatory for non-US)"],
        "argentina_friendly": True,
        "notes": "Largest platform. Payoneer is the most practical for Argentina. Some programs support crypto directly.",
    },
    "bugcrowd": {
        "payout_methods": ["Payoneer", "Bank Transfer"],
        "min_payout": 50,
        "payout_frequency": "Per bounty, upon triage acceptance",
        "payout_time_avg_days": "5-10 after acceptance",
        "fee_to_receiver": "Payoneer: 2%, Bank: varies",
        "tax_forms": ["W-8BEN (for US programs)"],
        "argentina_friendly": True,
        "notes": "Good platform. Payoneer works well. Some VDP programs don't pay.",
    },
    "intigriti": {
        "payout_methods": ["PayPal", "Bank Transfer"],
        "min_payout": 50,
        "payout_frequency": "Per report, after validation",
        "payout_time_avg_days": "7-21 after acceptance",
        "fee_to_receiver": "PayPal: 4.4% + fixed fee, Bank: varies",
        "tax_forms": ["EU tax form required"],
        "argentina_friendly": True,
        "notes": "European platform. PayPal is main option. Consider pairing with Lemon Cash for ARS extraction.",
    },
    "synack": {
        "payout_methods": ["Payoneer", "Bank Transfer"],
        "min_payout": 100,
        "payout_frequency": "Monthly or per milestone",
        "payout_time_avg_days": "30-45 (monthly cycle)",
        "fee_to_receiver": "Payoneer: 2%",
        "tax_forms": ["W-8BEN mandatory", "NDA required"],
        "argentina_friendly": True,
        "notes": "Invitation-only. Monthly payouts. Payoneer is reliable. W-8BEN is mandatory.",
    },
    "yeswehack": {
        "payout_methods": ["PayPal", "Bank Transfer (SEPA)", "Crypto (some)"],
        "min_payout": 50,
        "payout_frequency": "Per validated report",
        "payout_time_avg_days": "7-14 after validation",
        "fee_to_receiver": "PayPal: 4.4%",
        "tax_forms": ["May require EU tax info"],
        "argentina_friendly": True,
        "notes": "European platform. Crypto option available for some programs.",
    },
    "immunefi": {
        "payout_methods": ["USDC", "USDT", "ETH", "DAI", "Other crypto"],
        "min_payout": "Varies by program (often $1,000+)",
        "payout_frequency": "Per valid finding, on-chain",
        "payout_time_avg_days": "1-3 after acceptance (on-chain)",
        "fee_to_receiver": "Gas fees only (network dependent)",
        "tax_forms": ["No tax forms required (crypto)"],
        "argentina_friendly": True,
        "notes": "Best for crypto payouts. No KYC needed from platform side. High-value targets (DeFi protocols).",
    },
    "code4rena": {
        "payout_methods": ["USDC", "USDT", "ETH"],
        "min_payout": "Varies by contest",
        "payout_frequency": "After contest completion + judging",
        "payout_time_avg_days": "14-30 after contest ends",
        "fee_to_receiver": "Gas fees only",
        "tax_forms": ["No tax forms (crypto)"],
        "argentina_friendly": True,
        "notes": "Audit contests. Payouts in crypto. Competitive but rewarding.",
    },
    "huntr": {
        "payout_methods": ["PayPal"],
        "min_payout": "Varies",
        "payout_frequency": "Per accepted report",
        "payout_time_avg_days": "7-14 after acceptance",
        "fee_to_receiver": "PayPal: 4.4%",
        "tax_forms": ["May require W-8BEN"],
        "argentina_friendly": True,
        "notes": "PayPal is the only option. Pair with Lemon Cash / Belo for ARS.",
    },
}


class PlatformRegistry:
    """Compares payout platforms for informed decision making."""

    def list_platforms(self) -> list[dict[str, Any]]:
        base = list_all_payout_infos()
        enriched: list[dict[str, Any]] = []
        for info in base:
            pid = info.get("platform_id", "")
            details = _PLATFORM_DETAILS.get(pid, {})
            enriched.append({**info, **details})
        return enriched

    def get_platform(self, platform_id: str) -> dict[str, Any] | None:
        details = _PLATFORM_DETAILS.get(platform_id.lower())
        if details is None:
            return None

        base = None
        for info in list_all_payout_infos():
            if info.get("platform_id") == platform_id.lower():
                base = info
                break

        result = {**(base or {}), **details}
        return result

    def compare(self, platform_ids: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for pid in platform_ids:
            platform = self.get_platform(pid)
            if platform:
                results.append(platform)
        return results

    def argentina_ranked(self) -> list[dict[str, Any]]:
        platforms = self.list_platforms()
        return sorted(
            platforms,
            key=lambda p: (
                p.get("argentina_friendly", False),
                not p.get("fee_to_receiver", "").startswith("Gas"),
                p.get("min_payout", 9999) if isinstance(p.get("min_payout"), (int, float)) else 9999,
            ),
            reverse=True,
        )
