"""Unified AI Provider System — Single source of truth for all AI providers in OWNEX.

This system unifies all AI providers to use the same free models as the IDE:
- OmniRoute (DeepSeek, Qwen, Gemini, Groq, Samba)
- NVIDIA NIM (Mistral, Llama, Nemotron)
- Ollama (local models)
- FCC Proxy (Claude via OpenRouter)

This ensures:
- OWNEX auto-repair uses same providers as IDE
- Copilot uses same providers
- MERLIN uses same providers
- All systems use free models consistently
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

logger = logging.getLogger("ownex.unified_ai")


class UnifiedAIProvider:
    """Unified AI provider using same free models as IDE."""

    def __init__(self):
        self._omniroute_base_url = os.getenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")
        self._omniroute_api_key = os.getenv("OMNIROUTE_API_KEY", "omniroute")
        self._nvidia_enabled = bool(os.getenv("NVIDIA_API_KEY") or os.getenv("NIM_API_KEY"))
        self._nvidia_base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self._nvidia_api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NIM_API_KEY", "")
        self._ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._ollama_model = os.getenv("OLLAMA_MODEL", "qwen3-coder:8b")
        self._fcc_base_url = os.getenv("FCC_BASE_URL", "http://localhost:8082")

        # OmniRoute free models (same as IDE)
        self._omniroute_models = [
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

        # NVIDIA models (same as IDE)
        self._nvidia_models = [
            "nv-ai-foundation-541280:mistral-8x7b-instruct-v0.2",
            "nv-ai-foundation-541280:llama-3.1-70b-instruct",
            "nv-ai-foundation-541280:nemotron-3-ultra",
            "nvidia/nemotron-3-ultra",
            "meta/llama-3.1-70b-instruct",
        ]

        # Ollama models (same as IDE)
        self._ollama_models = [
            "qwen3-coder:8b",
            "llama3.1:8b",
            "codellama:7b",
            "mistral:7b",
        ]

        self._default_model = "oc/deepseek-v4-flash-free"

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Chat with AI using unified provider system."""
        model = model or self._default_model
        t0 = time.monotonic()

        # Check if model is NVIDIA model
        is_nvidia = model in self._nvidia_models or model.startswith(("nvidia/", "nv-", "meta/"))

        # Try OmniRoute first for non-NVIDIA models
        if not is_nvidia:
            try:
                result = await self._chat_omniroute(messages, model, max_tokens, temperature, stream)
                if result.get("content"):
                    result["duration_ms"] = (time.monotonic() - t0) * 1000
                    return result
            except Exception as e:
                logger.warning("OmniRoute chat failed: %s", e)

        # NVIDIA fallback
        if self._nvidia_enabled and is_nvidia:
            try:
                result = await self._chat_nvidia(messages, model, max_tokens, temperature, stream)
                if result.get("content"):
                    result["duration_ms"] = (time.monotonic() - t0) * 1000
                    return result
            except Exception as e:
                logger.warning("NVIDIA chat failed: %s", e)

        # Ollama fallback
        try:
            result = await self._chat_ollama(messages, model, max_tokens, temperature, stream)
            if result.get("content"):
                result["duration_ms"] = (time.monotonic() - t0) * 1000
                return result
        except Exception as e:
            logger.warning("Ollama chat failed: %s", e)

        return {
            "content": "",
            "provider": "unified",
            "model": model,
            "error": "All providers unavailable",
            "duration_ms": (time.monotonic() - t0) * 1000,
        }

    async def _chat_omniroute(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        stream: bool,
    ) -> dict[str, Any]:
        """Chat via OmniRoute provider."""
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{self._omniroute_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._omniroute_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "stream": stream,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            if r.status_code == 200:
                data = r.json()
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                usage = data.get("usage", {})
                return {
                    "content": content,
                    "provider": "omniroute",
                    "model": data.get("model", model),
                    "tokens_in": usage.get("prompt_tokens", 0),
                    "tokens_out": usage.get("completion_tokens", 0),
                }
            else:
                return {"error": f"OmniRoute API error {r.status_code}"}

    async def _chat_nvidia(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        stream: bool,
    ) -> dict[str, Any]:
        """Chat via NVIDIA NIM provider."""
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{self._nvidia_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._nvidia_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            if r.status_code == 200:
                data = r.json()
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                usage = data.get("usage", {})
                return {
                    "content": content,
                    "provider": "nvidia",
                    "model": model,
                    "tokens_in": usage.get("prompt_tokens", 0),
                    "tokens_out": usage.get("completion_tokens", 0),
                }
            else:
                return {"error": f"NVIDIA API error {r.status_code}"}

    async def _chat_ollama(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        stream: bool,
    ) -> dict[str, Any]:
        """Chat via Ollama provider."""
        # Convert messages to prompt
        prompt = "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{self._ollama_host}/api/generate",
                json={
                    "model": self._ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
            )
            if r.status_code == 200:
                data = r.json()
                return {
                    "content": data.get("response", ""),
                    "provider": "ollama",
                    "model": self._ollama_model,
                }
            else:
                return {"error": f"Ollama API error {r.status_code}"}

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream chat with AI using unified provider system."""
        model = model or self._default_model
        is_nvidia = model in self._nvidia_models or model.startswith(("nvidia/", "nv-", "meta/"))

        # Try OmniRoute first
        if not is_nvidia:
            try:
                async for chunk in self._stream_omniroute(messages, model, max_tokens, temperature):
                    yield chunk
                return
            except Exception as e:
                logger.warning("OmniRoute stream failed: %s", e)

        # NVIDIA fallback
        if self._nvidia_enabled and is_nvidia:
            try:
                async for chunk in self._stream_nvidia(messages, model, max_tokens, temperature):
                    yield chunk
                return
            except Exception as e:
                logger.warning("NVIDIA stream failed: %s", e)

        # Ollama fallback
        try:
            async for chunk in self._stream_ollama(messages, model, max_tokens, temperature):
                yield chunk
            return
        except Exception as e:
            logger.warning("Ollama stream failed: %s", e)

    async def _stream_omniroute(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        """Stream via OmniRoute."""
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{self._omniroute_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._omniroute_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            ) as r:
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

    async def _stream_nvidia(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        """Stream via NVIDIA."""
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
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
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            ) as r:
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

    async def _stream_ollama(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        """Stream via Ollama."""
        prompt = "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{self._ollama_host}/api/generate",
                json={
                    "model": self._ollama_model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
            ) as r:
                async for line in r.aiter_lines():
                    try:
                        data = json.loads(line)
                        if response := data.get("response"):
                            yield response
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    def get_available_models(self) -> list[str]:
        """Get all available models from all providers."""
        models = []
        models.extend(self._omniroute_models)
        if self._nvidia_enabled:
            models.extend(self._nvidia_models)
        models.extend(self._ollama_models)
        return models

    async def check_health(self) -> dict[str, Any]:
        """Check health of all providers."""
        health = {
            "omniroute": False,
            "nvidia": False,
            "ollama": False,
        }

        # Check OmniRoute
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{self._omniroute_base_url}/models")
                health["omniroute"] = r.status_code == 200
        except Exception:
            pass

        # Check NVIDIA
        if self._nvidia_enabled:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    r = await client.get(
                        f"{self._nvidia_base_url}/models",
                        headers={"Authorization": f"Bearer {self._nvidia_api_key}"},
                    )
                    health["nvidia"] = r.status_code == 200
            except Exception:
                pass

        # Check Ollama
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{self._ollama_host}/api/tags")
                health["ollama"] = r.status_code == 200
        except Exception:
            pass

        return health


# Singleton instance
_global_provider: UnifiedAIProvider | None = None


def get_unified_provider() -> UnifiedAIProvider:
    """Get the global unified AI provider."""
    global _global_provider
    if _global_provider is None:
        _global_provider = UnifiedAIProvider()
    return _global_provider
