"""Convert all v2 concepts to PNG using cairosvg."""

from pathlib import Path
import cairosvg

CONCEPTS_DIR = Path("assets/branding/concepts")
BRANDING_DIR = Path("assets/branding")

(BRANDING_DIR / "concepts_png").mkdir(parents=True, exist_ok=True)

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

# Convert all concepts
convert_svg_to_png(CONCEPTS_DIR / "product_overview_v2.svg", BRANDING_DIR / "concepts_png" / "product_overview_v2.png", width=1600)
convert_svg_to_png(CONCEPTS_DIR / "mission_control_v2.svg", BRANDING_DIR / "concepts_png" / "mission_control_v2.png", width=1600)
convert_svg_to_png(CONCEPTS_DIR / "architecture_diagram_v2.svg", BRANDING_DIR / "concepts_png" / "architecture_diagram_v2.png", width=1600)
convert_svg_to_png(CONCEPTS_DIR / "mobile_experience_v2.svg", BRANDING_DIR / "concepts_png" / "mobile_experience_v2.png", width=1600)
convert_svg_to_png(CONCEPTS_DIR / "boot_sequence_v2.svg", BRANDING_DIR / "concepts_png" / "boot_sequence_v2.png", width=1600)

print(f"\nAll concepts converted to PNG in: {BRANDING_DIR / 'concepts_png'}")
