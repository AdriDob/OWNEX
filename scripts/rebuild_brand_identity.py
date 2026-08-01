"""OWNEX ALPHA/OMEGA — Complete Brand Identity System

Rebuild brand identity to match Tesla/Apple/SpaceX/Linear/NVIDIA/PlayStation standards.
Goal: Make OWNEX look like a real technology company, not a hobby project.
"""

from pathlib import Path
import json

BRANDING_DIR = Path("assets/branding")
NEW_STRUCTURE = {
    "logos": "Logo system (main, app icon, favicon, monochrome, transparent, UI)",
    "banners": "Hero banners for README and marketing",
    "concepts": "Conceptual images (Product Overview, Mission Control, Architecture, Mobile, Boot)",
    "mobile": "Mobile-specific branding (Android OMEGA, Wear OS)",
    "desktop": "Desktop-specific branding (OWNEX ALPHA)",
    "video": "Video assets (trailer, boot sequence)"
}

# Create new structure
for folder_name, description in NEW_STRUCTURE.items():
    folder_path = BRANDING_DIR / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created: {folder_path}/")

# Color System (according to prompt)
COLOR_SYSTEM = {
    "primary": {
        "name": "Cyber Cyan",
        "hex": "#00F0FF",
        "rgb": "rgb(0, 240, 255)",
        "usage": "Primary accent, highlights, emphasis"
    },
    "secondary": {
        "name": "Deep Blue",
        "hex": "#0044FF",
        "rgb": "rgb(0, 68, 255)",
        "usage": "Secondary accent, depth, professional"
    },
    "accent": {
        "name": "Emerald",
        "hex": "#00FF88",
        "rgb": "rgb(0, 255, 136)",
        "usage": "Success, positive indicators, growth"
    },
    "background": {
        "name": "Space Black",
        "hex": "#0A0A0A",
        "rgb": "rgb(10, 10, 10)",
        "usage": "Background, dark theme foundation"
    },
    "neutral": {
        "name": "Dark Gray",
        "hex": "#1A1A1A",
        "rgb": "rgb(26, 26, 26)",
        "usage": "Cards, panels, secondary backgrounds"
    },
    "text": {
        "name": "Pure White",
        "hex": "#FFFFFF",
        "rgb": "rgb(255, 255, 255)",
        "usage": "Primary text, headlines"
    },
    "text_secondary": {
        "name": "Light Gray",
        "hex": "#E0E0E0",
        "rgb": "rgb(224, 224, 224)",
        "usage": "Secondary text, descriptions"
    }
}

# Typography System (according to prompt)
TYPOGRAPHY = {
    "primary": {
        "name": "Inter",
        "category": "Sans-serif",
        "style": "Geometric, modern, clean",
        "usage": "Headlines, UI, body text"
    },
    "secondary": {
        "name": "Roboto",
        "category": "Sans-serif",
        "style": "Professional, readable",
        "usage": "Body text, documentation"
    },
    "mono": {
        "name": "JetBrains Mono",
        "category": "Monospace",
        "style": "Technical, code",
        "usage": "Code, technical documentation, terminal"
    },
    "display": {
        "name": "Inter Display",
        "category": "Sans-serif",
        "style": "Bold, impactful",
        "usage": "Hero titles, large headlines"
    }
}

# Brand Guidelines
BRAND_GUIDELINES = {
    "no_use": [
        "brains",
        "robots",
        "eyes",
        "circuits",
        "holograms",
        "generic AI symbols",
        "excessive neon",
        "cartoon elements"
    ],
    "use": [
        "geometry",
        "precision",
        "engineering",
        "evolution",
        "intelligence",
        "minimalism",
        "elegance"
    ],
    "scales": [
        "32px (UI elements)",
        "64px (icons)",
        "128px (small logos)",
        "256px (medium logos)",
        "512px (large logos)",
        "1024px (hero)",
        "screen (full screen)"
    ],
    "formats": [
        "SVG (vector)",
        "PNG (raster)",
        "PDF (print)",
        "ICO (Windows icons)"
    ]
}

# Save brand identity
brand_identity = {
    "color_system": COLOR_SYSTEM,
    "typography": TYPOGRAPHY,
    "brand_guidelines": BRAND_GUIDELINES,
    "structure": NEW_STRUCTURE
}

identity_file = BRANDING_DIR / "BRAND_IDENTITY_V2.json"
with open(identity_file, "w") as f:
    json.dump(brand_identity, f, indent=2)

print(f"\n✓ Brand Identity System defined: {identity_file}")
print(f"  - Color System: {len(COLOR_SYSTEM)} colors")
print(f"  - Typography: {len(TYPOGRAPHY)} font families")
print(f"  - Brand Guidelines: {len(BRAND_GUIDELINES['no_use'])} avoid, {len(BRAND_GUIDELINES['use'])} use")
print(f"  - Scales: {len(BRAND_GUIDELINES['scales'])} sizes")
print(f"  - Formats: {len(BRAND_GUIDELINES['formats'])} formats")
print(f"\nNew asset structure created")
print(f"  - {len(NEW_STRUCTURE)} folders")
