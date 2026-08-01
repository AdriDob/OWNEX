"""Generate cinematic hero banner for GitHub README.

Format: GitHub README banner (1200x400)
Elements: Dashboard holográfico, agentes trabajando, datos, terminal, conexiones, inteligencia distribuida
Style: Cinematic, premium, commercial product
Inspiration: Tesla (simplicity), SpaceX (engineering), Linear (modern), Apple (elegance)
"""

from pathlib import Path

BANNERS_DIR = Path("assets/branding/banners")
BANNERS_DIR.mkdir(parents=True, exist_ok=True)

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

def generate_cinematic_hero_banner() -> str:
    """Generate cinematic hero banner for GitHub README.

    Shows: Dashboard holográfico, agentes trabajando, datos, terminal, conexiones, inteligencia distribuida
    """
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" width="1200" height="400">
  <defs>
    <linearGradient id="heroGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['primary_main']};stop-opacity:1" />
      <stop offset="50%" style="stop-color:{COLORS['primary_light']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['accent_blue']};stop-opacity:0.3" />
    </linearGradient>
    <linearGradient id="glowGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:{COLORS['accent_cyan']};stop-opacity:0.8" />
      <stop offset="100%" style="stop-color:{COLORS['accent_blue']};stop-opacity:0.2" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="1200" height="400" fill="url(#heroGrad)"/>

  <!-- Grid lines (subtle, professional) -->
  <g stroke="{COLORS['white']}" stroke-width="0.5" opacity="0.1">
    <line x1="0" y1="100" x2="1200" y2="100"/>
    <line x1="0" y1="200" x2="1200" y2="200"/>
    <line x1="0" y1="300" x2="1200" y2="300"/>
    <line x1="300" y1="0" x2="300" y2="400"/>
    <line x1="600" y1="0" x2="600" y2="400"/>
    <line x1="900" y1="0" x2="900" y2="400"/>
  </g>

  <!-- Left: Terminal Panel -->
  <rect x="50" y="80" width="280" height="240" rx="8" fill="{COLORS['primary_light']}" opacity="0.8" stroke="{COLORS['accent_blue']}" stroke-width="1"/>
  <text x="70" y="110" font-family="JetBrains Mono, monospace" font-size="12" fill="{COLORS['accent_cyan']}">$ ownex --status</text>
  <text x="70" y="135" font-family="JetBrains Mono, monospace" font-size="11" fill="{COLORS['white']}" opacity="0.8">● System: ONLINE</text>
  <text x="70" y="155" font-family="JetBrains Mono, monospace" font-size="11" fill="{COLORS['white']}" opacity="0.8">● Agents: 12 active</text>
  <text x="70" y="175" font-family="JetBrains Mono, monospace" font-size="11" fill="{COLORS['white']}" opacity="0.8">● Workflows: 8 running</text>
  <text x="70" y="195" font-family="JetBrains Mono, monospace" font-size="11" fill="{COLORS['accent_emerald']}" opacity="0.8">● Findings: 47 new</text>
  <text x="70" y="215" font-family="JetBrains Mono, monospace" font-size="11" fill="{COLORS['white']}" opacity="0.8">● Revenue: $12,450</text>
  <text x="70" y="235" font-family="JetBrains Mono, monospace" font-size="11" fill="{COLORS['accent_gold']}" opacity="0.8">● Uptime: 99.7%</text>

  <!-- Center: Holographic Dashboard -->
  <rect x="360" y="50" width="480" height="300" rx="12" fill="url(#glowGrad)" opacity="0.3" stroke="{COLORS['accent_cyan']}" stroke-width="2" filter="url(#glow)"/>

  <!-- Dashboard Elements -->
  <!-- Top: KPI Cards -->
  <rect x="380" y="70" width="100" height="60" rx="4" fill="{COLORS['primary_light']}" opacity="0.9"/>
  <text x="430" y="95" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.6">VULNERABILITIES</text>
  <text x="430" y="115" text-anchor="middle" font-family="Inter, sans-serif" font-size="18" font-weight="700" fill="{COLORS['accent_cyan']}">127</text>

  <rect x="500" y="70" width="100" height="60" rx="4" fill="{COLORS['primary_light']}" opacity="0.9"/>
  <text x="550" y="95" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.6">VALIDATED</text>
  <text x="550" y="115" text-anchor="middle" font-family="Inter, sans-serif" font-size="18" font-weight="700" fill="{COLORS['accent_emerald']}">89</text>

  <rect x="620" y="70" width="100" height="60" rx="4" fill="{COLORS['primary_light']}" opacity="0.9"/>
  <text x="670" y="95" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.6">PAYOUTS</text>
  <text x="670" y="115" text-anchor="middle" font-family="Inter, sans-serif" font-size="18" font-weight="700" fill="{COLORS['accent_gold']}">$84K</text>

  <rect x="740" y="70" width="80" height="60" rx="4" fill="{COLORS['primary_light']}" opacity="0.9"/>
  <text x="780" y="95" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.6">RANK</text>
  <text x="780" y="115" text-anchor="middle" font-family="Inter, sans-serif" font-size="18" font-weight="700" fill="{COLORS['accent_purple']}">#23</text>

  <!-- Middle: Activity Graph -->
  <polyline points="380,200 420,180 460,190 500,160 540,170 580,140 620,150 660,130 700,140 740,120 780,130 820,110"
            fill="none" stroke="{COLORS['accent_cyan']}" stroke-width="2" filter="url(#glow)"/>
  <rect x="380" y="220" width="440" height="60" rx="4" fill="{COLORS['primary_light']}" opacity="0.5"/>
  <text x="600" y="255" text-anchor="middle" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">Activity Timeline — Last 24h</text>

  <!-- Bottom: Agent Fleet -->
  <g transform="translate(380, 300)">
    <circle cx="20" cy="20" r="8" fill="{COLORS['accent_emerald']}" filter="url(#glow)"/>
    <circle cx="60" cy="20" r="8" fill="{COLORS['accent_cyan']}" filter="url(#glow)"/>
    <circle cx="100" cy="20" r="8" fill="{COLORS['accent_blue']}" filter="url(#glow)"/>
    <circle cx="140" cy="20" r="8" fill="{COLORS['accent_purple']}" filter="url(#glow)"/>
    <circle cx="180" cy="20" r="8" fill="{COLORS['accent_gold']}" filter="url(#glow)"/>
    <circle cx="220" cy="20" r="8" fill="{COLORS['accent_emerald']}" filter="url(#glow)"/>
    <circle cx="260" cy="20" r="8" fill="{COLORS['accent_cyan']}" filter="url(#glow)"/>
    <circle cx="300" cy="20" r="8" fill="{COLORS['accent_blue']}" filter="url(#glow)"/>
    <circle cx="340" cy="20" r="8" fill="{COLORS['accent_purple']}" filter="url(#glow)"/>
    <circle cx="380" cy="20" r="8" fill="{COLORS['accent_gold']}" filter="url(#glow)"/>
    <circle cx="420" cy="20" r="8" fill="{COLORS['accent_emerald']}" filter="url(#glow)"/>
  </g>

  <!-- Right: Connection Network -->
  <rect x="870" y="80" width="280" height="240" rx="8" fill="{COLORS['primary_light']}" opacity="0.8" stroke="{COLORS['accent_purple']}" stroke-width="1"/>

  <!-- Network Nodes -->
  <circle cx="950" cy="130" r="15" fill="{COLORS['accent_cyan']}" filter="url(#glow)"/>
  <circle cx="1070" cy="130" r="15" fill="{COLORS['accent_blue']}" filter="url(#glow)"/>
  <circle cx="950" cy="200" r="15" fill="{COLORS['accent_purple']}" filter="url(#glow)"/>
  <circle cx="1070" cy="200" r="15" fill="{COLORS['accent_emerald']}" filter="url(#glow)"/>
  <circle cx="1010" cy="270" r="15" fill="{COLORS['accent_gold']}" filter="url(#glow)"/>

  <!-- Network Connections -->
  <line x1="950" y1="145" x2="1010" y2="270" stroke="{COLORS['white']}" stroke-width="1" opacity="0.3"/>
  <line x1="1070" y1="145" x2="1010" y2="270" stroke="{COLORS['white']}" stroke-width="1" opacity="0.3"/>
  <line x1="950" y1="185" x2="1010" y2="270" stroke="{COLORS['white']}" stroke-width="1" opacity="0.3"/>
  <line x1="1070" y1="185" x2="1010" y2="270" stroke="{COLORS['white']}" stroke-width="1" opacity="0.3"/>
  <line x1="950" y1="130" x2="1070" y2="130" stroke="{COLORS['white']}" stroke-width="1" opacity="0.3"/>
  <line x1="950" y1="200" x2="1070" y2="200" stroke="{COLORS['white']}" stroke-width="1" opacity="0.3"/>

  <!-- Title -->
  <text x="600" y="30" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="36" font-weight="700" fill="{COLORS['white']}" letter-spacing="2">OWNEX ALPHA</text>

  <!-- Subtitle -->
  <text x="600" y="385" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="16" font-weight="400" fill="{COLORS['accent_cyan']}" letter-spacing="3">Autonomous Personal Operating System</text>
</svg>'''

    output_path = BANNERS_DIR / "cinematic_hero_banner.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)


if __name__ == "__main__":
    print("Generating cinematic hero banner...")

    hero_banner = generate_cinematic_hero_banner()
    print(f"✓ Cinematic hero banner: {hero_banner}")
    print("  Format: GitHub README banner (1200x400)")
    print("  Elements: Dashboard holográfico, agentes trabajando, datos, terminal, conexiones")
    print("  Style: Cinematic, premium, commercial product")
    print("  Inspiration: Tesla (simplicity), SpaceX (engineering), Linear (modern), Apple (elegance)")

    print(f"\nBanner generated in: {BANNERS_DIR}")
