from __future__ import annotations

import logging
from typing import Any

from cores.platforms.base import BugBountyPlatform, SubmissionResult, SyncResult

logger = logging.getLogger("ownex.platforms.intigriti")


class Intigriti(BugBountyPlatform):
    @property
    def platform_id(self) -> str:
        return "intigriti"

    @property
    def display_name(self) -> str:
        return "Intigriti"

    def _supports_api_submission(self) -> bool:
        return True

    def _format_report(self, report_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": report_data.get("vulnerability", "Security Finding"),
            "program": report_data.get("program", ""),
            "severity": report_data.get("severity", "medium"),
            "content": report_data.get("content", {}),
        }

    def _get_submit_url(self, report_data: dict[str, Any]) -> str:
        return "https://app.intigriti.com/researcher/submissions"

    def submit(self, report_data: dict[str, Any], api_key: str) -> SubmissionResult:
        formatted = self._format_report(report_data)
        try:
            import requests
            resp = requests.post(
                "https://api.intigriti.com/v1/submissions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=formatted,
                timeout=30,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                ext_id = data.get("id", "")
                return SubmissionResult(
                    success=True,
                    external_id=str(ext_id),
                    url=f"https://app.intigriti.com/researcher/submissions/{ext_id}",
                    data=data,
                )
            return SubmissionResult(
                success=False,
                error=f"Intigriti API error {resp.status_code}: {resp.text[:200]}",
            )
        except ImportError:
            return SubmissionResult(success=False, error="requests library not available")
        except Exception as exc:
            return SubmissionResult(success=False, error=str(exc))

    def check_status(self, external_id: str, api_key: str = "") -> str:
        try:
            import requests
            resp = requests.get(
                f"https://api.intigriti.com/v1/submissions/{external_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("status", "unknown")
            return "unknown"
        except Exception:
            return "unknown"

    def sync_earnings(self, api_key: str) -> SyncResult:
        try:
            import requests
            resp = requests.get(
                "https://api.intigriti.com/v1/researcher/submissions",
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return SyncResult(success=False, error=f"API error {resp.status_code}")

            data = resp.json()
            items = data if isinstance(data, list) else []
            earnings = []
            total_earned = 0.0
            total_pending = 0.0
            paid_statuses = {"resolved", "closed"}
            for item in items:
                bounty = item.get("bounty") or {}
                amount = float(bounty.get("amount", 0) or 0)
                state = item.get("status", "")
                entry = {
                    "id": item.get("id", ""),
                    "amount": amount,
                    "currency": bounty.get("currency", "EUR"),
                    "program": item.get("program", {}).get("name", ""),
                    "state": state,
                    "created_at": item.get("createdAt", ""),
                }
                earnings.append(entry)
                if state.lower() in paid_statuses:
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
