from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from core.copilot.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = logging.getLogger("orion.copilot.providers.omniroute")

_OMNIROUTE_MODELS = [
    "oc/deepseek-v4-flash-free",
    "oc/qwen3.6-plus-free",
    "oc/minimax-m3-free",
    "aug/gemini-3.1-pro",
    "aug/gemini-3.0-flash",
    "groq/llama-3.3-70b-versatile",
    "groq/meta-llama/llama-4-scout-17b-16e-instruct",
    "groq/qwen/qwen3-32b",
    "groq/qwen/qwen3.6-27b",
    "samba/Meta-Llama-3.3-70B-Instruct",
    "samba/Llama-4-Maverick-17B-128E-Instruct",
    "samba/DeepSeek-V3.2",
    "auto/best-coding",
    "auto/best-fast",
    "auto/best-reasoning",
]

# NVIDIA models available via NVIDIA NIM API
_NVIDIA_MODELS = [
    "nv-ai-foundation-541280:mistral-8x7b-instruct-v0.2",
    "nv-ai-foundation-541280:llama-3.1-70b-instruct",
    "nv-ai-foundation-541280:nemotron-3-ultra",
    "nvidia/nemotron-3-ultra",
    "meta/llama-3.1-70b-instruct",
]


class OmniRouteProvider(BaseProvider):
    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(
            config
            or ProviderConfig(
                name="omniroute",
                priority=15,
                models=_OMNIROUTE_MODELS,
                timeout_s=60,
            )
        )
        self._base_url = self._config.extra.get(
            "base_url", os.getenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")
        )
        self._api_key = self._config.extra.get("api_key", os.getenv("OMNIROUTE_API_KEY", "omniroute"))
        self._default_model = self._config.models[0]
        # NVIDIA integration for models not available via OmniRoute
        self._nvidia_enabled = bool(os.getenv("NVIDIA_API_KEY") or os.getenv("NIM_API_KEY"))
        self._nvidia_base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self._nvidia_api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NIM_API_KEY", "")

    async def check(self) -> bool:
        """Quick health check with short timeout."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{self._base_url}/models")
                if r.status_code == 200:
                    return True
        except Exception:
            pass
        # Fallback to NVIDIA if OmniRoute is down
        if self._nvidia_enabled:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    r = await client.get(
                        f"{self._nvidia_base_url}/models",
                        headers={"Authorization": f"Bearer {self._nvidia_api_key}"},
                    )
                    return r.status_code == 200
            except Exception:
                pass
        return False

    async def list_models(self) -> list[str]:
        """List available models from OmniRoute + NVIDIA."""
        models = []
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self._base_url}/models")
                if r.status_code == 200:
                    data = r.json()
                    models = [m.get("id", "") for m in data.get("data", [])]
        except Exception as e:
            logger.warning("Failed to list OmniRoute models: %s", e)

        # Add NVIDIA models if available
        if self._nvidia_enabled:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    r = await client.get(
                        f"{self._nvidia_base_url}/models",
                        headers={"Authorization": f"Bearer {self._nvidia_api_key}"},
                    )
                    if r.status_code == 200:
                        data = r.json()
                        nvidia_models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                        models.extend(nvidia_models)
            except Exception as e:
                logger.warning("Failed to list NVIDIA models: %s", e)

        if not models:
            models = _OMNIROUTE_MODELS
            if self._nvidia_enabled:
                models.extend(_NVIDIA_MODELS)
        return models[:100]  # Limit to first 100 models

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        import time

        model = kwargs.get("model", self._default_model)
        t0 = time.monotonic()

        # Check if model is a NVIDIA model
        is_nvidia_model = (
            model in _NVIDIA_MODELS
            or model.startswith("nvidia/")
            or model.startswith("nv-")
            or model.startswith("meta/")
        )

        # Try OmniRoute first for non-NVIDIA models
        if not is_nvidia_model:
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
                            "temperature": kwargs.get("temperature", 0.7),
                        },
                    )
                    if r.status_code == 200:
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
                    elif r.status_code in (401, 402, 403, 429, 500, 502, 503, 504):
                        logger.warning("OmniRoute API error %d, will try NVIDIA fallback: %s", r.status_code, r.text)
                    else:
                        logger.warning("OmniRoute API error: %s - %s", r.status_code, r.text)
            except Exception as exc:
                logger.warning("OmniRoute chat failed, will try NVIDIA fallback: %s", exc)

        # NVIDIA fallback (or primary for NVIDIA models)
        if self._nvidia_enabled:
            try:
                async with httpx.AsyncClient(timeout=self._config.timeout_s) as client:
                    r = await client.post(
                        f"{self._nvidia_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self._nvidia_api_key}",
                            "Content-Type": "application/json",
                            "Accept": "text/event-stream",
                        },
                        json={"model": model, "messages": messages, "max_tokens": kwargs.get("max_tokens", 4096)},
                    )
                    if r.status_code == 200:
                        data = r.json()
                        dur = (time.monotonic() - t0) * 1000
                        choice = data.get("choices", [{}])[0]
                        content = choice.get("message", {}).get("content", "")
                        usage = data.get("usage", {})
                        return ProviderResponse(
                            content=content,
                            provider="omniroute",
                            model=model,
                            tokens_in=usage.get("prompt_tokens", 0),
                            tokens_out=usage.get("completion_tokens", 0),
                            duration_ms=dur,
                        )
                    else:
                        logger.warning("NVIDIA API error: %s - %s", r.status_code, r.text)
                        return ProviderResponse(
                            content="",
                            provider="omniroute",
                            model=model,
                            error=f"NVIDIA API error {r.status_code}",
                            duration_ms=(time.monotonic() - t0) * 1000,
                        )
            except Exception as exc:
                logger.warning("NVIDIA chat failed: %s", exc)
                return ProviderResponse(
                    content="",
                    provider="omniroute",
                    model=model,
                    error=str(exc),
                    duration_ms=(time.monotonic() - t0) * 1000,
                )

        # OmniRoute failed and no NVIDIA fallback
        return ProviderResponse(
            content="",
            provider="omniroute",
            model=model,
            error="All providers unavailable",
            duration_ms=(time.monotonic() - t0) * 1000,
        )

    async def chat_stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        import httpx

        model = kwargs.get("model", self._default_model)
        is_nvidia_model = (
            model in _NVIDIA_MODELS
            or model.startswith("nvidia/")
            or model.startswith("nv-")
            or model.startswith("meta/")
        )

        # Try OmniRoute first for non-NVIDIA models
        if not is_nvidia_model:
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
                    return
            except Exception as exc:
                logger.warning("OmniRoute stream failed, will try NVIDIA fallback: %s", exc)

        # NVIDIA fallback (or primary for NVIDIA models)
        if self._nvidia_enabled:
            try:
                async with (
                    httpx.AsyncClient(timeout=self._config.timeout_s) as client,
                    client.stream(
                        "POST",
                        f"{self._nvidia_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self._nvidia_api_key}",
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
                logger.warning("NVIDIA stream failed: %s", exc)
