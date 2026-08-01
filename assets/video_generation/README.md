# OWNEX OMEGA — Video Generation Guide

## Overview

Esta guía explica cómo generar el video de presentación cinematográfico profesional de OWNEX OMEGA usando ComfyUI.

## Prerequisites

### Hardware
- **GPU:** NVIDIA GPU con 12GB+ VRAM (24GB+ recomendado)
- **RAM:** 32GB (64GB recomendado)
- **Storage:** 50GB+ free para modelos y renders

### Software
- **ComfyUI:** Ya instalado en `.ai/brand/comfyui/`
- **Python:** 3.10+ (ComfyUI venv)
- **Video Models:** Stable Video Diffusion / Hunyuan Video / Wan

## Directory Structure

```
assets/video_generation/
├── models/                    # Video models (SVD, Hunyuan, Wan)
├── workflows/                 # ComfyUI workflow JSON files
├── prompts/                   # Text prompts for each scene
├── renders/                   # Generated video segments
├── audio/                     # Audio files (TTS, music, SFX)
└── config.json                # Configuration file
```

## Scenes

| Scene | Duration | Description |
|-------|----------|-------------|
| 1. Awakening | 8s | Logo appears with particles and energy lines |
| 2. System Boot | 10s | OWNEX modules initializing with HUD |
| 3. Desktop ALPHA | 15s | Mission Control, agents, terminal, dashboards |
| 4. MERLIN Assistant | 12s | Intelligent interface, no humanoid |
| 5. Autonomous Agents | 12s | Departments collaborating as digital company |
| 6. Android OMEGA | 12s | Mobile Companion with HUD interface |
| 7. Smartwatch | 8s | Wear OS with alerts and approvals |
| 8. Ecosystem | 10s | Desktop → Mobile → Watch → Cloud → Agents |
| 9. Final | 8s | Logo with tagline |
| **Total** | **95s** | **Main trailer** |

**Bonus:** Boot Sequence (20s) - PC powers on → OWNEX → Scan → MERLIN → Mission Control

## Visual Style

- **Primary Color:** #00F0FF (Cyan)
- **Secondary Color:** #00FF88 (Emerald)
- **Background:** Deep Space Black
- **Accent:** White
- **Style:** Premium cyber intelligence, minimalist, elegant
- **Avoid:** Robots, digital brains, AI clichés, excessive neon

## Audio Configuration

- **Start:** Space system, technology advanced
- **Interface:** Premium clicks, soft sounds, confirmations
- **Agents:** Ambient intelligent
- **Final:** Cinematic impact
- **TTS Engine:** Piper / XTTS / equivalent open source
- **Music:** Ambient, cinematic, subtle

## How to Generate Video

### Step 1: Install ComfyUI (if not already installed)

ComfyUI ya está instalado en `.ai/brand/comfyui/`.

### Step 2: Download Video Models

Download video models from HuggingFace or Civitai:

- **Stable Video Diffusion (SVD):** https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt
- **Hunyuan Video:** https://huggingface.co/hunyuanlab/HunyuanVideo
- **Wan:** https://huggingface.com/Wan-Video/Wan2.1

Place models in `assets/video_generation/models/`.

### Step 3: Start ComfyUI

```bash
cd .ai/brand/comfyui
source venv/bin/activate
python main.py --listen 127.0.0.1 --port 8188
```

ComfyUI UI estará disponible en: http://127.0.0.1:8188

### Step 4: Load Workflows

Para cada escena:

1. Abre ComfyUI UI
2. Carga el workflow JSON desde `assets/video_generation/workflows/`
3. Ajusta el modelo checkpoint en el nodo CheckpointLoaderSimple
4. Carga el prompt desde `assets/video_generation/prompts/`
5. Ajusta la semilla si deseas variación
6. Renderiza

### Step 5: Generate Audio

Usa TTS open source (Piper/XTTS) para voz MERLIN.

```bash
# Install Piper
pip install piper-tts

# Generate audio
piper-tts --model en_US-lessac-medium --text "Welcome back. Your system is ready." --output audio/merlin_greeting.wav
```

### Step 6: Assemble Video

Usa FFmpeg para unir los segmentos:

```bash
# Install FFmpeg
sudo apt install ffmpeg

# Join video segments
ffmpeg -f concat -i segments.txt -c copy ownex_trailer.mp4

# Add audio
ffmpeg -i ownex_trailer.mp4 -i audio/music.mp4 -c:v copy -c:a aac ownex_trailer_with_audio.mp4
```

## Estimated Render Time

- **GPU with 12GB VRAM:** ~2-4 hours por 10 segundos de video
- **GPU with 24GB VRAM:** ~1-2 horas por 10 segundos de video
- **Total 95 seconds:** ~10-20 horas (dependiendo de GPU)

## Alternative: Manual Creation

Si no tienes GPU suficiente, considera:

1. **Usar renders de IA existentes** (generar imágenes con Stable Diffusion, luego animar)
2. **Capturas reales de OWNEX** (grabar la interfaz real funcionando)
3. **Animaciones de interfaz** (usar After Effects / Premiere)
4. **Motion graphics** (crear animaciones 2D profesionales)
5. **Combinar todo** (renders + capturas + animaciones)

## Output

Videos finales:

- `ownex_trailer.mp4` (95s - 2min)
- `ownex_short.mp4` (30s - redes sociales)
- `ownex_boot_sequence.mp4` (20s - demo)
- `ownex_trailer_4k.mp4` (4K si es posible)

## Update README

Después de generar el video, actualiza README.md:

```markdown
## Demo

[![OWNEX OMEGA Trailer](assets/video/ownex_trailer.mp4)]

**[Watch Full Trailer](assets/video/ownex_trailer.mp4)** (95s)

**[Watch Boot Sequence](assets/video/ownex_boot_sequence.mp4)** (20s)

**[Watch Short Version](assets/video/ownex_short.mp4)** (30s)
```

## Notes

- Video generation es computacionalmente intensivo
- Requiere GPU dedicada o servicio en la nube
- Los workflows son templates - pueden requerir ajustes manuales
- La calidad depende de los modelos usados
- Considera outsourcing si no tienes GPU suficiente

## Alternative Services

Si no quieres generar localmente:

- **RunPod / Lambda Labs:** GPU en la nube con ComfyUI pre-installed
- **Render farms:** Servicios de render profesional
- **AI video tools:** Runway ML, Pika Labs, etc.

## Troubleshooting

### ComfyUI no inicia
- Verifica que Python 3.10+ esté instalado
- Verifica que CUDA 11.8+ esté instalado
- Verifica VRAM disponible

### OOM (Out of Memory)
- Reduce resolución (1080p en lugar de 4K)
- Reduce frames por segundo (24fps en lugar de 30fps)
- Reduce steps en KSampler
- Usa modelo más pequeño

### Generación lenta
- Usa GPU con más VRAM
- Reduce la longitud del video
- Usa modelo más eficiente
- Considera usar la nube
