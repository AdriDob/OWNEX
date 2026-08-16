"""OWNEX Design System — native token layer for PySide6/Qt.

Re-exports the curated OWNEX v3 brand tokens as Python classes so the
native GUI can consume them without touching the legacy JSON or frontend.

Single source of truth: ``assets/branding/design-tokens.json`` (unchanged).
This module is the *native projection* of those tokens into Qt.

It also provides the ``ThemeRegistry`` — 7 ThemeSpecs (1 default + 6 branded)
loaded from ``assets/branding/themes/*.json``.  The "default" theme is the
system baseline; the 6 branded themes each carry their own visual personality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Path to the single source of truth (owned by the branding pipeline).
# ---------------------------------------------------------------------------
_TOKENS_PATH = Path(__file__).resolve().parents[3] / "assets/branding/design-tokens.json"

# ---------------------------------------------------------------------------
# Brand themes loaded from ``assets/branding/themes/*.json``.
# One "default" theme (system baseline) + 6 branded themes, each with its
# own visual personality (background, accent, surfaces, text, success/warning/
# danger/decision, borders, intention).  The registry lives in
# ``ThemeRegistry`` below.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Color tokens — mapped from design-tokens.json -> #RRGGBB for Qt.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ColorToken:
    hex_value: str
    role: str


@dataclass(frozen=True)
class ColorSystem:
    space_black: ColorToken = ColorToken("#05060A", "base background")
    cyber_cyan: ColorToken = ColorToken("#00D5FF", "intelligence accent")
    deep_blue: ColorToken = ColorToken("#1E40FF", "intelligence accent")
    emerald: ColorToken = ColorToken("#00E39A", "progress accent")
    decision: ColorToken = ColorToken("#FF7A1A", "decision accent")
    surface: ColorToken = ColorToken("#111318", "surface")
    surface_alt: ColorToken = ColorToken("#1F2229", "surface alt")
    stroke: ColorToken = ColorToken("#2A2E37", "border/stroke")
    white: ColorToken = ColorToken("#FFFFFF", "on-black text")
    muted: ColorToken = ColorToken("#8B8D98", "secondary text")
    text: ColorToken = ColorToken("#F6F8FB", "primary text")


COLORS = ColorSystem()


# ---------------------------------------------------------------------------
# ThemeSpec — contrato nativo de Qt para un tema visual completo.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ThemeSpec:
    name: str
    background: str  # bg-base equivalent
    surface: str  # bg-surface equivalent
    surface_alt: str  # surface ligeramente elevada/elevated surface
    accent: str  # color de acento principal
    progress: str  # color para progreso/éxito
    decision: str  # color para decisiones / advertencias
    text: str  # texto primario
    muted: str  # texto secundario/muted
    stroke: str  # bordes/separators
    window_title: str  # título de ventana
    intention: str  # descripción breve de la intención UX del tema
    cycles: dict = field(default_factory=dict)  # cycles por segmento (security/forge/...)
    platforms: dict = field(default_factory=dict)  # platforms mapeados (hackerone/bugcrowd/...)


# ---------------------------------------------------------------------------
# 7 ThemeSpecs: 1 default (sistema baseline) + 6 branded themes.
#   • default  — baseline usada por el sistema antes de este refactor.
#   • tesla    — minimalista, monocromático, silencioso, poderoso.
#   • event_horizon — oscuro, tecnológico, ciano profundo.
#   • executive_intelligence — ejecutivo, sobrio, jerárquico.
#   • neural_flow — fluido, tecnológico, neón morado y cian.
#   • precision_lab — laboratorio, precisión instrumental.
#   • quantum_glass — glass morphism, premium, profundidad y capas.
# ---------------------------------------------------------------------------
THEMES: dict[str, ThemeSpec] = {
    "default": ThemeSpec(
        name="default",
        background="#05060A",
        surface="#111318",
        surface_alt="#1F2229",
        accent="#00D5FF",
        progress="#16A34A",
        decision="#E82127",
        text="#F6F8FB",
        muted="#8B8D98",
        stroke="#2A2E37",
        window_title="RASTRRO",
        intention="baseline del sistema RASTRO. Contraste equilibrado, acento cian suave, legibilidad óptima.",
        cycles={},
        platforms={},
    ),
    "tesla": ThemeSpec(
        name="Tesla",
        background="#050505",
        surface="#111318",
        surface_alt="#1F2229",
        accent="#FFFFFF",
        progress="#16A34A",
        decision="#E82127",
        text="#F5F5F5",
        muted="#8A8A8A",
        stroke="#1F1F1F",
        window_title="Tesla",
        intention="minimalista, monocromático, silencioso y poderoso. Contraste máximo sobre negro, acento blanco puro. Personalidad: intemporal, sin ruido visual, enfoque en el contenido.",
        cycles={
            "security": "#F5F5F5",
            "forge": "#9CA3AF",
            "pulse": "#16A34A",
            "vault": "#D97706",
            "atlas": "#D4D4D8",
            "odyssey": "#E82127",
        },
        platforms={"hackerone": "#16A34A", "bugcrowd": "#B45309"},
    ),
    "event_horizon": ThemeSpec(
        name="Event Horizon",
        background="#070A12",
        surface="#0B0F1A",
        surface_alt="#1A2535",
        accent="#00D5FF",
        progress="#00E39A",
        decision="#FF4466",
        text="#F0F8FF",
        muted="#8BA4B8",
        stroke="#142030",
        window_title="Event Horizon",
        intention="oscuro, tecnológico, ciano profundo. Fondo muy oscuro con acentos cian neon que sugieren tecnología avanzada y presencia en el límite del conocimiento. Personalidad: intenso, futurista, revela lo oculto.",
        cycles={
            "security": "#E8F4FD",
            "forge": "#8BA4B8",
            "pulse": "#00E39A",
            "vault": "#FFB800",
            "atlas": "#D4D8DD",
            "odyssey": "#FF4466",
        },
        platforms={"hackerone": "#00E39A", "bugcrowd": "#FFB800"},
    ),
    "executive_intelligence": ThemeSpec(
        name="Executive Intelligence",
        background="#0D0F11",
        surface="#121518",
        surface_alt="#1E2833",
        accent="#0066CC",
        progress="#059669",
        decision="#DC2626",
        text="#F8F8F8",
        muted="#9CA3AF",
        stroke="#1F2937",
        window_title="Executive Intelligence",
        intention="ejecutivo, sobrio y jerárquico. Paleta corporativa, acentos azules moderados, conveys authority and seriousness. Personalidad: autoridad, decisión, profesionalismo sin distracciones.",
        cycles={
            "security": "#FAFAFA",
            "forge": "#9CA3AF",
            "pulse": "#059669",
            "vault": "#D97706",
            "atlas": "#D4D4D8",
            "odyssey": "#DC2626",
        },
        platforms={"hackerone": "#059669", "bugcrowd": "#B45309"},
    ),
    "neural_flow": ThemeSpec(
        name="Neural Flow",
        background="#120712",
        surface="#1A0F1A",
        surface_alt="#25152A",
        accent="#9C64FF",
        progress="#00FFB8",
        decision="#FF4488",
        text="#F8F0FF",
        muted="#B8A0C8",
        stroke="#2A1A2A",
        window_title="Neural Flow",
        intention="fluido, tecnológico, neón morado y cian. Sugiere conectividad, flujo continuo y ideas en movimiento. Personalidad: creativo, dinámico, energético, con profundidad visual y sugerencia de redes neuronales.",
        cycles={
            "security": "#F5E8FF",
            "forge": "#B8A0C8",
            "pulse": "#00FFB8",
            "vault": "#FFB800",
            "atlas": "#D8D0DD",
            "odyssey": "#FF4488",
        },
        platforms={"hackerone": "#00FFB8", "bugcrowd": "#FFB800"},
    ),
    "precision_lab": ThemeSpec(
        name="Precision Lab",
        background="#0A0C10",
        surface="#0F1216",
        surface_alt="#1A2430",
        accent="#1E40FF",
        progress="#16A34A",
        decision="#E82127",
        text="#F0F3F8",
        muted="#8A94A8",
        stroke="#1A2028",
        window_title="Precision Lab",
        intention="laboratorio, precisión instrumental. Azules fríos, verdes de laboratorio, conveys scientific rigor and attention to detail. Personalidad: metódico, exacto, cada píxel cuenta, sin excesos.",
        cycles={
            "security": "#E8EDF5",
            "forge": "#8A94A8",
            "pulse": "#16A34A",
            "vault": "#D97706",
            "atlas": "#D4D4D8",
            "odyssey": "#E82127",
        },
        platforms={"hackerone": "#16A34A", "bugcrowd": "#B45309"},
    ),
    "quantum_glass": ThemeSpec(
        name="Quantum Glass",
        background="#0D1018",
        surface="#121822",
        surface_alt="#1A2838",
        accent="#00D5FF",
        progress="#34D399",
        decision="#F87171",
        text="#F5F8FC",
        muted="#A8B8C8",
        stroke="#FFFFFF0A",  # rgba
        window_title="Quantum Glass",
        intention="glass morphism, premium, profundidad y capas. Efecto vidrio enrarecido, acentos cian, conveys sophistication and modern luxury. Personalidad: elegante, lujoso moderno, capas sutiles que sugieren tecnología de próxima generación.",
        cycles={
            "security": "#F8FAFC",
            "forge": "#A8B8C8",
            "pulse": "#34D399",
            "vault": "#FBBF24",
            "atlas": "#E8EEF4",
            "odyssey": "#F87171",
        },
        platforms={"hackerone": "#34D399", "bugcrowd": "#FBBF24"},
    ),
}

# ---------------------------------------------------------------------------
# ThemeRegistry — singleton que gestiona el tema activo y persiste la preferencia.
# ---------------------------------------------------------------------------

_THEME_REGISTRY: ThemeRegistry | None = None


@dataclass
class ThemeRegistry:
    """Registry of all available themes and the currently active one."""

    current_name: str = "default"

    def set_current(self, name: str) -> None:
        if name not in THEMES:
            raise KeyError(f"Unknown theme: {name}")
        self.current_name = name

    def current(self) -> ThemeSpec:
        return THEMES[self.current_name]

    def names(self) -> list[str]:
        return list(THEMES.keys())

    def reset_to_default(self) -> None:
        self.current_name = "default"


def get_registry() -> ThemeRegistry:
    """Singleton accessor — creates on first call if not yet initialized."""
    global _THEME_REGISTRY
    if _THEME_REGISTRY is None:
        _THEME_REGISTRY = ThemeRegistry()
    return _THEME_REGISTRY


def get_theme(name: str = "default") -> ThemeSpec:
    """Convenience wrapper that forwards to the registry."""
    return get_registry().set_current(name) or get_registry().current()  # py: no cover


# ---------------------------------------------------------------------------
# Legacy helper — kept for backward compatibility.
# Old callers used ``COLORS.space_black`` etc.; they still work.
# ---------------------------------------------------------------------------


def _load_theme_overrides() -> dict[str, dict[str, str]]:
    """Load per-theme overrides from the legacy theme JSON files.

    Returns a mapping ``theme_name -> {token_name: hex_value}``.
    If the files cannot be read, an empty dict is returned (graceful).
    """
    import json

    themes_dir = _TOKENS_PATH.parent / "themes"
    overrides: dict[str, dict[str, str]] = {}
    if not themes_dir.is_dir():
        return overrides
    for p in themes_dir.glob("*.json"):
        try:
            data = json.loads(p.read_text())
            overrides[p.stem] = {k: v for k, v in data.items() if isinstance(v, str) and k != "name"}
        except Exception:
            continue
    return overrides


_THEME_OVERRIDES: dict[str, dict[str, str]] = _load_theme_overrides()


def get_theme_legacy(name: str = "default") -> ThemeSpec:
    """Legacy getter that applies JSON overrides on top of the ThemeSpec base.

    Kept for backward compatibility — new code should use ``get_theme()`` or
    ``ThemeRegistry``.
    """
    spec = THEMES.get(name)
    if spec is None:
        spec = THEMES["default"]
    ov = _THEME_OVERRIDES.get(name, {})
    if not ov:
        return spec
    # Apply only fields that also exist in ThemeSpec; ignore unknown keys.
    return ThemeSpec(
        name=spec.name,
        background=ov.get("space_black", spec.background) or spec.background,
        surface=ov.get("surface", spec.surface) or spec.surface,
        surface_alt=ov.get("surface_alt", spec.surface_alt) or spec.surface_alt,
        accent=ov.get("accent", spec.accent) or spec.accent,
        progress=ov.get("emerald", spec.progress) or spec.progress,
        decision=ov.get("decision", spec.decision) or spec.decision,
        text=ov.get("text", spec.text) or spec.text,
        muted=ov.get("muted", spec.muted) or spec.muted,
        stroke=ov.get("stroke", spec.stroke) or spec.stroke,
        window_title=spec.window_title,
    )
