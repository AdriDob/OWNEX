"""HackerOne API connector — hacktivity + structured scopes."""

from __future__ import annotations

import base64
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("cateye.bugbounty.hackerone")

HACKERONE_API = "https://api.hackerone.com/v1"


class HackerOneConnector:
    def __init__(self) -> None:
        self._username = os.environ.get("HACKERONE_API_USERNAME", "")
        self._token = os.environ.get("HACKERONE_API_TOKEN", "")
        self._enabled = bool(self._username and self._token)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def _auth_header(self) -> dict[str, str]:
        raw = f"{self._username}:{self._token}"
        encoded = base64.b64encode(raw.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    def get_hacktivity(self, page: int = 1, per_page: int = 25) -> list[dict[str, Any]]:
        if not self._enabled:
            return []
        try:
            resp = httpx.get(
                f"{HACKERONE_API}/hackers/hacktivity",
                headers=self._auth_header(),
                params={"page[number]": page, "page[size]": per_page, "sort": "-disclosed_at"},
                timeout=15.0,
            )
            if resp.status_code == 200:
                return resp.json().get("data", [])
            logger.warning("Hacktivity fetch failed: HTTP %s", resp.status_code)
            return []
        except Exception as exc:
            logger.warning("Hacktivity fetch error: %s", exc)
            return []

    def get_structured_scopes(self, program_id: str) -> list[dict[str, Any]]:
        if not self._enabled:
            return []
        try:
            resp = httpx.get(
                f"{HACKERONE_API}/hackers/programs/{program_id}/structured_scopes",
                headers=self._auth_header(),
                timeout=15.0,
            )
            if resp.status_code == 200:
                return resp.json().get("data", [])
            logger.warning("Scopes fetch failed: HTTP %s", resp.status_code)
            return []
        except Exception as exc:
            logger.warning("Scopes fetch error: %s", exc)
            return []

    def get_programs(self, page: int = 1) -> list[dict[str, Any]]:
        if not self._enabled:
            return []
        try:
            resp = httpx.get(
                f"{HACKERONE_API}/hackers/programs",
                headers=self._auth_header(),
                params={"page[number]": page, "page[size]": 25},
                timeout=15.0,
            )
            if resp.status_code == 200:
                return resp.json().get("data", [])
            return []
        except Exception as exc:
            logger.warning("Programs fetch error: %s", exc)
            return []


_H1: HackerOneConnector | None = None


def get_hackerone_connector() -> HackerOneConnector:
    global _H1
    if _H1 is None:
        _H1 = HackerOneConnector()
    return _H1
