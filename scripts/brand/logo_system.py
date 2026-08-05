#!/usr/bin/env python3
"""
OWNEX TESLA Logo System — deterministic SVG components.
Single source of truth for the O+X mark across all visuals.
"""

from __future__ import annotations

from dataclasses import dataclass

# ─── Palette (from frontend/src/design/tokens.css) ───
C = {
    "bg": "#000000",
    "fg": "#F5F5F5",
    "muted_fg": "#9CA3AF",
    "muted": "#6B7280",
    "accent": "#E82127",      # Tesla red — ONLY saturated color
    "accent_hover": "#FF333D",
    "border": "#2A2A2A",
    "border_light": "#3A3A3A",
    "surface": "#111111",
    "surface_hover": "#1A1A1A",
    "success": "#10B981",
    "warning": "#F59E0B",
    "c_security": "#E82127",
    "c_forge": "#FF6B35",
    "c_pulse": "#10B981",
    "c_vault": "#8B5CF6",
    "c_atlas": "#06B6D4",
    "c_odyssey": "#EC4899",
}

FONT_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Fira Code', monospace"


def txt(x: float, y: float, s: str, size: float, fill: str,
        weight: int = 400, family: str = FONT_SANS,
        anchor: str = "start", ls: str = "0") -> str:
    s = str(s).replace("&", "&").replace("<", "<").replace(">", ">")
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
            f'letter-spacing="{ls}" dominant-baseline="alphabetic">{s}</text>')


def rect(x: float, y: float, w: float, h: float, fill: str,
         rx: float = 0, stroke: str = "none", sw: float = 0) -> str:
    attrs = f'x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"'
    if rx:
        attrs += f' rx="{rx}"'
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{sw}"'
    return f"<rect {attrs}/>"


def circle(cx: float, cy: float, r: float, fill: str,
           stroke: str = "none", sw: float = 0) -> str:
    attrs = f'cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"'
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{sw}"'
    return f"<circle {attrs}/>"


# ═══════════════════════════════════════════════════════════════════
# MARK — O+X as a single geometric unit
# Design: optical centering, 8:5 ratio ring:arms, red core at golden ratio
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MarkGeometry:
    """All proportions derived from a single unit."""
    unit: float = 4.0              # base grid unit
    ring_stroke: float = 12.0      # O ring thickness
    arm_width: float = 12.0        # X arm thickness
    arm_gap: float = 6.0           # gap at X center (optical)
    core_ratio: float = 0.17       # core radius / ring radius (≈ 1/φ)
    padding: float = 4.0           # viewBox padding

    @property
    def ring_r(self) -> float:
        return 30 * self.unit       # 120

    @property
    def arm_half_len(self) -> float:
        return self.ring_r * 1.15   # arms extend ~15% beyond ring

    @property
    def core_r(self) -> float:
        return self.ring_r * self.core_ratio

    @property
    def viewbox(self) -> float:
        return (self.ring_r + self.ring_stroke + self.padding) * 2


GEO = MarkGeometry()


def mark_svg(
    size: float = 512,
    fg: str = C["fg"],
    accent: str = C["accent"],
    bg: str = C["bg"],
    with_bg: bool = True,
    viewbox_pad: float = 0,
) -> str:
    """
    OWNEX mark: O + X unified.
    Returns standalone SVG string.
    """
    g = GEO
    ring_r = g.ring_r
    arm_half = g.arm_half_len
    arm_w = g.arm_width
    arm_gap = g.arm_gap
    core_r = g.core_r
    stroke = g.ring_stroke
    vb = g.viewbox + viewbox_pad * 2
    cx = cy = vb / 2
    scale = size / vb

    parts = [f'<svg width="{size}" height="{size}" viewBox="0 0 {vb} {vb}" '
              f'xmlns="http://www.w3.org/2000/svg">']

    if with_bg:
        parts.append(f'<rect width="{vb}" height="{vb}" fill="{bg}"/>')

    # ─── X arms: two rotated rectangles meeting at center with optical gap ───
    # Transform: rotate ±45° around center, translate to close the gap
    x_arm = (f'<rect x="{cx - arm_w/2}" y="{cy - arm_half}" '
             f'width="{arm_w}" height="{arm_half - arm_gap/2}" fill="{fg}" '
             f'transform="rotate(45 {cx} {cy})"/>')
    x_arm2 = (f'<rect x="{cx - arm_w/2}" y="{cy - arm_half}" '
              f'width="{arm_w}" height="{arm_half - arm_gap/2}" fill="{fg}" '
              f'transform="rotate(-45 {cx} {cy})"/>')
    parts.append(x_arm)
    parts.append(x_arm2)

    # ─── O ring ───
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="{ring_r}" '
        f'fill="none" stroke="{fg}" stroke-width="{stroke}" '
        f'stroke-linecap="round"/>')

    # ─── Red core at center (the only saturated pixel) ───
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{core_r}" fill="{accent}"/>')

    parts.append("</svg>")
    return "".join(parts)


# ═══════════════════════════════════════════════════════════════════
# Variants
# ═══════════════════════════════════════════════════════════════════

def mark_white_svg(size: float = 512) -> str:
    """Mark for dark backgrounds: white geometry, red core, transparent bg."""
    return mark_svg(size=size, fg="#FFFFFF", accent=C["accent"], bg="transparent", with_bg=False)


def mark_black_svg(size: float = 512) -> str:
    """Mark for light backgrounds: black geometry, red core, transparent bg."""
    return mark_svg(size=size, fg="#000000", accent=C["accent"], bg="transparent", with_bg=False)


def icon_svg(size: float = 512) -> str:
    """App icon: rounded square with mark centered."""
    g = GEO
    ring_r = g.ring_r
    stroke = g.ring_stroke
    pad = 48  # padding around mark inside square
    inner = (ring_r + stroke) * 2 + pad * 2
    cx = cy = inner / 2
    r_corner = inner * 0.1875  # 18.75% — Apple/Android standard

    parts = [f'<svg width="{size}" height="{size}" viewBox="0 0 {inner} {inner}" '
              f'xmlns="http://www.w3.org/2000/svg">']

    # background rounded square
    parts.append(f'<rect width="{inner}" height="{inner}" rx="{r_corner}" fill="{C["bg"]}"/>')

    # X arms
    arm_half = g.arm_half_len
    arm_w = g.arm_width
    arm_gap = g.arm_gap
    x_arm = (f'<rect x="{cx - arm_w/2}" y="{cy - arm_half}" '
             f'width="{arm_w}" height="{arm_half - arm_gap/2}" fill="{C["fg"]}" '
             f'transform="rotate(45 {cx} {cy})"/>')
    x_arm2 = (f'<rect x="{cx - arm_w/2}" y="{cy - arm_half}" '
              f'width="{arm_w}" height="{arm_half - arm_gap/2}" fill="{C["fg"]}" '
              f'transform="rotate(-45 {cx} {cy})"/>')
    parts.append(x_arm)
    parts.append(x_arm2)

    # O ring
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="{ring_r}" '
        f'fill="none" stroke="{C["fg"]}" stroke-width="{stroke}" '
        f'stroke-linecap="round"/>')

    # red core
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{g.core_r}" fill="{C["accent"]}"/>')

    parts.append("</svg>")
    return "".join(parts)


def favicon_svg(size: float = 32) -> str:
    """Favicon: minimal O+X, red core, no ring stroke (too thin at 32px)."""
    inner = 32
    cx = cy = 16
    ring_r = 12
    arm_half = 14
    arm_w = 3
    arm_gap = 2
    core_r = 3

    parts = [f'<svg width="{size}" height="{size}" viewBox="0 0 {inner} {inner}" '
              f'xmlns="http://www.w3.org/2000/svg">']

    parts.append(f'<rect width="{inner}" height="{inner}" fill="{C["bg"]}"/>')

    x_arm = (f'<rect x="{cx - arm_w/2}" y="{cy - arm_half}" '
             f'width="{arm_w}" height="{arm_half - arm_gap/2}" fill="{C["fg"]}" '
             f'transform="rotate(45 {cx} {cy})"/>')
    x_arm2 = (f'<rect x="{cx - arm_w/2}" y="{cy - arm_half}" '
              f'width="{arm_w}" height="{arm_half - arm_gap/2}" fill="{C["fg"]}" '
              f'transform="rotate(-45 {cx} {cy})"/>')
    parts.append(x_arm)
    parts.append(x_arm2)

    # O as thick stroke (filled circle with hole)
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="{ring_r}" '
        f'fill="{C["fg"]}"/>')
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="{ring_r - 2}" '
        f'fill="{C["bg"]}"/>')

    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{core_r}" fill="{C["accent"]}"/>')

    parts.append("</svg>")
    return "".join(parts)


def lockup_svg(width: float = 1200, height: float = 240) -> str:
    """Horizontal lockup: mark + wordmark. Optically balanced."""
    mark_size = height * 0.72
    mark_pad = 32
    text_x = mark_size + mark_pad * 2
    baseline = height * 0.62

    parts = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
              f'xmlns="http://www.w3.org/2000/svg">']

    parts.append(f'<rect width="{width}" height="{height}" fill="{C["bg"]}"/>')

    # Mark (inline, scaled)
    g = GEO
    ring_r = g.ring_r
    stroke = g.ring_stroke
    arm_half = g.arm_half_len
    arm_w = g.arm_width
    arm_gap = g.arm_gap
    core_r = g.core_r
    vb = g.viewbox
    cx = cy = vb / 2
    scale = mark_size / vb

    parts.append(f'<g transform="translate({mark_pad}, {(height - mark_size)/2}) scale({scale})">')

    # X
    x_arm = (f'<rect x="{cx - arm_w/2}" y="{cy - arm_half}" '
             f'width="{arm_w}" height="{arm_half - arm_gap/2}" fill="{C["fg"]}" '
             f'transform="rotate(45 {cx} {cy})"/>')
    x_arm2 = (f'<rect x="{cx - arm_w/2}" y="{cy - arm_half}" '
              f'width="{arm_w}" height="{arm_half - arm_gap/2}" fill="{C["fg"]}" '
              f'transform="rotate(-45 {cx} {cy})"/>')
    parts.append(x_arm)
    parts.append(x_arm2)

    # O ring
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="{ring_r}" '
        f'fill="none" stroke="{C["fg"]}" stroke-width="{stroke}" '
        f'stroke-linecap="round"/>')

    # Red core
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{core_r}" fill="{C["accent"]}"/>')
    parts.append("</g>")

    # Wordmark — tracking tightened for logotype feel
    parts.append(
        f'<text x="{text_x}" y="{baseline}" font-family="{FONT_SANS}" '
        f'font-size="{height * 0.42}" font-weight="700" fill="{C["fg"]}" '
        f'letter-spacing="-0.025em" dominant-baseline="alphabetic">OWNEX</text>')

    parts.append("</svg>")
    return "".join(parts)


# ═══════════════════════════════════════════════════════════════════
# CLI: write all variants
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    from pathlib import Path

    out = Path("assets/logos")
    out.mkdir(parents=True, exist_ok=True)

    variants = {
        "ownex-mark.svg": mark_svg(),
        "ownex-mark-white.svg": mark_white_svg(),
        "ownex-mark-black.svg": mark_black_svg(),
        "ownex-icon.svg": icon_svg(),
        "ownex-favicon.svg": favicon_svg(),
        "ownex-lockup.svg": lockup_svg(),
    }

    for name, svg in variants.items():
        (out / name).write_text(svg)
        print(f"Wrote {out/name}")

    print("✓ All logo variants written")