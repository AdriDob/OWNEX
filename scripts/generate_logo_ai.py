#!/usr/bin/env python3
"""
OWNEX Logo Generator usando Pollinations.ai (IA gratuita sin API key)
"""

import requests
import os
from PIL import Image
from io import BytesIO

def generate_logo_with_ai():
    """Generar logo OWNEX usando IA de Pollinations.ai."""

    # Prompt para el logo
    prompt = "professional modern logo for tech company OWNEX, minimalist, futuristic, cyan and blue colors, clean design, vector style, on dark background, high quality, 4k"

    # URL de Pollinations.ai (gratuito, no API key)
    url = f"https://image.pollinations.ai/prompt/{prompt}?width=1280&height=640&nologo=true&seed=42"

    try:
        print("Generando logo con IA...")
        response = requests.get(url, timeout=60)

        if response.status_code == 200:
            # Guardar imagen
            output_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'banner.png')

            img = Image.open(BytesIO(response.content))
            img.save(output_path, 'PNG', quality=98)

            print(f"Logo IA guardado en: {output_path}")
            return output_path
        else:
            print(f"Error: {response.status_code}")
            return None

    except Exception as e:
        print(f"Error generando logo: {e}")
        return None

if __name__ == "__main__":
    generate_logo_with_ai()
