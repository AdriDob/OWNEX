"""Convert all OWNEX logos to high-quality PNG."""

from pathlib import Path
import cairosvg

LOGOS_DIR = Path("assets/branding/logos")
PROFESSIONAL_DIR = Path("assets/branding/professional")
PROFESSIONAL_DIR.mkdir(parents=True, exist_ok=True)

def convert_svg_to_png(svg_path: Path, output_path: Path, width: int = 1200) -> None:
    """Convert SVG to PNG with specified width."""
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(output_path),
        output_width=width,
    )
    print(f"Converted: {svg_path.name} -> {output_path.name}")

# Convert main logos
convert_svg_to_png(LOGOS_DIR / "ownex_main_logo.svg", PROFESSIONAL_DIR / "ownex_main_logo.png", width=800)
convert_svg_to_png(LOGOS_DIR / "ownex_icon.svg", PROFESSIONAL_DIR / "ownex_icon.png", width=256)
convert_svg_to_png(LOGOS_DIR / "ownex_app_icon.svg", PROFESSIONAL_DIR / "ownex_app_icon.png", width=512)
convert_svg_to_png(LOGOS_DIR / "ownex_favicon.svg", PROFESSIONAL_DIR / "ownex_favicon.png", width=64)
convert_svg_to_png(LOGOS_DIR / "ownex_monogram.svg", PROFESSIONAL_DIR / "ownex_monogram.png", width=256)

# Convert ALPHA and OMEGA logos
convert_svg_to_png(LOGOS_DIR / "ownex_alpha_logo.svg", PROFESSIONAL_DIR / "alpha_logo.png", width=800)
convert_svg_to_png(LOGOS_DIR / "ownex_omega_logo.svg", PROFESSIONAL_DIR / "omega_logo.png", width=800)

print(f"\nAll logos converted to PNG in: {PROFESSIONAL_DIR}")
