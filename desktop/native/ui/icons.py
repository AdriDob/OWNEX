"""Native icon registry — maps semantic names to SVG resources.

Consumes vendored assets under ``assets/logos/`` (OWNEX "aperture nexus"
mark + wordmark). No external icon fonts; everything is a local SVG file so
the shipped app has zero runtime web dependencies for icons.

Resolution order:
  1. PyInstaller bundle: ``sys._MEIPASS`` relative path.
  2. Repository source: ``_REPO_ROOT / "assets/logos/"`` (for dev).
  3. Fallback: ``None`` (caller renders a placeholder glyph).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_svg(name: str) -> str | None:
    """Resolve an SVG icon path with bundle-aware priority.

    1. PyInstaller bundle: ``sys._MEIPASS`` / ``assets/logos/{name}.svg``
    2. Repository source: ``_REPO_ROOT / "assets/logos/{name}.svg"`` (dev)
    3. Fallback: ``None`` (caller renders placeholder glyph)
    """
    # Bundle mode takes priority
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        p = Path(meipass) / "assets/logos" / f"{name}.svg"
        if p.is_file():
            return str(p)
    # Dev mode fallback
    p = _REPO_ROOT / "assets/logos" / f"{name}.svg"
    if p.is_file():
        return str(p)
    return None


# Primary app icon (mark + wordmark variants).
# Uses the bundle-aware resolver so icons work both in dev and in the PyInstaller bundle.
RASTRO_ICON_PATH = _resolve_svg("app")
RASTRO_MARK_PATH = _resolve_svg("app")

# Semantic icon -> SVG path. These resolve to local files so the UI never
# depends on a remote icon font. Missing icons are None (caller renders a
# fallback placeholder glyph).
SEMANTIC_ICONS: dict[str, str | None] = {
    "app": RASTRO_ICON_PATH,
    "target": _resolve_svg("target"),
    "finding": _resolve_svg("finding"),
    "report": _resolve_svg("report"),
    "terminal": _resolve_svg("terminal"),
    "intelligence": _resolve_svg("intelligence"),
    "automation": _resolve_svg("automation"),
    "system": _resolve_svg("system"),
    "settings": _resolve_svg("settings"),
    "activity": _resolve_svg("activity"),
    "opportunity": _resolve_svg("opportunity"),
}
