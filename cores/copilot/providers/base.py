from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderError(Exception):
    pass


@dataclass
class ProviderResponse:
    content: str
    provider: str
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: float = 0.0
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderConfig:
    name: str
    enabled: bool = True
    priority: int = 10
    timeout_s: int = 60
    max_retries: int = 2
    models: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class BaseProvider(ABC):
    def __init__(self, config: ProviderConfig) -> None:
        self._config = config

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def priority(self) -> int:
        return self._config.priority

    async def check(self) -> bool:
        return True

    @abstractmethod
    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse: ...

    async def complete(self, prompt: str, **kwargs: Any) -> ProviderResponse:
        return await self.chat([{"role": "user", "content": prompt}], **kwargs)
