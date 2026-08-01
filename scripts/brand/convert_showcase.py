#!/usr/bin/env python3
"""
Convert showcase SVGs to PNG format
"""

import os
from pathlib import Path
import cairosvg

def svg_to_png(svg_path, png_path, width=None, height=None):
    """Convert SVG to PNG"""
    svg_path = Path(svg_path)
    png_path = Path(png_path)
    png_path.parent.mkdir(parents=True, exist_ok=True)

    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(png_path),
        output_width=width,
        output_height=height
    )
    print(f"Converted: {svg_path.name} → {png_path.name}")

def main():
    """Convert all showcase SVGs to PNG"""
    concepts_dir = Path("assets/concepts")

    # Showcase sizes
    desktop_size = 1200
    mobile_size = 400

    # Convert showcases
    showcase_files = [
        'desktop-showcase.svg',
        'mobile-showcase.svg',
    ]

    for showcase_name in showcase_files:
        svg_file = concepts_dir / showcase_name
        if svg_file.exists():
            try:
                if 'desktop' in showcase_name:
                    svg_to_png(svg_file, concepts_dir / showcase_name.replace('.svg', '.png'), desktop_size)
                elif 'mobile' in showcase_name:
                    svg_to_png(svg_file, concepts_dir / showcase_name.replace('.svg', '.png'), mobile_size)
            except Exception as e:
                print(f"Error converting {showcase_name}: {e}")

    print("\n✓ All showcase SVGs converted to PNG successfully")

if __name__ == "__main__":
    main()
