"""Convert custom OWNEX logos to high-quality PNG."""

from pathlib import Path
import cairosvg

LOGOS_DIR = Path("assets/branding/logos-custom")
OUTPUT_DIR = Path("assets/branding/professional")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def convert_svg_to_png(svg_path: Path, output_path: Path, width: int = 1200) -> None:
    """Convert SVG to PNG with specified width."""
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(output_path),
        output_width=width,
    )
    print(f"Converted: {svg_path.name} -> {output_path.name}")

# Convert logos
convert_svg_to_png(LOGOS_DIR / "ownex_alpha_logo.svg", OUTPUT_DIR / "alpha_logo.png", width=800)
convert_svg_to_png(LOGOS_DIR / "ownex_omega_logo.svg", OUTPUT_DIR / "omega_logo.png", width=800)
convert_svg_to_png(LOGOS_DIR / "ai_hero_banner.svg", OUTPUT_DIR / "ai_hero_banner.png", width=1200)

print(f"\nAll custom logos converted to PNG in: {OUTPUT_DIR}")
