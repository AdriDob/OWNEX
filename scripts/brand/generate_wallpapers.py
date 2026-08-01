"""Generate ALPHA desktop wallpaper + OMEGA mobile splash."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import DESKTOP, MOBILE, C, mark_svg, render

W, H = 2560, 1440


def alpha_wallpaper() -> None:
    mark = mark_svg("alpha", size=512)
    texts = [
        (W / 2, 830, "OWNEX", "sg", 700, 88, "#F6F8FB", 14, "center"),
        (W / 2, 890, "ALPHA — DESKTOP OPERATING SYSTEM", "jbm", 400, 22, C["cyber_cyan"], 6, "center"),
    ]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">
  <defs>
    <radialGradient id="wallGlow" cx="50%" cy="42%" r="46%">
      <stop offset="0%" stop-color="#00D5FF" stop-opacity="0.14"/>
      <stop offset="60%" stop-color="#1E40FF" stop-opacity="0.04"/>
      <stop offset="100%" stop-color="#05060A" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="wallBg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#05060A"/>
      <stop offset="100%" stop-color="#080C16"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#wallBg)"/>
  <rect width="{W}" height="{H}" fill="url(#wallGlow)"/>
  {"".join(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#0A0F1C" stroke-width="1"/>' for x in range(0, W + 1, 160))}
  {"".join(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#0A0F1C" stroke-width="1"/>' for y in range(0, H + 1, 160))}
  <g transform="translate({W / 2}, 420) scale(1.55)"><g transform="translate(-256,-256) scale(0.66)">{mark}</g></g>
  <line x1="{W / 2 - 260}" y1="1010" x2="{W / 2 + 260}" y2="1010" stroke="#141B2C" stroke-width="1"/>
</svg>"""
    out = DESKTOP / "alpha-wallpaper.png"
    render(svg, out, width=W, text_fn=lambda d, s: _draw(d, texts, s), text_scale=1.0)
    (DESKTOP / "alpha-wallpaper.svg").write_text(svg)
    print("desktop:", out)


def omega_splash() -> None:
    w2, h2 = 1080, 2400
    mark = mark_svg("omega", size=512)
    texts = [
        (w2 / 2, 640, "OWNEX", "sg", 700, 120, "#F6F8FB", 14, "center"),
        (w2 / 2, 720, "OMEGA", "jbm", 500, 40, C["emerald"], 8, "center"),
        (w2 / 2, 790, "MOBILE COMPANION", "inter", 400, 28, C["muted"], 6, "center"),
        (w2 / 2, 1750, "SYSTEM LINKED", "jbm", 400, 26, C["emerald"], 5, "center"),
        (w2 / 2, 1810, "12 AGENTS · 3 APPROVALS · MEMORY SYNCED", "jbm", 400, 20, "#3D4A63", 3, "center"),
    ]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w2} {h2}">
  <defs>
    <radialGradient id="splashGlow" cx="50%" cy="30%" r="50%">
      <stop offset="0%" stop-color="#00E39A" stop-opacity="0.12"/>
      <stop offset="60%" stop-color="#00D5FF" stop-opacity="0.04"/>
      <stop offset="100%" stop-color="#05060A" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="splashBg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#05060A"/>
      <stop offset="100%" stop-color="#080C16"/>
    </linearGradient>
  </defs>
  <rect width="{w2}" height="{h2}" fill="url(#splashBg)"/>
  <rect width="{w2}" height="{h2}" fill="url(#splashGlow)"/>
  {"".join(f'<line x1="{x}" y1="0" x2="{x}" y2="{h2}" stroke="#0A0F1C" stroke-width="1"/>' for x in range(0, w2 + 1, 135))}
  {"".join(f'<line x1="0" y1="{y}" x2="{w2}" y2="{y}" stroke="#0A0F1C" stroke-width="1"/>' for y in range(0, h2 + 1, 135))}
  <g transform="translate({w2 / 2}, 300) scale(1.35)"><g transform="translate(-256,-256) scale(0.8)">{mark}</g></g>
  <rect x="{w2 / 2 - 300}" y="1640" width="600" height="300" rx="24" fill="#0B0E15" stroke="#1D2430" stroke-width="1.5"/>
  <rect x="{w2 / 2 - 240}" y="1710" width="480" height="14" rx="7" fill="#16213A"/>
  <rect x="{w2 / 2 - 240}" y="1710" width="360" height="14" rx="7" fill="#00E39A"/>
</svg>"""
    out = MOBILE / "omega-splash.png"
    render(svg, out, width=w2, text_fn=lambda d, s: _draw(d, texts, s), text_scale=1.0)
    (MOBILE / "omega-splash.svg").write_text(svg)
    print("mobile:", out)


def _draw(d, texts, s):
    from textlib import text_pil

    text_pil(d, texts, s)


def main() -> None:
    DESKTOP.mkdir(parents=True, exist_ok=True)
    MOBILE.mkdir(parents=True, exist_ok=True)
    alpha_wallpaper()
    omega_splash()


if __name__ == "__main__":
    main()
