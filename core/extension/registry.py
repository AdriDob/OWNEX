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

logger = logging.getLogger("orion.core.extensions")

EXTENSIONS_DIR = Path(__file__).resolve().parent.parent.parent / "extensions"
EXTENSIONS_PACKAGE = "extensions"


class ExtensionRegistry:
    """Discovers, validates, and manages ORION extensions."""

    def __init__(self) -> None:
        self._extensions: dict[str, ExtensionManifest] = {}
        self._loaded: dict[str, bool] = {}  # extension_id → is_loaded
        self._failed: dict[str, str] = {}   # extension_id → error_message

    # ── Discovery ────────────────────────────────────

    def discover(self) -> dict[str, ExtensionManifest]:
        """Scan ``extensions/`` directory and load every manifest."""
        if not EXTENSIONS_DIR.is_dir():
            logger.info("extensions/ directory not found — skipping extension discovery")
            return self._extensions

        for entry in sorted(EXTENSIONS_DIR.iterdir()):
            if not entry.is_dir() or entry.name.startswith("_") or entry.name.startswith("."):
                continue
            manifest_path = entry / "manifest.py"
            if not manifest_path.exists():
                logger.debug("Skipping %s — no manifest.py", entry.name)
                continue
            self._load_manifest(entry.name)

        return self._extensions

    def _load_manifest(self, dir_name: str) -> None:
        try:
            mod = importlib.import_module(f"{EXTENSIONS_PACKAGE}.{dir_name}.manifest")
            manifest: ExtensionManifest = getattr(mod, "manifest", None)
            if manifest is None:
                logger.warning("%s/manifest.py has no 'manifest' variable", dir_name)
                return
            manifest._path = str(EXTENSIONS_DIR / dir_name)
            self._extensions[manifest.id] = manifest
            self._loaded[manifest.id] = False
            logger.info("Discovered extension: %s v%s", manifest.name, manifest.version)
            self._register_capabilities(manifest)
        except Exception as exc:
            logger.error("Failed to load extension %s: %s", dir_name, exc)
            self._failed[dir_name] = str(exc)

    # ── Loading ──────────────────────────────────────

    def load(self, extension_id: str) -> bool:
        """Load (activate) an extension. Registers hooks, capabilities, etc."""
        manifest = self._extensions.get(extension_id)
        if manifest is None:
            logger.warning("Extension %s not found", extension_id)
            return False

        if self._loaded.get(extension_id):
            return True

        # Check dependencies
        missing = self._check_dependencies(manifest)
        if missing:
            logger.error("Extension %s missing dependencies: %s", extension_id, missing)
            self._failed[extension_id] = f"Missing dependencies: {', '.join(missing)}"
            return False

        # Register hooks
        hook_registry = get_hook_registry()
        for hook_name, handler_path in manifest.hooks.items():
            try:
                module_path, func_name = handler_path.rsplit(".", 1)
                mod = importlib.import_module(f"{EXTENSIONS_PACKAGE}.{extension_id}.{module_path}")
                handler = getattr(mod, func_name, None)
                if handler:
                    hook_registry.register_handler(hook_name, extension_id, handler)
                    logger.debug("  Hook: %s → %s", hook_name, handler_path)
                else:
                    logger.warning("  Hook %s: handler %s not found", hook_name, handler_path)
            except Exception as exc:
                logger.warning("  Hook %s failed to load: %s", hook_name, exc)

        self._loaded[extension_id] = True
        self._failed.pop(extension_id, None)
        logger.info("Extension loaded: %s", manifest.name)
        return True

    def unload(self, extension_id: str) -> bool:
        """Unload (deactivate) an extension."""
        manifest = self._extensions.get(extension_id)
        if manifest is None:
            return False

        # Unregister hooks
        get_hook_registry().unregister_extension(extension_id)

        # Unregister capabilities
        get_capability_registry().unregister(extension_id)

        self._loaded[extension_id] = False
        logger.info("Extension unloaded: %s", manifest.name)
        return True

    def load_all(self) -> dict[str, bool]:
        """Load all discovered extensions. Returns {id: success}."""
        results = {}
        for ext_id in self._extensions:
            results[ext_id] = self.load(ext_id)
        return results

    def reload(self, extension_id: str) -> bool:
        self.unload(extension_id)
        self._extensions.pop(extension_id, None)
        self._load_manifest(extension_id)
        return self.load(extension_id)

    # ── Queries ──────────────────────────────────────

    def get(self, extension_id: str) -> ExtensionManifest | None:
        return self._extensions.get(extension_id)

    def list_extensions(self) -> list[ExtensionManifest]:
        return sorted(self._extensions.values(), key=lambda e: e.name)

    def status(self) -> dict[str, dict]:
        return {
            ext_id: {
                "name": m.name,
                "version": m.version,
                "loaded": self._loaded.get(ext_id, False),
                "capabilities": [f"{c.domain}:{c.name}" for c in m.capabilities] if isinstance(next(iter(m.capabilities), None), Capability) else m.capabilities,
                "hooks": list(m.hooks.keys()),
                "settings_count": len(m.settings),
            }
            for ext_id, m in self._extensions.items()
        }

    # ── Internal ─────────────────────────────────────

    def _register_capabilities(self, manifest: ExtensionManifest) -> None:
        cap_reg = get_capability_registry()
        for cap in manifest.capabilities:
            if isinstance(cap, str):
                # "scanner:subdomain" format
                parts = cap.split(":", 1)
                cap_obj = Capability(domain=parts[0], name=parts[1] if len(parts) > 1 else "")
            else:
                cap_obj = cap
            cap_reg.register(manifest.id, cap_obj)

    def _check_dependencies(self, manifest: ExtensionManifest) -> list[str]:
        missing = []
        for dep in manifest.dependencies:
            # Check if dep is an app_id
            from core.app_registry import get_app_registry
            app = get_app_registry().get(dep)
            if app is not None:
                continue
            # Check if dep is a capability
            cap_reg = get_capability_registry()
            if ":" in dep:
                domain, name = dep.split(":", 1)
                if cap_reg.has(domain, name):
                    continue
            elif cap_reg.find(dep):
                continue
            # Check if dep is an extension
            if dep in self._extensions:
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
