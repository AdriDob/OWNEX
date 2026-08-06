"""Auto-Tax Tracker — registra ingresos para impuestos.

Automatically tracks:
- Income by source (BB, Pulse, Forge, Investment)
- By currency (USD, crypto)
- By date (monthly, yearly)
- Generates tax reports
- Calculates estimated tax owed
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("orion.auto_tax")


class AutoTaxTracker:
    """Tracks all income for tax purposes."""

    def __init__(self) -> None:
        self._data_dir = os.path.expanduser("~/.config/ownex/taxes/")
        os.makedirs(self._data_dir, exist_ok=True)

    def record_income(
        self,
        amount: float,
        currency: str,
        source: str,
        platform: str,
        date: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Record an income entry."""
        entry = {
            "amount": amount,
            "currency": currency.upper(),
            "source": source,
            "platform": platform,
            "date": date or datetime.now(UTC).isoformat(),
            "description": description,
            "recorded_at": datetime.now(UTC).isoformat(),
        }

        # Save to monthly file
        month_key = entry["date"][:7]  # YYYY-MM
        monthly_file = os.path.join(self._data_dir, f"{month_key}.json")

        entries = []
        if os.path.exists(monthly_file):
            with open(monthly_file) as f:
                entries = json.load(f)

        entries.append(entry)
        with open(monthly_file, "w") as f:
            json.dump(entries, f, indent=2)

        logger.info("[TAX] Recorded: $%.2f %s from %s/%s", amount, currency, platform, source)
        return entry

    def get_monthly_summary(self, year_month: str = "") -> dict[str, Any]:
        """Get income summary for a month."""
        if not year_month:
            year_month = datetime.now(UTC).strftime("%Y-%m")

        monthly_file = os.path.join(self._data_dir, f"{year_month}.json")

        if not os.path.exists(monthly_file):
            return {"month": year_month, "total": 0, "entries": [], "by_source": {}}

        with open(monthly_file) as f:
            entries = json.load(f)

        total = sum(e["amount"] for e in entries)
        by_source: dict[str, float] = {}
        by_platform: dict[str, float] = {}

        for e in entries:
            source = e.get("source", "unknown")
            platform = e.get("platform", "unknown")
            by_source[source] = by_source.get(source, 0) + e["amount"]
            by_platform[platform] = by_platform.get(platform, 0) + e["amount"]

        return {
            "month": year_month,
            "total": round(total, 2),
            "entries": len(entries),
            "by_source": by_source,
            "by_platform": by_platform,
            "detail": entries,
        }

    def get_yearly_summary(self, year: str = "") -> dict[str, Any]:
        """Get income summary for a year."""
        if not year:
            year = datetime.now(UTC).strftime("%Y")

        months = []
        yearly_total = 0.0

        for m in range(1, 13):
            ym = f"{year}-{m:02d}"
            monthly = self.get_monthly_summary(ym)
            if monthly["entries"] > 0:
                months.append(monthly)
                yearly_total += monthly["total"]

        return {
            "year": year,
            "total": round(yearly_total, 2),
            "months": months,
            "months_with_income": len(months),
        }

    def generate_tax_report(self, year: str = "") -> dict[str, Any]:
        """Generate a tax report for the year."""
        summary = self.get_yearly_summary(year)

        # Estimate tax (simplified US progressive)
        total = summary["total"]
        estimated_tax = self._estimate_tax(total)

        return {
            "report_type": "Annual Income Summary",
            "year": summary["year"],
            "total_income": total,
            "estimated_tax": round(estimated_tax, 2),
            "effective_rate": round(estimated_tax / max(total, 1) * 100, 1),
            "by_source": summary.get("by_source", {}),
            "detail": summary,
            "generated_at": datetime.now(UTC).isoformat(),
            "disclaimer": "This is an estimate. Consult a tax professional.",
        }

    def _estimate_tax(self, income: float) -> float:
        """Simplified US federal tax estimate (single filer 2024)."""
        brackets = [
            (0, 11600, 0.10),
            (11600, 47150, 0.12),
            (47150, 100525, 0.22),
            (100525, 191950, 0.24),
            (191950, 243725, 0.32),
            (243725, 609350, 0.35),
            (609350, float("inf"), 0.37),
        ]

        tax = 0.0
        for low, high, rate in brackets:
            if income > high:
                tax += (high - low) * rate
            else:
                tax += max(0, income - low) * rate
                break

        return tax


_tracker: AutoTaxTracker | None = None


def get_tax_tracker() -> AutoTaxTracker:
    """Get singleton AutoTaxTracker."""
    global _tracker
    if _tracker is None:
        _tracker = AutoTaxTracker()
    return _tracker
