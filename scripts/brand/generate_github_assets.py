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


# ---------------------------------------------------------------- logos ---
def draw_mark(draw: ImageDraw.ImageDraw, cx, cy, size, color=CYAN, node=BLUE, w=None):
    """O+X Aperture Nexus: octagonal ring + X rays + central node."""
    cx, cy, size = int(cx), int(cy), int(size)
    w = w or max(2, size // 22)
    r = size / 2
    pts = []
    for i in range(8):
        a = math.radians(22.5 + i * 45)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    draw.polygon(pts, outline=color, width=w)
    inner = [(cx + (x - cx) * 0.72, cy + (y - cy) * 0.72) for x, y in pts]
    draw.polygon(inner, outline=color + "66", width=w)
    n = size * 0.16
    rr(draw, (cx - n, cy - n, cx + n, cy + n), r=3, fill=node)
    draw.line((cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62), fill=color + "AA", width=w)
    draw.line((cx - r * 0.62, cy + r * 0.62, cx + r * 0.62, cy - r * 0.62), fill=color + "AA", width=w)


def lockup(w, h, color=CYAN, bg: str | None = BG, text_color=TEXT, sub_color=MUTED):
    img = Image.new("RGBA", (w, h), bg or (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    mark_sz = h * 0.62
    draw_mark(d, h * 0.62, h / 2, mark_sz, color=color)
    text(d, (h * 1.15, h / 2 - 22), "OWNEX", display_font(int(h * 0.34), 700), fill=text_color, anchor="lm")
    f = font(int(h * 0.115))
    t = "AUTONOMOUS WORK OPERATING SYSTEM"
    tw = d.textlength(t, font=f)
    text(
        d,
        (h * 1.15 + (d.textlength("OWNEX", display_font(int(h * 0.34), 700)) - tw) / 2, h / 2 + 20),
        t,
        f,
        fill=sub_color,
        anchor="lm",
    )
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
    draw_mark(d, 44, 42, 40, color=CYAN, node=BLUE)
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
def render_hero(mode: str = "dark") -> Image.Image:
    w, h = 2400, 900
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    # subtle grid
    for gx in range(0, w, 120):
        d.line((gx, 0, gx, h), fill="#0A0C11", width=1)
    for gy in range(0, h, 120):
        d.line((0, gy, w, gy), fill="#0A0C11", width=1)

    # centered brand lockup
    cx = w // 2
    draw_mark(d, cx - 470, h // 2 - 150, 300, color=CYAN, node=BLUE)
    text(d, (cx + 120, h // 2 - 150), "OWNEX", display_font(150, 700), anchor="lm")
    text(d, (cx + 122, h // 2 + 60), "AUTONOMOUS WORK OPERATING SYSTEM", font(34), fill=MUTED, anchor="lm")

    chip(d, cx - 210, h - 150, "100% local · no cloud · no telemetry", EMERALD, 18)
    chip(d, cx + 40, h - 150, "bug bounty · dev bounty · AI work · wealth", CYAN, 18)
    return img


def render_og() -> Image.Image:
    img = render_hero()
    return img.resize((1200, 630), Image.Resampling.LANCZOS)


# ----------------------------------------------------------------- main ---
def make_surface_renderer(name: str, spec: dict) -> Callable[[], Image.Image]:
    return lambda: render_surface(name, spec)


def make_mobile_renderer(name: str, spec: dict) -> Callable[[], Image.Image]:
    return lambda: render_mobile(name, spec)


ASSETS = {
    "hero": {
        "hero-banner-dark.png": lambda: render_hero("dark"),
    },
    "logo": {
        "lockup-horizontal.png": lambda: lockup(2048, 512),
        "lockup-horizontal-light.png": lambda: lockup(2048, 512, bg=None, text_color="#0D0F14", sub_color="#4B5563"),
        "mark-aperture-alpha.png": lambda: mark_img(1024, CYAN, BLUE, bg=None),
        "mark-aperture-omega.png": lambda: mark_img(1024, EMERALD, CYAN, bg=None),
        "mark-mono-white.png": lambda: mark_img(1024, WHITE, WHITE, bg=None),
        "mark-mono-black.png": lambda: mark_img(1024, "#0D0F14", "#0D0F14", bg=None),
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
    draw_mark(ImageDraw.Draw(img), size / 2, size / 2, size * 0.78, color=color, node=node)
    return img


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
    print(f"\nGenerated {total} assets in {OUT}")


if __name__ == "__main__":
    main()
