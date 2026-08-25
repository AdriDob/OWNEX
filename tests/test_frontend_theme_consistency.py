"""Theme consistency guards — single red + dark-blue ambient background.

Owner decision (2026-08-25): the global ambient background layer is DARK
BLUE; Tesla red (#E82127) is reserved for error/destructive states only.

Regression context: --ownex-red was mislabeled as cyan (#00d5ff) in
tokens.css while themes/tesla.json set it to #E82127 at runtime — every
error indicator silently flipped color after theme load, and
JarvisBackground painted a permanent reddish tint over all pages.
"""

from __future__ import annotations

import json
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
TESLA_RED = "#E82127"


def test_tokens_red_is_tesla_red_not_cyan() -> None:
    tokens = (FRONTEND / "src" / "design" / "tokens.css").read_text(encoding="utf-8")
    line = next(ln for ln in tokens.splitlines() if "--ownex-red:" in ln)
    assert TESLA_RED in line, f"--ownex-red must be {TESLA_RED}, got: {line.strip()}"
    assert "#00d5ff" not in line, "red token must not be cyan (de-neón artifact)"


def test_default_theme_agrees_with_tokens() -> None:
    theme = json.loads(
        (FRONTEND / "public" / "assets" / "branding" / "themes" / "tesla.json").read_text(encoding="utf-8")
    )
    palette = theme.get("palette", {})
    assert palette.get("red", "").upper() == TESLA_RED


def test_ambient_background_has_no_red() -> None:
    """The global background layer is dark blue — zero red references."""
    src = (FRONTEND / "src" / "components" / "JarvisBackground.vue").read_text(encoding="utf-8")
    assert "227, 25, 55" not in src and "e31937" not in src.lower()
    assert "accent-primary" not in src, "background must not depend on legacy jarvis vars"
    # Owner directive: dark blue ambient
    assert "30, 64, 255" in src


def test_legacy_jarvis_theme_not_imported_into_global_layers() -> None:
    """JarvisBackground must be self-contained; main.ts may keep the legacy
    stylesheet for its remaining page-local consumers only."""
    bg = (FRONTEND / "src" / "components" / "JarvisBackground.vue").read_text(encoding="utf-8")
    assert "--gradient-primary" not in bg and ".btn-primary" not in bg
