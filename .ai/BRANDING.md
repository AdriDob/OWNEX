# OWNEX Branding — Single Source of Truth

> **The Aperture Nexus.** Deterministic, GPU-free, 100% reproducible. Zero generative AI.
> This is the canonical reference for all visual identity decisions. Update this first; `scripts/brand/` implements.

## Mark

**OWNEX mark — "The Aperture Nexus"**
- Octagonal ring (precision instrument) + X of conics from a central square node (core intelligence) + lightning bolt breaking the ring at the top-right (evolution core→edge).
- Two geometry-locked editions (same mark, different color):
  - **ALPHA** — desktop (Tesla blue `cyan→blue`)
  - **OMEGA** — mobile/wear companion (emerald→cyan)
- All renders produced deterministically in `scripts/brand/render_hero_assets.py` from `cores/brand/mark_spec.py`.

## Color System

**Tesla dark** — no noise, no glow, no neon gradients.

| Token | Value | Use |
|---|---|---|
| `space_black` | `#05060A` | Page/surface background |
| `deep_blue` | `#1E40FF` | Primary accent, links, OWNEX mark |
| `cyber_cyan` | `#00D5FF` | Secondary accent (OMEGA edition) |
| `emerald` | `#00E39A` | Success state / alternative accent |
| `white` | `#F6F8FB` | Primary text |
| `muted` | `rgba(246,248,251,0.6)` | Secondary/diminished text |
| `stroke` | `rgba(246,248,251,0.06)` | Hairline dividers |
| `red` | `#e82127` | Destructive / error (Tesla red accent) |

### Light mode palette

| Token | Value | Use |
|---|---|---|
| `bg` | `#FFFFFF` | Light background |
| `text` | `#1F2328` | Primary text |
| `border` | `#EAECEF` | Dividers |

**Rule:** never use arbitrary RGB. All colors must map to a named token. The full editable SSOT lives in `assets/branding/design-tokens.json`.

## Typography

| Role | Font | Source |
|---|---|---|
| Display (logo, hero) | Space Grotesk | `assets/branding/fonts/space-grotesk/` (SIL OFL) |
| UI body | Inter | `assets/branding/fonts/inter/` (SIL OFL) |
| Monospace (terminal, code) | JetBrains Mono | `assets/branding/fonts/jetbrains-mono/` (SIL OFL) |

All fonts vendored (no Google Fonts runtime fetch). `scripts/brand/textlib.py` renders text with PIL from these paths.

## Asset Registry

Everything deterministic lives under `docs/assets/branding/` and `docs/assets/screenshots/`.

| Asset | Path | Notes |
|---|---|---|
| Hero banner | `docs/assets/branding/banners/ownex-hero-banner.png` (2400×900) | Tesla gradient + O+X mark |
| Footer banner | `docs/assets/branding/banners/ownex-footer.png` (2400×420) | Compact footer |
| Hero mark | `docs/assets/branding/logo/ownex-mark-hero.png` (1024×1024) | Used in splash/boot |
| App badge | `docs/assets/branding/logo/ownex-mark-badge.png` (512×512) | App icon / notifications |
| Light mark | `docs/assets/branding/logo/ownex-mark-light.png` | For white/light contexts |
| Dark mark | `docs/assets/branding/logo/ownex-light-mode.{svg,png}` / `ownex-dark-mode.{svg,png}` | Toggle by `prefers-color-scheme` |
| Favicon | `docs/assets/branding/logo/ownex-favicon.{svg,png}` | 64px |
| Social preview | `docs/assets/branding/social/ownex-social-preview.png` (1200×630) | GitHub `.github/social-preview.png` + copy |
| Light screenshots | `docs/assets/screenshots/desktop-light/*.png` | Product captures (light theme) |
| Dark screenshots | `docs/assets/screenshots/desktop/*.png` | Product captures (dark theme) |
| Design tokens | `assets/branding/design-tokens.json` | Canonical color/style tokens |

## Regeneration Pipeline

`scripts/brand/regenerate.sh` orchestrates every step:

```
1. scripts/brand/generate_ownex_logo.py       # SVG + PNG logo system
2. scripts/brand/generate_ownex_banners.py    # hero + footer banners
3. scripts/brand/render_hero_assets.py        # high-fidelity PNG renders (mark/hero/badge/social)
4. scripts/brand/sync_readme_bages.py         # README badges (version + test count from SSOT)
5. scripts/brand/optimize_assets.py           # screenshot palette quantization
6. scripts/brand/validate_assets.py           # checks all asset references resolve
```

`--shots` adds `node scripts/capture_screenshots.mjs dark|light` (Playwright, requires servers on :8000/:5173 — **no browser/Playwright runs in headless CI without a display server**).

## Fonts & Licensing

- Fonts: Space Grotesk, Inter, JetBrains Mono — all SIL OFL, vendored under `assets/branding/fonts/`.
- `textlib.py` (fontTools) instances static `@font-face` per family; PIL composites text (cairosvg cannot render `<text>`).
- License files: `assets/branding/fonts/OFL.txt`.

## Conventions

- **Brand name:** OWNEX (not Rastro/CATEYE/ORION in user-facing text). Backend paths stay `core/` internally.
- **No generative AI** for any visual asset. If you need a new render, extend `render_hero_assets.py`.
- **Assets are not versioned in git history.** If a render changes visually, re-run the pipeline and re-sync `.github/social-preview.png`.
