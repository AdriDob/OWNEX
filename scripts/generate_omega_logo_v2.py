"""Rebuild OWNEX OMEGA Logo (Mobile Edition).

Inspired by Tesla (simplicity), Apple (elegance), SpaceX (engineering), Linear (modern),
NVIDIA (precision), PlayStation (impact).

Concept: Android + Wear OS Companion - mobility, connection, personal intelligence, system extension.
Symbol: Circular/dynamic pattern representing mobility and connection.
No: brains, robots, eyes, circuits, holograms, generic AI symbols.
"""

from pathlib import Path

LOGOS_DIR = Path("assets/branding/logos")

# Color System (from BRAND_IDENTITY_V2.json)
COLORS = {
    "primary": "#00F0FF",  # Cyber Cyan
    "secondary": "#0044FF",  # Deep Blue
    "accent": "#00FF88",  # Emerald
    "background": "#0A0A0A",  # Space Black
    "neutral": "#1A1A1A",  # Dark Gray
    "text": "#FFFFFF",  # Pure White
    "text_secondary": "#E0E0E0"  # Light Gray
}

def generate_omega_logo_v2() -> str:
    """Generate OWNEX OMEGA logo v2 - Mobile Edition.

    Design: Circular/dynamic pattern - orbiting nodes representing mobility and connection.
    Represents: Mobility, connection, personal intelligence, system extension.
    Inspired by: Apple (circle), SpaceX (orbits), Tesla (minimalism).
    """
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="omegaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['secondary']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['primary']};stop-opacity:1" />
    </linearGradient>
    <filter id="subtleGlow">
      <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Background: Space Black -->
  <rect width="512" height="512" fill="{COLORS['background']}"/>

  <!-- Outer Circle - Mobility (Apple-inspired) -->
  <circle cx="256" cy="256" r="200"
          fill="none" stroke="url(#omegaGrad)" stroke-width="4" filter="url(#subtleGlow)"/>

  <!-- Inner Circle - Connection -->
  <circle cx="256" cy="256" r="150"
          fill="url(#omegaGrad)" opacity="0.15"/>

  <!-- Orbit Path - Connection (SpaceX-inspired) -->
  <circle cx="256" cy="256" r="110"
          fill="none" stroke="{COLORS['primary']}" stroke-width="1" opacity="0.5"/>

  <!-- Orbiting Nodes - Connection Points -->
  <!-- Top node -->
  <circle cx="256" cy="146" r="18" fill="{COLORS['primary']}" filter="url(#subtleGlow)"/>
  <!-- Right node -->
  <circle cx="366" cy="256" r="18" fill="{COLORS['accent']}" filter="url(#subtleGlow)"/>
  <!-- Bottom node -->
  <circle cx="256" cy="366" r="18" fill="{COLORS['secondary']}" filter="url(#subtleGlow)"/>
  <!-- Left node -->
  <circle cx="146" cy="256" r="18" fill="{COLORS['accent']}" filter="url(#subtleGlow)"/>

  <!-- Center Intelligence Core -->
  <circle cx="256" cy="256" r="35" fill="{COLORS['primary']}" filter="url(#subtleGlow)"/>

  <!-- Inner Core - Intelligence -->
  <circle cx="256" cy="256" r="20" fill="{COLORS['secondary']}" opacity="0.8"/>

  <!-- OWNEX Text -->
  <text x="256" y="390" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="42" font-weight="700" fill="{COLORS['text']}" letter-spacing="3">OWNEX</text>

  <!-- OMEGA Text -->
  <text x="256" y="435" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="24" font-weight="600" fill="{COLORS['secondary']}" letter-spacing="6">OMEGA</text>

  <!-- Tagline -->
  <text x="256" y="470" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="14" font-weight="400" fill="{COLORS['text_secondary']}" letter-spacing="1">Mobile Companion</text>
</svg>'''

    output_path = LOGOS_DIR / "omega_logo_v2.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)


if __name__ == "__main__":
    print("Rebuilding OWNEX OMEGA logo v2...")
    omega_logo = generate_omega_logo_v2()
    print(f"✓ OMEGA logo v2: {omega_logo}")
    print("  Design: Circular/dynamic pattern (orbiting nodes)")
    print("  Represents: Mobility, connection, personal intelligence, system extension")
    print("  Inspired by: Apple (circle), SpaceX (orbits), Tesla (minimalism)")
    print("  No: brains, robots, eyes, circuits, holograms, generic AI symbols")
