"""OWNEX Design System - Premium Color Palette & Typography.

Inspired by Tesla (simplicity), SpaceX (engineering), Linear (modern software),
Apple (elegance), but with OWNEX's own identity.

Design Philosophy:
- Simple, recognizable, scalable
- No robots, no circuits, no cliché AI symbols
- Geometric, precise, engineered
- Premium dark UI aesthetic
"""

from pathlib import Path
import json

# Directory
DESIGN_SYSTEM_DIR = Path("assets/branding/design-system")
DESIGN_SYSTEM_DIR.mkdir(parents=True, exist_ok=True)

# Color Palette - Inspired by premium tech brands but OWNEX-specific
COLORS = {
    "name": "OWNEX Color Palette",
    "description": "Premium dark theme inspired by Tesla, SpaceX, Linear, Apple",
    "colors": {
        # Primary Colors
        "primary": {
            "main": "#1A1A1A",  # Deep Space Black (Tesla-like)
            "light": "#2A2A2A",  # Lighter Deep Space
            "dark": "#0A0A0A",  # Obsidian Black
        },
        # Accent Colors
        "accent": {
            "blue": "#3B82F6",  # Cyber Blue (Linear-like but OWNEX)
            "cyan": "#06B6D4",  # Electric Cyan (SpaceX-like)
            "emerald": "#10B981",  # Emerald Success (Apple-like)
            "gold": "#F59E0B",  # Golden Amber (Tesla-like)
            "purple": "#8B5CF6",  # Digital Purple (premium accent)
        },
        # Semantic Colors
        "semantic": {
            "success": "#10B981",  # Emerald
            "warning": "#F59E0B",  # Amber
            "error": "#EF4444",  # Red
            "info": "#3B82F6",  # Blue
        },
        # Neutral Colors
        "neutral": {
            "white": "#FFFFFF",
            "gray_50": "#808080",
            "gray_100": "#505050",
            "gray_200": "#3A3A3A",
            "gray_300": "#252525",
            "gray_400": "#1A1A1A",
            "gray_500": "#0F0F0F",
        },
        # Gradients
        "gradients": {
            "primary": "linear-gradient(135deg, #1A1A1A 0%, #0A0A0A 100%)",
            "accent": "linear-gradient(135deg, #3B82F6 0%, #06B6D4 100%)",
            "success": "linear-gradient(135deg, #10B981 0%, #059669 100%)",
            "gold": "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)",
        }
    }
}

# Typography - Modern, professional, legible
TYPOGRAPHY = {
    "name": "OWNEX Typography",
    "description": "Modern sans-serif inspired by Linear and Apple",
    "fonts": {
        "primary": {
            "family": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            "weights": {
                "light": 300,
                "regular": 400,
                "medium": 500,
                "semibold": 600,
                "bold": 700,
            }
        },
        "mono": {
            "family": "JetBrains Mono, 'Fira Code', 'Cascadia Code', monospace",
            "weights": {
                "regular": 400,
                "medium": 500,
                "bold": 700,
            }
        }
    },
    "scale": {
        "xs": "0.75rem",
        "sm": "0.875rem",
        "base": "1rem",
        "lg": "1.125rem",
        "xl": "1.25rem",
        "2xl": "1.5rem",
        "3xl": "1.875rem",
        "4xl": "2.25rem",
        "5xl": "3rem",
    }
}

# Spacing System
SPACING = {
    "name": "OWNEX Spacing",
    "description": "Consistent spacing system inspired by Apple and Linear",
    "spacing": {
        "xs": "0.25rem",
        "sm": "0.5rem",
        "md": "1rem",
        "lg": "1.5rem",
        "xl": "2rem",
        "2xl": "3rem",
        "3xl": "4rem",
        "4xl": "6rem",
    }
}

# Border Radius
BORDER_RADIUS = {
    "name": "OWNEX Border Radius",
    "description": "Rounded corners inspired by Apple and Linear",
    "radius": {
        "none": "0",
        "sm": "0.25rem",
        "md": "0.5rem",
        "lg": "0.75rem",
        "xl": "1rem",
        "2xl": "1.5rem",
        "full": "9999px",
    }
}

# Shadow System
SHADOWS = {
    "name": "OWNEX Shadows",
    "description": "Subtle shadows inspired by Linear and Apple",
    "shadows": {
        "sm": "0 1px 2px rgba(0, 0, 0, 0.1)",
        "md": "0 4px 6px rgba(0, 0, 0, 0.1)",
        "lg": "0 10px 15px rgba(0, 0, 0, 0.1)",
        "xl": "0 20px 25px rgba(0, 0, 0, 0.15)",
    }
}

# Save Design System
DESIGN_SYSTEM = {
    "colors": COLORS,
    "typography": TYPOGRAPHY,
    "spacing": SPACING,
    "border_radius": BORDER_RADIUS,
    "shadows": SHADOWS,
}

DESIGN_SYSTEM_FILE = DESIGN_SYSTEM_DIR / "design_system.json"
with open(DESIGN_SYSTEM_FILE, "w") as f:
    json.dump(DESIGN_SYSTEM, f, indent=2)

print(f"✓ Design System created: {DESIGN_SYSTEM_FILE}")
print(f"  - {len(COLORS['colors'])} color groups")
print(f"  - {len(TYPOGRAPHY['fonts'])} font families")
print(f"  - {len(SPACING['spacing'])} spacing steps")
print(f"  - {len(BORDER_RADIUS['radius'])} radius values")
print(f"  - {len(SHADOWS['shadows'])} shadow levels")
