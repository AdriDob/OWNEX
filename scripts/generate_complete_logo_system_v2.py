"""Generate complete OWNEX logo system v2.

Creates: main logo, app icon, favicon, monochrome, transparent, UI versions.
All logos follow Tesla/Apple/SpaceX/Linear/NVIDIA/PlayStation standards.
"""

from pathlib import Path

LOGOS_DIR = Path("assets/branding/logos")

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

def generate_main_logo_v2() -> str:
    """Generate main OWNEX logo (512x512)."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="mainGrad" x1="0%" y1="0%" x2="100%" y2="100%">
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

  <rect width="512" height="512" fill="{COLORS['background']}"/>

  <!-- Main symbol: Interlocking geometric pattern -->
  <polygon points="256,30 476,136 476,376 256,482 36,376 36,136"
           fill="none" stroke="url(#mainGrad)" stroke-width="3" filter="url(#glow)"/>
  <polygon points="256,60 436,144 436,368 256,452 76,368 76,144"
           fill="url(#mainGrad)" opacity="0.2"/>
  <polygon points="256,100 356,256 256,300"
           fill="{COLORS['primary']}" filter="url(#glow)"/>
  <polygon points="256,140 320,256 256,260"
           fill="{COLORS['secondary']}" opacity="0.9"/>
  <circle cx="256" cy="220" r="18" fill="{COLORS['accent']}" filter="url(#glow)"/>

  <text x="256" y="400" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="48" font-weight="700" fill="{COLORS['text']}" letter-spacing="4">OWNEX</text>
  <text x="256" y="445" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="16" font-weight="400" fill="{COLORS['primary']}" letter-spacing="2">Autonomous Intelligence</text>
</svg>'''

    output_path = LOGOS_DIR / "ownex_main_logo_v2.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)
    return str(output_path)

def generate_app_icon_v2() -> str:
    """Generate app icon (512x512)."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="appGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['background']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['neutral']};stop-opacity:1" />
    </linearGradient>
    <linearGradient id="symbolGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['primary']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['secondary']};stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Background with rounded corners -->
  <rect width="512" height="512" rx="100" fill="url(#appGrad)"/>

  <!-- Symbol centered -->
  <g transform="translate(256, 256)">
    <polygon points="0,-150 260,-75 260,75 0,150 -260,75 -260,-75"
             fill="none" stroke="url(#symbolGrad)" stroke-width="4"/>
    <polygon points="0,-110 210,-55 210,55 0,110 -210,55 -210,-55"
             fill="url(#symbolGrad)" opacity="0.3"/>
    <polygon points="0,-50 140,0 0,50"
             fill="{COLORS['primary']}"/>
    <polygon points="0,-20 110,0 0,20"
             fill="{COLORS['secondary']}" opacity="0.9"/>
    <circle cx="0" cy="40" r="15" fill="{COLORS['accent']}"/>
  </g>
</svg>'''

    output_path = LOGOS_DIR / "ownex_app_icon_v2.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)
    return str(output_path)

def generate_favicon_v2() -> str:
    """Generate favicon (32x32)."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <defs>
    <linearGradient id="favGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['primary']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['secondary']};stop-opacity:1" />
    </linearGradient>
  </defs>

  <rect width="32" height="32" fill="{COLORS['background']}"/>

  <!-- Symbol simplified -->
  <polygon points="16,2 28,8 28,24 16,30 4,24 4,8"
           fill="url(#favGrad)" opacity="0.8"/>
  <polygon points="16,8 24,14 24,22 16,8"
           fill="{COLORS['secondary']}" opacity="0.7"/>
  <circle cx="16" cy="16" r="3" fill="{COLORS['accent']}"/>
</svg>'''

    output_path = LOGOS_DIR / "ownex_favicon_v2.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)
    return str(output_path)

def generate_monochrome_v2() -> str:
    """Generate monochrome version (512x512)."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <rect width="512" height="512" fill="{COLORS['background']}"/>

  <polygon points="256,30 476,136 476,376 256,482 36,376 36,136"
           fill="none" stroke="{COLORS['text']}" stroke-width="3"/>
  <polygon points="256,60 436,144 436,368 256,452 76,368 76,144"
           fill="{COLORS['text']}" opacity="0.15"/>
  <polygon points="256,100 356,256 256,300"
           fill="{COLORS['text']}"/>
  <polygon points="256,140 320,256 256,260"
           fill="{COLORS['text']}" opacity="0.9"/>
  <circle cx="256" cy="220" r="18" fill="{COLORS['text']}"/>

  <text x="256" y="400" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="48" font-weight="700" fill="{COLORS['text']}" letter-spacing="4">OWNEX</text>
</svg>'''

    output_path = LOGOS_DIR / "ownex_monochrome_v2.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)
    return str(output_path)

def generate_transparent_v2() -> str:
    """Generate transparent version (512x512)."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="transGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['primary']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['secondary']};stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- No background - transparent -->

  <!-- Symbol -->
  <polygon points="256,30 476,136 476,376 256,482 36,376 36,136"
           fill="none" stroke="url(#transGrad)" stroke-width="3"/>
  <polygon points="256,60 436,144 436,368 256,452 76,368 76,144"
           fill="url(#transGrad)" opacity="0.2"/>
  <polygon points="256,100 356,256 256,300"
           fill="{COLORS['primary']}"/>
  <polygon points="256,140 320,256 256,260"
           fill="{COLORS['secondary']}" opacity="0.9"/>
  <circle cx="256" cy="220" r="18" fill="{COLORS['accent']}"/>

  <text x="256" y="400" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="48" font-weight="700" fill="{COLORS['text']}" letter-spacing="4">OWNEX</text>
</svg>'''

    output_path = LOGOS_DIR / "ownex_transparent_v2.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)
    return str(output_path)

def generate_ui_32px_v2() -> str:
    """Generate UI icon (32x32) for small elements."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <rect width="32" height="32" fill="{COLORS['background']}"/>

  <polygon points="16,2 28,8 28,24 16,30 4,24 4,8"
           fill="none" stroke="{COLORS['primary']}" stroke-width="2"/>
  <polygon points="16,8 24,14 24,22 16,8"
           fill="{COLORS['primary']}" opacity="0.3"/>
  <polygon points="16,10 22,16 16,22"
           fill="{COLORS['primary']}"/>
  <circle cx="16" cy="16" r="2" fill="{COLORS['accent']}"/>
</svg>'''

    output_path = LOGOS_DIR / "ownex_ui_32px_v2.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)
    return str(output_path)

if __name__ == "__main__":
    print("Generating complete OWNEX logo system v2...")

    main_logo = generate_main_logo_v2()
    print(f"✓ Main logo: {main_logo}")

    app_icon = generate_app_icon_v2()
    print(f"✓ App icon: {app_icon}")

    favicon = generate_favicon_v2()
    print(f"✓ Favicon: {favicon}")

    monochrome = generate_monochrome_v2()
    print(f"✓ Monochrome: {monochrome}")

    transparent = generate_transparent_v2()
    print(f"✓ Transparent: {transparent}")

    ui_32px = generate_ui_32px_v2()
    print(f"✓ UI icon (32px): {ui_32px}")

    print(f"\nAll logos generated in: {LOGOS_DIR}")
    print("  - Scales: 32px (UI), 64px (small), 512px (main)")
    print("  - Versions: main, app icon, favicon, monochrome, transparent, UI")
