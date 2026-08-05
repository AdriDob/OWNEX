#!/usr/bin/env python3
"""
OWNEX TESLA Visual Generator
Deterministic SVG production for the GitHub visual package.
Palette: tokens.css (pure black, neutral grays, white primary, Tesla red #E82127).
No glows. No color gradients. Function over decoration.
Faithful to the real frontend: status bar, cycle sidebar, Next Best Action,
Opportunity Radar, Cashflow Radar, Agent Fleet, Knowledge Feed.
"""

import sys
from pathlib import Path

import cairosvg

# import logo system
sys.path.insert(0, str(Path(__file__).parent))
from logo_system import lockup_svg

ROOT = Path(__file__).resolve().parents[2]

# ── TESLA tokens (mirror of frontend/src/design/tokens.css) ──
C = {
    "bg": "#000000",
    "surface": "#0a0a0a",
    "surface_hover": "#141414",
    "border": "#1f1f1f",
    "border_light": "#2e2e2e",
    "muted": "#4a4a4a",
    "muted_fg": "#8a8a8a",
    "fg": "#f5f5f5",
    "primary": "#ffffff",
    "accent": "#00D5FF",  # OWNEX blue — the ONLY saturated accent
    "warning": "#d97706",
    "success": "#16a34a",
    "gold": "#b45309",
    "hackerone": "#16a34a",
    "bugcrowd": "#b45309",
    "intigriti": "#9CA3AF",
    "yeswehack": "#dc2626",
    # cycle colors (monochrome hierarchy, red = odyssey)
    "c_security": "#00D5FF",
    "c_forge": "#1E40FF",
    "c_pulse": "#16a34a",
    "c_vault": "#d97706",
    "c_atlas": "#d4d4d8",
    "c_odyssey": "#e82127",
}

FONT_SANS = "'Inter','DM Sans',system-ui,sans-serif"
FONT_MONO = "'JetBrains Mono','Fira Code',monospace"


def txt(x, y, s, size, fill, weight=400, family=FONT_SANS, anchor="start", ls="0"):
    s = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
        f'letter-spacing="{ls}" dominant-baseline="alphabetic">{s}</text>'
    )


def rect(x, y, w, h, fill, rx=0, stroke=None, sw=0, opacity=1):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"'
    if stroke:
        s += f' stroke="{stroke}" stroke-width="{sw}"'
    if opacity != 1:
        s += f' opacity="{opacity}"'
    return s + "/>"


def dot(x, y, r, fill):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>'


def status_pill(x, y, label, color):
    """Small status pill: dot + label."""
    return dot(x + 5, y - 4, 3, color) + txt(x + 14, y, label, 10, C["muted_fg"])


def bar(x, y, w, h, pct, color=C["primary"]):
    """Progress bar: track + fill (white or status token)."""
    return rect(x, y, w, h, C["surface_hover"], rx=2) + rect(x, y, int(w * pct), h, color, rx=2)


def card(x, y, w, h):
    return rect(x, y, w, h, C["surface"], rx=10, stroke=C["border"], sw=1)


# ═══════════════════════════════════════════════════════════════
# SOCIAL PREVIEW — 1280x640 (GitHub repo card)
# ═══════════════════════════════════════════════════════════════
def social_preview():
    w, h = 1280, 640
    g = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
    g.append(rect(0, 0, w, h, C["bg"]))
    for x in range(0, w + 1, 64):
        g.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke="{C["border"]}" stroke-width="1"/>')
    for y in range(0, h + 1, 64):
        g.append(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{C["border"]}" stroke-width="1"/>')
    # logo lockup en el centro superior, tamaño más pequeño 180px (ya que no es necesario el panel del Mission Control)
    mark_size = 180
    lockup_scale = mark_size / 512  # lockup_svg: viewBox 1200x240, width 1200px, height 240px, ratio ~5:1
    lockup_width = 400
    lockup_height = 80
    lockup_x = (w - lockup_width) // 2
    lockup_y = 80
    g.append(f'<g transform="translate({lockup_x}, {lockup_y}) scale({lockup_scale})">')
    g.append(lockup_svg(width=800, height=160).replace("<svg", "<g").replace("</svg>", "</g>"))
    g.append("</g>")
    # wordmark debajo del lockup
    g.append(txt(lockup_x, lockup_y + lockup_height + 24, "OWNEX", 48, C["fg"], 700, ls="-0.02em"))
    g.append(
        txt(lockup_x, lockup_y + lockup_height + 84, "The personalized autonomous operating system", 20, C["muted_fg"])
    )
    # bottom subtle line
    g.append(rect(lockup_x, lockup_y + lockup_height + 120, lockup_width, 2, C["accent"], rx=1))
    g.append("</svg>")
    return "".join(g)


# ═══════════════════════════════════════════════════════════════
# HERO BANNER — 2400x1260 (README hero)
# ═══════════════════════════════════════════════════════════════
def hero_banner():
    w, h = 2400, 1260
    g = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
    g.append(rect(0, 0, w, h, C["bg"]))
    for x in range(0, w + 1, 60):
        g.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke="{C["border"]}" stroke-width="1"/>')
    for y in range(0, h + 1, 60):
        g.append(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{C["border"]}" stroke-width="1"/>')
    # lockup top-left (con wordmark) — mismo que en social_preview pero un poco más grande
    lockup_x = 96
    lockup_y = 96
    g.append(f'<g transform="translate({lockup_x}, {lockup_y}) scale(1.0)">')
    g.append(lockup_svg(width=800, height=160).replace("<svg", "<g").replace("</svg>", "</g>"))
    g.append("</g>")
    # subtítulo debajo del lockup
    g.append(txt(lockup_x, lockup_y + 160 + 40, "The personalized autonomous operating system", 24, C["muted_fg"]))
    g.append("</svg>")
    return "".join(g)


# ═══════════════════════════════════════════════════════════════
# DESKTOP SHOWCASE — 1200x800 (README product screens)
# ═══════════════════════════════════════════════════════════════
def desktop_showcase():
    w, h = 1200, 800
    g = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
    g.append(rect(0, 0, w, h, C["bg"]))
    px, py, pw, ph = 60, 40, 1080, 720
    g.append(rect(px, py, pw, ph, C["surface"], rx=12, stroke=C["border_light"], sw=1))
    g.append(rect(px, py, pw, 44, C["surface_hover"], rx=12))
    g.append(rect(px, py + 22, pw, 22, C["surface_hover"]))
    g.append(dot(px + 22, py + 22, 5, C["accent"]))
    g.append(txt(px + 36, py + 27, "OWNEX — MISSION CONTROL", 12, C["muted_fg"], 600, FONT_MONO))
    sb_w = 200
    g.append(rect(px, py + 44, sb_w, ph - 44, C["bg"], stroke=C["border"], sw=1))
    for i, name in enumerate(["MISSION CONTROL", "RADAR", "CYCLES", "FLEET", "FEED", "REPORTS"]):
        y0 = py + 68 + i * 40
        act = i == 0
        if act:
            g.append(rect(px + 8, y0 - 16, sb_w - 16, 36, C["surface_hover"], rx=5))
            g.append(rect(px + 8, y0 - 16, 3, 36, C["accent"]))
        g.append(txt(px + 22, y0, name, 11, C["fg"] if act else C["muted_fg"], 500, FONT_MONO))
    cx0 = px + sb_w + 20
    cw = pw - sb_w - 40
    stats = [("HEALTH", "94%", C["success"]), ("AGENTS", "05", C["fg"]), ("REVENUE", "$12,480", C["fg"])]
    sw_ = (cw - 32) // 3
    for i, (lab, val, col) in enumerate(stats):
        x0 = cx0 + i * (sw_ + 16)
        g.append(card(x0, py + 60, sw_, 84))
        g.append(txt(x0 + 14, py + 84, lab, 9, C["muted_fg"], 600, FONT_MONO))
        g.append(txt(x0 + 14, py + 116, val, 30, col, 700, FONT_MONO))
    g.append(card(cx0, py + 160, cw, 150))
    g.append(txt(cx0 + 18, py + 186, "NEXT BEST ACTION", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(cx0 + 18, py + 216, "Draft & submit report — Intigriti XSS chain", 18, C["fg"], 500))
    g.append(txt(cx0 + 18, py + 240, "acceptance 0.82 · est. $2,400 · effort 6h", 11, C["muted_fg"], FONT_MONO))
    g.append(rect(cx0 + 18, py + 260, cw - 36, 5, C["surface_hover"], rx=2))
    g.append(rect(cx0 + 18, py + 260, int((cw - 36) * 0.82), 5, C["primary"], rx=2))
    g.append(txt(cx0 + 18, py + 292, "acceptance probability", 10, C["muted"], FONT_MONO))
    g.append(txt(cx0 + int(cw * 0.58) - 24, py + 292, "0.82 / 1.00", 10, C["muted_fg"], FONT_MONO, "end"))
    g.append(card(cx0, py + 326, int(cw * 0.58), 210))
    g.append(txt(cx0 + 24, py + 352, "OPPORTUNITY RADAR", 10, C["muted_fg"], 600, FONT_MONO))
    rows = [
        ("HackerOne — auth bypass chain", "$2,400", C["hackerone"]),
        ("Bugcrowd — IDOR escalation", "$1,800", C["bugcrowd"]),
        ("Intigriti — XSS persistence", "$1,200", C["intigriti"]),
        ("YesWeHack — SSRF probe", "$900", C["yeswehack"]),
    ]
    for i, (name, amt, col) in enumerate(rows):
        y0 = py + 380 + i * 62
        g.append(dot(cx0 + 24, y0, 4, col))
        g.append(txt(cx0 + 38, y0, name, 12, C["fg"], 500))
        g.append(txt(cx0 + int(cw * 0.58) - 24, y0, amt, 12, C["fg"], 600, FONT_MONO, "end"))
    g.append("</svg>")
    return "".join(g)


# ═══════════════════════════════════════════════════════════════
# MOBILE SHOWCASE — 480x960 (README product screens / Companion)
# ═══════════════════════════════════════════════════════════════
def mobile_showcase():
    w, h = 480, 960
    g = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
    g.append(rect(0, 0, w, h, C["bg"]))
    fx, fy, fw, fh = 40, 30, 400, 900
    g.append(rect(fx, fy, fw, fh, "#0d0d0d", rx=48, stroke=C["border_light"], sw=2))
    g.append(rect(fx + 12, fy + 12, fw - 24, fh - 24, C["bg"], rx=38))
    g.append(rect(fx + 140, fy + 20, 120, 24, "#0d0d0d", rx=12))
    g.append(txt(fx + 34, fy + 66, "9:41", 14, C["fg"], 600, FONT_MONO))
    g.append(txt(fx + fw - 34, fy + 66, "● 100%", 11, C["muted_fg"], 600, FONT_MONO, "end"))
    g.append(txt(fx + 34, fy + 120, "OWNEX", 20, C["fg"], 700, ls="0.08em"))
    g.append(txt(fx + 34, fy + 146, "COMPANION", 10, C["muted_fg"], 600, FONT_MONO, ls="0.2em"))
    g.append(card(fx + 28, fy + 168, fw - 56, 96))
    g.append(txt(fx + 46, fy + 196, "SYSTEM HEALTH", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(fx + 46, fy + 230, "94%", 30, C["success"], 700, FONT_MONO))
    g.append(rect(fx + 46, fy + 244, 120, 5, C["surface_hover"], rx=2))
    g.append(rect(fx + 46, fy + 244, 112, 5, C["success"], rx=2))
    g.append(card(fx + 28, fy + 284, fw - 56, 120))
    g.append(txt(fx + 46, fy + 310, "OPPORTUNITY ALERT", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(fx + 46, fy + 338, "Intigriti XSS chain", 15, C["fg"], 600))
    g.append(txt(fx + 46, fy + 362, "acceptance 0.82 · $2,400", 11, C["muted_fg"], FONT_MONO))
    g.append(rect(fx + 46, fy + 380, 150, 30, C["primary"], rx=15))
    g.append(txt(fx + 121, fy + 400, "REVIEW", 10, "#000000", 700, FONT_MONO))
    g.append(card(fx + 28, fy + 424, fw - 56, 130))
    g.append(txt(fx + 46, fy + 450, "APPROVALS (2)", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(dot(fx + 46, fy + 478, 4, C["warning"]))
    g.append(txt(fx + 60, fy + 483, "Submit report · Forge → HackerOne", 12, C["fg"], 500))
    g.append(dot(fx + 46, fy + 510, 4, C["muted_fg"]))
    g.append(txt(fx + 60, fy + 515, "Payout split · Vault", 12, C["muted_fg"], 500))
    g.append(rect(fx + 46, fy + 530, 110, 26, C["surface_hover"], rx=13, stroke=C["border_light"], sw=1))
    g.append(txt(fx + 101, fy + 547, "APPROVE", 9, C["fg"], 600, FONT_MONO))
    g.append(card(fx + 28, fy + 574, (fw - 56 - 16) // 2, 110))
    g.append(txt(fx + 44, fy + 600, "REVENUE MTD", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(fx + 44, fy + 640, "$12,480", 19, C["fg"], 700, FONT_MONO))
    g.append(card(fx + 28 + (fw - 56 - 16) // 2 + 16, fy + 574, (fw - 56 - 16) // 2, 110))
    g.append(txt(fx + 44 + (fw - 56 - 16) // 2 + 16, fy + 600, "RADAR TODAY", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(fx + 44 + (fw - 56 - 16) // 2 + 16, fy + 640, "$640", 19, C["fg"], 700, FONT_MONO))
    nav = ["HOME", "RADAR", "FLEET", "WALLET"]
    for i, n in enumerate(nav):
        x0 = fx + 28 + i * ((fw - 56) / 4)
        g.append(txt(x0 + ((fw - 56) / 8), fy + 880, n, 9, C["accent"] if i == 0 else C["muted_fg"], 600, FONT_MONO))
    g.append("</svg>")
    return "".join(g)


def main():
    out = ROOT / "assets" / "banners"
    out.mkdir(parents=True, exist_ok=True)

    jobs = [
        (out / "hero-banner.svg", hero_banner, 2400, 1260),
        (ROOT / ".github" / "social-preview.svg", social_preview, 1280, 640),
        (ROOT / "assets" / "concepts" / "desktop-showcase.svg", desktop_showcase, 1200, 800),
        (ROOT / "assets" / "concepts" / "mobile-showcase.svg", mobile_showcase, 480, 960),
    ]
    for path, fn, w, h in jobs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(fn())
        png = path.with_suffix(".png")
        cairosvg.svg2png(url=str(path), write_to=str(png), output_width=w, output_height=h)
        print(f"✓ {path.relative_to(ROOT)} (+ {png.name})")


if __name__ == "__main__":
    main()
