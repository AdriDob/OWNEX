"""OwnEx backend API client — source of truth for operational data.

The desktop shell is a panel: it does not run the scheduler or the
discovery pipeline. Operational data (targets, findings, activity, direct
work state) is owned by the backend process (api.main + api.scheduler),
reached through the defined HTTP interface at 127.0.0.1:8000.

Every call is defensive: any failure degrades to None/False, never raises,
so the UI can fall back to local in-process data. The client tolerates
temporary backend unavailability and will retry when the service returns.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

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
        for attempt in range(3):
            try:
                resp = httpx.post(
                    self._base_url + "/api/auth/login",
                    json={"device_id": self._device_id, "device_info": {"app": "OWNEX Desktop"}},
                    timeout=REQUEST_TIMEOUT,
                )
                if resp.status_code != 200:
                    if attempt < 2:
                        time.sleep(1.0)
                        continue
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
                if attempt < 2:
                    time.sleep(1.0)
                    continue
                logger.warning("api login failed: %s", exc)
                return False
        return False

    # -- generic GET -------------------------------------------------------
    def get(self, path: str, params: dict | None = None) -> dict | list | None:
        """GET with Bearer auth; retries on 401 with re-login. Never raises."""
        token = self._token or ""
        headers = {"Authorization": "Bearer " + token} if token else {}
        for attempt in range(3):
            try:
                resp = httpx.get(
                    self._base_url + path,
                    params=params or {},
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("api GET %s failed: %s", path, exc)
                if attempt < 2:
                    time.sleep(0.5)
                    continue
                return None
            if resp.status_code == 401 and attempt < 2 and self.login():
                headers = {"Authorization": "Bearer " + (self._token or "")}
                continue
            if resp.status_code != 200:
                logger.debug("api GET %s status %s", path, resp.status_code)
                # If no token and we got 200, return what we can
                if not token and resp.status_code == 200:
                    try:
                        return resp.json()
                    except Exception:
                        return None
                return None
            try:
                return resp.json()
            except Exception:  # noqa: BLE001
                logger.debug("api GET %s returned non-JSON", path)
                return None
        return None

    # -- generic POST ------------------------------------------------------
    def post(self, path: str, payload: dict | None = None, params: dict | None = None) -> dict | list | None:
        """POST with Bearer auth; retries on 401 with re-login. Never raises."""
        token = self._token or ""
        headers = {"Authorization": "Bearer " + token} if token else {}
        for attempt in range(3):
            try:
                resp = httpx.post(
                    self._base_url + path,
                    params=params or {},
                    json=payload or {},
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("api POST %s failed: %s", path, exc)
                if attempt < 2:
                    time.sleep(0.5)
                    continue
                return None
            if resp.status_code == 401 and attempt < 2 and self.login():
                headers = {"Authorization": "Bearer " + (self._token or "")}
                continue
            if resp.status_code not in (200, 201):
                logger.debug("api POST %s status %s", path, resp.status_code)
                return None
            try:
                return resp.json()
            except Exception:  # noqa: BLE001
                logger.debug("api POST %s returned non-JSON", path)
                return None
        return None

    # -- generic download (binary/text payloads to disk) --------------------
    def download(self, path: str, dest: Path) -> Path | None:
        """GET a payload and write it to ``dest``. Never raises; returns dest or None."""
        token = self._token or ""
        headers = {"Authorization": "Bearer " + token} if token else {}
        for attempt in range(3):
            try:
                resp = httpx.get(self._base_url + path, headers=headers, timeout=REQUEST_TIMEOUT + 2.0)
            except Exception as exc:  # noqa: BLE001
                logger.debug("api download %s failed: %s", path, exc)
                if attempt < 2:
                    time.sleep(0.5)
                    continue
                return None
            if resp.status_code == 401 and attempt < 2 and self.login():
                headers = {"Authorization": "Bearer " + (self._token or "")}
                continue
            if resp.status_code != 200:
                logger.debug("api download %s status %s", path, resp.status_code)
                return None
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(resp.content)
                return dest
            except Exception as exc:  # noqa: BLE001
                logger.warning("api download %s write failed: %s", path, exc)
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

    # -- reports -----------------------------------------------------------
    def fetch_reports(self, limit: int = 20, offset: int = 0, status: str | None = None) -> list[dict]:
        params: dict = {"limit": limit, "offset": offset, "sort_by": "created_at", "sort_order": "desc"}
        if status:
            params["status"] = status
        data = self.get("/api/reports", params)
        if isinstance(data, dict):
            return data.get("items") or []
        return []

    def fetch_report(self, report_id: int) -> dict | None:
        data = self.get(f"/api/reports/{report_id}")
        return data if isinstance(data, dict) else None

    def create_report(self, finding_ids: list[int]) -> dict | None:
        data = self.post("/api/reports", {"finding_ids": finding_ids})
        return data if isinstance(data, dict) else None

    def export_report(self, report_id: int, fmt: str = "markdown") -> Path | None:
        """Export a report to the exports dir. Returns the file path or None."""
        dest = self._exports_dir() / f"report_{report_id}.{fmt}"
        return self.download(f"/api/reports/{report_id}/export?format={fmt}", dest)

    def fetch_report_versions(self, report_id: int) -> list[dict]:
        data = self.get(f"/api/reports/{report_id}/versions")
        if isinstance(data, list):
            return data
        return []

    def submit_report(self, report_id: int, platform: str) -> dict | None:
        data = self.post(f"/api/reports/{report_id}/submit", {"platform": platform})
        return data if isinstance(data, dict) else None

    # -- findings ----------------------------------------------------------
    def fetch_finding(self, finding_id: int) -> dict | None:
        data = self.get(f"/api/findings/{finding_id}")
        return data if isinstance(data, dict) else None

    def generate_report_from_finding(self, finding_id: int) -> dict | None:
        data = self.post(f"/api/findings/{finding_id}/generate-report")
        return data if isinstance(data, dict) else None

    def export_finding(self, finding_id: int, fmt: str = "markdown") -> Path | None:
        """Export a finding (markdown or pdf) to the exports dir. Returns path or None."""
        if fmt not in ("markdown", "pdf"):
            return None
        ext = "md" if fmt == "markdown" else "pdf"
        dest = self._exports_dir() / f"finding_{finding_id}.{ext}"
        return self.download(f"/api/findings/{finding_id}/export-{fmt}", dest)

    # -- operations --------------------------------------------------------
    def fetch_operations_timeline(self, limit: int = 50, hours: int = 72) -> list[dict]:
        data = self.get("/api/operations/timeline", {"limit": limit, "hours": hours})
        if isinstance(data, dict):
            return data.get("events") or []
        if isinstance(data, list):
            return data
        return []

    def fetch_operations_metrics(self) -> dict | None:
        data = self.get("/api/operations/metrics")
        return data if isinstance(data, dict) else None

    def fetch_operations_tasks(self) -> list[dict]:
        data = self.get("/api/operations/tasks")
        if isinstance(data, dict):
            return data.get("items") or []
        if isinstance(data, list):
            return data
        return []

    # -- intelligence ------------------------------------------------------
    def fetch_intelligence_state(self) -> dict | None:
        data = self.get("/api/intelligence/state")
        return data if isinstance(data, dict) else None

    def fetch_intelligence_analyze(self) -> dict | None:
        data = self.get("/api/intelligence/analyze")
        return data if isinstance(data, dict) else None

    def refresh_intelligence(self) -> dict | None:
        data = self.post("/api/intelligence/refresh")
        return data if isinstance(data, dict) else None

    # -- payment compat ------------------------------------------------------
    def fetch_payment_network(self) -> dict | None:
        data = self.get("/api/payment-compat")
        return data if isinstance(data, dict) else None

    def fetch_payment_network_grouped(self) -> dict | None:
        data = self.get("/api/payment-compat/network")
        return data if isinstance(data, dict) else None

    def fetch_payment_account(self, account_id: str) -> dict | None:
        data = self.get(f"/api/payment-compat/account/{account_id}")
        return data if isinstance(data, dict) else None

    def payment_evaluate(
        self,
        method: str = "crypto",
        currency: str = "USDC",
        region: str = "global",
        amount: float = 0.0,
        required_documentation: str = "",
        platform: str = "",
    ) -> dict | None:
        payload = {
            "method": method,
            "currency": currency,
            "region": region,
            "amount": amount,
            "required_documentation": required_documentation,
            "platform": platform,
        }
        data = self.post("/api/payment-compat/evaluate", payload)
        return data if isinstance(data, dict) else None

    def payment_evaluate_chain(
        self,
        method: str = "crypto",
        currency: str = "USDC",
        region: str = "global",
        amount: float = 0.0,
        required_documentation: str = "",
        platform: str = "",
        final_currency: str = "ARS",
    ) -> dict | None:
        payload = {
            "method": method,
            "currency": currency,
            "region": region,
            "amount": amount,
            "required_documentation": required_documentation,
            "platform": platform,
            "final_currency": final_currency,
        }
        data = self.post("/api/payment-compat/evaluate/chain", payload)
        return data if isinstance(data, dict) else None

    # -- knowledge bridge ------------------------------------------------------
    def fetch_knowledge_status(self) -> dict | None:
        data = self.get("/api/knowledge")
        return data if isinstance(data, dict) else None

    def knowledge_connect(self, path: str) -> dict | None:
        data = self.post("/api/knowledge/connect", {"path": path})
        return data if isinstance(data, dict) else None

    def knowledge_disconnect(self) -> dict | None:
        data = self.post("/api/knowledge/disconnect")
        return data if isinstance(data, dict) else None

    def knowledge_scan(self, full: bool = False) -> dict | None:
        data = self.post("/api/knowledge/scan", {"full": full})
        return data if isinstance(data, dict) else None

    def knowledge_search(self, q: str, limit: int = 10) -> dict | None:
        data = self.get("/api/knowledge/search", {"q": q, "limit": limit})
        return data if isinstance(data, dict) else None

    def knowledge_note(self, path: str) -> dict | None:
        data = self.get("/api/knowledge/note", {"path": path})
        return data if isinstance(data, dict) else None

    def knowledge_context(self, q: str, max_notes: int = 5) -> dict | None:
        data = self.get("/api/knowledge/context", {"q": q, "max_notes": max_notes})
        return data if isinstance(data, dict) else None

    def knowledge_health(self) -> dict | None:
        data = self.get("/api/knowledge/health")
        return data if isinstance(data, dict) else None

    def knowledge_history(self, limit: int = 7) -> dict | None:
        data = self.get("/api/knowledge/history", {"limit": limit})
        return data if isinstance(data, dict) else None

    def knowledge_sync(self) -> dict | None:
        data = self.post("/api/knowledge/sync")
        return data if isinstance(data, dict) else None

    # -- voice ------------------------------------------------------
    def fetch_voice_status(self) -> dict | None:
        data = self.get("/voice/status")
        return data if isinstance(data, dict) else None

    def voice_synthesize(self, text: str) -> bytes | None:
        payload = {"text": text}
        data = self.post("/voice/tts", payload)
        if isinstance(data, bytes):
            return data
        if isinstance(data, dict) and "detail" in data.get("detail", ""):
            return None
        return None

    def voice_get_config(self) -> dict | None:
        data = self.get("/voice/config")
        return data if isinstance(data, dict) else None

    def voice_update_config(self, update: dict[str, Any]) -> dict | None:
        data = self.post("/voice/config", update)
        return data if isinstance(data, dict) else None

    def voice_process_command(self, text: str) -> dict | None:
        data = self.post("/voice/command", {"text": text})
        return data if isinstance(data, dict) else None

    def voice_get_replies(self, since: int = 0) -> dict | None:
        data = self.get("/voice/assistant/replies", {"since": since})
        return data if isinstance(data, dict) else None

    # -- system / pipeline / scans / hunt ----------------------------------
    def fetch_system_status(self) -> dict | None:
        data = self.get("/api/system/status")
        return data if isinstance(data, dict) else None

    def fetch_health(self) -> dict | None:
        data = self.get("/api/health")
        return data if isinstance(data, dict) else None

    def fetch_pipeline(self) -> dict | None:
        data = self.get("/api/pipeline")
        return data if isinstance(data, dict) else None

    def fetch_pipeline_stages(self) -> list[dict]:
        data = self.get("/api/pipeline/stages")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("stages") or data.get("items") or []
        return []

    def fetch_scan_runs(self, limit: int = 20) -> list[dict]:
        data = self.get("/api/scans/runs", {"limit": limit})
        if isinstance(data, dict):
            return data.get("items") or []
        if isinstance(data, list):
            return data
        return []

    def fetch_hunt_status(self) -> dict | None:
        data = self.get("/api/hunt/status")
        return data if isinstance(data, dict) else None

    def start_hunt(self) -> dict | None:
        data = self.post("/api/hunt/start")
        return data if isinstance(data, dict) else None

    def stop_hunt(self) -> dict | None:
        data = self.post("/api/hunt/stop")
        return data if isinstance(data, dict) else None

    # -- helpers -----------------------------------------------------------
    def _exports_dir(self) -> Path:
        path = self._data_dir / "exports"
        path.mkdir(parents=True, exist_ok=True)
        return path
