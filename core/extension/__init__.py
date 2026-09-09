"""ORION Extension SDK — second-party and third-party extensions.
Extensions live in ``extensions/<name>/``, declare a ``manifest.py``,
and are auto-discovered by the ExtensionRegistry.
An extension CAN be as simple as a single hook, and as complex as a full app.
"""

from cores.extension.capabilities import Capability, CapabilityRegistry, get_capability_registry
from cores.extension.hooks import Hook, HookRegistry, get_hook_registry
from cores.extension.manifest import ExtensionManifest
from cores.extension.registry import ExtensionRegistry, get_extension_registry
from cores.extension.settings import ApiKeyField, NumberField, SelectField, SettingsField, SwitchField, TextField

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
