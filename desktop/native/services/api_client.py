"""OwnEx backend API client — source of truth for operational data.

The desktop shell is a panel: it does not run the scheduler or the
discovery pipeline. Operational data (targets, findings, activity, direct
work state) is owned by the backend process (api.main + api.scheduler),
reached through the defined HTTP interface at 127.0.0.1:8000.

Every call is defensive: any failure degrades to None/False, never raises,
so the UI can fall back to local in-process data.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path

import httpx

from database.db import user_data_dir

logger = logging.getLogger("ownex.native.api")

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
CONNECT_TIMEOUT = 1.5
REQUEST_TIMEOUT = 3.0
CONNECTED_CACHE_SECONDS = 5.0


class ApiClient:
    """Thin httpx client for the OwnEx backend API."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, data_dir: Path | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        # Device identity persists in the user data dir (survives upgrades).
        self._data_dir = data_dir if data_dir is not None else user_data_dir()
        self._device_id: str | None = None
        self._token: str | None = None
        self._refresh_token: str | None = None
        self._connected_until: float = 0.0
        self._load_device()

    # -- device identity (persisted next to the local data dir) -----------
    def _device_file(self) -> Path:
        return self._data_dir / "desktop_device.json"

    def _load_device(self) -> None:
        try:
            with open(self._device_file(), encoding="utf-8") as fh:
                data = json.load(fh)
            self._device_id = data.get("device_id")
            self._token = data.get("token")
            self._refresh_token = data.get("refresh_token")
        except Exception as exc:  # noqa: BLE001
            logger.debug("no persisted device id: %s", exc)

    def _save_device(self) -> None:
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            with open(self._device_file(), "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "device_id": self._device_id,
                        "token": self._token,
                        "refresh_token": self._refresh_token,
                    },
                    fh,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("could not persist device id: %s", exc)

    # -- connectivity ------------------------------------------------------
    def connected(self) -> bool:
        """True if the backend answers /api/health (cached briefly)."""
        now = time.monotonic()
        if now < self._connected_until:
            return True
        try:
            resp = httpx.get(self._base_url + "/api/health", timeout=CONNECT_TIMEOUT)
            ok = resp.status_code == 200
        except Exception as exc:  # noqa: BLE001
            logger.debug("backend health check failed: %s", exc)
            ok = False
        self._connected_until = now + CONNECTED_CACHE_SECONDS if ok else now
        return ok

    # -- auth --------------------------------------------------------------
    def login(self) -> bool:
        """Device-based login (POST /api/auth/login). Returns True on token."""
        if not self._device_id:
            self._device_id = "desktop-" + uuid.uuid4().hex[:16]
        try:
            resp = httpx.post(
                self._base_url + "/api/auth/login",
                json={"device_id": self._device_id, "device_info": {"app": "OWNEX Desktop"}},
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.warning("api login failed with status %s", resp.status_code)
                return False
            payload = resp.json()
            data = payload.get("data", payload) if isinstance(payload, dict) else {}
            token = (data or {}).get("token")
            if not token:
                logger.warning("api login response had no token")
                return False
            self._token = token
            self._refresh_token = (data or {}).get("refresh_token")
            self._save_device()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("api login failed: %s", exc)
            return False

    # -- generic GET -------------------------------------------------------
    def get(self, path: str, params: dict | None = None) -> dict | list | None:
        """GET with Bearer auth; one re-login retry on 401. Never raises."""
        token = self._token or ""
        headers = {"Authorization": "Bearer " + token} if token else {}
        for attempt in range(2):
            try:
                resp = httpx.get(
                    self._base_url + path,
                    params=params or {},
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("api GET %s failed: %s", path, exc)
                return None
            if resp.status_code == 401 and attempt == 0 and self.login():
                headers = {"Authorization": "Bearer " + (self._token or "")}
                continue
            if resp.status_code != 200:
                logger.debug("api GET %s status %s", path, resp.status_code)
                return None
            try:
                return resp.json()
            except Exception:  # noqa: BLE001
                logger.debug("api GET %s returned non-JSON", path)
                return None
        return None

    # -- domain fetchers (paginated contracts) ----------------------------
    def fetch_targets(self, limit: int = 20) -> list[dict]:
        data = self.get("/api/targets", {"limit": limit, "sort_by": "name", "sort_order": "asc"})
        if isinstance(data, dict):
            return data.get("items") or []
        return []

    def fetch_findings(self, limit: int = 50) -> list[dict]:
        data = self.get("/api/findings", {"limit": limit, "sort_by": "severity", "sort_order": "desc"})
        if isinstance(data, dict):
            return data.get("items") or []
        return []

    def fetch_activity(self, hours: int = 24, limit: int = 40) -> list[dict]:
        data = self.get("/api/activity", {"hours": hours, "limit": limit})
        if isinstance(data, list):
            return data
        return []

    def fetch_direct_work_status(self) -> dict | None:
        data = self.get("/api/direct-work/status")
        return data if isinstance(data, dict) else None
