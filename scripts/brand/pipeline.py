"""OWNEX brand pipeline — deterministic vector identity system.

Generates the full OWNEX brand system (mark, lockups, banners, concepts)
from exact geometry + design tokens. No randomness: every output is
reproducible from this module.

Toolchain: Python + cairosvg + fontTools/PIL (all open source).
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
BRAND = ASSETS / "branding"
FONTS = BRAND / "fonts"
LOGOS = ASSETS / "logos"
BANNERS = ASSETS / "banners"
CONCEPTS = ASSETS / "concepts"
DESKTOP = ASSETS / "desktop"
MOBILE = ASSETS / "mobile"

TOKENS = json.loads((BRAND / "design-tokens.json").read_text())
C = {k: v["hex"] for k, v in TOKENS["color_system"].items()}

SIZE = 512
CX = CY = SIZE / 2

# ---------------------------------------------------------------------------
# Mark geometry — "The Aperture Nexus"
# ---------------------------------------------------------------------------

OCT_R = 208  # octagon circumradius
OCT_SW = 15  # ring stroke width
RAY_R_EDGE = 196  # rays ending at ring inner edge
RAY_R_BREAK = 258  # breaking ray length (through aperture gap)
RAY_R_CORE = 26  # ray start radius (narrow center)
RAY_W_CORE = 30  # ray width at center
RAY_W_TIP = 78  # ray width at tip
NODE = 46  # central node square size

# Octagon vertex angles (deg, from +x, CCW); y-flipped for SVG later.
OCT_ANGLES = [22.5 + 45 * k for k in range(8)]


def pt(angle_deg: float, radius: float, cx: float = CX, cy: float = CY) -> tuple[float, float]:
    a = math.radians(angle_deg)
    return (cx + radius * math.cos(a), cy - radius * math.sin(a))


def octagon_segments(radius: float) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """7 segments (top-right one open — the aperture gap)."""
    segs = []
    for i in range(8):
        a1, a2 = OCT_ANGLES[i], OCT_ANGLES[(i + 1) % 8]
        if {round(a1, 1), round(a2, 1)} == {round(22.5, 1), round(67.5, 1)}:
            continue
        segs.append((pt(a1, radius), pt(a2, radius)))
    return segs


def ray_quad(
    angle_deg: float, r_tip: float, core: float = RAY_R_CORE, w_core: float = RAY_W_CORE, w_tip: float = RAY_W_TIP
) -> str:
    """Tapered ray: narrow at core, wide at tip. Returns polygon points."""
    a = math.radians(angle_deg)
    nx, ny = -math.sin(a), -math.cos(a)  # perpendicular (y-flipped space)
    x0, y0 = CX + core * math.cos(a), CY - core * math.sin(a)
    x1, y1 = CX + r_tip * math.cos(a), CY - r_tip * math.sin(a)
    hc, ht = w_core / 2, w_tip / 2
    p = [
        (x0 + hc * nx, y0 + hc * ny),
        (x1 + ht * nx, y1 + ht * ny),
        (x1 - ht * nx, y1 - ht * ny),
        (x0 - hc * nx, y0 - hc * ny),
    ]
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in p)


def mark_defs(variant: str = "alpha") -> str:
    cyan, blue = C["cyber_cyan"], C["deep_blue"]
    if variant == "omega":
        cyan, blue = C["emerald"], C["cyber_cyan"]
    return f"""
  <defs>
    <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{cyan}"/>
      <stop offset="100%" stop-color="{blue}"/>
    </linearGradient>
    <linearGradient id="rayGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{cyan}"/>
      <stop offset="100%" stop-color="{blue}"/>
    </linearGradient>
  </defs>"""


def mark_group(variant: str = "alpha", mono: str | None = "white", bold: bool = False) -> str:
    """Core mark group on transparent canvas. mono: 'white' | 'black' | None."""
    m = 2.0 if bold else 1.0
    oct_sw, ray_wc, ray_wt, node = OCT_SW * m, RAY_W_CORE * m, RAY_W_TIP * m, NODE * m
    fill = "#FFFFFF" if mono == "white" else ("#05060A" if mono == "black" else "url(#rayGrad)")
    ring = "#FFFFFF" if mono == "white" else ("#05060A" if mono == "black" else "url(#ringGrad)")
    node_fill = "#FFFFFF" if mono == "white" else ("#05060A" if mono == "black" else "#FFFFFF")

    segs = octagon_segments(OCT_R)
    pts = []
    for p1, p2 in segs:
        if not pts:
            pts.append(p1)
        pts.append(p2)
    ring_path = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in pts)

    rays = []
    # breaking ray along 45° (through aperture), opposite arm along 225°
    rays.append(ray_quad(45, RAY_R_BREAK, w_core=ray_wc, w_tip=ray_wt))
    rays.append(ray_quad(225, RAY_R_EDGE, w_core=ray_wc, w_tip=ray_wt))
    # second axis 135° / 315°
    rays.append(ray_quad(135, RAY_R_EDGE, w_core=ray_wc, w_tip=ray_wt))
    rays.append(ray_quad(315, RAY_R_EDGE, w_core=ray_wc, w_tip=ray_wt))

    node_rect = (
        f'<rect x="{CX - node / 2:.1f}" y="{CY - node / 2:.1f}" width="{node}" height="{node}" fill="{node_fill}"/>'
    )

    rays_svg = "".join(f'<polygon points="{p}" fill="{fill}" fill-opacity="1"/>' for p in rays)
    return f"""
  <g id="ownex-mark">
    {rays_svg}
    <path d="{ring_path}" fill="none" stroke="{ring}" stroke-width="{oct_sw}" stroke-linejoin="miter"/>
    {node_rect}
  </g>"""


def mark_svg(
    variant: str = "alpha", mono: str | bool = False, size: int = SIZE, bg: str | None = None, bold: bool = False
) -> str:
    mono_out: str | None = "white" if mono is True else (mono or None)
    bg_rect = f'<rect width="{size}" height="{size}" fill="{bg}"/>' if bg else ""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">
  {bg_rect}{mark_defs(variant)}
  <g transform="scale({size / SIZE})">
    {mark_group(variant, mono_out, bold)}
  </g>
</svg>"""
    return svg


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def svg_to_png(svg: str, out: Path, width: int) -> None:
    import cairosvg

    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(out), output_width=width)


def font(name: str, weight: int, px: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"{name}-{weight}.ttf"), int(round(px)))


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    fname: str,
    weight: int,
    px: float,
    fill: str,
    tracking: float = 0,
    anchor_mid: bool = True,
    alpha: int = 255,
) -> None:
    """Text with letter-spacing. anchor_mid → xy is the text center."""
    f = font(fname, weight, px)
    spacing = int(round(tracking * px / 1000))
    widths = [draw.textlength(ch, font=f) + spacing for ch in text]
    total = sum(widths[:-1]) + draw.textlength(text[-1], font=f) if text else 0
    x0 = xy[0] - total / 2 if anchor_mid else xy[0]
    y0 = xy[1] - px * 0.72 if anchor_mid else xy[1]
    fill_rgba = fill if alpha >= 255 else fill + f"{alpha:02X}"
    for ch, w in zip(text, widths):
        draw.text((x0, y0), ch, font=f, fill=fill_rgba)
        x0 += w


def draw_text_left(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    fname: str,
    weight: int,
    px: float,
    fill: str,
    tracking: float = 0,
    alpha: int = 255,
) -> None:
    f = font(fname, weight, px)
    spacing = int(round(tracking * px / 1000))
    x = xy[0]
    for ch in text:
        draw.text((x, xy[1]), ch, font=f, fill=fill if alpha >= 255 else fill + f"{alpha:02X}")
        x += draw.textlength(ch, font=f) + spacing


def render(svg: str, out: Path, width: int = 1024, text_fn=None, text_scale: float | None = None) -> Path:
    """Render SVG → PNG, optionally compositing PIL text on top.

    `<text>` elements are stripped before rasterizing (cairosvg renders
    them in a fallback font); PIL text provides the pixel-exact type.
    """
    import re

    out.parent.mkdir(parents=True, exist_ok=True)
    svg_notext = re.sub(r"<text\b[^>]*>.*?</text>", "", svg, flags=re.S)
    svg_to_png(svg_notext, out, width)
    if text_fn:
        img = Image.open(out).convert("RGBA")
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        s = width / 512 if text_scale is None else text_scale
        text_fn(d, s)
        img.alpha_composite(layer)
        img.save(out)
    return out


def view(path: Path) -> None:
    """Open the rendered asset for human inspection."""
    subprocess.run(["xdg-open", str(path)])


if __name__ == "__main__":
    print("OWNEX pipeline OK", C)
