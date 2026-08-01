#!/usr/bin/env python3
"""
Convert SVG logos to PNG format using cairosvg
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
    """Convert all SVG logos to PNG"""
    logos_dir = Path("assets/logos")

    # Standard sizes
    sizes = {
        "favicon": 32,
        "icon": 512,
        "standard": 1024,
    }

    # Only convert the new premium logos
    premium_logos = [
        "ownex-mark.svg",
        "ownex-mark-black.svg",
        "ownex-mark-white.svg",
        "ownex-wordmark.svg",
        "ownex-wordmark-black.svg",
        "ownex-wordmark-white.svg",
        "ownex-lockup.svg",
        "ownex-lockup-black.svg",
        "ownex-lockup-white.svg",
        "ownex-alpha.svg",
        "ownex-alpha-black.svg",
        "ownex-alpha-white.svg",
        "ownex-omega.svg",
        "ownex-omega-black.svg",
        "ownex-omega-white.svg",
        "ownex-favicon.svg",
        "ownex-favicon-black.svg",
        "ownex-favicon-white.svg",
        "ownex-icon.svg",
        "ownex-icon-accent.svg",
        "ownex-icon-alpha.svg",
        "ownex-icon-omega.svg",
    ]

    for logo_name in premium_logos:
        svg_file = logos_dir / logo_name
        if svg_file.exists():
            try:
                if "favicon" in logo_name:
                    svg_to_png(svg_file, logos_dir / logo_name.replace(".svg", ".png"), sizes["favicon"])
                elif "icon" in logo_name:
                    svg_to_png(svg_file, logos_dir / logo_name.replace(".svg", ".png"), sizes["icon"])
                else:
                    svg_to_png(svg_file, logos_dir / logo_name.replace(".svg", ".png"), sizes["standard"])
            except Exception as e:
                print(f"Error converting {logo_name}: {e}")

    print("\n✓ All premium SVGs converted to PNG successfully")


if __name__ == "__main__":
    main()
