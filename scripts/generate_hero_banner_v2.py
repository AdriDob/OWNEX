"""Generate premium hero banner for README.

Shows: dashboard, agents, intelligence, terminal, workflows.
Inspired by Tesla/Apple/SpaceX/Linear/NVIDIA/PlayStation promotional banners.
Size: 1600x400 (GitHub README standard).
"""

from pathlib import Path

BANNERS_DIR = Path("assets/branding/banners")

# Color System
COLORS = {
    "primary": "#00F0FF",  # Cyber Cyan
    "secondary": "#0044FF",  # Deep Blue
    "accent": "#00FF88",  # Emerald
    "background": "#0A0A0A",  # Space Black
    "neutral": "#1A1A1A",  # Dark Gray
    "text": "#FFFFFF",  # Pure White
    "text_secondary": "#E0E0E0"  # Light Gray
}

def generate_hero_banner_v2() -> str:
    """Generate premium hero banner (1600x400)."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 400" width="1600" height="400">
  <defs>
    <linearGradient id="heroGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['background']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['neutral']};stop-opacity:1" />
    </linearGradient>
    <linearGradient id="textGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:{COLORS['primary']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['secondary']};stop-opacity:1" />
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
  <rect width="1600" height="400" fill="url(#heroGrad)"/>

  <!-- Left: Terminal Panel -->
  <rect x="50" y="50" width="350" height="300" rx="8" fill="{COLORS['neutral']}" stroke="{COLORS['primary']}" stroke-width="1"/>
  <text x="70" y="80" font-family="JetBrains Mono, monospace" font-size="12" fill="{COLORS['primary']}">OWNEX-ALPHA:~/system</text>
  <text x="70" y="100" font-family="JetBrains Mono, monospace" font-size="10" fill="{COLORS['text']}" opacity="0.7">$ ownex init</text>
  <text x="70" y="120" font-family="JetBrains Mono, monospace" font-size="10" fill="{COLORS['accent']}">✓ Core initialized</text>
  <text x="70" y="140" font-family="JetBrains Mono, monospace" font-size="10" fill="{COLORS['accent']}">✓ Agents connected</text>
  <text x="70" y="160" font-family="JetBrains Mono, monospace" font-size="10" fill="{COLORS['accent']}">✓ Mission Control ready</text>
  <text x="70" y="180" font-family="JetBrains Mono, monospace" font-size="10" fill="{COLORS['text']}" opacity="0.7">$ _</text>

  <!-- Center: Dashboard Preview -->
  <rect x="420" y="50" width="760" height="300" rx="8" fill="{COLORS['neutral']}" stroke="{COLORS['secondary']}" stroke-width="1"/>
  <text x="440" y="80" font-family="Inter, system-ui, sans-serif" font-size="14" font-weight="600" fill="{COLORS['secondary']}">Mission Control</text>

  <!-- KPI Cards -->
  <rect x="440" y="100" width="160" height="60" rx="4" fill="{COLORS['background']}" opacity="0.5"/>
  <text x="450" y="120" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['text']}" opacity="0.6">Active Agents</text>
  <text x="450" y="140" font-family="Inter, system-ui, sans-serif" font-size="20" font-weight="700" fill="{COLORS['primary']}">12</text>

  <rect x="620" y="100" width="160" height="60" rx="4" fill="{COLORS['background']}" opacity="0.5"/>
  <text x="630" y="120" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['text']}" opacity="0.6">Workflows</text>
  <text x="630" y="140" font-family="Inter, system-ui, sans-serif" font-size="20" font-weight="700" fill="{COLORS['secondary']}">8</text>

  <rect x="800" y="100" width="160" height="60" rx="4" fill="{COLORS['background']}" opacity="0.5"/>
  <text x="810" y="120" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['text']}" opacity="0.6">Revenue (24h)</text>
  <text x="810" y="140" font-family="Inter, system-ui, sans-serif" font-size="20" font-weight="700" fill="{COLORS['accent']}">$12.4K</text>

  <rect x="980" y="100" width="160" height="60" rx="4" fill="{COLORS['background']}" opacity="0.5"/>
  <text x="990" y="120" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['text']}" opacity="0.6">Uptime</text>
  <text x="990" y="140" font-family="Inter, system-ui, sans-serif" font-size="20" font-weight="700" fill="{COLORS['primary']}">99.7%</text>

  <!-- Agent Fleet Visualization -->
  <text x="440" y="180" font-family="Inter, system-ui, sans-serif" font-size="12" font-weight="600" fill="{COLORS['text']}" opacity="0.7">Agent Fleet</text>
  <rect x="440" y="200" width="200" height="40" rx="4" fill="{COLORS['background']}" opacity="0.3"/>
  <text x="450" y="225" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['accent']}">● Security Scout</text>
  <rect x="660" y="200" width="200" height="40" rx="4" fill="{COLORS['background']}" opacity="0.3"/>
  <text x="670" y="225" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['primary']}">● Code Generator</text>
  <rect x="880" y="200" width="200" height="40" rx="4" fill="{COLORS['background']}" opacity="0.3"/>
  <text x="890" y="225" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['secondary']}">● Validator</text>

  <!-- Workflows Visualization -->
  <text x="440" y="260" font-family="Inter, system-ui, sans-serif" font-size="12" font-weight="600" fill="{COLORS['text']}" opacity="0.7">Active Workflows</text>
  <rect x="440" y="280" width="140" height="30" rx="4" fill="{COLORS['primary']}" opacity="0.2"/>
  <text x="450" y="300" font-family="Inter, system-ui, sans-serif" font-size="9" fill="{COLORS['primary']}">Security Cycle</text>
  <rect x="600" y="280" width="140" height="30" rx="4" fill="{COLORS['secondary']}" opacity="0.2"/>
  <text x="610" y="300" font-family="Inter, system-ui, sans-serif" font-size="9" fill="{COLORS['secondary']}">Forge Cycle</text>
  <rect x="760" y="280" width="140" height="30" rx="4" fill="{COLORS['accent']}" opacity="0.2"/>
  <text x="770" y="300" font-family="Inter, system-ui, sans-serif" font-size="9" fill="{COLORS['accent']}">Pulse Cycle</text>

  <!-- Right: Intelligence Core -->
  <rect x="1200" y="50" width="350" height="300" rx="8" fill="{COLORS['neutral']}" stroke="{COLORS['accent']}" stroke-width="1"/>
  <text x="1220" y="80" font-family="Inter, system-ui, sans-serif" font-size="14" font-weight="600" fill="{COLORS['accent']}">Intelligence Core</text>

  <!-- Intelligence Visualization -->
  <circle cx="1375" cy="180" r="60" fill="none" stroke="{COLORS['primary']}" stroke-width="2"/>
  <circle cx="1375" cy="180" r="40" fill="{COLORS['primary']}" opacity="0.2"/>
  <circle cx="1375" cy="180" r="20" fill="{COLORS['accent']}" filter="url(#glow)"/>

  <!-- Memory Nodes -->
  <circle cx="1320" cy="180" r="12" fill="{COLORS['secondary']}" filter="url(#glow)"/>
  <circle cx="1430" cy="180" r="12" fill="{COLORS['secondary']}" filter="url(#glow)"/>
  <circle cx="1375" cy="130" r="12" fill="{COLORS['primary']}" filter="url(#glow)"/>
  <circle cx="1375" cy="230" r="12" fill="{COLORS['primary']}" filter="url(#glow)"/>

  <!-- Connection Lines -->
  <line x1="1332" y1="180" x2="1355" y2="180" stroke="{COLORS['text']}" stroke-width="1" opacity="0.4"/>
  <line x1="1418" y1="180" x2="1395" y2="180" stroke="{COLORS['text']}" stroke-width="1" opacity="0.4"/>
  <line x1="1375" y1="142" x2="1375" y2="160" stroke="{COLORS['text']}" stroke-width="1" opacity="0.4"/>
  <line x1="1375" y1="218" x2="1375" y2="200" stroke="{COLORS['text']}" stroke-width="1" opacity="0.4"/>

  <!-- Metrics -->
  <text x="1220" y="270" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['text']}" opacity="0.7">Memory: 4.2GB / 16GB</text>
  <text x="1220" y="290" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['text']}" opacity="0.7">CPU: 23%</text>
  <text x="1220" y="310" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['accent']}">Status: Online</text>

  <!-- Overlay Text -->
  <text x="800" y="370" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="32" font-weight="700" fill="url(#textGrad)" letter-spacing="4">OWNEX ALPHA</text>
  <text x="800" y="390" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="14" fill="{COLORS['text']}" opacity="0.7" letter-spacing="2">Autonomous Personal Operating System</text>
</svg>'''

    output_path = BANNERS_DIR / "hero_banner_v2.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)


if __name__ == "__main__":
    print("Generating premium hero banner v2...")
    hero_banner = generate_hero_banner_v2()
    print(f"✓ Hero banner v2: {hero_banner}")
    print("  Size: 1600x400 (GitHub README standard)")
    print("  Shows: Terminal, Dashboard, KPI Cards, Agent Fleet, Workflows, Intelligence Core")
    print("  Inspired by: Tesla/Apple/SpaceX/Linear/NVIDIA/PlayStation promotional banners")
