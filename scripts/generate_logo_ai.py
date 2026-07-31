#!/usr/bin/env python3
"""
OWNEX Professional Banner Generator usando Pollinations.ai (IA gratuita sin API key)
Genera banner completo de alta calidad para portada GitHub
"""

import os
from io import BytesIO

import requests
from PIL import Image


def generate_professional_banner():
    """Generar banner OWNEX profesional usando IA de Pollinations.ai."""

    # Prompt ULTRA PROFESIONAL para banner completo - Actualizado
    prompt = "OWNEX professional banner, futuristic tech company branding, bold cyan text on dark navy background, sleek modern design, geometric elements, glowing effects, professional startup aesthetic, high contrast, centered composition, minimalist yet striking, 4K UHD, ultra detailed"

    # URL de Pollinations.ai (gratuito, no API key) - dimensiones grandes para banner
    url = f"https://image.pollinations.ai/prompt/{prompt}?width=1280&height=640&nologo=true&seed=ownex2025&model=flux"

    try:
        print("Generando banner profesional con IA...")
        response = requests.get(url, timeout=90)

        if response.status_code == 200:
            # Guardar imagen
            output_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'banner.png')

            img = Image.open(BytesIO(response.content))
            img.save(output_path, 'PNG', quality=98)

            print(f"Banner profesional guardado en: {output_path}")
            return output_path
        else:
            print(f"Error: {response.status_code}")
            return None

    except Exception as e:
        print(f"Error generando banner: {e}")
        return None

if __name__ == "__main__":
    generate_professional_banner()
