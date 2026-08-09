#!/usr/bin/env python3
"""OWNEX definitive logo system — O+X geometric mark.

Generates the full logo set (SVG + PNG) into docs/assets/branding/logo/.
Design: octagonal O-ring + X of rays + central node that breaks the ring
(top-right), Tesla-red node as the only saturated accent.

Pure geometry, no AI. Reproducible.
"""

from __future__ import annotations

from pathlib import Path

import cairosvg

OUT = Path(__file__).resolve().parents[2] / "docs" / "assets" / "branding" / "logo"
OUT.mkdir(parents=True, exist_ok=True)

WHITE = "#F6F8FB"
BLACK = "#08090A"
DEEP_BLUE = "#1E40FF"
MUTED = "#8B8D98"


def mark_svg(color: str, node: str = DEEP_BLUE, ring: str | None = None, size: int = 512) -> str:
    """O+X mark: octagonal ring + X of rays + central node breaking the ring."""
    r = 190.0
    cx = cy = 256.0
    stroke = 26.0
    ring_color = ring or color
    # X rays: two bars crossing the center, rotated ±45°
    x1 = f"""<rect x="{cx - stroke / 2}" y="{cy - r * 0.72}" width="{stroke}" height="{r * 1.44}" rx="{stroke / 2}" fill="{color}" transform="rotate(45 {cx} {cy})"/>"""
    x2 = f"""<rect x="{cx - stroke / 2}" y="{cy - r * 0.72}" width="{stroke}" height="{r * 1.44}" rx="{stroke / 2}" fill="{color}" transform="rotate(-45 {cx} {cy})"/>"""
    # Octagonal ring (O) — 8 segments, with a gap at the top-right where the node breaks it
    import math

    n = 8
    gap_deg = 34.0
    segments = []
    gap_start = 45.0 - gap_deg / 2  # top-right area
    for i in range(n):
        a0 = i * (360.0 / n)
        a1 = a0 + (360.0 / n)
        # skip segment that overlaps the break
        center = (a0 + a1) / 2
        if abs(((center - gap_start + 180) % 360) - 180) < gap_deg / 2 + 5:
            continue
        x0 = cx + r * math.cos(math.radians(a0))
        y0 = cy + r * math.sin(math.radians(a0))
        x1p = cx + r * math.cos(math.radians(a1))
        y1p = cy + r * math.sin(math.radians(a1))
        segments.append(
            f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1p:.1f}" y2="{y1p:.1f}" stroke="{ring_color}" stroke-width="{stroke}" stroke-linecap="round"/>'
        )
    # Central node that breaks the ring (top-right)
    nx = cx + r * 1.06
    ny = cy - r * 1.06
    node_circle = f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{stroke * 0.62:.1f}" fill="{node}"/>'
    # Central core square
    core = f'<rect x="{cx - 14}" y="{cy - 14}" width="28" height="28" fill="{color}" transform="rotate(45 {cx} {cy})"/>'
    svg = f"""<svg width="{size}" height="{size}" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
{"".join(segments)}
{x1}
{x2}
{node_circle}
{core}
</svg>"""
    return svg


def wordmark_svg(color: str, size_w: int = 1200) -> str:
    """OWNEX wordmark (Space Grotesk, tracked)."""
    h = 200
    svg = f"""<svg width="{size_w}" height="{h}" viewBox="0 0 {size_w} {h}" xmlns="http://www.w3.org/2000/svg">
<text x="{size_w / 2}" y="{h * 0.68}" font-family="'Space Grotesk','Inter',sans-serif" font-size="150" font-weight="600" letter-spacing="-2" fill="{color}" text-anchor="middle">OWNEX</text>
</svg>"""
    return svg


def lockup_svg(color: str, node: str = DEEP_BLUE, size_w: int = 1200) -> str:
    """Mark + wordmark lockup."""
    m = mark_svg(color, node, size=200)
    h = 200
    svg = f"""<svg width="{size_w}" height="{h}" viewBox="0 0 {size_w} {h}" xmlns="http://www.w3.org/2000/svg">
<g transform="translate(0,0)">{m}</g>
<text x="230" y="{h * 0.68}" font-family="'Space Grotesk','Inter',sans-serif" font-size="130" font-weight="600" letter-spacing="-2" fill="{color}">OWNEX</text>
</svg>"""
    return svg


def favicon_svg(color: str = WHITE, node: str = DEEP_BLUE) -> str:
    """Simplified 64px favicon (mark without ring gap, bolder)."""
    cx = cy = 32.0
    stroke = 5.0
    import math

    parts = []
    n = 8
    for i in range(n):
        a0 = i * (360.0 / n)
        a1 = a0 + (360.0 / n)
        x0 = cx + 22 * math.cos(math.radians(a0))
        y0 = cy + 22 * math.sin(math.radians(a0))
        x1 = cx + 22 * math.cos(math.radians(a1))
        y1 = cy + 22 * math.sin(math.radians(a1))
        parts.append(
            f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round"/>'
        )
    # X
    parts.append(
        f'<rect x="{cx - stroke / 2}" y="{cy - 15.5}" width="{stroke}" height="31" rx="2.5" fill="{color}" transform="rotate(45 {cx} {cy})"/>'
    )
    parts.append(
        f'<rect x="{cx - stroke / 2}" y="{cy - 15.5}" width="{stroke}" height="31" rx="2.5" fill="{color}" transform="rotate(-45 {cx} {cy})"/>'
    )
    # Node
    parts.append(f'<circle cx="{cx + 23.5}" cy="{cy - 23.5}" r="4.6" fill="{node}"/>')
    parts.append(
        f'<rect x="{cx - 3.4}" y="{cy - 3.4}" width="6.8" height="6.8" fill="{color}" transform="rotate(45 {cx} {cy})"/>'
    )
    return f"""<svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
{"".join(parts)}
</svg>"""


def write(name: str, svg: str) -> Path:
    p = OUT / name
    p.write_text(svg)
    return p


def png(svg_path: Path, width: int, height: int | None = None) -> Path:
    p = svg_path.with_suffix(".png")
    h = height or width
    cairosvg.svg2png(url=str(svg_path), write_to=str(p), output_width=width, output_height=h)
    return p


def main() -> None:
    variants = {
        "ownex-mark-white": (WHITE, DEEP_BLUE),
        "ownex-mark-black": (BLACK, DEEP_BLUE),
        "ownex-mark-mono": (WHITE, None),
        "ownex-mark-omega": (WHITE, "#00E39A"),
    }
    for name, (color, node) in variants.items():
        s = write(f"{name}.svg", mark_svg(color, node or color))
        png(s, 1024)
        print("mark", name)

    for name, color in [
        ("ownex-wordmark-white", WHITE),
        ("ownex-wordmark-black", BLACK),
        ("ownex-wordmark-mono", MUTED),
    ]:
        s = write(f"{name}.svg", wordmark_svg(color))
        png(s, 1200, 200)
        print("wordmark", name)

    for name, color in [("ownex-lockup-white", WHITE), ("ownex-lockup-black", BLACK)]:
        s = write(f"{name}.svg", lockup_svg(color))
        png(s, 1200, 200)
        print("lockup", name)

    s = write("ownex-favicon.svg", favicon_svg())
    png(s, 64)
    png(s, 512)
    print("favicon done")

    # mark white PNG at 512 for README
    s = OUT / "ownex-mark-white.svg"
    png(s, 512)
    print("ALL DONE", OUT)


if __name__ == "__main__":
    main()
