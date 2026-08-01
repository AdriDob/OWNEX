"""Generate ALPHA and OMEGA specific logos.

ALPHA (Desktop): Command center theme - Professional, robust, enterprise-grade
OMEGA (Mobile): Mobile companion theme - Modern, sleek, mobile-first

Both share OWNEX identity but with distinct visual characteristics.
"""

from pathlib import Path

LOGOS_DIR = Path("assets/branding/logos")
LOGOS_DIR.mkdir(parents=True, exist_ok=True)

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

def generate_alpha_logo() -> str:
    """Generate OWNEX ALPHA logo (Desktop edition).

    Concept: "El centro de comando personal"
    Represents: Stability, creation, development, engineering, productivity, control
    Design: Strong, geometric, authoritative
    """
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
  <defs>
    <linearGradient id="alphaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['accent_blue']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['accent_cyan']};stop-opacity:1" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Background: Deep Space Black -->
  <rect width="400" height="400" fill="{COLORS['primary_main']}"/>

  <!-- Outer Hexagon - Engineering/Stability (stronger lines) -->
  <polygon points="200,25 355,110 355,290 200,375 45,290 45,110"
           fill="none" stroke="url(#alphaGrad)" stroke-width="4" filter="url(#glow)"/>

  <!-- Inner Hexagon (more filled for stability) -->
  <polygon points="200,55 325,135 325,265 200,345 75,265 75,135"
           fill="url(#alphaGrad)" opacity="0.25"/>

  <!-- Central Command Structure - Interconnected Squares (Command Center) -->
  <!-- Top square -->
  <rect x="180" y="100" width="40" height="40" fill="{COLORS['accent_cyan']}" filter="url(#glow)"/>

  <!-- Bottom square -->
  <rect x="180" y="260" width="40" height="40" fill="{COLORS['accent_blue']}" filter="url(#glow)"/>

  <!-- Left square -->
  <rect x="100" y="180" width="40" height="40" fill="{COLORS['accent_purple']}" filter="url(#glow)"/>

  <!-- Right square -->
  <rect x="260" y="180" width="40" height="40" fill="{COLORS['accent_emerald']}" filter="url(#glow)"/>

  <!-- Center Command Point -->
  <circle cx="200" cy="200" r="10" fill="{COLORS['accent_gold']}" filter="url(#glow)"/>

  <!-- Connection lines (command network) -->
  <line x1="200" y1="140" x2="200" y2="180" stroke="{COLORS['white']}" stroke-width="2" opacity="0.5"/>
  <line x1="200" y1="220" x2="200" y2="260" stroke="{COLORS['white']}" stroke-width="2" opacity="0.5"/>
  <line x1="140" y1="200" x2="180" y2="200" stroke="{COLORS['white']}" stroke-width="2" opacity="0.5"/>
  <line x1="220" y1="200" x2="260" y2="200" stroke="{COLORS['white']}" stroke-width="2" opacity="0.5"/>

  <!-- OWNEX ALPHA Text -->
  <text x="200" y="320" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="32" font-weight="700" fill="{COLORS['white']}" letter-spacing="4">OWNEX</text>

  <text x="200" y="355" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="20" font-weight="600" fill="{COLORS['accent_cyan']}" letter-spacing="6">ALPHA</text>

  <!-- Tagline -->
  <text x="200" y="380" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="12" font-weight="400" fill="{COLORS['white']}" opacity="0.6" letter-spacing="2">Desktop Command Center</text>
</svg>'''

    output_path = LOGOS_DIR / "ownex_alpha_logo.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)

def generate_omega_logo() -> str:
    """Generate OWNEX OMEGA logo (Mobile edition).

    Concept: "Tu inteligencia personal siempre contigo"
    Represents: Mobility, connection, evolution, autonomy
    Design: Modern, sleek, mobile-first
    """
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
  <defs>
    <linearGradient id="omegaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['accent_purple']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['accent_blue']};stop-opacity:1" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Background: Deep Space Black -->
  <rect width="400" height="400" fill="{COLORS['primary_main']}"/>

  <!-- Outer Circle - Mobility/Connection (more dynamic) -->
  <circle cx="200" cy="200" r="160"
          fill="none" stroke="url(#omegaGrad)" stroke-width="3" filter="url(#glow)"/>

  <!-- Inner Circle (more transparent for lightness) -->
  <circle cx="200" cy="200" r="120"
          fill="url(#omegaGrad)" opacity="0.15"/>

  <!-- Orbiting Elements - Evolution/Mobility -->
  <!-- Orbit path -->
  <circle cx="200" cy="200" r="90"
          fill="none" stroke="{COLORS['white']}" stroke-width="1" opacity="0.3"/>

  <!-- Orbiting nodes (representing connection points) -->
  <circle cx="200" cy="110" r="12" fill="{COLORS['accent_cyan']}" filter="url(#glow)"/>
  <circle cx="290" cy="200" r="12" fill="{COLORS['accent_emerald']}" filter="url(#glow)"/>
  <circle cx="200" cy="290" r="12" fill="{COLORS['accent_blue']}" filter="url(#glow)"/>
  <circle cx="110" cy="200" r="12" fill="{COLORS['accent_purple']}" filter="url(#glow)"/>

  <!-- Central Core - Intelligence -->
  <circle cx="200" cy="200" r="25" fill="{COLORS['accent_gold']}" filter="url(#glow)"/>

  <!-- Connection rays (representing mobility) -->
  <line x1="200" y1="122" x2="200" y2="175" stroke="{COLORS['white']}" stroke-width="1" opacity="0.4"/>
  <line x1="278" y1="200" x2="225" y2="200" stroke="{COLORS['white']}" stroke-width="1" opacity="0.4"/>
  <line x1="200" y1="278" x2="200" y2="225" stroke="{COLORS['white']}" stroke-width="1" opacity="0.4"/>
  <line x1="122" y1="200" x2="175" y2="200" stroke="{COLORS['white']}" stroke-width="1" opacity="0.4"/>

  <!-- OWNEX OMEGA Text -->
  <text x="200" y="320" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="32" font-weight="700" fill="{COLORS['white']}" letter-spacing="4">OWNEX</text>

  <text x="200" y="355" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="20" font-weight="600" fill="{COLORS['accent_purple']}" letter-spacing="6">OMEGA</text>

  <!-- Tagline -->
  <text x="200" y="380" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="12" font-weight="400" fill="{COLORS['white']}" opacity="0.6" letter-spacing="2">Mobile Companion</text>
</svg>'''

    output_path = LOGOS_DIR / "ownex_omega_logo.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)


if __name__ == "__main__":
    print("Generating ALPHA and OMEGA logos...")

    alpha_logo = generate_alpha_logo()
    print(f"✓ ALPHA logo: {alpha_logo}")
    print("  Concept: Command center theme")
    print("  Represents: Stability, creation, development, engineering, productivity, control")

    omega_logo = generate_omega_logo()
    print(f"✓ OMEGA logo: {omega_logo}")
    print("  Concept: Mobile companion theme")
    print("  Represents: Mobility, connection, evolution, autonomy")

    print(f"\nAll logos generated in: {LOGOS_DIR}")
