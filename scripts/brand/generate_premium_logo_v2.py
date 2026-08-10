#!/usr/bin/env python3
"""
OWNEX Premium Logo Generator v2
Creates a completely new, professional logo system
"""

from pathlib import Path


def generate_ownex_mark():
    """
    Create the OWNEX mark - abstract convergence symbol
    Concept: Central node with orbital paths + directional convergence
    """
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="ownex-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#2D7FF9;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1E40FF;stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Outer orbital ring - represents autonomous navigation -->
  <circle cx="256" cy="256" r="180"
          fill="none"
          stroke="url(#ownex-gradient)"
          stroke-width="12"
          opacity="0.9"/>

  <!-- Inner orbital ring -->
  <circle cx="256" cy="256" r="120"
          fill="none"
          stroke="url(#ownex-gradient)"
          stroke-width="8"
          opacity="0.7"/>

  <!-- Central convergence node - the core intelligence -->
  <circle cx="256" cy="256" r="40"
          fill="url(#ownex-gradient)"/>

  <!-- Directional convergence paths - 4 cardinal directions -->
  <!-- Top path -->
  <path d="M 256 76 L 256 216"
        stroke="url(#ownex-gradient)"
        stroke-width="10"
        stroke-linecap="round"
        opacity="0.8"/>

  <!-- Bottom path -->
  <path d="M 256 296 L 256 436"
        stroke="url(#ownex-gradient)"
        stroke-width="10"
        stroke-linecap="round"
        opacity="0.8"/>

  <!-- Left path -->
  <path d="M 76 256 L 216 256"
        stroke="url(#ownex-gradient)"
        stroke-width="10"
        stroke-linecap="round"
        opacity="0.8"/>

  <!-- Right path -->
  <path d="M 296 256 L 436 256"
        stroke="url(#ownex-gradient)"
        stroke-width="10"
        stroke-linecap="round"
        opacity="0.8"/>

  <!-- Opportunity nodes at orbital intersections -->
  <circle cx="256" cy="76" r="16" fill="#2D7FF9"/>
  <circle cx="256" cy="436" r="16" fill="#2D7FF9"/>
  <circle cx="76" cy="256" r="16" fill="#2D7FF9"/>
  <circle cx="436" cy="256" r="16" fill="#2D7FF9"/>

  <!-- Diagonal convergence lines - subtle intelligence connections -->
  <path d="M 130 130 L 216 216"
        stroke="#2D7FF9"
        stroke-width="4"
        stroke-linecap="round"
        opacity="0.4"/>
  <path d="M 382 130 L 296 216"
        stroke="#2D7FF9"
        stroke-width="4"
        stroke-linecap="round"
        opacity="0.4"/>
  <path d="M 130 382 L 216 296"
        stroke="#2D7FF9"
        stroke-width="4"
        stroke-linecap="round"
        opacity="0.4"/>
  <path d="M 382 382 L 296 296"
        stroke="#2D7FF9"
        stroke-width="4"
        stroke-linecap="round"
        opacity="0.4"/>
</svg>"""
    return svg


def generate_ownex_wordmark():
    """
    Create the OWNEX wordmark with premium typography
    """
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 80" width="400" height="80">
  <defs>
    <linearGradient id="wordmark-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#2D7FF9;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1E40FF;stop-opacity:1" />
    </linearGradient>
  </defs>

  <text x="0" y="65"
        font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
        font-size="64"
        font-weight="700"
        letter-spacing="-2"
        fill="url(#wordmark-gradient)">
    OWNEX
  </text>
</svg>"""
    return svg


def generate_ownex_lockup():
    """
    Create the horizontal lockup (mark + wordmark)
    """
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 120" width="600" height="120">
  <defs>
    <linearGradient id="lockup-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#2D7FF9;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1E40FF;stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Mark (scaled and positioned) -->
  <g transform="translate(10, 10)">
    <circle cx="50" cy="50" r="40"
            fill="none"
            stroke="url(#lockup-gradient)"
            stroke-width="6"
            opacity="0.9"/>
    <circle cx="50" cy="50" r="26"
            fill="none"
            stroke="url(#lockup-gradient)"
            stroke-width="4"
            opacity="0.7"/>
    <circle cx="50" cy="50" r="10"
            fill="url(#lockup-gradient)"/>
    <path d="M 50 10 L 50 40"
          stroke="url(#lockup-gradient)"
          stroke-width="5"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 50 60 L 50 90"
          stroke="url(#lockup-gradient)"
          stroke-width="5"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 10 50 L 40 50"
          stroke="url(#lockup-gradient)"
          stroke-width="5"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 60 50 L 90 50"
          stroke="url(#lockup-gradient)"
          stroke-width="5"
          stroke-linecap="round"
          opacity="0.8"/>
    <circle cx="50" cy="10" r="8" fill="#2D7FF9"/>
    <circle cx="50" cy="90" r="8" fill="#2D7FF9"/>
    <circle cx="10" cy="50" r="8" fill="#2D7FF9"/>
    <circle cx="90" cy="50" r="8" fill="#2D7FF9"/>
  </g>

  <!-- Wordmark -->
  <text x="120" y="75"
        font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
        font-size="56"
        font-weight="700"
        letter-spacing="-1.5"
        fill="url(#lockup-gradient)">
    OWNEX
  </text>
</svg>"""
    return svg


def generate_mark_white():
    """Mark variant for dark backgrounds"""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <circle cx="256" cy="256" r="180"
          fill="none"
          stroke="#FFFFFF"
          stroke-width="12"
          opacity="0.9"/>
  <circle cx="256" cy="256" r="120"
          fill="none"
          stroke="#FFFFFF"
          stroke-width="8"
          opacity="0.7"/>
  <circle cx="256" cy="256" r="40"
          fill="#FFFFFF"/>
  <path d="M 256 76 L 256 216"
        stroke="#FFFFFF"
        stroke-width="10"
        stroke-linecap="round"
        opacity="0.8"/>
  <path d="M 256 296 L 256 436"
        stroke="#FFFFFF"
        stroke-width="10"
        stroke-linecap="round"
        opacity="0.8"/>
  <path d="M 76 256 L 216 256"
        stroke="#FFFFFF"
        stroke-width="10"
        stroke-linecap="round"
        opacity="0.8"/>
  <path d="M 296 256 L 436 256"
        stroke="#FFFFFF"
        stroke-width="10"
        stroke-linecap="round"
        opacity="0.8"/>
  <circle cx="256" cy="76" r="16" fill="#FFFFFF"/>
  <circle cx="256" cy="436" r="16" fill="#FFFFFF"/>
  <circle cx="76" cy="256" r="16" fill="#FFFFFF"/>
  <circle cx="436" cy="256" r="16" fill="#FFFFFF"/>
  <path d="M 130 130 L 216 216"
        stroke="#FFFFFF"
        stroke-width="4"
        stroke-linecap="round"
        opacity="0.4"/>
  <path d="M 382 130 L 296 216"
        stroke="#FFFFFF"
        stroke-width="4"
        stroke-linecap="round"
        opacity="0.4"/>
  <path d="M 130 382 L 216 296"
        stroke="#FFFFFF"
        stroke-width="4"
        stroke-linecap="round"
        opacity="0.4"/>
  <path d="M 382 382 L 296 296"
        stroke="#FFFFFF"
        stroke-width="4"
        stroke-linecap="round"
        opacity="0.4"/>
</svg>"""
    return svg


def generate_mark_black():
    """Mark variant for light backgrounds"""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <circle cx="256" cy="256" r="180"
          fill="none"
          stroke="#0B0B0B"
          stroke-width="12"
          opacity="0.9"/>
  <circle cx="256" cy="256" r="120"
          fill="none"
          stroke="#0B0B0B"
          stroke-width="8"
          opacity="0.7"/>
  <circle cx="256" cy="256" r="40"
          fill="#0B0B0B"/>
  <path d="M 256 76 L 256 216"
        stroke="#0B0B0B"
        stroke-width="10"
        stroke-linecap="round"
        opacity="0.8"/>
  <path d="M 256 296 L 256 436"
        stroke="#0B0B0B"
        stroke-width="10"
        stroke-linecap="round"
        opacity="0.8"/>
  <path d="M 76 256 L 216 256"
        stroke="#0B0B0B"
        stroke-width="10"
        stroke-linecap="round"
        opacity="0.8"/>
  <path d="M 296 256 L 436 256"
        stroke="#0B0B0B"
        stroke-width="10"
        stroke-linecap="round"
        opacity="0.8"/>
  <circle cx="256" cy="76" r="16" fill="#0B0B0B"/>
  <circle cx="256" cy="436" r="16" fill="#0B0B0B"/>
  <circle cx="76" cy="256" r="16" fill="#0B0B0B"/>
  <circle cx="436" cy="256" r="16" fill="#0B0B0B"/>
  <path d="M 130 130 L 216 216"
        stroke="#0B0B0B"
        stroke-width="4"
        stroke-linecap="round"
        opacity="0.4"/>
  <path d="M 382 130 L 296 216"
        stroke="#0B0B0B"
        stroke-width="4"
        stroke-linecap="round"
        opacity="0.4"/>
  <path d="M 130 382 L 216 296"
        stroke="#0B0B0B"
        stroke-width="4"
        stroke-linecap="round"
        opacity="0.4"/>
  <path d="M 382 382 L 296 296"
        stroke="#0B0B0B"
        stroke-width="4"
        stroke-linecap="round"
        opacity="0.4"/>
</svg>"""
    return svg


def generate_favicon():
    """16x16 favicon"""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">
  <circle cx="8" cy="8" r="6"
          fill="none"
          stroke="#2D7FF9"
          stroke-width="1.5"
          opacity="0.9"/>
  <circle cx="8" cy="8" r="4"
          fill="none"
          stroke="#2D7FF9"
          stroke-width="1"
          opacity="0.7"/>
  <circle cx="8" cy="8" r="1.5"
          fill="#2D7FF9"/>
  <path d="M 8 2 L 8 6"
        stroke="#2D7FF9"
        stroke-width="1"
        stroke-linecap="round"
        opacity="0.8"/>
  <path d="M 8 10 L 8 14"
        stroke="#2D7FF9"
        stroke-width="1"
        stroke-linecap="round"
        opacity="0.8"/>
  <path d="M 2 8 L 6 8"
        stroke="#2D7FF9"
        stroke-width="1"
        stroke-linecap="round"
        opacity="0.8"/>
  <path d="M 10 8 L 14 8"
        stroke="#2D7FF9"
        stroke-width="1"
        stroke-linecap="round"
        opacity="0.8"/>
</svg>"""
    return svg


def generate_lockup_white():
    """Lockup variant for dark backgrounds (includes wordmark)"""
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 120" width="600" height="120">
  <defs>
    <linearGradient id="lockup-white-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#FFFFFF;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#E0E0E0;stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Mark (scaled and positioned) -->
  <g transform="translate(10, 10)">
    <circle cx="50" cy="50" r="40"
            fill="none"
            stroke="url(#lockup-white-gradient)"
            stroke-width="6"
            opacity="0.9"/>
    <circle cx="50" cy="50" r="26"
            fill="none"
            stroke="url(#lockup-white-gradient)"
            stroke-width="4"
            opacity="0.7"/>
    <circle cx="50" cy="50" r="10"
            fill="url(#lockup-white-gradient)"/>
    <path d="M 50 10 L 50 40"
          stroke="url(#lockup-white-gradient)"
          stroke-width="5"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 50 60 L 50 90"
          stroke="url(#lockup-white-gradient)"
          stroke-width="5"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 10 50 L 40 50"
          stroke="url(#lockup-white-gradient)"
          stroke-width="5"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 60 50 L 90 50"
          stroke="url(#lockup-white-gradient)"
          stroke-width="5"
          stroke-linecap="round"
          opacity="0.8"/>
    <circle cx="50" cy="10" r="8" fill="#FFFFFF"/>
    <circle cx="50" cy="90" r="8" fill="#FFFFFF"/>
    <circle cx="10" cy="50" r="8" fill="#FFFFFF"/>
    <circle cx="90" cy="50" r="8" fill="#FFFFFF"/>
  </g>

  <!-- Wordmark -->
  <text x="120" y="75"
        font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
        font-size="56"
        font-weight="700"
        letter-spacing="-1.5"
        fill="url(#lockup-white-gradient)">
    OWNEX
  </text>
</svg>"""
    return svg


def generate_lockup_black():
    """Lockup variant for light backgrounds (includes wordmark)"""
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 120" width="600" height="120">
  <defs>
    <linearGradient id="lockup-black-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0B0B0B;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1A1A1A;stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Mark (scaled and positioned) -->
  <g transform="translate(10, 10)">
    <circle cx="50" cy="50" r="40"
            fill="none"
            stroke="url(#lockup-black-gradient)"
            stroke-width="6"
            opacity="0.9"/>
    <circle cx="50" cy="50" r="26"
            fill="none"
            stroke="url(#lockup-black-gradient)"
            stroke-width="4"
            opacity="0.7"/>
    <circle cx="50" cy="50" r="10"
            fill="url(#lockup-black-gradient)"/>
    <path d="M 50 10 L 50 40"
          stroke="url(#lockup-black-gradient)"
          stroke-width="5"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 50 60 L 50 90"
          stroke="url(#lockup-black-gradient)"
          stroke-width="5"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 10 50 L 40 50"
          stroke="url(#lockup-black-gradient)"
          stroke-width="5"
          stroke-linecap="round"
          opacity="0.8"/>
    <path d="M 60 50 L 90 50"
          stroke="url(#lockup-black-gradient)"
          stroke-width="5"
          stroke-linecap="round"
          opacity="0.8"/>
    <circle cx="50" cy="10" r="8" fill="#0B0B0B"/>
    <circle cx="50" cy="90" r="8" fill="#0B0B0B"/>
    <circle cx="10" cy="50" r="8" fill="#0B0B0B"/>
    <circle cx="90" cy="50" r="8" fill="#0B0B0B"/>
  </g>

  <!-- Wordmark -->
  <text x="120" y="75"
        font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
        font-size="56"
        font-weight="700"
        letter-spacing="-1.5"
        fill="url(#lockup-black-gradient)">
    OWNEX
  </text>
</svg>"""
    return svg


def main():
    """Generate all logo assets"""
    brand_dir = Path("docs/assets/branding/logo")
    brand_dir.mkdir(parents=True, exist_ok=True)

    # Generate all variants
    assets = {
        "ownex-mark.svg": generate_ownex_mark(),
        "ownex-mark-white.svg": generate_mark_white(),
        "ownex-mark-black.svg": generate_mark_black(),
        "ownex-wordmark.svg": generate_ownex_wordmark(),
        "ownex-lockup.svg": generate_ownex_lockup(),
        "ownex-lockup-white.svg": generate_lockup_white(),
        "ownex-lockup-black.svg": generate_lockup_black(),
        "favicon.svg": generate_favicon(),
    }

    for filename, content in assets.items():
        filepath = brand_dir / filename
        filepath.write_text(content, encoding="utf-8")
        print(f"Generated: {filepath}")


if __name__ == "__main__":
    main()
