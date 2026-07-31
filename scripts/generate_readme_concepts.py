#!/usr/bin/env python3
"""
OWNEX README Conceptual Images Generator
=========================================
Genera imágenes conceptuales para las secciones del README con el estilo
visual Tesla (minimalista, negro mate, acento azul eléctrico, glows sutiles)
y la taxonomía OWNEX original de Work Cycles:

  FORGE   → Dev Bounty (Superteam, Opire, TaskBounty)      [azul]
  PULSE   → AI Work (Outlier, DataAnnotation, Mindrift)    [verde]
  VAULT   → Wealth (capital, payouts, revenue)             [dorado]
  ATLAS   → Intelligence (mercados, señales)               [púrpura]
  SECURITY→ Bug bounty (Rastro)                            [rojo]
  ODYSSEY → Predictive markets                             [cyan]

- Fondos conceptuales: generados con IA open-source (Pollinations.ai / Flux)
- Composición final: tipografía OWNEX + branding vectorial nítidos con PIL
"""

from __future__ import annotations

import os
from io import BytesIO
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

# ── OWNEX Tesla Palette ────────────────────────────────────────────────
BG = (5, 6, 10)
BLUE = (59, 130, 246)
BLUE_LIGHT = (96, 165, 250)
WHITE = (245, 245, 245)
GRAY = (100, 116, 139)
GOLD = (245, 158, 11)
GREEN = (52, 211, 153)
PURPLE = (167, 139, 250)
RED = (239, 68, 68)
CYAN = (34, 211, 238)

FONT_DIR = "/usr/share/fonts/truetype/lato"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def ai_background(prompt: str, width: int, height: int, seed: str, model: str = "flux") -> Image.Image | None:
    """Genera un fondo conceptual con IA open-source (Flux vía Pollinations)."""
    url = (
        "https://image.pollinations.ai/prompt/"
        f"{quote(prompt)}?width={width}&height={height}"
        f"&nologo=true&model={model}&seed={seed}&enhance=true"
    )
    try:
        print(f"  IA generando [{seed}] {width}x{height} ...")
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        return img.resize((width, height), Image.Resampling.LANCZOS)
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ fallo IA ({e}); usando fallback oscuro")
        return None


def dark_fallback(width: int, height: int, accent: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        c = tuple(int(BG[i] + (accent[i] - BG[i]) * ratio * 0.10) for i in range(3))
        d.line([(0, y), (width, y)], fill=c)
    return img


def overlay_vinette(img: Image.Image, strength: float = 0.35) -> Image.Image:
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    dm = ImageDraw.Draw(mask)
    dm.ellipse([-int(w * 0.2), -int(h * 0.2), int(w * 1.2), int(h * 1.2)], fill=int(255 * (1 - strength)))
    mask = mask.filter(ImageFilter.GaussianBlur(60))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    img = Image.composite(img, dark, mask)
    return img


def mix(c: tuple[int, int, int], a: float) -> tuple[int, int, int]:
    return (int(c[0] * a + BG[0] * (1 - a)), int(c[1] * a + BG[1] * (1 - a)), int(c[2] * a + BG[2] * (1 - a)))


def draw_ownex_mark(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    """Dibuja el logomark 'O' de OWNEX."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=mix(BLUE, 0.9), width=max(2, r // 12))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=mix(WHITE, 0.12), width=1)
    inner = int(r * 0.55)
    d.ellipse([cx - inner, cy - inner, cx + inner, cy + inner], outline=mix(BLUE_LIGHT, 0.35), width=1)
    # gold accent dot (top-right of O)
    gx, gy = int(cx + r * 0.70), int(cy - r * 0.70)
    dot = max(2, int(r * 0.10))
    d.ellipse([gx - dot, gy - dot, gx + dot, gy + dot], fill=mix(GOLD, 1.0))
    # inner dot
    ir = max(2, r // 8)
    d.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=mix(WHITE, 0.95))
    d.ellipse([cx - ir * 3, cy - ir * 3, cx + ir * 3, cy + ir * 3], fill=mix(BLUE_LIGHT, 0.45))


def text_width(d: ImageDraw.ImageDraw, txt: str, fnt: ImageFont.FreeTypeFont) -> int:
    b = d.textbbox((0, 0), txt, font=fnt)
    return int(b[2] - b[0])


def compose_card(
    bg: Image.Image | None,
    out: str,
    *,
    title: str,
    subtitle: str,
    tag: str,
    accent: tuple[int, int, int] = BLUE,
    w: int = 1600,
    h: int = 700,
) -> None:
    """Compone la card final: fondo IA + logomark + tipografía OWNEX."""
    img = bg if bg is not None else dark_fallback(w, h, accent)
    img = overlay_vinette(img, 0.42)

    d = ImageDraw.Draw(img, "RGBA")

    # ── Logo mark ──
    draw_ownex_mark(d, int(w * 0.50), int(h * 0.28), int(h * 0.15))

    # ── OWNEX wordmark ──
    f_word = font("Lato-Bold.ttf", int(h * 0.060))
    word = "OWNEX"
    tw = text_width(d, word, f_word)
    for dx in range(3):
        d.text((int(w * 0.5) - tw // 2 + dx, int(h * 0.205) + dx), word, font=f_word, fill=(59, 130, 246, 28))
    d.text((int(w * 0.5) - tw // 2, int(h * 0.205)), word, font=f_word, fill=WHITE)

    # thin accent rule
    rw = int(tw * 0.9)
    d.rectangle(
        [int(w * 0.5) - rw // 2, int(h * 0.295), int(w * 0.5) + rw // 2, int(h * 0.295) + max(2, int(h * 0.004))],
        fill=(*accent, 190),
    )

    # ── Title ──
    f_title = font("Lato-Bold.ttf", int(h * 0.058))
    ttw = text_width(d, title, f_title)
    d.text((int(w * 0.5) - ttw // 2, int(h * 0.36)), title, font=f_title, fill=WHITE)

    # ── Subtitle ──
    f_sub = font("Lato-Regular.ttf", int(h * 0.026))
    stw = text_width(d, subtitle, f_sub)
    d.text((int(w * 0.5) - stw // 2, int(h * 0.44)), subtitle, font=f_sub, fill=GRAY)

    # ── Tag pill ──
    f_tag = font("Lato-Bold.ttf", int(h * 0.022))
    pad = int(h * 0.016)
    twd = text_width(d, tag, f_tag) + pad * 2
    box_h = int(h * 0.052)
    bx = int(w * 0.5) - twd // 2
    by = int(h * 0.52)
    d.rounded_rectangle(
        [bx, by, bx + twd, by + box_h], radius=box_h // 2, fill=(*accent, 26), outline=(*accent, 160), width=1
    )
    d.text((int(w * 0.5) - twd // 2 + pad, by + int(h * 0.012)), tag, font=f_tag, fill=accent)

    # ── bottom hairline ──
    d.line([(int(w * 0.06), int(h * 0.96)), (int(w * 0.94), int(h * 0.96))], fill=(30, 41, 59, 200), width=1)

    img.save(out, "PNG")
    print(f"  ✓ {os.path.basename(out)} ({w}x{h})")


def generate() -> None:
    os.makedirs(ASSETS, exist_ok=True)
    seed_base = "ownex-cycles-2026"

    # ── Portada (hero) ──
    print("▶ Portada / Hero")
    hero_prompt = (
        "ultra minimalist premium technology hero banner, matte black carbon background, "
        "sleek electric blue thin light lines and geometric grid vanishing to horizon, "
        "soft blue rim lighting, subtle depth of field, futuristic command center aesthetic, "
        "tesla product keynote style, cinematic, clean composition, high detail, no text"
    )
    bg = ai_background(hero_prompt, 1600, 700, f"{seed_base}-hero")
    compose_card(
        bg,
        os.path.join(ASSETS, "concept-hero.png"),
        title="Autonomous Work Operating System",
        subtitle="Forge · Pulse · Vault · Atlas — a command center that works for you 24/7",
        tag="OWNEX ALPHA · OMEGA",
        accent=BLUE,
    )

    # ── FORGE — Dev Bounty ──
    print("▶ FORGE — Dev Bounty")
    forge_prompt = (
        "abstract software development and code bounty concept, glowing blue and cyan code "
        "fragments and terminal windows floating on dark background, premium minimal tech "
        "aesthetic, tesla keynote style, cinematic, no text"
    )
    bg = ai_background(forge_prompt, 1600, 700, f"{seed_base}-forge")
    compose_card(
        bg,
        os.path.join(ASSETS, "concept-forge.png"),
        title="FORGE",
        subtitle="Dev Bounty — Superteam · Opire · TaskBounty · CoderAgent",
        tag="DEV BOUNTY",
        accent=BLUE,
    )

    # ── PULSE — AI Work ──
    print("▶ PULSE — AI Work")
    pulse_prompt = (
        "abstract artificial intelligence and data annotation concept, glowing green and cyan "
        "connection nodes over dark background, flowing data streams, premium minimal tech, "
        "tesla keynote style, cinematic, no text"
    )
    bg = ai_background(pulse_prompt, 1600, 700, f"{seed_base}-pulse")
    compose_card(
        bg,
        os.path.join(ASSETS, "concept-pulse.png"),
        title="PULSE",
        subtitle="AI Work — Outlier · DataAnnotation · Mindrift",
        tag="AI WORK",
        accent=GREEN,
    )

    # ── VAULT — Wealth ──
    print("▶ VAULT — Wealth")
    vault_prompt = (
        "abstract wealth and capital concept, glowing gold and blue ascending bars and charts, "
        "dark premium background, elegant data visualization, tesla keynote style, "
        "cinematic lighting, depth of field, no text"
    )
    bg = ai_background(vault_prompt, 1600, 700, f"{seed_base}-vault")
    compose_card(
        bg,
        os.path.join(ASSETS, "concept-vault.png"),
        title="VAULT",
        subtitle="Wealth — Revenue intelligence · Payouts · Capital dashboard",
        tag="WEALTH",
        accent=GOLD,
    )

    # ── ATLAS — Intelligence ──
    print("▶ ATLAS — Intelligence")
    atlas_prompt = (
        "abstract market intelligence concept, glowing purple and blue radar and constellation "
        "networks over dark background, premium minimal tech aesthetic, tesla keynote style, "
        "cinematic, no text"
    )
    bg = ai_background(atlas_prompt, 1600, 700, f"{seed_base}-atlas")
    compose_card(
        bg,
        os.path.join(ASSETS, "concept-atlas.png"),
        title="ATLAS",
        subtitle="Intelligence — Market signals · Opportunity scoring · Atlas",
        tag="INTELLIGENCE",
        accent=PURPLE,
    )

    # ── SECURITY — Bug Bounty (Rastro) ──
    print("▶ SECURITY — Bug Bounty")
    security_prompt = (
        "cybersecurity command center abstract, dark digital shield made of glowing red and blue "
        "hexagons, grid wireframe, subtle scan lines, premium minimal tech aesthetic, tesla "
        "keynote style, cinematic, no text"
    )
    bg = ai_background(security_prompt, 1600, 700, f"{seed_base}-security")
    compose_card(
        bg,
        os.path.join(ASSETS, "concept-security.png"),
        title="SECURITY",
        subtitle="Bug Bounty — Recon → Hypothesis → Validation → Evidence → Report",
        tag="BUG BOUNTY",
        accent=RED,
    )

    # ── ODYSSEY — Predictive Markets ──
    print("▶ ODYSSEY — Predictive Markets")
    odyssey_prompt = (
        "abstract predictive markets concept, glowing cyan orbs and orbital rings over dark "
        "background, constellation network, premium minimal tech aesthetic, tesla keynote style, "
        "cinematic, no text"
    )
    bg = ai_background(odyssey_prompt, 1600, 700, f"{seed_base}-odyssey")
    compose_card(
        bg,
        os.path.join(ASSETS, "concept-odyssey.png"),
        title="ODYSSEY",
        subtitle="Predictive Markets — Betting · Probability models",
        tag="PREDICTIVE MARKETS",
        accent=CYAN,
    )

    print("\n✅ Todas las imágenes conceptuales generadas en assets/")


if __name__ == "__main__":
    generate()
