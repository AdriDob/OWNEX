from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from typing import Any

from core.copilot.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger("orion.copilot.providers.fcc")


class FCCProvider(BaseProvider):
    """OpenRouter free models provider — :free tagged models only."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(
            config
            or ProviderConfig(
                name="fcc",
                priority=20,
                models=[
                    "nvidia/nemotron-3-super-120b-a12b:free",
                    "nvidia/nemotron-3-ultra-550b-a55b:free",
                    "nvidia/nemotron-3-nano-30b-a3b:free",
                    "nvidia/nemotron-nano-12b-v2-vl:free",
                    "google/gemma-4-31b-it:free",
                    "openai/gpt-oss-20b:free",
                    "cohere/north-mini-code:free",
                    "liquid/lfm-2.5-2.6b:free",
                ],
                timeout_s=60,
            )
        )
        self._base_url = (
            self._config.extra.get("base_url", os.getenv("ANTHROPIC_BASE_URL", "")) or "https://openrouter.ai/api/v1"
        )
        self._api_key = self._config.extra.get(
            "api_key",
            os.getenv(
                "ANTHROPIC_API_KEY",
                os.getenv(
                    "OPENROUTER_API_KEY", "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"
                ),
            ),
        )
        self._default_model = self._config.models[0]

    async def check(self) -> bool:
        """Quick health check - just verify API key is present."""
        return bool(self._api_key)

    async def list_models(self) -> list[str]:
        """List available free models from OpenRouter."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                if r.status_code == 200:
                    data = r.json()
                    models = []
                    for m in data.get("data", []):
                        # Filter for free models
                        pricing = m.get("pricing", {})
                        if pricing:
                            prompt_price = float(pricing.get("prompt", "0"))
                            completion_price = float(pricing.get("completion", "0"))
                            # Consider models with price <= 0.001 as "free"
                            if prompt_price <= 0.001 and completion_price <= 0.001:
                                models.append(m.get("id", ""))
                    return models[:50]  # Limit to first 50 free models
        except Exception as e:
            logger.warning("Failed to list FCC models: %s", e)
        return self._config.models

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        import time

        import httpx

        model = kwargs.get("model", self._default_model)
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._config.timeout_s) as client:
                r = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/adri/Rastro",
                        "X-Title": "OWNEX",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": kwargs.get("max_tokens", 4096),
                        "temperature": kwargs.get("temperature", 0.7),
                    },
                )
                if r.status_code != 200:
                    logger.warning("FCC API error: %s - %s", r.status_code, r.text)
                    return ProviderResponse(
                        content="",
                        provider="fcc",
                        model=model,
                        error=f"API error {r.status_code}",
                        duration_ms=(time.monotonic() - t0) * 1000,
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
