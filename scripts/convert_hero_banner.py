"""Convert hero banner to PNG."""

from pathlib import Path
import cairosvg

BANNERS_DIR = Path("assets/branding/banners")
PROFESSIONAL_DIR = Path("assets/branding/professional")

def convert_svg_to_png(svg_path: Path, output_path: Path, width: int = 1200) -> None:
    """Convert SVG to PNG with specified width."""
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(output_path),
        output_width=width,
    )
    print(f"Converted: {svg_path.name} -> {output_path.name}")

convert_svg_to_png(BANNERS_DIR / "cinematic_hero_banner.svg", PROFESSIONAL_DIR / "cinematic_hero_banner.png", width=1200)

print(f"\nHero banner converted to PNG in: {PROFESSIONAL_DIR}")
