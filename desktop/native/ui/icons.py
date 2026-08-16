"""Native icon registry — maps semantic names to SVG resources.

Consumes vendored assets under ``assets/logos/`` (OWNEX "aperture nexus"
mark + wordmark). No external icon fonts; everything is a local SVG file so
the shipped app has zero runtime web dependencies for icons.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_svg(name: str) -> str | None:
    p = _REPO_ROOT / "assets/icons" / f"{name}.svg"
    if p.is_file():
        return str(p)
    return None


# Primary app icon (mark + wordmark variants).
RASTRO_ICON_PATH = str(_REPO_ROOT / "assets/logos/ownex-alpha.svg")
RASTRO_MARK_PATH = str(_REPO_ROOT / "assets/logos/ownex-icon.svg")

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
