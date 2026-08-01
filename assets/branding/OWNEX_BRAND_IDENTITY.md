# OWNEX Brand Identity

> **Version 3.0** — "The Aperture Nexus"
> A deterministic, vector-first identity system. No stock imagery, no AI-generated
> randomness: every asset is produced from exact geometry by a reproducible pipeline
> (`scripts/brand/`).

---

## 1. The Mark

**Name:** The Aperture Nexus

**Concept:** An octagonal aperture ring — precision instrument language — crossed by an
X of tapered rays radiating from a central square node. The top-right ray breaks through
the aperture: intelligence at the core, evolution toward the edge.

```
  ┌─────────────────────────────┐
  │  aperture ring (octagon)    │  ← the system, the loop, precision
  │    X of tapered rays        │  ← OWNEX, convergence, distributed signal
  │    central square node      │  ← the intelligence core
  │    top-right ray breakout   │  ← evolution: ALPHA core → OMEGA edge
  └─────────────────────────────┘
```

**Meaning map**

| Element | Meaning |
|---|---|
| Octagonal aperture | Precision instrument, engineered system |
| X of rays | OWNEX — intersection of human decision and autonomous execution |
| Tapered rays (narrow at core → wide at tips) | Signal radiating from the core |
| Square node (not a dot) | Engineering precision; the decision point |
| Aperture gap + breakout ray | Growth, evolution, extension to devices |

**Forbidden elements** (never use): brains, robots, eyes, circuit traces, holograms,
orbiting-dot clichés, cartoon characters, photo textures.

---

## 2. The Two Editions

One mark. Two connected identities.

| Edition | Role | Color treatment | Tag |
|---|---|---|---|
| **OWNEX ALPHA** | Desktop Operating System — the command center | Cyber Cyan → Deep Blue gradient | `ALPHA — DESKTOP OPERATING SYSTEM` |
| **OWNEX OMEGA** | Android + Wear OS Companion — permanent connection | Emerald → Cyber Cyan gradient | `OMEGA — MOBILE COMPANION` |

The mark geometry is **identical** in both editions. Identity difference lives in color
and framing only — the editions must always be recognizable as one ecosystem.

---

## 3. Color System

| Token | Hex | Usage |
|---|---|---|
| **Cyber Cyan** `primary` | `#00D5FF` | Key elements, focus, links, active states |
| **Deep Blue** `secondary` | `#1E40FF` | Depth, gradients, secondary accents |
| **Emerald** `accent` | `#00E39A` | Success, growth, OMEGA edition |
| **Space Black** `background` | `#05060A` | Global background |
| Surface 1 | `#0B0E15` | Cards, panels |
| Surface 2 | `#11151F` | Nested surfaces |
| Stroke | `#1D2430` | Borders, dividers |
| White | `#F6F8FB` | Primary text |
| Muted | `#8A94A6` | Secondary text |

**Rules**

- Space Black is the default background. Cyan is reserved for what matters.
- Do not use more than one accent hue per view. Cyan is the hero; Emerald marks success
  or the OMEGA edition; Deep Blue only in gradients.
- Text contrast: white/muted only — never colored text for body copy.

---

## 4. Typography

| Role | Family | Weights | Usage |
|---|---|---|---|
| Display | **Space Grotesk** | 500, 700 | Wordmark, headlines |
| UI | **Inter** | 400–700 | Body, UI, documentation |
| Mono | **JetBrains Mono** | 400, 500 | Labels, technical captions, terminal |

**Voice:** precise, measured, understated. Full sentences in headlines; mono labels in
uppercase with letter-spacing for system captions.

All three families are licensed under SIL Open Font License 1.1 (Google Fonts) and are
vendored in `assets/branding/fonts/` for deterministic rendering.

---

## 5. Logo System

| Asset | File | Use |
|---|---|---|
| Primary mark (transparent) | `assets/logos/ownex-mark.svg/.png` | Everywhere: docs, app, web |
| Horizontal lockup | `assets/logos/ownex-lockup.svg/.png` | README, site header |
| App icon | `assets/logos/ownex-icon.svg/.png` | Application icon (squircle) |
| Favicon | `assets/logos/ownex-favicon.svg/.png` | Browser tab (64px) |
| UI mark 32px | `assets/logos/ownex-ui-32px.png` | Toolbars, menus (bold variant) |
| Monochrome white | `assets/logos/ownex-monochrome.svg/.png` | Dark surfaces |
| Monochrome black | `assets/logos/ownex-monochrome-black.svg/.png` | Light surfaces |
| ALPHA lockup | `assets/logos/ownex-alpha.svg/.png` | ALPHA edition |
| OMEGA lockup | `assets/logos/ownex-omega.svg/.png` | OMEGA edition |
| Mono lockup | `assets/logos/ownex-lockup-mono.svg/.png` | Favicon/watermark contexts |

**Clearance:** keep at least one quarter of the mark's height free on all sides.
**Minimum size:** 24px for the mark, 32px for lockups. **Do not** re-color, add
gradients, drop shadows, or distort the geometry.

---

## 6. Imagery Direction

All conceptual artwork follows a single art direction:

- Space-black canvas with a fine blueprint grid
- Thin mono captions in uppercase, letter-spaced
- Rounded-16 cards on Surface 1 with Stroke borders
- One gradient accent per composition; emerald reserved for status/growth
- Engineering crop marks at corners
- Footer strip with mono status line — the system always "reports state"

**Produced with:** Python + cairosvg + fontTools (open source). No AI image generators,
no stock photos — the images are deterministic output of `scripts/brand/generate_*.py`.

---

## 7. Asset Map

```
assets/
├── branding/          design tokens, fonts, this document
├── logos/             mark + lockups (SVG + PNG)
├── banners/           hero banner, OG cover
├── concepts/          product overview, mission control, architecture,
│                      mobile experience, boot sequence
├── desktop/           ALPHA wallpaper
├── mobile/            OMEGA splash
└── video/             trailer storyboard
```

## 8. License

Brand geometry and concept artwork: MIT (same as the project).
Fonts: SIL OFL 1.1 — see `assets/branding/fonts/`.
