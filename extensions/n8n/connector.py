from __future__ import annotations

import logging
import os

import httpx

from core.interfaces.connector import ConnectorHealth, IConnector

logger = logging.getLogger("ownex.n8n.connector")


class N8nConnector(IConnector):
    """Connector to n8n workflow automation.

    Bridges OWNEX EventBus events to n8n webhooks, enabling visual
    workflow automation for sensor triggers, agent actions, and
    notification pipelines.
    """

    connector_id = "n8n_bridge"
    app_id = "ownex"
    display_name = "n8n Workflow Bridge"

    def __init__(self) -> None:
        self._connected = False
        self._base_url: str = ""
        self._api_key: str = ""

    async def connect(self) -> bool:
        self._base_url = os.environ.get("N8N_BASE_URL", "http://localhost:5678")
        self._api_key = os.environ.get("N8N_API_KEY", "")
        if not self._api_key:
            logger.warning("N8N_API_KEY not set — webhook-only mode")
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> ConnectorHealth:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._base_url}/health")
                return ConnectorHealth(
                    connected=resp.status_code == 200,
                    error=None if resp.status_code == 200 else f"HTTP {resp.status_code}",
                )
        except Exception as exc:
            return ConnectorHealth(
                connected=False,
                error=str(exc),
            )

    def get_config_fields(self) -> list[dict]:
        return [
            {
                "key": "n8n_base_url",
                "label": "n8n Base URL",
                "type": "text",
                "default": "http://localhost:5678",
            },
            {
                "key": "n8n_api_key",
                "label": "n8n API Key",
                "type": "text",
            },
        ]

    async def trigger_webhook(self, webhook_id: str, payload: dict) -> dict:
        """Trigger an n8n webhook workflow."""
        url = f"{self._base_url}/webhook/{webhook_id}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload)
                return {
                    "status": resp.status_code,
                    "data": resp.json() if resp.status_code < 300 else {},
                }
        except Exception as exc:
            logger.error("n8n webhook trigger failed: %s", exc)
            return {"error": str(exc)}

    async def create_webhook(self, name: str, path: str) -> dict:
        """Register a new webhook in n8n (requires API key)."""
        if not self._api_key:
            return {"error": "API key required"}
        url = f"{self._base_url}/api/v1/workflows"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url,
                    headers={"X-N8N-API-KEY": self._api_key},
                    json={"name": name, "nodes": [], "connections": {}},
                )
                return {"status": resp.status_code, "data": resp.json() if resp.status_code < 300 else {}}
        except Exception as exc:
            logger.error("n8n create workflow failed: %s", exc)
            return {"error": str(exc)}

    async def list_workflows(self) -> list[dict]:
        """List all n8n workflows."""
        if not self._api_key:
            return []
        url = f"{self._base_url}/api/v1/workflows"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers={"X-N8N-API-KEY": self._api_key})
                return resp.json().get("data", []) if resp.status_code < 300 else []
        except Exception as exc:
            logger.error("n8n list workflows failed: %s", exc)
            return []


async def on_eventbus_event(event: object) -> None:
    """Bridge EventBus events to n8n webhooks."""
    connector = N8nConnector()
    await connector.connect()
    webhook_id = getattr(event, "webhook_id", "ownex-eventbus")
    payload = {
        "event_type": type(event).__name__,
        "data": getattr(event, "data", str(event)),
        "source": getattr(event, "source", "ownex"),
    }
    await connector.trigger_webhook(webhook_id, payload)


async def on_workflow_request(event: object) -> None:
    """Execute an n8n workflow from an OWNEX event."""
    connector = N8nConnector()
    await connector.connect()
    webhook_id = getattr(event, "webhook_id", "")
    payload = getattr(event, "payload", {})
    if webhook_id:
        result = await connector.trigger_webhook(webhook_id, payload)
        if result and hasattr(event, "set_result"):
            event.set_result(result)
