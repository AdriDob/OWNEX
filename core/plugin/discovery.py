"""Shared plugin discovery — directory scanning + manifest loading.

Both AppRegistry and ExtensionRegistry use this to avoid duplicating
the ``iterdir() → manifest.py → import → validate`` pattern.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

logger = logging.getLogger("orion.core.plugin.discovery")


def discover_manifests(
    directory: Path,
    package: str,
    manifest_type: type[T],
    *,
    attr_name: str = "manifest",
    exclude_prefixes: tuple[str, ...] = ("_", "."),
) -> dict[str, T]:
    """Scan ``directory`` for subdirs containing a ``manifest.py``,
    import each, validate its manifest attribute, and return ``{id: manifest}``.
    """
    manifests: dict[str, T] = {}
    if not directory.is_dir():
        logger.info("Directory not found: %s", directory)
        return manifests

    for entry in sorted(directory.iterdir()):
        if not entry.is_dir() or entry.name.startswith(exclude_prefixes):
            continue
        manifest_file = entry / "manifest.py"
        if not manifest_file.exists():
            continue
        try:
            mod = importlib.import_module(f"{package}.{entry.name}.{attr_name}")
            manifest: T = getattr(mod, attr_name, None)  # type: ignore
            if manifest is None:
                logger.warning("%s/manifest.py has no '%s' variable", entry.name, attr_name)
                continue
            if hasattr(manifest, "_path"):
                manifest._path = str(entry)  # type: ignore
            manifests[getattr(manifest, "id", entry.name)] = manifest
            logger.info("Discovered: %s v%s", getattr(manifest, "name", entry.name), getattr(manifest, "version", "?"))
        except Exception as exc:
            logger.error("Failed to load manifest from %s: %s", entry.name, exc)

    return manifests
