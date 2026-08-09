#!/usr/bin/env python3
"""OWNEX presentation validation — exits non-zero on any failure.

Checks:
  - Every image referenced in README.md exists on disk
  - README Mermaid fences are balanced
  - Every PNG under docs/assets is a valid image
  - .github/social-preview.{png,svg} match the regenerated social preview
  - Expected brand deliverables exist (logo variants, banner, favicon)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if cond:
        print(f"  ok  {msg}")
    else:
        failures.append(msg)
        print(f"FAIL  {msg}")


def main() -> None:
    readme = ROOT / "README.md"
    text = readme.read_text()

    print("README images")
    for ref in sorted(set(re.findall(r"\]\((docs/assets/[^)#]+)\)", text))):
        check((ROOT / ref).exists(), f"image exists: {ref}")

    print("Mermaid fences")
    fences = re.findall(r"```mermaid\n(.*?)```", text, re.DOTALL)
    check(len(fences) == 1, f"exactly 1 mermaid block (found {len(fences)})")
    for f in fences:
        check(f.count("flowchart") == 1 and "end" in f, "mermaid block has flowchart + end")

    print("PNG validity")
    pngs = sorted((ROOT / "docs" / "assets").rglob("*.png"))
    for p in pngs:
        try:
            Image.open(p).verify()
            check(True, f"{p.relative_to(ROOT)}")
        except Exception:
            check(False, f"invalid PNG: {p.relative_to(ROOT)}")

    print("Brand deliverables")
    logo = ROOT / "docs" / "assets" / "branding" / "logo"
    for name in [
        "ownex-mark-white.svg",
        "ownex-mark-white.png",
        "ownex-mark-black.svg",
        "ownex-lockup-white.svg",
        "ownex-favicon.svg",
        "ownex-favicon.png",
    ]:
        check((logo / name).exists(), f"logo: {name}")
    check((ROOT / "docs" / "assets" / "branding" / "banners" / "ownex-hero-banner.png").exists(), "hero banner")
    check((ROOT / "docs" / "assets" / "branding" / "social" / "ownex-social-preview.png").exists(), "social preview")
    check((ROOT / "docs" / "assets" / "diagrams" / "architecture.mmd").exists(), "architecture.mmd")
    for doc in ["INTERNAL_AUDIT.md", "GITHUB_PRESENTATION_REPORT.md"]:
        check((ROOT / "docs" / "audit" / doc).exists(), f"audit doc: {doc}")

    print("GitHub social preview sync")
    from hashlib import md5

    def md5_of(p: Path) -> str:
        return md5(p.read_bytes()).hexdigest()

    src = ROOT / "docs" / "assets" / "branding" / "social" / "ownex-social-preview.png"
    dst = ROOT / ".github" / "social-preview.png"
    check(src.exists() and dst.exists() and md5_of(src) == md5_of(dst), "social-preview.png in sync")

    print("Screenshots")
    shots = list((ROOT / "docs" / "assets" / "screenshots" / "desktop").glob("*.png"))
    check(len(shots) >= 5, f"at least 5 desktop screenshots (found {len(shots)})")

    if failures:
        print(f"\nVALIDATION FAILED: {len(failures)} issue(s)")
        sys.exit(1)
    print("\nVALIDATION PASSED")


if __name__ == "__main__":
    main()
