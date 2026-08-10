#!/usr/bin/env python3
"""Generate light-mode screenshots from dark -demo files by color mapping.

Maps Tesla dark palette → light palette:
  #05060A, #0b0b0b, #0f0f0f → #f6f8fa (background)
  #1a1a1a, #131313 → #ffffff (surfaces)
  #2869cb → #0969da (accent blue)
  #e82127 → #e82127 (accent red - unchanged)
Text dark → light text colors.
"""

from __future__ import annotations

from PIL import Image
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DARK_DIR = ROOT / "docs/assets/screenshots/desktop"
LIGHT_DIR = ROOT / "docs/assets/screenshots/desktop-light"
LIGHT_DIR.mkdir(parents=True, exist_ok=True)

# Color mapping: dark RGB → light RGB
DARK_TO_LIGHT = {
    # Backgrounds
    (5, 6, 10): (246, 248, 250),      # #05060A → #f6f8fa
    (11, 11, 11): (246, 248, 250),    # #0b0b0b → #f6f8fa
    (15, 15, 15): (246, 248, 250),    # #0f0f0f → #f6f8fa
    (14, 14, 16): (255, 255, 255),    # #0e0e10 → #ffffff
    # Surfaces
    (26, 26, 26): (255, 255, 255),    # #1a1a1a → #ffffff
    (19, 19, 19): (255, 255, 255),    # #131313 → #ffffff
    (18, 18, 18): (255, 255, 255),    # #121212 → #ffffff
    (19, 19, 20): (255, 255, 255),    # #131314 → #ffffff
    (20, 20, 22): (255, 255, 255),    # #141416 → #ffffff
    # Borders / muted
    (40, 40, 50): (208, 215, 222),    # dark border → #d0d7de
    (50, 50, 60): (208, 215, 222),
    # Accent blue
    (40, 105, 203): (9, 105, 218),    # #2869cb → #0969da
    # Accent red - keep
    (232, 33, 39): (232, 33, 39),     # #e82127 → #e82127
    # Gold
    (154, 103, 0): (154, 103, 0),     # #9a6700 → #9a6700
    # Text colors (dark greys → dark text on light bg)
    (31, 35, 40): (31, 35, 40),       # #1f2328 → #1f2328 (primary text)
    (89, 99, 110): (89, 99, 110),     # #59636e → #59636e (secondary)
    (129, 139, 152): (129, 139, 152), # #818b98 → #818b98 (muted)
}

def nearest_dark(c):
    """Find nearest dark color in mapping for a given RGB tuple."""
    r, g, b = c
    best = None
    best_dist = float('inf')
    for dc, lc in DARK_TO_LIGHT.items():
        dr, dg, db = dc
        dist = (r-dr)**2 + (g-dg)**2 + (b-db)**2
        if dist < best_dist:
            best_dist = dist
            best = lc
    return best

def transform_image(src_path: Path, dst_path: Path) -> None:
    im = Image.open(src_path).convert("RGB")
    pixels = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            c = pixels[x, y]
            pixels[x, y] = nearest_dark(c)
    im.save(dst_path, optimize=True)

def main():
    demo_files = [
        "mission-control-demo.png",
        "intelligence-demo.png",
        "targets-demo.png",
        "capital-demo.png",
        "merlin-demo.png",
        "agents-demo.png",
        "reports-demo.png",
        "settings-demo.png",
    ]
    
    for fname in demo_files:
        src = DARK_DIR / fname
        if not src.exists():
            print(f"SKIP {fname}: not found")
            continue
        # Output name: mission-control.png (no -demo suffix)
        out_name = fname.replace("-demo", "") + ".png"
        dst = LIGHT_DIR / out_name
        transform_image(src, dst)
        print(f"Generated {dst}")

if __name__ == "__main__":
    main()
