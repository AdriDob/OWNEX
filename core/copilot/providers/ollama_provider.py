from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from core.copilot.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger("orion.copilot.providers.ollama")


class OllamaProvider(BaseProvider):
    """Local Ollama provider — qwen3-coder, hermes-orion, etc."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(
            config or ProviderConfig(name="ollama", priority=30, models=["qwen3-coder:8b", "hermes-orion"])
        )
        self._base_url = self._config.extra.get("base_url", "http://localhost:11434")
        self._default_model = self._config.models[0] if self._config.models else "qwen3-coder:8b"

    async def check(self) -> bool:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self._base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        import time

        import httpx

        model = kwargs.get("model", self._default_model)
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._config.timeout_s) as client:
                r = await client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {"num_predict": kwargs.get("max_tokens", 2048)},
                    },
                )
                data = r.json()
                dur = (time.monotonic() - t0) * 1000
                return ProviderResponse(
                    content=data.get("message", {}).get("content", ""), provider="ollama", model=model, duration_ms=dur
                )
        except Exception as exc:
            logger.warning("Ollama chat failed: %s", exc)
            return ProviderResponse(
                content="", provider="ollama", model=model, error=str(exc), duration_ms=(time.monotonic() - t0) * 1000
            )

    async def chat_stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        import httpx

        model = kwargs.get("model", self._default_model)
        try:
            async with (
                httpx.AsyncClient(timeout=self._config.timeout_s) as client,
                client.stream(
                    "POST", f"{self._base_url}/api/chat", json={"model": model, "messages": messages, "stream": True}
                ) as r,
            ):
                async for line in r.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        if content := chunk.get("message", {}).get("content"):
                            yield content
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.warning("Ollama stream failed: %s", exc)
