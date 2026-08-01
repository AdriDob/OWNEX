#!/usr/bin/env python3
"""
Convert banner SVGs to PNG format
"""

from pathlib import Path

import cairosvg


def svg_to_png(svg_path, png_path, width=None, height=None):
    """Convert SVG to PNG"""
    svg_path = Path(svg_path)
    png_path = Path(png_path)
    png_path.parent.mkdir(parents=True, exist_ok=True)

    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=width, output_height=height)
    print(f"Converted: {svg_path.name} → {png_path.name}")


def main():
    """Convert all banner SVGs to PNG"""
    banners_dir = Path("assets/banners")

    # Banner sizes
    banner_size = 2400
    og_size = 1200

    # Convert banners
    premium_banners = [
        "hero-banner-unified.svg",
        "hero-banner-alpha.svg",
        "hero-banner-omega.svg",
        "og-cover.svg",
    ]

    for banner_name in premium_banners:
        svg_file = banners_dir / banner_name
        if svg_file.exists():
            try:
                if "og-cover" in banner_name:
                    svg_to_png(svg_file, banners_dir / banner_name.replace(".svg", ".png"), og_size)
                else:
                    svg_to_png(svg_file, banners_dir / banner_name.replace(".svg", ".png"), banner_size)
            except Exception as e:
                print(f"Error converting {banner_name}: {e}")

    print("\n✓ All banner SVGs converted to PNG successfully")


if __name__ == "__main__":
    main()
