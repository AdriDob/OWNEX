#!/usr/bin/env python3
"""
Generate social preview images for GitHub with premium branding
"""

import os
from pathlib import Path

# Brand colors from new identity
COLORS = {
    "cosmos": "#08090A",
    "surface": "#111113",
    "surface_alt": "#1F2023",
    "text_primary": "#F6F8FB",
    "text_secondary": "#8B8D98",
    "accent": "#5E6AD2",
    "accent_hover": "#7B85E0",
    "success": "#00E39A",
    "white": "#FFFFFF",
    "black": "#000000",
}


def create_github_social_preview():
    """Creates GitHub social preview image"""
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="1280" height="640" viewBox="0 0 1280 640" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="1280" height="640" fill="{COLORS["cosmos"]}"/>

  <!-- Geometric mark (large, subtle) -->
  <g opacity="0.05">
    <circle cx="640" cy="320" r="220" stroke="{COLORS["text_primary"]}" stroke-width="30" fill="none"/>
    <path d="M640 100 L640 220 L840 320 L640 420 L640 520 L440 320 L640 100 Z" fill="{COLORS["text_primary"]}"/>
    <circle cx="640" cy="320" r="55" fill="{COLORS["cosmos"]}" stroke="{COLORS["text_primary"]}" stroke-width="15"/>
  </g>

  <!-- Content -->
  <g transform="translate(640, 320)">
    <!-- Wordmark -->
    <text x="0" y="20" text-anchor="middle" font-family="'Inter Display', 'Inter', system-ui, sans-serif" font-weight="700" font-size="90" letter-spacing="-0.02em" fill="{COLORS["text_primary"]}">OWNEX</text>

    <!-- Tagline -->
    <text x="0" y="70" text-anchor="middle" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="24" letter-spacing="0.02em" fill="{COLORS["text_secondary"]}">The Personalized Autonomous Operating System</text>

    <!-- Accent line -->
    <rect x="-100" y="100" width="200" height="2" fill="{COLORS["accent"]}"/>
  </g>
</svg>"""
    return svg


def save_svg(svg_content, filepath):
    """Save SVG content to file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(svg_content)
    print(f"Created: {filepath}")


def convert_svg_to_png(svg_path, png_path, width=1280, height=640):
    """Convert SVG to PNG using cairosvg"""
    try:
        import cairosvg

        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=width, output_height=height)
        print(f"Converted: {svg_path.name} → {png_path.name}")
    except ImportError:
        print("cairosvg not available, skipping PNG conversion")


def main():
    """Generate social preview assets"""
    output_dir = Path(".github")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating social preview assets...")
    svg_path = output_dir / "social-preview.svg"
    save_svg(create_github_social_preview(), svg_path)

    # Convert to PNG
    png_path = output_dir / "social-preview.png"
    convert_svg_to_png(svg_path, png_path)

    print("\n✓ Social preview assets generated successfully")
    print(f"Output directory: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
