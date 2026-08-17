"""Freebuff provider — GitHub autonomous coding agent.

Freebuff is a free autonomous coding agent that works with GitHub repositories.
It's ideal for mobile/cloud scenarios since it doesn't require local servers.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from core.copilot.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger("orion.copilot.providers.freebuff")


class FreebuffProvider(BaseProvider):
    """Freebuff provider — GitHub autonomous coding agent.

    Free agent that works with GitHub repositories without requiring local servers.
    Ideal for mobile/cloud scenarios.
    """

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(
            config or ProviderConfig(
                name="freebuff",
                priority=12,  # Between Devin (15) and OpenCode (10)
                models=["freebuff"],
                timeout_s=180,
                extra={"config_path": os.path.expanduser("~/.orion/freebuff_config.yaml")},
            )
        )
        self._config_path = self._config.extra.get("config_path")
        self._detection = None
        self._freebuff_config = None

    async def check(self) -> bool:
        """Check if Freebuff is installed and configured."""
        try:
            # Try to import freebuff detection
            try:
                from core.ai_providers.freebuff import detect_freebuff, load_config
            except ImportError:
                from cores.ai_providers.freebuff import detect_freebuff, load_config

            self._detection = detect_freebuff()
            self._freebuff_config = load_config(self._config_path)

            is_installed = self._detection.get("installed", False)
            is_enabled = self._freebuff_config.enabled if self._freebuff_config else False

            return is_installed and is_enabled
        except Exception as exc:
            logger.warning("Freebuff check failed: %s", exc)
            return False

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        """Chat with Freebuff - routes coding tasks to the agent."""
        return await self.execute_task(messages)

    async def execute_task(self, messages: list[dict[str, str]], project_dir: str | None = None) -> ProviderResponse:
        """Execute a coding task via Freebuff."""
        if not messages:
            return ProviderResponse(content="", provider="freebuff", error="no messages")

        # Extract task from messages
        task_content = ""
        for msg in messages:
            if msg.get("role") == "user":
                task_content = msg.get("content", "")
                break

        if not task_content:
            return ProviderResponse(content="", provider="freebuff", error="no task content")

        t0 = time.monotonic()
        try:
            # Import Freebuff modules
            try:
                from core.ai_providers.freebuff import FreebuffTaskRequest, route_task
            except ImportError:
                from cores.ai_providers.freebuff import FreebuffTaskRequest, route_task

            # Use project_dir from kwargs or default to Rastro
            workspace = project_dir or os.path.expanduser("~/projects/Rastro")

            request = FreebuffTaskRequest(
                task=task_content,
                workspace=workspace,
                task_type="code",
                complexity="LOW",
                risk_level="LOW",
                files_affected=1,
                requires_review=True,
                network_allowed=False,
                secrets_present=False,
            )

            result = route_task(request)
            dur = (time.monotonic() - t0) * 1000

            if result.success:
                return ProviderResponse(
                    content=f"Freebuff ejecutó la tarea exitosamente. Archivos modificados: {result.files_changed}. Duración: {result.duration_ms}ms.",
                    provider="freebuff",
                    model="freebuff",
                    duration_ms=dur,
                    extra={"files_changed": result.files_changed, "workspace": workspace},
                )
            else:
                return ProviderResponse(
                    content=f"Freebuff falló: {result.stderr}",
                    provider="freebuff",
                    model="freebuff",
                    error=str(result.stderr),
                    duration_ms=dur,
                )
        except Exception as exc:
            logger.warning("Freebuff execution failed: %s", exc)
            return ProviderResponse(
                content="",
                provider="freebuff",
                model="freebuff",
                error=str(exc),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    def get_config(self) -> dict[str, Any]:
        """Get Freebuff configuration info."""
        return {
            "provider": self.name,
            "available": self._detection.get("installed", False) if self._detection else False,
            "version": self._detection.get("version", "unknown") if self._detection else "unknown",
            "config_path": self._config_path,
            "enabled": self._freebuff_config.enabled if self._freebuff_config else False,
        }
