#!/usr/bin/env python3
"""OWNEX asset optimization — lossy reduction for product screenshots.

UI screenshots are quantized to 8-bit palette (P mode) which typically
cuts file size 50-70% with negligible visual impact. Brand logos keep
full color fidelity and are untouched.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "docs" / "assets" / "screenshots"


def optimize_dir(directory: Path) -> None:
    for p in sorted(directory.glob("*.png")):
        im = Image.open(p)
        if im.mode in ("RGB", "RGBA"):
            q = im.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT)
            before = p.stat().st_size
            q.save(p, optimize=True)
            after = p.stat().st_size
            print(f"{p.name}: {before // 1024}KB -> {after // 1024}KB ({100 * (1 - after / before):.0f}% smaller)")
        else:
            print(f"{p.name}: skipped (mode={im.mode})")


def main() -> None:
    if not SHOTS.exists():
        print("no screenshots dir found")
        return
    desktop = SHOTS / "desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    print(f"optimizing {desktop}")
    optimize_dir(desktop)


if __name__ == "__main__":
    main()
