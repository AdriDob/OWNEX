#!/usr/bin/env python3
"""
OWNEX Banner Generator — Crea banner PNG profesional
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_professional_banner():
    """Crear banner PNG profesional para OWNEX."""

    # Configuración
    width = 1200
    height = 600
    background_color = (10, 10, 26)  # #0a0a1a
    accent_color = (0, 240, 255)  # #00f0ff
    text_color = (255, 255, 255)
    secondary_color = (136, 136, 136)  # #888888
    success_color = (0, 255, 136)  # #00ff88

    # Crear imagen
    img = Image.new('RGB', (width, height), background_color)
    draw = ImageDraw.Draw(img)

    # Gradiente background (simulado con rectángulos)
    for i in range(height):
        alpha = int(255 * (i / height) * 0.2)
        color = (
            int(background_color[0] + (accent_color[0] - background_color[0]) * (i / height) * 0.3),
            int(background_color[1] + (accent_color[1] - background_color[1]) * (i / height) * 0.3),
            int(background_color[2] + (accent_color[2] - background_color[2]) * (i / height) * 0.3)
        )
        draw.line([(0, i), (width, i)], fill=color)

    # Intentar cargar fuente
    try:
        # Intentar usar fuentes del sistema
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        tagline_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        badge_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except:
        # Fallback a default
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        tagline_font = ImageFont.load_default()
        badge_font = ImageFont.load_default()

    # Logo OWNEX - Texto grande con glow
    text = "OWNEX"
    # Calcular posición centrada
    bbox = draw.textbbox((0, 0), text, font=title_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = 180

    # Glow effect (dibujar texto varias veces con opacidad)
    for i in range(5):
        alpha = 255 - (i * 40)
        glow_color = (
            min(255, accent_color[0] + i * 20),
            min(255, accent_color[1] + i * 20),
            min(255, accent_color[2] + i * 20)
        )
        draw.text((x + i, y + i), text, font=title_font, fill=glow_color)

    # Texto principal
    draw.text((x, y), text, font=title_font, fill=accent_color)

    # Subtítulo
    subtitle = "Autonomous Work Operating Platform"
    bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = bbox[2] - bbox[0]
    subtitle_x = (width - subtitle_width) // 2
    draw.text((subtitle_x, 280), subtitle, font=subtitle_font, fill=text_color)

    # Tagline
    tagline = "Zero-Barrier Entry • Autonomous Operation • AI-Powered Intelligence"
    bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
    tagline_width = bbox[2] - bbox[0]
    tagline_x = (width - tagline_width) // 2
    draw.text((tagline_x, 340), tagline, font=tagline_font, fill=secondary_color)

    # Badge "PRODUCTION READY"
    badge_text = "PRODUCTION READY"
    badge_width = 300
    badge_height = 60
    badge_x = (width - badge_width) // 2
    badge_y = 420

    # Badge background (rounded rect)
    draw.rounded_rectangle(
        [(badge_x, badge_y), (badge_x + badge_width, badge_y + badge_height)],
        radius=30,
        fill=(0, 255, 136, 30),
        outline=success_color,
        width=3
    )

    # Badge text
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_text_width = bbox[2] - bbox[0]
    badge_text_height = bbox[3] - bbox[1]
    badge_text_x = badge_x + (badge_width - badge_text_width) // 2
    badge_text_y = badge_y + (badge_height - badge_text_height) // 2 - 5
    draw.text((badge_text_x, badge_text_y), badge_text, font=badge_font, fill=success_color)

    # Elementos decorativos - círculos
    # Círculo grande izquierda
    draw.ellipse([50, 450, 150, 550], fill=accent_color)
    # Opacidad simulada (no podemos hacer alpha directo en draw, así que usamos colores más claros)
    draw.ellipse([70, 470, 130, 530], fill=background_color)

    # Círculo derecha superior
    draw.ellipse([1050, 50, 1150, 150], fill=accent_color)
    draw.ellipse([1070, 70, 1130, 130], fill=background_color)

    # Círculo pequeño derecha inferior
    draw.ellipse([1100, 480, 1160, 540], fill=success_color)
    draw.ellipse([1110, 490, 1150, 530], fill=background_color)

    # Líneas decorativas
    draw.line([(0, 200), (width, 200)], fill=accent_color, width=2)
    draw.line([(0, 400), (width, 400)], fill=accent_color, width=1)

    # Guardar imagen
    output_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'banner.png')
    img.save(output_path, 'PNG', quality=95)
    print(f"Banner guardado en: {output_path}")

    return output_path

if __name__ == "__main__":
    create_professional_banner()
