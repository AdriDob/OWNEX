"""Taskmarket write-actions client — gated behind explicit owner authorization.

Endpoints verified against https://api.taskmarket.dev/openapi.json
(2026-11-21). NOTHING here runs without:
  1. ``authorized=True`` — caller asserts human approval happened
     (FINAL_HUMAN_ACTIONS B6 / record_approval evidence).
  2. Credentials — agent identity token / wallet signature supplied by
     the owner; this module never registers, claims wallets, or signs.

Discovery stays read-only in ``agent_markets.py``; this module only
wraps the write surface so it exists, is testable, and cannot fire
accidentally.
"""

from __future__ import annotations

from typing import Any

import httpx

BASE = "https://api.taskmarket.dev"


class AuthorizationRequiredError(RuntimeError):
    """Raised when a write action is attempted without owner authorization."""


class TaskmarketActions:
    """Gated write client for the Taskmarket agent API.

    ``credentials`` is a dict like ``{"identity_token": "..."}`` or
    ``{"api_key": "..."}`` — supplied by the owner after registration.
    The client never creates credentials itself.
    """

    def __init__(self, credentials: dict[str, str] | None = None, authorized: bool = False):
        self._creds = credentials or {}
        self._authorized = authorized
        self._client = httpx.Client(base_url=BASE, timeout=30.0)

    # -- gates ---------------------------------------------------------

    def _require_authorized(self, action: str) -> None:
        if not self._authorized:
            raise AuthorizationRequiredError(f"{action} requires owner authorization (FINAL_HUMAN_ACTIONS B6)")
        if not self._creds:
            raise AuthorizationRequiredError(f"{action} requires agent credentials — register first (B6)")

    def _headers(self) -> dict[str, str]:
        if "identity_token" in self._creds:
            return {"Authorization": f"Bearer {self._creds['identity_token']}"}
        if "api_key" in self._creds:
            return {"X-API-Key": self._creds["api_key"]}
        return {}

    # -- verified endpoints (openapi.json, 2026-11-21) ------------------

    def submit_pitch(self, task_id: str, pitch_text: str) -> dict[str, Any]:
        """POST /tasks/{taskId}/pitches — 'Submit a pitch for a task'."""
        self._require_authorized("submit_pitch")
        r = self._client.post(
            f"/tasks/{task_id}/pitches",
            json={"pitch": pitch_text},
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def submit_work(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /tasks/{taskId}/submissions — 'Submit work for a task'.

        ``payload`` follows the spec's submission schema (artifact keys
        from request-upload-url flow, or inline content).
        """
        self._require_authorized("submit_work")
        r = self._client.post(
            f"/tasks/{task_id}/submissions",
            json=payload,
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def request_upload_url(self, task_id: str, filename: str, content_type: str = "text/markdown") -> dict[str, Any]:
        """POST /tasks/{taskId}/submissions/request-upload-url — presigned S3 PUT."""
        self._require_authorized("request_upload_url")
        r = self._client.post(
            f"/tasks/{task_id}/submissions/request-upload-url",
            json={"filename": filename, "contentType": content_type},
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    # -- identity (human-driven; client only wraps the call) -----------

    def register_identity(self, registration_payload: dict[str, Any]) -> dict[str, Any]:
        """POST /identity/register — agent identity creation.

        Requires wallet signature material from the owner; this method
        only transports it. Authorization is implied by possessing valid
        signing credentials, but we still require the flag for audit.
        """
        self._require_authorized("register_identity")
        r = self._client.post("/identity/register", json=registration_payload, headers=self._headers())
        r.raise_for_status()
        return r.json()

    # -- read helpers (no auth needed beyond public API) ---------------

    def list_pitches(self, task_id: str) -> dict[str, Any]:
        """GET /tasks/{taskId}/pitches — public pitch listing."""
        r = self._client.get(f"/tasks/{task_id}/pitches")
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()
