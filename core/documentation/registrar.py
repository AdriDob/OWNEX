"""Documentation Registrar — modules self-describe here.

Usage:

    from core.documentation.registrar import register_module, get_module_doc

    register_module(ModuleDoc(
        id="event_bus",
        name="Event Bus",
        category="core",
        capabilities=[CapabilityDoc(name="publish_events", ...)],
        ...
    ))

    # Later, the generator retrieves everything:
    all_modules = list_all_modules()
"""

from __future__ import annotations

import logging
from typing import Any

from core.documentation.models import ModuleDoc

logger = logging.getLogger("orion.core.documentation")

_registry: dict[str, ModuleDoc] = {}


def register_module(doc: ModuleDoc) -> None:
    """Register or update a module's self-description."""
    _registry[doc.id] = doc
    logger.debug("Documentation registered: %s (%s)", doc.id, doc.name)


def get_module_doc(module_id: str) -> ModuleDoc | None:
    """Get a registered module's documentation."""
    return _registry.get(module_id)


def list_all_modules() -> list[ModuleDoc]:
    """Return all registered module docs, ordered by category then name."""
    return sorted(_registry.values(), key=lambda m: (m.category or "", m.name or ""))


def list_by_category(category: str) -> list[ModuleDoc]:
    """Return all modules in a category."""
    return [m for m in _registry.values() if m.category == category]


def unregister_module(module_id: str) -> None:
    """Remove a module from the documentation registry."""
    _registry.pop(module_id, None)


def clear() -> None:
    _registry.clear()


def count() -> int:
    return len(_registry)


def to_dict() -> dict[str, Any]:
    return {mid: doc.to_dict() for mid, doc in _registry.items()}
