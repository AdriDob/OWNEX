#!/usr/bin/env python3
"""OWNEX — high-quality PNG rendering (Tesla dark).

Deterministic, reproducible, zero SVG. Renders the O+X Aperture Nexus mark,
hero banner, footer and social preview as richly-layered PNGs using PIL +
numpy + vendored SIL-OFL fonts. No GPU required.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path("/home/adrie/projects/Rastro")
F = ROOT / "assets/branding/fonts"
OUT_L = ROOT / "docs/assets/branding/logo"
OUT_B = ROOT / "docs/assets/branding/banners"
OUT_S = ROOT / "docs/assets/branding/social"
for d in (OUT_L, OUT_B, OUT_S):
    d.mkdir(parents=True, exist_ok=True)

SURF = (5, 6, 10)
SURF2 = (8, 9, 14)
WHITE = (246, 248, 250)
BLUE = (30, 64, 255)
RED = (232, 33, 39)
MUTED = (140, 143, 152)
TEXT_DIM = (140, 148, 160)


def tf(name, sz):
    return ImageFont.truetype(str(F / name), sz)


def _vgrad(w, h, c1, c2):
    """Vertical gradient as RGB ndarray."""
    a = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    arr = np.empty((h, w, 3), dtype=np.float32)
    for i in range(3):
        arr[:, :, i] = c1[i] * (1 - a) + c2[i] * a
    return Image.fromarray(arr.astype("uint8"), "RGB")


def _ring(draw, cx, cy, r, st, color, gap_deg=22.0, gap_start=50.0, n=8):
    for i in range(n):
        a0 = i * 360 / n
        a1 = a0 + 360 / n
        ctr = (a0 + a1) / 2
        d = ((ctr - gap_start + 180) % 360) - 180
        if gap_deg and abs(d) < gap_deg / 2 + 4:
            continue
        x0 = cx + r * math.cos(math.radians(a0))
        y0 = cy + r * math.sin(math.radians(a0))
        x1 = cx + r * math.cos(math.radians(a1))
        y1 = cy + r * math.sin(math.radians(a1))
        draw.line([(x0, y0), (x1, y1)], fill=color, width=int(st), joint="curve")


def _rays(img, cx, cy, r, st, color, angle):
    bar = Image.new("RGBA", img.size, 0)
    bd = ImageDraw.Draw(bar)
    bd.rectangle([cx - st / 2, cy - r, cx + st / 2, cy + r], fill=color)
    bar = bar.rotate(angle, center=(cx, cy), resample=Image.Resampling.BICUBIC)
    img.paste(bar, (0, 0), bar)


def render_mark(size=1024, color=WHITE, node=BLUE, muted=TEXT_DIM, glow=True, bg=(0, 0, 0, 0)):
    img = Image.new("RGBA", (size, size), bg)
    cx = cy = size / 2
    r = size * 0.37
    st = size * 0.05

    if glow:
        g = Image.new("RGBA", img.size, 0)
        gd = ImageDraw.Draw(g)
        rg = r + st * 0.6
        for i in range(24, 0, -1):
            a = i / 24
            rr = rg * a
            val = int(55 * a * a)
            gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(*node, val))
        g = g.filter(ImageFilter.GaussianBlur(radius=size * 0.06))
        img.paste(g, (0, 0), g)

    d = ImageDraw.Draw(img)
    _ring(d, cx, cy, r, st, color, gap_deg=24)
    arm = r * 0.82
    _rays(img, cx, cy, arm, st * 0.45, muted, 45)
    _rays(img, cx, cy, arm, st * 0.45, muted, -45)
    nx = cx + r * 1.02
    ny = cy - r * 1.02
    d.ellipse([nx - st * 0.58, ny - st * 0.58, nx + st * 0.58, ny + st * 0.58], fill=node)
    cs = st * 0.54
    core = Image.new("RGBA", (int(cs * 1.6), int(cs * 1.6)), 0)
    cd = ImageDraw.Draw(core)
    cd.rectangle([cs * 0.2, cs * 0.2, cs * 0.2 + cs, cs * 0.2 + cs], fill=color)
    core = core.rotate(45, resample=Image.Resampling.BICUBIC)
    img.paste(core, (int(cx - cs * 0.8), int(cy - cs * 0.8)), core)
    return img


def _tc(draw, img, text, y, font, fill):
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    draw.text((img.width / 2 - tw / 2, y), text, font=font, fill=fill)
    return bb[3] - bb[1]


def render_hero(w=2400, h=900):
    img = _vgrad(w, h, SURF, SURF2)
    # noise texture (fast via numpy)
    rng = np.random.default_rng(42)
    noise = rng.integers(0, 19, size=(h, w), dtype=np.uint8)
    noise_img = Image.fromarray(noise, "L").filter(ImageFilter.GaussianBlur(3))
    img = Image.composite(img, img.point(lambda v: v), noise_img.point(lambda v: 255 - v * 9))

    m = render_mark(size=720, color=WHITE, node=BLUE, muted=(160, 163, 172), glow=True)
    mi = m.convert("RGBA")
    img.paste(mi, (int(w * 0.10), int(h * 0.10)), mi)

    d = ImageDraw.Draw(img)
    ty = int(h * 0.12)
    _tc(d, img, "OWNEX", ty, tf("SpaceGrotesk-700.ttf", 110), WHITE)
    ty += 130
    _tc(d, img, "Autonomous Work Operating System", ty, tf("Inter-400.ttf", 46), TEXT_DIM)
    ty += 70
    _tc(d, img, "Discover · Evaluate · Prepare · Deliver", ty, tf("Inter-500.ttf", 38), BLUE)

    f_ft = tf("Inter-400.ttf", 26)
    d.text((w / 2, h - 64), "Security • Forge • Vault • Atlas • Pulse", font=f_ft, fill=(100, 104, 114), anchor="mm")

    # vignette
    v = Image.new("RGB", (w, h), 0)
    vd = ImageDraw.Draw(v)
    for i in range(80, 0, -1):
        a = i / 80
        rad = (w * 0.55) * (1 - a * 0.18)
        vd.ellipse(
            [w / 2 - rad, h / 2 - rad, w / 2 + rad, h / 2 + rad], fill=tuple(int(c * a * 0.22) for c in (0, 0, 0))
        )
    img = Image.blend(img, v, 0.12)
    return img


def render_footer(w=2400, h=420):
    img = _vgrad(w, h, SURF, SURF2)
    d = ImageDraw.Draw(img)
    _tc(d, img, "OWNEX", h * 0.38 - 40, tf("SpaceGrotesk-700.ttf", 76), WHITE)
    _tc(d, img, "Personal Autonomous Work Operating System", h * 0.38 + 30, tf("Inter-400.ttf", 34), TEXT_DIM)
    d.line([(w * 0.2, h - 70), (w * 0.8, h - 70)], fill=MUTED, width=1)
    d.text(
        (w / 2, h - 30), "v7.0.0 · The Aperture Nexus", font=tf("Inter-400.ttf", 26), fill=(100, 104, 114), anchor="mm"
    )
    return img


def render_social(w=1200, h=630):
    img = _vgrad(w, h, SURF, SURF2)
    m = render_mark(size=512, color=WHITE, node=BLUE, muted=(150, 154, 165), glow=True)
    mi = m.convert("RGBA")
    img.paste(mi, (int(w / 2 - 256), int(h * 0.18)), mi)
    d = ImageDraw.Draw(img)
    _tc(d, img, "Autonomous Work Operating System", h * 0.56, tf("SpaceGrotesk-700.ttf", 56), WHITE)
    _tc(d, img, "Security • Automation • Revenue", h * 0.66, tf("Inter-400.ttf", 28), TEXT_DIM)
    return img


def main():
    mark_img = render_mark(size=1024)
    mark_img.save(OUT_L / "ownex-mark-hero.png", optimize=True)
    print("logo/ownex-mark-hero.png 1024x1024")
    mark_img.resize((512, 512), Image.Resampling.LANCZOS).save(OUT_L / "ownex-mark-badge.png", optimize=True)
    print("logo/ownex-mark-badge.png 512x512")
    render_mark(size=512, color=SURF, node=BLUE, muted=(110, 113, 120), bg=(255, 255, 255, 255)).save(
        OUT_L / "ownex-mark-light.png", optimize=True
    )
    print("logo/ownex-mark-light.png (on white)")

    render_hero().save(OUT_B / "ownex-hero-banner.png", optimize=True, quality=92)
    print("banners/ownex-hero-banner.png")
    render_footer().save(OUT_B / "ownex-footer.png", optimize=True, quality=92)
    print("banners/ownex-footer.png")
    render_social().save(OUT_S / "ownex-social-preview.png", optimize=True, quality=92)
    print("social/ownex-social-preview.png")


if __name__ == "__main__":
    main()
