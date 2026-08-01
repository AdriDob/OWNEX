"""Generate the 5 OWNEX concept artworks (SVG + PNG, 2400×1350).

Consistent art direction: space-black canvas, blueprint grid, mono labels,
cyan/blue/emerald accents, Space Grotesk / Inter / JetBrains Mono type.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import CONCEPTS, C, mark_svg, render
from textlib import card_svg, footer_svg, footer_texts, header_svg, header_texts, text_pil

W, H = 2400, 1350


def canvas(svg: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <defs>
    <radialGradient id="bgGlow" cx="50%" cy="30%" r="60%">
      <stop offset="0%" stop-color="#00D5FF" stop-opacity="0.07"/>
      <stop offset="100%" stop-color="#05060A" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="#05060A"/>
  <rect width="{W}" height="{H}" fill="url(#bgGlow)"/>
  {grid()}
  {svg}
</svg>"""


def grid() -> str:
    lines = []
    for x in range(0, W + 1, 150):
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#0A0F1C" stroke-width="1"/>')
    for y in range(0, H + 1, 150):
        lines.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#0A0F1C" stroke-width="1"/>')
    return "".join(lines)


def emit(name: str, svg: str, texts: list, width: int = W) -> None:
    out = CONCEPTS / name
    (CONCEPTS / name.replace(".png", ".svg")).write_text(svg)
    render(svg, out, width=width, text_fn=lambda d, s: text_pil(d, texts, s), text_scale=width / W)
    print("concept:", out)


# ---------------------------------------------------------------------------
# 01 — Product Overview (ecosystem)
# ---------------------------------------------------------------------------


def product_overview() -> None:
    cxs, cys = W / 2, 720
    nodes = [
        ("ALPHA DESKTOP", "Command center · core operations", 240, 400, C["cyber_cyan"]),
        ("OMEGA MOBILE", "Android companion · approvals", 1120, 250, C["emerald"]),
        ("WEAR OS", "Wrist alerts · quick actions", 1360, 640, C["emerald"]),
        ("MERLIN", "Intelligent assistant", 560, 1080, C["cyber_cyan"]),
        ("AGENTS", "Autonomous departments", 1040, 1120, C["cyber_cyan"]),
        ("MEMORY", "Persistent knowledge store", 1880, 460, "#8A94A6"),
    ]
    cards = []
    links = []
    for _title, _sub, x, y, accent in nodes:
        links.append(
            f'<line x1="{cxs}" y1="{cys}" x2="{x}" y2="{y}" stroke="#16213A" stroke-width="2" stroke-dasharray="10 8"/>'
        )
        cards.append(card_svg(x - 150, y - 78, 300, 156))
        cards.append(f'<circle cx="{x - 116}" cy="{y - 42}" r="5" fill="{accent}"/>')
    cards.append(card_svg(cxs - 260, cys - 260, 520, 520, glow=True))

    mark = mark_svg("alpha", size=512)
    body = f"""
  {header_svg("PRODUCT OVERVIEW", "01", "ECOSYSTEM")}
  {"".join(links)}
  {"".join(cards)}
  <g transform="translate({cxs}, {cys}) scale(1.9)"><g transform="translate(-256,-256) scale(0.62)">{mark}</g></g>
  <rect x="{cxs - 260}" y="{cys + 120}" width="520" height="140" fill="#0B0E15" rx="16" stroke="#1D2430" stroke-width="1.5"/>
  {footer_svg(note="ONE CORE — TWO EDITIONS — EVERY DEVICE")}
"""
    texts = header_texts("PRODUCT OVERVIEW", "01", "ECOSYSTEM") + [
        (cxs, cys + 195, "OWNEX CORE", "sg", 700, 30, "#F6F8FB", 4, "center"),
    ]
    for title, _sub, x, y, _accent in nodes:
        texts += [
            (x, y - 20, title, "sg", 600, 24, "#F6F8FB", 2, "center"),
            (x, y + 14, _sub, "inter", 400, 16, C["muted"], 1, "center"),
        ]
    texts += footer_texts("ONE CORE — TWO EDITIONS — EVERY DEVICE", W, H)
    emit("product-overview.png", canvas(body), texts)


# ---------------------------------------------------------------------------
# 02 — Mission Control (dashboard)
# ---------------------------------------------------------------------------


def kpi_svg(x, y, w, h, label, value, delta, accent) -> str:
    return card_svg(x, y, w, h) + f'<rect x="{x}" y="{y + h - 4}" width="{w}" height="4" rx="2" fill="{accent}"/>'


def mission_control() -> None:
    sb_w, main_x = 300, 340
    kpi_w = (W - main_x - 120) / 4
    nav = ["MISSION CONTROL", "AGENT FLEET", "OPPORTUNITIES", "FINDINGS", "REPORTS", "TERMINAL", "MEMORY", "EVOLUTION"]
    body = f"""
  {header_svg("MISSION CONTROL", "02", "DASHBOARD")}
  <rect x="0" y="120" width="{sb_w}" height="{H - 120 - 72}" fill="#07090F"/>
  <line x1="{sb_w}" y1="120" x2="{sb_w}" y2="{H - 72}" stroke="#1D2430" stroke-width="1"/>
  {"".join(f'<circle cx="48" cy="{214 + i * 92}" r="4" fill="{"#00D5FF" if i == 0 else "#1D2430"}"/>' for i in range(len(nav)))}
  {kpi_svg(main_x, 160, kpi_w, 150, "HEALTH", "98", "+2", C["cyber_cyan"])}
  {kpi_svg(main_x + kpi_w + 20, 160, kpi_w, 150, "ACTIVE AGENTS", "12", "+3", C["cyber_cyan"])}
  {kpi_svg(main_x + 2 * (kpi_w + 20), 160, kpi_w, 150, "OPPORTUNITIES", "47", "+9", C["emerald"])}
  {kpi_svg(main_x + 3 * (kpi_w + 20), 160, kpi_w, 150, "REVENUE MTD", "$4,312", "+18%", C["emerald"])}
  {card_svg(main_x, 350, (W - main_x - 40) * 0.55, 420)}
  {card_svg(main_x + (W - main_x - 40) * 0.55 + 20, 350, (W - main_x - 40) * 0.45, 420)}
  {card_svg(main_x, 810, (W - main_x - 40) * 0.62, 400)}
  {card_svg(main_x + (W - main_x - 40) * 0.62 + 20, 810, (W - main_x - 40) * 0.38, 400)}
  {"".join(f'<rect x="{main_x + 40}" y="{408 + i * 64}" width="{380 if i % 2 == 0 else 320}" height="10" rx="5" fill="#16213A"/>' for i in range(5))}
  {"".join(f'<rect x="{main_x + (W - main_x - 40) * 0.55 + 60}" y="{408 + i * 64}" width="150" height="34" rx="8" fill="#0F1524" stroke="#1D2430" stroke-width="1"/>' for i in range(5))}
  {"".join(f'<rect x="{main_x + (W - main_x - 40) * 0.62 + 60}" y="{868 + i * 60}" width="{460 - i * 40}" height="8" rx="4" fill="#16213A"/>' for i in range(5))}
  {"".join(f'<circle cx="{main_x + (W - main_x - 40) * 0.62 + 60}" cy="{868 + i * 60}" r="6" fill="{"#00D5FF" if i % 2 == 0 else "#00E39A"}"/>' for i in range(5))}
  <rect x="{main_x + (W - main_x - 40) * 0.62 + 100}" y="930" width="330" height="150" rx="12" fill="#0F1524" stroke="#1D2430" stroke-width="1"/>
  {footer_svg(note="SCHEDULER ACTIVE · 26 JOBS · EVENT BUS HEALTHY")}
"""
    texts = header_texts("MISSION CONTROL", "02", "DASHBOARD")
    for i, n in enumerate(nav):
        texts.append(
            (78, 214 + i * 92, n, "jbm", 500 if i == 0 else 400, 18, "#F6F8FB" if i == 0 else "#8A94A6", 3, "left")
        )
    kpis = [
        ("HEALTH", "98", "+2"),
        ("ACTIVE AGENTS", "12", "+3"),
        ("OPPORTUNITIES", "47", "+9"),
        ("REVENUE MTD", "$4,312", "+18%"),
    ]
    for i, (lbl, val, d) in enumerate(kpis):
        x = main_x + i * (kpi_w + 20) + kpi_w / 2
        texts += [
            (x, 198, lbl, "jbm", 400, 16, C["muted"], 3, "center"),
            (x, 248, val, "sg", 700, 44, "#F6F8FB", 1, "center"),
            (x, 286, d, "inter", 500, 16, C["emerald"] if "+" in d else "#F6F8FB", 0, "center"),
        ]
    ax = main_x + 40
    texts += [
        (ax, 372, "AGENT FLEET", "jbm", 500, 18, "#F6F8FB", 3, "left"),
        (ax + 360, 372, "12 ACTIVE", "jbm", 400, 14, C["emerald"], 2, "left"),
        (ax + (W - main_x - 40) * 0.55 - 40, 372, "OPPORTUNITY RADAR", "jbm", 500, 18, "#F6F8FB", 3, "right"),
    ]
    for i in range(5):
        names = [
            "FORGE — Opire #412",
            "SECURITY — Recon stage",
            "PULSE — Review batch",
            "VAULT — Payout sync",
            "ATLAS — Market scan",
        ]
        status = ["EXECUTING", "SCHEDULED", "EXECUTING", "COMPLETE", "ANALYZING"][i]
        col = [C["cyber_cyan"], "#3D4A63", C["cyber_cyan"], C["emerald"], C["cyber_cyan"]][i]
        texts += [
            (ax, 408 + i * 64, names[i], "inter", 400, 17, "#F6F8FB", 0, "left"),
            (ax + (W - main_x - 40) * 0.55 + 85, 408 + i * 64, status, "jbm", 400, 13, col, 2, "center"),
        ]
    bx = main_x + (W - main_x - 40) * 0.62 + 60
    texts += [
        (bx, 868, "ACTIVITY FEED", "jbm", 500, 18, "#F6F8FB", 3, "left"),
        (bx + 800, 868, "NEXT BEST ACTION", "jbm", 500, 18, "#F6F8FB", 3, "left"),
    ]
    for i in range(5):
        act = [
            "Finding validated — IDOR #221",
            "Opportunity claimed — Opire",
            "Memory consolidated — 14 entries",
            "Report drafted — SSRF #118",
            "Agent retrained — FORGE 2.0",
        ][i]
        texts.append((bx + 22, 868 + i * 60, act, "inter", 400, 17, "#F6F8FB", 0, "left"))
    texts += [
        (bx + 100, 955, "PRIORITY: HIGH", "jbm", 500, 14, C["cyber_cyan"], 2, "center"),
        (bx + 100, 995, "Validate 3 pending findings with", "inter", 400, 16, "#F6F8FB", 0, "center"),
        (bx + 100, 1025, "highest EV before end of cycle.", "inter", 400, 16, "#F6F8FB", 0, "center"),
        (bx + 100, 1060, "EST. VALUE $1,240", "jbm", 500, 14, C["emerald"], 2, "center"),
    ]
    texts += footer_texts("SCHEDULER ACTIVE · 26 JOBS · EVENT BUS HEALTHY", W, H)
    emit("mission-control.png", canvas(body), texts)


# ---------------------------------------------------------------------------
# 03 — Architecture
# ---------------------------------------------------------------------------


def architecture() -> None:
    layers = [
        ("OWNEX CORE", "Event bus · scheduler · memory · security layer", C["cyber_cyan"]),
        ("DEPARTMENTS", "Orchestrator · Engineering · Quality · Security · Revenue", C["cyber_cyan"]),
        ("AGENTS", "Autonomous specialists coordinated per department", C["cyber_cyan"]),
        ("EXECUTION", "Workflows · executors · platform connectors", "#6A8CFF"),
        ("LEARNING", "Feedback loops · knowledge capture · reward models", C["emerald"]),
        ("EVOLUTION", "Self-improvement · version rollback · recovery", C["emerald"]),
    ]
    lw, lh, lx = 1500, 118, (W - 1500) / 2
    svg_parts = []
    for i, (_name, _sub, accent) in enumerate(layers):
        y = 260 + i * (lh + 62)
        svg_parts.append(card_svg(lx, y, lw, lh))
        svg_parts.append(f'<rect x="{lx}" y="{y}" width="10" height="{lh}" rx="5" fill="{accent}"/>')
        if i < len(layers) - 1:
            svg_parts.append(
                f'<line x1="{W / 2}" y1="{y + lh}" x2="{W / 2}" y2="{y + lh + 62}" stroke="#2A3650" stroke-width="2"/>'
            )
            svg_parts.append(
                f'<polygon points="{W / 2 - 9},{y + lh + 50} {W / 2 + 9},{y + lh + 50} {W / 2},{y + lh + 62}" fill="#2A3650"/>'
            )
    body = f"""
  {header_svg("ARCHITECTURE", "03", "SYSTEM FLOW")}
  {"".join(svg_parts)}
  <text x="120" y="330" font-family="JetBrains Mono, monospace" font-size="20" fill="#3D4A63" letter-spacing="3">CONTROL PLANE</text>
  <text x="120" y="620" font-family="JetBrains Mono, monospace" font-size="20" fill="#3D4A63" letter-spacing="3">ORGANIZATION</text>
  <text x="120" y="850" font-family="JetBrains Mono, monospace" font-size="20" fill="#3D4A63" letter-spacing="3">EXECUTION</text>
  <text x="120" y="1080" font-family="JetBrains Mono, monospace" font-size="20" fill="#3D4A63" letter-spacing="3">INTELLIGENCE</text>
  <text x="120" y="1290" font-family="JetBrains Mono, monospace" font-size="20" fill="#3D4A63" letter-spacing="3">FEEDBACK</text>
  {footer_svg(note="DESIGNED FOR AUTONOMY — HUMAN AT THE DECISION GATE")}
"""
    texts = header_texts("ARCHITECTURE", "03", "SYSTEM FLOW")
    for i, (name, sub, _accent) in enumerate(layers):
        y = 260 + i * (lh + 62)
        texts += [
            (lx + 44, y + 40, name, "sg", 700, 30, "#F6F8FB", 2, "left"),
            (lx + 44, y + 84, sub, "inter", 400, 18, C["muted"], 0, "left"),
        ]
        labels = ["CONTROL PLANE", "ORGANIZATION", "ORGANIZATION", "EXECUTION", "INTELLIGENCE", "FEEDBACK"]
        texts.append((120, y + 40, labels[i], "jbm", 400, 20, "#3D4A63", 3, "left"))
    texts += footer_texts("DESIGNED FOR AUTONOMY — HUMAN AT THE DECISION GATE", W, H)
    emit("architecture.png", canvas(body), texts)


# ---------------------------------------------------------------------------
# 04 — Mobile Experience (OMEGA + Wear OS)
# ---------------------------------------------------------------------------


def mobile_omega() -> None:
    phone_x, phone_y, phone_w, phone_h = 560, 250, 560, 1000
    watch_x, watch_y, watch_r = 1650, 540, 260
    body = f"""
  {header_svg("MOBILE EXPERIENCE", "04", "OMEGA EDITION")}
  <rect x="{phone_x}" y="{phone_y}" width="{phone_w}" height="{phone_h}" rx="56" fill="#0B0E15" stroke="#1D2430" stroke-width="3"/>
  <rect x="{phone_x + 24}" y="{phone_y + 24}" width="{phone_w - 48}" height="{phone_h - 48}" rx="38" fill="#07090F"/>
  <rect x="{phone_x + phone_w / 2 - 60}" y="{phone_y + 12}" width="120" height="8" rx="4" fill="#1D2430"/>
  <rect x="{phone_x + 60}" y="{phone_y + 70}" width="{phone_w - 120}" height="96" rx="14" fill="#0F1524" stroke="#1D2430" stroke-width="1"/>
  {"".join(f'<rect x="{phone_x + 60}" y="{phone_y + 200 + i * 150}" width="{phone_w - 120}" height="118" rx="14" fill="#0B0E15" stroke="#1D2430" stroke-width="1"/>' for i in range(4))}
  <circle cx="{watch_x}" cy="{watch_y}" r="{watch_r}" fill="#0B0E15" stroke="#1D2430" stroke-width="4"/>
  <circle cx="{watch_x}" cy="{watch_y}" r="{watch_r - 26}" fill="#07090F" stroke="#16213A" stroke-width="1"/>
  <rect x="{watch_x - 30}" y="{watch_y - watch_r - 34}" width="60" height="14" rx="7" fill="#1D2430"/>
  {"".join(f'<rect x="{watch_x - 170}" y="{watch_y - 120 + i * 70}" width="{340 - i * 50}" height="9" rx="4" fill="#16213A"/>' for i in range(3))}
  <rect x="{watch_x - 170}" y="{watch_y + 60}" width="340" height="120" rx="14" fill="#0F1524" stroke="#1D2430" stroke-width="1"/>
  <rect x="{watch_x - 170}" y="{watch_y + 200}" width="340" height="70" rx="14" fill="#0F1524" stroke="#1D2430" stroke-width="1"/>
  {footer_svg(note="PERMANENT CONNECTION — DESKTOP TO WRIST")}
"""
    texts = header_texts("MOBILE EXPERIENCE", "04", "OMEGA EDITION")
    texts += [
        (phone_x + phone_w / 2, phone_y + 118, "SYSTEM HEALTH 98", "jbm", 500, 20, "#F6F8FB", 3, "center"),
        (
            phone_x + phone_w / 2,
            phone_y + 148,
            "12 AGENTS · 3 PENDING APPROVALS",
            "jbm",
            400,
            15,
            C["emerald"],
            2,
            "center",
        ),
    ]
    cards = [
        ("APPROVAL REQUIRED", "FORGE · Submit PR #412 to Opire", C["cyber_cyan"], "APPROVE / REJECT"),
        ("MERLIN", "Morning brief: 3 opportunities scored high EV", C["cyber_cyan"], "OPEN CHAT"),
        ("NOTIFICATION", "Finding IDOR #221 validated — evidence ready", C["emerald"], "VIEW"),
        ("WATCH SYNC", "Wear OS connected · alerts enabled", C["emerald"], "CONFIG"),
    ]
    for i, (t, s, accent, btn) in enumerate(cards):
        y = phone_y + 200 + i * 150
        texts += [
            (phone_x + 92, y + 36, t, "jbm", 500, 16, accent, 2, "left"),
            (phone_x + 92, y + 74, s, "inter", 400, 17, "#F6F8FB", 0, "left"),
            (phone_x + phone_w - 92, y + 90, btn, "jbm", 400, 13, "#8A94A6", 1, "right"),
        ]
    texts += [
        (watch_x, watch_y - 200, "OMEGA", "sg", 700, 44, "#F6F8FB", 6, "center"),
        (watch_x, watch_y - 160, "WRIST ALERTS", "jbm", 400, 18, C["emerald"], 3, "center"),
        (watch_x, watch_y + 102, "APPROVAL: FORGE #412", "jbm", 500, 16, "#F6F8FB", 1, "center"),
        (watch_x, watch_y + 132, "SWIPE TO APPROVE", "inter", 400, 15, C["muted"], 1, "center"),
        (watch_x, watch_y + 235, "STATUS: CONNECTED", "jbm", 400, 15, C["emerald"], 2, "center"),
    ]
    texts += footer_texts("PERMANENT CONNECTION — DESKTOP TO PHONE", W, H)
    emit("mobile-omega.png", canvas(body), texts)


# ---------------------------------------------------------------------------
# 05 — Boot Sequence (cinematic)
# ---------------------------------------------------------------------------


def boot_sequence() -> None:
    mark = mark_svg("alpha", size=512)
    steps = [
        "VERIFYING SYSTEM INTEGRITY",
        "INITIALIZING EVENT BUS",
        "STARTING AGENT FLEET",
        "LOADING MEMORY",
        "SYNCING OMEGA DEVICES",
        "MISSION CONTROL ONLINE",
    ]
    body = f"""
  <g transform="translate(1200, 470) scale(1.4)"><g transform="translate(-256,-256) scale(0.55)">{mark}</g></g>
  {"".join(f'<rect x="870" y="{640 + i * 88}" width="660" height="44" rx="22" fill="#0B0E15" stroke="#1D2430" stroke-width="1"/>' for i in range(len(steps)))}
  {"".join(f'<rect x="890" y="{652 + i * 88}" width="{560 - i * 62}" height="20" rx="10" fill="#00D5FF" opacity="0.85"/>' for i in range(len(steps)))}
  {footer_svg(note="BOOT SEQUENCE 00:00:09 — CLEARANCE: AUTONOMOUS")}
"""
    texts = [
        (1200, 160, "INITIALIZING", "jbm", 400, 24, "#3D4A63", 8, "center"),
        (1200, 240, "OWNEX", "sg", 700, 110, "#F6F8FB", 12, "center"),
        (1200, 300, "AUTONOMOUS PERSONAL OPERATING SYSTEM", "inter", 400, 20, "#8A94A6", 6, "center"),
    ]
    for i, s in enumerate(steps):
        pct = f"{(i + 1) * 16:03d}%"
        texts += [
            (880, 663 + i * 88, f"0{i + 1}", "jbm", 400, 16, C["cyber_cyan"], 2, "left"),
            (944, 663 + i * 88, s, "jbm", 500, 17, "#F6F8FB", 2, "left"),
            (1520, 663 + i * 88, pct, "jbm", 400, 16, C["emerald"], 2, "right"),
        ]
    texts += footer_texts("BOOT SEQUENCE 00:00:09 — CLEARANCE: AUTONOMOUS", W, H)
    emit("boot-sequence.png", canvas(body), texts)


def main() -> None:
    CONCEPTS.mkdir(parents=True, exist_ok=True)
    product_overview()
    mission_control()
    architecture()
    mobile_omega()
    boot_sequence()
    print("All concepts generated →", CONCEPTS)


if __name__ == "__main__":
    main()
