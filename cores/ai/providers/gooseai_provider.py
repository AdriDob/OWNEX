"""GooseAI Provider — NLP-as-a-Service at 30% cost of competitors.

Integrated into OWNEX's AI Router ecosystem with automatic fallback support
from Ollama → OpenCode → GooseAI → FCC Proxy → NVIDIA NIM
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Generator

import httpx

from ..provider import OpenAICompatibleProvider

logger = logging.getLogger("ownex.ai.providers.gooseai")


class GooseAIProvider(OpenAICompatibleProvider):
    """GooseAI provider — fully managed NLP-as-a-Service via API.

    Features:
    - 30% the cost of OpenAI/Anthropic
    - Industry-standard API compatibility (OpenAI-like)
    - Multiple model tiers: Small/Medium/Large/Massive
    - Automatic failover support
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        super().__init__(
            api_key=api_key or os.getenv("GOSEAI_API_KEY", ""),
            base_url=base_url or os.getenv("GOSEAI_API_BASE", "https://api.goose.ai/v1"),
            model=model or "gooseai/gpt-neo-1.3b",
        )

    @property
    def name(self) -> str:
        return f"gooseai/{self.model}"

    def is_available(self) -> bool:
        if self._available is None:
            self._available = bool(self.api_key)
        return self._available

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 512) -> str:
        # Override to use GooseAI specific headers and handle errors
        if not self.api_key:
            return ""
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "OWNEX-CORTEY",
                "X-Title": "OWNEX Autonomous Work System",
            }
            req = httpx.Request(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            with httpx.Client(timeout=120) as client:
                resp = client.send(req)

            if resp.status_code != 200:
                error_msg = f"GooseAI API error: {resp.status_code} - {resp.text}"
                logger.warning(error_msg)
                self._available = False
                return ""

            data = resp.json()
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            return content.strip()
        except Exception as e:
            logger.warning(f"GooseAI call failed: {e}")
            self._available = False
            return ""

    def chat_stream(self, messages: list[dict[str, str]], max_tokens: int = 512) -> Generator[str, None, None]:
        if not self.api_key:
            return
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
                "stream": True,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "OWNEX-CORTEY",
                "X-Title": "OWNEX Autonomous Work System",
            }
            with (
                httpx.Client(timeout=120) as client,
                client.stream("POST", f"{self.base_url}/chat/completions", json=payload, headers=headers) as resp,
            ):
                if resp.status_code != 200:
                    logger.warning(f"GooseAI stream error: {resp.status_code}")
                    return

                for line in resp.iter_lines():
                    if not line.strip() or line.startswith(":"):
                        continue
                    if line.strip() == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            if content := delta.get("content"):
                                yield content
                        except Exception:
                            continue
        except Exception as e:
            logger.warning(f"GooseAI stream failed: {e}")
