"""Shared helpers for concept art: single text definition → SVG + PIL."""

from __future__ import annotations

from pathlib import Path

from pipeline import draw_text, draw_text_left

# text tuple: (x, y, text, family, weight, size, fill, tracking, align)
# align: "center" | "left"


def text_svg(texts: list, scale: float = 1.0) -> str:
    fam = {"sg": "Space Grotesk, sans-serif", "inter": "Inter, sans-serif", "jbm": "JetBrains Mono, monospace"}
    out = []
    for x, y, t, f, w, size, fill, tracking, align in texts:
        x, y, size = x * scale, y * scale, size * scale
        anchor = "middle" if align == "center" else "start"
        out.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'font-family="{fam[f]}" font-weight="{w}" font-size="{size:.1f}" '
            f'fill="{fill}" letter-spacing="{tracking}">{t}</text>'
        )
    return "".join(out)


def text_pil(d, texts: list, s: float = 1.0) -> None:
    from PIL import ImageFont

    for x, y, t, f, w, size, fill, tracking, align in texts:
        fn = {"sg": "SpaceGrotesk", "inter": "Inter", "jbm": "JetBrainsMono"}[f]
        fnt = ImageFont.truetype(
            f"{Path(__file__).resolve().parent.parent.parent / 'assets' / 'branding' / 'fonts' / f'{fn}-{w}.ttf'}",
            int(round(size * s)),
        )
        if align == "center":
            draw_text(d, (x * s, y * s), t, fn, w, size * s, fill, tracking=tracking)
        elif align == "right":
            width = 0
            for ch in t:
                width += d.textlength(ch, font=fnt) + int(round(tracking * size * s / 1000))
            draw_text_left(d, (x * s - width, y * s - size * s * 0.72), t, fn, w, size * s, fill, tracking=tracking)
        else:
            draw_text_left(d, (x * s, y * s - size * s * 0.72), t, fn, w, size * s, fill, tracking=tracking)


def card_svg(x, y, w, h, fill="#0B0E15", stroke="#1D2430", rx=16, glow=False) -> str:
    extra = '<filter id="cardGlow"><feGaussianBlur stdDeviation="24" result="b"/></filter>' if glow else ""
    return f'{extra}<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'


def header_svg(title: str, num: str, sub: str = "", W: int = 2400, H: int = 1350) -> str:
    return f"""
  <rect x="0" y="0" width="{W}" height="120" fill="#07090F"/>
  <line x1="0" y1="120" x2="{W}" y2="120" stroke="#1D2430" stroke-width="1"/>
  <circle cx="52" cy="60" r="6" fill="#00E39A"/>
  <text x="78" y="70" font-family="JetBrains Mono, monospace" font-weight="500" font-size="24"
        fill="#F6F8FB" letter-spacing="4">{title}</text>
  <text x="{W - 320}" y="70" font-family="JetBrains Mono, monospace" font-size="20"
        fill="#8A94A6" letter-spacing="3">OWNEX CONCEPT {num} / {sub}</text>
  <line x1="{W - 340}" y1="42" x2="{W - 340}" y2="78" stroke="#1D2430" stroke-width="2"/>
"""


def header_texts(title: str, num: str, sub: str = "") -> list:
    return [
        (78, 70, title, "jbm", 500, 24, "#F6F8FB", 4, "left"),
        (2400 - 320, 70, f"OWNEX CONCEPT {num} / {sub}", "jbm", 400, 20, "#8A94A6", 3, "left"),
    ]


def footer_svg(W: int = 2400, H: int = 1350, note: str = "SYSTEM NOMINAL — ALL MODULES OPERATIONAL") -> str:
    return f"""
  <line x1="0" y1="{H - 72}" x2="{W}" y2="{H - 72}" stroke="#1D2430" stroke-width="1"/>
  <circle cx="52" cy="{H - 36}" r="5" fill="#00D5FF"/>
  <text x="72" y="{H - 29}" font-family="JetBrains Mono, monospace" font-size="20"
        fill="#3D4A63" letter-spacing="3">{note}</text>
  <text x="{W - 52}" y="{H - 29}" text-anchor="end" font-family="JetBrains Mono, monospace"
        font-size="20" fill="#3D4A63" letter-spacing="3">OWNEX © 2026</text>
"""


def footer_texts(note: str = "SYSTEM NOMINAL — ALL MODULES OPERATIONAL") -> list:
    return [
        (72, 1350 - 29, note, "jbm", 400, 20, "#3D4A63", 3, "left"),
        (2400 - 52, 1350 - 29, "OWNEX © 2026", "jbm", 400, 20, "#3D4A63", 3, "right"),
    ]
