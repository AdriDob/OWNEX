#!/usr/bin/env python3
"""Generate all ORION/CATEYE SVG screenshots with cyber aesthetic."""

import os
import shutil

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots")

# ── Design tokens ────────────────────────────────────────────────────
BG = "#050508"
BG2 = "#0A0A0E"
BG3 = "#121218"
CARD = "rgba(12,12,18,0.92)"
CARD_BORDER = "rgba(109,40,217,0.15)"
PURPLE = "#A855F7"
PURPLE_MID = "#8B5CF6"
PURPLE_CORE = "#7C3AED"
PURPLE_DEEP = "#6D28D9"
GOLD = "#F5A623"
GREEN = "#00FF41"
RED = "#FF1744"
ORANGE = "#FF6600"
CYAN = "#00FFFF"
TEXT = "#E2E8F0"
TEXT2 = "#94A3B8"
TEXT3 = "#64748B"
W = 1280
H = 800


# ── SVG helpers ──────────────────────────────────────────────────────
def svg_open(w=W, h=H, extra=""):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
  <defs>
    <linearGradient id="purpleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{PURPLE}"/>
      <stop offset="100%" stop-color="{PURPLE_DEEP}"/>
    </linearGradient>
    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{GOLD}"/>
      <stop offset="100%" stop-color="#FFCC66"/>
    </linearGradient>
    <linearGradient id="greenGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{GREEN}"/>
      <stop offset="100%" stop-color="#00E676"/>
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glowStrong">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <clipPath id="round12"><rect width="{w}" height="{h}" rx="12"/></clipPath>
    {extra}
  </defs>
  <rect width="{w}" height="{h}" fill="{BG}"/>
  <!-- Grid pattern -->
  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="{PURPLE_DEEP}" stroke-width="0.3" opacity="0.15"/>
  </pattern>
  <rect width="{w}" height="{h}" fill="url(#grid)" opacity="0.4"/>
'''


SVG_CLOSE = "</svg>"


def rect(x, y, w, h, fill=None, rx=0, stroke=None, sw=1, op=1):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o = f' opacity="{op}"' if op < 1 else ""
    r = f' rx="{rx}"' if rx else ""
    f = f' fill="{fill}"' if fill else ' fill="none"'
    return f'  <rect x="{x}" y="{y}" width="{w}" height="{h}"{r}{f}{s}{o}/>'


def text(x, y, txt, fill=TEXT, size=14, font="Inter", weight="400", anchor="start", ls=0, op=1):
    o = f' opacity="{op}"' if op < 1 else ""
    ls_s = f' letter-spacing="{ls}"' if ls else ""
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    t = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'  <text x="{x}" y="{y}" font-family={chr(39)}{font}{chr(39)}, sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill}"{ls_s}{a}{o}>{t}</text>'


def circle(cx, cy, r, fill, op=1, filt="", stroke=None, sw=0):
    o = f' opacity="{op}"' if op < 1 else ""
    f = f' filter="url(#{filt})"' if filt else ""
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{s}{o}{f}/>'


def line(x1, y1, x2, y2, stroke=TEXT3, sw=1, op=1, dash=""):
    o = f' opacity="{op}"' if op < 1 else ""
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{o}{d}/>'


def ellipse(cx, cy, rx, ry, fill="none", stroke=PURPLE, sw=1.5, op=1, rot=0, transform=""):
    t = f' transform="rotate({rot} {cx} {cy})"' if rot else ""
    o = f' opacity="{op}"' if op < 1 else ""
    f = f' fill="{fill}"' if fill != "none" else ' fill="none"'
    return f'  <ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"{f} stroke="{stroke}" stroke-width="{sw}"{o}{t}/>'


def card(x, y, w, h, rx=12):
    return f"{rect(x, y, w, h, fill=CARD, rx=rx, stroke=PURPLE_DEEP, sw=0.5, op=0.9)}\n{rect(x, y, w, 1, fill=PURPLE, rx=0, op=0.15)}"


# ── Sidebar ──────────────────────────────────────────────────────────
def sidebar(active="Dashboard"):
    items = [
        ("Dashboard", True),
        ("Pipeline", False),
        ("Discoveries", False),
        ("Validations", False),
        ("Reports", False),
        ("Identity", False),
        ("Intelligence", False),
        ("System", False),
        ("Settings", False),
    ]
    s = rect(0, 0, 220, H, fill="#0D111C")
    s += line(220, 0, 220, H, stroke=PURPLE_DEEP, sw=1, op=0.3)
    s += text(30, 38, "CATEYE", fill=PURPLE, size=22, font="Orbitron", weight="900", ls=4)
    s += text(30, 58, "Bug Bounty Intelligence", fill=TEXT3, size=10, ls=1)
    for i, (label, is_active) in enumerate(items):
        iy = 90 + i * 42
        if is_active:
            s += rect(0, iy, 220, 36, fill=PURPLE_DEEP, op=0.2)
            s += rect(0, iy, 3, 36, fill=PURPLE)
        c = TEXT if is_active else TEXT2
        s += text(32, iy + 22, label, fill=c, size=13)
    s += text(30, H - 40, "ORION v4.7.0", fill=TEXT3, size=10)
    s += circle(30, H - 22, 4, GREEN)
    s += text(40, H - 18, "System Online", fill=GREEN, size=10)
    return s


# ── Topbar ───────────────────────────────────────────────────────────
def topbar(title):
    s = rect(220, 0, W - 220, 56, fill="#0D111C")
    s += line(220, 56, W, 56, stroke=PURPLE_DEEP, sw=1, op=0.3)
    s += text(250, 35, title, fill=TEXT, size=18, font="Orbitron", weight="700", ls=1)
    # Search
    s += rect(900, 14, 150, 28, fill=BG3, rx=6, stroke=PURPLE_DEEP, sw=0.5)
    s += text(916, 33, "Search...", fill=TEXT3, size=12)
    # Status dots
    s += circle(1070, 28, 5, PURPLE, filt="glow")
    s += circle(1090, 28, 5, GREEN, filt="glow")
    s += circle(1110, 28, 5, GOLD, filt="glow")
    return s


# ── Stat card ────────────────────────────────────────────────────────
def stat_card(x, y, w, h, label, value, color=PURPLE, sub="", trend=""):
    s = card(x, y, w, h)
    s += text(x + 16, y + 22, label, fill=TEXT2, size=11)
    s += text(x + 16, y + 52, str(value), fill=color, size=28, font="Orbitron", weight="700")
    if sub:
        s += text(x + 16, y + 72, sub, fill=TEXT3, size=10)
    if trend:
        tc = GREEN if trend.startswith("+") else RED
        s += text(x + w - 60, y + 22, trend, fill=tc, size=11)
    return s


# ── Bar chart ────────────────────────────────────────────────────────
def bar_chart(x, y, w, h, title, bars_data=None, labels=None):
    if bars_data is None:
        bars_data = [0.62, 0.35, 0.78, 0.50, 0.88, 0.42, 0.71, 0.55, 0.92, 0.38, 0.65, 0.80]
    if labels is None:
        labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"]
    s = card(x, y, w, h)
    if title:
        s += text(x + 16, y + 22, title, fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    cx, cy_chart = x + 50, y + 50
    cw, ch = w - 65, h - 75
    s += rect(cx, cy_chart, cw, ch, fill=BG3, rx=4)
    for i in range(1, 5):
        gy = cy_chart + ch * i // 5
        s += line(cx, gy, cx + cw, gy, stroke=PURPLE_DEEP, sw=0.5, op=0.3)
        s += text(cx - 35, gy + 4, str(100 - i * 25), fill=TEXT3, size=9)
    bw = cw // len(bars_data) - 4
    for i, val in enumerate(bars_data):
        bx = int(cx + i * (bw + 4) + 2)
        bh = int(val * ch)
        by = cy_chart + ch - bh
        bar_color = PURPLE if i % 2 == 0 else PURPLE_MID
        s += rect(bx, by, bw, bh, fill=bar_color, rx=3, op=0.85)
        if i < len(labels):
            s += text(bx, cy_chart + ch + 14, labels[i], fill=TEXT3, size=8)
    return s


# ── Table ────────────────────────────────────────────────────────────
def data_table(x, y, w, h, title, headers, rows, severity_col=None):
    s = card(x, y, w, h)
    if title:
        s += text(x + 16, y + 22, title, fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    ty = y + 44
    s += line(x + 16, ty, x + w - 16, ty, stroke=PURPLE_DEEP, sw=0.5, op=0.4)
    col_widths = [w // len(headers)] * len(headers)
    col_x = [x + 16]
    for cw_i in col_widths[:-1]:
        col_x.append(col_x[-1] + cw_i)
    for i, h_text in enumerate(headers):
        s += text(col_x[i], ty + 16, h_text, fill=TEXT3, size=10, font="Orbitron", weight="600", ls=1)
    sev_colors = {
        "Critical": RED,
        "High": ORANGE,
        "Medium": GOLD,
        "Low": GREEN,
        "Confirmed": GREEN,
        "Validated": PURPLE,
        "Pending": GOLD,
        "Rejected": RED,
        "Pending Review": GOLD,
    }
    for ri, row in enumerate(rows):
        ry = ty + 30 + ri * 30
        if ri % 2 == 0:
            s += rect(x + 12, ry - 4, w - 24, 28, fill="#0F1219", rx=4)
        for ci, val in enumerate(row):
            c = sev_colors.get(val, TEXT) if ci == (severity_col or 1) else TEXT
            s += text(col_x[ci], ry + 14, val, fill=c, size=11)
    return s


# ── Pipeline diagram ─────────────────────────────────────────────────
def pipeline_diagram(x, y, w, h, title, stages=None):
    if stages is None:
        stages = [
            ("DISCOVER", GREEN),
            ("RECON", PURPLE),
            ("HYPOTHESIS", PURPLE_MID),
            ("VALIDATE", GOLD),
            ("REPORT", ORANGE),
            ("SUBMIT", GREEN),
        ]
    s = card(x, y, w, h)
    if title:
        s += text(x + 16, y + 22, title, fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    n = len(stages)
    node_w = min(130, (w - 40 - (n - 1) * 16) // n)
    gap = (w - 40 - n * node_w) // (n - 1) if n > 1 else 0
    base_y = y + h // 2 - 18
    for i, (label, color) in enumerate(stages):
        nx = x + 20 + i * (node_w + gap)
        s += rect(nx, base_y, node_w, 36, fill=color, rx=8)
        tc = BG if color in (GOLD, GREEN, ORANGE) else TEXT
        s += text(
            nx + node_w // 2, base_y + 22, label, fill=tc, size=10, font="Orbitron", weight="600", anchor="middle", ls=1
        )
        if i < n - 1:
            ax = nx + node_w
            ay = base_y + 18
            s += line(ax + 2, ay, ax + gap - 4, ay, stroke=TEXT3, sw=2)
            s += f'  <polygon points="{ax + gap - 2},{ay} {ax + gap - 8},{ay - 5} {ax + gap - 8},{ay + 5}" fill="{TEXT3}"/>'
    s += text(
        x + 16,
        y + h - 14,
        f"Pipeline: {n}/{n} stages  |  355 tests passing  |  CoreScheduler active",
        fill=TEXT3,
        size=9,
    )
    return s


# ── Health grid ──────────────────────────────────────────────────────
def health_grid(x, y, w, h, title, items):
    s = card(x, y, w, h)
    if title:
        s += text(x + 16, y + 22, title, fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    per_row = 3
    iw = (w - 32) // per_row
    for i, (label, value, color) in enumerate(items):
        col = i % per_row
        row = i // per_row
        ix = x + 16 + col * iw
        iy = y + 44 + row * 56
        s += circle(ix + 8, iy + 12, 5, color, filt="glow")
        s += text(ix + 20, iy + 8, label, fill=TEXT2, size=11)
        s += text(ix + 20, iy + 26, value, fill=TEXT, size=16, font="Orbitron", weight="600")
    return s


# ════════════════════════════════════════════════════════════════════
#  SCREENSHOTS
# ════════════════════════════════════════════════════════════════════


def gen_dashboard():
    s = svg_open()
    s += sidebar("Dashboard")
    s += topbar("Executive Dashboard")
    s += stat_card(240, 72, 230, 100, "Active Targets", "24", PURPLE, "+3 today", "+14%")
    s += stat_card(485, 72, 230, 100, "Open Findings", "47", RED, "12 critical", "+8%")
    s += stat_card(730, 72, 230, 100, "Reports Today", "8", GREEN, "6 pending review", "+22%")
    s += stat_card(975, 72, 230, 100, "Confidence Score", "89.4%", GOLD, "trending up", "+2.1%")
    s += bar_chart(240, 186, 500, 280, "Findings by Day")
    s += data_table(
        755,
        186,
        485,
        280,
        "Recent Findings",
        ["Target", "Severity", "Status", "EV"],
        [
            ("api.example.com", "Critical", "Confirmed", "$2,400"),
            ("app.test.org", "High", "Validated", "$1,200"),
            ("dev.internal.net", "Medium", "Pending", "$600"),
            ("admin.dashboard.io", "Critical", "Validated", "$3,100"),
            ("cdn.assets.com", "Low", "Rejected", "$150"),
        ],
    )
    s += pipeline_diagram(240, 480, 1000, 150, "Pipeline Overview")
    s += health_grid(
        240,
        645,
        1000,
        135,
        "System Health",
        [
            ("API", "Online", GREEN),
            ("Agents", "4/4", GREEN),
            ("Pipeline", "Idle", GREEN),
            ("Database", "OK", GREEN),
            ("Memory", "42%", GOLD),
            ("CPU", "18%", GREEN),
        ],
    )
    s += SVG_CLOSE
    return s


def gen_revenue():
    s = svg_open()
    s += sidebar("Intelligence")
    s += topbar("Revenue Intelligence")
    # Pipeline E2E
    s += pipeline_diagram(240, 72, 1000, 100, "Revenue Pipeline: Finding → Evidence → Report → Platform → Payout")
    # Stats
    s += stat_card(240, 188, 230, 90, "Total Revenue", "$12,847", GOLD, "+$2,100 this month", "+19%")
    s += stat_card(485, 188, 230, 90, "Avg. Bounty", "$428", PURPLE, "per accepted report")
    s += stat_card(730, 188, 230, 90, "Acceptance Rate", "67.3%", GREEN, "top 5% of hunters")
    s += stat_card(975, 188, 230, 90, "USD/Hour", "$89.20", GOLD, "effective hourly rate")
    # Platform breakdown
    s += data_table(
        240,
        294,
        500,
        240,
        "Platform Breakdown",
        ["Platform", "Reports", "Accepted", "Revenue"],
        [
            ("HackerOne", "24", "18", "$7,200"),
            ("Bugcrowd", "15", "9", "$3,400"),
            ("Intigriti", "8", "5", "$1,800"),
            ("Immunefi", "3", "2", "$447"),
        ],
    )
    # EV scoring
    s += data_table(
        755,
        294,
        485,
        240,
        "Top EV Targets",
        ["Target", "EV Score", "Difficulty", "Priority"],
        [
            ("api.paypal.com", "9.8", "Hard", "P1"),
            ("app.stripe.com", "9.2", "Medium", "P1"),
            ("dev.notion.so", "8.7", "Easy", "P2"),
            ("cdn.shopify.com", "8.1", "Medium", "P2"),
        ],
    )
    # Economic memory
    s += card(240, 550, 1000, 220)
    s += text(256, 572, "Economic Memory", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    mem_items = [
        ("SQLi in auth endpoints", "HIGH", GOLD, "Avg. payout: $1,800 — 73% acceptance rate"),
        ("IDOR on user profiles", "MEDIUM", PURPLE, "Avg. payout: $600 — 45% acceptance rate"),
        ("XSS in admin panel", "HIGH", GOLD, "Avg. payout: $2,200 — 82% acceptance rate"),
        ("SSRF in webhook handler", "LOW", TEXT2, "Avg. payout: $350 — 28% acceptance rate"),
        ("Auth bypass via OAuth", "CRITICAL", RED, "Avg. payout: $4,500 — 91% acceptance rate"),
    ]
    for i, (vuln, risk, rc, desc) in enumerate(mem_items):
        iy = 600 + i * 32
        s += circle(270, iy, 4, rc)
        s += text(284, iy + 4, vuln, fill=TEXT, size=12)
        s += text(540, iy + 4, f"[{risk}]", fill=rc, size=10, font="JetBrains Mono")
        s += text(640, iy + 4, desc, fill=TEXT3, size=10)
    return s


def gen_offensive():
    s = svg_open()
    s += sidebar("Intelligence")
    s += topbar("Offensive Intelligence — CATEYE")
    # Reasoners
    reasoners = [
        ("IDOR", "12", GREEN, "3 confirmed"),
        ("SSRF", "8", PURPLE, "2 confirmed"),
        ("XSS", "15", GOLD, "5 confirmed"),
        ("SQLi", "6", RED, "2 confirmed"),
        ("Auth Bypass", "4", RED, "1 confirmed"),
    ]
    s += card(240, 72, 1000, 130)
    s += text(256, 94, "5 Reasoners Active", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    for i, (name, count, color, conf) in enumerate(reasoners):
        rx = 270 + i * 190
        s += rect(rx, 110, 170, 72, fill=BG3, rx=8, stroke=PURPLE_DEEP, sw=0.5)
        s += text(rx + 12, 132, name, fill=color, size=14, font="Orbitron", weight="700", ls=2)
        s += text(rx + 12, 152, f"{count} findings", fill=TEXT, size=11)
        s += text(rx + 12, 170, conf, fill=color, size=10)
    # Contradiction Engine
    s += card(240, 216, 480, 240)
    s += text(256, 238, "Contradiction Engine", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    contra_items = [
        ("7 vuln types supported", GREEN, "IDOR, SSRF, XSS, SQLi, Auth, CSRF, XXE"),
        ("Alternative explanations", PURPLE, "Auto-generated for each finding"),
        ("Missing verifications", GOLD, "Explicit gaps in evidence chain"),
        ("Uncertainty scoring", PURPLE_MID, "Penalty: -0.00 to -0.12 per finding"),
    ]
    for i, (label, color, desc) in enumerate(contra_items):
        iy = 268 + i * 42
        s += circle(272, iy + 4, 4, color)
        s += text(284, iy + 8, label, fill=TEXT, size=12)
        s += text(284, iy + 22, desc, fill=TEXT3, size=10)
    # HTTP Probes
    s += card(735, 216, 505, 240)
    s += text(751, 238, "HTTP Probes Pipeline", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    probes = [
        ("GET /api/v1/users", "200", GREEN, "45ms"),
        ("POST /api/v1/auth/login", "401", RED, "120ms"),
        ("GET /admin/dashboard", "403", GOLD, "23ms"),
        ("PUT /api/v1/profile", "200", GREEN, "67ms"),
        ("DELETE /api/v1/sessions", "405", ORANGE, "12ms"),
        ("GET /graphql?query={}", "200", GREEN, "89ms"),
    ]
    for i, (req, status, color, time) in enumerate(probes):
        iy = 268 + i * 30
        s += rect(751, iy, 475, 24, fill=BG3, rx=4)
        s += text(760, iy + 16, req, fill=TEXT2, size=10, font="JetBrains Mono")
        s += text(1020, iy + 16, status, fill=color, size=11, font="JetBrains Mono", weight="600")
        s += text(1070, iy + 16, time, fill=TEXT3, size=10, font="JetBrains Mono")
    # Evidence Composer
    s += card(240, 472, 1000, 290)
    s += text(256, 494, "Evidence Composer", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    evidence = [
        ("PoC (curl)", "curl -X POST 'https://api.target.com/login' -d \"username=admin' OR 1=1--\"", GREEN),
        ("PoC (Python)", "requests.post(url, data={'username': \"admin' OR 1=1--\"})", PURPLE),
        ("CVSS 3.1", "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H — Score: 9.8", RED),
        ("CWE", "CWE-89: SQL Injection", GOLD),
        ("CAPEC", "CAPEC-66: SQL Injection via Parameter", PURPLE_MID),
        ("MITRE", "T1190: Exploit Public-Facing Application", CYAN),
    ]
    for i, (label, value, color) in enumerate(evidence):
        iy = 524 + i * 36
        s += rect(260, iy, 120, 24, fill=BG3, rx=4)
        s += text(268, iy + 16, label, fill=color, size=10, font="Orbitron", weight="600")
        s += rect(390, iy, 830, 24, fill=BG3, rx=4)
        s += text(398, iy + 16, value, fill=TEXT2, size=10, font="JetBrains Mono")
    return s


def gen_knowledge():
    s = svg_open()
    s += sidebar("Intelligence")
    s += topbar("Knowledge Intelligence")
    # Evidence Graph
    s += card(240, 72, 500, 320)
    s += text(256, 94, "Evidence Graph", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    # Central node
    s += circle(490, 240, 30, PURPLE, filt="glowStrong")
    s += text(490, 244, "SQLi", fill=BG, size=11, font="Orbitron", weight="700", anchor="middle")
    # Evidence nodes
    evid_nodes = [
        (340, 160, "PoC", GREEN, 0.9),
        (640, 160, "CVSS", GOLD, 0.8),
        (340, 320, "CWE", PURPLE_MID, 0.7),
        (640, 320, "CURL", CYAN, 0.6),
        (490, 120, "MITRE", RED, 0.85),
        (490, 360, "REQUEST", ORANGE, 0.75),
    ]
    for nx, ny, label, color, strength in evid_nodes:
        s += circle(nx, ny, 18, color, op=0.8, filt="glow")
        s += text(nx, ny + 4, label, fill=BG, size=8, font="Orbitron", weight="700", anchor="middle")
        s += line(490, 240, nx, ny, stroke=color, sw=1, op=strength * 0.4)
    # Balance score
    s += rect(270, 358, 160, 20, fill=BG3, rx=10)
    s += rect(270, 358, int(160 * 0.78), 20, fill=GREEN, rx=10, op=0.7)
    s += text(280, 372, "Balance: 78%", fill=TEXT, size=10, font="JetBrains Mono")
    # Knowledge Graph
    s += card(755, 72, 485, 320)
    s += text(771, 94, "Knowledge Graph Explorer", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    kg_nodes = [
        ("Target", 850, 150, PURPLE),
        ("Finding", 980, 150, RED),
        ("Evidence", 850, 230, GREEN),
        ("Report", 980, 230, GOLD),
        ("Payout", 850, 310, GOLD),
        ("Learning", 980, 310, CYAN),
    ]
    for label, kx, ky, color in kg_nodes:
        s += rect(kx - 40, ky - 12, 80, 24, fill=BG3, rx=12, stroke=color, sw=1)
        s += text(kx, ky + 4, label, fill=color, size=9, font="Orbitron", weight="600", anchor="middle")
    # Arrows
    s += line(890, 150, 940, 150, stroke=TEXT3, sw=1)
    s += line(850, 162, 850, 218, stroke=TEXT3, sw=1)
    s += line(1020, 150, 1020, 218, stroke=TEXT3, sw=1)
    s += line(940, 230, 890, 230, stroke=TEXT3, sw=1)
    s += line(850, 242, 850, 298, stroke=TEXT3, sw=1)
    s += line(1020, 242, 1020, 298, stroke=TEXT3, sw=1)
    s += text(771, 365, "SQL query explorer available via COPILOT", fill=TEXT3, size=9)
    # Decision Journal
    s += card(240, 406, 1000, 160)
    s += text(256, 428, "Decision Journal — Append-Only", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    decisions = [
        ("2026-07-25 14:32", "Validated SQLi in /login — confidence 94%", GREEN),
        ("2026-07-25 13:18", "Rejected XSS in /search — false positive (DOM context)", RED),
        ("2026-07-25 12:05", "Escalated IDOR in /api/v2/users — EV $1,200", GOLD),
        ("2026-07-25 11:42", "Confirmed SSRF via webhook — 3 evidence nodes", PURPLE),
    ]
    for i, (ts, desc, color) in enumerate(decisions):
        iy = 458 + i * 28
        s += circle(270, iy + 4, 3, color)
        s += text(280, iy + 4, ts, fill=TEXT3, size=10, font="JetBrains Mono")
        s += text(440, iy + 4, desc, fill=TEXT, size=11)
    # COPILOT integration
    s += card(240, 582, 1000, 180)
    s += text(256, 604, "COPILOT — Natural Language Query", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    s += rect(270, 624, 940, 36, fill=BG3, rx=8, stroke=PURPLE, sw=1)
    s += text(286, 647, "What are the top 3 findings by EV this week?", fill=PURPLE, size=12)
    s += rect(270, 672, 940, 80, fill=BG3, rx=8)
    s += text(286, 694, "1. SQLi in api.paypal.com/login — $2,400 EV — confidence 94%", fill=GREEN, size=11)
    s += text(286, 714, "2. Auth bypass via OAuth in app.stripe.com — $1,800 EV — confidence 87%", fill=GREEN, size=11)
    s += text(286, 734, "3. IDOR in dev.notion.so/api — $1,200 EV — confidence 82%", fill=GREEN, size=11)
    return s


def gen_automation():
    s = svg_open()
    s += sidebar("Pipeline")
    s += topbar("Automation & Operations — MERLIN")
    # Core Scheduler
    s += card(240, 72, 1000, 140)
    s += text(256, 94, "Core Scheduler — 13-Stage Pipeline", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    sched_stages = [
        ("IDLE", TEXT3),
        ("RECON", PURPLE),
        ("PROBE", PURPLE_MID),
        ("ANALYZE", PURPLE),
        ("HYPOTHESIS", GOLD),
        ("VALIDATE", GREEN),
        ("CONFIRM", GREEN),
        ("REPORT", ORANGE),
        ("OPTIMIZE", GOLD),
        ("SUBMIT", GREEN),
        ("TRACK", CYAN),
        ("LEARN", PURPLE),
        ("DONE", GREEN),
    ]
    sx = 260
    sy = 120
    stage_w = 68
    for i, (label, color) in enumerate(sched_stages):
        s += rect(sx + i * stage_w, sy, stage_w - 4, 28, fill=color, rx=6)
        tc = BG if color in (GREEN, GOLD, ORANGE) else TEXT
        s += text(
            sx + i * stage_w + stage_w // 2 - 2,
            sy + 18,
            label,
            fill=tc,
            size=7,
            font="Orbitron",
            weight="600",
            anchor="middle",
        )
    s += text(
        260,
        sy + 50,
        "Scheduler: Active  |  Last run: 2 min ago  |  Next: 28 min  |  Jobs: 8 registered",
        fill=TEXT3,
        size=10,
    )
    # Hermes Agent
    s += card(240, 228, 480, 220)
    s += text(256, 250, "Hermes Automation Agent", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    hermes_cmds = [
        ("scan --target <domain>", "Deep recon + vulnerability scan"),
        ("report --finding <id>", "Generate evidence-backed report"),
        ("submit --report <id>", "Auto-submit to platform"),
        ("learn --outcome <result>", "Update acceptance memory"),
        ("health --check", "System health + diagnostics"),
        ("hunt --mode aggressive", "Full pipeline E2E execution"),
    ]
    for i, (cmd, desc) in enumerate(hermes_cmds):
        iy = 278 + i * 28
        s += rect(270, iy, 210, 22, fill=BG3, rx=4)
        s += text(278, iy + 15, cmd, fill=PURPLE, size=9, font="JetBrains Mono")
        s += text(490, iy + 15, desc, fill=TEXT3, size=9)
    # Workflow Engine
    s += card(735, 228, 505, 220)
    s += text(751, 250, "Workflow Engine", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    workflows = [
        ("Bug Bounty Pipeline", "E2E: scan → report → submit → track", GREEN),
        ("Nightly Health Check", "System diagnostics + auto-heal", PURPLE),
        ("Revenue Optimization", "EV scoring + target prioritization", GOLD),
        ("Learning Loop", "Feedback integration + model update", CYAN),
    ]
    for i, (name, desc, color) in enumerate(workflows):
        iy = 278 + i * 42
        s += circle(755, iy + 8, 4, color)
        s += text(768, iy + 12, name, fill=TEXT, size=12, font="Orbitron", weight="600")
        s += text(768, iy + 28, desc, fill=TEXT3, size=10)
    # Extension SDK
    s += card(240, 464, 480, 150)
    s += text(256, 486, "Extension SDK", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    sdk_items = [
        "Hot reload support",
        "Manifest-based registration",
        "Event hooks for all stages",
        "Custom reasoner plugin API",
    ]
    for i, item in enumerate(sdk_items):
        s += circle(272, 514 + i * 24, 3, PURPLE_MID)
        s += text(284, 518 + i * 24, item, fill=TEXT2, size=11)
    # Senior Copilot Agent
    s += card(735, 464, 505, 150)
    s += text(751, 486, "Senior Copilot Agent", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    copilot_items = [
        ("Authority Levels", "5 levels: observer → advisor → executor → autonomous → override"),
        ("Auditors", "4 active: security, performance, accuracy, compliance"),
        ("Policy Engine", "12 rules active, 3 pending review"),
        ("Recommender", "Next-best-action engine with EV scoring"),
    ]
    for i, (label, desc) in enumerate(copilot_items):
        iy = 514 + i * 24
        s += text(755, iy, label, fill=GOLD, size=10, font="Orbitron", weight="600")
        s += text(900, iy, desc, fill=TEXT3, size=9)
    # Status bar
    s += card(240, 630, 1000, 130)
    s += text(256, 652, "System Status", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    status_items = [
        ("CoreScheduler", "Active", GREEN, "13 stages, 8 jobs"),
        ("EventBus", "Active", GREEN, "40+ event types, 0 stuck"),
        ("AgentBus", "Active", GREEN, "4 agents responsive"),
        ("RecoveryEngine", "Idle", PURPLE, "Last heal: 2h ago"),
    ]
    for i, (svc, status, color, desc) in enumerate(status_items):
        sx_i = 270 + i * 240
        s += circle(sx_i, 682, 5, color, filt="glow")
        s += text(sx_i + 14, 686, svc, fill=TEXT, size=11, font="Orbitron", weight="600")
        s += text(sx_i + 14, 702, status, fill=color, size=10)
        s += text(sx_i + 14, 718, desc, fill=TEXT3, size=9)
    return s


def gen_architecture():
    s = svg_open()
    s += sidebar("System")
    s += topbar("Architecture Overview — ORION")
    # Core block
    s += rect(300, 80, 680, 180, fill=BG3, rx=12, stroke=PURPLE_DEEP, sw=1)
    s += text(316, 102, "ORION CORE", fill=PURPLE, size=14, font="Orbitron", weight="700", ls=2)
    core_items = [
        ("Registry", 330, 130),
        ("EventBus", 470, 130),
        ("Scheduler", 610, 130),
        ("DB Manager", 330, 170),
        ("AI Runtime", 470, 170),
        ("Memory", 610, 170),
        ("Decision Journal", 330, 210),
        ("Simulation", 470, 210),
    ]
    for label, cx_i, cy_i in core_items:
        s += rect(cx_i, cy_i, 120, 28, fill=PURPLE_DEEP, rx=6)
        s += text(cx_i + 60, cy_i + 18, label, fill=TEXT, size=10, font="Orbitron", weight="600", anchor="middle")
    # Shared Security Layer
    s += rect(300, 280, 680, 50, fill=BG3, rx=8, stroke=GOLD, sw=1)
    s += text(
        640,
        310,
        "SHARED SECURITY LAYER — Auth · CSRF · Encryption · Audit",
        fill=GOLD,
        size=11,
        font="Orbitron",
        weight="600",
        anchor="middle",
        ls=1,
    )
    # Apps
    apps = [("CATEYE", 320, 360, RED), ("ATLAS", 560, 360, GREEN), ("ODYSSEY", 800, 360, CYAN)]
    for label, ax, ay, color in apps:
        s += rect(ax, ay, 180, 80, fill=BG3, rx=10, stroke=color, sw=1.5)
        s += text(ax + 90, ay + 30, label, fill=color, size=16, font="Orbitron", weight="700", anchor="middle", ls=2)
        s += text(ax + 90, ay + 52, "Bug Bounty Intel", fill=TEXT3, size=9, anchor="middle")
    # Frontend
    s += rect(300, 470, 680, 50, fill=BG3, rx=8, stroke=PURPLE, sw=1)
    s += text(
        640,
        500,
        "FRONTEND — Vue 3 · TypeScript · Tailwind · ShadCN",
        fill=PURPLE,
        size=11,
        font="Orbitron",
        weight="600",
        anchor="middle",
        ls=1,
    )
    # Arrows
    s += line(640, 260, 640, 280, stroke=TEXT3, sw=2)
    s += line(420, 330, 420, 360, stroke=TEXT3, sw=2)
    s += line(640, 330, 640, 360, stroke=TEXT3, sw=2)
    s += line(860, 330, 860, 360, stroke=TEXT3, sw=2)
    s += line(640, 440, 640, 470, stroke=TEXT3, sw=2)
    # Problems documented
    s += card(240, 540, 1000, 220)
    s += text(
        256,
        562,
        "Known Issues — 4 Critical Problems Documented",
        fill=RED,
        size=13,
        font="Orbitron",
        weight="600",
        ls=1,
    )
    problems = [
        ("0.1", "EventBus bridge not propagating legacy events", "FIXED", GREEN),
        ("0.2", "CATEYE manifest exporting empty router list", "FIXED", GREEN),
        ("0.3", "Scheduler jobs not registered at startup", "FIXED", GREEN),
        ("0.4", "Frontend routes not connected to backend APIs", "FIXED", GREEN),
    ]
    for i, (pid, desc, status, color) in enumerate(problems):
        iy = 592 + i * 32
        s += rect(270, iy, 40, 22, fill=PURPLE_DEEP, rx=4)
        s += text(290, iy + 15, pid, fill=PURPLE, size=11, font="Orbitron", weight="700", anchor="middle")
        s += text(320, iy + 15, desc, fill=TEXT, size=11)
        s += rect(960, iy, 60, 22, fill=color, rx=11)
        s += text(990, iy + 15, status, fill=BG, size=9, font="Orbitron", weight="700", anchor="middle")
    return s


def gen_mobile():
    s = svg_open(w=420, h=800)
    # Mobile frame
    s += rect(0, 0, 420, 800, fill=BG)
    s += rect(10, 10, 400, 780, fill=BG2, rx=24, stroke=PURPLE_DEEP, sw=1)
    # Status bar
    s += text(30, 36, "09:41", fill=TEXT, size=14, font="JetBrains Mono", weight="600")
    s += circle(380, 32, 5, GREEN)
    s += text(340, 36, "5G", fill=TEXT2, size=10)
    # Header
    s += text(30, 80, "ORION", fill=PURPLE, size=28, font="Orbitron", weight="900", ls=4)
    s += text(30, 104, "Companion", fill=PURPLE_MID, size=14, ls=2)
    # Health score
    s += circle(210, 200, 60, BG3, stroke=PURPLE, sw=2)
    s += circle(210, 200, 60, GREEN, op=0.15)
    s += text(210, 195, "94", fill=GREEN, size=36, font="Orbitron", weight="900", anchor="middle")
    s += text(210, 218, "HEALTH", fill=TEXT3, size=10, font="Orbitron", weight="600", anchor="middle", ls=2)
    # Quick actions
    actions = [
        ("Scan", PURPLE, "🔍"),
        ("Report", GOLD, "📝"),
        ("Payouts", GREEN, "💰"),
        ("COPILOT", CYAN, "🤖"),
    ]
    for i, (label, color, icon) in enumerate(actions):
        ax = 30 + i * 95
        s += rect(ax, 290, 80, 80, fill=BG3, rx=12, stroke=color, sw=1)
        s += text(ax + 40, 330, icon, fill=color, size=24, anchor="middle")
        s += text(ax + 40, 358, label, fill=TEXT, size=9, font="Orbitron", weight="600", anchor="middle")
    # Status cards
    status_items = [
        ("Targets", "24 active", GREEN),
        ("Findings", "47 open", GOLD),
        ("Revenue", "$12,847", PURPLE),
        ("Pipeline", "Idle", TEXT3),
    ]
    for i, (label, value, color) in enumerate(status_items):
        iy = 400 + i * 52
        s += rect(30, iy, 360, 42, fill=BG3, rx=8)
        s += circle(50, iy + 21, 4, color)
        s += text(64, iy + 18, label, fill=TEXT2, size=12)
        s += text(370, iy + 18, value, fill=color, size=12, font="Orbitron", weight="600", anchor="end")
    # Recent activity
    s += text(30, 630, "RECENT ACTIVITY", fill=PURPLE, size=10, font="Orbitron", weight="600", ls=2)
    activities = [
        ("SQLi confirmed in api.target.com", GREEN, "2m ago"),
        ("Report submitted to HackerOne", GOLD, "15m ago"),
        ("New target added: app.newsite.com", PURPLE_MID, "1h ago"),
    ]
    for i, (desc, color, time) in enumerate(activities):
        iy = 650 + i * 32
        s += circle(40, iy + 4, 3, color)
        s += text(52, iy + 4, desc, fill=TEXT, size=10)
        s += text(380, iy + 4, time, fill=TEXT3, size=9, anchor="end")
    # Bottom nav
    s += rect(10, 740, 400, 50, fill=BG3, rx=0)
    nav_items = ["Home", "Dashboard", "Alerts", "Config"]
    for i, label in enumerate(nav_items):
        nx = 60 + i * 95
        c = PURPLE if i == 0 else TEXT3
        s += text(nx, 770, label, fill=c, size=10, font="Orbitron", weight="600", anchor="middle")
    return s


def gen_event_flow():
    s = svg_open()
    s += sidebar("Pipeline")
    s += topbar("Event Flow & Pipeline")
    # Pipeline stages horizontal
    stages = [
        ("DISCOVER", PURPLE, "TargetPrioritizer"),
        ("RECON", PURPLE_MID, "HTTPProbes"),
        ("HYPOTHESIS", GOLD, "Reasoners"),
        ("VALIDATE", GREEN, "ConfidenceEngine"),
        ("REPORT", ORANGE, "EvidenceComposer"),
        ("AUTO-REPORT", CYAN, "AutoSubmit"),
    ]
    s += card(240, 72, 1000, 120)
    s += text(256, 94, "Pipeline — 6 Stages", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    stage_w = 150
    for i, (label, color, component) in enumerate(stages):
        sx = 260 + i * (stage_w + 12)
        s += rect(sx, 112, stage_w, 56, fill=BG3, rx=8, stroke=color, sw=1.5)
        s += text(
            sx + stage_w // 2, 134, label, fill=color, size=10, font="Orbitron", weight="700", anchor="middle", ls=1
        )
        s += text(sx + stage_w // 2, 152, component, fill=TEXT3, size=8, anchor="middle")
        if i < len(stages) - 1:
            ax = sx + stage_w
            s += line(ax + 2, 140, ax + 10, 140, stroke=TEXT3, sw=2)
            s += f'  <polygon points="{ax + 12},140 {ax + 6},136 {ax + 6},144" fill="{TEXT3}"/>'
    # Producers/Consumers
    s += card(240, 208, 480, 260)
    s += text(256, 230, "Event Producers", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    producers = [
        ("TargetDiscoveryEvent", "DISCOVER"),
        ("ProbeResultEvent", "RECON"),
        ("HypothesisEvent", "HYPOTHESIS"),
        ("ValidationEvent", "VALIDATE"),
        ("ReportReadyEvent", "REPORT"),
        ("SubmissionEvent", "AUTO-REPORT"),
    ]
    for i, (evt, stage) in enumerate(producers):
        iy = 258 + i * 28
        s += rect(270, iy, 200, 22, fill=BG3, rx=4)
        s += text(278, iy + 15, evt, fill=PURPLE, size=9, font="JetBrains Mono")
        s += rect(480, iy, 100, 22, fill=PURPLE_DEEP, rx=4)
        s += text(530, iy + 15, stage, fill=PURPLE, size=8, font="Orbitron", weight="600", anchor="middle")
    s += card(735, 208, 505, 260)
    s += text(751, 230, "Event Consumers", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    consumers = [
        ("CoreEventBus", "Central hub", GREEN),
        ("CATEYE Legacy Bridge", "Backward compat", GOLD),
        ("KnowledgeGraph", "Persistence", PURPLE_MID),
        ("DecisionJournal", "Audit trail", ORANGE),
        ("LearningLoop", "Feedback", CYAN),
        ("MetricsCollector", "Observability", RED),
    ]
    for i, (svc, desc, color) in enumerate(consumers):
        iy = 258 + i * 28
        s += circle(755, iy + 8, 4, color)
        s += text(768, iy + 4, svc, fill=TEXT, size=10, font="JetBrains Mono")
        s += text(960, iy + 4, desc, fill=TEXT3, size=9)
    # Correlation ID
    s += card(240, 484, 1000, 100)
    s += text(256, 506, "Correlation ID — End-to-End Trace", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    s += rect(270, 524, 940, 32, fill=BG3, rx=6, stroke=PURPLE, sw=1)
    s += text(
        280,
        544,
        "corr_id=abc-123-def  |  DISCOVER→RECON→HYPOTHESIS→VALIDATE→REPORT→SUBMIT  |  6 events  |  2.4s total",
        fill=PURPLE_MID,
        size=10,
        font="JetBrains Mono",
    )
    # Event catalog
    s += card(240, 600, 1000, 160)
    s += text(256, 622, "Event Catalog — 40+ Types", fill=TEXT, size=13, font="Orbitron", weight="600", ls=1)
    event_cats = [
        ("Discovery", "8 types", PURPLE),
        ("Intelligence", "12 types", GOLD),
        ("Validation", "6 types", GREEN),
        ("Revenue", "5 types", PURPLE_MID),
        ("System", "10+ types", CYAN),
    ]
    for i, (cat, count, color) in enumerate(event_cats):
        ex = 270 + i * 190
        s += rect(ex, 650, 170, 50, fill=BG3, rx=8, stroke=color, sw=1)
        s += text(ex + 85, 670, cat, fill=color, size=12, font="Orbitron", weight="600", anchor="middle")
        s += text(ex + 85, 688, count, fill=TEXT3, size=10, anchor="middle")
    return s


def gen_cover():
    s = svg_open()
    # Full background with radial glow
    s += f'''  <defs>
    <radialGradient id="coverGlow" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="{PURPLE}" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="{BG}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <rect width="{W}" height="{H}" fill="url(#coverGlow)"/>
'''
    # Grid
    s += """  <pattern id="cgrid" width="40" height="40" patternUnits="userSpaceOnUse">
    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#6D28D9" stroke-width="0.3" opacity="0.12"/>
  </pattern>
  <rect width="1280" height="800" fill="url(#cgrid)"/>
"""
    # Logo mark (centered)
    s += f'''  <g transform="translate(540, 80)">
    <circle cx="100" cy="100" r="80" fill="{PURPLE}" opacity="0.08"/>
    <ellipse cx="100" cy="100" rx="120" ry="40" fill="none" stroke="{PURPLE_DEEP}" stroke-width="1" transform="rotate(-25 100 100)" opacity="0.4"/>
    <ellipse cx="100" cy="100" rx="95" ry="32" fill="none" stroke="{PURPLE_MID}" stroke-width="1.5" transform="rotate(20 100 100)" opacity="0.6"/>
    <ellipse cx="100" cy="100" rx="70" ry="24" fill="none" stroke="{PURPLE}" stroke-width="2.5" transform="rotate(-10 100 100)" filter="url(#glow)"/>
    <circle cx="40" cy="82" r="2" fill="{GREEN}" opacity="0.8"/>
    <circle cx="160" cy="118" r="2" fill="{GREEN}" opacity="0.6"/>
    <circle cx="65" cy="118" r="1.5" fill="{GOLD}" opacity="0.7"/>
    <path d="M 100 100 L 180 50 A 110 110 0 0 1 195 90 Z" fill="{GOLD}" opacity="0.08"/>
    <circle cx="100" cy="100" r="14" fill="{PURPLE}" filter="url(#glowStrong)"/>
    <circle cx="100" cy="100" r="5" fill="#FFF" opacity="0.9"/>
  </g>
'''
    # Title
    s += text(640, 330, "ORION", fill=PURPLE, size=72, font="Orbitron", weight="900", anchor="middle", ls=12)
    s += text(
        640,
        365,
        "SECURITY INTELLIGENCE OS",
        fill=PURPLE_MID,
        size=16,
        font="Orbitron",
        weight="400",
        anchor="middle",
        ls=8,
        op=0.7,
    )
    s += line(440, 385, 840, 385, stroke=GOLD, sw=1, op=0.3)
    s += text(640, 410, "v4.7.0  |  STABLE", fill=TEXT3, size=12, font="JetBrains Mono", anchor="middle", ls=2)
    # Pillars
    pillars = [
        ("AEGIS", "Security Layer", PURPLE),
        ("CATEYE", "Bug Bounty Intel", RED),
        ("ATLAS", "Recon & Discovery", GREEN),
        ("ODYSSEY", "Revenue Intelligence", GOLD),
        ("MERLIN", "Automation", PURPLE_MID),
        ("COPILOT", "AI Assistant", CYAN),
        ("REVENUE", "Economic Engine", ORANGE),
    ]
    for i, (name, desc, color) in enumerate(pillars):
        px = 60 + i * 170
        s += rect(px, 460, 150, 70, fill=BG3, rx=8, stroke=color, sw=1)
        s += text(px + 75, 486, name, fill=color, size=13, font="Orbitron", weight="700", anchor="middle", ls=1)
        s += text(px + 75, 506, desc, fill=TEXT3, size=9, anchor="middle")
    # System status
    s += card(240, 560, 800, 80)
    s += text(256, 582, "SYSTEM STATUS", fill=PURPLE, size=10, font="Orbitron", weight="600", ls=2)
    status = [
        ("Backend", GREEN),
        ("EventBus", GREEN),
        ("Scheduler", GREEN),
        ("Agents", GREEN),
        ("Database", GREEN),
        ("355 Tests", GREEN),
    ]
    for i, (label, color) in enumerate(status):
        sx = 270 + i * 120
        s += circle(sx, 610, 4, color, filt="glow")
        s += text(sx + 12, 614, label, fill=TEXT, size=11)
    # Footer
    s += text(
        640,
        680,
        "Modular Monolith  |  Event-Driven  |  AI-Powered  |  100% Local",
        fill=TEXT3,
        size=11,
        anchor="middle",
        ls=2,
    )
    s += text(
        640, 710, "Built for Bug Bounty Hunters  |  by CATEYE", fill=PURPLE_MID, size=10, anchor="middle", ls=1, op=0.6
    )
    # Decorative corner elements
    s += f'''  <line x1="20" y1="20" x2="80" y2="20" stroke="{PURPLE}" stroke-width="1" opacity="0.3"/>
  <line x1="20" y1="20" x2="20" y2="80" stroke="{PURPLE}" stroke-width="1" opacity="0.3"/>
  <line x1="1260" y1="20" x2="1200" y2="20" stroke="{PURPLE}" stroke-width="1" opacity="0.3"/>
  <line x1="1260" y1="20" x2="1260" y2="80" stroke="{PURPLE}" stroke-width="1" opacity="0.3"/>
  <line x1="20" y1="780" x2="80" y2="780" stroke="{PURPLE}" stroke-width="1" opacity="0.3"/>
  <line x1="20" y1="780" x2="20" y2="720" stroke="{PURPLE}" stroke-width="1" opacity="0.3"/>
  <line x1="1260" y1="780" x2="1200" y2="780" stroke="{PURPLE}" stroke-width="1" opacity="0.3"/>
  <line x1="1260" y1="780" x2="1260" y2="720" stroke="{PURPLE}" stroke-width="1" opacity="0.3"/>
'''
    s += SVG_CLOSE
    return s


# ── Logos ────────────────────────────────────────────────────────────
def copy_logos():
    brand_dir = os.path.join(os.path.dirname(__file__), "..", "brand")
    for fname in ["logo-mark.svg", "logo-horizontal.svg", "logo.svg", "favicon.svg"]:
        src = os.path.join(brand_dir, fname)
        dst = os.path.join(OUT, fname.replace(".svg", "") + ".svg")
        if fname == "logo-mark.svg":
            dst = os.path.join(OUT, "orion-logo-mark.svg")
        elif fname == "logo-horizontal.svg":
            dst = os.path.join(OUT, "orion-logo-horizontal.svg")
        elif fname == "logo.svg":
            dst = os.path.join(OUT, "orion-logo-vertical.svg")
        elif fname == "favicon.svg":
            dst = os.path.join(OUT, "orion-favicon.svg")
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"[OK] {os.path.basename(dst)} (copied from brand/)")


# ── Main ─────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUT, exist_ok=True)
    generators = [
        ("orion-cover.svg", gen_cover),
        ("orion-dashboard.svg", gen_dashboard),
        ("orion-revenue-intelligence.svg", gen_revenue),
        ("orion-offensive-intelligence.svg", gen_offensive),
        ("orion-knowledge-intelligence.svg", gen_knowledge),
        ("orion-automation-operations.svg", gen_automation),
        ("orion-architecture-overview.svg", gen_architecture),
        ("orion-mobile-companion.svg", gen_mobile),
        ("orion-event-flow.svg", gen_event_flow),
    ]
    for fname, gen_fn in generators:
        path = os.path.join(OUT, fname)
        content = gen_fn()
        with open(path, "w") as f:
            f.write(content)
        print(f"[OK] {fname}")

    copy_logos()

    # Generate README
    readme = """# ORION Platform — Screenshots

Imágenes del sistema ORION Platform v4.7.0. Todos los screenshots son SVGs generados con la estética cyber/terminal del sistema (púrpura `#A855F7` / oro `#F5A623` sobre negro `#050508`).

## Pantallas Principales

| Screenshot | Descripción |
|---|---|
| [![Cover](screenshots/orion-cover.svg)](screenshots/orion-cover.svg) | **ORION Cover / Hero** — Portada del sistema con logo ORION (marca CE), versión, pilares funcionales (AEGIS, CATEYE, ATLAS, ODYSSEY, MERLIN, COPILOT, REVENUE) y estado del sistema. |
| [![Dashboard](screenshots/orion-dashboard.svg)](screenshots/orion-dashboard.svg) | **Dashboard Principal ORION** — Centro de mando con KPIs en tiempo real (targets, endpoints, hallazgos, pagos), gráficos de severidad y veredictos, oportunidades prioritarias con EV scoring. |
| [![Revenue Intelligence](screenshots/orion-revenue-intelligence.svg)](screenshots/orion-revenue-intelligence.svg) | **Revenue Intelligence** — Pipeline completo Finding→Evidence→Report→Platform→Payout. Desglose por plataforma (HackerOne, Bugcrowd, Intigriti, Immunefi), Target Prioritizer con EV scoring, Economic Memory (aprendizaje de pagos), Report Acceptance Optimizer. |
| [![Offensive Intelligence](screenshots/orion-offensive-intelligence.svg)](screenshots/orion-offensive-intelligence.svg) | **Inteligencia Ofensiva (CATEYE)** — 5 Reasoners (IDOR, SSRF, XSS, SQLi, Auth Bypass) con stats, técnicas y hallazgos recientes. Contradiction Engine (7 tipos), Evidence Composer (PoC, curl, Python, CVSS, CWE, CAPEC, MITRE), HTTP Probes Pipeline en vivo. |
| [![Knowledge Intelligence](screenshots/orion-knowledge-intelligence.svg)](screenshots/orion-knowledge-intelligence.svg) | **Inteligencia de Conocimiento** — Evidence Graph (nodo central + evidencias a favor/en contra/neutral con balance scoring), Knowledge Graph (explorador SQL de nodos/aristas), Decision Journal (append-only), integración COPILOT (consultas en lenguaje natural). |
| [![Automation & Operations](screenshots/orion-automation-operations.svg)](screenshots/orion-automation-operations.svg) | **Automatización y Operaciones (MERLIN)** — Core Scheduler (13 etapas pipeline E2E), Hermes Automation Agent (6 comandos), Workflow Engine (definiciones declarativas), Extension SDK (hot reload, manifest, hooks), Senior Copilot Agent (5 niveles autoridad, 4 auditors, Policy Engine, Recommender). |
| [![Architecture Overview](screenshots/orion-architecture-overview.svg)](screenshots/orion-architecture-overview.svg) | **Visión Arquitectónica** — Diagrama completo monolito modular + event-driven: ORION Core (Registry, EventBus, Scheduler, DB Manager, AI Runtime, Memory, Decision Journal, Simulation), Shared Security Layer, Apps (CATEYE/ATLAS/ODYSSEY), Frontend (Vue 3). Incluye 4 problemas críticos documentados (0.1-0.4) con fixes propuestos. |
| [![Mobile Companion](screenshots/orion-mobile-companion.svg)](screenshots/orion-mobile-companion.svg) | **ORION Companion (Android/Wear OS)** — Centro de control móvil: health score, tabs (Home/Dashboard/Alertas/Config), quick actions (Scan, Reportar, Cobros, COPILOT), estado del sistema en un vistazo. |
| [![Event Flow / Pipeline](screenshots/orion-event-flow.svg)](screenshots/orion-event-flow.svg) | **Flujo de Eventos y Pipeline** — 6 etapas pipeline horizontal (DISCOVER→RECON→HYPOTHESIS→VALIDATE→REPORT→AUTO-REPORT), productores/consumidores de eventos, CoreEventBus central con bridge a legacy, Correlation ID trace E2E, catálogo 40+ tipos de eventos. |

---

## Logos y Branding

| Asset | Descripción |
|---|---|
| [![Logo Mark](screenshots/orion-logo-mark.svg)](screenshots/orion-logo-mark.svg) | **Logo Mark** — Icono principal ORION (anillos orbitales, core púrpura/oro, punto cian). |
| [![Logo Horizontal](screenshots/orion-logo-horizontal.svg)](screenshots/orion-logo-horizontal.svg) | **Logo Horizontal** — Para sidebar/header. |
| [![Logo Vertical](screenshots/orion-logo-vertical.svg)](screenshots/orion-logo-vertical.svg) | **Logo Vertical** — Para splash/loading. |
| [![Favicon](screenshots/orion-favicon.svg)](screenshots/orion-favicon.svg) | **Favicon** — 48×48 optimizado. |

---

## Convenciones Visuales

- **Fondo**: `#050508` con grid sutil y scanline overlay
- **Púrpura primario**: `#A855F7` / `#7C3AED` / `#6D28D9` — marca, headers, acentos
- **Oro acento**: `#F5A623` / `#FFCC66` — métricas económicas, warnings, highlights
- **Verde éxito**: `#00FF41` / `#00E676` — confirmados, activo, online
- **Cian info**: `#00FFFF` / `#00B8FF` — EventBus, COPILOT, arquitectura
- **Naranja warning**: `#FF6600` / `#FFAB00` — medio-alto, cola
- **Rojo crítico**: `#FF1744` / `#FF4466` — rechazados, errores, bugs críticos
- **Tipografía**: Orbitron (display/títulos), Inter (sans), JetBrains Mono (mono/código)
- **Tarjetas**: Glass effect `rgba(12,12,18,0.92)` + borde `rgba(109,40,217,0.15)` + glow superior
- **Grid**: Pattern sutil 40×40px con `#6D28D9` opacity 0.12

---

## Regeneración

```bash
# Desde la raíz del proyecto
python scripts/generate_screenshots.py
```

Última actualización: **Julio 2026** — ORION v4.7.0 STABLE
"""
    with open(os.path.join(OUT, "README.md"), "w") as f:
        f.write(readme)
    print("[OK] README.md")
    print(f"\n✅ {len(generators)} screenshots + 4 logos + README generated in docs/screenshots/")


if __name__ == "__main__":
    main()
