from __future__ import annotations

import logging
import os

import httpx

from core.interfaces.connector import ConnectorHealth, IConnector

logger = logging.getLogger("ownex.kestra.connector")


class KestraConnector(IConnector):
    """Connector to Kestra orchestration platform.

    Bridges OWNEX EventBus events to Kestra flow executions,
    enabling production-grade scheduling, retries, and error handling
    for autonomous workflows.
    """

    connector_id = "kestra_orchestrator"
    app_id = "ownex"
    display_name = "Kestra Orchestration"

    def __init__(self) -> None:
        self._connected = False
        self._base_url: str = ""

    async def connect(self) -> bool:
        self._base_url = os.environ.get("KESTRA_BASE_URL", "http://localhost:8080")
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> ConnectorHealth:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._base_url}/api/v1/health")
                return ConnectorHealth(
                    connected=resp.status_code == 200,
                    error=None if resp.status_code == 200 else f"HTTP {resp.status_code}",
                )
        except Exception as exc:
            return ConnectorHealth(connected=False, error=str(exc))

    def get_config_fields(self) -> list[dict]:
        return [
            {
                "key": "kestra_base_url",
                "label": "Kestra API Base URL",
                "type": "text",
                "default": "http://localhost:8080",
            },
        ]

    async def execute_flow(self, namespace: str, flow_id: str, inputs: dict | None = None) -> dict:
        """Execute a Kestra flow."""
        url = f"{self._base_url}/api/v1/executions/{namespace}/{flow_id}"
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, json=inputs or {})
                return {"status": resp.status_code, "data": resp.json() if resp.status_code < 300 else {}}
        except Exception as exc:
            logger.error("Kestra execute_flow failed: %s", exc)
            return {"error": str(exc)}

    async def create_flow(self, namespace: str, flow_yaml: str) -> dict:
        """Register a new flow from YAML definition."""
        url = f"{self._base_url}/api/v1/flows/{namespace}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, content=flow_yaml, headers={"Content-Type": "text/yaml"})
                return {"status": resp.status_code, "data": resp.json() if resp.status_code < 300 else {}}
        except Exception as exc:
            logger.error("Kestra create_flow failed: %s", exc)
            return {"error": str(exc)}

    async def list_executions(self, namespace: str = "", limit: int = 10) -> list[dict]:
        """List recent flow executions."""
        url = f"{self._base_url}/api/v1/executions"
        if namespace:
            url += f"?namespace={namespace}&limit={limit}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                return resp.json() if resp.status_code < 300 else []
        except Exception as exc:
            logger.error("Kestra list_executions failed: %s", exc)
            return []


async def on_flow_trigger(event: object) -> None:
    connector = KestraConnector()
    await connector.connect()
    namespace = getattr(event, "namespace", "ownex")
    flow_id = getattr(event, "flow_id", "")
    inputs = getattr(event, "inputs", None)
    if flow_id:
        result = await connector.execute_flow(namespace, flow_id, inputs)
        if result and hasattr(event, "set_result"):
            event.set_result(result)


async def on_schedule_event(event: object) -> None:
    connector = KestraConnector()
    await connector.connect()
    schedule = getattr(event, "schedule", "")
    flow_id = getattr(event, "flow_id", "ownex-daily")
    if schedule and hasattr(event, "set_result"):
        flow_yaml = f"""id: {flow_id}
namespace: ownex
tasks:
  - id: trigger
    type: io.kestra.plugin.core.flow.Subflow
    flowId: {flow_id}
revision: 1
triggers:
  - id: schedule
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "{schedule}"
"""
        result = await connector.create_flow("ownex", flow_yaml)
        event.set_result(result)
