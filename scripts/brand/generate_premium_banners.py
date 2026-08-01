#!/usr/bin/env python3
"""
OWNEX Premium Banner Generator
Creates hero banners based on the new premium brand identity v2.0
Minimal, typography-focused, functional design
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

def create_hero_banner_unified():
    """
    Creates the unified hero banner for README
    Typography-focused, minimal design
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="2400" height="600" viewBox="0 0 2400 600" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="2400" height="600" fill="{COLORS['cosmos']}"/>

  <!-- Geometric mark (large, subtle) -->
  <g opacity="0.03">
    <circle cx="1200" cy="300" r="280" stroke="{COLORS['text_primary']}" stroke-width="40" fill="none"/>
    <path d="M1200 20 L1200 220 L1600 300 L1200 380 L1200 580 L800 300 L1200 20 Z" fill="{COLORS['text_primary']}"/>
    <circle cx="1200" cy="300" r="70" fill="{COLORS['cosmos']}" stroke="{COLORS['text_primary']}" stroke-width="20"/>
  </g>

  <!-- Content -->
  <g transform="translate(1200, 300)">
    <!-- Wordmark -->
    <text x="0" y="20" text-anchor="middle" font-family="'Inter Display', 'Inter', system-ui, sans-serif" font-weight="700" font-size="120" letter-spacing="-0.02em" fill="{COLORS['text_primary']}">OWNEX</text>

    <!-- Tagline -->
    <text x="0" y="80" text-anchor="middle" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="28" letter-spacing="0.02em" fill="{COLORS['text_secondary']}">The Personalized Autonomous Operating System</text>

    <!-- Accent line -->
    <rect x="-100" y="110" width="200" height="2" fill="{COLORS['accent']}"/>
  </g>
</svg>"""
    return svg

def create_hero_banner_alpha():
    """
    Creates ALPHA-specific hero banner
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="2400" height="600" viewBox="0 0 2400 600" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="2400" height="600" fill="{COLORS['cosmos']}"/>

  <!-- Geometric mark (large, subtle) -->
  <g opacity="0.03">
    <circle cx="1200" cy="300" r="280" stroke="{COLORS['accent']}" stroke-width="40" fill="none"/>
    <path d="M1200 20 L1200 220 L1600 300 L1200 380 L1200 580 L800 300 L1200 20 Z" fill="{COLORS['accent']}"/>
    <circle cx="1200" cy="300" r="70" fill="{COLORS['cosmos']}" stroke="{COLORS['accent']}" stroke-width="20"/>
  </g>

  <!-- Content -->
  <g transform="translate(1200, 300)">
    <!-- Wordmark -->
    <text x="0" y="20" text-anchor="middle" font-family="'Inter Display', 'Inter', system-ui, sans-serif" font-weight="700" font-size="120" letter-spacing="-0.02em" fill="{COLORS['text_primary']}">OWNEX</text>

    <!-- Edition -->
    <text x="0" y="80" text-anchor="middle" font-family="'Inter', system-ui, sans-serif" font-weight="600" font-size="32" letter-spacing="0.1em" fill="{COLORS['accent']}">ALPHA</text>

    <!-- Tagline -->
    <text x="0" y="130" text-anchor="middle" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="24" letter-spacing="0.02em" fill="{COLORS['text_secondary']}">Desktop Operating System</text>

    <!-- Accent line -->
    <rect x="-100" y="160" width="200" height="2" fill="{COLORS['accent']}"/>
  </g>
</svg>"""
    return svg

def create_hero_banner_omega():
    """
    Creates OMEGA-specific hero banner
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="2400" height="600" viewBox="0 0 2400 600" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="2400" height="600" fill="{COLORS['cosmos']}"/>

  <!-- Geometric mark (large, subtle) -->
  <g opacity="0.03">
    <circle cx="1200" cy="300" r="280" stroke="{COLORS['success']}" stroke-width="40" fill="none"/>
    <path d="M1200 20 L1200 220 L1600 300 L1200 380 L1200 580 L800 300 L1200 20 Z" fill="{COLORS['success']}"/>
    <circle cx="1200" cy="300" r="70" fill="{COLORS['cosmos']}" stroke="{COLORS['success']}" stroke-width="20"/>
  </g>

  <!-- Content -->
  <g transform="translate(1200, 300)">
    <!-- Wordmark -->
    <text x="0" y="20" text-anchor="middle" font-family="'Inter Display', 'Inter', system-ui, sans-serif" font-weight="700" font-size="120" letter-spacing="-0.02em" fill="{COLORS['text_primary']}">OWNEX</text>

    <!-- Edition -->
    <text x="0" y="80" text-anchor="middle" font-family="'Inter', system-ui, sans-serif" font-weight="600" font-size="32" letter-spacing="0.1em" fill="{COLORS['success']}">OMEGA</text>

    <!-- Tagline -->
    <text x="0" y="130" text-anchor="middle" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="24" letter-spacing="0.02em" fill="{COLORS['text_secondary']}">Android &amp; Wear OS Companion</text>

    <!-- Accent line -->
    <rect x="-100" y="160" width="200" height="2" fill="{COLORS['success']}"/>
  </g>
</svg>"""
    return svg

def create_og_cover():
    """
    Creates Open Graph cover image
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="1200" height="630" viewBox="0 0 1200 630" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="1200" height="630" fill="{COLORS['cosmos']}"/>

  <!-- Geometric mark (large, subtle) -->
  <g opacity="0.05">
    <circle cx="600" cy="315" r="200" stroke="{COLORS['text_primary']}" stroke-width="30" fill="none"/>
    <path d="M600 115 L600 215 L820 315 L600 415 L600 515 L380 315 L600 115 Z" fill="{COLORS['text_primary']}"/>
    <circle cx="600" cy="315" r="50" fill="{COLORS['cosmos']}" stroke="{COLORS['text_primary']}" stroke-width="15"/>
  </g>

  <!-- Content -->
  <g transform="translate(600, 315)">
    <!-- Wordmark -->
    <text x="0" y="20" text-anchor="middle" font-family="'Inter Display', 'Inter', system-ui, sans-serif" font-weight="700" font-size="80" letter-spacing="-0.02em" fill="{COLORS['text_primary']}">OWNEX</text>

    <!-- Tagline -->
    <text x="0" y="70" text-anchor="middle" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="20" letter-spacing="0.02em" fill="{COLORS['text_secondary']}">The Personalized Autonomous Operating System</text>

    <!-- Accent line -->
    <rect x="-80" y="100" width="160" height="2" fill="{COLORS['accent']}"/>
  </g>
</svg>"""
    return svg

def save_svg(svg_content, filepath):
    """Save SVG content to file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(svg_content)
    print(f"Created: {filepath}")

def main():
    """Generate all banner assets"""
    banners_dir = Path("assets/banners")
    banners_dir.mkdir(parents=True, exist_ok=True)

    # Backup existing banners
    backup_dir = Path(".ownex_backups/banners_backup")
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Generate new banners
    print("Generating premium banners...")
    save_svg(create_hero_banner_unified(), banners_dir / "hero-banner-unified.svg")
    save_svg(create_hero_banner_alpha(), banners_dir / "hero-banner-alpha.svg")
    save_svg(create_hero_banner_omega(), banners_dir / "hero-banner-omega.svg")
    save_svg(create_og_cover(), banners_dir / "og-cover.svg")

    print("\n✓ All premium banners generated successfully")
    print(f"Output directory: {banners_dir.absolute()}")

if __name__ == "__main__":
    main()
