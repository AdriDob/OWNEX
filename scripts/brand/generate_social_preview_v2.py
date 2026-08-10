#!/usr/bin/env python3
"""
OWNEX Social Preview Generator v2
Creates 1200×630 Open Graph image for social sharing
"""

from pathlib import Path


def generate_social_preview():
    """
    Create social preview with OWNEX branding
    Clean, professional, optimized for social platforms
    """
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630">
  <defs>
    <!-- Premium gradient background -->
    <linearGradient id="social-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0B0B0B;stop-opacity:1" />
      <stop offset="50%" style="stop-color:#111115;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0B0B0B;stop-opacity:1" />
    </linearGradient>

    <!-- Blue gradient for elements -->
    <linearGradient id="social-blue" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#2D7FF9;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1E40FF;stop-opacity:1" />
    </linearGradient>

    <!-- Subtle glow -->
    <radialGradient id="social-glow" cx="50%" cy="40%" r="40%">
      <stop offset="0%" style="stop-color:#2D7FF9;stop-opacity:0.15" />
      <stop offset="100%" style="stop-color:#2D7FF9;stop-opacity:0" />
    </radialGradient>
  </defs>

  <!-- Background -->
  <rect width="1200" height="630" fill="url(#social-bg)"/>

  <!-- Subtle glow area -->
  <ellipse cx="600" cy="250" rx="300" ry="200" fill="url(#social-glow)"/>

  <!-- OWNEX mark (centered and scaled) -->
  <g transform="translate(540, 180) scale(0.6)">
    <circle cx="100" cy="100" r="80"
            fill="none"
            stroke="url(#social-blue)"
            stroke-width="8"
            opacity="0.9"/>
    <circle cx="100" cy="100" r="52"
            fill="none"
            stroke="url(#social-blue)"
            stroke-width="5"
            opacity="0.7"/>
    <circle cx="100" cy="100" r="20"
            fill="url(#social-blue)"/>
    <path d="M 100 20 L 100 80"
          stroke="url(#social-blue)"
          stroke-width="6"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 100 120 L 100 180"
          stroke="url(#social-blue)"
          stroke-width="6"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 20 100 L 80 100"
          stroke="url(#social-blue)"
          stroke-width="6"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 120 100 L 180 100"
          stroke="url(#social-blue)"
          stroke-width="6"
          stroke-linecap="round"
          opacity="0.8"/>
    <circle cx="100" cy="20" r="10" fill="#2D7FF9"/>
    <circle cx="100" cy="180" r="10" fill="#2D7FF9"/>
    <circle cx="20" cy="100" r="10" fill="#2D7FF9"/>
    <circle cx="180" cy="100" r="10" fill="#2D7FF9"/>
  </g>

  <!-- OWNEX wordmark -->
  <text x="600" y="420"
        text-anchor="middle"
        font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
        font-size="72"
        font-weight="700"
        letter-spacing="4"
        fill="url(#social-blue)">
    OWNEX
  </text>

  <!-- Tagline -->
  <text x="600" y="490"
        text-anchor="middle"
        font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
        font-size="28"
        font-weight="400"
        letter-spacing="2"
        fill="#FFFFFF"
        opacity="0.8">
    Autonomous Work Operating System
  </text>

  <!-- Subtle technical elements -->
  <line x1="100" y1="580" x2="1100" y2="580"
        stroke="#2D7FF9"
        stroke-width="1"
        opacity="0.2"/>

  <circle cx="100" cy="580" r="3" fill="#2D7FF9" opacity="0.4"/>
  <circle cx="1100" cy="580" r="3" fill="#2D7FF9" opacity="0.4"/>

  <!-- Corner accent dots -->
  <circle cx="50" cy="50" r="2" fill="#2D7FF9" opacity="0.3"/>
  <circle cx="1150" cy="50" r="2" fill="#2D7FF9" opacity="0.3"/>
  <circle cx="50" cy="580" r="2" fill="#2D7FF9" opacity="0.3"/>
  <circle cx="1150" cy="580" r="2" fill="#2D7FF9" opacity="0.3"/>
</svg>"""
    return svg


def main():
    """Generate social preview"""
    social_dir = Path("docs/assets/branding/social")
    social_dir.mkdir(parents=True, exist_ok=True)

    social_svg = generate_social_preview()
    social_path = social_dir / "ownex-social-preview.svg"
    social_path.write_text(social_svg, encoding="utf-8")
    print(f"Generated social preview: {social_path}")

    # Generate PNG version
    try:
        import cairosvg

        png_path = social_dir / "ownex-social-preview.png"
        cairosvg.svg2png(url=str(social_path), write_to=str(png_path), output_width=1200, output_height=630)
        print(f"Generated PNG: {png_path}")
    except ImportError:
        print("cairosvg not available, SVG only")


if __name__ == "__main__":
    main()
