from __future__ import annotations

import json
import logging
from typing import Any

from cores.platforms.base import BugBountyPlatform, SubmissionResult, SyncResult

logger = logging.getLogger("catseye.platforms.hackerone")

H1_SUBMIT_URL = "https://hackerone.com/reports/new"
H1_API_BASE = "https://api.hackerone.com/v1"


class HackerOne(BugBountyPlatform):
    @property
    def platform_id(self) -> str:
        return "hackerone"

    @property
    def display_name(self) -> str:
        return "HackerOne"

    def _supports_api_submission(self) -> bool:
        return True

    def _format_report(self, report_data: dict[str, Any]) -> dict[str, Any]:
        content = report_data.get("content", {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                content = {"summary": content[:200]}
        return {
            "team_handle": report_data.get("program", ""),
            "title": report_data.get("vulnerability", content.get("title", "Security Report")),
            "vulnerability": content,
            "severity_rating": report_data.get("severity", "medium"),
            "source": "CATEYE",
        }

    def _get_submit_url(self, report_data: dict[str, Any]) -> str:
        return H1_SUBMIT_URL

    def submit(self, report_data: dict[str, Any], api_key: str) -> SubmissionResult:
        formatted = self._format_report(report_data)
        try:
            import requests
            resp = requests.post(
                f"{H1_API_BASE}/reports",
                auth=(api_key, ""),
                json={
                    "data": {
                        "type": "report",
                        "attributes": {
                            "title": formatted["title"],
                            "vulnerability": formatted["vulnerability"],
                            "severity_rating": formatted["severity_rating"],
                            "source": "CATEYE",
                        },
                    }
                },
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                ext_id = data.get("data", {}).get("id", "")
                return SubmissionResult(
                    success=True,
                    external_id=str(ext_id),
                    url=f"https://hackerone.com/reports/{ext_id}",
                    data=data,
                )
            return SubmissionResult(
                success=False,
                error=f"HackerOne API error {resp.status_code}: {resp.text[:200]}",
            )
        except ImportError:
            return SubmissionResult(
                success=False,
                error="requests library not available",
            )
        except Exception as exc:
            return SubmissionResult(
                success=False,
                error=str(exc),
            )

    def check_status(self, external_id: str, api_key: str = "") -> str:
        try:
            import requests
            resp = requests.get(
                f"{H1_API_BASE}/reports/{external_id}",
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                attr = data.get("data", {}).get("attributes", {})
                return attr.get("state", "unknown")
            return "unknown"
        except Exception:
            return "unknown"

    def sync_earnings(self, api_key: str) -> SyncResult:
        try:
            import requests
            resp = requests.get(
                f"{H1_API_BASE}/me/bounties",
                auth=(api_key, ""),
                headers={"Accept": "application/json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return SyncResult(success=False, error=f"API error {resp.status_code}")

            data = resp.json()
            bounties = data if isinstance(data, list) else data.get("data", [])
            earnings = []
            total = 0.0
            for b in bounties:
                attrs = b.get("attributes", {})
                amount = float(attrs.get("amount", 0))
                total += amount
                earnings.append({
                    "id": b.get("id", ""),
                    "amount": amount,
                    "currency": attrs.get("currency", "USD"),
                    "program": attrs.get("team", {}).get("handle", ""),
                    "report_id": attrs.get("report", {}).get("id", ""),
                    "state": attrs.get("state", ""),
                    "created_at": attrs.get("created_at", ""),
                })

            return SyncResult(
                success=True,
                earnings=earnings,
                total_earned=total,
                total_pending=0.0,
            )
        except Exception as exc:
            return SyncResult(success=False, error=str(exc))
