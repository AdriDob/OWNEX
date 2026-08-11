from __future__ import annotations

import logging
import subprocess
import time
from typing import Any

from core.copilot.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger("orion.copilot.providers.opencode")


class OpenCodeProvider(BaseProvider):
    """OpenCode provider — executes code modifications via `opencode run`.

    Only for TASK execution (write code, refactor, implement). Not a chat provider.
    Routes queries with require_code=True to this provider via the Router.
    """

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(
            config
            or ProviderConfig(name="opencode", priority=10, models=["opencode/deepseek-v4-flash-free"], timeout_s=180)
        )
        self._binary = self._config.extra.get("binary", "opencode")
        self._model = (
            self._config.extra.get("model", self._config.models[0])
            if self._config.models
            else "opencode/deepseek-v4-flash-free"
        )

    async def check(self) -> bool:
        try:
            result = subprocess.run([self._binary, "--version"], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        return await self.execute_task(messages)

    async def execute_task(self, messages: list[dict[str, str]], project_dir: str | None = None) -> ProviderResponse:
        """Execute a code task via OpenCode CLI. Messages describe the task."""
        if not messages:
            return ProviderResponse(content="", provider="opencode", error="no messages")

        task_text = messages[-1].get("content", "") if isinstance(messages[-1], dict) else str(messages[-1])
        t0 = time.monotonic()
        try:
            cmd = [self._binary, "run", task_text]
            if self._model:
                cmd.extend(["--model", self._model])

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._config.timeout_s, cwd=project_dir
            )
            dur = (time.monotonic() - t0) * 1000

            if result.returncode == 0:
                return ProviderResponse(
                    content=result.stdout or "(no output)", provider="opencode", model=self._model, duration_ms=dur
                )
            else:
                return ProviderResponse(
                    content=result.stderr or result.stdout,
                    provider="opencode",
                    model=self._model,
                    error=f"exit code {result.returncode}",
                    duration_ms=dur,
                )
        except subprocess.TimeoutExpired:
            return ProviderResponse(
                content="",
                provider="opencode",
                model=self._model,
                error="timeout",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        except FileNotFoundError:
            return ProviderResponse(
                content="", provider="opencode", model=self._model, error="opencode binary not found"
            )
        except Exception as exc:
            return ProviderResponse(
                content="",
                provider="opencode",
                model=self._model,
                error=str(exc),
                duration_ms=(time.monotonic() - t0) * 1000,
            )
