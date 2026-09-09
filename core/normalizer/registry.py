"""Normalizer Registry — maps connector IDs to their normalizer."""

from __future__ import annotations

from core.normalizer.base import BaseNormalizer

_registry: dict[str, type[BaseNormalizer]] = {}


def register_normalizer(connector_id: str, normalizer_class: type[BaseNormalizer]) -> None:
    _registry[connector_id] = normalizer_class


def get_normalizer(connector_id: str) -> BaseNormalizer | None:
    cls = _registry.get(connector_id)
    if cls is None:
        return None
    return cls()


def list_normalizers() -> list[str]:
    return list(_registry.keys())
