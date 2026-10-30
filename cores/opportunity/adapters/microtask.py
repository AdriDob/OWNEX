"""Microtask marketplace adapters — Prolific only.

Contract (honest by design):
- Prolific exposes an authenticated API: live fetch ONLY when an API
  key is configured (vault or config). Otherwise curated deep-links.
- Toloka/Clickworker removed per owner (purge 2026-09-13): sub-scale
  payouts, no skill assessment, not worth human time.
- Every item carries metadata["apply"] == "MANUAL": these platforms need
  accounts + qualifications that only a human completes.
- Rewards: published figures only, else 0.0 (never invented).
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

import httpx

from cores.credentials.adapter_helpers import load_credentials
from cores.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.opportunity.adapters.microtask")

_HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) OWNEX-discovery/1.0"}
_TIMEOUT_S = 12.0


def _curated(platform: str, entries: list[dict[str, str]]) -> list[RawOpportunity]:
    out: list[RawOpportunity] = []
    for entry in entries:
        out.append(
            RawOpportunity(
                id=entry["id"],
                name=entry["name"],
                description=entry["description"],
                platform=platform,
                url=entry["url"],
                reward=0.0,
                effort_hours=1.0,
                tags=["microtask", "manual_apply"],
                cycle="pulse",
                source_type="ai_work",
                source_name=platform,
                metadata={"apply": "MANUAL", "live": False},
            )
        )
    return out


class ProlificAdapter(OpportunityAdapter):
    """Prolific — research studies. Live API needs token."""

    platform = "prolific"
    cycle = "pulse"

    _CURATED = [
        {
            "id": "prolific-studies",
            "name": "Prolific: available studies",
            "description": "Prolific study feed (verified account required). Manual apply.",
            "url": "https://app.prolific.com/",
        },
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        merged = load_credentials("prolific", config)
        super().__init__(merged)
        self.api_key = (merged or {}).get("api_key") or (merged or {}).get("token")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Live study fetch when keyed, else curated deep-links. Never raises."""
        if self.api_key:
            try:
                headers = {**_HEADERS, "Authorization": f"Token {self.api_key}"}
                async with httpx.AsyncClient(timeout=_TIMEOUT_S, headers=headers) as client:
                    resp = await client.get("https://api.prolific.com/api/v1/studies/?published=true")
                    if resp.status_code == 200:
                        studies = resp.json().get("results", [])
                        out = []
                        for study in studies[:15]:
                            reward = 0.0
                            with contextlib.suppress(TypeError, ValueError):
                                reward = float(study.get("reward", 0) or 0)
                            out.append(
                                RawOpportunity(
                                    id=f"prolific_{study.get('id')}",
                                    name=study.get("name") or "Prolific study",
                                    description=study.get("description") or "Prolific study. Manual apply.",
                                    platform="prolific",
                                    url="https://app.prolific.com/",
                                    reward=reward,
                                    effort_hours=1.0,
                                    tags=["microtask", "manual_apply"],
                                    cycle="pulse",
                                    source_type="ai_work",
                                    source_name="prolific",
                                    metadata={"apply": "MANUAL", "live": True, "original": study},
                                )
                            )
                        if out:
                            return out
            except Exception as exc:
                logger.debug("Prolific live fetch failed (fallback to curated): %s", exc)
        return _curated("prolific", self._CURATED)
