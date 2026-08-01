"""Generate README hero banner + OG/social cover."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import C, BANNERS, render, draw_text, draw_text_left, mark_svg

W, H = 2400, 1260


def background(svg: str = "") -> str:
    return f"""<defs>
    <radialGradient id="glow" cx="50%" cy="38%" r="55%">
      <stop offset="0%" stop-color="#00D5FF" stop-opacity="0.16"/>
      <stop offset="45%" stop-color="#00D5FF" stop-opacity="0.05"/>
      <stop offset="100%" stop-color="#05060A" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="sky" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#05060A"/>
      <stop offset="100%" stop-color="#080B14"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#sky)"/>
  <rect width="{W}" height="{H}" fill="url(#glow)"/>
  {grid()}
  {corner_marks()}
  {svg}"""


def grid() -> str:
    lines = []
    for x in range(0, W + 1, 120):
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#0C1220" stroke-width="1"/>')
    for y in range(0, H + 1, 120):
        lines.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#0C1220" stroke-width="1"/>')
    return "".join(lines)


def corner_marks() -> str:
    """Engineering crop marks at the corners (precision language)."""
    m = 60
    parts = []
    corners = [(m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)]
    for cx, cy, dx, dy in corners:
        ln = 46
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + dx * ln}" y2="{cy}" stroke="#1E2A3D" stroke-width="2"/>')
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy + dy * ln}" stroke="#1E2A3D" stroke-width="2"/>')
    return "".join(parts)


def hero_svg() -> str:
    mark = mark_svg("alpha", size=512)
    mark_scaled = (
        f'<g transform="translate(944, 270) scale(1.0)"><g transform="translate(-256, -256) scale(1.45)">{mark}</g></g>'
    )
    body = f"""
  <text x="1200" y="972" text-anchor="middle" font-family="Space Grotesk, sans-serif"
        font-weight="700" font-size="150" fill="#F6F8FB" letter-spacing="14">OWNEX</text>
  <text x="1200" y="1040" text-anchor="middle" font-family="Inter, sans-serif"
        font-size="34" fill="#8A94A6" letter-spacing="10">AUTONOMOUS PERSONAL OPERATING SYSTEM</text>
  <g>
    <rect x="950" y="1092" width="210" height="54" rx="27" fill="none" stroke="{C["cyber_cyan"]}" stroke-width="2"/>
    <text x="1055" y="1128" text-anchor="middle" font-family="JetBrains Mono, monospace"
          font-size="20" fill="{C["cyber_cyan"]}" letter-spacing="4">ALPHA</text>
    <rect x="1190" y="1092" width="210" height="54" rx="27" fill="none" stroke="{C["emerald"]}" stroke-width="2"/>
    <text x="1295" y="1128" text-anchor="middle" font-family="JetBrains Mono, monospace"
          font-size="20" fill="{C["emerald"]}" letter-spacing="4">OMEGA</text>
  </g>
  <line x1="260" y1="1176" x2="2140" y2="1176" stroke="#141B2C" stroke-width="1"/>
  <text x="1200" y="1222" text-anchor="middle" font-family="JetBrains Mono, monospace"
        font-size="22" fill="#3D4A63" letter-spacing="6">AGENTS · MEMORY · EVOLUTION · WORKFLOWS · TERMINAL</text>
  {mark_scaled}
"""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{background(body)}</svg>'


def hero_png(out: Path) -> Path:
    svg = hero_svg()
    tmp = out.with_suffix(".tmp.png")
    render(svg, tmp, width=W)
    from PIL import Image, ImageDraw

    img = Image.open(tmp).convert("RGBA")
    d = ImageDraw.Draw(img)
    draw_text(d, (1200, 928), "OWNEX", "SpaceGrotesk", 700, 150, "#F6F8FB", tracking=14)
    draw_text(d, (1200, 1008), "AUTONOMOUS PERSONAL OPERATING SYSTEM", "Inter", 500, 34, C["muted"], tracking=10)
    draw_text(d, (1055, 1125), "ALPHA", "JetBrainsMono", 500, 20, C["cyber_cyan"], tracking=4)
    draw_text(d, (1295, 1125), "OMEGA", "JetBrainsMono", 500, 20, C["emerald"], tracking=4)
    draw_text(
        d,
        (1200, 1222),
        "AGENTS · MEMORY · EVOLUTION · WORKFLOWS · TERMINAL",
        "JetBrainsMono",
        400,
        22,
        "#3D4A63",
        tracking=6,
    )
    img.save(out)
    tmp.unlink()
    return out


# ---------------------------------------------------------------------------
# OG / social cover (1200×630)
# ---------------------------------------------------------------------------

OGW, OGH = 1200, 630


def og_svg() -> str:
    mark = mark_svg("alpha", size=512)
    mark_scaled = f'<g transform="translate(250, 315) scale(0.78)"><g transform="translate(-256,-256)">{mark}</g></g>'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {OGW} {OGH}">
  <defs>
    <radialGradient id="ogGlow" cx="22%" cy="50%" r="42%">
      <stop offset="0%" stop-color="#00D5FF" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#05060A" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="{OGW}" height="{OGH}" fill="#05060A"/>
  <rect width="{OGW}" height="{OGH}" fill="url(#ogGlow)"/>
  {grid()}
  {mark_scaled}
  <text x="600" y="262" font-family="Space Grotesk, sans-serif" font-weight="700"
        font-size="86" fill="#F6F8FB" letter-spacing="8">OWNEX</text>
  <text x="600" y="330" font-family="Inter, sans-serif" font-size="24" fill="#8A94A6" letter-spacing="6">
    AUTONOMOUS PERSONAL OPERATING SYSTEM</text>
  <text x="600" y="398" font-family="JetBrains Mono, monospace" font-size="17" fill="#3D4A63" letter-spacing="4">
    ALPHA DESKTOP · OMEGA MOBILE · MERLIN · AGENTS · EVOLUTION</text>
  <line x1="600" y1="452" x2="1080" y2="452" stroke="#141B2C" stroke-width="1"/>
</svg>"""


def og_png(out: Path) -> Path:
    svg = og_svg()
    tmp = out.with_suffix(".tmp.png")
    render(svg, tmp, width=OGW)
    from PIL import Image, ImageDraw

    img = Image.open(tmp).convert("RGBA")
    d = ImageDraw.Draw(img)
    draw_text(d, (600, 240), "OWNEX", "SpaceGrotesk", 700, 86, "#F6F8FB", tracking=8)
    draw_text(d, (600, 306), "AUTONOMOUS PERSONAL OPERATING SYSTEM", "Inter", 500, 24, C["muted"], tracking=6)
    draw_text(
        d,
        (600, 376),
        "ALPHA DESKTOP · OMEGA MOBILE · MERLIN · AGENTS · EVOLUTION",
        "JetBrainsMono",
        400,
        17,
        "#3D4A63",
        tracking=4,
    )
    img.save(out)
    tmp.unlink()
    return out


def main() -> None:
    BANNERS.mkdir(parents=True, exist_ok=True)
    (BANNERS / "hero-banner.svg").write_text(hero_svg())
    hero_png(BANNERS / "hero-banner.png")
    (BANNERS / "og-cover.svg").write_text(og_svg())
    og_png(BANNERS / "og-cover.png")
    print("Banners generated →", BANNERS)


if __name__ == "__main__":
    main()
