from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from typing import Any

from core.copilot.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger("orion.copilot.providers.fcc")


class FCCProvider(BaseProvider):
    """FCC proxy — Claude models via OpenRouter proxy (free tier)."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(config or ProviderConfig(name="fcc", priority=20, models=["claude-sonnet-4-5"], timeout_s=120))
        self._base_url = (
            self._config.extra.get("base_url", os.getenv("ANTHROPIC_BASE_URL", "")) or "https://openrouter.ai/api/v1"
        )
        self._api_key = self._config.extra.get(
            "api_key", os.getenv("ANTHROPIC_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
        )
        self._default_model = self._config.models[0]

    async def check(self) -> bool:
        return bool(self._api_key)

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        import time

        import httpx

        model = kwargs.get("model", self._default_model)
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._config.timeout_s) as client:
                r = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages, "max_tokens": kwargs.get("max_tokens", 4096)},
                )
                data = r.json()
                dur = (time.monotonic() - t0) * 1000
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                usage = data.get("usage", {})
                return ProviderResponse(
                    content=content,
                    provider="fcc",
                    model=model,
                    tokens_in=usage.get("prompt_tokens", 0),
                    tokens_out=usage.get("completion_tokens", 0),
                    duration_ms=dur,
                )
        except Exception as exc:
            logger.warning("FCC chat failed: %s", exc)
            return ProviderResponse(
                content="", provider="fcc", model=model, error=str(exc), duration_ms=(time.monotonic() - t0) * 1000
            )

    async def chat_stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        import httpx

        model = kwargs.get("model", self._default_model)
        try:
            async with (
                httpx.AsyncClient(timeout=self._config.timeout_s) as client,
                client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": True,
                        "max_tokens": kwargs.get("max_tokens", 4096),
                    },
                ) as r,
            ):
                async for line in r.aiter_lines():
                    if not line.strip() or line.startswith(":"):
                        continue
                    import json

                    try:
                        data = json.loads(line.removeprefix("data: "))
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        if content := delta.get("content"):
                            yield content
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
        except Exception as exc:
            logger.warning("FCC stream failed: %s", exc)
