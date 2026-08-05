#!/usr/bin/env python3
"""Convert OWNEX Mermaid diagrams to the TESLA palette (tokens.css).

Mapping (old brand -> TESLA):
  #5E6AD2 (purple border) -> #2e2e2e  border_light
  #00E39A (green)         -> #16a34a  success (desaturated)
  #FFB020 (orange)        -> #d97706  warning (desaturated)
  #FF5252 (red)           -> #e82127  Tesla red — the ONLY saturated accent
  #F6F8FB (text)          -> #f5f5f5  fg
  #111113 (cluster)       -> #0a0a0a  surface
  #1F2023 (secondary)     -> #141414  surface_hover
  #2A2D35 (tertiary)      -> #1f1f1f  border
  #08090A (edge bg)       -> #000000  bg
  #8B8D98 (muted)         -> #4a4a4a  muted
"""

from pathlib import Path

MAPPING = {
    "#5E6AD2": "#2e2e2e",
    "#00E39A": "#16a34a",
    "#FFB020": "#d97706",
    "#FF5252": "#e82127",
    "#F6F8FB": "#f5f5f5",
    "#111113": "#0a0a0a",
    "#1F2023": "#141414",
    "#2A2D35": "#1f1f1f",
    "#08090A": "#000000",
    "#8B8D98": "#4a4a4a",
}

ROOT = Path(__file__).resolve().parents[2]
DIAGRAMS = ROOT / "assets" / "diagrams"

for mmd in sorted(DIAGRAMS.glob("*.mmd")):
    text = mmd.read_text(encoding="utf-8")
    for old, new in MAPPING.items():
        text = text.replace(old, new)
    mmd.write_text(text, encoding="utf-8")
    print(f"converted: {mmd.name}")
