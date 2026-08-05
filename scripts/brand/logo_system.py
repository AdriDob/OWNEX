"""
OWNEX TESLA Logo System — deterministic SVG components.
Single source of truth for the O+X mark across all visuals.
"""

from __future__ import annotations

# ─── Palette (from frontend/src/design/tokens.css) ───
C = {
    "bg": "#000000",
    "fg": "#F5F5F5",
    "muted_fg": "#9CA3AF",
    "muted": "#6B7280",
    "accent": "#00D5FF",  # OWNEX blue — ONLY saturated color
    "accent_hover": "#1E40FF",
    "border": "#2A2A2A",
    "border_light": "#3A3A3A",
    "surface": "#111111",
    "surface_hover": "#1A1A1A",
    "success": "#10B981",
    "warning": "#F59E0B",
    "c_security": "#00D5FF",  # Blue for security
    "c_forge": "#1E40FF",  # Dark blue for forge
    "c_pulse": "#10B981",
    "c_vault": "#8B5CF6",
    "c_atlas": "#06B6D4",
    "c_odyssey": "#EC4899",
}

FONT_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Fira Code', monospace"


def txt(
    x: float,
    y: float,
    s: str,
    size: float,
    fill: str,
    weight: int = 400,
    family: str = FONT_SANS,
    anchor: str = "start",
    ls: str = "0",
) -> str:
    s = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
        f'letter-spacing="{ls}" dominant-baseline="alphabetic">{s}</text>'
    )


def rect(x: float, y: float, w: float, h: float, fill: str, rx: float = 0, stroke: str = "none", sw: float = 0) -> str:
    attrs = f'x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"'
    if rx:
        attrs += f' rx="{rx}"'
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{sw}"'
    return f"<rect {attrs}/>"


def circle(cx: float, cy: float, r: float, fill: str, stroke: str = "none", sw: float = 0) -> str:
    attrs = f'cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"'
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{sw}"'
    return f"<circle {attrs}/>"


def mark_svg_alpha(size: float = 512, fill: str = C["accent"], bg: str | None = C["bg"], with_bg: bool = True) -> str:
    """
    OWNEX ALPHA mark: O ring (blue).
    Returns standalone SVG string with viewbox matching size.
    """
    # radius scales with size; keep 2:1 ratio
    r = size / 2
    stroke_w = size / 64  # thin stroke, scales
    viewbox = size

    g = f'<svg width="{size}" height="{size}" viewBox="0 0 {viewbox} {viewbox}" xmlns="http://www.w3.org/2000/svg">'
    if with_bg and bg:
        g += rect(0, 0, size, size, bg)
    # ring (O)
    g += f'<circle cx="{size / 2}" cy="{size / 2}" r="{r - stroke_w / 2}" fill="none" stroke="{fill}" stroke-width="{stroke_w}" />'
    g += "</svg>"
    return g


def mark_svg_omega(size: float = 512, fill: str = C["accent"], bg: str | None = C["bg"], with_bg: bool = True) -> str:
    """
    OWNEX OMEGA mark: X arms (blue).
    Returns standalone SVG string with viewbox matching size.
    """
    # X geometry: arms cross at center
    arm_w = size / 32  # arm thickness
    viewbox = size

    g = f'<svg width="{size}" height="{size}" viewBox="0 0 {viewbox} {viewbox}" xmlns="http://www.w3.org/2000/svg">'
    if with_bg and bg:
        g += rect(0, 0, size, size, bg)
    # X1
    g += f'<line x1="{size / 64}" y1="{size / 64}" x2="{size - size / 64}" y2="{size - size / 64}" stroke="{fill}" stroke-width="{arm_w}" stroke-linecap="round"/>'
    # X2
    g += f'<line x1="{size - size / 64}" y1="{size / 64}" x2="{size / 64}" y2="{size - size / 64}" stroke="{fill}" stroke-width="{arm_w}" stroke-linecap="round"/>'
    g += "</svg>"
    return g


def lockup_svg(width: float = 800, height: float = 160) -> str:
    """
    ALPHA | OMEGA lockup: side-by-side marks with wordmark below.
    Returns a standalone SVG of the complete lockup (no background).
    """
    mark_size = 120
    alpha = mark_svg_alpha(size=mark_size, fill=C["accent"], with_bg=False)
    omega = mark_svg_omega(size=mark_size, fill=C["accent"], with_bg=False)

    # replace root SVG tags with g groups for inline composition
    alpha_g = alpha.replace("<svg", "<g").replace("</svg>", "</g>")
    omega_g = omega.replace("<svg", "<g").replace("</svg>", "</g>")

    # layout: ALPHA mark left, OMEGA mark right, wordmark below center
    logo_w = width
    logo_h = height
    gap = width * 0.12
    mark_offset_y = (logo_h - mark_size) / 2
    word_y = logo_h * 0.85

    g = f'<svg width="{logo_w}" height="{logo_h}" viewBox="0 0 {logo_w} {logo_h}" xmlns="http://www.w3.org/2000/svg">'
    g += f'<g transform="translate({gap / 2}, {mark_offset_y})">{alpha_g}</g>'
    g += f'<g transform="translate({logo_w - mark_size - gap / 2}, {mark_offset_y})">{omega_g}</g>'
    g += txt(logo_w / 2, word_y, "OWNEX", 48, C["fg"], 700, ls="-0.02em")
    g += txt(logo_w / 2, word_y + 60, "The personalized autonomous operating system", 20, C["muted_fg"])
    g += "</svg>"
    return g
