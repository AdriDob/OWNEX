# OWNEX Brand Identity v4 — "The Signal"

> A refined geometric identity. Deterministic, vector-first, reproducible.
> Pipeline: `scripts/brand/` (Python + cairosvg + Pillow + fontTools).

---

## 1. The Mark — "The Signal"

**Concept:** Two intersecting bars at 45° and 135° with a precise negative-space gap at the center — a clean intersection that reads as both a signal crossing and a monogram. A subtle outer ring and a 8px center node complete the composition.

**Design principles:**
- **Precision over ornament** — exact geometry, no hand-drawn approximation
- **Negative space as feature** — the center gap is the signature
- **Works at 32px** — bold variant for favicon/UI, mono variants for dark/light
- **Two editions, one geometry** — ALPHA (cyan→blue) / OMEGA (emerald→cyan)

---

## 2. Geometry (512px canonical space)

| Parameter | Value | Purpose |
|---|---|---|
| `MARK_R` | 220 | Outer bounding radius |
| `BAR_W` | 38 | Bar thickness |
| `BAR_GAP` | 8 | Center intersection gap |
| `ARM_LEN` | 200 | Arm length from center |
| `END_R` | 12 | Rounded end radius |
| `RING_R` | 248 | Subtle outer ring radius |
| `RING_SW` | 2.5 | Ring stroke weight |

**Angles:** 45° + 225° (main axis), 135° + 315° (secondary axis)

---

## 3. Color System

| Token | Hex | Usage |
|---|---|---|
| **Cyber Cyan** | `#00D5FF` | ALPHA primary, key actions |
| **Deep Blue** | `#1E40FF` | ALPHA secondary, depth |
| **Emerald** | `#00E39A` | OMEGA primary, success, growth |
| **Space Black** | `#05060A` | Global background |
| Surface 1 | `#0B0E15` | Cards, panels |
| Surface 2 | `#11151F` | Nested surfaces |
| Stroke | `#1D2430` | Borders, dividers |
| White | `#F6F8FB` | Primary text |
| Muted | `#8A94A6` | Secondary text |

**Gradients:** ALPHA = cyan→blue, OMEGA = emerald→cyan

---

## 4. Typography

| Role | Family | Weights | Source |
|---|---|---|---|
| Display | **Space Grotesk** | 500, 700 | Google Fonts (SIL OFL) |
| UI | **Inter** | 400–700 | Google Fonts (SIL OFL) |
| Mono | **JetBrains Mono** | 400, 500 | Google Fonts (SIL OFL) |

Vendored in `assets/branding/fonts/` — 3 variable fonts + 10 static instances.

---

## 5. Logo System (19 files)

| Asset | File | Use |
|---|---|---|
| Primary mark | `assets/logos/ownex-mark.svg/.png` | App icon, docs, generic |
| Horizontal lockup | `assets/logos/ownex-lockup.svg/.png` | README header, site |
| ALPHA edition | `assets/logos/ownex-alpha.svg/.png` | Desktop context |
| OMEGA edition | `assets/logos/ownex-omega.svg/.png` | Mobile/wear context |
| App icon | `assets/logos/ownex-icon.svg/.png` | 1024px rounded |
| Favicon | `assets/logos/ownex-favicon.svg/.png` | 64px bold |
| UI mark 32px | `assets/logos/ownex-ui-32px.png` | Toolbars, menus (bold) |
| Monochrome white | `assets/logos/ownex-monochrome.svg/.png` | Dark surfaces |
| Monochrome black | `assets/logos/ownex-monochrome-black.svg/.png` | Light surfaces |
| Mono lockup | `assets/logos/ownex-lockup-mono.svg/.png` | Watermark, favicon fallback |

**Clearance:** ≥ ¼ mark height on all sides. **Minimum:** 24px mark, 32px lockup.

---

## 6. Imagery Direction

- Canvas: Space Black with fine blueprint grid (120–150px)
- Cards: Surface 1 + Stroke border, rounded 16
- Accent: one gradient per composition (cyan for ALPHA, emerald for OMEGA)
- Captions: JetBrains Mono, uppercase, letter-spaced
- Engineering crop marks at corners
- Footer status strip: mono, system-state language
- All rendered from deterministic pipeline — no AI generation, no stock

---

## 7. Asset Map

```
assets/
├── branding/          design-tokens.json, fonts/, OWNEX_BRAND_IDENTITY.md
├── logos/             19 files (mark, lockups, icon, favicon, mono, editions)
├── banners/           hero-banner (2400×1260), og-cover (1200×630)
├── concepts/          5 artworks 2400×1350
│   ├── product-overview.png
│   ├── mission-control.png
│   ├── architecture.png
│   ├── mobile-omega.png
│   └── boot-sequence.png
├── desktop/           alpha-wallpaper 2560×1440
├── mobile/            omega-splash 1080×2400
└── video/             trailer-storyboard.md
```

---

## 8. Pipeline

`scripts/brand/` — 6 modules:
- `pipeline.py` — core geometry, gradients, SVG→PNG render, text compositing
- `generate_logos.py` — 19 logo variants
- `generate_banners.py` — hero + OG cover
- `generate_concepts.py` — 5 concept artworks
- `generate_wallpapers.py` — desktop + mobile
- `textlib.py` — shared text definitions (SVG + PIL)

**Regenerate all:** `python scripts/brand/generate_logos.py && python scripts/brand/generate_banners.py && python scripts/brand/generate_concepts.py && python scripts/brand/generate_wallpapers.py`

---

## 9. License

Brand geometry & concept art: MIT. Fonts: SIL OFL 1.1 (vendored).