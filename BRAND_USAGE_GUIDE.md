# OWNEX Brand Usage Guide

Guidelines for using OWNEX brand assets consistently across all touchpoints.

## Brand Assets Location

All brand assets are located in the `assets/` directory:

```
assets/
├── logos/              # Logo files (SVG + PNG)
├── branding/          # Brand identity documentation
├── banners/           # Hero banners
├── concepts/          # Concept art
├── screenshots/       # Application screenshots
└── video/             # Video assets
```

## Logo System

### Primary Logos

| Logo | Format | Usage |
|------|--------|-------|
| **OWNEX Mark** | SVG, PNG | Icon, favicon, small spaces |
| **OWNEX ALPHA** | SVG, PNG | Desktop edition branding |
| **OWNEX OMEGA** | SVG, PNG | Mobile edition branding |
| **OWNEX Lockup** | SVG, PNG | Horizontal lockup for headers |
| **OWNEX Icon** | SVG, PNG | App icon, launcher |

### Logo Variants

- **Color**: Full color branding (default)
- **Monochrome**: Single color for restricted contexts
- **Mono Black**: Black only for high contrast
- **UI 32px**: Optimized for UI elements

### Logo Usage Rules

1. **Minimum Size**: 32px for UI, 120px for print
2. **Clear Space**: Maintain 1x logo height clear space
3. **Background**: Use light or dark backgrounds, never mid-tone
4. **Distortion**: Never stretch or alter aspect ratio
5. **Modifications**: Never modify colors, shapes, or proportions

## Color System

### Primary Colors

```css
--ownex-cyber-cyan: #00D5FF;
--ownex-deep-blue: #0B0E15;
--ownex-emerald: #00E39A;
--ownex-space-black: #07090F;
```

### Secondary Colors

```css
--ownex-surface-1: #16213A;
--ownex-surface-2: #1D2430;
--ownex-surface-3: #3D4A63;
--ownex-muted: #8A94A6;
--ownex-text-primary: #F6F8FB;
--ownex-text-secondary: #C4CBD5;
```

### Color Usage

- **Cyber Cyan**: CTAs, highlights, success states
- **Deep Blue**: Primary backgrounds, UI elements
- **Emerald**: Success, validation, positive feedback
- **Space Black**: Main background, depth
- **Muted**: Secondary text, disabled states

## Typography

### Font Families

```css
--font-display: 'Space Grotesk', sans-serif;
--font-body: 'Inter', sans-serif;
--font-mono: 'JetBrains Mono', monospace;
```

### Typography Scale

| Level | Size | Weight | Usage |
|-------|------|--------|-------|
| H1 | 48px | 700 | Page titles |
| H2 | 36px | 600 | Section headers |
| H3 | 24px | 500 | Subsections |
| Body | 16px | 400 | Body text |
| Small | 14px | 400 | Captions |
| Mono | 14px | 400 | Code, data |

### Typography Rules

1. **Line Height**: 1.5 for body, 1.2 for headings
2. **Letter Spacing**: 0.01em for headings, normal for body
3. **Case**: Title case for headings, sentence case for body
4. **Max Width**: 75 characters for body text

## Component Branding

### Mission Control

- **Color**: Cyber Cyan + Deep Blue
- **Style**: Dashboard, grid-based, metrics-focused
- **Tone**: Professional, technical, precise

### MERLIN Assistant

- **Color**: Emerald + Space Black
- **Style**: Conversational, clean, accessible
- **Tone**: Helpful, intelligent, patient

### Agent Fleet

- **Color**: Cycle-based (Security/Forge/Pulse/Vault/Atlas/Odyssey)
- **Style**: Status indicators, activity cards
- **Tone**: Dynamic, operational, fleet-focused

## Application Branding

### Desktop (ALPHA)

- **Window Title**: "OWNEX ALPHA - Mission Control"
- **Icon**: ownex-icon.png
- **Color Scheme**: Deep Blue + Cyber Cyan
- **Window Frame**: Space Black with Cyan accents

### Mobile (OMEGA)

- **App Name**: "OWNEX OMEGA"
- **Icon**: ownex-icon.png
- **Color Scheme**: Emerald + Deep Blue
- **Navigation**: Bottom tab bar with colored indicators

## Web Branding

### Website Headers

- **Logo**: OWNEX Lockup (left aligned)
- **Background**: Space Black
- **CTA**: Cyber Cyan button
- **Navigation**: White text on hover

### Documentation

- **Logo**: OWNEX Mark (small)
- **Background**: White/Space Black toggle
- **Headings**: Deep Blue text
- **Code Blocks**: Surface-1 background

## Print Branding

### Business Cards

- **Front**: OWNEX Mark + Name + Title
- **Back**: Contact info + QR code
- **Colors**: Black + White + Cyan accent
- **Paper**: Matte finish, 300gsm

### Presentations

- **Title Slide**: OWNEX Lockup + Title
- **Content**: White background, dark text
- **Charts**: OWNEX color palette
- **Footer**: OWNEX Mark + page number

## Digital Marketing

### Social Media

- **Avatar**: OWNEX Mark (circular)
- **Header**: OWNEX Lockup + tagline
- **Posts**: Cyan accent colors
- **Stories**: Full-screen OWNEX branding

### Email Signatures

```
[OWNEX Mark]
Your Name
Title
OWNEX — Autonomous Personal Operating System
https://ownex.ai
```

## Video Branding

### Intro Sequence

1. OWNEX Mark fade-in (2s)
2. Text: "OWNEX" (1s)
3. Text: "Autonomous Personal Operating System" (2s)
4. Fade to content (1s)

### Outro Sequence

1. OWNEX Mark fade-in (1s)
2. Text: "OWNEX" (1s)
3. URL: "https://ownex.ai" (2s)
4. Fade to black (1s)

## Asset Generation

All brand assets are generated deterministically using the pipeline in `scripts/brand/`:

```bash
# Generate all logos
cd scripts/brand
python generate_logos.py

# Generate concept art
python generate_concepts.py

# Generate wallpapers
python generate_wallpapers.py
```

## Brand Guidelines Compliance

### Do's

✅ Use official logo files from `assets/logos/`
✅ Maintain minimum clear space around logos
✅ Use official color palette
✅ Follow typography scale
✅ Use appropriate logo for context (ALPHA vs OMEGA)

### Don'ts

❌ Modify logo colors or shapes
❌ Stretch or distort logos
❌ Use unofficial colors
❌ Mix fonts outside the system
❌ Use logos on mid-tone backgrounds

## Brand Asset Requests

For custom brand assets or variations:

1. Check existing assets in `assets/`
2. Review brand identity documentation
3. Submit request with specific requirements
4. Allow 2-3 business days for delivery

## Brand Maintenance

Brand assets are updated quarterly:

- **Q1**: Logo refinements
- **Q2**: Color palette review
- **Q3**: Typography updates
- **Q4**: New asset generation

## Brand Guidelines Version

- **Current Version**: 1.0
- **Last Updated**: 2026-08-01
- **Next Review**: 2026-11-01

## Contact

For brand-related questions:
- Email: brand@ownex.ai
- Documentation: assets/branding/OWNEX_BRAND_IDENTITY.md
- Design Tokens: assets/branding/design-tokens.json

---

**OWNEX Brand System v1.0**
**Autonomous Personal Operating System**
