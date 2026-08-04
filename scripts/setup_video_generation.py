"""OWNEX OMEGA — Video Generation Configuration

Configuration for generating cinematic product presentation trailer using ComfyUI.

Structure:
- models/ — Video models (Stable Video Diffusion, Hunyuan Video, Wan)
- workflows/ — ComfyUI workflow JSON files
- prompts/ — Text prompts for each scene
- renders/ — Generated video segments
- audio/ — Audio files (TTS, music, SFX)
"""

import json
from pathlib import Path

VIDEO_GEN_DIR = Path("assets/video_generation")
MODELS_DIR = VIDEO_GEN_DIR / "models"
WORKFLOWS_DIR = VIDEO_GEN_DIR / "workflows"
PROMPTS_DIR = VIDEO_GEN_DIR / "prompts"
RENDERS_DIR = VIDEO_GEN_DIR / "renders"
AUDIO_DIR = VIDEO_GEN_DIR / "audio"

# Create directories
for dir_path in [MODELS_DIR, WORKFLOWS_DIR, PROMPTS_DIR, RENDERS_DIR, AUDIO_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Scene Configuration
SCENES = {
    "scene_1_awakening": {
        "duration": 8,
        "description": "Awakening - Logo appears with particles and energy lines",
        "style": "Cinematic, dark, particles, energy lines, premium minimal",
        "camera": "Center zoom in",
        "audio": "Deep startup sound, technology advanced",
    },
    "scene_2_system_boot": {
        "duration": 10,
        "description": "System Boot - OWNEX modules initializing with HUD",
        "style": "Futuristic HUD, premium minimal, not exaggerated",
        "camera": "Progressive scan",
        "audio": "System initialization sounds, premium clicks",
    },
    "scene_3_desktop_alpha": {
        "duration": 15,
        "description": "Desktop ALPHA - Mission Control, agents, terminal, dashboards",
        "style": "Professional command center, dark theme, premium UI",
        "camera": "Pan across dashboard",
        "audio": "Ambient intelligence, soft interface sounds",
    },
    "scene_4_merlin_assistant": {
        "duration": 12,
        "description": "MERLIN AI Assistant - Intelligent interface, no humanoid",
        "style": "Geometric intelligence interface, hexagonal patterns, voice rings",
        "camera": "Focus on intelligence core",
        "audio": "Voice TTS (Piper/XTTS), interface sounds",
    },
    "scene_5_autonomous_agents": {
        "duration": 12,
        "description": "Autonomous Agents - Departments collaborating as digital company",
        "style": "Multiple agents working together, collaboration visualization",
        "camera": "Orbit shot around agents",
        "audio": "Ambient intelligent, collaboration sounds",
    },
    "scene_6_android_omega": {
        "duration": 12,
        "description": "Android OMEGA - Mobile Companion with HUD interface",
        "style": "Premium Android phone, HUD interface, notifications",
        "camera": "Focus on phone, then zoom out",
        "audio": "Mobile interface sounds, notification sounds",
    },
    "scene_7_smartwatch": {
        "duration": 8,
        "description": "Smartwatch - Wear OS with alerts and approvals",
        "style": "Circular interface, natural extension, not separate app",
        "camera": "Close-up on watch",
        "audio": "Smartwatch sounds, haptic feedback simulation",
    },
    "scene_8_ecosystem": {
        "duration": 10,
        "description": "Ecosystem Connected - Desktop → Mobile → Watch → Cloud → Agents",
        "style": "Connection visualization, data flow, network topology",
        "camera": "Flow through ecosystem",
        "audio": "Connection sounds, data flow audio",
    },
    "scene_9_final": {
        "duration": 8,
        "description": "Final - Logo OWNEX with tagline",
        "style": "Cinematic final logo, impact, premium",
        "camera": "Hero shot of logo",
        "audio": "Cinematic impact sound, music crescendo",
    },
}

# Visual Style Configuration
VISUAL_STYLE = {
    "primary_color": "#00F0FF",  # Cyan
    "secondary_color": "#00FF88",  # Emerald
    "background": "Deep Space Black",
    "accent": "White",
    "style_description": "Premium cyber intelligence, minimalist, elegant",
    "avoid": ["robots", "digital brains", "AI clichés", "excessive neon"],
}

# Audio Configuration
AUDIO_CONFIG = {
    "start": "Space system, technology advanced",
    "interface": "Premium clicks, soft sounds, confirmations",
    "agents": "Ambient intelligent",
    "final": "Cinematic impact",
    "tts_engine": "Piper / XTTS / equivalent open source",
    "music": "Ambient, cinematic, subtle",
}

# ComfyUI Configuration
COMFYUI_CONFIG = {
    "host": "127.0.0.1",
    "port": 8188,
    "models": {
        "video": ["Stable Video Diffusion", "Hunyuan Video", "Wan"],
        "image": ["FLUX Dev", "FLUX Schnell", "Stable Diffusion XL"],
    },
    "output_format": "mp4",
    "output_resolution": "1920x1080",
    "fps": 30,
}

# Save configuration
config = {
    "scenes": SCENES,
    "visual_style": VISUAL_STYLE,
    "audio_config": AUDIO_CONFIG,
    "comfyui_config": COMFYUI_CONFIG,
}

config_file = VIDEO_GEN_DIR / "config.json"
with open(config_file, "w") as f:
    json.dump(config, f, indent=2)

print(f"✓ Video generation structure created: {VIDEO_GEN_DIR}")
print("  - models/")
print("  - workflows/")
print("  - prompts/")
print("  - renders/")
print("  - audio/")
print(f"✓ Configuration saved: {config_file}")
print(f"  - {len(SCENES)} scenes configured")
print(f"  - Total duration: {sum(s['duration'] for s in SCENES.values())} seconds")
