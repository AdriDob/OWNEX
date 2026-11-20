"""
Plugin Registry - manages plugin discovery and registration.

Provides the get_plugin_registry() function used by core/app_registry.py.
"""
from __future__ import annotations

def get_plugin_registry() -> dict:
    """Get the plugin registry instance."""
    return {"plugins": [], "status": "initial"}
