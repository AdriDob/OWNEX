"""Custom Provider — User-defined custom AI provider."""

from __future__ import annotations

import logging
from typing import Any

from core.copilot.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger("core.ai.providers.custom")


class CustomProvider(BaseProvider):
    """Custom provider for user-defined AI endpoints."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(
            config
            or ProviderConfig(
                name="custom",
                priority=10,
                models=["custom"],
                timeout_s=120,
            )
        )
        self._base_url = self._config.extra.get("base_url", "http://localhost:11434/v1")
        self._api_key = self._config.extra.get("api_key", "")
        self._default_model = self._config.models[0]

    async def check(self) -> bool:
        """Check if custom provider is available and configured."""
        return bool(self._base_url)

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
                        "Authorization": f"Bearer {self._api_key}" if self._api_key else "",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": kwargs.get("max_tokens", 4096),
                        "temperature": kwargs.get("temperature", 0.7),
                    },
                )
                dur = (time.monotonic() - t0) * 1000

                if r.status_code != 200:
                    error_msg = f"Custom provider API error: {r.status_code} - {r.text}"
                    logger.warning(error_msg)
                    return ProviderResponse(
                        content="",
                        provider="custom",
                        model=model,
                        error=error_msg,
                        duration_ms=dur,
                    )

                data = r.json()
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                usage = data.get("usage", {})

                return ProviderResponse(
                    content=content,
                    provider="custom",
                    model=model,
                    tokens_in=usage.get("prompt_tokens", 0),
                    tokens_out=usage.get("completion_tokens", 0),
                    duration_ms=dur,
                )

        except Exception as exc:
            logger.warning("Custom provider chat failed: %s", exc)
            return ProviderResponse(
                content="",
                provider="custom",
                model=model,
                error=str(exc),
                duration_ms=(time.monotonic() - t0) * 1000,
            )
