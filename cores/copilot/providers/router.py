from __future__ import annotations

import logging
from typing import Any

from cores.copilot.prompt_guard import flag_response, guard_messages
from cores.copilot.providers.base import BaseProvider, ProviderResponse
from cores.copilot.providers.devin_provider import DevinProvider
from cores.copilot.providers.fcc_provider import FCCProvider
from cores.copilot.providers.freebuff_provider import FreebuffProvider
from cores.copilot.providers.nvidia_provider import NvidiaProvider  # Nuevo proveedor
from cores.copilot.providers.ollama_provider import OllamaProvider
from cores.copilot.providers.omniroute_provider import OmniRouteProvider
from cores.copilot.providers.opencode_provider import OpenCodeProvider

logger = logging.getLogger("orion.copilot.providers.router")

TASK_CODE = "code"
TASK_REASON = "reason"
TASK_CHAT = "chat"
TASK_SYSTEM = "system"


class ProviderRouter:
    """Routes queries to the best available LLM provider based on task type.

    Cadena free 24/7 VERIFICADA 2026-09-15 (contenido real vía HTTP):
      FCC (claude no-thinking) → NVIDIA NIM (deepseek-v4-flash) → OmniRoute
      (auto/best-free) → OpenCode (*-free) → Ollama local (qwen2.5:3b).
      Devin + Freebuff se conservan al final para code como agentes gratuitos.

      code -> FCC -> NVIDIA -> OmniRoute -> OpenCode -> Ollama -> Devin -> Freebuff
      reason/chat -> FCC -> NVIDIA -> OmniRoute -> OpenCode -> Ollama
      system -> deterministic (internal)
    """

    def __init__(self) -> None:
        self._providers: list[BaseProvider] = [
            FCCProvider(),  # Claude vía proxy free (verificado: claude-3-5 no-thinking)
            NvidiaProvider(),  # NVIDIA NIM free (verificado: deepseek-v4-flash-0731)
            OmniRouteProvider(),  # Orquestador local free (auto/best-free)
            OpenCodeProvider(),  # Modelos opencode/*-free
            OllamaProvider(),  # Local más ligero (qwen2.5:3b-instruct)
            DevinProvider(),  # Free AI agent with tools (conservado)
            FreebuffProvider(),  # GitHub autonomous coding agent (conservado)
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

    async def _chat_guarded(
        self, provider: BaseProvider, messages: list[dict[str, str]], matched: list[str], **kwargs: Any
    ) -> ProviderResponse:
        """Single provider call site: runs chat and flags suspected injections."""
        result = await provider.chat(messages, **kwargs)
        if matched:
            flag_response(result, matched)
        return result

    async def route(
        self, task_type: str = TASK_CHAT, messages: list[dict[str, str]] | None = None, **kwargs: Any
    ) -> ProviderResponse:
        messages, _suspected, matched = guard_messages(messages or [])

        # Task-specific routing with proper fallback chain (free 24/7 first).
        if task_type == TASK_CODE:
            # code -> FCC -> NVIDIA -> OmniRoute -> OpenCode -> Ollama -> Devin -> Freebuff
            for provider_name in ["fcc", "nvidia", "omniroute", "opencode", "ollama", "devin", "freebuff"]:
                if (provider := self.get_provider(provider_name)) and await provider.check():
                    return await self._chat_guarded(provider, messages, matched, **kwargs)
                logger.warning("%s unavailable, trying next", provider_name)

        else:
            # reason/chat -> FCC -> NVIDIA -> OmniRoute -> OpenCode -> Ollama
            for provider_name in ["fcc", "nvidia", "omniroute", "opencode", "ollama"]:
                if (provider := self.get_provider(provider_name)) and await provider.check():
                    return await self._chat_guarded(provider, messages, matched, **kwargs)
                logger.warning("%s unavailable, trying next", provider_name)

        return ProviderResponse(content="No provider available", provider="none", error="all providers unavailable")

    async def route_stream(
        self, task_type: str = TASK_CHAT, messages: list[dict[str, str]] | None = None, **kwargs: Any
    ):
        # Guarded (log-only: token streams carry no response metadata channel).
        messages, _suspected, _matched = guard_messages(messages or [])
        if (
            task_type == TASK_REASON
            and (provider := self.get_provider("fcc"))
            and await provider.check()
            and hasattr(provider, "chat_stream")
        ):
            async for token in await provider.chat_stream(messages, **kwargs):  # type: ignore
                yield token
            return

        # Try NVIDIA for streaming (reasoning models)
        if (provider := self.get_provider("nvidia")) and await provider.check() and hasattr(provider, "chat_stream"):
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
