"""OWNEX brand pipeline — deterministic vector identity system.

Generates the full OWNEX brand system (mark, lockups, banners, concepts)
from exact geometry + design tokens. No randomness: every output is
reproducible from this module.

Toolchain: Python + cairosvg + fontTools/PIL (all open source).
"""

from __future__ import annotations

import json
import math
import re
import subprocess
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
# Mark geometry — "The Signal" — clean geometric precision
# A refined monogram: intersecting diagonals with precise negative space
# ---------------------------------------------------------------------------

# Core mark dimensions (in 512px coordinate space)
MARK_R = 220  # outer bounding radius
BAR_W = 38  # bar thickness
BAR_GAP = 8  # gap at center intersection
ARM_LEN = 200  # arm length from center
END_R = 12  # rounded end radius

# Secondary accent ring
RING_R = 248
RING_SW = 2.5


def pt(angle_deg: float, radius: float, cx: float = CX, cy: float = CY) -> tuple[float, float]:
    a = math.radians(angle_deg)
    return (cx + radius * math.cos(a), cy - radius * math.sin(a))


def rounded_rect_path(x: float, y: float, w: float, h: float, r: float) -> str:
    """SVG path for rounded rect centered at (x,y)."""
    hw, hh = w / 2, h / 2
    x0, y0 = x - hw, y - hh
    x1, y1 = x + hw, y + hh
    return (
        f"M {x0 + r:.2f} {y0:.2f}"
        f" L {x1 - r:.2f} {y0:.2f}"
        f" Q {x1:.2f} {y0:.2f} {x1:.2f} {y0 + r:.2f}"
        f" L {x1:.2f} {y1 - r:.2f}"
        f" Q {x1:.2f} {y1:.2f} {x1 - r:.2f} {y1:.2f}"
        f" L {x0 + r:.2f} {y1:.2f}"
        f" Q {x0:.2f} {y1:.2f} {x0:.2f} {y1 - r:.2f}"
        f" L {x0:.2f} {y0 + r:.2f}"
        f" Q {x0:.2f} {y0:.2f} {x0 + r:.2f} {y0:.2f}"
        " Z"
    )


def mark_defs(variant: str = "alpha") -> str:
    """Gradient definitions per variant."""
    if variant == "alpha":
        start, end = C["cyber_cyan"], C["deep_blue"]
    elif variant == "omega":
        start, end = C["emerald"], C["cyber_cyan"]
    else:
        start, end = C["cyber_cyan"], C["deep_blue"]
    return f"""
  <defs>
    <linearGradient id="markGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{start}"/>
      <stop offset="100%" stop-color="{end}"/>
    </linearGradient>
    <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{start}"/>
      <stop offset="100%" stop-color="{end}" stop-opacity="0.6"/>
    </linearGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>"""


def mark_group(variant: str = "alpha", mono: str | None = None, bold: bool = False) -> str:
    """Core mark: two intersecting bars with precise center gap + subtle ring."""
    m = 1.2 if bold else 1.0
    bar_w = BAR_W * m
    gap = BAR_GAP * m
    arm_len = ARM_LEN * m
    end_r = END_R * m
    ring_sw = RING_SW * m

    fill = "#FFFFFF" if mono == "white" else ("#05060A" if mono == "black" else "url(#markGrad)")
    ring_fill = "none" if mono else "url(#ringGrad)"
    ring_stroke = "#FFFFFF" if mono == "white" else ("#05060A" if mono == "black" else C["cyber_cyan"])

    half_w = bar_w / 2
    half_gap = gap / 2

    # Main diagonal bar (\) - top-left to bottom-right
    bar1_points = [
        pt(225, arm_len + half_w * 1.414),
        pt(45, arm_len + half_w * 1.414),
        pt(45, arm_len - half_w * 1.414),
        pt(225, arm_len - half_w * 1.414),
    ]
    # Other diagonal (/) - top-right to bottom-left
    bar2_points = [
        pt(135, arm_len + half_w * 1.414),
        pt(315, arm_len + half_w * 1.414),
        pt(315, arm_len - half_w * 1.414),
        pt(135, arm_len - half_w * 1.414),
    ]

    # Center gap - cut out the intersection square
    center_gap = gap * 1.414
    cx, cy = CX, CY

    # Build as paths with center gap
    def bar_path(angle: float) -> str:
        a = math.radians(angle)
        cos_a, sin_a = math.cos(a), math.sin(a)
        hw = half_w
        # Four corners of the bar, with center cutout
        # Start at far end, trace around, leaving center gap
        if angle == 45:  # main diagonal
            pts = [
                (cx + cos_a * (arm_len + hw), cy - sin_a * (arm_len + hw)),  # tip
                (cx + cos_a * (arm_len - hw), cy - sin_a * (arm_len - hw)),
                (cx + cos_a * half_gap, cy - sin_a * half_gap),
                # inner corner, go perpendicular to create gap
                (cx + cos_a * half_gap - sin_a * hw, cy - sin_a * half_gap - cos_a * hw),
                (cx - cos_a * half_gap - sin_a * hw, cy + sin_a * half_gap - cos_a * hw),
                (cx - cos_a * half_gap, cy + sin_a * half_gap),
                (cx - cos_a * (arm_len - hw), cy + sin_a * (arm_len - hw)),
                (cx - cos_a * (arm_len + hw), cy + sin_a * (arm_len + hw)),
            ]
        else:  # 135° diagonal
            pts = [
                (cx - cos_a * (arm_len + hw), cy - sin_a * (arm_len + hw)),
                (cx - cos_a * (arm_len - hw), cy - sin_a * (arm_len - hw)),
                (cx - cos_a * half_gap, cy - sin_a * half_gap),
                (cx - cos_a * half_gap + sin_a * hw, cy - sin_a * half_gap + cos_a * hw),
                (cx + cos_a * half_gap + sin_a * hw, cy + sin_a * half_gap + cos_a * hw),
                (cx + cos_a * half_gap, cy + sin_a * half_gap),
                (cx + cos_a * (arm_len - hw), cy + sin_a * (arm_len - hw)),
                (cx + cos_a * (arm_len + hw), cy + sin_a * (arm_len + hw)),
            ]
        return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"

    bar1 = bar_path(45)
    bar2 = bar_path(135)

    # Subtle outer ring
    ring = f'<circle cx="{CX}" cy="{CY}" r="{RING_R}" fill="none" stroke="{ring_stroke}" stroke-width="{ring_sw}" opacity="0.35"/>'

    # Small center node (precision indicator)
    node = f'<rect x="{CX - 4}" y="{CY - 4}" width="8" height="8" rx="2" fill="{fill}"/>'

    return f"""
  <g id="ownex-mark" filter="url(#glow)">
    <path d="{bar1}" fill="{fill}"/>
    <path d="{bar2}" fill="{fill}"/>
    {ring}
    {node}
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
    f = font(fname, weight, px)
    spacing = int(round(tracking * px / 1000))
    widths = [draw.textlength(ch, font=f) + spacing for ch in text]
    total = sum(widths[:-1]) + draw.textlength(text[-1], font=f) if text else 0
    x0 = xy[0] - total / 2 if anchor_mid else xy[0]
    y0 = xy[1] - px * 0.72 if anchor_mid else xy[1]
    fill_rgba = fill if alpha >= 255 else fill + f"{alpha:02X}"
    for ch, w in zip(text, widths, strict=False):
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
    subprocess.run(["xdg-open", str(path)])


if __name__ == "__main__":
    print("OWNEX pipeline OK", C)
