#!/usr/bin/env python3
"""
OWNEX TESLA Visual Generator
Deterministic SVG production for the GitHub visual package.
Palette: tokens.css (pure black, neutral grays, white primary, Tesla red #E82127).
No glows. No color gradients. Function over decoration.
Faithful to the real frontend: status bar, cycle sidebar, Next Best Action,
Opportunity Radar, Cashflow Radar, Agent Fleet, Knowledge Feed.
"""

from pathlib import Path

import cairosvg

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
    "accent": "#e82127",  # Tesla red — the ONLY saturated accent
    "warning": "#d97706",
    "success": "#16a34a",
    "gold": "#b45309",
    "hackerone": "#16a34a",
    "bugcrowd": "#b45309",
    "intigriti": "#9CA3AF",
    "yeswehack": "#dc2626",
    # cycle colors (monochrome hierarchy, red = odyssey)
    "c_security": "#f5f5f5",
    "c_forge": "#9ca3af",
    "c_pulse": "#16a34a",
    "c_vault": "#d97706",
    "c_atlas": "#d4d4d8",
    "c_odyssey": "#e82127",
}

FONT_SANS = "'Inter','DM Sans',system-ui,sans-serif"
FONT_MONO = "'JetBrains Mono','Fira Code',ui-monospace,monospace"


def txt(x, y, s, size, fill, weight=400, family=FONT_SANS, anchor="start", ls="0"):
    s = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
            f'letter-spacing="{ls}">{s}</text>')


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
    return (dot(x + 5, y - 4, 3, color)
            + txt(x + 14, y, label, 10, C["muted_fg"]))


def bar(x, y, w, h, pct, color=C["primary"]):
    """Progress bar: track + fill (white or status token)."""
    return (rect(x, y, w, h, C["surface_hover"], rx=2)
            + rect(x, y, int(w * pct), h, color, rx=2))


def card(x, y, w, h):
    return rect(x, y, w, h, C["surface"], rx=10, stroke=C["border"], sw=1)


# ════════════════════════════════════════════════════════════════
# SOCIAL PREVIEW — 1280x640 (GitHub repo card)
# ════════════════════════════════════════════════════════════════
def social_preview():
    w, h = 1280, 640
    g = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
    g.append(rect(0, 0, w, h, C["bg"]))
    # faint grid — monochrome, no glow
    for x in range(0, w + 1, 64):
        g.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke="{C["border"]}" stroke-width="1"/>')
    for y in range(0, h + 1, 64):
        g.append(f'<line x1="0" y1="{x}" x2="{w}" y2="{y}" stroke="{C["border"]}" stroke-width="1"/>')
    # mark (O+X)
    g.append('<g transform="translate(80,110)">')
    g.append(rect(0, 0, 26, 140, C["fg"]))
    g.append(rect(114, 0, 26, 140, C["fg"]))
    g.append(rect(0, 57, 140, 26, C["fg"]))
    g.append(f'<circle cx="70" cy="70" r="62" fill="none" stroke="{C["fg"]}" stroke-width="8"/>')
    g.append(dot(70, 70, 13, C["accent"]))
    g.append("</g>")
    # wordmark
    g.append(txt(80, 340, "OWNEX", 84, C["fg"], 700, ls="-0.02em"))
    g.append(txt(80, 392, "The personalized autonomous operating system", 22, C["muted_fg"]))
    # right panel — mini Mission Control (real UI)
    px, py, pw, ph = 560, 70, 620, 500
    g.append(rect(px, py, pw, ph, C["surface"], rx=14, stroke=C["border_light"], sw=1))
    g.append(rect(px, py, pw, 44, C["surface_hover"], rx=14))
    g.append(rect(px, py + 22, pw, 22, C["surface_hover"]))
    g.append(dot(px + 24, py + 22, 6, C["accent"]))
    g.append(txt(px + 40, py + 27, "MISSION CONTROL", 12, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(px + pw - 24, py + 27, "ALPHA", 11, C["muted"], 600, FONT_MONO, "end"))
    # stat row
    stats = [("SYSTEM HEALTH", "94%", C["success"]), ("ACTIVE AGENTS", "05", C["fg"]),
             ("REVENUE MTD", "$12,480", C["fg"]), ("OPPORTUNITIES", "47", C["fg"])]
    sw_ = 133
    for i, (lab, val, col) in enumerate(stats):
        x0 = px + 24 + i * (sw_ + 10)
        g.append(card(x0, py + 58, sw_, 74))
        g.append(txt(x0 + 14, py + 82, lab, 9, C["muted_fg"], 600, FONT_MONO))
        g.append(txt(x0 + 14, py + 112, val, 20, col, 700, FONT_MONO))
    # next best action
    g.append(card(px + 24, py + 148, pw - 48, 92))
    g.append(txt(px + 40, py + 172, "NEXT BEST ACTION", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(px + 40, py + 200, "Draft & submit report — Intigriti XSS chain", 16, C["fg"], 500))
    g.append(txt(px + 40, py + 222, "acceptance 0.82  ·  est. $2,400  ·  effort 6h", 11, C["muted_fg"], FONT_MONO))
    # cashflow radar mini
    g.append(card(px + 24, py + 256, pw - 48, 64))
    g.append(txt(px + 40, py + 280, "CASHFLOW RADAR", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(dot(px + 40, py + 300, 4, C["success"]))
    g.append(txt(px + 52, py + 304, "TODAY  $640", 12, C["fg"], 600, FONT_MONO))
    g.append(dot(px + 170, py + 300, 4, C["warning"]))
    g.append(txt(px + 182, py + 304, "WEEK  $3,180", 12, C["fg"], 600, FONT_MONO))
    g.append(dot(px + 310, py + 300, 4, C["muted_fg"]))
    g.append(txt(px + 322, py + 304, "GROWTH  $8,940", 12, C["fg"], 600, FONT_MONO))
    # sidebar strip
    cycles = [("SECURITY", C["c_security"]), ("FORGE", C["c_forge"]), ("PULSE", C["c_pulse"]),
              ("VAULT", C["c_vault"]), ("ATLAS", C["c_atlas"]), ("ODYSSEY", C["c_odyssey"])]
    for i, (name, col) in enumerate(cycles):
        y0 = py + 336 + i * 26
        g.append(rect(px + 24, y0, 3, 14, col))
        g.append(txt(px + 36, y0 + 12, name, 10, C["muted_fg"], 600, FONT_MONO))
    g.append(rect(px, py + ph - 30, pw, 30, C["surface_hover"], rx=0))
    g.append(txt(px + 24, py + ph - 12, "scheduler 32 jobs · event bus live · 0 findings unvalidated", 10, C["muted"], FONT_MONO))
    g.append("</svg>")
    return "".join(g)


# ════════════════════════════════════════════════════════════════
# HERO BANNER — 2400x1260 (README hero)
# ════════════════════════════════════════════════════════════════
def hero_banner():
    w, h = 2400, 1260
    g = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
    g.append(rect(0, 0, w, h, C["bg"]))
    for x in range(0, w + 1, 60):
        g.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke="{C["border"]}" stroke-width="1"/>')
    for y in range(0, h + 1, 60):
        g.append(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{C["border"]}" stroke-width="1"/>')
    # lockup top-left
    g.append('<g transform="translate(96,96)">')
    g.append(rect(0, 0, 24, 128, C["fg"]))
    g.append(rect(104, 0, 24, 128, C["fg"]))
    g.append(rect(0, 52, 128, 24, C["fg"]))
    g.append(f'<circle cx="64" cy="64" r="56" fill="none" stroke="{C["fg"]}" stroke-width="7"/>')
    g.append(dot(64, 64, 12, C["accent"]))
    g.append("</g>")
    g.append(txt(96, 300, "OWNEX", 140, C["fg"], 700, ls="-0.02em"))
    g.append(txt(96, 360, "The personalized autonomous operating system", 34, C["muted_fg"]))
    g.append(rect(96, 400, 240, 2, C["border_light"]))
    g.append(txt(96, 450, "mission control · opportunity intelligence · cashflow radar · work cycles", 20, C["muted"], FONT_MONO))
    # main window
    px, py, pw, ph = 480, 96, 1800, 1068
    g.append(rect(px, py, pw, ph, C["surface"], rx=16, stroke=C["border_light"], sw=1))
    g.append(rect(px, py, pw, 56, C["surface_hover"], rx=16))
    g.append(rect(px, py + 28, pw, 28, C["surface_hover"]))
    g.append(dot(px + 28, py + 28, 7, C["accent"]))
    g.append(txt(px + 48, py + 34, "OWNEX — MISSION CONTROL", 14, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(px + pw - 28, py + 34, "ALPHA · v7.0.0", 13, C["muted"], 600, FONT_MONO, "end"))
    # sidebar
    sb_w = 280
    g.append(rect(px, py + 56, sb_w, ph - 56, C["bg"], stroke=C["border"], sw=1))
    items = [("MISSION CONTROL", C["fg"], True), ("OPPORTUNITY RADAR", C["muted_fg"], False),
             ("CASHFLOW RADAR", C["muted_fg"], False), ("WORK CYCLES", C["muted_fg"], False),
             ("AGENT FLEET", C["muted_fg"], False), ("KNOWLEDGE FEED", C["muted_fg"], False),
             ("REPORTS", C["muted_fg"], False), ("SETTINGS", C["muted_fg"], False)]
    for i, (name, col, active) in enumerate(items):
        y0 = py + 84 + i * 52
        if active:
            g.append(rect(px + 8, y0 - 20, sb_w - 16, 36, C["surface_hover"], rx=6))
            g.append(rect(px + 8, y0 - 20, 3, 36, C["accent"]))
        g.append(txt(px + 28, y0, name, 13, col, 500, FONT_MONO))
    g.append(rect(px, py + ph - 96, sb_w, 40, C["surface_hover"]))
    g.append(txt(px + 28, py + ph - 72, "scheduler: 32 jobs", 11, C["muted"], FONT_MONO))
    g.append(txt(px + 28, py + ph - 44, "event bus: live", 11, C["success"], FONT_MONO))
    # content
    cx0 = px + sb_w + 28
    cw = pw - sb_w - 56
    # stat row
    stats = [("SYSTEM HEALTH", "94%", C["success"]), ("ACTIVE AGENTS", "05", C["fg"]),
             ("REVENUE MTD", "$12,480", C["fg"]), ("OPPORTUNITIES", "47", C["fg"]),
             ("FINDINGS OPEN", "03", C["warning"])]
    sw_ = (cw - 4 * 16) // 5
    for i, (lab, val, col) in enumerate(stats):
        x0 = cx0 + i * (sw_ + 16)
        g.append(card(x0, py + 76, sw_, 108))
        g.append(txt(x0 + 18, py + 106, lab, 10, C["muted_fg"], 600, FONT_MONO))
        g.append(txt(x0 + 18, py + 150, val, 30, col, 700, FONT_MONO))
    # next best action + radar side by side
    g.append(card(cx0, py + 208, int(cw * 0.58), 220))
    g.append(txt(cx0 + 24, py + 240, "NEXT BEST ACTION", 10, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(cx0 + 24, py + 284, "Draft & submit report — Intigriti XSS chain", 24, C["fg"], 500))
    g.append(txt(cx0 + 24, py + 316, "acceptance 0.82 · est. $2,400 · effort 6h · evidence ready", 14, C["muted_fg"], FONT_MONO))
    g.append(rect(cx0 + 24, py + 340, int((cw * 0.58) - 48), 6, C["surface_hover"], rx=3))
    g.append(rect(cx0 + 24, py + 340, int((cw * 0.58) - 48) * 0.82, 6, C["primary"], rx=3))
    g.append(txt(cx0 + 24, py + 392, "acceptance probability", 10, C["muted"], FONT_MONO))
    g.append(txt(cx0 + int(cw * 0.58) - 24, py + 392, "0.82 / 1.00", 10, C["muted_fg"], FONT_MONO, "end"))
    # cashflow radar
    rf_x = cx0 + int(cw * 0.58) + 16
    rf_w = cw - int(cw * 0.58) - 16
    g.append(card(rf_x, py + 208, rf_w, 220))
    g.append(txt(rf_x + 24, py + 240, "CASHFLOW RADAR", 10, C["muted_fg"], 600, FONT_MONO))
    g.append(dot(rf_x + 28, py + 276, 5, C["success"]))
    g.append(txt(rf_x + 42, py + 281, "TODAY", 12, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(rf_x + rf_w - 24, py + 281, "$640", 14, C["fg"], 700, FONT_MONO, "end"))
    g.append(dot(rf_x + 28, py + 310, 5, C["warning"]))
    g.append(txt(rf_x + 42, py + 315, "WEEK", 12, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(rf_x + rf_w - 24, py + 315, "$3,180", 14, C["fg"], 700, FONT_MONO, "end"))
    g.append(dot(rf_x + 28, py + 344, 5, C["muted_fg"]))
    g.append(txt(rf_x + 42, py + 349, "GROWTH", 12, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(rf_x + rf_w - 24, py + 349, "$8,940", 14, C["fg"], 700, FONT_MONO, "end"))
    g.append(txt(rf_x + 24, py + 390, "top pick: payout in 2d · $1,200", 10, C["muted"], FONT_MONO))
    # bottom row: opportunity radar list + agent fleet + knowledge feed
    g.append(card(cx0, py + 452, int(cw * 0.38), 340))
    g.append(txt(cx0 + 24, py + 484, "OPPORTUNITY RADAR", 10, C["muted_fg"], 600, FONT_MONO))
    rows = [("HackerOne — auth bypass chain", "$2,400", "0.82", C["hackerone"]),
            ("Bugcrowd — IDOR escalation", "$1,800", "0.74", C["bugcrowd"]),
            ("Intigriti — XSS persistence", "$1,200", "0.68", C["intigriti"]),
            ("YesWeHack — SSRF probe", "$900", "0.61", C["yeswehack"])]
    for i, (name, amt, acc, col) in enumerate(rows):
        y0 = py + 516 + i * 62
        g.append(dot(cx0 + 24, y0, 4, col))
        g.append(txt(cx0 + 38, y0, name, 12, C["fg"], 500))
        g.append(txt(cx0 + 38, y0 + 20, f"acceptance {acc}", 10, C["muted_fg"], FONT_MONO))
        g.append(txt(cx0 + int(cw * 0.38) - 24, y0, amt, 12, C["fg"], 600, FONT_MONO, "end"))
    # agent fleet
    af_x = cx0 + int(cw * 0.38) + 16
    af_w = int(cw * 0.30)
    g.append(card(af_x, py + 452, af_w, 340))
    g.append(txt(af_x + 24, py + 484, "AGENT FLEET", 10, C["muted_fg"], 600, FONT_MONO))
    agents = [("forge", "discovery", "running", C["success"]), ("pulse", "validation", "running", C["success"]),
              ("vault", "payouts", "idle", C["muted_fg"]), ("atlas", "knowledge", "running", C["success"]),
              ("odyssey", "deep-dive", "queued", C["warning"])]
    for i, (a, role, st, col) in enumerate(agents):
        y0 = py + 516 + i * 52
        g.append(dot(af_x + 24, y0 - 4, 4, col))
        g.append(txt(af_x + 38, y0, a, 13, C["fg"], 600, FONT_MONO))
        g.append(txt(af_x + 38, y0 + 18, role, 10, C["muted_fg"]))
        g.append(txt(af_x + af_w - 24, y0, st, 10, C["muted_fg"], FONT_MONO, "end"))
    # knowledge feed
    kf_x = af_x + af_w + 16
    kf_w = cw - int(cw * 0.38) - af_w - 32
    g.append(card(kf_x, py + 452, kf_w, 340))
    g.append(txt(kf_x + 24, py + 484, "KNOWLEDGE FEED", 10, C["muted_fg"], 600, FONT_MONO))
    feeds = [("lesson saved", "intigriti XSS: persistence beats payload", "2m"),
             ("report accepted", "HackerOne #8812 · $2,400", "1h"),
             ("signal updated", "auth bypass signal 0.61 → 0.74", "3h"),
             ("target synced", "bugcrowd public program catalog", "5h")]
    for i, (tag, msg, t) in enumerate(feeds):
        y0 = py + 516 + i * 62
        g.append(txt(kf_x + 24, y0, tag, 9, C["accent"], 600, FONT_MONO))
        g.append(txt(kf_x + 24, y0 + 20, msg, 12, C["fg"], 500))
        g.append(txt(kf_x + kf_w - 24, y0, t, 10, C["muted"], FONT_MONO, "end"))
    # status bar
    g.append(rect(px, py + ph - 32, pw, 32, C["bg"], stroke=C["border"], sw=1))
    g.append(dot(px + 24, py + ph - 16, 4, C["success"]))
    g.append(txt(px + 36, py + ph - 12, "event bus live · scheduler ok · recovery idle", 11, C["muted_fg"], FONT_MONO))
    g.append(txt(px + pw - 24, py + ph - 12, "throughput 1.2k/h · uptime 99.98%", 11, C["muted_fg"], FONT_MONO, "end"))
    g.append("</svg>")
    return "".join(g)


# ════════════════════════════════════════════════════════════════
# DESKTOP SHOWCASE — 1200x800 (README product screens)
# ════════════════════════════════════════════════════════════════
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
    # sidebar
    sb_w = 200
    g.append(rect(px, py + 44, sb_w, ph - 44, C["bg"], stroke=C["border"], sw=1))
    for i, name in enumerate(["MISSION CONTROL", "RADAR", "CYCLES", "FLEET", "FEED", "REPORTS"]):
        y0 = py + 68 + i * 40
        act = i == 0
        if act:
            g.append(rect(px + 8, y0 - 16, sb_w - 16, 30, C["surface_hover"], rx=5))
            g.append(rect(px + 8, y0 - 16, 3, 30, C["accent"]))
        g.append(txt(px + 22, y0, name, 11, C["fg"] if act else C["muted_fg"], 500, FONT_MONO))
    # content
    cx0 = px + sb_w + 20
    cw = pw - sb_w - 40
    stats = [("HEALTH", "94%", C["success"]), ("AGENTS", "05", C["fg"]), ("REVENUE", "$12,480", C["fg"])]
    sw_ = (cw - 32) // 3
    for i, (lab, val, col) in enumerate(stats):
        x0 = cx0 + i * (sw_ + 16)
        g.append(card(x0, py + 60, sw_, 84))
        g.append(txt(x0 + 14, py + 84, lab, 9, C["muted_fg"], 600, FONT_MONO))
        g.append(txt(x0 + 14, py + 116, val, 22, col, 700, FONT_MONO))
    g.append(card(cx0, py + 160, cw, 150))
    g.append(txt(cx0 + 18, py + 186, "NEXT BEST ACTION", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(cx0 + 18, py + 216, "Draft & submit — Intigriti XSS chain", 18, C["fg"], 500))
    g.append(txt(cx0 + 18, py + 240, "acceptance 0.82 · est. $2,400 · effort 6h", 11, C["muted_fg"], FONT_MONO))
    g.append(rect(cx0 + 18, py + 260, cw - 36, 5, C["surface_hover"], rx=2))
    g.append(rect(cx0 + 18, py + 260, int((cw - 36) * 0.82), 5, C["primary"], rx=2))
    g.append(card(cx0, py + 326, int(cw * 0.48), 210))
    g.append(txt(cx0 + 18, py + 352, "OPPORTUNITY RADAR", 9, C["muted_fg"], 600, FONT_MONO))
    rows = [("HackerOne — auth bypass", "$2,400", C["hackerone"]),
            ("Bugcrowd — IDOR", "$1,800", C["bugcrowd"]),
            ("Intigriti — XSS", "$1,200", C["intigriti"]),
            ("YesWeHack — SSRF", "$900", C["yeswehack"])]
    for i, (name, amt, col) in enumerate(rows):
        y0 = py + 380 + i * 36
        g.append(dot(cx0 + 18, y0 - 4, 3, col))
        g.append(txt(cx0 + 30, y0, name, 11, C["fg"], 500))
        g.append(txt(cx0 + int(cw * 0.48) - 18, y0, amt, 11, C["fg"], 600, FONT_MONO, "end"))
    g.append(card(cx0 + int(cw * 0.48) + 16, py + 326, cw - int(cw * 0.48) - 16, 210))
    g.append(txt(cx0 + int(cw * 0.48) + 34, py + 352, "CASHFLOW RADAR", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(dot(cx0 + int(cw * 0.48) + 38, py + 386, 4, C["success"]))
    g.append(txt(cx0 + int(cw * 0.48) + 52, py + 391, "TODAY", 11, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(cx0 + cw - 34, py + 391, "$640", 13, C["fg"], 700, FONT_MONO, "end"))
    g.append(dot(cx0 + int(cw * 0.48) + 38, py + 416, 4, C["warning"]))
    g.append(txt(cx0 + int(cw * 0.48) + 52, py + 421, "WEEK", 11, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(cx0 + cw - 34, py + 421, "$3,180", 13, C["fg"], 700, FONT_MONO, "end"))
    g.append(dot(cx0 + int(cw * 0.48) + 38, py + 446, 4, C["muted_fg"]))
    g.append(txt(cx0 + int(cw * 0.48) + 52, py + 451, "GROWTH", 11, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(cx0 + cw - 34, py + 451, "$8,940", 13, C["fg"], 700, FONT_MONO, "end"))
    g.append(rect(px, py + ph - 24, pw, 24, C["bg"], stroke=C["border"], sw=1))
    g.append(dot(px + 16, py + ph - 12, 3, C["success"]))
    g.append(txt(px + 26, py + ph - 9, "event bus live · scheduler ok", 10, C["muted_fg"], FONT_MONO))
    g.append("</svg>")
    return "".join(g)


# ════════════════════════════════════════════════════════════════
# MOBILE SHOWCASE — 480x960 (README product screens / Companion)
# ════════════════════════════════════════════════════════════════
def mobile_showcase():
    w, h = 480, 960
    g = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
    g.append(rect(0, 0, w, h, C["bg"]))
    # phone frame
    fx, fy, fw, fh = 40, 30, 400, 900
    g.append(rect(fx, fy, fw, fh, "#0d0d0d", rx=48, stroke=C["border_light"], sw=2))
    g.append(rect(fx + 12, fy + 12, fw - 24, fh - 24, C["bg"], rx=38))
    # notch
    g.append(rect(fx + 140, fy + 20, 120, 24, "#0d0d0d", rx=12))
    # status bar
    g.append(txt(fx + 34, fy + 66, "9:41", 14, C["fg"], 600, FONT_MONO))
    g.append(txt(fx + fw - 34, fy + 66, "● 100%", 11, C["muted_fg"], 600, FONT_MONO, "end"))
    # header
    g.append(txt(fx + 34, fy + 120, "OWNEX", 20, C["fg"], 700, ls="0.08em"))
    g.append(txt(fx + 34, fy + 146, "COMPANION", 10, C["muted_fg"], 600, FONT_MONO, ls="0.2em"))
    # health card
    g.append(card(fx + 28, fy + 168, fw - 56, 96))
    g.append(txt(fx + 46, fy + 196, "SYSTEM HEALTH", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(fx + 46, fy + 230, "94%", 30, C["success"], 700, FONT_MONO))
    g.append(rect(fx + 46, fy + 244, 120, 5, C["surface_hover"], rx=2))
    g.append(rect(fx + 46, fy + 244, 112, 5, C["success"], rx=2))
    # opportunity alert
    g.append(card(fx + 28, fy + 284, fw - 56, 120))
    g.append(txt(fx + 46, fy + 310, "OPPORTUNITY ALERT", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(fx + 46, fy + 338, "Intigriti XSS chain", 15, C["fg"], 600))
    g.append(txt(fx + 46, fy + 362, "acceptance 0.82 · $2,400", 11, C["muted_fg"], FONT_MONO))
    g.append(rect(fx + 46, fy + 380, 150, 30, C["primary"], rx=15))
    g.append(txt(fx + 121, fy + 400, "REVIEW", 10, "#000000", 700, FONT_MONO))
    # approvals
    g.append(card(fx + 28, fy + 424, fw - 56, 130))
    g.append(txt(fx + 46, fy + 450, "APPROVALS (2)", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(dot(fx + 46, fy + 478, 4, C["warning"]))
    g.append(txt(fx + 60, fy + 483, "Submit report · Forge → HackerOne", 12, C["fg"], 500))
    g.append(dot(fx + 46, fy + 510, 4, C["muted_fg"]))
    g.append(txt(fx + 60, fy + 515, "Payout split · Vault", 12, C["muted_fg"], 500))
    g.append(rect(fx + 46, fy + 530, 110, 26, C["surface_hover"], rx=13, stroke=C["border_light"], sw=1))
    g.append(txt(fx + 101, fy + 547, "APPROVE", 9, C["fg"], 600, FONT_MONO))
    # metrics
    g.append(card(fx + 28, fy + 574, (fw - 56 - 16) // 2, 110))
    g.append(txt(fx + 44, fy + 600, "REVENUE MTD", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(fx + 44, fy + 640, "$12,480", 19, C["fg"], 700, FONT_MONO))
    g.append(card(fx + 28 + (fw - 56 - 16) // 2 + 16, fy + 574, (fw - 56 - 16) // 2, 110))
    g.append(txt(fx + 44 + (fw - 56 - 16) // 2 + 16, fy + 600, "RADAR TODAY", 9, C["muted_fg"], 600, FONT_MONO))
    g.append(txt(fx + 44 + (fw - 56 - 16) // 2 + 16, fy + 640, "$640", 19, C["fg"], 700, FONT_MONO))
    # bottom nav
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
        path.write_text(fn())
        png = path.with_suffix(".png")
        cairosvg.svg2png(url=str(path), write_to=str(png), output_width=w, output_height=h)
        print(f"✓ {path.relative_to(ROOT)} (+ {png.name})")


if __name__ == "__main__":
    main()
