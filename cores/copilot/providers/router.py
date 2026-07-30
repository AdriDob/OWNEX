from __future__ import annotations

import logging
from typing import Any

from core.copilot.providers.base import BaseProvider, ProviderResponse
from core.copilot.providers.devin_provider import DevinProvider
from core.copilot.providers.fcc_provider import FCCProvider
from core.copilot.providers.nvidia_provider import NvidiaProvider  # Nuevo proveedor
from core.copilot.providers.ollama_provider import OllamaProvider
from core.copilot.providers.opencode_provider import OpenCodeProvider

logger = logging.getLogger("orion.copilot.providers.router")

TASK_CODE = "code"
TASK_REASON = "reason"
TASK_CHAT = "chat"
TASK_SYSTEM = "system"


class ProviderRouter:
    """Routes queries to the best available LLM provider based on task type.

    Priority chain:
      code -> Devin (free AI agent) -> OpenCode (CLI)
      reason -> Devin (free AI agent) -> FCC (Claude via proxy)
      chat -> Devin (free AI agent) -> Ollama (local, fast)
      system -> deterministic (internal)
      # Added NVIDIA as an additional provider
    """

    def __init__(self) -> None:
        self._providers: list[BaseProvider] = [
            DevinProvider(),  # Free AI agent with tools
            FCCProvider(),
            OllamaProvider(),
            OpenCodeProvider(),
            NvidiaProvider()
        ]
        self._health_cache: dict[str, bool] = {}

    @property
    def providers(self) -> list[BaseProvider]:
        return self._providers

    def get_provider(self, name: str) -> BaseProvider | None:
        for p in self._providers:
            if p.name == name:
                return p
        return None

    async def route(
        self, task_type: str = TASK_CHAT, messages: list[dict[str, str]] | None = None, **kwargs: Any
    ) -> ProviderResponse:
        messages = messages or []
        
        # Try Devin first (free AI agent with tools)
        if (provider := self.get_provider("devin")) and await provider.check():
            return await provider.chat(messages, **kwargs)
        logger.warning("Devin unavailable, falling back to other providers")
        
        # Original fallback chain
        if task_type == TASK_CODE and (provider := self.get_provider("opencode")):
            if await provider.check():
                return await provider.chat(messages, **kwargs)
            logger.warning("OpenCode unavailable, falling back to FCC")

        if task_type in (TASK_REASON, TASK_CODE) and (provider := self.get_provider("fcc")):
            if await provider.check():
                return await provider.chat(messages, **kwargs)
            logger.warning("FCC unavailable, falling back to Ollama")

        if provider := self.get_provider("ollama"):
            return await provider.chat(messages, **kwargs)

        return ProviderResponse(content="No provider available", provider="none", error="all providers unavailable")

    async def route_stream(
        self, task_type: str = TASK_CHAT, messages: list[dict[str, str]] | None = None, **kwargs: Any
    ):
        messages = messages or []
        if (
            task_type == TASK_REASON
            and (provider := self.get_provider("fcc"))
            and await provider.check()
            and hasattr(provider, "chat_stream")
        ):
            async for token in await provider.chat_stream(messages, **kwargs):  # type: ignore
                yield token
            return

        if (provider := self.get_provider("ollama")) and hasattr(provider, "chat_stream"):
            async for token in await provider.chat_stream(messages, **kwargs):  # type: ignore
                yield token


_router: ProviderRouter | None = None


def get_provider_router() -> ProviderRouter:
    global _router
    if _router is None:
        _router = ProviderRouter()
    return _router
