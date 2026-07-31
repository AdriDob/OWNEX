"""Convert OWNEX SVG concepts to high-quality PNG images."""

from pathlib import Path
import cairosvg

CONCEPTS_DIR = Path(".ai/brand/concepts")
OUTPUT_DIR = Path("assets/branding/concepts-png")
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
for svg_file in (CONCEPTS_DIR / "logos").glob("*.svg"):
    output_file = OUTPUT_DIR / f"logo_{svg_file.stem}.png"
    convert_svg_to_png(svg_file, output_file, width=800)

# Convert heroes
for svg_file in (CONCEPTS_DIR / "heroes").glob("*.svg"):
    output_file = OUTPUT_DIR / f"hero_{svg_file.stem}.png"
    convert_svg_to_png(svg_file, output_file, width=1200)

# Convert icons
for svg_file in (CONCEPTS_DIR / "icons").glob("*.svg"):
    output_file = OUTPUT_DIR / f"icon_{svg_file.stem}.png"
    convert_svg_to_png(svg_file, output_file, width=400)

print(f"\nAll concepts converted to PNG in: {OUTPUT_DIR}")
