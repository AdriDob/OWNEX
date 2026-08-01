# OWNEX OMEGA — Simple Presentation Video Guide

## Overview

Generar un video de presentación simple usando las imágenes de branding ya creadas.

## Opción 1: Canva (Recomendado - Fácil y Rápido)

### Pasos:

1. **Ir a Canva** (https://www.canva.com)
2. **Crear presentación**
   - Buscar "Video" → "Video de presentación"
   - Elegir plantilla premium (tema oscuro/corporativo)
3. **Subir imágenes**
   - Arrastrar las imágenes de `assets/branding/professional/`:
     - `ownex_main_logo.png`
     - `cinematic_hero_banner.png`
     - `alpha_logo.png`
     - `omega_logo.png`
     - `architecture_diagram.png`
     - `mission_control_screenshot.png`
     - `merlin_assistant_concept.png`
     - `mobile_omega_concept.png`
     - `boot_animation_concept.png`
4. **Añadir texto**
   - Título: "OWNEX OMEGA"
   - Subtítulo: "Autonomous Personal Operating System"
   - Tagline: "Build. Learn. Automate. Evolve."
5. **Añadir música**
   - Usar música premium de Canva (categoría: Tech, Corporate, Cinematic)
6. **Exportar**
   - Formato: MP4
   - Calidad: 1080p (HD)
   - Duración: 60-90 segundos

### Tiempo estimado: 30-60 minutos

## Opción 2: CapCut (Gratuito y Potente)

### Pasos:

1. **Descargar CapCut** (https://www.capcut.com)
2. **Crear proyecto**
   - Nuevo proyecto
   - Proporción: 16:9
   - Resolución: 1080p
3. **Importar imágenes**
   - Importar desde `assets/branding/professional/`
4. **Editar timeline**
   - Arrastrar imágenes a timeline
   - Duración por imagen: 4-6 segundos
   - Añadir transiciones (fade, dissolve)
5. **Añadir texto**
   - Títulos con estilo premium
   - Fuente: Inter o Roboto
   - Color: Cyan (#00F0FF) y Emerald (#00FF88)
6. **Añadir música**
   - Biblioteca de música de CapCut
   - Categoría: Tech, Corporate
7. **Exportar**
   - Calidad: 1080p
   - Frame rate: 30fps

### Tiempo estimado: 45-90 minutos

## Opción 3: DaVinci Resolve (Profesional y Gratuito)

### Pasos:

1. **Descargar DaVinci Resolve** (https://www.blackmagicdesign.com/products/davinciresolve)
2. **Crear proyecto**
   - Configuración: 1080p 24fps
3. **Importar media**
   - Importar imágenes de branding
4. **Editar en timeline**
   - Añadir a timeline
   - Usar transiciones
   - Añadir texto (Resolve FX → Titles)
5. **Color grading**
   - Ajustar colores para consistencia
   - Aplicar LUT premium
6. **Añadir audio**
   - Importar música royalty-free
7. **Exportar**
   - Preset: YouTube 1080p

### Tiempo estimado: 60-120 minutos

## Opción 4: AI Video Tools (Automatizado)

### Runway ML (https://runwayml.com)
- Subir imágenes
- Usar "Gen-2" para generar video
- Exportar MP4

### Pika Labs (https://pika.art)
- Subir imágenes
- Generar video con AI
- Exportar MP4

### Tiempo estimado: 20-40 minutos

## Script Automatizado (FFmpeg)

Si tienes FFmpeg instalado, ejecuta:

```bash
python3 scripts/generate_simple_video.py
```

Este generará un slideshow automático de las imágenes de branding.

**Instalar FFmpeg:**
- Ubuntu/Debian: `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: Descargar de https://ffmpeg.org/download.html

## Secuencia Sugerida del Video

| Imagen | Duración | Texto |
|--------|----------|-------|
| ownex_main_logo.png | 4s | OWNEX OMEGA |
| cinematic_hero_banner.png | 6s | Autonomous Personal Operating System |
| alpha_logo.png | 4s | OWNEX ALPHA - Desktop Command Center |
| omega_logo.png | 4s | OWNEX OMEGA - Mobile Companion |
| architecture_diagram.png | 8s | Architecture: Agents, Workflows, Memory, Evolution |
| mission_control_screenshot.png | 8s | Mission Control: Dashboard, Agents, Opportunities |
| merlin_assistant_concept.png | 8s | MERLIN: Intelligent Assistant, Voice, Memory |
| mobile_omega_concept.png | 8s | Mobile: Android + Wear OS, Connected Ecosystem |
| boot_animation_concept.png | 6s | Boot Sequence: Startup → Scan → Ready |
| ownex_main_logo.png | 4s | Build. Learn. Automate. Evolve. |

**Total:** ~60 segundos

## Música Sugerida

**Estilo:** Cinematic, Tech, Corporate, Ambient

**Fuentes:**
- YouTube Audio Library (gratis)
- Epidemic Sound (gratis trial)
- Artlist (suscripción)
- Pond5 (suscripción)

**Búsqueda terms:**
- "Tech cinematic"
- "Corporate presentation"
- "Futuristic technology"
- "Space technology"

## Colores del Video

- **Primary:** #00F0FF (Cyan)
- **Secondary:** #00FF88 (Emerald)
- **Background:** Deep Space Black (#1A1A1A)
- **Accent:** White (#FFFFFF)

## Fuente Sugerida

- **Primary:** Inter (ya usado en OWNEX)
- **Alternative:** Roboto, SF Pro
- **Títulos:** Bold/700
- **Cuerpo:** Regular/400

## Output Final

- **Formato:** MP4
- **Resolución:** 1080p (1920x1080)
- **Frame rate:** 30fps
- **Bitrate:** 8-10 Mbps
- **Audio:** AAC 128kbps

## Update README

Después de generar el video, actualiza README.md:

```markdown
## Demo

[![OWNEX OMEGA Presentation](assets/video/ownex_presentation.mp4)]

**[Watch Presentation Video](assets/video/ownex_presentation.mp4)** (60s)
```

## Recomendación

**Para mejores resultados:** Use Canva (más fácil, plantillas premium, música integrada)

**Para control total:** Use CapCut (gratis, potente, transiciones profesionales)

**Para calidad profesional:** Use DaVinci Resolve (gratuito, color grading avanzado)

**Para automatización:** Use el script FFmpeg si tienes FFmpeg instalado
