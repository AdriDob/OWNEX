#!/usr/bin/env python3
"""OWNEX hero banner + OpenGraph social preview generator.

Same visual language as the logo system: space black, white text,
Tesla red as the only saturated accent. Deterministic, reproducible.

Composition: geometric SVG (no <text> — cairosvg cannot render fonts),
text composited with PIL using vendored fonts, same as the logo pipeline.
"""

from __future__ import annotations

import math
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT_B = ROOT / "docs" / "assets" / "branding" / "banners"
OUT_S = ROOT / "docs" / "assets" / "branding" / "social"
FONTS = ROOT / "assets" / "branding" / "fonts"
OUT_B.mkdir(parents=True, exist_ok=True)
OUT_S.mkdir(parents=True, exist_ok=True)

BLACK = "#05060A"
GRID = "#0B0C10"
STROKE = "#262B35"
WHITE = "#F6F8FB"
MUTED = "#8B8D98"
DEEP_BLUE = "#1E40FF"


def _font(name: str, weight: int, px: float):
    from PIL import ImageFont

    return ImageFont.truetype(str(FONTS / f"{name}-{weight}.ttf"), int(round(px)))


def _draw(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    name: str,
    weight: int,
    px: float,
    fill: str,
    tracking: float = 0,
    mid: bool = True,
) -> None:
    f = _font(name, weight, px)
    spacing = int(round(tracking * px / 1000))
    widths = [draw.textlength(ch, font=f) + spacing for ch in text[:-1]]
    total = sum(widths) + draw.textlength(text[-1], font=f)
    x0 = xy[0] - total / 2 if mid else xy[0]
    y0 = xy[1] - px * 0.72 if mid else xy[1]
    for _, ch in enumerate(text):
        draw.text((x0, y0), ch, font=f, fill=fill)
        x0 += draw.textlength(ch, font=f) + spacing


def _mark(cx: float, cy: float, r: float, stroke: float, color: str) -> str:
    parts = []
    n = 8
    gap_start = 45.0 - 9.0
    for i in range(n):
        a0 = i * (360.0 / n)
        a1 = a0 + (360.0 / n)
        center = (a0 + a1) / 2
        if abs(((center - gap_start + 180) % 360) - 180) < 22:
            continue
        x0 = cx + r * math.cos(math.radians(a0))
        y0 = cy + r * math.sin(math.radians(a0))
        x1 = cx + r * math.cos(math.radians(a1))
        y1 = cy + r * math.sin(math.radians(a1))
        parts.append(
            f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{color}" stroke-width="{stroke:.1f}" stroke-linecap="round"/>'
        )
    length = r * 0.80
    parts.append(
        f'<rect x="{cx - stroke / 2:.1f}" y="{cy - length:.1f}" width="{stroke:.1f}" height="{2 * length:.1f}" rx="{stroke / 2:.1f}" fill="{color}" transform="rotate(45 {cx} {cy})"/>'
    )
    parts.append(
        f'<rect x="{cx - stroke / 2:.1f}" y="{cy - length:.1f}" width="{stroke:.1f}" height="{2 * length:.1f}" rx="{stroke / 2:.1f}" fill="{color}" transform="rotate(-45 {cx} {cy})"/>'
    )
    nx = cx + r * 1.10
    ny = cy - r * 1.10
    parts.append(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{stroke * 0.66:.1f}" fill="{DEEP_BLUE}"/>')
    parts.append(
        f'<rect x="{cx - 4.2}" y="{cy - 4.2}" width="8.4" height="8.4" fill="{color}" transform="rotate(45 {cx} {cy})"/>'
    )
    return "".join(parts)


def _grid(w: int, h: int) -> str:
    subtle = ""
    for i in range(14):
        x = 60 + i * ((w - 120) / 13)
        subtle += f'<line x1="{x:.0f}" y1="40" x2="{x:.0f}" y2="{h - 40}" stroke="{GRID}" stroke-width="1"/>'
    for i in range(5):
        y = 40 + i * ((h - 80) / 3)
        subtle += f'<line x1="40" y1="{y:.0f}" x2="{w - 40}" y2="{y:.0f}" stroke="{GRID}" stroke-width="1"/>'
    return subtle


def hero_banner_svg() -> str:
    width, height = 2400, 900
    r, stroke = 230, 28
    cx, cy = 1200, 360
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="{width}" height="{height}" fill="{BLACK}"/>
{_grid(width, height)}
<rect x="60" y="60" width="{width - 120}" height="{height - 120}" rx="24" fill="none" stroke="{STROKE}" stroke-width="1.5"/>
<g>{_mark(cx, cy, r, stroke, WHITE)}</g>
</svg>"""


def hero_banner_png() -> None:
    svg = hero_banner_svg().encode()
    png = OUT_B / "ownex-hero-banner.png"
    cairosvg.svg2png(bytestring=svg, write_to=str(png), output_width=2400, output_height=900)
    img = Image.open(png).convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = 2400, 900
    cx, cy = w / 2, 360
    y0 = cy + 235
    _draw(d, (cx, y0 + 100), "OWNEX", "SpaceGrotesk", 700, 150, WHITE, tracking=-4)
    _draw(d, (cx, y0 + 225), "PERSONAL AUTONOMOUS WORK OPERATING SYSTEM", "JetBrainsMono", 400, 22, MUTED, tracking=6)
    d.rectangle([cx - 760, y0 + 285, cx + 760, y0 + 287], fill=STROKE)
    d.ellipse([cx - 4, y0 + 278.5, cx + 4, y0 + 286.5], fill=DEEP_BLUE)
    _draw(d, (cx, y0 + 345), "Discovery  ·  Orchestration  ·  Execution  ·  Evolution", "Inter", 400, 26, MUTED)
    _draw(d, (176, h - 78), "v7.0.0 — Python · FastAPI · Vue 3 · Tauri v2", "JetBrainsMono", 400, 20, MUTED, mid=False)
    _draw(d, (w - 150, h - 78), "EST. 2026", "JetBrainsMono", 400, 20, MUTED)
    img.alpha_composite(layer)
    img.save(png)
    Path(str(png).replace(".png", ".svg")).write_text(hero_banner_svg())


def social_svg() -> str:
    width, height = 1200, 630
    cx, cy, r, stroke = 330, 315, 150, 19
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="{width}" height="{height}" fill="{BLACK}"/>
{_grid(width, height)}
<rect x="40" y="40" width="{width - 80}" height="{height - 80}" rx="20" fill="none" stroke="{STROKE}" stroke-width="1.5"/>
<g>{_mark(cx, cy, r, stroke, WHITE)}</g>
</svg>"""


def social_png() -> None:
    svg = social_svg().encode()
    png = OUT_S / "ownex-social-preview.png"
    cairosvg.svg2png(bytestring=svg, write_to=str(png), output_width=1200, output_height=630)
    img = Image.open(png).convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = 1200, 630
    _draw(d, (620, 230), "OWNEX", "SpaceGrotesk", 700, 92, WHITE, tracking=-3)
    _draw(d, (622, 305), "PERSONAL AUTONOMOUS WORK OS", "JetBrainsMono", 400, 19, MUTED, tracking=4)
    d.rectangle([620, 355, 900, 357], fill=STROKE)
    _draw(d, (620, 425), "Discovery · Orchestration · Execution · Evolution", "Inter", 400, 23, MUTED)
    _draw(d, (620, 465), "Python · FastAPI · Vue 3 · Tauri v2 · v7.0.0", "Inter", 400, 18, MUTED)
    d.ellipse([w - 118, h - 97, w - 98, h - 77], fill=DEEP_BLUE)
    img.alpha_composite(layer)
    img.save(png)
    Path(str(png).replace(".png", ".svg")).write_text(social_svg())


def main() -> None:
    hero_banner_png()
    social_png()
    print("banner + social OK")


if __name__ == "__main__":
    main()
