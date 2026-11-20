"""
Core Plugin System - Module Discovery and Registry.

Provides discovery, registry, and management of
plug-in modules for the OWNEX platform.
"""

from cores.plugin.registry import get_plugin_registry

__all__ = [
    "get_plugin_registry",
]
