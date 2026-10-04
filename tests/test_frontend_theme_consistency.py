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
    # NOTA: `styles/accessibility.css` tiene 0 importadores pero NO es un fichero
    # muerto — `.skip-nav` se usa en 1 .vue y sólo ese fichero lo define (no es
    # clase de Tailwind). Está NO IMPORTADO, no muerto: ver KNOWN_DEBT. Corregirlo
    # cambia la accesibilidad visible, así que no se decide en un guard.
    for dead in ("styles/ownex-theme.css", "styles/special-effects.css"):
        assert not (FRONTEND / "src" / dead).exists(), f"dead stylesheet still present: {dead}"


def test_no_dead_voice_component() -> None:
    """VoiceAssistantRecorder was unmounted with zero importers (Listener+Panel live)."""
    assert not (FRONTEND / "src" / "components" / "voice" / "VoiceAssistantRecorder.vue").exists()


# ─────────────────────────────────────────────────────────────────────────
# Audit 2026-09-30 (FASE −1 / C4): el guard de cero-rojo tenía un agujero
#
# RED_HEXES ya listaba #FF4D6A, pero ningún test abría
# `frontend/src/styles/tesla-jarvis-theme.css`. Ese fichero SÍ se importa
# globalmente (`main.ts:9`), define `--gradient-primary` con `#ff4d6a`, y
# ese gradiente lo consume `.progress-fill`, usado por 4 .vue. Es decir: la
# directiva "cero rojo en la UI" estaba violada, en producción, sin cobertura.
# ─────────────────────────────────────────────────────────────────────────

_STYLESHEETS = sorted((FRONTEND / "src").rglob("*.css"))


def _hexes(css: str) -> set[str]:
    import re

    return {h.upper() for h in re.findall(r"#[0-9a-fA-F]{3,8}\b", css)}


def test_no_red_in_any_live_stylesheet() -> None:
    """Cero rojo en TODOS los stylesheets bajo frontend/src, no sólo en tokens.css.

    El guard anterior sólo abría `tokens.css`, `tesla.json` y
    `JarvisBackground.vue`. Un stylesheet importado globalmente podía usar
    `#ff4d6a` sin que nadie lo notara — y lo usaba.
    """
    assert _STYLESHEETS, "no se encontró ningún .css bajo frontend/src — el guard sería vacío"
    offenders: list[str] = []
    for path in _STYLESHEETS:
        found = _hexes(_strip_comments(path.read_text(encoding="utf-8"))) & set(RED_HEXES)
        if found:
            offenders.append(f"{path.relative_to(FRONTEND)}: {sorted(found)}")
    assert not offenders, f"rojo prohibido en la UI (directiva owner 2026-08-25): {offenders}"


def test_no_arbitrary_hex_in_vue_components() -> None:
    """Los .vue no hardcodean hex: todo el color sale de tokens.css.

    Hoy el estado es perfecto (0 hex en 100+ .vue), lo que hace el test barato
    y fuerte a la vez: cualquier hex futuro tiene que pasar por el SSOT. Se
    afirma el número de .vue escaneados para que un cambio de layout que dejara
    el glob vacío no convierta el test en verdad vacía.
    """
    tokens = {h.upper() for h in _hexes((FRONTEND / "src" / "design" / "tokens.css").read_text(encoding="utf-8"))}
    assert tokens, "tokens.css no define ningún hex — el guard sería vacío"

    vues = sorted((FRONTEND / "src").rglob("*.vue"))
    assert len(vues) > 50, f"sólo {len(vues)} .vue escaneados — el glob cambió, el guard perdió alcance"

    offenders: dict[str, list[str]] = {}
    for path in vues:
        stray = _hexes(path.read_text(encoding="utf-8", errors="ignore")) - tokens
        if stray:
            offenders[str(path.relative_to(FRONTEND))] = sorted(stray)
    assert not offenders, f"hex fuera de tokens.css en {len(offenders)} .vue (usar var(--ownex-*)): {offenders}"
