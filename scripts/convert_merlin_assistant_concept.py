"""Convert MERLIN Assistant concept to PNG."""

from pathlib import Path
import cairosvg

CONCEPTS_DIR = Path("assets/branding/concepts")
PROFESSIONAL_DIR = Path("assets/branding/professional")

def convert_svg_to_png(svg_path: Path, output_path: Path, width: int = 1200) -> None:
    """Convert SVG to PNG with specified width."""
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(output_path),
        output_width=width,
    )
    print(f"Converted: {svg_path.name} -> {output_path.name}")

convert_svg_to_png(CONCEPTS_DIR / "merlin_assistant_concept.svg", PROFESSIONAL_DIR / "merlin_assistant_concept.png", width=1200)

print(f"\nMERLIN Assistant concept converted to PNG in: {PROFESSIONAL_DIR}")
