"""ExtensionRegistry — discovers, loads, and manages all extensions.

Extensions live in ``extensions/<name>/`` and MUST expose a module-level
``manifest`` variable of type ``ExtensionManifest``.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path

from core.extension.capabilities import Capability, get_capability_registry
from core.extension.hooks import get_hook_registry
from core.extension.manifest import ExtensionManifest
from core.plugin.discovery import discover_manifests

logger = logging.getLogger("orion.core.extensions")

EXTENSIONS_DIR = Path(__file__).resolve().parent.parent.parent / "extensions"
EXTENSIONS_PACKAGE = "extensions"


class ExtensionRegistry:
    """Discovers, validates, and manages ORION extensions."""

    def __init__(self) -> None:
        self._extensions: dict[str, ExtensionManifest] = {}
        self._loaded: dict[str, bool] = {}
        self._failed: dict[str, str] = {}

    def discover(self) -> dict[str, ExtensionManifest]:
        """Scan ``extensions/`` directory and load every manifest."""
        if self._extensions:
            return self._extensions
        manifests = discover_manifests(EXTENSIONS_DIR, EXTENSIONS_PACKAGE, ExtensionManifest)
        for ext_id, manifest in manifests.items():
            self._extensions[ext_id] = manifest
            self._loaded[ext_id] = False
            self._register_capabilities(manifest)
        return self._extensions

    def load(self, extension_id: str) -> bool:
        manifest = self._extensions.get(extension_id)
        if manifest is None:
            logger.warning("Extension %s not found", extension_id)
            return False
        if self._loaded.get(extension_id):
            return True

        missing = self._check_dependencies(manifest)
        if missing:
            logger.error("Extension %s missing dependencies: %s", extension_id, missing)
            self._failed[extension_id] = f"Missing dependencies: {', '.join(missing)}"
            return False

        hook_registry = get_hook_registry()
        for hook_name, handler_path in manifest.hooks.items():
            try:
                module_path, func_name = handler_path.rsplit(".", 1)
                mod = importlib.import_module(f"{EXTENSIONS_PACKAGE}.{extension_id}.{module_path}")
                handler = getattr(mod, func_name, None)
                if handler:
                    hook_registry.register_handler(hook_name, extension_id, handler)
                else:
                    logger.warning("  Hook %s: handler %s not found", hook_name, handler_path)
            except Exception as exc:
                logger.warning("  Hook %s failed to load: %s", hook_name, exc)

        self._loaded[extension_id] = True
        self._failed.pop(extension_id, None)
        logger.info("Extension loaded: %s", manifest.name)
        return True

    def unload(self, extension_id: str) -> bool:
        manifest = self._extensions.get(extension_id)
        if manifest is None:
            return False
        get_hook_registry().unregister_extension(extension_id)
        get_capability_registry().unregister(extension_id)
        self._loaded[extension_id] = False
        logger.info("Extension unloaded: %s", manifest.name)
        return True

    def load_all(self) -> dict[str, bool]:
        results = {}
        for ext_id in self._extensions:
            results[ext_id] = self.load(ext_id)
        return results

    def reload(self, extension_id: str) -> bool:
        self.unload(extension_id)
        self._extensions.pop(extension_id, None)
        self.discover()
        return self.load(extension_id)

    def get(self, extension_id: str) -> ExtensionManifest | None:
        return self._extensions.get(extension_id)

    def list_extensions(self) -> list[ExtensionManifest]:
        return sorted(self._extensions.values(), key=lambda e: e.name)

    def status(self) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for ext_id, m in self._extensions.items():
            # Safely format capabilities — handle both Capability objects and strings
            caps: list[str] = []
            for c in m.capabilities or []:
                if isinstance(c, Capability):
                    caps.append(f"{c.domain}:{c.name}")
                elif isinstance(c, str):
                    caps.append(c)
                else:
                    caps.append(str(c))

            result[ext_id] = {
                "name": m.name,
                "version": m.version,
                "loaded": self._loaded.get(ext_id, False),
                "capabilities": caps,
                "hooks": list(m.hooks.keys()),
                "settings_count": len(m.settings),
            }
        return result

    def _register_capabilities(self, manifest: ExtensionManifest) -> None:
        cap_reg = get_capability_registry()
        for cap in manifest.capabilities:
            if isinstance(cap, str):
                parts = cap.split(":", 1)
                cap_obj = Capability(domain=parts[0], name=parts[1] if len(parts) > 1 else "")
            else:
                cap_obj = cap
            cap_reg.register(manifest.id, cap_obj)

    def _check_dependencies(self, manifest: ExtensionManifest) -> list[str]:
        missing = []
        for dep in manifest.dependencies:
            if dep in self._extensions:
                continue
            cap_reg = get_capability_registry()
            if ":" in dep:
                domain, name = dep.split(":", 1)
                if cap_reg.has(domain, name):
                    continue
            elif cap_reg.find(dep):
                continue
            missing.append(dep)
        return missing

    @property
    def count(self) -> int:
        return len(self._extensions)

    @property
    def failed_count(self) -> int:
        return len(self._failed)

    def get_errors(self) -> dict[str, str]:
        return dict(self._failed)


_registry: ExtensionRegistry | None = None


def get_extension_registry() -> ExtensionRegistry:
    global _registry
    if _registry is None:
        _registry = ExtensionRegistry()
    return _registry
