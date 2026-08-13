"""Generate the 38 GitHub presentation assets deterministically (PIL, GPU-free).

Replaces the previous placeholder/absent images with a coherent, premium,
Tesla-dark asset set: hero, logos, desktop surfaces, OMEGA mobile screens,
architecture diagrams and the Open Graph preview.

Usage:
    python scripts/brand/generate_github_assets.py

Output:
    docs/assets/github/...
"""

from __future__ import annotations

import math
import os
import random
import shutil
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "assets" / "github"
FONTS = ROOT / "assets" / "branding" / "fonts"

# ---------------------------------------------------------------- palette ---
BG = "#05060A"
SURFACE = "#0D0F14"
SURFACE2 = "#12151B"
HAIRLINE = "#1C2028"
TEXT = "#F6F8FB"
MUTED = "#8A93A3"
BLUE = "#1E40FF"
CYAN = "#00D5FF"
EMERALD = "#00E39A"
ORANGE = "#FF7A1A"
RED = "#E82127"
WHITE = "#FFFFFF"


# ------------------------------------------------------------------ fonts ---
def font(size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    fam = {400: "Inter-400", 500: "Inter-500", 600: "Inter-600", 700: "Inter-700"}
    return ImageFont.truetype(str(FONTS / f"{fam[weight]}.ttf"), size)


def display_font(size: int, weight: int = 600) -> ImageFont.FreeTypeFont:
    fam = {400: "SpaceGrotesk-400", 500: "SpaceGrotesk-500", 600: "SpaceGrotesk-600", 700: "SpaceGrotesk-700"}
    return ImageFont.truetype(str(FONTS / f"{fam[weight]}.ttf"), size)


def mono_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / "JetBrainsMono-500.ttf"), size)


# ----------------------------------------------------------------- helpers ---
def rr(draw: ImageDraw.ImageDraw, box, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def text(draw: ImageDraw.ImageDraw, xy, s, f, fill=TEXT, anchor="la"):
    draw.text(xy, s, font=f, fill=fill, anchor=anchor)


def chip(draw: ImageDraw.ImageDraw, x, y, label, color, fs=13):
    f = font(fs, 600)
    w = draw.textlength(label, font=f) + 20
    rr(draw, (x, y, x + w, y + fs + 12), r=(fs + 12) // 2, fill=color + "1F", outline=color + "55", width=1)
    text(draw, (x + 10, y + (fs + 12) // 2), label, f, fill=color, anchor="lm")


def sparkline(draw: ImageDraw.ImageDraw, box, values, color=CYAN, fill=True):
    x0, y0, x1, y1 = (int(v) for v in box)
    pts = len(values)
    step = (x1 - x0) / max(pts - 1, 1)
    lo, hi = min(values), max(values)
    rng = (hi - lo) or 1
    points = [(x0 + i * step, y1 - (v - lo) / rng * (y1 - y0)) for i, v in enumerate(values)]
    draw.line(points, fill=color, width=3, joint="curve")
    if fill:
        poly = [(x0, y1), *points, (x1, y1)]
        draw.polygon(poly, fill=None)
        overlay = Image.new("RGBA", (x1 - x0 + 2, y1 - y0 + 2), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.polygon([(p[0] - x0, p[1] - y0) for p in poly], fill=color + "18")
        return overlay, (int(x0) - 1, int(y0) - 1)
    return None


def bars(draw: ImageDraw.ImageDraw, box, values, color=CYAN):
    x0, y0, x1, y1 = (int(v) for v in box)
    n = len(values)
    w = (x1 - x0) / n * 0.62
    gap = (x1 - x0) / n
    lo, hi = min(values), max(values)
    rng = (hi - lo) or 1
    for i, v in enumerate(values):
        h = max(2, (v - lo) / rng * (y1 - y0))
        cx = x0 + i * gap + gap / 2
        rr(draw, (cx - w / 2, y1 - h, cx + w / 2, y1), r=3, fill=color)


def donut(draw: ImageDraw.ImageDraw, cx, cy, r, frac, color=CYAN, track=SURFACE2, width=14):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=track, width=width)
    if frac > 0:
        a0 = -90
        a1 = a0 + 360 * frac
        bbox = (cx - r, cy - r, cx + r, cy + r)
        draw.arc(bbox, a0, a1, fill=color, width=width)


def card(draw: ImageDraw.ImageDraw, box, title=None, subtitle=None, r=12):
    x0, y0, x1, y1 = box
    rr(draw, box, r=r, fill=SURFACE, outline=HAIRLINE, width=1)
    if title:
        text(draw, (x0 + 16, y0 + 14), title, display_font(16, 600))
    if subtitle:
        text(draw, (x0 + 16, y0 + 36), subtitle, font(11), fill=MUTED)
    return (x0 + 16, y0 + 56)


def kpi(draw: ImageDraw.ImageDraw, x0, y0, w, h, label, value, delta, dcol=EMERALD):
    rr(draw, (x0, y0, x0 + w, y0 + h), r=12, fill=SURFACE, outline=HAIRLINE, width=1)
    text(draw, (x0 + 16, y0 + 14), label, font(11), fill=MUTED)
    text(draw, (x0 + 16, y0 + 34), value, display_font(28, 700))
    text(draw, (x0 + 16, y0 + 62), delta, font(11), fill=dcol)


def status_dot(draw: ImageDraw.ImageDraw, x, y, color, r=4):
    draw.ellipse((x - r, y - r, x + r, y + r), fill=color)


def signal_bars(draw: ImageDraw.ImageDraw, x1, cy, n=4, color=TEXT, w=10, gap=8, maxh=26):
    """Drawn signal bars (no font glyphs needed), right-aligned at x1."""
    for i in range(n):
        h = 10 + int((maxh - 10) * i / max(n - 1, 1))
        draw.rounded_rectangle(
            (x1 - (n - i) * (w + gap), cy - h // 2, x1 - (n - 1 - i) * (w + gap) - gap, cy + h // 2),
            radius=3,
            fill=color,
        )


def equalizer(draw: ImageDraw.ImageDraw, cx, cy, n=6, color=WHITE, w=10, gap=12, maxh=44, seed=7):
    """Drawn equalizer bars (no font glyphs needed), centered at cx."""
    random.seed(seed)
    total = n * w + (n - 1) * gap
    x0 = cx - total // 2
    for i in range(n):
        h = random.randint(maxh // 4, maxh)
        draw.rounded_rectangle(
            (x0 + i * (w + gap), cy - h // 2, x0 + i * (w + gap) + w, cy + h // 2), radius=4, fill=color
        )


# ---------------------------------------------------------- premium fx ---
def gradient_bg(img: Image.Image, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> ImageDraw.ImageDraw:
    """Vertical gradient background; returns a fresh draw handle."""
    w, h = img.size
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line((0, y, w, y), fill=tuple(int(top[c] + (bottom[c] - top[c]) * t) for c in range(3)))
    return ImageDraw.Draw(img)


def glow(img: Image.Image, d: ImageDraw.ImageDraw, cx, cy, r, color: str, peak=10, steps=16):
    """Soft radial glow via concentric alpha rings (no numpy/gpu)."""
    for i in range(steps, 0, -1):
        rr_i = r * i / steps
        a = int(peak * ((1 - i / steps) ** 1.5))
        if a <= 0:
            continue
        d.ellipse((cx - rr_i, cy - rr_i, cx + rr_i, cy + rr_i), fill=color + f"{a:02X}")


def grid_faded(img: Image.Image, cx, cy, step=120, base=(13, 16, 22), peak=44):
    """Grid that fades toward the focal point (premium depth)."""
    w, h = img.size
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for gx in range(0, w, step):
        dist = abs(gx - cx)
        a = int(peak * min(1.0, 0.22 + 0.78 * dist / (w * 0.5)))
        od.line((gx, 0, gx, h), fill=base + (a,))
    for gy in range(0, h, step):
        dist = abs(gy - cy)
        a = int(peak * min(1.0, 0.22 + 0.78 * dist / (h * 0.5)))
        od.line((0, gy, w, gy), fill=base + (a,))
    img.paste(ov, (0, 0), ov)


def grain(img: Image.Image, seed: int, n=16000, alpha=7, color=(255, 255, 255)):
    """Subtle film grain overlay (deterministic)."""
    random.seed(seed)
    w, h = img.size
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for _ in range(n):
        x = random.randrange(w)
        y = random.randrange(h)
        a = random.randint(max(alpha - 3, 1), alpha + 3)
        od.point((x, y), fill=color + (a,))
    img.paste(ov, (0, 0), ov)


def tracked_text(d: ImageDraw.ImageDraw, xy, s: str, f, fill, tracking=0, anchor="la"):
    """Letter-spaced text (premium typography)."""
    x, y = xy
    if anchor == "mm":
        total = sum(d.textlength(c, font=f) for c in s) + tracking * (len(s) - 1)
        x -= total / 2
    for c in s:
        d.text((x, y), c, font=f, fill=fill, anchor="la")
        x += d.textlength(c, font=f) + tracking


def gradient_text(img: Image.Image, xy, s: str, f, top: str, bottom: str, anchor="lm", tracking=0):
    """Text filled with a vertical gradient via luminance mask."""
    mask = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(mask)
    x, y = xy
    if anchor == "mm":
        total = sum(md.textlength(c, font=f) for c in s) + tracking * (len(s) - 1)
        x -= total / 2
        widths = []
        for c in s:
            widths.append(md.textlength(c, font=f))
        x -= (total - sum(widths) - tracking * (len(s) - 1)) / 2  # keep mm centered exactly
    for c in s:
        md.text((x, y), c, font=f, fill=255, anchor="lm")
        x += md.textlength(c, font=f) + tracking
    bb = mask.getbbox()
    if not bb:
        return
    x0, y0, x1, y1 = bb
    grad = Image.new("RGB", img.size, bottom)
    gd = ImageDraw.Draw(grad)
    tc, bc = _hex(top), _hex(bottom)
    for row in range(y0, y1 + 1):
        t = (row - y0) / max(y1 - y0, 1)
        gd.line((x0, row, x1, row), fill=tuple(int(tc[c] + (bc[c] - tc[c]) * t) for c in range(3)))
    img.paste(grad, (0, 0), mask)


def _hex(h: str) -> tuple[int, int, int]:
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))


def _mix_hex(a: str, b: str, t: float) -> str:
    """Interpolate between two hex colors (t in 0..1)."""
    ca, cb = _hex(a), _hex(b)
    return "#{:02X}{:02X}{:02X}".format(*(int(ca[c] + (cb[c] - ca[c]) * t) for c in range(3)))


def _grad_line(d: ImageDraw.ImageDraw, p0, p1, c0: str, c1: str, width: int, steps: int = 24):
    """Line with a color gradient c0→c1 (drawn as stepped segments)."""
    x0, y0 = p0
    x1, y1 = p1
    for i in range(steps):
        t0 = i / steps
        t1 = (i + 1) / steps
        c = _mix_hex(c0, c1, (t0 + t1) / 2)
        d.line(
            (x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0, x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1),
            fill=c,
            width=width,
        )


def flatten(img: Image.Image, bg: str = BG) -> Image.Image:
    """Composite an RGBA canvas onto an opaque background (alpha-correct)."""
    base = Image.new("RGB", img.size, bg)
    base.paste(img, (0, 0), img)
    return base


def corner_ticks(d: ImageDraw.ImageDraw, w, h, length=70, color="#2A2F3A"):
    for tx, ty, dx, dy in ((0, 0, 1, 1), (w - 1, 0, -1, 1), (0, h - 1, 1, -1), (w - 1, h - 1, -1, -1)):
        d.line((tx, ty, tx + dx * length, ty), fill=color, width=2)
        d.line((tx, ty, tx, ty + dy * length), fill=color, width=2)


def eyebrow(d: ImageDraw.ImageDraw, w, t: str, y, fs=20, color="#5C6575", hair=HAIRLINE, dot=EMERALD):
    """Centered mono eyebrow with hairline + status dot."""
    f_ey = mono_font(fs)
    ew = d.textlength(t, font=f_ey)
    ex = (w - ew) // 2
    wing = 300 if fs > 16 else 170
    d.line((ex - wing, y - fs // 2, ex - 80, y - fs // 2), fill=hair, width=1)
    d.line((ex + ew + 80, y - fs // 2, ex + ew + wing, y - fs // 2), fill=hair, width=1)
    status_dot(d, w // 2, y - fs // 2, dot)
    d.text((ex, y), t, font=f_ey, fill=color, anchor="la")


def hero_pills(d: ImageDraw.ImageDraw, w, pills, y, fs=20, fill=SURFACE, outline=HAIRLINE, tcol=TEXT):
    fch = font(fs, 600)
    ws = [d.textlength(lbl, font=fch) + 52 for lbl, _ in pills]
    gap = 26
    total = sum(ws) + gap * (len(pills) - 1)
    x = (w - total) // 2
    for (lbl, c), ww in zip(pills, ws, strict=True):
        rr(d, (x, y, x + ww, y + fs + 26), r=(fs + 26) // 2, fill=fill, outline=outline, width=1)
        status_dot(d, x + 22, y + (fs + 26) // 2, c, 5)
        d.text((x + 38, y + (fs + 26) // 2), lbl, font=fch, fill=tcol, anchor="lm")
        x += ww + gap


# ---------------------------------------------------------- premium helpers ---
def card_shadow(img: Image.Image, box, r=12, offset=(4, 4), blur=12, alpha=80):
    """Soft shadow for premium cards (no numpy). Draws shadow on img."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    ov = Image.new("RGBA", (w + offset[0] + blur * 2, h + offset[1] + blur * 2), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for i in range(blur, 0, -1):
        a = int(alpha * (1 - i / blur) ** 1.5)
        if a <= 0:
            continue
        od.rounded_rectangle(
            (i, i, w + i + offset[0], h + i + offset[1]),
            radius=r,
            fill=(0, 0, 0, a),
        )
    img.paste(ov, (x0 - blur, y0 - blur), ov)


def gradient_line(d: ImageDraw.ImageDraw, x0, y, x1, colors: list[str], width=2):
    """Horizontal gradient line: list of hex colors."""
    segs = len(colors) - 1
    if segs <= 0:
        d.line((x0, y, x1, y), fill=colors[0], width=width)
        return
    step = (x1 - x0) / segs
    for i in range(segs):
        c0 = _hex(colors[i])
        c1 = _hex(colors[i + 1])
        sx = x0 + i * step
        ex = x0 + (i + 1) * step
        for px in range(int(sx), int(ex) + 1):
            t = (px - sx) / (ex - sx) if ex != sx else 0
            col = tuple(int(c0[c] + (c1[c] - c0[c]) * t) for c in range(3))
            d.line((px, y, px, y + width - 1), fill=col)


def premium_chip(d: ImageDraw.ImageDraw, x, y, label, color, fs=13):
    """Premium chip: rgba fill + border + text."""
    f = font(fs, 600)
    w = d.textlength(label, font=f) + 24
    r = (fs + 14) // 2
    fill_col = color + "1F"
    outline_col = color + "55"
    rr(d, (x, y, x + w, y + fs + 14), r=r, fill=fill_col, outline=outline_col, width=1)
    text(d, (x + 12, y + (fs + 14) // 2), label, f, fill=color, anchor="lm")


def render_lockup_premium(
    w: int, h: int, color=CYAN, bg: str | None = BG, text_color=TEXT, sub_color=MUTED
) -> Image.Image:
    """Premium lockup: mark + wordmark + tagline with refined metrics."""
    img = Image.new("RGBA", (w, h), bg or (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    mark_sz = h * 0.58
    draw_mark(d, h * 0.6, h / 2, mark_sz, color=color, img=img)
    f_own = display_font(int(h * 0.36), 700)
    own_x = h * 1.15
    own_y = h / 2 - 24
    d.text((own_x, own_y), "OWNEX", font=f_own, fill=text_color, anchor="lm")
    f_tag = font(int(h * 0.11))
    t = "AUTONOMOUS WORK OPERATING SYSTEM"
    own_bbox = d.textbbox((own_x, own_y), "OWNEX", font=f_own, anchor="lm")
    tag_y = own_bbox[3] + int(h * 0.06)
    d.text((own_x, tag_y), t, font=f_tag, fill=sub_color, anchor="lt")
    return img


def render_mark_card(size: int, color: str, node: str, label: str, accent: str) -> Image.Image:
    """Premium mark card: 160x160 surface card with mark, label, shadow."""
    pad = 16
    card_w = size - 2 * pad
    card_h = size - 2 * pad
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    box = (pad, pad, pad + card_w, pad + card_h)
    card_shadow(img, box, r=16, offset=(4, 8), blur=16, alpha=100)
    rr(d, box, r=16, fill=SURFACE, outline=HAIRLINE, width=1)
    mark_sz = card_h * 0.48
    draw_mark(d, size // 2, size // 2 - 10, mark_sz, color=color, node=node, img=img)
    f_lbl = font(11, 500)
    d.text((size // 2, size - pad - 24), label, font=f_lbl, fill=MUTED, anchor="mm")
    accent_bar_h = 3
    d.rounded_rectangle(
        (pad + 20, size - pad - 8, size - pad - 20, size - pad - 8 + accent_bar_h), radius=1, fill=accent
    )
    return img


def render_deliverables_grid() -> Image.Image:
    """Composite: 3 mark cards + wide lockup card in a grid."""
    w, h = 1600, 520
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    card_w = 240
    card_h = 440
    gap = 40
    start_x = (w - 3 * card_w - 2 * gap) // 2
    y0 = (h - card_h) // 2
    for i, (label, color, node, accent) in enumerate(
        [
            ("ALPHA", CYAN, BLUE, CYAN),
            ("OMEGA", EMERALD, CYAN, EMERALD),
            ("MONO", WHITE, WHITE, MUTED),
        ]
    ):
        x = start_x + i * (card_w + gap)
        card_img = render_mark_card(card_h, color, node, label, accent)
        img.paste(card_img, (x, y0), card_img)
    lockup_w = w - 2 * start_x
    lockup_h = 160
    lockup_img = render_lockup_premium(lockup_w, lockup_h, color=CYAN, bg=SURFACE, text_color=TEXT, sub_color=MUTED)
    lx = start_x
    ly = y0 + card_h + 20
    card_shadow(img, (lx, ly, lx + lockup_w, ly + lockup_h), r=16, offset=(4, 8), blur=16, alpha=100)
    img.paste(lockup_img, (lx, ly), lockup_img)
    return img


def render_footer_lockup() -> Image.Image:
    """Footer: gradient separator + compact single-line lockup."""
    w, h = 1600, 120
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    gradient_line(d, 120, 18, w - 120, ["#00000000", BLUE, CYAN, "#00000000"], width=2)
    mark_sz = 48
    draw_mark(d, 80, h // 2, mark_sz, color=CYAN, node=BLUE, img=img)
    f_own = display_font(28, 700)
    own_x = 100 + mark_sz
    own_y = h // 2 - 6
    d.text((own_x, own_y), "OWNEX", font=f_own, fill=TEXT, anchor="lm")
    f_tag = font(11)
    t = "AUTONOMOUS WORK OPERATING SYSTEM"
    d.text((own_x + 180, own_y + 4), t, font=f_tag, fill=MUTED, anchor="lm")
    return img


def render_hero_premium() -> Image.Image:
    """Premium hero: radial depth, cyan→emerald wordmark, premium chips, decorative line."""
    w, h = 2400, 900
    img = Image.new("RGBA", (w, h), _hex(BG) + (255,))
    d = gradient_bg(img, (5, 6, 10), (10, 13, 19))
    glow(img, d, w // 2, 200, 950, BLUE, peak=8, steps=24)
    glow(img, d, 700, 480, 550, CYAN, peak=6, steps=22)
    glow(img, d, w - 700, 480, 550, EMERALD, peak=5, steps=20)
    grid_faded(img, w // 2, h // 2)
    grain(img, seed=20260812, n=20000, alpha=8)
    d = ImageDraw.Draw(img)
    d.line((0, 0, w, 0), fill="#262B35", width=1)
    corner_ticks(d, w, h)
    eyebrow(d, w, "PERSONAL AUTONOMOUS WORK OPERATING SYSTEM", 160, fs=22)
    draw_mark(d, 770, 500, 360, color=CYAN, node=BLUE, img=img)
    gradient_text(img, (1045, 460), "OWNEX", display_font(170, 700), CYAN, EMERALD, tracking=2)
    d = ImageDraw.Draw(img)
    tracked_text(d, (1051, 582), "AUTONOMOUS WORK OPERATING SYSTEM", font(28), MUTED, tracking=16)
    gradient_line(d, 1051, 650, 1051 + 760, ["#00000000", BLUE, CYAN, EMERALD, "#00000000"], width=2)
    premium_chip(d, 1051, 680, "100% LOCAL · NO CLOUD", EMERALD, fs=16)
    premium_chip(d, 1051 + 280 + 24, 680, "135 CURATED SOURCES", CYAN, fs=16)
    premium_chip(d, 1051 + 280 + 24 + 300 + 24, 680, "28 CRON JOBS · 7 CYCLES", BLUE, fs=16)
    return img.convert("RGB")


# ---------------------------------------------------------------- logos ---
def draw_mark(draw: ImageDraw.ImageDraw, cx, cy, size, color=CYAN, node=BLUE, w=None, img=None):
    """Premium O+X Aperture Nexus: halo, precision ring + ticks, gradient octagon,
    X rays, inner fine octagon, core, node with glint (mirrors mark_svg)."""
    cx, cy, size = int(cx), int(cy), int(size)
    w = w or max(2, size // 22)
    r = size / 2
    lo = _mix_hex(color, "#FFFFFF", 0.06)
    hi = _mix_hex(color, "#FFFFFF", 0.38)

    def vtx(rad, i):
        a = math.radians(22.5 + i * 45)
        return (cx + rad * math.cos(a), cy + rad * math.sin(a))

    # halo behind everything
    if img is not None and img.mode == "RGBA":
        glow(img, draw, cx, cy, int(r * 1.35), node, peak=8, steps=18)

    # outer precision octagon (thin) + vertex ticks
    outer = [vtx(r * 1.17, i) for i in range(8)]
    tw = max(1, w // 5)
    for i in range(8):
        draw.line((*outer[i], *outer[(i + 1) % 8]), fill=lo, width=tw)
    tick = max(2, size * 0.012)
    for px, py in outer:
        draw.ellipse((px - tick, py - tick, px + tick, py + tick), fill=hi)

    # main octagonal ring — 8 segments with a gap at the top-right
    gap_deg = 34.0
    gap_start = 45.0 - gap_deg / 2
    ring = [vtx(r, i) for i in range(8)]
    for i in range(8):
        a0 = i * 45.0
        a1 = a0 + 45.0
        center = (a0 + a1) / 2
        if abs(((center - gap_start + 180) % 360) - 180) < gap_deg / 2 + 5:
            continue
        c = _mix_hex(lo, hi, i / 7)  # angular gradient around the ring
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % 8]
        draw.line((x0, y0, x1, y1), fill=c, width=w)
        # round caps at both ends (matches SVG stroke-linecap="round")
        rc = w / 2
        for ex, ey in ((x0, y0), (x1, y1)):
            draw.ellipse((ex - rc, ey - rc, ex + rc, ey + rc), fill=c)

    # X rays (gradient along each bar)
    ray = r * 0.8
    _grad_line(draw, (cx - ray, cy - ray), (cx + ray, cy + ray), lo, hi, w)
    _grad_line(draw, (cx - ray, cy + ray), (cx + ray, cy - ray), lo, hi, w)

    # inner fine octagon
    inner = [vtx(r * 0.66, i) for i in range(8)]
    iw = max(1, w // 10)
    for i in range(8):
        draw.line((*inner[i], *inner[(i + 1) % 8]), fill=lo, width=iw)

    # central core (rotated square, radial-ish gradient)
    n = size * 0.055
    core_pts = [(cx, cy - n), (cx + n, cy), (cx, cy + n), (cx - n, cy)]
    draw.polygon(core_pts, fill=color)
    for i in range(4):
        draw.line((*core_pts[i], *core_pts[(i + 1) % 4]), fill=_mix_hex(color, hi, 0.5), width=max(1, w // 6))

    # node breaking the ring (top-right): halo + body + glint
    nx, ny = cx + r * 1.06 * math.cos(math.radians(45)), cy - r * 1.06 * math.sin(math.radians(45))
    nr = max(2, int(w * 0.62))
    if img is not None and img.mode == "RGBA":
        glow(img, draw, int(nx), int(ny), int(nr * 2.6), node, peak=10, steps=14)
    draw.ellipse((nx - nr, ny - nr, nx + nr, ny + nr), fill=node)
    gl = max(1, int(nr * 0.32))
    draw.ellipse(
        (nx - nr * 0.25 - gl, ny - nr * 0.25 - gl, nx - nr * 0.25 + gl, ny - nr * 0.25 + gl),
        fill=_mix_hex(node, "#FFFFFF", 0.6),
    )


def lockup(w, h, color=CYAN, bg: str | None = BG, text_color=TEXT, sub_color=MUTED):
    img = Image.new("RGBA", (w, h), bg or (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    mark_sz = h * 0.62
    draw_mark(d, h * 0.62, h / 2, mark_sz, color=color, img=img)
    f_own = display_font(int(h * 0.34), 700)
    own_x = h * 1.15
    own_y = h / 2 - 22
    d.text((own_x, own_y), "OWNEX", font=f_own, fill=text_color, anchor="lm")
    f_tag = font(int(h * 0.115))
    t = "AUTONOMOUS WORK OPERATING SYSTEM"
    # Position tagline below OWNEX, left-aligned, anchor=lt for precise top
    own_bbox = d.textbbox((own_x, own_y), "OWNEX", font=f_own, anchor="lm")
    tag_y = own_bbox[3] + int(h * 0.08)
    d.text((own_x, tag_y), t, font=f_tag, fill=sub_color, anchor="lt")
    return img


# ----------------------------------------------------------- desktop UI ---
SIDEBAR = [
    ("Mission Control", "👁"),
    ("Intelligence", "🧠"),
    ("Targets", "📍"),
    ("Capital", "💰"),
    ("MERLIN", "🤖"),
    ("Agents", "🤖"),
    ("Reports", "📊"),
    ("Settings", "⚙️"),
]

SURFACE_CONTENT = {
    "mission-control": {
        "title": "Mission Control",
        "subtitle": "Live throughput · 7 cycles · 28 jobs",
        "kpis": [
            ("Health Score", "92", "+2.1"),
            ("Findings", "128", "+14"),
            ("USD / hour", "$34.2", "+12%"),
            ("Ready to deliver", "7", "+3"),
        ],
        "charts": [
            ("line", "Revenue — 30d", [10, 18, 14, 26, 22, 34, 30, 44, 40, 58, 52, 66]),
            ("bar", "Findings by platform", [3, 8, 5, 11, 7, 9]),
            ("line", "Hypothesis confidence", [40, 55, 48, 62, 70, 66, 78, 84]),
        ],
        "feed": [
            ("Cycle security advanced to validation", "08:41"),
            ("Finding H1-223 validated · IDOR", "08:12"),
            ("New opportunity · Opire $150", "07:58"),
            ("Work Bank prepared 4 items", "06:15"),
        ],
    },
    "intelligence": {
        "title": "Intelligence",
        "subtitle": "Findings · hypotheses · evidence · confidence",
        "kpis": [
            ("Total findings", "128", "+14"),
            ("Confirmed", "41", "+6"),
            ("Pending validation", "23", "−3"),
            ("Confidence avg", "0.84", "+0.02"),
        ],
        "charts": [
            ("bar", "Findings by severity", [4, 7, 12, 9]),
            ("donut", "Verdict distribution", 0.72),
            ("line", "Confidence over time", [50, 55, 61, 60, 68, 74, 79, 84]),
        ],
        "feed": [
            ("IDOR in /api/v2/orders · high confidence", "0.91"),
            ("SSRF candidate · external host", "0.76"),
            ("XSS stored · param reflection", "0.68"),
            ("Auth bypass · JWT alg confusion", "0.82"),
        ],
    },
    "targets": {
        "title": "Targets",
        "subtitle": "Attack surface · prioritization · scan queues",
        "kpis": [
            ("Active targets", "34", "+5"),
            ("Endpoints mapped", "1,240", "+180"),
            ("Open findings", "23", "−4"),
            ("Next scan", "02:14", "auto"),
        ],
        "charts": [
            ("line", "Endpoints discovered", [120, 260, 410, 590, 760, 940, 1120, 1240]),
            ("bar", "Top platforms by EV", [9, 7, 6, 5, 4]),
            ("donut", "Scan coverage", 0.66),
        ],
        "feed": [
            ("hackerone.com · scope expanded", "EV $2,400"),
            ("app.example.com · 240 endpoints", "EV $1,100"),
            ("api.example.com · 520 endpoints", "EV $980"),
            ("beta.example.io · new program", "EV $640"),
        ],
    },
    "capital": {
        "title": "Capital",
        "subtitle": "Revenue intelligence · payout timelines · ROI",
        "kpis": [
            ("Month total", "$4,860", "+18%"),
            ("Pending", "$1,240", "+$320"),
            ("Best USD/h", "$58.2", "HackerOne"),
            ("Avg payout", "14d", "−2d"),
        ],
        "charts": [
            ("line", "Revenue — 6 months", [12, 18, 22, 30, 38, 48]) * 2,
            ("bar", "USD/hour by platform", [58, 41, 33, 27, 19]),
            ("donut", "Accepted rate", 0.71),
        ],
        "feed": [
            ("HackerOne payout received", "$1,500"),
            ("Bugcrowd payout received", "$750"),
            ("Fiverr order completed", "$180"),
            ("Opire bounty paid", "$150"),
        ],
    },
    "merlin": {
        "title": "MERLIN",
        "subtitle": "Voice-first assistant · calm_operator · persistent memory",
        "kpis": [
            ("Commands today", "42", "+9"),
            ("Voice replies", "28", "+4"),
            ("Memory entries", "1,876", "+32"),
            ("Accuracy", "0.96", "0.0"),
        ],
        "charts": [
            ("wave", "Voice waveform", 40),
            ("line", "Assistance requests", [12, 16, 15, 22, 28, 31, 36, 42]),
            ("donut", "Intent coverage", 0.88),
        ],
        "feed": [
            ("“what is my top opportunity today?”", "→ answered 06:15"),
            ("“prepare the fiverr delivery”", "→ done 09:02"),
            ("“any critical findings?”", "→ 0 critical, 2 high"),
            ("“summarize the week”", "→ briefing sent"),
        ],
    },
    "agents": {
        "title": "Agents",
        "subtitle": "12 departmental specialists · autonomous fleet",
        "kpis": [("Active", "9", "+1"), ("Working", "4", "now"), ("Idle", "3", "−1"), ("Errors 24h", "0", "clean")],
        "charts": [
            ("bars", "Workload by agent", [8, 6, 7, 5, 9, 4, 6, 5, 7, 3, 6, 4]),
            ("donut", "Fleet health", 0.92),
            ("line", "Tasks completed", [20, 26, 24, 34, 38, 42, 48, 55]),
        ],
        "feed": [
            ("Security · validated 3 findings", "idle"),
            ("Coding · built delivery package", "done"),
            ("Revenue · scanned 135 sources", "done"),
            ("QA · ran 28 regression tests", "done"),
        ],
    },
    "reports": {
        "title": "Reports",
        "subtitle": "Generation · submission · acceptance tracking",
        "kpis": [
            ("Submitted", "17", "+3"),
            ("Accepted", "11", "+2"),
            ("Pending review", "4", "0"),
            ("Acceptance rate", "64%", "+5%"),
        ],
        "charts": [
            ("bar", "Submissions by platform", [5, 4, 3, 3, 2]),
            ("line", "Acceptance trend", [30, 38, 45, 44, 52, 58, 61, 64]),
            ("donut", "Report quality", 0.81),
        ],
        "feed": [
            ("IDOR report → accepted", "HackerOne · $1,500"),
            ("SSRF report → triaged", "Bugcrowd · $750"),
            ("XSS report → duplicate", "HackerOne · 0"),
            ("CSRF report → accepted", "Intigriti · $400"),
        ],
    },
    "settings": {
        "title": "Settings",
        "subtitle": "Configuration · providers · scheduler · security",
        "kpis": [
            ("AI providers", "5/9", "active"),
            ("Scheduled jobs", "28", "running"),
            ("Backups", "12", "verified"),
            ("Security score", "100", "perfect"),
        ],
        "charts": [
            ("donut", "Storage used", 0.41),
            ("bars", "Jobs by cycle", [5, 4, 4, 4, 4, 2, 5]),
            ("line", "Uptime — 30d", [100, 100, 99, 100, 100, 100, 100, 100]),
        ],
        "feed": [
            ("Scheduler tick ok · 28 jobs", "every 30s"),
            ("IdentityVault sealed", "AES-256-GCM"),
            ("CSRF middleware active", "double-submit"),
            ("Backup verified", "SHA-256 ok"),
        ],
    },
    "cycles": {
        "title": "Work Cycles",
        "subtitle": "Security · Forge · Pulse · Vault · Atlas · QA · Direct Work",
        "kpis": [
            ("Running", "3", "now"),
            ("Completed today", "7", "+1"),
            ("Jobs", "28", "cron"),
            ("Findings today", "14", "+6"),
        ],
        "charts": [
            ("bars", "Cycle progress", [7, 6, 5, 4, 4, 3, 7]),
            ("donut", "Cycle completion", 0.78),
            ("line", "Automation %, 30d", [40, 52, 58, 63, 68, 72, 75, 79]),
        ],
        "feed": [
            ("Security · stage 4/7 validation", "running"),
            ("Forge · 22 bounties ranked", "done"),
            ("Pulse · 135 sources scanned", "done"),
            ("Vault · portfolio synced", "done"),
        ],
    },
    "manuals": {
        "title": "Manuals",
        "subtitle": "Playbooks · guides · runbooks",
        "kpis": [
            ("Documents", "26", "+2"),
            ("Playbooks", "9", "ready"),
            ("Guides", "14", "ready"),
            ("Updated", "today", "auto"),
        ],
        "charts": [
            ("bars", "Docs by category", [6, 5, 4, 4, 3, 4]),
            ("donut", "Coverage", 0.86),
            ("line", "Weekly reads", [14, 18, 16, 22, 26, 25, 30, 34]),
        ],
        "feed": [
            ("Setup guide · v7.0.0", "updated"),
            ("Bug bounty playbook · IDOR focus", "ready"),
            ("Fiverr delivery runbook", "ready"),
            ("Security policy · reviewed", "ok"),
        ],
    },
    "direct-work": {
        "title": "Direct Work",
        "subtitle": "Zero-barrier opportunities · ranked by EV",
        "kpis": [
            ("Scanned today", "135", "+12"),
            ("Ready to deliver", "7", "+3"),
            ("Needs access", "4", "−1"),
            ("Best EV", "$240", "Opire"),
        ],
        "charts": [
            ("bar", "EV by platform", [9, 7, 6, 5, 4, 3]),
            ("donut", "Success floor", 0.68),
            ("line", "Accepted, 30d", [20, 24, 28, 27, 33, 38, 41, 45]),
        ],
        "feed": [
            ("opire · Python CLI refactor", "$150 · 88%"),
            ("issuehunt · API pagination bug", "$90 · 82%"),
            ("freelancer · data pipeline script", "$240 · 74%"),
            ("github · OSS docs improvement", "$60 · 91%"),
        ],
    },
    "daily-companion": {
        "title": "Daily Companion",
        "subtitle": "The morning briefing · one call, everything",
        "kpis": [
            ("System health", "92", "ready"),
            ("Tasks today", "5", "+2"),
            ("Market top", "HackerOne", "stable"),
            ("Projected month", "$6.1k", "+12%"),
        ],
        "charts": [
            ("line", "Projected earnings", [30, 42, 48, 55, 60, 66, 70, 75]),
            ("donut", "Focus balance", 0.62),
            ("bar", "Sources by tier", [8, 6, 3]),
        ],
        "feed": [
            ("Briefing generated", "06:15"),
            ("Top action: prepare Opire delivery", "EV $150"),
            ("Skill gap: reverse engineering", "plan ready"),
            ("3 improvements proposed", "2 approved"),
        ],
    },
    "work-bank": {
        "title": "Work Bank",
        "subtitle": "Prepared work · ready to deliver",
        "kpis": [
            ("Prepared", "7", "+3"),
            ("Delivered", "23", "+2"),
            ("Accepted", "15", "+1"),
            ("Projected 30d", "$3.4k", "+8%"),
        ],
        "charts": [
            ("bar", "Bank by platform", [5, 4, 4, 3, 2]),
            ("line", "Deliveries 30d", [10, 14, 13, 18, 22, 21, 26, 30]),
            ("donut", "Success rate", 0.71),
        ],
        "feed": [
            ("Python automation · Fiverr", "$240 · ready"),
            ("API integration · Fiverr", "$180 · ready"),
            ("Bug fix · Upwork", "$150 · needs access"),
            ("Data pipeline · Opire", "$120 · ready"),
        ],
    },
    "executive-dashboard": {
        "title": "Executive Dashboard",
        "subtitle": "Verdict: +$4,860 this month · on track",
        "kpis": [
            ("Weekly", "$1,420", "+22%"),
            ("Monthly", "$4,860", "+18%"),
            ("USD/hour", "$34.2", "+12%"),
            ("Time to payout", "14d", "−2d"),
        ],
        "charts": [
            ("line", "Revenue vs target", [30, 38, 44, 52, 58, 66, 72, 80]),
            ("bar", "USD/h by platform", [58, 41, 33, 27, 19]),
            ("donut", "Revenue mix", 0.55),
        ],
        "feed": [
            ("Made money this week: yes", "+$1,420"),
            ("Top platform: HackerOne", "$58/h"),
            ("Projection: $6.1k by month end", "+12%"),
            ("5 work cycles active", "all healthy"),
        ],
    },
    "voice": {
        "title": "OWNEX Voice",
        "subtitle": "Native mic · Piper TTS · calm_operator",
        "kpis": [
            ("Session status", "listening", "mic"),
            ("STT", "native", "APK"),
            ("TTS", "piper", "es-419"),
            ("Replies today", "28", "+4"),
        ],
        "charts": [
            ("wave", "Voice activity", 46),
            ("line", "Voice commands 30d", [18, 22, 21, 28, 34, 38, 40, 42]),
            ("donut", "TTS coverage", 0.94),
        ],
        "feed": [
            ("“resultado, IDOR confirmado”", "replied"),
            ("“prepará la entrega”", "done"),
            ("“estado del sistema”", "92 · ready"),
            ("“resumí el brief”", "sent"),
        ],
    },
    "calendar": {
        "title": "Calendar",
        "subtitle": "Scheduled opportunities · progress tracking",
        "kpis": [
            ("This week", "11", "+3"),
            ("Upcoming", "6", "planned"),
            ("Deliveries", "4", "this week"),
            ("Targets met", "9/11", "82%"),
        ],
        "charts": [
            ("bars", "Workload by day", [4, 5, 3, 6, 4, 2, 1]),
            ("donut", "Week completion", 0.62),
            ("line", "Deliveries 8w", [6, 8, 9, 8, 12, 13, 15, 18]),
        ],
        "feed": [
            ("Mon · prepare 3 deliveries", "ready"),
            ("Wed · Fiverr delivery due", "reminder"),
            ("Fri · Opire bounty deadline", "24h"),
            ("Sun · weekly review", "auto"),
        ],
    },
    "threat-intel": {
        "title": "Threat Intelligence",
        "subtitle": "CISA KEV · proactive hypotheses · recency-calibrated",
        "kpis": [
            ("KEV entries", "1,210", "synced"),
            ("Matched stack", "7", "+3"),
            ("Hypotheses", "14", "new"),
            ("Active campaigns", "3", "tracked"),
        ],
        "charts": [
            ("line", "Exploited CVEs 30d", [20, 34, 42, 50, 58, 66, 74, 86]),
            ("bar", "Hypotheses by severity", [5, 8, 6, 3]),
            ("donut", "Recency ≤30d", 0.58),
        ],
        "feed": [
            ("CVE-2026-1843 · exploited · matches nginx", "likelihood 0.95"),
            ("CVE-2026-0121 · ransomware · matches java", "0.87"),
            ("CVE-2026-0032 · exploited · matches postgres", "0.80"),
            ("CVE-2025-8220 · exploited · no match", "skipped"),
        ],
    },
    "notifications": {
        "title": "Notifications",
        "subtitle": "Smart alerts · dedup · priority",
        "kpis": [
            ("Today", "18", "−6"),
            ("Critical", "1", "0"),
            ("Digest ready", "06:30", "sent"),
            ("Sources", "14", "events"),
        ],
        "charts": [
            ("bar", "Alerts by priority", [2, 6, 8, 2]),
            ("line", "Alerts 7d", [22, 18, 25, 19, 16, 21, 18]),
            ("donut", "Read rate", 0.77),
        ],
        "feed": [
            ("High · finding validated · IDOR", "09:02"),
            ("Info · new opportunity · Opire", "07:58"),
            ("Success · payout $1,500", "06:44"),
            ("Info · daily digest ready", "06:30"),
        ],
    },
}


def render_surface(name: str, spec: dict) -> Image.Image:
    w, h = 1600, 1000
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    random.seed(sum(map(ord, name)))

    # sidebar
    rr(d, (0, 0, 220, h), r=0, fill=SURFACE)
    draw_mark(d, 44, 42, 40, color=CYAN, node=BLUE, img=img)
    text(d, (70, 42), "OWNEX", display_font(18, 700), anchor="lm")
    for i, (label, _icon) in enumerate(SIDEBAR):
        sel = label.lower() in name or (name == "mission-control" and label == "Mission Control")
        y = 90 + i * 44
        if sel:
            rr(d, (12, y, 208, y + 32), r=8, fill=BLUE + "22", outline=BLUE + "44", width=1)
            text(d, (28, y + 16), label, font(13, 600), fill=WHITE, anchor="lm")
        else:
            text(d, (28, y + 16), label, font(13, 500), fill=MUTED, anchor="lm")
    text(d, (28, h - 54), "v7.0.0 · tesla", font(10), fill=MUTED)

    # top bar
    text(d, (252, 34), spec["title"], display_font(26, 700))
    text(d, (252, 66), spec["subtitle"], font(12), fill=MUTED)
    chip(d, 252 + int(d.textlength(spec["title"], display_font(26, 700))) + 24, 38, "● LIVE", EMERALD)

    # KPI row
    kw = (w - 252 - 48 - 3 * 16) / 4
    for i, (lab, val, delta) in enumerate(spec["kpis"]):
        kpi(d, 252 + i * (kw + 16), 92, kw, 88, lab, val, delta)

    # charts row (3 cards)
    cw = (w - 252 - 48 - 2 * 16) / 3
    cy0 = 196
    ch = 300
    for i, chart in enumerate(spec["charts"]):
        x = 252 + i * (cw + 16)
        kind, label, data = chart[0], chart[1], chart[2]
        card(d, (x, cy0, x + cw, cy0 + ch), title=label)
        box = (x + 16, cy0 + 56, x + cw - 16, cy0 + ch - 16)
        if kind == "line":
            ov = sparkline(d, box, [v * 1.0 for v in data], color=CYAN)
            if ov:
                img.paste(ov[0], ov[1], ov[0])
        elif kind == "bar":
            bars(d, box, data, color=BLUE)
        elif kind == "bars":
            bars(d, box, data, color=EMERALD)
        elif kind == "donut":
            donut(d, (x + cw // 2), cy0 + 150, 62, data, color=CYAN)
            text(d, (x + cw // 2, cy0 + 150), f"{int(data * 100)}%", display_font(20, 700), anchor="mm")
        elif kind == "wave":
            xs = list(range(0, int(box[2] - box[0]), 14))
            ys = [box[3] - 4 - (random.randint(0, data * 2)) for _ in xs]
            d.line([(box[0] + x, y) for x, y in zip(xs, ys, strict=False)], fill=CYAN, width=2)

    # feed card
    fy0 = cy0 + ch + 16
    card(d, (252, fy0, w - 48, h - 40), title="Activity")
    for i, (msg, meta) in enumerate(spec["feed"]):
        y = fy0 + 56 + i * 44
        status_dot(d, 268, y + 14, EMERALD if i < 2 else MUTED)
        text(d, (284, y), msg, font(13, 500), fill=TEXT)
        text(d, (w - 72, y), meta, font(11), fill=MUTED, anchor="ra")

    return img


# ------------------------------------------------------------ mobile UI ---
MOBILE_SCREENS = {
    "omega-home": {
        "title": "Good morning, Adriel",
        "subtitle": "Today's top opportunity",
        "top": ("HackerOne · IDOR validation", "$1,500 · 88%", "PREPARE"),
        "metrics": [("Health", "92", EMERALD), ("Ready", "7", CYAN), ("USD/h", "$34", ORANGE)],
        "items": [
            ("opire · CLI refactor", "$150 · 88%"),
            ("issuehunt · pagination bug", "$90 · 82%"),
            ("fiverr · API integration", "$240 · 74%"),
        ],
    },
    "omega-opportunities": {
        "title": "Opportunities",
        "subtitle": "Work Bank · ranked by EV",
        "top": ("Filter: ready_to_deliver", "7 items", "RANK"),
        "metrics": [("Best EV", "$240", EMERALD), ("Delivered", "23", CYAN), ("Accepted", "15", ORANGE)],
        "items": [
            ("fiverr · Python automation", "$240 · 74%"),
            ("opire · CLI refactor", "$150 · 88%"),
            ("issuehunt · pagination bug", "$90 · 82%"),
            ("fiverr · bug fixing", "$180 · 71%"),
            ("upwork · data pipeline", "$120 · 66%"),
        ],
    },
    "omega-opportunity-detail": {
        "title": "Opportunity",
        "subtitle": "opire · CLI refactor",
        "top": ("Expected value", "$150 · 88% acceptance", "PREPARE"),
        "metrics": [("Effort", "3h", EMERALD), ("Payout", "7d", CYAN), ("Barrier", "0", ORANGE)],
        "items": [
            ("Requirement: refactor CLI arg parser", "clear"),
            ("Requirement: add --json output", "clear"),
            ("Portfolio: not required", "clear"),
            ("Preparation: package ready", "done"),
        ],
    },
    "omega-merlin": {
        "title": "MERLIN",
        "subtitle": "Hold to talk · es-419",
        "top": ("Resultado, IDOR confirmado", "confidence 0.91", "EQ"),
        "metrics": [("STT", "native", EMERALD), ("TTS", "piper", CYAN), ("Memory", "1.8k", ORANGE)],
        "items": [
            ("“what is my top opportunity today?”", "answered"),
            ("“prepare the fiverr delivery”", "done"),
            ("“any critical findings?”", "0 critical"),
        ],
    },
    "omega-agents": {
        "title": "Agent Fleet",
        "subtitle": "12 specialists · 9 active",
        "top": ("Security · validating 2 findings", "working", "PAUSE"),
        "metrics": [("Active", "9", EMERALD), ("Working", "4", CYAN), ("Errors", "0", ORANGE)],
        "items": [
            ("Security", "working"),
            ("Coding", "done"),
            ("QA", "idle"),
            ("Revenue", "scanning"),
            ("Research", "idle"),
            ("Evolution", "idle"),
        ],
    },
    "omega-settings": {
        "title": "Settings",
        "subtitle": "Mobile preferences",
        "top": ("Biometric unlock", "enabled", "ON"),
        "metrics": [("Push", "on", EMERALD), ("Voice", "es-419", CYAN), ("Theme", "tesla", ORANGE)],
        "items": [
            ("Biometric unlock", "FaceID"),
            ("Push notifications", "high only"),
            ("Voice language", "es-419"),
            ("Theme", "Tesla dark"),
            ("Offline mode", "auto"),
        ],
    },
    "omega-notification": {
        "title": "09:41",
        "subtitle": "Tuesday, August 11",
        "top": ("Finding validated · IDOR", "high confidence", "OPEN"),
        "metrics": [("HackerOne", "$1,500", EMERALD), ("Severity", "high", CYAN), ("Confidence", "0.91", ORANGE)],
        "items": [
            ("Finding H1-223 · IDOR in /api/v2/orders", "validated"),
            ("Evidence: 3 verifications passed", "ok"),
            ("Action: prepare report", "ready"),
            ("Reward estimate", "$1,500"),
        ],
    },
    "omega-watch": {
        "title": "09:41",
        "subtitle": "Watch Companion",
        "top": ("System online · 92", "2 findings high", "OPEN"),
        "metrics": [("Cycles", "3", EMERALD), ("Approvals", "1", CYAN), ("Alerts", "2", ORANGE)],
        "items": [("IDOR validated", "open"), ("New opportunity · opire", "open"), ("Daily briefing", "read")],
    },
    "omega-hero": {
        "title": "OMEGA",
        "subtitle": "The pocket command center",
        "top": ("Top pick · $1,500 · 88%", "one tap to prepare", "GET"),
        "metrics": [("EV ranking", "live", EMERALD), ("Voice", "native", CYAN), ("Watch", "sync", ORANGE)],
        "items": [
            ("Today View", "one-tap execution"),
            ("Opportunities", "swipeable bank"),
            ("MERLIN Voice", "hold to talk"),
        ],
    },
}


def render_mobile(name: str, spec: dict) -> Image.Image:
    w, h = 1290, 2796
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    random.seed(sum(map(ord, name)))

    pad = 64
    rr(d, (pad, pad, w - pad, h - pad), r=80, fill=SURFACE, outline=HAIRLINE, width=3)
    rr(d, (pad + 24, pad + 24, w - pad - 24, h - pad - 24), r=56, fill=BG)

    x0, y0, x1, y1 = pad + 24, pad + 24, w - pad - 24, h - pad - 24
    # dynamic island + status bar
    rr(d, (w // 2 - 110, y0 + 18, w // 2 + 110, y0 + 56), r=20, fill="#000000")
    text(d, (x0 + 12, y0 + 30), "9:41", display_font(26, 600), anchor="lm")
    signal_bars(d, x1 - 12, y0 + 30)

    # header
    text(d, (x0 + 12, y0 + 120), spec["title"], display_font(44, 700))
    text(d, (x0 + 12, y0 + 182), spec["subtitle"], font(24), fill=MUTED)

    # hero card
    top_t, top_m, btn = spec["top"]
    hx0, hy0 = x0 + 12, y0 + 240
    rr(d, (hx0, hy0, x1 - 12, hy0 + 330), r=36, fill=SURFACE2, outline=HAIRLINE, width=2)
    text(d, (hx0 + 40, hy0 + 44), top_t, display_font(32, 600))
    text(d, (hx0 + 40, hy0 + 104), top_m, font(24), fill=MUTED)
    rr(d, (x1 - 12 - 260, hy0 + 200, x1 - 12 - 40, hy0 + 276), r=38, fill=BLUE)
    if btn == "EQ":
        equalizer(d, x1 - 12 - 150, hy0 + 238)
    else:
        text(d, (x1 - 12 - 150, hy0 + 238), btn, display_font(26, 700), fill=WHITE, anchor="mm")

    # metrics row
    mw = (x1 - x0 - 24 - 2 * 16) / 3
    for i, (lab, val, col) in enumerate(spec["metrics"]):
        mx = x0 + 12 + i * (mw + 16)
        rr(d, (mx, hy0 + 360, mx + mw, hy0 + 500), r=28, fill=SURFACE, outline=HAIRLINE, width=2)
        text(d, (mx + 28, hy0 + 392), lab, font(22), fill=MUTED)
        text(d, (mx + 28, hy0 + 436), val, display_font(30, 700), fill=col)

    # item list
    ly = hy0 + 540
    for i, (t1, t2) in enumerate(spec["items"]):
        iy = ly + i * 150
        rr(d, (x0 + 12, iy, x1 - 12, iy + 126), r=28, fill=SURFACE, outline=HAIRLINE, width=2)
        status_dot(d, x0 + 52, iy + 63, EMERALD if i < 2 else MUTED, r=9)
        text(d, (x0 + 84, iy + 44), t1, font(26, 500), fill=TEXT)
        text(d, (x0 + 84, iy + 88), t2, font(22), fill=MUTED)

    # bottom tab bar
    tb = y1 - 60
    rr(d, (x0, tb - 150, x1, tb), r=56, fill=SURFACE, outline=HAIRLINE, width=2)
    tabs = ["Home", "Bank", "MERLIN", "Fleet"]
    for i, t in enumerate(tabs):
        cx = x0 + (x1 - x0) * (i + 0.5) / len(tabs)
        col = CYAN if i == 0 else MUTED
        text(d, (cx, tb - 75), t, font(24, 600), fill=col, anchor="mm")
    return img


# ------------------------------------------------------ architecture UI ---
def render_architecture(name: str) -> Image.Image:
    w, h = 1600, 900
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    arrow = lambda x0, y0, x1, y1: (
        d.line((x0, y0, x1, y1), fill=MUTED, width=3)
        or d.polygon(((x1, y1), (x1 - 14, y1 - 8), (x1 - 14, y1 + 8)), fill=MUTED)
    )

    def col_title(x: float, y: int, t: str, col: str, dot_r: int = 7) -> None:
        status_dot(d, x + 14, y + 13, col, r=dot_r)
        text(d, (x + 36, y), t, display_font(22, 700), fill=col)

    if name == "system":
        title = "System Architecture — modular monolith + EventBus"
        cols = [
            ("Presentation", CYAN, ["Mission Control · Vue 3", "Desktop · Tauri v2", "OMEGA Mobile", "MERLIN"]),
            (
                "Core Platform",
                BLUE,
                ["EventBus", "Scheduler · 28 jobs", "Unified Memory", "IdentityVault", "Health Center"],
            ),
            ("Work Cycles", EMERALD, ["Security", "Forge", "Pulse", "Vault", "Atlas", "QA", "Direct Work"]),
            ("Engines", ORANGE, ["DWE", "Revenue Intel", "Opportunity", "Validation", "Evolution", "OAR AI"]),
        ]
        y0, boxh = 200, 560
        bw = 300
        gap = (w - 80 - 4 * bw) / 3
        for i, (t, col, items) in enumerate(cols):
            x = 40 + i * (bw + gap)
            rr(d, (x, y0, x + bw, y0 + boxh), r=20, fill=SURFACE, outline=HAIRLINE, width=2)
            col_title(x + 24, y0 + 26, t, col)
            for j, it in enumerate(items):
                text(d, (x + 24, y0 + 90 + j * 48), it, font(17, 500), fill=TEXT if j < 3 else MUTED)
            if i < 3:
                arrow(x + bw, y0 + boxh // 2, x + bw + gap, y0 + boxh // 2)
        text(d, (80, 120), title, display_font(30, 700))
        chip(d, 80, 790, "No microservices · one process · one database", EMERALD, 14)
        chip(
            d,
            80 + int(d.textlength("No microservices · one process · one database", font(14, 600))) + 40,
            790,
            "28 scheduled jobs",
            CYAN,
            14,
        )

    elif name == "mobile":
        title = "OMEGA Mobile Architecture"
        cols = [
            ("OMEGA App", CYAN, ["Today View", "Work Bank", "MERLIN Voice", "Agent Fleet", "Settings"]),
            (
                "API Layer",
                BLUE,
                ["/api/direct-work/*", "/api/voice/*", "/api/agents/*", "/api/wear-os/*", "REST + WS"],
            ),
            ("Core Platform", EMERALD, ["EventBus", "Scheduler", "Unified Memory", "IdentityVault"]),
        ]
        y0, boxh = 210, 520
        bw = 340
        gap = (w - 80 - 3 * bw) / 2
        for i, (t, col, items) in enumerate(cols):
            x = 40 + i * (bw + gap)
            rr(d, (x, y0, x + bw, y0 + boxh), r=20, fill=SURFACE, outline=HAIRLINE, width=2)
            col_title(x + 24, y0 + 26, t, col)
            for j, it in enumerate(items):
                text(d, (x + 24, y0 + 90 + j * 48), it, font(17, 500))
            if i < 2:
                arrow(x + bw, y0 + boxh // 2, x + bw + gap, y0 + boxh // 2)
        text(d, (80, 120), title, display_font(30, 700))
        chip(d, 80, 790, "Offline-first · biometric unlock · push deep links", ORANGE, 14)

    else:  # data-flow
        title = "EventBus Data Flow"
        nodes = [
            ("Scheduler", 60, 380),
            ("Work Cycles", 380, 380),
            ("Engines", 700, 380),
            ("Unified Memory", 1020, 380),
            ("Mission Control", 1340, 380),
        ]
        text(d, (80, 120), title, display_font(30, 700))
        for i, (t, x, y) in enumerate(nodes):
            rr(d, (x, y, x + 200, y + 100), r=16, fill=SURFACE, outline=HAIRLINE, width=2)
            text(d, (x + 100, y + 50), t, display_font(18, 600), anchor="mm")
            if i < len(nodes) - 1:
                arrow(x + 200, y + 50, x + 260, y + 50)
        rr(d, (60, 620, 1540, 720), r=16, fill=SURFACE2, outline=HAIRLINE, width=2)
        text(d, (80, 648), "event → handler → publish → subscribers (persisted, SQLite)", font(20, 500))
        chip(d, 80, 790, "finding:* · opportunity:* · report:* · system:* · financial:*", CYAN, 14)
    return img


# --------------------------------------------------------------- hero ---
def frame_surface(img: Image.Image, pad=56, radius=20) -> Image.Image:
    """Premium frame for desktop surface renders: backdrop + rounded app window."""
    w, h = img.size
    cw, ch = w + pad * 2, h + pad * 2
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = gradient_bg(canvas, (7, 8, 13), (4, 5, 8))
    glow(canvas, d, cw // 2, 0, int(cw * 0.55), BLUE, peak=9, steps=20)
    glow(canvas, d, cw // 2, ch, int(cw * 0.4), CYAN, peak=5, steps=16)
    grid_faded(canvas, cw // 2, ch // 2, step=140, base=(13, 16, 22), peak=26)
    grain(canvas, seed=20260814, n=14000, alpha=6)

    box = (pad, pad, pad + w, pad + h)
    card_shadow(canvas, box, r=radius, offset=(0, 26), blur=46, alpha=160)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    canvas.paste(img, (pad, pad), mask)
    dd = ImageDraw.Draw(canvas)
    dd.rounded_rectangle(box, radius=radius, outline=HAIRLINE, width=2)
    dd.rounded_rectangle(box, radius=radius, outline="#0A0C11", width=1)
    return canvas


def frame_device(img: Image.Image, pad=40, radius=72) -> Image.Image:
    """Premium device frame: dark bezel + screen inset + soft floor shadow."""
    w, h = img.size
    cw = w + pad * 2
    ch = h + pad * 2
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = gradient_bg(canvas, (7, 8, 13), (3, 4, 7))
    glow(canvas, d, cw // 2, 0, int(cw * 0.6), CYAN, peak=6, steps=18)
    grid_faded(canvas, cw // 2, ch // 2, step=100, base=(13, 16, 22), peak=24)
    grain(canvas, seed=20260815, n=10000, alpha=5)

    bezel = (pad - 6, pad - 6, pad + w + 6, pad + h + 6)
    card_shadow(canvas, bezel, r=radius + 6, offset=(0, 30), blur=50, alpha=170)
    ImageDraw.Draw(canvas).rounded_rectangle(bezel, radius=radius + 6, fill="#000000", outline="#262B35", width=4)

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    canvas.paste(img, (pad, pad), mask)
    dd = ImageDraw.Draw(canvas)
    dd.rounded_rectangle((pad, pad, pad + w, pad + h), radius=radius, outline=HAIRLINE, width=2)
    return canvas


def render_hero(mode: str = "dark") -> Image.Image:
    w, h = 2400, 900
    if mode == "light":
        light_bg = "#F4F6F9"
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = gradient_bg(img, (250, 251, 253), (227, 232, 240))
        glow(img, d, w // 2, 240, 900, "#1E40FF", peak=14, steps=22)
        glow(img, d, 780, 500, 500, "#0EA5C9", peak=10, steps=20)
        grid_faded(img, w // 2, h // 2, base=(203, 210, 222), peak=38)
        grain(img, seed=20260813, n=14000, alpha=5, color=(24, 29, 40))
        d = ImageDraw.Draw(img)
        d.line((0, 0, w, 0), fill="#D5DAE3", width=1)
        corner_ticks(d, w, h, color="#C3CAD6")

        eyebrow(d, w, "PERSONAL AUTONOMOUS WORK OPERATING SYSTEM", 175, fs=20, color="#5C6575", hair="#CDD3DE")

        draw_mark(d, 770, 500, 360, color="#0EA5C9", node="#1E40FF", img=img)
        gradient_text(img, (1045, 470), "OWNEX", display_font(170, 700), "#0D0F14", "#1E40FF")
        d = ImageDraw.Draw(img)
        tracked_text(d, (1051, 582), "AUTONOMOUS WORK OPERATING SYSTEM", font(28), "#4B5563", tracking=16)
        d.line((1051, 650, 1051 + 760, 650), fill="#CDD3DE", width=1)

        hero_pills(
            d,
            w,
            [
                ("100% LOCAL · NO CLOUD", "#00A37A"),
                ("135 CURATED SOURCES", "#0EA5C9"),
                ("28 CRON JOBS · 7 CYCLES", "#1E40FF"),
            ],
            h - 120,
            fill="#FFFFFF",
            outline="#D5DAE3",
            tcol="#0D0F14",
        )
        return flatten(img, bg=light_bg)

    img = Image.new("RGBA", (w, h), _hex(BG) + (255,))
    d = gradient_bg(img, (5, 6, 10), (10, 13, 19))
    glow(img, d, w // 2, 240, 900, BLUE, peak=40, steps=22)
    glow(img, d, 780, 500, 500, CYAN, peak=30, steps=20)
    grid_faded(img, w // 2, h // 2)
    grain(img, seed=20260812, n=18000, alpha=7)
    d = ImageDraw.Draw(img)
    d.line((0, 0, w, 0), fill="#262B35", width=1)
    corner_ticks(d, w, h)

    eyebrow(d, w, "PERSONAL AUTONOMOUS WORK OPERATING SYSTEM", 175, fs=20)

    draw_mark(d, 770, 500, 360, color=CYAN, node=BLUE, img=img)
    gradient_text(img, (1045, 470), "OWNEX", display_font(170, 700), "#FFFFFF", "#8FD8FF")
    d = ImageDraw.Draw(img)
    tracked_text(d, (1051, 582), "AUTONOMOUS WORK OPERATING SYSTEM", font(28), "#8A93A3", tracking=16)
    d.line((1051, 650, 1051 + 760, 650), fill=HAIRLINE, width=1)

    hero_pills(
        d,
        w,
        [("100% LOCAL · NO CLOUD", EMERALD), ("135 CURATED SOURCES", CYAN), ("28 CRON JOBS · 7 CYCLES", BLUE)],
        h - 120,
    )
    return flatten(img)


def render_og() -> Image.Image:
    w, h = 1200, 630
    img = Image.new("RGBA", (w, h), _hex(BG) + (255,))
    d = gradient_bg(img, (5, 6, 10), (10, 13, 19))
    glow(img, d, w // 2, 165, 480, BLUE, peak=34, steps=18)
    glow(img, d, 275, 345, 300, CYAN, peak=26, steps=16)
    grid_faded(img, w // 2, h // 2, step=90)
    grain(img, seed=20260813, n=9000, alpha=6)
    d = ImageDraw.Draw(img)
    d.line((0, 0, w, 0), fill="#262B35", width=1)
    corner_ticks(d, w, h, length=45, color="#232832")

    eyebrow(d, w, "AUTONOMOUS WORK OPERATING SYSTEM", 120, fs=14)

    draw_mark(d, 285, 345, 210, color=CYAN, node=BLUE, img=img)
    gradient_text(img, (445, 325), "OWNEX", display_font(88, 700), "#FFFFFF", "#8FD8FF")
    d = ImageDraw.Draw(img)
    tracked_text(d, (448, 385), "AUTONOMOUS WORK OPERATING SYSTEM", font(17), "#8A93A3", tracking=8)
    d.line((448, 428, 448 + 430, 428), fill=HAIRLINE, width=1)

    hero_pills(
        d,
        w,
        [("100% LOCAL · NO CLOUD", EMERALD), ("28 JOBS · 7 CYCLES", CYAN)],
        h - 118,
        fs=14,
    )
    return flatten(img)


# ----------------------------------------------------------------- main ---
def make_surface_renderer(name: str, spec: dict) -> Callable[[], Image.Image]:
    return lambda: frame_surface(render_surface(name, spec))


def make_mobile_renderer(name: str, spec: dict) -> Callable[[], Image.Image]:
    return lambda: frame_device(render_mobile(name, spec))


ASSETS = {
    "hero": {
        "hero-banner-dark.png": lambda: render_hero("dark"),
        "hero-banner-light.png": lambda: render_hero("light"),
        "hero-premium.png": lambda: render_hero_premium(),
    },
    "logo": {
        "lockup-horizontal.png": lambda: lockup(2048, 512),
        "lockup-horizontal-light.png": lambda: lockup(2048, 512, bg=None, text_color="#0D0F14", sub_color="#4B5563"),
        "lockup-premium-dark.png": lambda: render_lockup_premium(2048, 512),
        "lockup-premium-light.png": lambda: render_lockup_premium(
            2048, 512, bg=None, text_color="#0D0F14", sub_color="#4B5563"
        ),
        "mark-aperture-alpha.png": lambda: mark_img(1024, CYAN, BLUE, bg=None),
        "mark-aperture-omega.png": lambda: mark_img(1024, EMERALD, CYAN, bg=None),
        "mark-mono-white.png": lambda: mark_img(1024, WHITE, WHITE, bg=None),
        "mark-mono-black.png": lambda: mark_img(1024, "#0D0F14", "#0D0F14", bg=None),
    },
    "deliverables": {
        "mark-card-alpha.png": lambda: render_mark_card(200, CYAN, BLUE, "ALPHA", CYAN),
        "mark-card-omega.png": lambda: render_mark_card(200, EMERALD, CYAN, "OMEGA", EMERALD),
        "mark-card-mono.png": lambda: render_mark_card(200, WHITE, WHITE, "MONO", MUTED),
        "lockup-card.png": lambda: render_lockup_premium(
            1200, 160, color=CYAN, bg=SURFACE, text_color=TEXT, sub_color=MUTED
        ),
        "deliverables-grid.png": lambda: render_deliverables_grid(),
    },
    "footer": {
        "footer-lockup.png": lambda: render_footer_lockup(),
    },
    "desktop": {f"{name}.png": make_surface_renderer(name, spec) for name, spec in SURFACE_CONTENT.items()},
    "mobile": {f"{name}.png": make_mobile_renderer(name, spec) for name, spec in MOBILE_SCREENS.items()},
    "architecture": {
        "system.png": lambda: render_architecture("system"),
        "mobile.png": lambda: render_architecture("mobile"),
        "data-flow.png": lambda: render_architecture("data-flow"),
    },
    "social": {"og-image.png": lambda: render_og()},
}


def mark_img(size: int, color: str, node: str, bg: str | None = None) -> Image.Image:
    img = Image.new("RGBA", (size, size), bg or (0, 0, 0, 0))
    draw_mark(ImageDraw.Draw(img), size / 2, size / 2, size * 0.78, color=color, node=node, img=img)
    return img


def mark_svg(color: str, node: str = BLUE, size: int = 512) -> str:
    """Premium O+X Aperture Nexus as inline SVG (mirror of the logo pipeline)."""
    r = 190.0
    cx = cy = 256.0
    stroke = 26.0
    hi = _mix_hex(color, "#FFFFFF", 0.38)
    lo = _mix_hex(color, "#FFFFFF", 0.06)

    def vtx(radius: float, i: int) -> tuple[float, float]:
        a = math.radians(22.5 + i * 45)
        return (cx + radius * math.cos(a), cy + radius * math.sin(a))

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
            f'stroke="url(#markRingGrad)" stroke-width="{stroke}" stroke-linecap="round"/>'
        )
    ray_len = r * 0.8
    x1 = f'<rect x="{cx - stroke / 2}" y="{cy - ray_len}" width="{stroke}" height="{ray_len * 2}" rx="{stroke / 2}" fill="url(#markRayGrad)" transform="rotate(45 {cx} {cy})"/>'
    x2 = f'<rect x="{cx - stroke / 2}" y="{cy - ray_len}" width="{stroke}" height="{ray_len * 2}" rx="{stroke / 2}" fill="url(#markRayGrad)" transform="rotate(-45 {cx} {cy})"/>'
    inner = "".join(
        f'<line x1="{vtx(r * 0.66, i)[0]:.1f}" y1="{vtx(r * 0.66, i)[1]:.1f}" '
        f'x2="{vtx(r * 0.66, i + 1)[0]:.1f}" y2="{vtx(r * 0.66, i + 1)[1]:.1f}" '
        f'stroke="{lo}" stroke-width="2.5" stroke-linecap="round"/>'
        for i in range(8)
    )
    core = f'<rect x="{cx - 14}" y="{cy - 14}" width="28" height="28" fill="url(#markCoreGrad)" transform="rotate(45 {cx} {cy})"/>'
    nx = cx + r * 1.06 * math.cos(math.radians(45))
    ny = cy - r * 1.06 * math.sin(math.radians(45))
    node_halo = f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{stroke * 1.35:.1f}" fill="url(#markNodeHalo)" opacity="0.9"/>'
    node_circle = f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{stroke * 0.62:.1f}" fill="url(#markNodeGrad)"/>'
    glint = (
        f'<circle cx="{nx - stroke * 0.18:.1f}" cy="{ny - stroke * 0.18:.1f}" '
        f'r="{stroke * 0.2:.1f}" fill="{_mix_hex(node, "#FFFFFF", 0.6)}" opacity="0.9"/>'
    )
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
<defs>
  <radialGradient id="markHalo" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{color}" stop-opacity="0.16"/>
    <stop offset="1" stop-color="{color}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="markRingGrad" x1="0" y1="0" x2="512" y2="512" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{lo}"/>
    <stop offset="0.5" stop-color="{color}"/>
    <stop offset="1" stop-color="{hi}"/>
  </linearGradient>
  <linearGradient id="markRayGrad" x1="0" y1="0" x2="512" y2="512" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{lo}"/>
    <stop offset="1" stop-color="{hi}"/>
  </linearGradient>
  <radialGradient id="markCoreGrad" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{hi}"/>
    <stop offset="1" stop-color="{color}"/>
  </radialGradient>
  <radialGradient id="markNodeHalo" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{node}" stop-opacity="0.5"/>
    <stop offset="1" stop-color="{node}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="markNodeGrad" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{_mix_hex(node, "#FFFFFF", 0.55)}"/>
    <stop offset="1" stop-color="{node}"/>
  </linearGradient>
</defs>
<circle cx="{cx}" cy="{cy}" r="{r * 1.35:.0f}" fill="url(#markHalo)"/>
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


def social_preview_svg() -> str:
    """Premium social preview SVG, coherent with the render_og() PNG.

    Same composition: Aperture Nexus mark + OWNEX wordmark + eyebrow + pills
    on a Tesla-dark gradient with soft glows. Rendered by GitHub when the
    PNG is unavailable (e.g. some chat clients use the SVG directly).
    """
    grid_lines = []
    for x in range(0, 1201, 80):
        grid_lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="630" stroke="rgba(28,32,40,0.45)" stroke-width="1"/>')
    for y in range(0, 631, 80):
        grid_lines.append(f'<line x1="0" y1="{y}" x2="1200" y2="{y}" stroke="rgba(28,32,40,0.45)" stroke-width="1"/>')

    mark = mark_svg("#F6F8FB", "#1E40FF", size=512)
    return f"""<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#05060A"/>
    <stop offset="1" stop-color="#0C0F1A"/>
  </linearGradient>
  <radialGradient id="glowBlue" cx="0.22" cy="0.18" r="0.65">
    <stop offset="0" stop-color="rgba(30,64,255,0.32)"/>
    <stop offset="1" stop-color="rgba(30,64,255,0)"/>
  </radialGradient>
  <radialGradient id="glowCyan" cx="0.78" cy="0.88" r="0.6">
    <stop offset="0" stop-color="rgba(0,213,255,0.14)"/>
    <stop offset="1" stop-color="rgba(0,213,255,0)"/>
  </radialGradient>
  <linearGradient id="titleText" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#F6F8FB"/>
    <stop offset="1" stop-color="#8FD8FF"/>
  </linearGradient>
</defs>
<rect width="1200" height="630" fill="url(#bg)"/>
<rect width="1200" height="630" fill="url(#glowBlue)"/>
<rect width="1200" height="630" fill="url(#glowCyan)"/>
<g opacity="0.5">{"".join(grid_lines)}</g>
<rect x="72" y="62" width="1056" height="1" fill="#1C2028" opacity="0.7"/>
<g transform="translate(190, 155) scale(0.62)">{mark}</g>
<circle cx="560" cy="318" r="3.5" fill="#00E39A"/>
<text x="576" y="324" font-family="'JetBrains Mono','DejaVu Sans Mono',monospace" font-size="16" font-weight="500" letter-spacing="6" fill="#8A93A3">AUTONOMOUS WORK OPERATING SYSTEM</text>
<text x="558" y="402" font-family="'Space Grotesk','Inter',sans-serif" font-size="104" font-weight="700" letter-spacing="-4" fill="url(#titleText)">OWNEX</text>
<text x="560" y="448" font-family="'JetBrains Mono','DejaVu Sans Mono',monospace" font-size="15" letter-spacing="3" fill="#8A93A3">DISCOVER · ANALYZE · VALIDATE · EARN</text>
<rect x="560" y="470" width="520" height="1" fill="#1C2028"/>
<g font-family="'JetBrains Mono','DejaVu Sans Mono',monospace" font-size="14" letter-spacing="2">
  <circle cx="560" cy="508" r="2.5" fill="#00E39A"/>
  <text x="572" y="513" fill="#00E39A">100% LOCAL · NO CLOUD</text>
  <circle cx="852" cy="508" r="2.5" fill="#00D5FF"/>
  <text x="864" y="513" fill="#00D5FF">7 WORK CYCLES · 28 JOBS</text>
</g>
</svg>"""


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for folder, files in ASSETS.items():
        outdir = OUT / folder
        os.makedirs(outdir, exist_ok=True)
        for fname, render in files.items():
            img = render()
            if img.mode == "RGBA":
                img.save(outdir / fname, "PNG", optimize=True)
            else:
                img.convert("RGB").save(outdir / fname, "PNG", optimize=True)
            kb = os.path.getsize(outdir / fname) / 1024
            print(f"  ✓ {folder}/{fname}  {img.size[0]}×{img.size[1]}  {kb:.0f}KB")
            total += 1

    gh = ROOT / ".github"
    gh.mkdir(exist_ok=True)
    shutil.copyfile(OUT / "social" / "og-image.png", gh / "social-preview.png")
    (gh / "social-preview.svg").write_text(social_preview_svg())
    print("  ✓ .github/social-preview.png (synced to premium OG render)")
    print("  ✓ .github/social-preview.svg (premium, generated)")
    print(f"\nGenerated {total} assets in {OUT}")


if __name__ == "__main__":
    main()
