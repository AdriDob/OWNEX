#!/usr/bin/env python3
"""OWNEX hero banner + OpenGraph social preview generator.

Same visual language as the logo system: space black, white text,
Tesla red as the only saturated accent. Deterministic, reproducible.
"""

from __future__ import annotations

import math
from pathlib import Path

import cairosvg

ROOT = Path(__file__).resolve().parents[2]
OUT_B = ROOT / "docs" / "assets" / "branding" / "banners"
OUT_S = ROOT / "docs" / "assets" / "branding" / "social"
OUT_B.mkdir(parents=True, exist_ok=True)
OUT_S.mkdir(parents=True, exist_ok=True)

BLACK = "#05060A"
STROKE = "#2A2E37"
WHITE = "#F6F8FB"
MUTED = "#8B8D98"
DEEP_BLUE = "#1E40FF"


def _mark(cx: float, cy: float, r: float, stroke: float, color: str, node: str = DEEP_BLUE) -> str:
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
    parts.append(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{stroke * 0.66:.1f}" fill="{node}"/>')
    parts.append(
        f'<rect x="{cx - 4.2}" y="{cy - 4.2}" width="8.4" height="8.4" fill="{color}" transform="rotate(45 {cx} {cy})"/>'
    )
    return "".join(parts)


def hero_banner() -> str:
    width, height = 2400, 900
    r, stroke = 132, 17
    subtle = ""
    for i in range(14):
        x = 60 + i * 170
        subtle += f'<line x1="{x}" y1="0" x2="{x}" y2="{height}" stroke="#0B0C10" stroke-width="1"/>'
    for i in range(7):
        y = 60 + i * 130
        subtle += f'<line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="#0B0C10" stroke-width="1"/>'
    svg = f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="{width}" height="{height}" fill="{BLACK}"/>
{subtle}
<rect x="60" y="60" width="{width - 120}" height="{height - 120}" rx="24" fill="none" stroke="{STROKE}" stroke-width="1.5"/>
<g>{_mark(272, 450, r, stroke, WHITE)}</g>
<g fill="{WHITE}">
<text x="330" y="430" font-family="'Space Grotesk','Inter',sans-serif" font-size="118" font-weight="600" letter-spacing="-3">OWNEX</text>
<text x="334" y="500" font-family="'JetBrains Mono','Fira Code',monospace" font-size="26" letter-spacing="6" fill="{MUTED}">PERSONAL AUTONOMOUS WORK OPERATING SYSTEM</text>
</g>
<g font-family="'Inter',sans-serif">
<rect x="330" y="560" width="300" height="2" fill="{STROKE}"/>
<text x="334" y="640" font-size="26" fill="{MUTED}">Discovery · Orchestration · Execution · Evolution</text>
<text x="334" y="690" font-size="22" fill="{MUTED}">v7.0.0 — Python · FastAPI · Vue 3 · Tauri</text>
</g>
<circle cx="{width - 140}" cy="{height - 130}" r="3.5" fill="{DEEP_BLUE}"/>
<text x="{width - 126}" y="{height - 124}" font-family="'JetBrains Mono',monospace" font-size="20" fill="{MUTED}">EST. 2026</text>
</svg>"""
    return svg


def social_preview() -> str:
    """OpenGraph 1200x630."""
    width, height = 1200, 630
    cx, cy, r, stroke = 250, 315, 105, 14
    svg = f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="{width}" height="{height}" fill="{BLACK}"/>
<rect x="40" y="40" width="{width - 80}" height="{height - 80}" rx="20" fill="none" stroke="{STROKE}" stroke-width="1.5"/>
<g transform="translate({cx - r}, {cy - r})"><g transform="translate({r}, {r})">{_mark(0, 0, r, stroke, WHITE)}</g></g>
<text x="440" y="250" font-family="'Space Grotesk','Inter',sans-serif" font-size="96" font-weight="600" letter-spacing="-2" fill="{WHITE}">OWNEX</text>
<text x="442" y="330" font-family="'JetBrains Mono',monospace" font-size="20" letter-spacing="4" fill="{MUTED}">PERSONAL AUTONOMOUS WORK OS</text>
<rect x="442" y="380" width="260" height="2" fill="{STROKE}"/>
<text x="442" y="440" font-family="'Inter',sans-serif" font-size="24" fill="{MUTED}">Discovery · Orchestration · Execution · Evolution</text>
<text x="442" y="480" font-family="'Inter',sans-serif" font-size="20" fill="{MUTED}">Python · FastAPI · Vue 3 · Tauri v2 · v7.0.0</text>
<circle cx="{width - 120}" cy="{height - 90}" r="7" fill="{DEEP_BLUE}"/>
</svg>"""
    return svg


def main() -> None:
    h = OUT_B / "ownex-hero-banner.svg"
    h.write_text(hero_banner())
    cairosvg.svg2png(url=str(h), write_to=str(OUT_B / "ownex-hero-banner.png"), output_width=2400, output_height=900)
    s = OUT_S / "ownex-social-preview.svg"
    s.write_text(social_preview())
    cairosvg.svg2png(url=str(s), write_to=str(OUT_S / "ownex-social-preview.png"), output_width=1200, output_height=630)
    print("banner + social OK")


if __name__ == "__main__":
    main()
