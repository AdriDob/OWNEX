"""OmniRoute provider — OpenAI-compatible HTTP provider via local Docker (:20128).

Connects to the OmniRoute AI Gateway running as a Docker container.
Uses specific model IDs like oc/deepseek-v4-flash-free (tested working).
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

from core.copilot.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger("orion.copilot.providers.omniroute")

_OMNIROUTE_MODELS = [
    "oc/deepseek-v4-flash-free",
    "auto/best-coding",
    "auto/best-fast",
    "auto/best-reasoning",
]


class OmniRouteProvider(BaseProvider):
    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(
            config
            or ProviderConfig(
                name="omniroute",
                priority=15,
                models=_OMNIROUTE_MODELS,
                timeout_s=120,
            )
        )
        self._base_url = self._config.extra.get(
            "base_url", os.getenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")
        )
        self._api_key = self._config.extra.get("api_key", os.getenv("OMNIROUTE_API_KEY", "omniroute"))
        self._default_model = self._config.models[0]

    async def check(self) -> bool:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self._base_url}/models")
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
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "max_tokens": kwargs.get("max_tokens", 4096),
                    },
                )
                data = r.json()
                dur = (time.monotonic() - t0) * 1000

                if "error" in data:
                    return ProviderResponse(
                        content="",
                        provider="omniroute",
                        model=model,
                        error=data["error"].get("message", str(data["error"])),
                        duration_ms=dur,
                    )

                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                usage = data.get("usage", {})
                return ProviderResponse(
                    content=content,
                    provider="omniroute",
                    model=data.get("model", model),
                    tokens_in=usage.get("prompt_tokens", 0),
                    tokens_out=usage.get("completion_tokens", 0),
                    duration_ms=dur,
                )
        except Exception as exc:
            logger.warning("OmniRoute chat failed: %s", exc)
            return ProviderResponse(
                content="",
                provider="omniroute",
                model=model,
                error=str(exc),
                duration_ms=(time.monotonic() - t0) * 1000,
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
                    if line.startswith("data: [DONE]"):
                        break
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line.removeprefix("data: "))
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            if content := delta.get("content"):
                                yield content
                            if reasoning := delta.get("reasoning_content"):
                                yield reasoning
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue
        except Exception as exc:
            logger.warning("OmniRoute stream failed: %s", exc)
