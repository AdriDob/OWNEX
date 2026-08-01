"""Rebuild OWNEX ALPHA Logo (Desktop Edition).

Inspired by Tesla (simplicity), Apple (elegance), SpaceX (engineering), Linear (modern),
NVIDIA (precision), PlayStation (impact).

Concept: Desktop Operating System - nucleus, engineering, productivity, development, command center.
Symbol: Geometric precision representing engineering and command center.
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

def generate_alpha_logo_v2() -> str:
    """Generate OWNEX ALPHA logo v2 - Desktop Edition.

    Design: Geometric precision - hexagon with interlocking triangular core.
    Represents: Engineering, precision, command center, stability.
    Inspired by: NVIDIA (hexagon), PlayStation (triangle), Tesla (minimalism).
    """
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="alphaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['primary']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['secondary']};stop-opacity:1" />
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

  <!-- Outer Hexagon - Engineering Precision (NVIDIA-inspired) -->
  <polygon points="256,30 476,136 476,376 256,482 36,376 36,136"
           fill="none" stroke="url(#alphaGrad)" stroke-width="4" filter="url(#subtleGlow)"/>

  <!-- Inner Hexagon - Command Structure -->
  <polygon points="256,60 436,144 436,368 256,452 76,368 76,144"
           fill="url(#alphaGrad)" opacity="0.15"/>

  <!-- Core Triangle - Stability and Force (PlayStation-inspired) -->
  <polygon points="256,120 360,256 256,300"
           fill="{COLORS['primary']}" filter="url(#subtleGlow)"/>

  <!-- Inner Triangle - Engineering Precision -->
  <polygon points="256,160 320,256 256,240"
           fill="{COLORS['secondary']}" opacity="0.8"/>

  <!-- Center Point - The Nucleus -->
  <circle cx="256" cy="200" r="20" fill="{COLORS['accent']}" filter="url(#subtleGlow)"/>

  <!-- OWNEX Text -->
  <text x="256" y="390" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="42" font-weight="700" fill="{COLORS['text']}" letter-spacing="3">OWNEX</text>

  <!-- ALPHA Text -->
  <text x="256" y="435" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="24" font-weight="600" fill="{COLORS['primary']}" letter-spacing="6">ALPHA</text>

  <!-- Tagline -->
  <text x="256" y="470" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="14" font-weight="400" fill="{COLORS['text_secondary']}" letter-spacing="1">Desktop Command Center</text>
</svg>'''

    output_path = LOGOS_DIR / "alpha_logo_v2.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)


if __name__ == "__main__":
    print("Rebuilding OWNEX ALPHA logo v2...")
    alpha_logo = generate_alpha_logo_v2()
    print(f"✓ ALPHA logo v2: {alpha_logo}")
    print("  Design: Geometric precision (hexagon + triangular core)")
    print("  Represents: Engineering, precision, command center, stability")
    print("  Inspired by: NVIDIA (hexagon), PlayStation (triangle), Tesla (minimalism)")
    print("  No: brains, robots, eyes, circuits, holograms, generic AI symbols")
