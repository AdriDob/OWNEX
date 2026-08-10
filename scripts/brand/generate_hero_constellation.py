#!/usr/bin/env python3
"""
OWNEX Hero Generator with Module Constellation
Creates a hero banner with OWNEX at center and connected modules as a constellation
"""

from pathlib import Path

def generate_hero_constellation():
    """
    Create hero banner with OWNEX constellation concept
    Central OWNEX nexus connected to module nodes (Security, Forge, Vault, Atlas, etc.)
    """
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2400 900" width="2400" height="900">
  <defs>
    <!-- Premium gradient for the hero background -->
    <linearGradient id="hero-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0B0B0B;stop-opacity:1" />
      <stop offset="50%" style="stop-color:#111115;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0B0B0B;stop-opacity:1" />
    </linearGradient>

    <!-- Blue gradient for connections -->
    <linearGradient id="connection-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#2D7FF9;stop-opacity:0.6" />
      <stop offset="100%" style="stop-color:#1E40FF;stop-opacity:0.3" />
    </linearGradient>

    <!-- Gold accent gradient -->
    <linearGradient id="gold-accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#D4AF37;stop-opacity:0.5" />
      <stop offset="100%" style="stop-color:#B8960C;stop-opacity:0.2" />
    </linearGradient>

    <!-- Nexus gradient -->
    <radialGradient id="nexus-glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#2D7FF9;stop-opacity:0.3" />
      <stop offset="100%" style="stop-color:#2D7FF9;stop-opacity:0" />
    </radialGradient>

    <!-- Module node gradient -->
    <radialGradient id="module-glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#2D7FF9;stop-opacity:0.4" />
      <stop offset="100%" style="stop-color:#2D7FF9;stop-opacity:0" />
    </radialGradient>
  </defs>

  <!-- Premium dark background -->
  <rect width="2400" height="900" fill="url(#hero-bg)"/>

  <!-- Subtle grid pattern for technical feel -->
  <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
    <path d="M 80 0 L 0 0 0 80" fill="none" stroke="#2D7FF9" stroke-width="0.5" opacity="0.03"/>
  </pattern>
  <rect width="2400" height="900" fill="url(#grid)"/>

  <!-- Central nexus glow area -->
  <ellipse cx="1200" cy="450" rx="500" ry="350" fill="url(#nexus-glow)"/>

  <!-- CONNECTIONS FROM CENTER TO MODULES -->
  <!-- Center to Security (top-left) -->
  <line x1="1200" y1="450" x2="400" y2="200" stroke="url(#connection-gradient)" stroke-width="2" opacity="0.5"/>
  <!-- Center to Forge (top-right) -->
  <line x1="1200" y1="450" x2="2000" y2="200" stroke="url(#connection-gradient)" stroke-width="2" opacity="0.5"/>
  <!-- Center to Vault (bottom-left) -->
  <line x1="1200" y1="450" x2="400" y2="700" stroke="url(#connection-gradient)" stroke-width="2" opacity="0.5"/>
  <!-- Center to Atlas (bottom-right) -->
  <line x1="1200" y1="450" x2="2000" y2="700" stroke="url(#connection-gradient)" stroke-width="2" opacity="0.5"/>
  <!-- Center to Intelligence (top-center) -->
  <line x1="1200" y1="450" x2="1200" y2="150" stroke="url(#connection-gradient)" stroke-width="2" opacity="0.5"/>
  <!-- Center to Automation (bottom-center) -->
  <line x1="1200" y1="450" x2="1200" y2="750" stroke="url(#connection-gradient)" stroke-width="2" opacity="0.5"/>

  <!-- INTER-MODULE CONNECTIONS (constellation effect) -->
  <line x1="400" y1="200" x2="1200" y2="150" stroke="url(#connection-gradient)" stroke-width="1" opacity="0.3"/>
  <line x1="2000" y1="200" x2="1200" y2="150" stroke="url(#connection-gradient)" stroke-width="1" opacity="0.3"/>
  <line x1="400" y1="700" x2="1200" y2="750" stroke="url(#connection-gradient)" stroke-width="1" opacity="0.3"/>
  <line x1="2000" y1="700" x2="1200" y2="750" stroke="url(#connection-gradient)" stroke-width="1" opacity="0.3"/>
  <line x1="400" y1="200" x2="400" y2="700" stroke="url(#connection-gradient)" stroke-width="1" opacity="0.3"/>
  <line x1="2000" y1="200" x2="2000" y2="700" stroke="url(#connection-gradient)" stroke-width="1" opacity="0.3"/>

  <!-- MODULE NODES -->
  <!-- Security Module (top-left) -->
  <g transform="translate(400, 200)">
    <ellipse cx="0" cy="0" rx="80" ry="80" fill="url(#module-glow)"/>
    <circle cx="0" cy="0" r="50" fill="none" stroke="#2D7FF9" stroke-width="3" opacity="0.8"/>
    <circle cx="0" cy="0" r="8" fill="#2D7FF9"/>
    <!-- Shield icon representation -->
    <path d="M -15 -10 L 0 -25 L 15 -10 L 15 10 C 15 25 0 35 0 35 C 0 35 -15 25 -15 10 Z" fill="none" stroke="#2D7FF9" stroke-width="2" opacity="0.6"/>
    <text x="0" y="60" text-anchor="middle" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="#FFFFFF" opacity="0.8">SECURITY</text>
  </g>

  <!-- Forge Module (top-right) -->
  <g transform="translate(2000, 200)">
    <ellipse cx="0" cy="0" rx="80" ry="80" fill="url(#module-glow)"/>
    <circle cx="0" cy="0" r="50" fill="none" stroke="#2D7FF9" stroke-width="3" opacity="0.8"/>
    <circle cx="0" cy="0" r="8" fill="#2D7FF9"/>
    <!-- Hammer/forge icon representation -->
    <path d="M -15 -15 L 15 15 M -10 -20 L 10 0 M 0 -25 L 20 -5" stroke="#2D7FF9" stroke-width="2" opacity="0.6"/>
    <text x="0" y="60" text-anchor="middle" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="#FFFFFF" opacity="0.8">FORGE</text>
  </g>

  <!-- Vault Module (bottom-left) -->
  <g transform="translate(400, 700)">
    <ellipse cx="0" cy="0" rx="80" ry="80" fill="url(#module-glow)"/>
    <circle cx="0" cy="0" r="50" fill="none" stroke="#2D7FF9" stroke-width="3" opacity="0.8"/>
    <circle cx="0" cy="0" r="8" fill="#2D7FF9"/>
    <!-- Vault/lock icon representation -->
    <rect x="-12" y="-8" width="24" height="20" fill="none" stroke="#2D7FF9" stroke-width="2" opacity="0.6" rx="2"/>
    <circle cx="0" cy="2" r="4" fill="none" stroke="#2D7FF9" stroke-width="2" opacity="0.6"/>
    <text x="0" y="60" text-anchor="middle" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="#FFFFFF" opacity="0.8">VAULT</text>
  </g>

  <!-- Atlas Module (bottom-right) -->
  <g transform="translate(2000, 700)">
    <ellipse cx="0" cy="0" rx="80" ry="80" fill="url(#module-glow)"/>
    <circle cx="0" cy="0" r="50" fill="none" stroke="#2D7FF9" stroke-width="3" opacity="0.8"/>
    <circle cx="0" cy="0" r="8" fill="#2D7FF9"/>
    <!-- Atlas/map icon representation -->
    <circle cx="0" cy="0" r="15" fill="none" stroke="#2D7FF9" stroke-width="2" opacity="0.6"/>
    <path d="M -10 0 L 10 0 M 0 -10 L 0 10" stroke="#2D7FF9" stroke-width="2" opacity="0.6"/>
    <text x="0" y="60" text-anchor="middle" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="#FFFFFF" opacity="0.8">ATLAS</text>
  </g>

  <!-- Intelligence Module (top-center) -->
  <g transform="translate(1200, 150)">
    <ellipse cx="0" cy="0" rx="80" ry="80" fill="url(#module-glow)"/>
    <circle cx="0" cy="0" r="50" fill="none" stroke="#2D7FF9" stroke-width="3" opacity="0.8"/>
    <circle cx="0" cy="0" r="8" fill="#2D7FF9"/>
    <!-- Brain/intelligence icon representation -->
    <path d="M -15 0 C -15 -10 -8 -15 0 -15 C 8 -15 15 -10 15 0 C 15 10 8 15 0 15 C -8 15 -15 10 -15 0" fill="none" stroke="#2D7FF9" stroke-width="2" opacity="0.6"/>
    <circle cx="-5" cy="-3" r="2" fill="#2D7FF9" opacity="0.6"/>
    <circle cx="5" cy="-3" r="2" fill="#2D7FF9" opacity="0.6"/>
    <text x="0" y="60" text-anchor="middle" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="#FFFFFF" opacity="0.8">INTELLIGENCE</text>
  </g>

  <!-- Automation Module (bottom-center) -->
  <g transform="translate(1200, 750)">
    <ellipse cx="0" cy="0" rx="80" ry="80" fill="url(#module-glow)"/>
    <circle cx="0" cy="0" r="50" fill="none" stroke="#2D7FF9" stroke-width="3" opacity="0.8"/>
    <circle cx="0" cy="0" r="8" fill="#2D7FF9"/>
    <!-- Gears/automation icon representation -->
    <circle cx="0" cy="0" r="12" fill="none" stroke="#2D7FF9" stroke-width="2" opacity="0.6"/>
    <circle cx="0" cy="0" r="4" fill="#2D7FF9" opacity="0.6"/>
    <path d="M -18 0 L -12 0 M 12 0 L 18 0 M 0 -18 L 0 -12 M 0 12 L 0 18" stroke="#2D7FF9" stroke-width="2" opacity="0.6"/>
    <text x="0" y="60" text-anchor="middle" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="#FFFFFF" opacity="0.8">AUTOMATION</text>
  </g>

  <!-- CENTRAL OWNEX NEXUS (larger, more prominent) -->
  <g transform="translate(1200, 450)">
    <!-- Outer orbital ring -->
    <circle cx="0" cy="0" r="100" fill="none" stroke="#2D7FF9" stroke-width="4" opacity="0.9"/>
    <!-- Inner orbital ring -->
    <circle cx="0" cy="0" r="70" fill="none" stroke="#2D7FF9" stroke-width="3" opacity="0.7"/>
    <!-- Central convergence node -->
    <circle cx="0" cy="0" r="30" fill="#2D7FF9"/>
    <!-- Directional convergence paths -->
    <path d="M 0 -100 L 0 -70" stroke="#2D7FF9" stroke-width="3" stroke-linecap="round" opacity="0.8"/>
    <path d="M 0 70 L 0 100" stroke="#2D7FF9" stroke-width="3" stroke-linecap="round" opacity="0.8"/>
    <path d="M -100 0 L -70 0" stroke="#2D7FF9" stroke-width="3" stroke-linecap="round" opacity="0.8"/>
    <path d="M 70 0 L 100 0" stroke="#2D7FF9" stroke-width="3" stroke-linecap="round" opacity="0.8"/>
    <!-- Opportunity nodes -->
    <circle cx="0" cy="-100" r="12" fill="#2D7FF9"/>
    <circle cx="0" cy="100" r="12" fill="#2D7FF9"/>
    <circle cx="-100" cy="0" r="12" fill="#2D7FF9"/>
    <circle cx="100" cy="0" r="12" fill="#2D7FF9"/>
    <!-- Diagonal connections -->
    <path d="M -70 -70 L -40 -40" stroke="#2D7FF9" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
    <path d="M 70 -70 L 40 -40" stroke="#2D7FF9" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
    <path d="M -70 70 L -40 40" stroke="#2D7FF9" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
    <path d="M 70 70 L 40 40" stroke="#2D7FF9" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
  </g>

  <!-- OWNEX WORDMARK -->
  <text x="1200" y="850" text-anchor="middle" font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="48" font-weight="700" letter-spacing="8" fill="#FFFFFF" opacity="0.9">OWNEX</text>

  <!-- TAGLINE -->
  <text x="1200" y="890" text-anchor="middle" font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="18" font-weight="400" letter-spacing="4" fill="#FFFFFF" opacity="0.6">AUTONOMOUS WORK OPERATING SYSTEM</text>

  <!-- Subtle gold accent line -->
  <line x1="200" y1="80" x2="2200" y2="80" stroke="url(#gold-accent)" stroke-width="1" opacity="0.3"/>
  <circle cx="200" cy="80" r="3" fill="#D4AF37" opacity="0.4"/>
  <circle cx="2200" cy="80" r="3" fill="#D4AF37" opacity="0.4"/>
</svg>"""
    return svg


def main():
    """Generate hero banner with constellation"""
    banners_dir = Path("docs/assets/branding/banners")
    banners_dir.mkdir(parents=True, exist_ok=True)

    hero_svg = generate_hero_constellation()
    hero_path = banners_dir / "ownex-hero-banner.svg"
    hero_path.write_text(hero_svg, encoding="utf-8")
    print(f"Generated hero: {hero_path}")

    # Generate PNG version
    try:
        import cairosvg
        png_path = banners_dir / "ownex-hero-banner.png"
        cairosvg.svg2png(url=str(hero_path), write_to=str(png_path), output_width=2400, output_height=900)
        print(f"Generated PNG: {png_path}")
    except ImportError:
        print("cairosvg not available, SVG only")


if __name__ == "__main__":
    main()