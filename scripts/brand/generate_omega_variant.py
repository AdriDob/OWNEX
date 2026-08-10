#!/usr/bin/env python3
"""
OWNEX OMEGA Variant Generator
Creates the OMEGA variant of the OWNEX symbol
OMEGA represents infinity, completeness, and the final/ultimate state
"""

from pathlib import Path


def generate_omega_mark(color="#FFFFFF"):
    """
    Generate OMEGA variant - OWNEX mark with omega (Ω) geometry suggestion
    The omega shape suggests infinity, convergence, and ultimate completeness
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="omega-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#2D7FF9;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1E40FF;stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Main orbital ring (omega shape suggestion) -->
  <path d="M 256 76 C 140 76 76 140 76 256 C 76 372 140 436 256 436 C 372 436 436 372 436 256 C 436 140 372 76 256 76"
        fill="none"
        stroke="url(#omega-gradient)"
        stroke-width="12"
        opacity="0.9"/>

  <!-- Inner omega path (suggesting infinity) -->
  <path d="M 256 156 C 180 156 156 180 156 256 C 156 332 180 356 256 356 C 332 356 356 332 356 256 C 356 180 332 156 256 156"
        fill="none"
        stroke="url(#omega-gradient)"
        stroke-width="8"
        opacity="0.7"/>

  <!-- Central nucleus (infinity point) -->
  <circle cx="256" cy="256" r="30" fill="url(#omega-gradient)"/>

  <!-- Omega arms - extending to cardinal directions -->
  <path d="M 256 76 L 256 156" stroke="url(#omega-gradient)" stroke-width="8" stroke-linecap="round" opacity="0.8"/>
  <path d="M 256 356 L 256 436" stroke="url(#omega-gradient)" stroke-width="8" stroke-linecap="round" opacity="0.8"/>
  <path d="M 76 256 L 156 256" stroke="url(#omega-gradient)" stroke-width="8" stroke-linecap="round" opacity="0.8"/>
  <path d="M 356 256 L 436 256" stroke="url(#omega-gradient)" stroke-width="8" stroke-linecap="round" opacity="0.8"/>

  <!-- Opportunity nodes at omega terminals -->
  <circle cx="256" cy="76" r="16" fill="{color}"/>
  <circle cx="256" cy="436" r="16" fill="{color}"/>
  <circle cx="76" cy="256" r="16" fill="{color}"/>
  <circle cx="436" cy="256" r="16" fill="{color}"/>

  <!-- Diagonal convergence paths (infinity lines) -->
  <path d="M 156 156 L 256 256" stroke="url(#omega-gradient)" stroke-width="4" stroke-linecap="round" opacity="0.4"/>
  <path d="M 356 156 L 256 256" stroke="url(#omega-gradient)" stroke-width="4" stroke-linecap="round" opacity="0.4"/>
  <path d="M 156 356 L 256 256" stroke="url(#omega-gradient)" stroke-width="4" stroke-linecap="round" opacity="0.4"/>
  <path d="M 356 356 L 256 256" stroke="url(#omega-gradient)" stroke-width="4" stroke-linecap="round" opacity="0.4"/>

  <!-- Small omega suggestion at center -->
  <path d="M 256 226 C 236 226 226 236 226 256 C 226 276 236 286 256 286 C 276 286 286 276 286 256 C 286 236 276 226 256 226"
        fill="none"
        stroke="{color}"
        stroke-width="3"
        opacity="0.5"/>
</svg>"""
    return svg


def generate_omega_wordmark(color="#FFFFFF"):
    """Generate OMEGA wordmark variant"""
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 80" width="500" height="80">
  <defs>
    <linearGradient id="omega-wordmark-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#2D7FF9;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1E40FF;stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- O with omega suggestion -->
  <g transform="translate(40, 40)">
    <circle cx="0" cy="0" r="24" fill="none" stroke="{color}" stroke-width="6"/>
    <circle cx="0" cy="0" r="4" fill="{color}" opacity="0.6"/>
    <!-- Small omega in center -->
    <path d="M 0 -12 C -8 -12 -12 -8 -12 0 C -12 8 -8 12 0 12 C 8 12 12 8 12 0 C 12 -8 8 -12 0 -12"
          fill="none" stroke="{color}" stroke-width="2" opacity="0.5"/>
  </g>

  <!-- W with standard geometry -->
  <g transform="translate(104, 40)">
    <path d="M -24 -20 L -12 20 L 0 -5 L 12 20 L 24 -20"
          fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
  </g>

  <!-- N with standard geometry -->
  <g transform="translate(176, 40)">
    <path d="M -24 -20 L -24 20 L 24 -20 L 24 20"
          fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
  </g>

  <!-- E with standard geometry -->
  <g transform="translate(248, 40)">
    <path d="M -24 -20 L 24 -20 M -24 0 L 16 0 M -24 20 L 24 20"
          fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
  </g>

  <!-- X with omega-style convergence -->
  <g transform="translate(328, 40)">
    <path d="M -20 -20 L 20 20 M 20 -20 L -20 20"
          fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
    <!-- Omega convergence suggestion -->
    <circle cx="0" cy="0" r="3" fill="{color}" opacity="0.4"/>
  </g>

  <!-- OMEGA accent (small omega symbol) -->
  <g transform="translate(400, 40)">
    <path d="M 0 -12 C -8 -12 -12 -8 -12 0 C -12 8 -8 12 0 12 C 8 12 12 8 12 0 C 12 -8 8 -12 0 -12"
          fill="none" stroke="url(#omega-wordmark-gradient)" stroke-width="3"/>
  </g>
</svg>"""
    return svg


def main():
    """Generate OMEGA variants"""
    logo_dir = Path("docs/assets/branding/logo")
    logo_dir.mkdir(parents=True, exist_ok=True)

    variants = {
        "ownex-mark-omega.svg": generate_omega_mark("#FFFFFF"),
        "ownex-mark-omega-white.svg": generate_omega_mark("#FFFFFF"),
        "ownex-mark-omega-black.svg": generate_omega_mark("#0B0B0B"),
        "ownex-mark-omega-blue.svg": generate_omega_mark("#2D7FF9"),
        "ownex-wordmark-omega.svg": generate_omega_wordmark("#FFFFFF"),
        "ownex-wordmark-omega-white.svg": generate_omega_wordmark("#FFFFFF"),
        "ownex-wordmark-omega-black.svg": generate_omega_wordmark("#0B0B0B"),
        "ownex-wordmark-omega-blue.svg": generate_omega_wordmark("#2D7FF9"),
    }

    for filename, content in variants.items():
        filepath = logo_dir / filename
        filepath.write_text(content, encoding="utf-8")
        print(f"Generated: {filepath}")

    # Convert to PNG
    try:
        import cairosvg

        for filename, _content in variants.items():
            svg_path = logo_dir / filename
            # Determine output dimensions
            if "wordmark" in filename:
                width, height = 500, 80
            else:
                width, height = 512, 512

            png_path = logo_dir / filename.replace(".svg", ".png")
            try:
                cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=width, output_height=height)
                print(f"Generated PNG: {png_path}")
            except Exception as e:
                print(f"Error converting {filename}: {e}")
    except ImportError:
        print("cairosvg not available, SVG only")


if __name__ == "__main__":
    main()
