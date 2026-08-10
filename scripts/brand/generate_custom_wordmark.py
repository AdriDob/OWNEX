#!/usr/bin/env python3
"""
OWNEX Custom Wordmark Generator
Creates a custom wordmark with subtle geometry modifications to O and X
"""

from pathlib import Path


def generate_custom_wordmark(color="#FFFFFF"):
    """
    Generate custom OWNEX wordmark with subtle geometry modifications
    - O: Suggests a node/portal/nucleus with subtle inner dot
    - X: Suggests intersection/convergence with subtle terminal weights
    - Spacing: Generous but controlled, engineered feel
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 80" width="400" height="80">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&amp;display=swap');
      .ownex-wordmark {{
        font-family: 'Sora', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-weight: 700;
        font-size: 64px;
        letter-spacing: 0.08em;
        fill: {color};
      }}
    </style>
  </defs>

  <!-- Custom O with subtle inner node suggestion -->
  <text x="0" y="64" class="ownex-wordmark">O</text>
  <!-- Subtle inner dot in O to suggest nucleus/node -->
  <circle cx="32" cy="32" r="3" fill="{color}" opacity="0.6"/>

  <!-- W with standard geometry -->
  <text x="80" y="64" class="ownex-wordmark">W</text>

  <!-- N with standard geometry -->
  <text x="160" y="64" class="ownex-wordmark">N</text>

  <!-- E with standard geometry -->
  <text x="240" y="64" class="ownex-wordmark">E</text>

  <!-- Custom X with subtle intersection weights -->
  <text x="320" y="64" class="ownex-wordmark">X</text>
  <!-- Subtle convergence suggestion in X -->
  <circle cx="352" cy="32" r="2" fill="{color}" opacity="0.4"/>
</svg>"""
    return svg


def generate_path_based_wordmark(color="#FFFFFF"):
    """
    Generate wordmark using SVG paths for maximum control
    This allows precise geometry control without font dependencies
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 80" width="400" height="80">
  <!-- O: Suggests node/portal with inner nucleus -->
  <g transform="translate(32, 40)">
    <circle cx="0" cy="0" r="24" fill="none" stroke="{color}" stroke-width="6"/>
    <circle cx="0" cy="0" r="4" fill="{color}" opacity="0.6"/>
  </g>

  <!-- W: Technical precision -->
  <g transform="translate(96, 40)">
    <path d="M -24 -20 L -12 20 L 0 -5 L 12 20 L 24 -20" 
          fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
  </g>

  <!-- N: Angular, precise -->
  <g transform="translate(168, 40)">
    <path d="M -24 -20 L -24 20 L 24 -20 L 24 20" 
          fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
  </g>

  <!-- E: Horizontal bars -->
  <g transform="translate(240, 40)">
    <path d="M -24 -20 L 24 -20 M -24 0 L 16 0 M -24 20 L 24 20" 
          fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
  </g>

  <!-- X: Intersection/convergence -->
  <g transform="translate(320, 40)">
    <path d="M -20 -20 L 20 20 M 20 -20 L -20 20" 
          fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
    <circle cx="0" cy="0" r="3" fill="{color}" opacity="0.4"/>
  </g>
</svg>"""
    return svg


def generate_descriptor():
    """Generate AUTONOMOUS WORK OPERATING SYSTEM descriptor"""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 30" width="500" height="30">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&amp;display=swap');
      .descriptor {{
        font-family: 'Sora', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-weight: 500;
        font-size: 16px;
        letter-spacing: 0.12em;
        fill: #888888;
      }}
    </style>
  </defs>
  <text x="0" y="22" class="descriptor">AUTONOMOUS WORK OPERATING SYSTEM</text>
</svg>"""
    return svg


def main():
    """Generate all wordmark variants"""
    logo_dir = Path("docs/assets/branding/logo")
    logo_dir.mkdir(parents=True, exist_ok=True)

    # Custom wordmark variants
    variants = {
        "ownex-wordmark-custom.svg": generate_custom_wordmark("#FFFFFF"),
        "ownex-wordmark-custom-white.svg": generate_custom_wordmark("#FFFFFF"),
        "ownex-wordmark-custom-black.svg": generate_custom_wordmark("#0B0B0B"),
        "ownex-wordmark-custom-blue.svg": generate_custom_wordmark("#2D7FF9"),
        "ownex-wordmark-path.svg": generate_path_based_wordmark("#FFFFFF"),
        "ownex-wordmark-path-white.svg": generate_path_based_wordmark("#FFFFFF"),
        "ownex-wordmark-path-black.svg": generate_path_based_wordmark("#0B0B0B"),
        "ownex-wordmark-path-blue.svg": generate_path_based_wordmark("#2D7FF9"),
        "ownex-descriptor.svg": generate_descriptor(),
    }

    for filename, content in variants.items():
        filepath = logo_dir / filename
        filepath.write_text(content, encoding="utf-8")
        print(f"Generated: {filepath}")

    # Convert to PNG
    try:
        import cairosvg
        for filename in variants.keys():
            if not filename.endswith('-descriptor.svg'):
                svg_path = logo_dir / filename
                png_path = logo_dir / filename.replace('.svg', '.png')
                try:
                    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=400, output_height=80)
                    print(f"Generated PNG: {png_path}")
                except Exception as e:
                    print(f"Error converting {filename}: {e}")
    except ImportError:
        print("cairosvg not available, SVG only")


if __name__ == "__main__":
    main()