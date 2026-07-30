from __future__ import annotations

import logging
from typing import Any

from cores.platforms.base import BugBountyPlatform, SyncResult

logger = logging.getLogger("ownex.platforms.synack")


class Synack(BugBountyPlatform):
    @property
    def platform_id(self) -> str:
        return "synack"

    @property
    def display_name(self) -> str:
        return "Synack"

    def _supports_api_submission(self) -> bool:
        return False

    def _format_report(self, report_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": report_data.get("vulnerability", "Security Finding"),
            "program": report_data.get("program", ""),
            "severity": report_data.get("severity", "medium"),
            "content": report_data.get("content", {}),
        }

    def _get_submit_url(self, report_data: dict[str, Any]) -> str:
        return "https://synack.com/red-team/reporting"

    def sync_earnings(self, api_key: str) -> SyncResult:
        try:
            import requests

            resp = requests.get(
                "https://api.synack.com/api/v3/submissions",
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return SyncResult(success=False, error=f"API error {resp.status_code}")

            data = resp.json()
            items = data.get("data", data if isinstance(data, list) else [])
            if isinstance(items, dict):
                items = [items]
            earnings = []
            total_earned = 0.0
            total_pending = 0.0
            for item in items:
                payout = item.get("payout") or {}
                amount = float(payout.get("amount", 0) or 0)
                state = item.get("status", "")
                entry = {
                    "id": item.get("id", ""),
                    "amount": amount,
                    "currency": payout.get("currency", "USD"),
                    "program": item.get("target", {}).get("codename", ""),
                    "state": state,
                    "created_at": item.get("created_at", ""),
                }
                earnings.append(entry)
                if state.lower() == "paid":
                    total_earned += amount
                else:
                    total_pending += amount

            return SyncResult(
                success=True,
                earnings=earnings,
                total_earned=total_earned,
                total_pending=total_pending,
            )
        except Exception as exc:
            return SyncResult(success=False, error=str(exc))
