"""Code4rena platform connector — audit contest submission & payout sync.

Code4rena is an audit marketplace where security researchers compete
to find vulnerabilities in smart contracts. Submissions are via GitHub
issues (not API), so this connector primarily supports:
  - Report preparation with contest-specific formatting
  - Status checking via the Code4rena API
  - Payout sync from completed contests
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cores.platforms.base import BugBountyPlatform, SubmissionResult, SyncResult

logger = logging.getLogger("cateye.platforms.code4rena")

C4_API_BASE = "https://api.code4rena.com/api"
C4_SUBMIT_URL = "https://github.com/code-423n4"


class Code4rena(BugBountyPlatform):
    @property
    def platform_id(self) -> str:
        return "code4rena"

    @property
    def display_name(self) -> str:
        return "Code4rena"

    def _supports_api_submission(self) -> bool:
        return False  # Submissions are via GitHub issues

    def _format_report(self, report_data: dict[str, Any]) -> dict[str, Any]:
        content = report_data.get("content", {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                content = {"summary": content[:200]}

        vuln_type = content.get("vulnerability_type", report_data.get("vulnerability_type", ""))
        severity = report_data.get("severity", "medium")

        # Code4rena uses Gas/QA/Med/High severity labels
        severity_map = {
            "critical": "High",
            "high": "High",
            "medium": "Medium",
            "low": "QA (Quality Assurance)",
            "info": "Gas (Optimization)",
        }
        c4_severity = severity_map.get(severity, severity.capitalize())

        return {
            "contest": report_data.get("program", ""),
            "title": content.get("title", report_data.get("vulnerability", "Security Finding")),
            "vulnerability_type": vuln_type,
            "severity": c4_severity,
            "description": content.get("description", content.get("summary", "")),
            "proof_of_concept": content.get("poc", content.get("proof_of_concept", "")),
            "reproduction_steps": content.get("reproduction_steps", []),
            "impact": content.get("impact", ""),
            "recommended_mitigation": content.get("remediation", content.get("recommendation", "")),
            "references": content.get("references", []),
            "source": "ORION",
        }

    def _get_submit_url(self, report_data: dict[str, Any]) -> str:
        contest = report_data.get("program", "")
        if contest:
            return f"{C4_SUBMIT_URL}/{contest}/issues"
        return C4_SUBMIT_URL

    def submit(self, report_data: dict[str, Any], api_key: str) -> SubmissionResult:
        return SubmissionResult(
            success=False,
            error="Code4rena does not support API submission. Submit via GitHub issues.",
        )

    def check_status(self, external_id: str, api_key: str = "") -> str:
        try:
            import requests

            resp = requests.get(
                f"{C4_API_BASE}/findings?id={external_id}",
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
                f"{C4_API_BASE}/awarded",
                headers={"Accept": "application/json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return SyncResult(success=False, error=f"API error {resp.status_code}")

            data = resp.json()
            awards = data if isinstance(data, list) else data.get("data", data.get("awards", []))
            earnings = []
            total = 0.0
            pending = 0.0

            for a in awards:
                amount = float(a.get("amount", a.get("award", 0)))
                currency = a.get("currency", "USDC")
                status = a.get("status", a.get("state", "paid"))
                total += amount
                if status.lower() in ("pending", "in_review", "awaiting_payment"):
                    pending += amount
                earnings.append(
                    {
                        "id": a.get("id", ""),
                        "amount": amount,
                        "currency": currency,
                        "contest": a.get("contest", a.get("program", "")),
                        "finding": a.get("finding", a.get("issue", "")),
                        "state": status,
                        "paid_at": a.get("paid_at", a.get("timestamp", "")),
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
