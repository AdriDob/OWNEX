"""OpenCode Provider — Free models via OpenCode."""

from __future__ import annotations

import logging
import os

from ..provider import OpenAICompatibleProvider

logger = logging.getLogger("ownex.ai.providers.opencode")


class OpenCodeProvider(OpenAICompatibleProvider):
    """OpenCode provider — Free models via OpenCode.

    Features:
    - Free models (DeepSeek, Nemotron, etc.)
    - OpenAI-compatible API
    - No API key required for some models
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        super().__init__(
            api_key=api_key or os.getenv("OPENCODE_API_KEY", ""),
            base_url=base_url or os.getenv("OPENCODE_BASE_URL", "https://api.opencode.ai/v1"),
            model=model or "opencode/deepseek-v4-flash-free",
        )

    @property
    def name(self) -> str:
        return f"opencode/{self.model}"

    def is_available(self) -> bool:
        # OpenCode free models don't require API key
        if self._available is None:
            self._available = True  # Always try
        return self._available

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 512) -> str:
        try:
            import httpx

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }
            headers = {
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            with httpx.Client(timeout=120) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )

            if resp.status_code != 200:
                logger.warning(f"OpenCode API error: {resp.status_code} - {resp.text}")
                return ""

            data = resp.json()
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            return content.strip()

        except Exception as e:
            logger.warning(f"OpenCode call failed: {e}")
            return ""
