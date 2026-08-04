from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from core.copilot.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger("orion.copilot.providers.nvidia")


class NvidiaProvider(BaseProvider):
    """NVIDIA NIM Provider."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(
            config
            or ProviderConfig(
                name="nvidia",
                priority=30,
                models=["nv-ai-foundation-541280:mistral-8x7b-instruct-v0.2"],
                timeout_s=120,
            )
        )
        self._base_url = (
            self._config.extra.get("base_url", os.getenv("NVIDIA_BASE_URL", ""))
            or "https://integrate.api.nvidia.com/v1"
        )
        self._api_key = self._config.extra.get("api_key", os.getenv("NVIDIA_API_KEY", ""))
        self._default_model = self._config.models[0]
        # Supported models list for routing
        self._supported_models = [
            "nv-ai-foundation-541280:mistral-8x7b-instruct-v0.2",
            "nv-ai-foundation-541280:llama-3.1-70b-instruct",
            "nv-ai-foundation-541280:nemotron-3-ultra",
            "nvidia/nemotron-3-ultra",
            "meta/llama-3.1-70b-instruct",
        ]

    async def check(self) -> bool:
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                return r.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        if not self._api_key:
            return self._supported_models
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                if r.status_code == 200:
                    data = r.json()
                    models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                    return models[:50]
        except Exception as e:
            logger.warning("Failed to list NVIDIA models: %s", e)
        return self._supported_models

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        import time

        model = kwargs.get("model", self._default_model)
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._config.timeout_s) as client:
                r = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                    },
                    json={"model": model, "messages": messages, "max_tokens": kwargs.get("max_tokens", 4096)},
                )
                if r.status_code != 200:
                    logger.error(f"NVIDIA chat failed with HTTP error: {r.status_code} - {r.text}")
                    return ProviderResponse(
                        content="",
                        provider="nvidia",
                        model=model,
                        error=f"HTTP {r.status_code}: {r.text}",
                        duration_ms=(time.monotonic() - t0) * 1000,
                    )
                data = r.json()
                dur = (time.monotonic() - t0) * 1000
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                usage = data.get("usage", {})
                return ProviderResponse(
                    content=content,
                    provider="nvidia",
                    model=model,
                    tokens_in=usage.get("prompt_tokens", 0),
                    tokens_out=usage.get("completion_tokens", 0),
                    duration_ms=dur,
                )
        except httpx.HTTPStatusError as e:
            logger.error(f"NVIDIA chat failed with HTTP error: {e.response.status_code} - {e.response.text}")
            return ProviderResponse(
                content="", provider="nvidia", model=model, error=str(e), duration_ms=(time.monotonic() - t0) * 1000
            )
        except Exception as exc:
            logger.warning("NVIDIA chat failed: %s", exc)
            return ProviderResponse(
                content="", provider="nvidia", model=model, error=str(exc), duration_ms=(time.monotonic() - t0) * 1000
            )

    async def chat_stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        model = kwargs.get("model", self._default_model)
        try:
            async with (
                httpx.AsyncClient(timeout=self._config.timeout_s) as client,
                client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": True,
                        "max_tokens": kwargs.get("max_tokens", 4096),
                    },
                ) as r,
            ):
                r.raise_for_status()  # Raise an exception for HTTP errors
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
        except httpx.HTTPStatusError as e:
            logger.error(f"NVIDIA stream failed with HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as exc:
            logger.warning("NVIDIA stream failed: %s", exc)
