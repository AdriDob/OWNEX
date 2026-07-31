#!/usr/bin/env python3
"""
OWNEX Professional Banner Generator — Canvas API para diseño high-end
"""

import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont


def create_professional_banner_v2():
    """Crear banner PNG profesional v2 con diseño high-end."""

    # Configuración
    width = 1280
    height = 640

    # Paleta de colores
    bg_dark = (8, 8, 20)  # #080814
    bg_light = (20, 20, 40)  # #141428
    primary = (0, 240, 255)  # #00f0ff
    secondary = (0, 255, 136)  # #00ff88
    white = (255, 255, 255)
    gray = (100, 100, 120)

    # Crear imagen
    img = Image.new('RGB', (width, height), bg_dark)
    draw = ImageDraw.Draw(img)

    # Gradient background (más suave)
    for y in range(height):
        ratio = y / height
        r = int(bg_dark[0] + (bg_light[0] - bg_dark[0]) * ratio)
        g = int(bg_dark[1] + (bg_light[1] - bg_dark[1]) * ratio)
        b = int(bg_dark[2] + (bg_light[2] - bg_dark[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Grid pattern sutil
    for x in range(0, width, 40):
        draw.line([(x, 0), (x, height)], fill=(primary[0], primary[1], primary[2], 20), width=1)
    for y in range(0, height, 40):
        draw.line([(0, y), (width, y)], fill=(primary[0], primary[1], primary[2], 10), width=1)

    # Cargar fuentes
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 96)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        tagline_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        badge_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        tagline_font = ImageFont.load_default()
        badge_font = ImageFont.load_default()

    # Logo OWNEX - Con efecto 3D
    text = "OWNEX"
    bbox = draw.textbbox((0, 0), text, font=title_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = 160

    # Shadow
    for i in range(8):
        shadow_color = (
            max(0, primary[0] - i * 20),
            max(0, primary[1] - i * 20),
            max(0, primary[2] - i * 20)
        )
        draw.text((x + i, y + i), text, font=title_font, fill=shadow_color)

    # Texto principal con glow
    for i in range(3):
        glow_color = (
            min(255, primary[0] + i * 40),
            min(255, primary[1] + i * 40),
            min(255, primary[2] + i * 40)
        )
        draw.text((x - i, y - i), text, font=title_font, fill=glow_color)

    draw.text((x, y), text, font=title_font, fill=primary)

    # Underline
    line_y = y + text_height + 20
    draw.line([(x, line_y), (x + text_width, line_y)], fill=primary, width=4)

    # Subtítulo
    subtitle = "AUTONOMOUS WORK OPERATING PLATFORM"
    bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = bbox[2] - bbox[0]
    subtitle_x = (width - subtitle_width) // 2
    draw.text((subtitle_x, 300), subtitle, font=subtitle_font, fill=white)

    # Tagline
    tagline = "ZERO-BARRIER ENTRY  •  AUTONOMOUS OPERATION  •  AI-POWERED INTELLIGENCE"
    bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
    tagline_width = bbox[2] - bbox[0]
    tagline_x = (width - tagline_width) // 2
    draw.text((tagline_x, 370), tagline, font=tagline_font, fill=gray)

    # Badge "PRODUCTION READY" - Más elegante
    badge_text = "PRODUCTION READY"
    badge_width = 280
    badge_height = 56
    badge_x = (width - badge_width) // 2
    badge_y = 460

    # Badge background con gradiente simulado
    draw.rounded_rectangle(
        [(badge_x, badge_y), (badge_x + badge_width, badge_y + badge_height)],
        radius=28,
        fill=(0, 255, 136, 40),
        outline=secondary,
        width=3
    )

    # Badge text
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_text_width = bbox[2] - bbox[0]
    badge_text_height = bbox[3] - bbox[1]
    badge_text_x = badge_x + (badge_width - badge_text_width) // 2
    badge_text_y = badge_y + (badge_height - badge_text_height) // 2 - 4
    draw.text((badge_text_x, badge_text_y), badge_text, font=badge_font, fill=secondary)

    # Elementos decorativos - Hexagon pattern
    # Hexagon grande izquierda
    hex_size = 80
    hex_x, hex_y = 120, 520
    points = []
    for i in range(6):
        angle = 60 * i - 30
        px = hex_x + hex_size * 0.866 * (angle if angle % 360 < 180 else 360 - angle) / 360
        py = hex_y + hex_size * 0.5 * ((angle + 90) % 360 - 180) / 180 * -1
        points.append((px, py))
    draw.polygon(points, fill=primary)
    draw.polygon(points, outline=bg_dark, width=3)

    # Hexagon derecha superior
    hex_x, hex_y = 1160, 120
    points = []
    for i in range(6):
        angle = 60 * i - 30
        px = hex_x + hex_size * 0.866 * (angle if angle % 360 < 180 else 360 - angle) / 360
        py = hex_y + hex_size * 0.5 * ((angle + 90) % 360 - 180) / 180 * -1
        points.append((px, py))
    draw.polygon(points, fill=secondary)
    draw.polygon(points, outline=bg_dark, width=3)

    # Líneas decorativas con glow
    # Línea superior
    draw.line([(100, 120), (width - 100, 120)], fill=primary, width=2)
    draw.line([(100, 120), (width - 100, 120)], fill=primary, width=1)

    # Línea inferior
    draw.line([(100, 420), (width - 100, 420)], fill=primary, width=2)
    draw.line([(100, 420), (width - 100, 420)], fill=primary, width=1)

    # Corner accents
    corner_size = 20
    # Esquina superior izquierda
    draw.rectangle([(20, 20), (20 + corner_size, 20 + 2)], fill=primary)
    draw.rectangle([(20, 20), (20 + 2, 20 + corner_size)], fill=primary)
    # Esquina superior derecha
    draw.rectangle([(width - 20 - corner_size, 20), (width - 20, 20 + 2)], fill=primary)
    draw.rectangle([(width - 20 - 2, 20), (width - 20, 20 + corner_size)], fill=primary)
    # Esquina inferior izquierda
    draw.rectangle([(20, height - 20 - corner_size), (20 + corner_size, height - 20)], fill=primary)
    draw.rectangle([(20, height - 20 - 2), (20 + 2, height - 20)], fill=primary)
    # Esquina inferior derecha
    draw.rectangle([(width - 20 - corner_size, height - 20 - 2), (width - 20, height - 20)], fill=primary)
    draw.rectangle([(width - 20 - 2, height - 20 - corner_size), (width - 20, height - 20)], fill=primary)

    # Aplicar blur sutil para efecto de profundidad
    img = img.filter(ImageFilter.SMOOTH_MORE)

    # Guardar imagen
    output_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'banner.png')
    img.save(output_path, 'PNG', quality=98)
    print(f"Banner PRO guardado en: {output_path}")

    return output_path

if __name__ == "__main__":
    create_professional_banner_v2()
