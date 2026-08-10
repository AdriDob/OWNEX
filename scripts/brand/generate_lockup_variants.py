#!/usr/bin/env python3
"""
OWNEX Brand Lockup Generator
Creates 9 brand lockup variants as specified in TYPOGRAPHY.md
"""

from pathlib import Path


def generate_symbol_only(color="#FFFFFF"):
    """1. Symbol only"""
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <circle cx="256" cy="256" r="180" fill="none" stroke="{color}" stroke-width="12" opacity="0.9"/>
  <circle cx="256" cy="256" r="120" fill="none" stroke="{color}" stroke-width="8" opacity="0.7"/>
  <circle cx="256" cy="256" r="40" fill="{color}"/>
  <path d="M 256 76 L 256 216" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
  <path d="M 256 296 L 256 436" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
  <path d="M 76 256 L 216 256" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
  <path d="M 296 256 L 436 256" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
  <circle cx="256" cy="76" r="16" fill="{color}"/>
  <circle cx="256" cy="436" r="16" fill="{color}"/>
  <circle cx="76" cy="256" r="16" fill="{color}"/>
  <circle cx="436" cy="256" r="16" fill="{color}"/>
  <path d="M 130 130 L 216 216" stroke="{color}" stroke-width="4" stroke-linecap="round" opacity="0.4"/>
  <path d="M 382 130 L 296 216" stroke="{color}" stroke-width="4" stroke-linecap="round" opacity="0.4"/>
  <path d="M 130 382 L 216 296" stroke="{color}" stroke-width="4" stroke-linecap="round" opacity="0.4"/>
  <path d="M 382 382 L 296 296" stroke="{color}" stroke-width="4" stroke-linecap="round" opacity="0.4"/>
</svg>"""
    return svg


def generate_wordmark_only(color="#FFFFFF"):
    """2. OWNEX wordmark only (using path-based version)"""
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 80" width="400" height="80">
  <g transform="translate(32, 40)">
    <circle cx="0" cy="0" r="24" fill="none" stroke="{color}" stroke-width="6"/>
    <circle cx="0" cy="0" r="4" fill="{color}" opacity="0.6"/>
  </g>
  <g transform="translate(96, 40)">
    <path d="M -24 -20 L -12 20 L 0 -5 L 12 20 L 24 -20" 
          fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
  <g transform="translate(168, 40)">
    <path d="M -24 -20 L -24 20 L 24 -20 L 24 20" 
          fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
  <g transform="translate(240, 40)">
    <path d="M -24 -20 L 24 -20 M -24 0 L 16 0 M -24 20 L 24 20" 
          fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
  </g>
  <g transform="translate(320, 40)">
    <path d="M -20 -20 L 20 20 M 20 -20 L -20 20" 
          fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
    <circle cx="0" cy="0" r="3" fill="{color}" opacity="0.4"/>
  </g>
</svg>"""
    return svg


def generate_symbol_wordmark(color="#FFFFFF"):
    """3. Symbol + OWNEX (horizontal)"""
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 120" width="600" height="120">
  <!-- Symbol (scaled and positioned) -->
  <g transform="translate(60, 60) scale(0.1)">
    <circle cx="0" cy="0" r="180" fill="none" stroke="{color}" stroke-width="12" opacity="0.9"/>
    <circle cx="0" cy="0" r="120" fill="none" stroke="{color}" stroke-width="8" opacity="0.7"/>
    <circle cx="0" cy="0" r="40" fill="{color}"/>
    <path d="M 0 -180 L 0 -40" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M 0 40 L 0 180" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M -180 0 L -40 0" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M 40 0 L 180 0" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <circle cx="0" cy="-180" r="16" fill="{color}"/>
    <circle cx="0" cy="180" r="16" fill="{color}"/>
    <circle cx="-180" cy="0" r="16" fill="{color}"/>
    <circle cx="180" cy="0" r="16" fill="{color}"/>
  </g>

  <!-- Wordmark -->
  <g transform="translate(160, 40)">
    <g transform="translate(32, 40)">
      <circle cx="0" cy="0" r="24" fill="none" stroke="{color}" stroke-width="6"/>
      <circle cx="0" cy="0" r="4" fill="{color}" opacity="0.6"/>
    </g>
    <g transform="translate(96, 40)">
      <path d="M -24 -20 L -12 20 L 0 -5 L 12 20 L 24 -20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <g transform="translate(168, 40)">
      <path d="M -24 -20 L -24 20 L 24 -20 L 24 20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <g transform="translate(240, 40)">
      <path d="M -24 -20 L 24 -20 M -24 0 L 16 0 M -24 20 L 24 20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
    </g>
    <g transform="translate(320, 40)">
      <path d="M -20 -20 L 20 20 M 20 -20 L -20 20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
      <circle cx="0" cy="0" r="3" fill="{color}" opacity="0.4"/>
    </g>
  </g>
</svg>"""
    return svg


def generate_symbol_wordmark_descriptor(color="#FFFFFF", descriptor_color="#888888"):
    """4. Symbol + OWNEX + descriptor"""
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 160" width="600" height="160">
  <!-- Symbol -->
  <g transform="translate(60, 60) scale(0.1)">
    <circle cx="0" cy="0" r="180" fill="none" stroke="{color}" stroke-width="12" opacity="0.9"/>
    <circle cx="0" cy="0" r="120" fill="none" stroke="{color}" stroke-width="8" opacity="0.7"/>
    <circle cx="0" cy="0" r="40" fill="{color}"/>
    <path d="M 0 -180 L 0 -40" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M 0 40 L 0 180" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M -180 0 L -40 0" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M 40 0 L 180 0" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <circle cx="0" cy="-180" r="16" fill="{color}"/>
    <circle cx="0" cy="180" r="16" fill="{color}"/>
    <circle cx="-180" cy="0" r="16" fill="{color}"/>
    <circle cx="180" cy="0" r="16" fill="{color}"/>
  </g>

  <!-- Wordmark -->
  <g transform="translate(160, 40)">
    <g transform="translate(32, 40)">
      <circle cx="0" cy="0" r="24" fill="none" stroke="{color}" stroke-width="6"/>
      <circle cx="0" cy="0" r="4" fill="{color}" opacity="0.6"/>
    </g>
    <g transform="translate(96, 40)">
      <path d="M -24 -20 L -12 20 L 0 -5 L 12 20 L 24 -20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <g transform="translate(168, 40)">
      <path d="M -24 -20 L -24 20 L 24 -20 L 24 20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <g transform="translate(240, 40)">
      <path d="M -24 -20 L 24 -20 M -24 0 L 16 0 M -24 20 L 24 20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
    </g>
    <g transform="translate(320, 40)">
      <path d="M -20 -20 L 20 20 M 20 -20 L -20 20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
      <circle cx="0" cy="0" r="3" fill="{color}" opacity="0.4"/>
    </g>
  </g>

  <!-- Descriptor -->
  <text x="160" y="130" font-family="Sora, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        font-size="14" font-weight="500" letter-spacing="0.12em" fill="{descriptor_color}">
    AUTONOMOUS WORK OPERATING SYSTEM
  </text>
</svg>"""
    return svg


def generate_horizontal_lockup(color="#FFFFFF"):
    """5. Horizontal lockup (standard, with descriptor)"""
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 160" width="800" height="160">
  <!-- Symbol -->
  <g transform="translate(60, 60) scale(0.1)">
    <circle cx="0" cy="0" r="180" fill="none" stroke="{color}" stroke-width="12" opacity="0.9"/>
    <circle cx="0" cy="0" r="120" fill="none" stroke="{color}" stroke-width="8" opacity="0.7"/>
    <circle cx="0" cy="0" r="40" fill="{color}"/>
    <path d="M 0 -180 L 0 -40" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M 0 40 L 0 180" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M -180 0 L -40 0" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M 40 0 L 180 0" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <circle cx="0" cy="-180" r="16" fill="{color}"/>
    <circle cx="0" cy="180" r="16" fill="{color}"/>
    <circle cx="-180" cy="0" r="16" fill="{color}"/>
    <circle cx="180" cy="0" r="16" fill="{color}"/>
  </g>

  <!-- Wordmark -->
  <g transform="translate(160, 40)">
    <g transform="translate(32, 40)">
      <circle cx="0" cy="0" r="24" fill="none" stroke="{color}" stroke-width="6"/>
      <circle cx="0" cy="0" r="4" fill="{color}" opacity="0.6"/>
    </g>
    <g transform="translate(96, 40)">
      <path d="M -24 -20 L -12 20 L 0 -5 L 12 20 L 24 -20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <g transform="translate(168, 40)">
      <path d="M -24 -20 L -24 20 L 24 -20 L 24 20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <g transform="translate(240, 40)">
      <path d="M -24 -20 L 24 -20 M -24 0 L 16 0 M -24 20 L 24 20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
    </g>
    <g transform="translate(320, 40)">
      <path d="M -20 -20 L 20 20 M 20 -20 L -20 20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
      <circle cx="0" cy="0" r="3" fill="{color}" opacity="0.4"/>
    </g>
  </g>

  <!-- Descriptor (right-aligned) -->
  <text x="780" y="90" text-anchor="end" font-family="Sora, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        font-size="14" font-weight="500" letter-spacing="0.12em" fill="#888888">
    AUTONOMOUS WORK OPERATING SYSTEM
  </text>
</svg>"""
    return svg


def generate_vertical_lockup(color="#FFFFFF", descriptor_color="#888888"):
    """6. Vertical lockup (stacked)"""
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500" width="400" height="500">
  <!-- Symbol (centered, larger) -->
  <g transform="translate(200, 120) scale(0.15)">
    <circle cx="0" cy="0" r="180" fill="none" stroke="{color}" stroke-width="12" opacity="0.9"/>
    <circle cx="0" cy="0" r="120" fill="none" stroke="{color}" stroke-width="8" opacity="0.7"/>
    <circle cx="0" cy="0" r="40" fill="{color}"/>
    <path d="M 0 -180 L 0 -40" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M 0 40 L 0 180" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M -180 0 L -40 0" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M 40 0 L 180 0" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <circle cx="0" cy="-180" r="16" fill="{color}"/>
    <circle cx="0" cy="180" r="16" fill="{color}"/>
    <circle cx="-180" cy="0" r="16" fill="{color}"/>
    <circle cx="180" cy="0" r="16" fill="{color}"/>
  </g>

  <!-- Wordmark (centered below symbol) -->
  <g transform="translate(200, 280)">
    <g transform="translate(-160, 0)">
      <g transform="translate(32, 40)">
        <circle cx="0" cy="0" r="24" fill="none" stroke="{color}" stroke-width="6"/>
        <circle cx="0" cy="0" r="4" fill="{color}" opacity="0.6"/>
      </g>
      <g transform="translate(96, 40)">
        <path d="M -24 -20 L -12 20 L 0 -5 L 12 20 L 24 -20" 
              fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
      <g transform="translate(168, 40)">
        <path d="M -24 -20 L -24 20 L 24 -20 L 24 20" 
              fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
      <g transform="translate(240, 40)">
        <path d="M -24 -20 L 24 -20 M -24 0 L 16 0 M -24 20 L 24 20" 
              fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
      </g>
      <g transform="translate(320, 40)">
        <path d="M -20 -20 L 20 20 M 20 -20 L -20 20" 
              fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
        <circle cx="0" cy="0" r="3" fill="{color}" opacity="0.4"/>
      </g>
    </g>
  </g>

  <!-- Descriptor (centered below wordmark) -->
  <text x="200" y="360" text-anchor="middle" font-family="Sora, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        font-size="14" font-weight="500" letter-spacing="0.12em" fill="{descriptor_color}">
    AUTONOMOUS WORK OPERATING SYSTEM
  </text>
</svg>"""
    return svg


def generate_monochrome(color="#000000"):
    """7. Monochrome version (single color)"""
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 120" width="600" height="120">
  <!-- Symbol -->
  <g transform="translate(60, 60) scale(0.1)">
    <circle cx="0" cy="0" r="180" fill="none" stroke="{color}" stroke-width="12" opacity="0.9"/>
    <circle cx="0" cy="0" r="120" fill="none" stroke="{color}" stroke-width="8" opacity="0.7"/>
    <circle cx="0" cy="0" r="40" fill="{color}"/>
    <path d="M 0 -180 L 0 -40" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M 0 40 L 0 180" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M -180 0 L -40 0" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <path d="M 40 0 L 180 0" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
    <circle cx="0" cy="-180" r="16" fill="{color}"/>
    <circle cx="0" cy="180" r="16" fill="{color}"/>
    <circle cx="-180" cy="0" r="16" fill="{color}"/>
    <circle cx="180" cy="0" r="16" fill="{color}"/>
  </g>

  <!-- Wordmark -->
  <g transform="translate(160, 40)">
    <g transform="translate(32, 40)">
      <circle cx="0" cy="0" r="24" fill="none" stroke="{color}" stroke-width="6"/>
      <circle cx="0" cy="0" r="4" fill="{color}" opacity="0.6"/>
    </g>
    <g transform="translate(96, 40)">
      <path d="M -24 -20 L -12 20 L 0 -5 L 12 20 L 24 -20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <g transform="translate(168, 40)">
      <path d="M -24 -20 L -24 20 L 24 -20 L 24 20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <g transform="translate(240, 40)">
      <path d="M -24 -20 L 24 -20 M -24 0 L 16 0 M -24 20 L 24 20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
    </g>
    <g transform="translate(320, 40)">
      <path d="M -20 -20 L 20 20 M 20 -20 L -20 20" 
            fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
      <circle cx="0" cy="0" r="3" fill="{color}" opacity="0.4"/>
    </g>
  </g>
</svg>"""
    return svg


def generate_dark_mode():
    """8. Dark-mode version (white on dark)"""
    return generate_symbol_wordmark("#FFFFFF")


def generate_light_mode():
    """9. Light-mode version (black on light)"""
    return generate_symbol_wordmark("#0B0B0B")


def main():
    """Generate all 9 lockup variants"""
    logo_dir = Path("docs/assets/branding/logo")
    logo_dir.mkdir(parents=True, exist_ok=True)

    variants = {
        "ownex-symbol-only.svg": generate_symbol_only("#FFFFFF"),
        "ownex-wordmark-only.svg": generate_wordmark_only("#FFFFFF"),
        "ownex-symbol-wordmark.svg": generate_symbol_wordmark("#FFFFFF"),
        "ownex-symbol-wordmark-descriptor.svg": generate_symbol_wordmark_descriptor("#FFFFFF", "#888888"),
        "ownex-horizontal-lockup.svg": generate_horizontal_lockup("#FFFFFF"),
        "ownex-vertical-lockup.svg": generate_vertical_lockup("#FFFFFF", "#888888"),
        "ownex-monochrome.svg": generate_monochrome("#000000"),
        "ownex-dark-mode.svg": generate_dark_mode(),
        "ownex-light-mode.svg": generate_light_mode(),
    }

    for filename, content in variants.items():
        filepath = logo_dir / filename
        filepath.write_text(content, encoding="utf-8")
        print(f"Generated: {filepath}")

    # Convert to PNG
    try:
        import cairosvg
        for filename, content in variants.items():
            svg_path = logo_dir / filename
            # Determine output dimensions based on variant
            if "vertical" in filename:
                width, height = 400, 500
            elif "horizontal" in filename:
                width, height = 800, 160
            elif "symbol-only" in filename:
                width, height = 512, 512
            elif "wordmark-only" in filename:
                width, height = 400, 80
            else:
                width, height = 600, 120
            
            png_path = logo_dir / filename.replace('.svg', '.png')
            try:
                cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=width, output_height=height)
                print(f"Generated PNG: {png_path}")
            except Exception as e:
                print(f"Error converting {filename}: {e}")
    except ImportError:
        print("cairosvg not available, SVG only")


if __name__ == "__main__":
    main()