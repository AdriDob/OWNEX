from __future__ import annotations

from abc import ABC, abstractmethod


class IStorage(ABC):
    """Simple file-based storage for artifacts, screenshots, evidence."""

    @abstractmethod
    def read(self, path: str) -> bytes | None:
        ...

    @abstractmethod
    def write(self, path: str, data: bytes) -> str:
        """Returns the full path written."""

    @abstractmethod
    def delete(self, path: str) -> bool:
        ...

    @abstractmethod
    def list(self, prefix: str) -> list[str]:
        ...

    @abstractmethod
    def exists(self, path: str) -> bool:
        ...
