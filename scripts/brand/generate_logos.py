"""Generate the complete OWNEX logo system (SVG + PNG)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import LOGOS, C, draw_text, draw_text_left, mark_svg, render, svg_to_png

LOGO_DIR = LOGOS  # assets/logos

MARK_SCALE = 0.5  # mark scale in lockups


def lockup_svg(edition: str | None = None, mono: bool = False) -> str:
    """Horizontal lockup: mark + OWNEX wordmark + optional edition tag."""
    w, _h = 1024, 384
    variant = "alpha" if edition is None else edition.lower()
    mark_x = 200
    mark_scale = MARK_SCALE
    text_x = mark_x + 170 * mark_scale + 110
    if mono:
        mark = mark_svg(variant, mono=True, size=w)
        tag_fill = "#FFFFFF"
    else:
        mark = mark_svg(variant, mono=False, size=w)
        tag_fill = C["cyber_cyan"] if variant == "alpha" else C["emerald"]
    # SVG text (rendered by browsers); PNG text composited by PIL.
    edition_tag = ""
    if edition:
        tag = "ALPHA — DESKTOP OPERATING SYSTEM" if edition == "ALPHA" else "OMEGA — MOBILE COMPANION"
        edition_tag = (
            f'<text x="{text_x}" y="312" font-family="JetBrains Mono, monospace" font-size="22" '
            f'fill="{tag_fill}" letter-spacing="6">{tag}</text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  {mark}
  <text x="{text_x}" y="216" font-family="Space Grotesk, sans-serif" font-weight="700"
        font-size="120" fill="{"#FFFFFF" if mono else "#F6F8FB"}" letter-spacing="8">OWNEX</text>
  {edition_tag}
</svg>"""


def lockup_png(edition: str | None, mono: bool, out: Path, width: int = 2048) -> Path:
    svg = lockup_svg(edition, mono)
    tmp = out.with_suffix(".tmp.png")
    render(svg, tmp, width=width)
    from PIL import Image, ImageDraw

    img = Image.open(tmp).convert("RGBA")
    s = width / 1024
    d = ImageDraw.Draw(img)
    text_x = 200 + 170 * MARK_SCALE + 110
    tag = None
    if edition == "ALPHA":
        tag = "ALPHA — DESKTOP OPERATING SYSTEM"
    elif edition == "OMEGA":
        tag = "OMEGA — MOBILE COMPANION"
    tag_fill = C["cyber_cyan"] if edition in (None, "ALPHA") else C["emerald"]
    if mono:
        tag_fill = "#FFFFFF"
    draw_text(
        d, (text_x * s, 312 * s), "OWNEX", "SpaceGrotesk", 700, 120 * s, "#FFFFFF" if mono else "#F6F8FB", tracking=8
    )
    if tag:
        draw_text_left(d, (text_x * s, 300 * s), tag, "JetBrainsMono", 400, 21 * s, tag_fill, tracking=6)
    img.save(out)
    tmp.unlink()
    return out


def app_icon_png(out: Path, width: int = 1024) -> Path:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="iconBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{C["surface_1"]}"/>
      <stop offset="100%" stop-color="{C["space_black"]}"/>
    </linearGradient>
    <linearGradient id="ringG" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{C["cyber_cyan"]}"/>
      <stop offset="100%" stop-color="{C["deep_blue"]}"/>
    </linearGradient>
  </defs>
  <rect width="1024" height="1024" rx="230" fill="url(#iconBg)"/>
  <rect x="28" y="28" width="968" height="968" rx="206" fill="none"
        stroke="{C["stroke"]}" stroke-width="6"/>
  {mark_svg("alpha", size=1024)}
</svg>"""
    return render(svg, out, width=width)


def main() -> None:
    logos = LOGO_DIR
    logos.mkdir(parents=True, exist_ok=True)

    # 1. Mark (transparent) — SVG + PNG 1024
    (logos / "ownex-mark.svg").write_text(mark_svg("alpha"))
    render(mark_svg("alpha"), logos / "ownex-mark.png", width=1024)

    # 2. Monochrome marks (white for dark UIs, black for light UIs)
    (logos / "ownex-monochrome.svg").write_text(mark_svg("alpha", mono="white"))
    render(mark_svg("alpha", mono="white"), logos / "ownex-monochrome.png", width=1024)
    (logos / "ownex-monochrome-black.svg").write_text(mark_svg("alpha", mono="black"))
    render(mark_svg("alpha", mono="black"), logos / "ownex-monochrome-black.png", width=1024)

    # 3. Lockups
    for edition in (None, "ALPHA", "OMEGA"):
        name = "ownex-lockup" if edition is None else f"ownex-{edition.lower()}"
        (logos / f"{name}.svg").write_text(lockup_svg(edition))
        lockup_png(edition, False, logos / f"{name}.png")
        if edition is None:
            (logos / "ownex-lockup-mono.svg").write_text(lockup_svg(None, mono=True))
            lockup_png(None, True, logos / "ownex-lockup-mono.png")

    # 4. App icon
    app_icon_png(logos / "ownex-icon.png")
    app_icon_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="iconBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{C["surface_1"]}"/>
      <stop offset="100%" stop-color="{C["space_black"]}"/>
    </linearGradient>
  </defs>
  <rect width="1024" height="1024" rx="230" fill="url(#iconBg)"/>
  {mark_svg("alpha", size=1024)}
</svg>"""
    (logos / "ownex-icon.svg").write_text(app_icon_svg)

    # 5. Favicon (64px SVG, 64px PNG) + UI 32px — bold strokes for small sizes
    (logos / "ownex-favicon.svg").write_text(mark_svg("alpha", size=64, bold=True))
    svg_to_png(mark_svg("alpha", size=64, bold=True), logos / "ownex-favicon.png", 64)
    svg_to_png(mark_svg("alpha", size=512, bold=True), logos / "ownex-ui-32px.png", 32)

    print("Logo system generated →", logos)


if __name__ == "__main__":
    main()
