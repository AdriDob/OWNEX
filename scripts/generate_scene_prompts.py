"""Generate scene prompts for OWNEX OMEGA video trailer.

Creates detailed prompts for each scene to be used with ComfyUI.
"""

from pathlib import Path
import json

PROMPTS_DIR = Path("assets/video_generation/prompts")

# Scene Prompts
SCENE_PROMPTS = {
    "scene_1_awakening": {
        "visual": "Screen fades from deep black to reveal OWNEX logo with cyan glow, particles of light converging, energy lines radiating outward, hexagonal geometric patterns forming, slow elegant animation, premium minimal style, no clutter, cinematic lighting",
        "camera": "Slow zoom in on logo, center frame",
        "duration": "8 seconds",
        "style": "Cinematic, Tesla-like startup, premium, minimalist"
    },
    "scene_2_system_boot": {
        "visual": "Futuristic HUD overlay showing OWNEX modules initializing: Memory Core ✓, Agent Network ✓, Mission Control ✓, Voice System ✓, Evolution Engine ✓, Security Layer ✓, clean typography, cyan and emerald status indicators, professional command center aesthetic, not exaggerated",
        "camera": "Progressive scan from top to bottom",
        "duration": "10 seconds",
        "style": "Linear-like HUD, SpaceX systems, premium minimal"
    },
    "scene_3_desktop_alpha": {
        "visual": "OWNEX ALPHA Desktop interface showing Mission Control dashboard with agent fleet panel, opportunity radar, activity timeline, system health metrics, dark theme with cyan accents, professional UI, agents working in background, terminal integrated, workflows visible, premium command center feel",
        "camera": "Pan across dashboard from left to right",
        "duration": "15 seconds",
        "style": "Apple-like minimal, premium dark UI, professional"
    },
    "scene_4_merlin_assistant": {
        "visual": "MERLIN Assistant interface as geometric intelligence core, hexagonal pattern with interconnected nodes, voice rings pulsing with audio, memory nodes connected to center, conversation panel with user-MERLIN dialogue, explanation engine panel showing Teach mode, no humanoid, no avatar, pure geometric intelligence representation",
        "camera": "Focus on intelligence core, slight rotation",
        "duration": "12 seconds",
        "style": "Linear-like minimal, geometric, no robots/brains cliché"
    },
    "scene_5_autonomous_agents": {
        "visual": "Autonomous agents collaborating as digital company, Architecture, Coding, QA, Research, Security, Documentation, Evolution departments working together, agent nodes communicating, data flowing between them, visualization of autonomous workforce, premium clean aesthetic",
        "camera": "Orbit shot around agent network",
        "duration": "12 seconds",
        "style": "Tesla-like automation visualization, premium"
    },
    "scene_6_android_omega": {
        "visual": "Premium Android phone showing OWNEX OMEGA interface, Mission Control dashboard mobile version, agent fleet monitor, push notifications, approval system, real-time sync, sleek modern phone, cyan and emerald accents, professional mobile UI, connected to desktop",
        "camera": "Focus on phone screen, then zoom out to show connection",
        "duration": "12 seconds",
        "style": "Apple-like premium mobile, sleek, professional"
    },
    "scene_7_smartwatch": {
        "visual": "Wear OS smartwatch with circular interface, system health indicator, pending approvals count, critical notifications, approval request UI, MERLIN summary, natural extension of system, not separate app feeling, premium circular design, cyan and emerald status",
        "camera": "Close-up on watch face",
        "duration": "8 seconds",
        "style": "Apple Watch premium, minimal, elegant"
    },
    "scene_8_ecosystem": {
        "visual": "Connected ecosystem visualization: Desktop ALPHA → Android OMEGA → Smartwatch → Cloud/Local AI → Agents, data flowing between all components, connection lines, network topology, real-time sync visualization, everything connected seamlessly",
        "camera": "Flow through ecosystem from desktop to watch",
        "duration": "10 seconds",
        "style": "SpaceX systems, clean network visualization, premium"
    },
    "scene_9_final": {
        "visual": "OWNEX logo appearing with text 'OWNEX' and tagline 'Build. Learn. Automate. Evolve.' below, subtext 'Your autonomous operating system', cinematic final logo shot, premium feel, cyan glow, deep black background, impact moment",
        "camera": "Hero shot of logo, slow zoom out",
        "duration": "8 seconds",
        "style": "Tesla-like final logo, cinematic impact, premium"
    }
}

# Boot Sequence Prompt (20 seconds bonus)
BOOT_SEQUENCE_PROMPT = {
    "visual": "PC powers on, OWNEX ALPHA appears, system health scan with HUD, MERLIN assistant greets with text 'Welcome back. Your system is ready.', Mission Control dashboard opens, agents initialize, smooth premium animation, 20 seconds total, boot sequence like Tesla startup",
    "camera": "Follow boot process linearly",
    "duration": "20 seconds",
    "style": "Tesla startup animation, space console, clean futuristic military systems"
}

# Save prompts
with open(PROMPTS_DIR / "scene_prompts.json", "w") as f:
    json.dump(SCENE_PROMPTS, f, indent=2)

with open(PROMPTS_DIR / "boot_sequence_prompt.json", "w") as f:
    json.dump(BOOT_SEQUENCE_PROMPT, f, indent=2)

print(f"✓ Scene prompts saved: {PROMPTS_DIR / 'scene_prompts.json'}")
print(f"  - {len(SCENE_PROMPTS)} scene prompts")
print(f"✓ Boot sequence prompt saved: {PROMPTS_DIR / 'boot_sequence_prompt.json'}")
print(f"  - 20 seconds boot sequence")
