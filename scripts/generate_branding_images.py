#!/usr/bin/env python3
"""
Generador de imágenes profesionales para branding Rastro v7.0.0
Usa Stable Diffusion vía diffusers (mejor herramienta opensource para generación de imágenes)
"""

import os
import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler
from pathlib import Path

# Configuración
OUTPUT_DIR = Path("assets/branding/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Usar modelo más reciente y de alta calidad
MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

# Prompts profesionales
PROMPTS = {
    "logo_icon": {
        "prompt": "Professional minimalist logo icon for cybersecurity bug bounty platform, stylized eye with circuit board patterns, modern tech aesthetic, vector style, clean lines, cyan and dark blue color scheme, white background, high quality, professional branding",
        "negative_prompt": "text, watermark, messy, complex, realistic photo, photograph, 3d render, gradient, blur",
        "steps": 50,
        "guidance_scale": 7.5,
    },
    "logo_horizontal": {
        "prompt": "Professional horizontal logo for cybersecurity platform 'RASTRO', modern tech company branding, minimalist eye symbol with circuit patterns, bold typography, cyan and dark blue, clean white background, corporate identity, professional",
        "negative_prompt": "text watermark, messy, hand drawn, cartoon, childish, low quality, realistic photo",
        "steps": 50,
        "guidance_scale": 7.5,
    },
    "hero_banner_dark": {
        "prompt": "Professional dark hero banner for cybersecurity dashboard, mission control interface, futuristic data visualization, holographic displays, network nodes, threat detection visualization, cyan neon accents on dark blue background, premium tech aesthetic, high resolution",
        "negative_prompt": "light background, cartoon, childish, low quality, messy, cluttered, realistic photo",
        "steps": 50,
        "guidance_scale": 8.0,
    },
    "hero_banner_light": {
        "prompt": "Professional light hero banner for cybersecurity dashboard, clean modern interface, data visualization, network topology, minimalist tech aesthetic, white and light gray background with cyan accents, professional corporate design",
        "negative_prompt": "dark background, neon, cyberpunk, messy, cartoon, childish, low quality",
        "steps": 50,
        "guidance_scale": 7.5,
    },
    "security_cycle_concept": {
        "prompt": "Professional conceptual illustration for security cycle workflow, bug bounty process visualization, reconnaissance to reporting pipeline, modern infographic style, clean geometric shapes, flow diagram, professional blue and cyan color scheme, white background",
        "negative_prompt": "messy, cartoon, childish, realistic photo, low quality, complex, cluttered",
        "steps": 50,
        "guidance_scale": 7.5,
    },
    "mission_control_concept": {
        "prompt": "Professional dashboard interface concept, cybersecurity mission control center, multiple data panels, real-time metrics, dark theme with cyan accents, modern UI design, professional monitoring interface, high resolution",
        "negative_prompt": "light theme, cartoon, childish, low quality, messy, realistic photo of physical dashboard",
        "steps": 50,
        "guidance_scale": 8.0,
    },
}


def generate_image(prompt_config: dict, output_path: Path):
    """Genera una imagen con la configuración dada."""
    print(f"Generating {output_path.name}...")
    
    # Cargar pipeline
    pipe = StableDiffusionXLPipeline.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        use_safetensors=True,
    )
    
    # Optimizar para CPU/MPS
    if torch.cuda.is_available():
        pipe = pipe.to("cuda")
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        pipe = pipe.to("mps")
    else:
        pipe = pipe.to("cpu")
    
    # Configurar scheduler
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    
    # Generar
    image = pipe(
        prompt=prompt_config["prompt"],
        negative_prompt=prompt_config["negative_prompt"],
        num_inference_steps=prompt_config["steps"],
        guidance_scale=prompt_config["guidance_scale"],
        width=1024,
        height=1024,
        num_images_per_prompt=1,
    ).images[0]
    
    # Guardar
    image.save(output_path)
    print(f"✓ Saved to {output_path}")
    
    # Limpiar memoria
    del pipe
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def main():
    """Genera todas las imágenes de branding."""
    print("🎨 Rastro v7.0.0 Branding Image Generator")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"🤖 Model: {MODEL_ID}")
    print()
    
    for name, config in PROMPTS.items():
        output_path = OUTPUT_DIR / f"{name}.png"
        try:
            generate_image(config, output_path)
        except Exception as e:
            print(f"✗ Error generating {name}: {e}")
            continue
    
    print()
    print("✅ Branding images generated successfully!")
    print(f"📁 Location: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
