"""Convert hero banner to PNG."""

from pathlib import Path
import cairosvg

BANNERS_DIR = Path("assets/branding/banners")
BRANDING_DIR = Path("assets/branding")

(BRANDING_DIR / "banners_png").mkdir(parents=True, exist_ok=True)

def convert_svg_to_png(svg_path: Path, output_path: Path, width: int = 1600) -> None:
    """Convert SVG to PNG with specified width."""
    try:
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(output_path),
            output_width=width,
        )
        print(f"✓ Converted: {svg_path.name} -> {output_path.name}")
    except Exception as e:
        print(f"❌ Error converting {svg_path.name}: {e}")

convert_svg_to_png(BANNERS_DIR / "hero_banner_v2.svg", BRANDING_DIR / "banners_png" / "hero_banner_v2.png", width=1600)

print(f"\nHero banner converted to PNG in: {BRANDING_DIR / 'banners_png'}")
