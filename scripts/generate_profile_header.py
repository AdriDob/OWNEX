#!/usr/bin/env python3
"""
Generate a professional GitHub profile header image for a full-stack software developer.
"""

from __future__ import annotations

import contextlib
import math

from PIL import Image, ImageDraw, ImageFont

# Configuration
WIDTH = 1280
HEIGHT = 400
CX = WIDTH / 2
CY = HEIGHT / 2

# Color palette - professional developer aesthetic
COLORS = {
    "bg_dark": "#0a0e17",
    "bg_card": "#111827",
    "primary": "#3b82f6",  # Blue
    "primary_light": "#60a5fa",
    "accent": "#22d3ee",  # Cyan
    "accent_green": "#22c55e",  # Green
    "accent_amber": "#f59e0b",  # Amber
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "border": "#1e293b",
    "grid_line": "#1e293b",
    "argentina_blue": "#75AADB",
    "argentina_yellow": "#FCBF49",
}

# Tech stack - organized by category
TECH_CATEGORIES = {
    "Languages": [
        ("Python", "#3776AB"),
        ("TypeScript", "#3178C6"),
        ("Rust", "#CE422B"),
        ("SQL", "#336791"),
        ("Bash", "#4EAA25"),
    ],
    "Backend": [
        ("FastAPI", "#009688"),
        ("SQLAlchemy", "#D71F00"),
        ("PostgreSQL", "#336791"),
        ("SQLite", "#003B57"),
        ("Redis", "#DC382D"),
    ],
    "Frontend": [
        ("Vue 3", "#42B883"),
        ("TypeScript", "#3178C6"),
        ("Tailwind CSS", "#06B6D4"),
        ("Vite", "#646CFF"),
        ("Pinia", "#FFD859"),
    ],
    "Desktop/Mobile": [
        ("Tauri v2", "#24C8DB"),
        ("Capacitor", "#119EFF"),
        ("Android", "#3DDC84"),
    ],
    "DevOps": [
        ("Docker", "#2496ED"),
        ("GitHub Actions", "#2088FF"),
        ("Tauri CLI", "#24C8DB"),
        ("PyInstaller", "#F78C25"),
    ],
    "AI/Testing": [
        ("Ollama", "#000000"),
        ("OpenRouter", "#00B4D8"),
        ("pytest", "#0A9EDC"),
        ("Ruff", "#F97316"),
        ("mypy", "#007ACC"),
    ],
}

# Flatten for backward compatibility
TECH_ICONS = [(tech, color) for cat in TECH_CATEGORIES.values() for tech, color in cat]


def draw_grid(draw: ImageDraw.ImageDraw, width: int, height: int, spacing: int = 50):
    """Draw subtle grid lines"""
    for x in range(0, width, spacing):
        draw.line([(x, 0), (x, height)], fill=COLORS["grid_line"], width=1)
    for y in range(0, height, spacing):
        draw.line([(0, y), (width, y)], fill=COLORS["grid_line"], width=1)


def draw_glowing_orb(draw: ImageDraw.ImageDraw, x: int, y: int, radius: int, color: str, glow_radius: int = 0):
    """Draw a glowing orb with soft edges"""
    if glow_radius == 0:
        glow_radius = radius * 3
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    for i in range(glow_radius, radius, -2):
        alpha = int(30 * (1 - (i - radius) / (glow_radius - radius)))
        color_with_alpha = (r, g, b, alpha)
        draw.ellipse([x - i, y - i, x + i, y + i], fill=color_with_alpha)
    draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=(r, g, b, 255))


def draw_tech_card(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    label: str,
    color: str,
    font: ImageFont.FreeTypeFont,
    small_font: ImageFont.FreeTypeFont,
):
    """Draw a tech stack card"""
    padding_x = 14
    padding_y = 6
    text_bbox = draw.textbbox((0, 0), label, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    card_w = text_w + padding_x * 2
    card_h = text_h + padding_y * 2

    # Card background
    draw.rounded_rectangle([x, y, x + card_w, y + card_h], radius=6, fill=COLORS["bg_card"], outline=color, width=1)
    # Accent line
    draw.line([(x + 3, y + 3), (x + 3, y + card_h - 3)], fill=color, width=2)
    # Text
    draw.text((x + 12, y + 5), label, font=font, fill=COLORS["text_primary"])


def draw_argentina_flag(draw: ImageDraw.ImageDraw, x: int, y: int, width: int = 48, height: int = 30):
    """Draw Argentina flag 🇦🇷"""
    stripe_h = height // 3
    # Top blue
    draw.rectangle([x, y, x + width, y + stripe_h], fill=COLORS["argentina_blue"])
    # Middle white
    draw.rectangle([x, y + stripe_h, x + width, y + 2 * stripe_h], fill="#FFFFFF")
    # Bottom blue
    draw.rectangle([x, y + 2 * stripe_h, x + width, y + height], fill=COLORS["argentina_blue"])
    # Sun of May (simplified)
    cx, cy = x + width // 2, y + height // 2
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=COLORS["argentina_yellow"])
    # Sun rays (simplified)
    for angle in range(0, 360, 30):
        r1, r2 = 7, 10
        x1 = cx + r1 * math.cos(math.radians(angle))
        y1 = cy - r1 * math.sin(math.radians(angle))
        x2 = cx + r2 * math.cos(math.radians(angle))
        y2 = cy - r2 * math.sin(math.radians(angle))
        draw.line([(x1, y1), (x2, y2)], fill=COLORS["argentina_yellow"], width=2)


def draw_argentina_flag_emoji(draw: ImageDraw.ImageDraw, x: int, y: int, font: ImageFont.FreeTypeFont):
    """Draw Argentina flag as emoji fallback"""
    draw.text((x, y), "🇦🇷", font=font, fill="#FFFFFF")


def generate_header_image(output_path: str = "/tmp/profile_header.png"):
    """Generate the GitHub profile header image"""
    img = Image.new("RGBA", (WIDTH, HEIGHT), COLORS["bg_dark"])
    draw = ImageDraw.Draw(img, "RGBA")

    # Try to load fonts
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    except OSError:
        # Las fuentes del sistema pueden no existir (WSL, Windows, CI). Las dos
        # que se usan tienen fallback; el resto se eliminó: estaban cargadas y
        # nunca leídas.
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()

    # Draw subtle grid background
    draw_grid(draw, WIDTH, HEIGHT, 50)

    # Subtle atmospheric orbs
    draw_glowing_orb(draw, 80, 60, 50, COLORS["primary"], 100)
    draw_glowing_orb(draw, WIDTH - 100, 60, 45, COLORS["accent"], 90)
    draw_glowing_orb(draw, 60, HEIGHT - 60, 35, COLORS["accent_green"], 70)
    draw_glowing_orb(draw, WIDTH - 60, HEIGHT - 60, 50, COLORS["accent_amber"], 100)

    # Top accent line
    draw.line([(40, 30), (WIDTH - 40, 30)], fill=COLORS["border"], width=1)

    # === HEADER SECTION ===
    # Argentina flag + Name
    name_y = 65

    # Draw Argentina flag next to name
    flag_size = 32
    flag_x = CX - 280
    flag_y = name_y - flag_size // 2
    try:
        draw_argentina_flag(draw, int(flag_x), int(flag_y), flag_size, flag_size * 2 // 3)
    except Exception:
        # Fallback: draw "🇦🇷 Argentina" as text
        draw.text(
            (int(flag_x), int(flag_y)),
            "🇦🇷 Argentina",
            font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16),
            fill=COLORS["text_primary"],
        )

    # Name centered
    draw.text((CX, name_y), "Adriel Dobal", font=font_large, fill=COLORS["text_primary"], anchor="mm")

    # Subtitle
    subtitle_y = name_y + 52
    draw.text(
        (CX, subtitle_y), "Full-Stack Software Developer", font=font_medium, fill=COLORS["primary_light"], anchor="mm"
    )

    # Tagline
    tagline_y = subtitle_y + 38
    draw.text(
        (CX, tagline_y),
        "Building autonomous systems • Security automation • AI orchestration",
        font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15),
        fill=COLORS["text_secondary"],
        anchor="mm",
    )

    # Divider
    divider_y = tagline_y + 32
    draw.line([(int(CX - 200), divider_y), (int(CX + 200), divider_y)], fill=COLORS["primary"], width=2)

    # Argentina identifier
    arg_y = divider_y + 22
    draw.text(
        (CX, arg_y),
        "🇦🇷  Basado en Monte Grande, Buenos Aires, Argentina",
        font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13),
        fill=COLORS["argentina_yellow"],
        anchor="mm",
    )

    # === TECH STACK SECTION ===
    tech_start_y = arg_y + 35

    # Category labels and tech cards
    cat_y = tech_start_y
    start_x = 60

    for cat_name, techs in TECH_CATEGORIES.items():
        # Category label
        cat_label_x = start_x + 10
        draw.text(
            (cat_label_x, cat_y),
            cat_name,
            font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12),
            fill=COLORS["text_muted"],
        )
        cat_y += 22

        # Tech cards in this category
        card_x = start_x
        for tech, color in techs:
            draw_tech_card(
                draw,
                card_x,
                cat_y,
                tech,
                color,
                ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11),
                ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10),
            )
            card_x += 120
            if card_x > WIDTH - 140:
                card_x = start_x
                cat_y += 34
        cat_y += 40

    # === BOTTOM SECTION ===
    bottom_y = HEIGHT - 120

    # Code snippet on left
    code_x = 60
    code_y = bottom_y
    code_lines = [
        "class Developer:",
        "    def __init__(self):",
        "        self.stack = ['Python', 'TypeScript', 'Rust', 'Vue 3']",
        "        self.focus = ['Security', 'Automation', 'AI']",
        "    ",
        "    def build(self) -> System:",
        "        return autonomous_systems()",
    ]

    for i, line in enumerate(code_lines):
        indent = "    " if line.startswith("    ") else ""
        color = (
            COLORS["accent_green"]
            if "class" in line or "def" in line
            else COLORS["accent_amber"]
            if "self." in line
            else COLORS["text_muted"]
        )
        draw.text(
            (code_x, code_y + i * 20),
            f"{indent}{line.strip()}",
            font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 12),
            fill=color,
        )

    # Right side: Key metrics
    metrics_x = WIDTH - 300
    metrics_y = bottom_y
    metrics = [
        ("3179+", "tests passing", COLORS["accent_green"]),
        ("7+", "projects shipped", COLORS["accent"]),
        ("9", "vuln types covered", COLORS["accent_amber"]),
        ("6", "work cycles", COLORS["primary"]),
        ("$0", "startup cost", COLORS["accent_green"]),
    ]

    for i, (value, label, color) in enumerate(metrics):
        y = metrics_y + i * 24
        # Value
        draw.text(
            (metrics_x, y),
            value,
            font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20),
            fill=color,
            anchor="rm",
        )
        # Label
        draw.text(
            (metrics_x + 15, y),
            label,
            font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12),
            fill=COLORS["text_secondary"],
        )

    # Bottom bar - tech stack summary
    bar_y = HEIGHT - 18
    draw.line([(40, bar_y - 10), (WIDTH - 40, bar_y - 10)], fill=COLORS["border"], width=1)

    stack_items = [
        ("Python/FastAPI", COLORS["primary"]),
        ("TypeScript/Vue 3", COLORS["accent"]),
        ("Rust/Tauri", COLORS["accent_amber"]),
        ("PostgreSQL/SQLite", COLORS["accent_green"]),
        ("TDD • CI/CD", COLORS["text_secondary"]),
    ]

    item_x = 50
    for label, color in stack_items:
        draw.ellipse([item_x, bar_y, item_x + 8, bar_y + 8], fill=color)
        draw.text(
            (item_x + 14, bar_y - 2),
            label,
            font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11),
            fill=COLORS["text_secondary"],
        )
        item_x += (
            draw.textlength(label, font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)) + 35
        )

    # Argentina flag small at bottom right
    with contextlib.suppress(BaseException):
        draw_argentina_flag(draw, WIDTH - 60, HEIGHT - 38, 24, 16)

    # Save
    img.save(output_path, "PNG")
    print(f"Header image saved to {output_path}")
    return output_path


if __name__ == "__main__":
    generate_header_image()
