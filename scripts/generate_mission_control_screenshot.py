"""Generate Mission Control screenshot concept.

Represents: Dashboard, metrics, agents, opportunities, system health
Style: Premium dashboard
Inspiration: Linear (modern), Apple (elegance), SpaceX (engineering)
"""

from pathlib import Path

SCREENSHOTS_DIR = Path("assets/branding/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Design System Colors
COLORS = {
    "primary_main": "#1A1A1A",
    "primary_light": "#2A2A2A",
    "accent_blue": "#3B82F6",
    "accent_cyan": "#06B6D4",
    "accent_emerald": "#10B981",
    "accent_gold": "#F59E0B",
    "accent_purple": "#8B5CF6",
    "white": "#FFFFFF",
}

def generate_mission_control_screenshot() -> str:
    """Generate Mission Control screenshot concept."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" width="1200" height="800">
  <defs>
    <linearGradient id="mcGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['primary_main']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['primary_light']};stop-opacity:1" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="1200" height="800" fill="url(#mcGrad)"/>

  <!-- Top Bar -->
  <rect x="0" y="0" width="1200" height="60" fill="{COLORS['primary_light']}" opacity="0.8"/>
  <text x="30" y="38" font-family="Inter, sans-serif" font-size="20" font-weight="700" fill="{COLORS['white']}">Mission Control</text>
  <circle cx="1150" cy="30" r="12" fill="{COLORS['accent_emerald']}" filter="url(#glow)"/>
  <text x="1100" y="35" font-family="Inter, sans-serif" font-size="12" fill="{COLORS['accent_emerald']}">ONLINE</text>

  <!-- KPI Cards Row -->
  <rect x="30" y="90" width="270" height="120" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_blue']}" stroke-width="1"/>
  <text x="50" y="120" font-family="Inter, sans-serif" font-size="12" fill="{COLORS['white']}" opacity="0.6">ACTIVE AGENTS</text>
  <text x="50" y="150" font-family="Inter, sans-serif" font-size="36" font-weight="700" fill="{COLORS['accent_blue']}">12</text>
  <text x="50" y="175" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['accent_emerald']}">+3 this hour</text>

  <rect x="320" y="90" width="270" height="120" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_cyan']}" stroke-width="1"/>
  <text x="340" y="120" font-family="Inter, sans-serif" font-size="12" fill="{COLORS['white']}" opacity="0.6">WORKFLOWS RUNNING</text>
  <text x="340" y="150" font-family="Inter, sans-serif" font-size="36" font-weight="700" fill="{COLORS['accent_cyan']}">8</text>
  <text x="340" y="175" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['accent_emerald']}">All healthy</text>

  <rect x="610" y="90" width="270" height="120" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_purple']}" stroke-width="1"/>
  <text x="630" y="120" font-family="Inter, sans-serif" font-size="12" fill="{COLORS['white']}" opacity="0.6">NEW FINDINGS</text>
  <text x="630" y="150" font-family="Inter, sans-serif" font-size="36" font-weight="700" fill="{COLORS['accent_purple']}">47</text>
  <text x="630" y="175" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['accent_gold']}">Awaiting validation</text>

  <rect x="900" y="90" width="270" height="120" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_gold']}" stroke-width="1"/>
  <text x="920" y="120" font-family="Inter, sans-serif" font-size="12" fill="{COLORS['white']}" opacity="0.6">REVENUE (24h)</text>
  <text x="920" y="150" font-family="Inter, sans-serif" font-size="36" font-weight="700" fill="{COLORS['accent_gold']}">$12.4K</text>
  <text x="920" y="175" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['accent_emerald']}">+15.3%</text>

  <!-- Agent Fleet Panel -->
  <rect x="30" y="240" width="560" height="280" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_blue']}" stroke-width="1"/>
  <text x="50" y="270" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="{COLORS['accent_blue']}">Agent Fleet</text>

  <!-- Agent Cards -->
  <rect x="50" y="290" width="240" height="80" rx="6" fill="{COLORS['primary_main']}" opacity="0.6"/>
  <text x="70" y="315" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{COLORS['white']}">Security Scout</text>
  <text x="70" y="335" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.6">Target: hackerone.com</text>
  <text x="70" y="355" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Working</text>

  <rect x="310" y="290" width="240" height="80" rx="6" fill="{COLORS['primary_main']}" opacity="0.6"/>
  <text x="330" y="315" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{COLORS['white']}">Code Generator</text>
  <text x="330" y="335" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.6">Task: Fix validation</text>
  <text x="330" y="355" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_cyan']}">● Processing</text>

  <rect x="50" y="390" width="240" height="80" rx="6" fill="{COLORS['primary_main']}" opacity="0.6"/>
  <text x="70" y="415" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{COLORS['white']}">Validator</text>
  <text x="70" y="435" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.6">Finding: SQL Injection</text>
  <text x="70" y="455" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_gold']}">● Reviewing</text>

  <rect x="310" y="390" width="240" height="80" rx="6" fill="{COLORS['primary_main']}" opacity="0.6"/>
  <text x="330" y="415" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{COLORS['white']}">Researcher</text>
  <text x="330" y="435" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.6">Target: bugcrowd.com</text>
  <text x="330" y="455" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Scanning</text>

  <!-- Opportunities Panel -->
  <rect x="610" y="240" width="560" height="280" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_purple']}" stroke-width="1"/>
  <text x="630" y="270" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="{COLORS['accent_purple']}">Opportunity Radar</text>

  <!-- Opportunity Cards -->
  <rect x="630" y="290" width="520" height="60" rx="6" fill="{COLORS['primary_main']}" opacity="0.6"/>
  <text x="650" y="315" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{COLORS['white']}">HackerOne — Target Analysis</text>
  <text x="650" y="335" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.6">Confidence: 87% • Est. Reward: $5,000-$15,000</text>
  <text x="1100" y="320" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">HIGH</text>

  <rect x="630" y="360" width="520" height="60" rx="6" fill="{COLORS['primary_main']}" opacity="0.6"/>
  <text x="650" y="385" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{COLORS['white']}">Intigriti — Program Discovery</text>
  <text x="650" y="405" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.6">Confidence: 72% • Est. Reward: $2,000-$8,000</text>
  <text x="1100" y="390" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_cyan']}">MEDIUM</text>

  <rect x="630" y="430" width="520" height="60" rx="6" fill="{COLORS['primary_main']}" opacity="0.6"/>
  <text x="650" y="455" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{COLORS['white']}">Bugcrowd — Critical Vuln</text>
  <text x="650" y="475" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.6">Confidence: 94% • Est. Reward: $10,000-$25,000</text>
  <text x="1100" y="460" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_gold']}">CRITICAL</text>

  <!-- System Health Panel -->
  <rect x="30" y="540" width="560" height="220" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_emerald']}" stroke-width="1"/>
  <text x="50" y="570" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="{COLORS['accent_emerald']}">System Health</text>

  <!-- Health Metrics -->
  <text x="50" y="600" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">● Uptime: 99.7%</text>
  <text x="50" y="620" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">● Memory: 4.2GB / 16GB</text>
  <text x="50" y="640" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">● CPU: 23%</text>
  <text x="50" y="660" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">● Network: Stable</text>
  <text x="50" y="680" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">● Database: Connected</text>
  <text x="50" y="700" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">● Scheduler: Active</text>
  <text x="50" y="720" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">● EventBus: Running</text>
  <text x="50" y="740" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['accent_emerald']}">● All Systems: OK</text>

  <!-- Activity Timeline Panel -->
  <rect x="610" y="540" width="560" height="220" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_cyan']}" stroke-width="1"/>
  <text x="630" y="570" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="{COLORS['accent_cyan']}">Activity Timeline</text>

  <!-- Timeline Items -->
  <text x="630" y="600" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">14:32 • New finding: XSS in target #234</text>
  <text x="630" y="620" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">14:28 • Agent Security Scout completed scan</text>
  <text x="630" y="640" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">14:25 • Workflow Security Cycle advanced</text>
  <text x="630" y="660" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">14:20 • New opportunity detected: HackerOne</text>
  <text x="630" y="680" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">14:15 • Knowledge capture: Learned SQL pattern</text>
  <text x="630" y="700" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">14:10 • Revenue: $500 payout received</text>
  <text x="630" y="720" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">14:05 • System health check passed</text>
  <text x="630" y="740" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['accent_emerald']}">● 47 events in last hour</text>
</svg>'''

    output_path = SCREENSHOTS_DIR / "mission_control_screenshot.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)


if __name__ == "__main__":
    print("Generating Mission Control screenshot...")

    mission_control = generate_mission_control_screenshot()
    print(f"✓ Mission Control screenshot: {mission_control}")
    print("  Represents: Dashboard, metrics, agents, opportunities, system health")
    print("  Style: Premium dashboard")
    print("  Inspiration: Linear (modern), Apple (elegance), SpaceX (engineering)")

    print(f"\nMission Control screenshot generated in: {SCREENSHOTS_DIR}")
