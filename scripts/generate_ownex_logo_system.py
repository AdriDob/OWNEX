"""Generate OWNEX Main Logo System.

Creates a premium logo system with OWNEX's own identity:
- Main logo
- Icon (reduced)
- App icon
- Favicon
- Monogram

Inspired by Tesla (simplicity), SpaceX (engineering), Linear (modern),
Apple (elegance) but with OWNEX's own geometric identity.

Design Philosophy:
- Geometric interconnected nodes (represents distributed intelligence)
- Hexagonal structure (represents engineering and stability)
- No robots, no circuits, no cliché AI symbols
- Scalable from 32px to giant screens
"""

from pathlib import Path

LOGOS_DIR = Path("assets/branding/logos")
LOGOS_DIR.mkdir(parents=True, exist_ok=True)

# Design System Colors (from design_system.json)
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

def generate_main_logo() -> str:
    """Generate main OWNEX logo.

    Symbol: Hexagonal structure with interconnected triangular nodes
    Represents: Distributed intelligence, engineering, stability, evolution
    """
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
  <defs>
    <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
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

  <!-- Outer Hexagon - Engineering/Stability -->
  <polygon points="200,30 350,115 350,285 200,370 50,285 50,115"
           fill="none" stroke="url(#logoGrad)" stroke-width="3" filter="url(#glow)"/>

  <!-- Inner Hexagon -->
  <polygon points="200,60 320,140 320,260 200,340 80,260 80,140"
           fill="url(#logoGrad)" opacity="0.15"/>

  <!-- Central Core - Interconnected Triangles (Intelligence/Evolution) -->
  <!-- Top triangle -->
  <polygon points="200,120 230,160 170,200 230,160"
           fill="{COLORS['accent_cyan']}" filter="url(#glow)"/>

  <!-- Bottom triangle -->
  <polygon points="200,280 170,240 230,200 170,240"
           fill="{COLORS['accent_blue']}" filter="url(#glow)"/>

  <!-- Left triangle -->
  <polygon points="120,200 160,170 160,230 120,240"
           fill="{COLORS['accent_purple']}" filter="url-gl ow)"/>

  <!-- Right triangle -->
  <polygon points="280,200 240,170 240,230 280,240"
           fill="{COLORS['accent_emerald']}" filter="url(#glow)"/>

  <!-- Center Point - The Nexus -->
  <circle cx="200" cy="200" r="8" fill="{COLORS['accent_gold']}" filter="url(#glow)"/>

  <!-- OWNEX Text -->
  <text x="200" y="320" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="36" font-weight="700" fill="{COLORS['white']}" letter-spacing="4">OWNEX</text>

  <!-- Tagline -->
  <text x="200" y="350" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="14" font-weight="400" fill="{COLORS['accent_cyan']}" letter-spacing="2">Autonomous Intelligence</text>
</svg>'''

    output_path = LOGOS_DIR / "ownex_main_logo.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)

def generate_icon() -> str:
    """Generate reduced icon.

    Symbol: Simplified interconnected nodes (no text)
    """
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="iconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['accent_blue']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['accent_cyan']};stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Outer Hexagon -->
  <polygon points="32,5 57,20 57,44 32,59 7,44 7,20"
           fill="none" stroke="url(#iconGrad)" stroke-width="2"/>

  <!-- Inner Hexagon -->
  <polygon points="32,10 52,22 52,42 32,54 12,42 12,22"
           fill="url(#iconGrad)" opacity="0.2"/>

  <!-- Interconnected triangles -->
  <polygon points="32,18 40,26 36,32 40,26" fill="{COLORS['accent_cyan']}"/>
  <polygon points="32,46 24,40 40,32 24,40" fill="{COLORS['accent_blue']}"/>
  <polygon points="12,32 20,26 20,38 12,42" fill="{COLORS['accent_purple']}"/>
  <polygon points="52,32 44,38 44,38 52,42" fill="{COLORS['accent_emerald']}"/>

  <!-- Center point -->
  <circle cx="32" cy="32" r="3" fill="{COLORS['accent_gold']}"/>
</svg>'''

    output_path = LOGOS_DIR / "ownex_icon.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)

def generate_app_icon() -> str:
    """Generate app icon (square with rounded corners).

    Symbol: Icon on dark background with subtle gradient
    """
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="appGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['primary_main']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['primary_light']};stop-opacity:1" />
    </linearGradient>
    <linearGradient id="iconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['accent_blue']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['accent_cyan']};stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Background with rounded corners -->
  <rect width="512" height="512" rx="100" fill="url(#appGrad)"/>

  <!-- Icon centered -->
  <g transform="translate(256, 256)">
    <!-- Outer Hexagon -->
    <polygon points="0,-120 104,-60 104,60 0,120 -104,60 -104,-60"
             fill="none" stroke="url(#iconGrad)" stroke-width="4"/>

    <!-- Inner Hexagon -->
    <polygon points="0,-80 69,-40 69,40 0,80 -69,40 -69,-40"
             fill="url(#iconGrad)" opacity="0.2"/>

    <!-- Interconnected triangles -->
    <polygon points="0,-48 26,-24 44,0 26,24" fill="{COLORS['accent_cyan']}"/>
    <polygon points="0,48 -26,24 -44,0 -26,-24" fill="{COLORS['accent_blue']}"/>
    <polygon points="-72,0 -26,-24 -26,24 -72,48" fill="{COLORS['accent_purple']}"/>
    <polygon points="72,0 26,-24 26,24 72,48" fill="{COLORS['accent_emerald']}"/>

    <!-- Center point -->
    <circle cx="0" cy="0" r="8" fill="{COLORS['accent_gold']}"/>
  </g>
</svg>'''

    output_path = LOGOS_DIR / "ownex_app_icon.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)

def generate_favicon() -> str:
    """Generate favicon (32x32).

    Symbol: Simplified interconnected nodes only
    """
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <defs>
    <linearGradient id="favGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['accent_blue']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['accent_cyan']};stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Outer Hexagon -->
  <polygon points="16,2 28,8 28,24 16,30 4,24 4,8"
           fill="url(#favGrad)" opacity="0.3"/>

  <!-- Interconnected triangles (simplified) -->
  <polygon points="16,8 20,12 22,16 20,12" fill="{COLORS['accent_cyan']}"/>
  <polygon points="16,24 12,20 20,16 12,20" fill="{COLORS['accent_blue']}"/>
  <polygon points="6,16 10,12 10,20 6,24" fill="{COLORS['accent_purple']}"/>
  <polygon points="26,16 22,12 22,12 26,24" fill="{COLORS['accent_emerald']}"/>

  <!-- Center point -->
  <circle cx="16" cy="16" r="2" fill="{COLORS['accent_gold']}"/>
</svg>'''

    output_path = LOGOS_DIR / "ownex_favicon.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)

def generate_monogram() -> str:
    """Generate monogram (single letter 'O').

    Symbol: Stylized 'O' with geometric detail
    """
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="monoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['accent_blue']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['accent_cyan']};stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Outer O -->
  <circle cx="32" cy="32" r="28"
          fill="none" stroke="url(#monoGrad)" stroke-width="3"/>

  <!-- Inner core -->
  <circle cx="32" cy="32" r="18"
          fill="url(#monoGrad)" opacity="0.3"/>

  <!-- Center point -->
  <circle cx="32" cy="32" r="4" fill="{COLORS['accent_gold']}"/>
</svg>'''

    output_path = LOGOS_DIR / "ownex_monogram.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)


if __name__ == "__main__":
    print("Generating OWNEX Logo System...")

    main_logo = generate_main_logo()
    print(f"✓ Main logo: {main_logo}")

    icon = generate_icon()
    print(f"✓ Icon: {icon}")

    app_icon = generate_app_icon()
    print(f"✓ App icon: {app_icon}")

    favicon = generate_favicon()
    print(f"✓ Favicon: {favicon}")

    monogram = generate_monogram()
    print(f"✓ Monogram: {monogram}")

    print(f"\nAll logos generated in: {LOGOS_DIR}")
    print("\nSymbol: Hexagonal structure with interconnected triangular nodes")
    print("Represents: Distributed intelligence, engineering, stability, evolution")
    print("Inspired by: Tesla (simplicity), SpaceX (engineering), Linear (modern), Apple (elegance)")
