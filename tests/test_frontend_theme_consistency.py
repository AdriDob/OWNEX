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


RED_HEXES = ("#E82127", "#E31937", "#D01E23", "#FF4D6A")


def _strip_comments(css: str) -> str:
    import re

    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def test_accent_token_is_defined_and_not_red() -> None:
    """--ownex-accent must resolve (no dangling/self-ref) and contain zero red.

    Regression: the token was once referenced but never defined (dead accent
    across the UI), then briefly set to Tesla red against the zero-red rule.
    """
    tokens = _strip_comments((FRONTEND / "src" / "design" / "tokens.css").read_text(encoding="utf-8"))
    line = next(ln for ln in tokens.splitlines() if "--ownex-accent:" in ln)
    value = line.split(":", 1)[1]
    assert "var(--ownex-accent)" not in value, f"self-referential accent: {line.strip()}"
    for hx in RED_HEXES:
        assert hx not in value.upper(), f"rojo prohibido en accent: {line.strip()}"


def test_cycle_odyssey_has_no_red() -> None:
    """Odyssey follows the accent (blue family), never Tesla red."""
    tokens = _strip_comments((FRONTEND / "src" / "design" / "tokens.css").read_text(encoding="utf-8"))
    line = next(ln for ln in tokens.splitlines() if "--ownex-cycle-odyssey:" in ln)
    for hx in RED_HEXES:
        assert hx not in line.upper(), f"rojo prohibido en odyssey: {line.strip()}"


def test_no_dead_stylesheets_shipped() -> None:
    """Stylesheets with zero importers must not linger (dead gradients/glows)."""
    for dead in ("styles/ownex-theme.css", "styles/special-effects.css"):
        assert not (FRONTEND / "src" / dead).exists(), f"dead stylesheet still present: {dead}"


def test_no_dead_voice_component() -> None:
    """VoiceAssistantRecorder was unmounted with zero importers (Listener+Panel live)."""
    assert not (FRONTEND / "src" / "components" / "voice" / "VoiceAssistantRecorder.vue").exists()
