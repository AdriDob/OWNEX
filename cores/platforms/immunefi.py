"""Immunefi platform connector — blockchain bug bounty submissions & payout sync."""

from __future__ import annotations

import json
import logging
from typing import Any

from cores.platforms.base import BugBountyPlatform, SubmissionResult, SyncResult

logger = logging.getLogger("cateye.platforms.immunefi")

IMMUNEFI_API_BASE = "https://api.immunefi.com/v1"
IMMUNEFI_SUBMIT_URL = "https://immunefi.com/submit/"


class Immunefi(BugBountyPlatform):
    @property
    def platform_id(self) -> str:
        return "immunefi"

    @property
    def display_name(self) -> str:
        return "Immunefi"

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
            "program": report_data.get("program", ""),
            "title": report_data.get("vulnerability", content.get("title", "Security Report")),
            "description": content.get("description", content.get("summary", "")),
            "vulnerability_type": content.get("vulnerability_type", report_data.get("vulnerability_type", "other")),
            "severity": report_data.get("severity", "medium"),
            "asset": content.get("asset", report_data.get("target", "")),
            "proof_of_concept": content.get("poc", content.get("proof_of_concept", "")),
            "reproduction_steps": content.get("reproduction_steps", []),
            "impact": content.get("impact", ""),
            "references": content.get("references", []),
            "source": "ORION",
        }

    def _get_submit_url(self, report_data: dict[str, Any]) -> str:
        return IMMUNEFI_SUBMIT_URL

    def submit(self, report_data: dict[str, Any], api_key: str) -> SubmissionResult:
        formatted = self._format_report(report_data)
        try:
            import requests

            resp = requests.post(
                f"{IMMUNEFI_API_BASE}/submissions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "program": formatted["program"],
                    "title": formatted["title"],
                    "description": formatted["description"],
                    "vulnerability_type": formatted["vulnerability_type"],
                    "severity": formatted["severity"],
                    "asset": formatted["asset"],
                    "proof_of_concept": formatted["proof_of_concept"],
                    "reproduction_steps": formatted["reproduction_steps"],
                    "impact": formatted["impact"],
                    "references": formatted["references"],
                },
                timeout=60,
            )
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                ext_id = data.get("id", data.get("submission_id", ""))
                return SubmissionResult(
                    success=True,
                    external_id=str(ext_id),
                    url=f"{IMMUNEFI_SUBMIT_URL}{ext_id}" if ext_id else IMMUNEFI_SUBMIT_URL,
                    data=data,
                )
            return SubmissionResult(
                success=False,
                error=f"Immunefi API error {resp.status_code}: {resp.text[:300]}",
            )
        except ImportError:
            return SubmissionResult(success=False, error="requests library not available")
        except Exception as exc:
            return SubmissionResult(success=False, error=str(exc))

    def check_status(self, external_id: str, api_key: str = "") -> str:
        try:
            import requests

            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            resp = requests.get(
                f"{IMMUNEFI_API_BASE}/submissions/{external_id}",
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("status", data.get("state", "unknown"))
            return "unknown"
        except Exception:
            return "unknown"

    def sync_earnings(self, api_key: str) -> SyncResult:
        try:
            import requests

            resp = requests.get(
                f"{IMMUNEFI_API_BASE}/me/bounties",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                },
                timeout=30,
            )
            if resp.status_code != 200:
                return SyncResult(success=False, error=f"API error {resp.status_code}")

            data = resp.json()
            bounties = data if isinstance(data, list) else data.get("data", data.get("bounties", []))
            earnings = []
            total = 0.0
            pending = 0.0

            for b in bounties:
                amount = float(b.get("amount", b.get("payout", 0)))
                currency = b.get("currency", b.get("token", "USD"))
                status = b.get("status", b.get("state", ""))
                total += amount
                if status.lower() in ("pending", "in_review"):
                    pending += amount
                earnings.append(
                    {
                        "id": b.get("id", ""),
                        "amount": amount,
                        "currency": currency,
                        "program": b.get("program", {}).get("name", b.get("project", "")),
                        "report_id": b.get("report_id", b.get("submission_id", "")),
                        "state": status,
                        "created_at": b.get("created_at", ""),
                        "paid_at": b.get("paid_at", ""),
                    }
                )

            return SyncResult(
                success=True,
                earnings=earnings,
                total_earned=total,
                total_pending=pending,
            )
        except Exception as exc:
            return SyncResult(success=False, error=str(exc))
