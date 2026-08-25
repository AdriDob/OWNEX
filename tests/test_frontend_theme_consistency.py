"""Theme consistency guards — ZERO red, blue-family only (danger incl.).

Owner decision (2026-08-25, revoca directiva anterior): la UI NO usa rojo en
absoluto — solo azules claros u oscuros. El peligro/error usa el azul fuerte
#3B82F6. El nombre `--ownex-red` sobrevive como alias legacy para sus ~15
consumidores hasta la migración de nombres.

Historial: (a) --ownex-red fue cian por artefacto de-neón; (b) se reservó
rojo Tesla #E82127 para error; (c) HOY: rojo eliminado por completo.
"""

from __future__ import annotations

import json
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
DANGER_BLUE = "#3B82F6"


def test_tokens_danger_is_blue_not_red() -> None:
    tokens = (FRONTEND / "src" / "design" / "tokens.css").read_text(encoding="utf-8")
    line = next(ln for ln in tokens.splitlines() if "--ownex-danger:" in ln)
    assert DANGER_BLUE in line, f"--ownex-danger must be {DANGER_BLUE}, got: {line.strip()}"
    assert "#E82127" not in line.upper().replace(DANGER_BLUE.upper(), ""), "rojo prohibido"
    assert "#00d5ff" not in line, "danger no debe ser el cian de accent"


def test_default_theme_agrees_with_tokens() -> None:
    theme = json.loads(
        (FRONTEND / "public" / "assets" / "branding" / "themes" / "tesla.json").read_text(encoding="utf-8")
    )
    palette = theme.get("palette", {})
    assert palette.get("red", "").upper() == DANGER_BLUE


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
