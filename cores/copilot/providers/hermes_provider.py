from __future__ import annotations

import asyncio
import logging
import subprocess
import time
from collections.abc import AsyncIterator
from typing import Any

from core.copilot.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger("orion.copilot.providers.hermes")

HERMES_binary = "hermes"


class HermesProvider(BaseProvider):
    """Hermes Agent CLI provider — uses Hermes as the reasoning/chat model.

    Hermes routes to FCC proxy (Claude) or local Ollama depending on config.
    """

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(
            config
            or ProviderConfig(
                name="hermes",
                priority=15,
                models=["hermes", "claude-haiku-4-5"],
                timeout_s=120,
            )
        )
        self._hermes_binary = self._config.extra.get("binary", HERMES_binary)
        self._default_model = self._config.models[0] if self._config.models else "hermes"

    async def check(self) -> bool:
        try:
            result = subprocess.run(
                [self._hermes_binary, "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        model = kwargs.get("model", self._default_model)
        t0 = time.monotonic()
        last_msg = messages[-1].get("content", "") if messages else ""
        try:
            cmd = [self._hermes_binary, "chat", "-q", last_msg, "--quiet"]
            if model != "hermes":
                cmd.extend(["-m", model])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._config.timeout_s,
            )
            dur = (time.monotonic() - t0) * 1000

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if result.returncode == 0 and stdout and "session_id:" not in stdout:
                return ProviderResponse(
                    content=stdout,
                    provider="hermes",
                    model=model,
                    duration_ms=dur,
                )

            if result.returncode == 0:
                session_id = stdout.split("session_id:")[-1].strip().split("\n")[0] if stdout else ""
                return ProviderResponse(
                    content=f"[Hermes session {session_id}]",
                    provider="hermes",
                    model=model,
                    duration_ms=dur,
                )

            error_detail = stderr[:500] if stderr else f"exit code {result.returncode}"
            logger.warning("Hermes chat failed: %s", error_detail)
            return ProviderResponse(content="", provider="hermes", model=model, error=error_detail, duration_ms=dur)
        except subprocess.TimeoutExpired:
            logger.warning("Hermes chat timed out")
            return ProviderResponse(
                content="", provider="hermes", model=model, error="timeout", duration_ms=(time.monotonic() - t0) * 1000
            )
        except FileNotFoundError:
            return ProviderResponse(content="", provider="hermes", model=model, error="hermes binary not found")
        except Exception as exc:
            logger.warning("Hermes chat failed: %s", exc)
            return ProviderResponse(
                content="", provider="hermes", model=model, error=str(exc), duration_ms=(time.monotonic() - t0) * 1000
            )

    async def chat_stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        model = kwargs.get("model", self._default_model)
        last_msg = messages[-1].get("content", "") if messages else ""
        try:
            cmd = [self._hermes_binary, "chat", "-q", last_msg, "--quiet"]
            if model != "hermes":
                cmd.extend(["-m", model])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            if proc.stdout is None:
                return
            stdout_bytes = await asyncio.wait_for(proc.stdout.read(), timeout=self._config.timeout_s)
            text = stdout_bytes.decode().strip()
            if text and "session_id:" not in text:
                yield text
            elif text:
                yield "[Hermes session]"
        except asyncio.TimeoutError:
            logger.warning("Hermes stream timed out")
        except FileNotFoundError:
            logger.warning("Hermes binary not found")
        except Exception as exc:
            logger.warning("Hermes stream failed: %s", exc)
