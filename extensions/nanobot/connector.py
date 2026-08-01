from __future__ import annotations

import importlib.util
import logging
import os
import subprocess
from pathlib import Path

from core.interfaces.connector import ConnectorHealth, IConnector

logger = logging.getLogger("ownex.nanobot.connector")

_NANOBOT_AVAILABLE = importlib.util.find_spec("nanobot") is not None


class NanobotConnector(IConnector):
    """Connector to Nanobot agent frontend.

    Nanobot provides the human-facing chat interface for OWNEX,
    supporting multi-model conversations, file uploads, MCP tools,
    and agent switching.
    """

    connector_id = "nanobot_frontend"
    app_id = "ownex"
    display_name = "Nanobot Agent UI"

    def __init__(self) -> None:
        self._connected = False
        self._process: subprocess.Popen | None = None
        self._port: int = 3000

    async def connect(self) -> bool:
        if not _NANOBOT_AVAILABLE:
            logger.warning("nanobot not installed")
            return False
        self._port = int(os.environ.get("NANOBOT_PORT", "3000"))
        self._connected = True
        return True

    async def disconnect(self) -> None:
        if self._process:
            self._process.terminate()
            self._process = None
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            connected=self._connected,
            error=None if self._connected else "not initialized",
        )

    def get_config_fields(self) -> list[dict]:
        return [
            {
                "key": "nanobot_port",
                "label": "Nanobot Port",
                "type": "number",
                "default": "3000",
            },
        ]

    async def start_server(self) -> dict:
        """Start the Nanobot server process."""
        if self._process:
            return {"status": "already_running"}
        try:
            config_dir = Path.home() / ".ownex" / "nanobot"
            config_dir.mkdir(parents=True, exist_ok=True)

            self._process = subprocess.Popen(
                ["nanobot", "serve", "--port", str(self._port), "--dir", str(config_dir)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return {"status": "started", "port": self._port}
        except Exception as exc:
            logger.error("Nanobot start failed: %s", exc)
            return {"error": str(exc)}

    async def stop_server(self) -> dict:
        """Stop the Nanobot server."""
        if not self._process:
            return {"status": "not_running"}
        self._process.terminate()
        self._process = None
        return {"status": "stopped"}

    async def send_message(self, agent: str, message: str) -> dict:
        """Send a message to a specific agent via Nanobot."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"http://localhost:{self._port}/api/chat",
                    json={"agent": agent, "message": message},
                )
                return resp.json() if resp.status_code < 300 else {"error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            logger.error("Nanobot send_message failed: %s", exc)
            return {"error": str(exc)}

    async def list_agents(self) -> list[str]:
        """List available agents in Nanobot."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"http://localhost:{self._port}/api/agents")
                return resp.json() if resp.status_code < 300 else []
        except Exception as exc:
            logger.error("Nanobot list_agents failed: %s", exc)
            return []


async def on_chat_request(event: object) -> None:
    if not _NANOBOT_AVAILABLE:
        return
    connector = NanobotConnector()
    await connector.connect()
    agent = getattr(event, "agent", "default")
    message = getattr(event, "data", "") or getattr(event, "message", "")
    if message:
        result = await connector.send_message(agent, message)
        if result and hasattr(event, "set_result"):
            event.set_result(result)


async def on_agent_switch(event: object) -> None:
    if not _NANOBOT_AVAILABLE:
        return
    connector = NanobotConnector()
    await connector.connect()
    agent = getattr(event, "agent", "")
    if agent:
        result = await connector.list_agents()
        if result and hasattr(event, "set_result"):
            event.set_result({"agents": result, "selected": agent})
