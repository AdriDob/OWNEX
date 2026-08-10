#!/usr/bin/env python3
"""
OWNEX Premium Hero Generator v2
Creates a professional 2400×900 hero banner
Concept: "An intelligent operating system navigating a universe of work"
"""

from pathlib import Path


def generate_hero():
    """
    Create premium hero banner with OWNEX identity
    Dark environment, central nexus, orbital paths, subtle blue illumination
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

    <!-- Blue gradient for illumination -->
    <linearGradient id="blue-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#2D7FF9;stop-opacity:0.3" />
      <stop offset="100%" style="stop-color:#1E40FF;stop-opacity:0.1" />
    </linearGradient>

    <!-- Gold accent gradient -->
    <linearGradient id="gold-accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#D4AF37;stop-opacity:0.4" />
      <stop offset="100%" style="stop-color:#B8960C;stop-opacity:0.2" />
    </linearGradient>

    <!-- Nexus gradient -->
    <radialGradient id="nexus-glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#2D7FF9;stop-opacity:0.2" />
      <stop offset="100%" style="stop-color:#2D7FF9;stop-opacity:0" />
    </radialGradient>
  </defs>

  <!-- Premium dark background -->
  <rect width="2400" height="900" fill="url(#hero-bg)"/>

  <!-- Subtle grid pattern for technical feel -->
  <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
    <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#2D7FF9" stroke-width="0.5" opacity="0.05"/>
  </pattern>
  <rect width="2400" height="900" fill="url(#grid)"/>

  <!-- Central nexus glow area -->
  <ellipse cx="1200" cy="450" rx="400" ry="300" fill="url(#nexus-glow)"/>

  <!-- Large orbital rings representing opportunity universe -->
  <circle cx="1200" cy="450" r="350"
          fill="none"
          stroke="url(#blue-glow)"
          stroke-width="2"
          opacity="0.4"/>

  <circle cx="1200" cy="450" r="280"
          fill="none"
          stroke="url(#blue-glow)"
          stroke-width="1.5"
          opacity="0.3"/>

  <circle cx="1200" cy="450" r="220"
          fill="none"
          stroke="url(#blue-glow)"
          stroke-width="1"
          opacity="0.2"/>

  <!-- Opportunity nodes distributed on orbits -->
  <!-- Top right cluster -->
  <circle cx="1500" cy="250" r="8" fill="#2D7FF9" opacity="0.6"/>
  <circle cx="1550" cy="280" r="5" fill="#2D7FF9" opacity="0.4"/>
  <circle cx="1480" cy="220" r="6" fill="#2D7FF9" opacity="0.5"/>

  <!-- Bottom right cluster -->
  <circle cx="1450" cy="650" r="7" fill="#2D7FF9" opacity="0.5"/>
  <circle cx="1520" cy="620" r="5" fill="#2D7FF9" opacity="0.4"/>

  <!-- Bottom left cluster -->
  <circle cx="950" cy="680" r="8" fill="#2D7FF9" opacity="0.6"/>
  <circle cx="880" cy="650" r="6" fill="#2D7FF9" opacity="0.5"/>

  <!-- Top left cluster -->
  <circle cx="900" cy="300" r="7" fill="#2D7FF9" opacity="0.5"/>
  <circle cx="850" cy="350" r="5" fill="#2D7FF9" opacity="0.4"/>

  <!-- Directional convergence paths - one highlighted route -->
  <path d="M 900 300 Q 1050 350 1200 450"
        stroke="#2D7FF9"
        stroke-width="3"
        stroke-linecap="round"
        opacity="0.8"/>

  <path d="M 1500 250 Q 1350 350 1200 450"
        stroke="#2D7FF9"
        stroke-width="2"
        stroke-linecap="round"
        opacity="0.4"/>

  <path d="M 950 680 Q 1075 565 1200 450"
        stroke="#2D7FF9"
        stroke-width="2"
        stroke-linecap="round"
        opacity="0.4"/>

  <path d="M 1450 650 Q 1325 550 1200 450"
        stroke="#2D7FF9"
        stroke-width="2"
        stroke-linecap="round"
        opacity="0.4"/>

  <!-- Central OWNEX mark (scaled for hero) -->
  <g transform="translate(1150, 400) scale(0.8)">
    <circle cx="62.5" cy="62.5" r="50"
            fill="none"
            stroke="#2D7FF9"
            stroke-width="6"
            opacity="0.9"/>
    <circle cx="62.5" cy="62.5" r="32"
            fill="none"
            stroke="#2D7FF9"
            stroke-width="4"
            opacity="0.7"/>
    <circle cx="62.5" cy="62.5" r="12"
            fill="#2D7FF9"/>
    <path d="M 62.5 12.5 L 62.5 50.5"
          stroke="#2D7FF9"
          stroke-width="4"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 62.5 74.5 L 62.5 112.5"
          stroke="#2D7FF9"
          stroke-width="4"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 12.5 62.5 L 50.5 62.5"
          stroke="#2D7FF9"
          stroke-width="4"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 74.5 62.5 L 112.5 62.5"
          stroke="#2D7FF9"
          stroke-width="4"
          stroke-linecap="round"
          opacity="0.8"/>
    <circle cx="62.5" cy="12.5" r="6" fill="#2D7FF9"/>
    <circle cx="62.5" cy="112.5" r="6" fill="#2D7FF9"/>
    <circle cx="12.5" cy="62.5" r="6" fill="#2D7FF9"/>
    <circle cx="112.5" cy="62.5" r="6" fill="#2D7FF9"/>
  </g>

  <!-- Subtle gold accent line - premium touch -->
  <line x1="200" y1="850" x2="2200" y2="850"
        stroke="url(#gold-accent)"
        stroke-width="1"
        opacity="0.3"/>

  <!-- Technical annotation dots - very subtle -->
  <circle cx="200" cy="850" r="2" fill="#D4AF37" opacity="0.4"/>
  <circle cx="2200" cy="850" r="2" fill="#D4AF37" opacity="0.4"/>

  <!--OWNEX wordmark -->
  <text x="1200" y="800"
        text-anchor="middle"
        font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
        font-size="48"
        font-weight="700"
        letter-spacing="8"
        fill="#FFFFFF"
        opacity="0.9">
    OWNEX
  </text>

  <!-- Subtitle -->
  <text x="1200" y="860"
        text-anchor="middle"
        font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
        font-size="24"
        font-weight="400"
        letter-spacing="4"
        fill="#FFFFFF"
        opacity="0.6">
    AUTONOMOUS WORK OPERATING SYSTEM
  </text>
</svg>"""
    return svg


def main():
    """Generate hero banner"""
    banners_dir = Path("docs/assets/branding/banners")
    banners_dir.mkdir(parents=True, exist_ok=True)

    hero_svg = generate_hero()
    hero_path = banners_dir / "ownex-hero-banner.svg"
    hero_path.write_text(hero_svg, encoding="utf-8")
    print(f"Generated hero: {hero_path}")

    # Also generate PNG version using cairosvg if available
    try:
        import cairosvg

        png_path = banners_dir / "ownex-hero-banner.png"
        cairosvg.svg2png(url=str(hero_path), write_to=str(png_path), output_width=2400, output_height=900)
        print(f"Generated PNG: {png_path}")
    except ImportError:
        print("cairosvg not available, SVG only")


if __name__ == "__main__":
    main()
