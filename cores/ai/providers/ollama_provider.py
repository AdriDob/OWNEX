"""Ollama Provider — Local Ollama models."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Generator

from ..provider import AIProvider

logger = logging.getLogger("ownex.ai.providers.ollama")


class OllamaProvider(AIProvider):
    """Ollama provider — Local Ollama models.

    Features:
    - Local inference with Ollama
    - No API key required
    - Multiple model support
    """

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
    ):
        self.host = (host or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "freehuntx/qwen3-coder:8b")
        self._available: bool | None = None

    def _check(self) -> bool:
        try:
            import urllib.request

            req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def is_available(self) -> bool:
        if self._available is None:
            self._available = self._check()
        return self._available

    @property
    def name(self) -> str:
        return f"ollama/{self.model}"

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 512) -> str:
        prompt = self._format_prompt(messages)
        try:
            import urllib.request

            payload = json.dumps(
                {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens, "temperature": 0.3},
                }
            ).encode()
            req = urllib.request.Request(
                f"{self.host}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                return result.get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama call failed: {e}")
            self._available = False
            return ""

    def _format_prompt(self, messages: list[dict[str, str]]) -> str:
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        parts.append("Assistant: ")
        return "\n".join(parts)

    def chat_stream(self, messages: list[dict[str, str]], max_tokens: int = 512) -> Generator[str, None, None]:
        try:
            import urllib.request

            prompt = self._format_prompt(messages)
            payload = json.dumps(
                {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {"num_predict": max_tokens, "temperature": 0.3},
                }
            ).encode()
            req = urllib.request.Request(
                f"{self.host}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                for line in resp:
                    if not line.strip():
                        continue
                    chunk = json.loads(line.decode())
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done", False):
                        break
        except Exception as e:
            logger.warning(f"Ollama stream failed: {e}")
            self._available = False
