from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from cores.copilot.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger("orion.copilot.providers.fcc")


class FCCProvider(BaseProvider):
    """FCC proxy — Free models via Free Claude Code proxy (claude no-thinking)."""

    # HTTP status codes that should trigger failover
    FAILOVER_STATUS_CODES = {401, 402, 403, 429, 500, 502, 503, 504}

    # Free models available via FCC proxy — CUADOS con evidencia (2026-09-15):
    # solo los que devuelven contenido real vía /chat/completions (HTTP 200 + texto).
    FREE_MODELS = [
        # Claude vía FCC (no-thinking) — verificado con contenido real
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ]

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(
            config
            or ProviderConfig(
                name="fcc",
                priority=20,
                models=[
                    "claude-3-5-sonnet-20241022",
                    "claude-3-5-haiku-20241022",
                ],
                timeout_s=60,
            )
        )
        # Support multiple API key sources: NVIDIA, Anthropic, OpenRouter
        self._api_key = self._config.extra.get(
            "api_key",
            os.getenv("ANTHROPIC_API_KEY")  # token del proxy FCC (orion-dev-local)
            or os.getenv("FCC_AUTH_TOKEN")
            or os.getenv("NVIDIA_API_KEY")
            or os.getenv("NIM_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
            or "",
        )
        # FCC es UN proxy local (free): siempre a http://localhost:8082/v1.
        # No seguir claves NVIDIA/OpenRouter aquí — eso apuntaba a upstream pago/404.
        self._provider_type = "fcc"
        self._base_url = self._config.extra.get("base_url") or os.getenv("FCC_API_BASE", "http://localhost:8082/v1")

        self._default_model = self._config.models[0]
        self._last_health_check = 0.0
        self._health_check_interval = 60.0  # seconds
        self._healthy = False

    def _get_free_models(self) -> list[str]:
        """Return the list of free models available via FCC proxy."""
        return self.FREE_MODELS

    async def list_models(self) -> list[str]:
        """List available free models from the configured provider."""
        try:
            # Try to fetch from the actual API
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{self._base_url}/models", headers={"Authorization": f"Bearer {self._api_key}"}, timeout=10
                )
                if r.status_code == 200:
                    data = r.json()
                    models = []
                    for m in data.get("data", []):
                        model_id = m.get("id", "")
                        # Filter for free models only
                        pricing = m.get("pricing", {})
                        if pricing:
                            prompt_price = float(pricing.get("prompt", "0"))
                            completion_price = float(pricing.get("completion", "0"))
                            if prompt_price <= 0.001 and completion_price <= 0.001:
                                models.append(model_id)
                        else:
                            # If no pricing info, assume free if it's in our free list
                            if m.get("id", "") in self.FREE_MODELS:
                                models.append(m.get("id", ""))
                    return models[:100]  # Limit to first 100 free models
        except Exception as e:
            logger.warning("Failed to list FCC models: %s", e)

        # Fallback to our curated free models list
        return self.FREE_MODELS[:50]

    async def check(self) -> bool:
        """Health check with actual connectivity verification and caching."""
        now = time.monotonic()
        if now - self._last_health_check < self._health_check_interval:
            return self._healthy

        self._last_health_check = now
        self._healthy = await self._verify_connectivity()
        return self._healthy

    async def _verify_connectivity(self) -> bool:
        """Verify actual API connectivity."""
        if not self._api_key:
            logger.debug("FCC: No API key configured")
            return False

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{self._base_url}/models", headers={"Authorization": f"Bearer {self._api_key}"}, timeout=10
                )
                if r.status_code == 200:
                    logger.debug("FCC: Health check passed (%s)", self._provider_type)
                    return True
                elif r.status_code in self.FAILOVER_STATUS_CODES:
                    logger.warning("FCC: Health check failed with status %d (%s)", r.status_code, self._provider_type)
                    return False
                else:
                    logger.warning("FCC: Health check unexpected status %d (%s)", r.status_code, self._provider_type)
                    return False
        except Exception as exc:
            logger.warning("FCC: Health check error (%s): %s", self._provider_type, exc)
            return False

    def _should_failover(self, status_code: int) -> bool:
        """Determine if a status code should trigger failover."""
        return status_code in self.FAILOVER_STATUS_CODES

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
                    # Include failover flag for router
                    should_failover = self._should_failover(r.status_code)
                    return ProviderResponse(
                        content="",
                        provider="fcc",
                        model=model,
                        error=f"API error {r.status_code}",
                        duration_ms=(time.monotonic() - t0) * 1000,
                        extra={"should_failover": should_failover, "status_code": r.status_code},
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
                        "temperature": kwargs.get("temperature", 0.7),
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
                return
        except Exception as exc:
            logger.warning("FCC stream failed: %s", exc)
