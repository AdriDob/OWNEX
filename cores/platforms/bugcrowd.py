from __future__ import annotations

import logging
from typing import Any

from cores.platforms.base import BugBountyPlatform, SubmissionResult, SyncResult

logger = logging.getLogger("cateye.platforms.bugcrowd")

BC_API_BASE = "https://api.bugcrowd.com/v1"


class Bugcrowd(BugBountyPlatform):
    @property
    def platform_id(self) -> str:
        return "bugcrowd"

    @property
    def display_name(self) -> str:
        return "Bugcrowd"

    def _supports_api_submission(self) -> bool:
        return True

    def _format_report(self, report_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "bugcrowd_submission": True,
            "title": report_data.get("vulnerability", "Security Finding"),
            "program": report_data.get("program", ""),
            "severity": report_data.get("severity", "medium"),
            "content": report_data.get("content", {}),
        }

    def _get_submit_url(self, report_data: dict[str, Any]) -> str:
        return "https://bugcrowd.com/submissions/new"

    def submit(self, report_data: dict[str, Any], api_key: str) -> SubmissionResult:
        formatted = self._format_report(report_data)
        try:
            import requests
            resp = requests.post(
                "https://api.bugcrowd.com/v1/submissions",
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
                    url=f"https://bugcrowd.com/submissions/{ext_id}",
                    data=data,
                )
            return SubmissionResult(
                success=False,
                error=f"Bugcrowd API error {resp.status_code}: {resp.text[:200]}",
            )
        except ImportError:
            return SubmissionResult(success=False, error="requests library not available")
        except Exception as exc:
            return SubmissionResult(success=False, error=str(exc))

    def check_status(self, external_id: str, api_key: str = "") -> str:
        try:
            import requests
            resp = requests.get(
                f"https://api.bugcrowd.com/v1/submissions/{external_id}",
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
                f"{BC_API_BASE}/researchers/me/bounties",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                },
                timeout=30,
            )
            if resp.status_code != 200:
                return SyncResult(success=False, error=f"API error {resp.status_code}")

            data = resp.json()
            bounties = data if isinstance(data, list) else data.get("data", [])
            earnings = []
            total_earned = 0.0
            total_pending = 0.0
            for b in bounties:
                attrs = b.get("attributes", {})
                amount = float(attrs.get("amount", 0) or 0)
                state = attrs.get("state", "")
                entry = {
                    "id": b.get("id", ""),
                    "amount": amount,
                    "currency": attrs.get("currency", "USD"),
                    "program": attrs.get("program_name", ""),
                    "submission_id": attrs.get("submission_id", ""),
                    "state": state,
                    "created_at": attrs.get("created_at", ""),
                }
                earnings.append(entry)
                if state == "paid":
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
