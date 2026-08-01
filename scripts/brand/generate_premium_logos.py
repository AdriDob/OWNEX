#!/usr/bin/env python3
"""
OWNEX Premium Logo Generator
Creates SVG logos based on the new premium brand identity v2.0
"""

import os
from pathlib import Path

# Brand colors from new identity
COLORS = {
    'cosmos': '#08090A',
    'surface': '#111113',
    'surface_alt': '#1F2023',
    'text_primary': '#F6F8FB',
    'text_secondary': '#8B8D98',
    'accent': '#5E6AD2',
    'accent_hover': '#7B85E0',
    'success': '#00E39A',
    'white': '#FFFFFF',
    'black': '#000000',
}

def create_geometric_mark(color=COLORS['text_primary']):
    """
    Creates the abstract geometric "O" mark
    Represents autonomous loop, intelligence cycle, system precision
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="512" height="512" viewBox="0 0 512 512" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Outer ring - represents the autonomous loop -->
  <circle cx="256" cy="256" r="200" stroke="{color}" stroke-width="32" fill="none"/>
  <!-- Inner geometric division - represents intelligence/precision -->
  <path d="M256 56 L256 200 L400 256 L256 312 L256 456 L112 256 L256 56 Z" fill="{color}"/>
  <!-- Negative space inner circle - represents system core -->
  <circle cx="256" cy="256" r="48" fill="{COLORS['cosmos']}" stroke="{color}" stroke-width="16"/>
</svg>"""
    return svg

def create_wordmark(color=COLORS['text_primary']):
    """
    Creates the OWNEX wordmark using SVG text
    Inter Display style - tight letter spacing, engineered feel
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="800" height="200" viewBox="0 0 800 200" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .wordmark {{
      font-family: 'Inter Display', 'Inter', system-ui, -apple-system, sans-serif;
      font-weight: 700;
      font-size: 140px;
      letter-spacing: -0.02em;
      fill: {color};
    }}
  </style>
  <text x="0" y="150" class="wordmark">OWNEX</text>
</svg>"""
    return svg

def create_lockup(color=COLORS['text_primary']):
    """
    Creates the lockup - geometric mark + wordmark
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="1000" height="300" viewBox="0 0 1000 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .wordmark {{
      font-family: 'Inter Display', 'Inter', system-ui, -apple-system, sans-serif;
      font-weight: 700;
      font-size: 120px;
      letter-spacing: -0.02em;
      fill: {color};
    }}
  </style>
  <!-- Geometric mark (scaled to 60% of wordmark height) -->
  <g transform="translate(0, 20)">
    <circle cx="70" cy="70" r="55" stroke="{color}" stroke-width="12" fill="none"/>
    <path d="M70 15 L70 55 L110 70 L70 85 L70 125 L30 70 L70 15 Z" fill="{color}"/>
    <circle cx="70" cy="70" r="14" fill="{COLORS['cosmos']}" stroke="{color}" stroke-width="5"/>
  </g>
  <!-- Wordmark -->
  <text x="160" y="180" class="wordmark">OWNEX</text>
</svg>"""
    return svg

def create_alpha_variant(color=COLORS['text_primary']):
    """
    Creates OWNEX ALPHA variant
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="100" viewBox="0 0 400 100" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .brand {{
      font-family: 'Inter Display', 'Inter', system-ui, -apple-system, sans-serif;
      font-weight: 700;
      font-size: 48px;
      letter-spacing: -0.02em;
      fill: {color};
    }}
    .edition {{
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      font-weight: 500;
      font-size: 24px;
      letter-spacing: 0.05em;
      fill: {COLORS['text_secondary']};
    }}
  </style>
  <text x="0" y="55" class="brand">OWNEX</text>
  <text x="0" y="85" class="edition">ALPHA</text>
</svg>"""
    return svg

def create_omega_variant(color=COLORS['text_primary']):
    """
    Creates OWNEX OMEGA variant
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="100" viewBox="0 0 400 100" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .brand {{
      font-family: 'Inter Display', 'Inter', system-ui, -apple-system, sans-serif;
      font-weight: 700;
      font-size: 48px;
      letter-spacing: -0.02em;
      fill: {color};
    }}
    .edition {{
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      font-weight: 500;
      font-size: 24px;
      letter-spacing: 0.05em;
      fill: {COLORS['text_secondary']};
    }}
  </style>
  <text x="0" y="55" class="brand">OWNEX</text>
  <text x="0" y="85" class="edition">OMEGA</text>
</svg>"""
    return svg

def create_favicon(size=32, color=COLORS['text_primary']):
    """
    Creates favicon at specified size
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{size}" height="{size}" viewBox="0 0 512 512" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="256" cy="256" r="200" stroke="{color}" stroke-width="32" fill="none"/>
  <path d="M256 56 L256 200 L400 256 L256 312 L256 456 L112 256 L256 56 Z" fill="{color}"/>
  <circle cx="256" cy="256" r="48" fill="{COLORS['cosmos']}" stroke="{color}" stroke-width="16"/>
</svg>"""
    return svg

def create_icon(size=512, color=COLORS['text_primary']):
    """
    Creates app icon at specified size
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{size}" height="{size}" viewBox="0 0 512 512" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="512" height="512" rx="96" fill="{COLORS['cosmos']}"/>
  <!-- Geometric mark centered -->
  <circle cx="256" cy="256" r="180" stroke="{color}" stroke-width="28" fill="none"/>
  <path d="M256 76 L256 180 L380 256 L256 332 L256 436 L132 256 L256 76 Z" fill="{color}"/>
  <circle cx="256" cy="256" r="44" fill="{COLORS['cosmos']}" stroke="{color}" stroke-width="14"/>
</svg>"""
    return svg

def save_svg(svg_content, filepath):
    """Save SVG content to file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(svg_content)
    print(f"Created: {filepath}")

def main():
    """Generate all logo assets"""
    output_dir = Path("assets/logos")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate primary logos
    print("Generating primary logos...")
    save_svg(create_geometric_mark(), output_dir / "ownex-mark.svg")
    save_svg(create_geometric_mark(COLORS['black']), output_dir / "ownex-mark-black.svg")
    save_svg(create_geometric_mark(COLORS['white']), output_dir / "ownex-mark-white.svg")

    save_svg(create_wordmark(), output_dir / "ownex-wordmark.svg")
    save_svg(create_wordmark(COLORS['black']), output_dir / "ownex-wordmark-black.svg")
    save_svg(create_wordmark(COLORS['white']), output_dir / "ownex-wordmark-white.svg")

    save_svg(create_lockup(), output_dir / "ownex-lockup.svg")
    save_svg(create_lockup(COLORS['black']), output_dir / "ownex-lockup-black.svg")
    save_svg(create_lockup(COLORS['white']), output_dir / "ownex-lockup-white.svg")

    # Generate edition variants
    print("Generating edition variants...")
    save_svg(create_alpha_variant(), output_dir / "ownex-alpha.svg")
    save_svg(create_alpha_variant(COLORS['black']), output_dir / "ownex-alpha-black.svg")
    save_svg(create_alpha_variant(COLORS['white']), output_dir / "ownex-alpha-white.svg")

    save_svg(create_omega_variant(), output_dir / "ownex-omega.svg")
    save_svg(create_omega_variant(COLORS['black']), output_dir / "ownex-omega-black.svg")
    save_svg(create_omega_variant(COLORS['white']), output_dir / "ownex-omega-white.svg")

    # Generate favicons
    print("Generating favicons...")
    save_svg(create_favicon(32), output_dir / "ownex-favicon.svg")
    save_svg(create_favicon(32, COLORS['black']), output_dir / "ownex-favicon-black.svg")
    save_svg(create_favicon(32, COLORS['white']), output_dir / "ownex-favicon-white.svg")

    # Generate app icons
    print("Generating app icons...")
    save_svg(create_icon(512), output_dir / "ownex-icon.svg")
    save_svg(create_icon(512, COLORS['accent']), output_dir / "ownex-icon-accent.svg")

    # Generate alpha/omega icons
    save_svg(create_icon(512, COLORS['accent']), output_dir / "ownex-icon-alpha.svg")
    save_svg(create_icon(512, COLORS['success']), output_dir / "ownex-icon-omega.svg")

    print("\n✓ All premium logos generated successfully")
    print(f"Output directory: {output_dir.absolute()}")

if __name__ == "__main__":
    main()
