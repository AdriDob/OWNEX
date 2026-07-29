"""ORION Extension SDK — second-party and third-party extensions.

Extensions live in ``extensions/<name>/``, declare a ``manifest.py``,
and are auto-discovered by the ExtensionRegistry.

An extension CAN be as simple as a single hook, and as complex as a full app.
"""

from core.extension.capabilities import Capability, CapabilityRegistry, get_capability_registry
from core.extension.hooks import Hook, HookRegistry, get_hook_registry
from core.extension.manifest import ExtensionManifest
from core.extension.registry import ExtensionRegistry, get_extension_registry
from core.extension.settings import ApiKeyField, NumberField, SelectField, SettingsField, SwitchField, TextField

__all__ = [
    "ExtensionManifest",
    "ExtensionRegistry",
    "get_extension_registry",
    "Hook",
    "HookRegistry",
    "get_hook_registry",
    "SettingsField",
    "TextField",
    "ApiKeyField",
    "SwitchField",
    "NumberField",
    "SelectField",
    "Capability",
    "CapabilityRegistry",
    "get_capability_registry",
]
