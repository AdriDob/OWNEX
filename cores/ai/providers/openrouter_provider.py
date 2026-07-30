"""OpenRouter provider — Premium models via OpenRouter API."""

from __future__ import annotations

import logging
import os
from typing import Any

from cores.ai.providers.base import BaseAIProvider

logger = logging.getLogger("ownex.ai.providers.openrouter")


class OpenRouterProvider(BaseAIProvider):
    """OpenRouter provider for premium AI models.

    Supports GPT-4, Claude, Gemini, and other premium models via OpenRouter.
    """

    def __init__(self, api_key: str | None = None, model: str = "openai/gpt-4o-mini") -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self._available: bool | None = None

    @property
    def name(self) -> str:
        return f"openrouter/{self.model}"

    def is_available(self) -> bool:
        """Check if OpenRouter API key is configured."""
        if self._available is not None:
            return self._available

        if not self.api_key:
            self._available = False
            return False

        # Try a simple health check
        try:
            import httpx

            response = httpx.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5,
            )
            self._available = response.status_code == 200
            return self._available
        except Exception as e:
            logger.warning(f"OpenRouter health check failed: {e}")
            self._available = False
            return False

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Send chat request to OpenRouter."""
        if not self.is_available():
            logger.warning("OpenRouter provider not available")
            return ""

        import time

        import httpx

        model = kwargs.get("model", self.model)
        max_tokens = kwargs.get("max_tokens", 4096)
        temperature = kwargs.get("temperature", 0.7)

        try:
            t0 = time.time()
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/adrie/Rastro",
                    "X-Title": "OWNEX",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=120,
            )
            elapsed = (time.time() - t0) * 1000

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                logger.info(f"OpenRouter chat success: {model} ({elapsed:.0f}ms)")
                return content
            else:
                logger.warning(f"OpenRouter API error: {response.status_code} - {response.text}")
                self._available = False
                return ""

        except Exception as e:
            logger.warning(f"OpenRouter chat failed: {e}")
            self._available = False
            return ""

    def chat_stream(self, messages: list[dict[str, str]], **kwargs: Any):
        """Stream chat response from OpenRouter."""
        if not self.is_available():
            logger.warning("OpenRouter provider not available")
            return

        import httpx

        model = kwargs.get("model", self.model)
        max_tokens = kwargs.get("max_tokens", 4096)
        temperature = kwargs.get("temperature", 0.7)

        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/adrie/Rastro",
                    "X-Title": "OWNEX",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True,
                },
                timeout=120,
            ) as response:
                for line in response.iter_lines():
                    if not line.strip() or line.startswith(b":"):
                        continue
                    if line.startswith(b"data: [DONE]"):
                        break
                    if line.startswith(b"data: "):
                        try:
                            import json

                            data = json.loads(line.removeprefix(b"data: ").decode())
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            if content := delta.get("content"):
                                yield content
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue
        except Exception as e:
            logger.warning(f"OpenRouter stream failed: {e}")
            self._available = False

    def get_config(self) -> dict[str, Any]:
        """Return provider configuration."""
        return {
            "provider": self.name,
            "model": self.model,
            "api_key_configured": bool(self.api_key),
            "base_url": self.base_url,
            "available": self.is_available(),
        }
