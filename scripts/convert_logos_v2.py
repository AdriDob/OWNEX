"""Convert all v2 logos to PNG using cairosvg."""

from pathlib import Path
import cairosvg

LOGOS_DIR = Path("assets/branding/logos")
BRANDING_DIR = Path("assets/branding")

# Create output directories
(BRANDING_DIR / "logos_png").mkdir(parents=True, exist_ok=True)
(BRANDING_DIR / "logos_ui").mkdir(parents=True, exist_ok=True)

def convert_svg_to_png(svg_path: Path, output_path: Path, width: int = 512) -> None:
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

# Convert main logos to 512px
for logo_name in ["ownex_main_logo_v2", "alpha_logo_v2", "omega_logo_v2", "ownex_app_icon_v2"]:
    svg_path = LOGOS_DIR / f"{logo_name}.svg"
    png_path = BRANDING_DIR / "logos_png" / f"{logo_name}.png"
    convert_svg_to_png(svg_path, png_path, width=512)

# Convert small logos to 64px
for logo_name in ["ownex_favicon_v2", "ownex_ui_32px_v2"]:
    svg_path = LOGOS_DIR / f"{logo_name}.svg"
    png_path = BRANDING_DIR / "logos_ui" / f"{logo_name}.png"
    convert_svg_to_png(svg_path, png_path, width=64)

# Convert monochrome and transparent to 512px
for logo_name in ["ownex_monochrome_v2", "ownex_transparent_v2"]:
    svg_path = LOGOS_DIR / f"{logo_name}.svg"
    png_path = BRANDING_DIR / "logos_png" / f"{logo_name}.png"
    convert_svg_to_png(svg_path, png_path, width=512)

print(f"\nAll logos converted to PNG in:")
print(f"  - {BRANDING_DIR / 'logos_png/'} (512px)")
print(f"  - {BRANDING_DIR / 'logos_ui/'} (64px)")
