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


def _mix_hex(a: str, b: str, t: float) -> str:
    """Interpolate two hex colors (t in 0..1)."""
    ca = (int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16))
    cb = (int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16))
    return "#{:02X}{:02X}{:02X}".format(*(int(ca[i] + (cb[i] - ca[i]) * t) for i in range(3)))


def _lighten(color: str, f: float) -> str:
    """Lighten a hex color by mixing with white (f in 0..1)."""
    return _mix_hex(color, "#FFFFFF", f)


def mark_svg(color: str, node: str = DEEP_BLUE, ring: str | None = None, size: int = 512) -> str:
    """O+X Aperture Nexus mark (premium): halo, precision ring, gradients, glint.

    Layering: radial halo → outer precision octagon (thin, with vertex ticks)
    → main octagonal ring (gradient stroke, gap top-right) → X of rays
    (gradient) → inner fine octagon → central core (radial gradient) → node
    breaking the ring with its own halo + glint.
    """
    import math

    r = 190.0
    cx = cy = 256.0
    stroke = 26.0
    ring_color = ring or color
    hi = _lighten(ring_color, 0.38)
    lo = _lighten(ring_color, 0.06)
    node_hi = _lighten(node, 0.55)

    def vtx(radius: float, i: int, n: int = 8, phase: float = 22.5) -> tuple[float, float]:
        a = math.radians(phase + i * (360.0 / n))
        return (cx + radius * math.cos(a), cy + radius * math.sin(a))

    # Outer precision octagon (thin) + vertex ticks
    outer = "".join(
        f'<line x1="{vtx(r * 1.17, i)[0]:.1f}" y1="{vtx(r * 1.17, i)[1]:.1f}" '
        f'x2="{vtx(r * 1.17, i + 1)[0]:.1f}" y2="{vtx(r * 1.17, i + 1)[1]:.1f}" '
        f'stroke="{lo}" stroke-width="3" stroke-linecap="round"/>'
        for i in range(8)
    )
    ticks = "".join(
        f'<circle cx="{vtx(r * 1.17, i)[0]:.1f}" cy="{vtx(r * 1.17, i)[1]:.1f}" r="4" fill="{hi}" opacity="0.85"/>'
        for i in range(8)
    )
    # Main octagonal ring — 8 gradient segments with a gap at the top-right
    gap_deg = 34.0
    gap_start = 45.0 - gap_deg / 2
    segments = []
    for i in range(8):
        a0 = i * (360.0 / 8)
        a1 = a0 + (360.0 / 8)
        center = (a0 + a1) / 2
        if abs(((center - gap_start + 180) % 360) - 180) < gap_deg / 2 + 5:
            continue
        x0, y0 = vtx(r, i)
        x1p, y1p = vtx(r, i + 1)
        segments.append(
            f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1p:.1f}" y2="{y1p:.1f}" '
            f'stroke="url(#ringGrad)" stroke-width="{stroke}" stroke-linecap="round"/>'
        )
    # X rays (gradient bars)
    ray_len = r * 0.8
    x1 = f'<rect x="{cx - stroke / 2}" y="{cy - ray_len}" width="{stroke}" height="{ray_len * 2}" rx="{stroke / 2}" fill="url(#rayGrad)" transform="rotate(45 {cx} {cy})"/>'
    x2 = f'<rect x="{cx - stroke / 2}" y="{cy - ray_len}" width="{stroke}" height="{ray_len * 2}" rx="{stroke / 2}" fill="url(#rayGrad)" transform="rotate(-45 {cx} {cy})"/>'
    # Inner fine octagon (precision core around the center)
    inner = "".join(
        f'<line x1="{vtx(r * 0.66, i)[0]:.1f}" y1="{vtx(r * 0.66, i)[1]:.1f}" '
        f'x2="{vtx(r * 0.66, i + 1)[0]:.1f}" y2="{vtx(r * 0.66, i + 1)[1]:.1f}" '
        f'stroke="{lo}" stroke-width="2.5" stroke-linecap="round"/>'
        for i in range(8)
    )
    # Central core square (rotated)
    core = f'<rect x="{cx - 14}" y="{cy - 14}" width="28" height="28" fill="url(#coreGrad)" transform="rotate(45 {cx} {cy})"/>'
    # Node breaking the ring (top-right): halo + body + glint
    node_ang = math.radians(45)
    nx = cx + r * 1.06 * math.cos(node_ang)
    ny = cy - r * 1.06 * math.sin(node_ang)
    node_halo = f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{stroke * 1.35:.1f}" fill="url(#nodeHalo)" opacity="0.9"/>'
    node_circle = f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{stroke * 0.62:.1f}" fill="url(#nodeGrad)"/>'
    glint = (
        f'<circle cx="{nx - stroke * 0.18:.1f}" cy="{ny - stroke * 0.18:.1f}" '
        f'r="{stroke * 0.2:.1f}" fill="{node_hi}" opacity="0.9"/>'
    )
    svg = f"""<svg width="{size}" height="{size}" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
<defs>
  <radialGradient id="halo" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{ring_color}" stop-opacity="0.16"/>
    <stop offset="1" stop-color="{ring_color}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="ringGrad" x1="0" y1="0" x2="512" y2="512" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{lo}"/>
    <stop offset="0.5" stop-color="{ring_color}"/>
    <stop offset="1" stop-color="{hi}"/>
  </linearGradient>
  <linearGradient id="rayGrad" x1="0" y1="0" x2="512" y2="512" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{lo}"/>
    <stop offset="1" stop-color="{hi}"/>
  </linearGradient>
  <radialGradient id="coreGrad" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{hi}"/>
    <stop offset="1" stop-color="{ring_color}"/>
  </radialGradient>
  <radialGradient id="nodeHalo" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{node}" stop-opacity="0.5"/>
    <stop offset="1" stop-color="{node}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="nodeGrad" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{node_hi}"/>
    <stop offset="1" stop-color="{node}"/>
  </linearGradient>
</defs>
<circle cx="{cx}" cy="{cy}" r="{r * 1.35:.0f}" fill="url(#halo)"/>
{outer}
{ticks}
{"".join(segments)}
{x1}
{x2}
{inner}
{core}
{node_halo}
{node_circle}
{glint}
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
    """Simplified 64px favicon (mark without ring gap, bolder, subtle halo)."""
    cx = cy = 32.0
    stroke = 5.0
    import math

    hi = _lighten(color, 0.4)
    lo = _lighten(color, 0.05)

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
            f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="url(#favRing)" stroke-width="{stroke}" stroke-linecap="round"/>'
        )
    # X
    parts.append(
        f'<rect x="{cx - stroke / 2}" y="{cy - 15.5}" width="{stroke}" height="31" rx="2.5" fill="url(#favRay)" transform="rotate(45 {cx} {cy})"/>'
    )
    parts.append(
        f'<rect x="{cx - stroke / 2}" y="{cy - 15.5}" width="{stroke}" height="31" rx="2.5" fill="url(#favRay)" transform="rotate(-45 {cx} {cy})"/>'
    )
    # Node
    parts.append(f'<circle cx="{cx + 23.5}" cy="{cy - 23.5}" r="4.6" fill="url(#favNode)"/>')
    parts.append(f'<circle cx="{cx + 23.5}" cy="{cy - 23.5}" r="7.5" fill="url(#favNodeHalo)"/>')
    parts.append(
        f'<rect x="{cx - 3.4}" y="{cy - 3.4}" width="6.8" height="6.8" fill="url(#favCore)" transform="rotate(45 {cx} {cy})"/>'
    )
    return f"""<svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="favRing" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{lo}"/>
    <stop offset="0.5" stop-color="{color}"/>
    <stop offset="1" stop-color="{hi}"/>
  </linearGradient>
  <linearGradient id="favRay" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{lo}"/>
    <stop offset="1" stop-color="{hi}"/>
  </linearGradient>
  <linearGradient id="favNode" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{_lighten(node, 0.55)}"/>
    <stop offset="1" stop-color="{node}"/>
  </linearGradient>
  <radialGradient id="favNodeHalo" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{node}" stop-opacity="0.45"/>
    <stop offset="1" stop-color="{node}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="favCore" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{hi}"/>
    <stop offset="1" stop-color="{color}"/>
  </radialGradient>
</defs>
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
