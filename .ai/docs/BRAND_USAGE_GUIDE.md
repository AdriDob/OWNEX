# OWNEX Brand Usage Guide v2.0

Guidelines for using OWNEX brand assets consistently across all touchpoints.

## Brand Philosophy

OWNEX represents precision, autonomy, and evolution. The brand communicates engineering excellence through extreme restraint, mathematical precision, and functional design.

**Inspired by:** Linear, Vercel, Tesla
**Core principle:** Every pixel has purpose. Decoration is latency made visible.

---

## Brand Assets Location

All brand assets are located in the `assets/` directory:

```
assets/
├── logos/              # Logo files (SVG + PNG)
├── branding/          # Brand identity documentation
├── banners/           # Hero banners
├── concepts/          # Concept art, architecture diagrams
└── screenshots/       # Application screenshots
```

---

## Logo System

### Primary Logos

| Logo | Format | Usage |
|------|--------|-------|
| **OWNEX Mark** | SVG, PNG | Icon, favicon, small spaces |
| **OWNEX Wordmark** | SVG, PNG | Typography-focused applications |
| **OWNEX Lockup** | SVG, PNG | Horizontal lockup for headers |
| **OWNEX Icon** | SVG, PNG | App icon, launcher |

### Edition Variants

| Logo | Format | Usage |
|------|--------|-------|
| **OWNEX ALPHA** | SVG, PNG | Desktop edition branding |
| **OWNEX OMEGA** | SVG, PNG | Mobile edition branding |

### Logo Variants

- **Color:** Full color branding (default)
- **Black:** Monochrome black for light backgrounds
- **White:** Monochrome white for dark backgrounds

### Logo Usage Rules

1. **Minimum Size:** 32px for UI, 120px for print
2. **Clear Space:** Maintain 1x logo height clear space
3. **Background:** Use cosmos (#08090A) or white only
4. **Distortion:** Never stretch or alter aspect ratio
5. **Modifications:** Never modify colors, shapes, or proportions
6. **Monochrome Preferred:** Use monochrome variants in most contexts

---

## Color System

### Primary Palette

```css
/* Backgrounds */
--ownex-cosmos: #08090A;        /* Main background */
--ownex-surface: #111113;       /* UI surface */
--ownex-surface-alt: #1F2023;   /* Panel, card background */
--ownex-surface-highlight: #2A2D35; /* Hover states */

/* Text */
--ownex-text-primary: #F6F8FB;  /* Primary text */
--ownex-text-secondary: #8B8D98; /* Secondary text */
--ownex-text-tertiary: #5E6272;  /* Tertiary, disabled */

/* Accent */
--ownex-accent: #1E40FF;        /* Primary action, links, active states */
--ownex-accent-hover: #3B5BFF;   /* Hover state */
--ownex-accent-subtle: rgba(30, 64, 255, 0.15); /* Subtle backgrounds */

/* Functional */
--ownex-success: #00E39A;      /* Success, validation */
--ownex-warning: #FFB020;       /* Warning, pending */
--ownex-error: #FF5252;         /* Error, critical */
```

### Color Usage Rules

1. **Accent is functional, not decorative** - Use only on links, buttons, active states
2. **Gray ramp is pure neutral** - No warm/cool tints, true gray
3. **High contrast required** - Minimum 4.5:1 contrast ratio for text
4. **Single accent principle** - Never mix accent with other brand colors
5. **Background consistency** - Cosmos (#08090A) is the primary background

---

## Typography

### Font Stack

```css
/* Display (Headlines) */
font-family: 'Inter Display', 'Inter', system-ui, -apple-system, sans-serif;

/* Body (UI, paragraphs) */
font-family: 'Inter', system-ui, -apple-system, sans-serif;

/* Mono (Code, technical) */
font-family: 'JetBrains Mono', 'Fira Code', monospace;
```

### Typography Scale

| Size | Weight | Line Height | Letter Spacing | Usage |
|------|--------|-------------|----------------|-------|
| 64px | 700 | 1.1 | -0.03em | H1 - Hero |
| 48px | 600 | 1.2 | -0.02em | H2 - Section |
| 36px | 600 | 1.2 | -0.02em | H3 - Subsection |
| 24px | 500 | 1.3 | -0.01em | H4 - Component |
| 16px | 400 | 1.5 | 0 | Body |
| 14px | 400 | 1.5 | 0 | Small |
| 12px | 400 | 1.4 | 0 | Caption |

### Typography Rules

1. **Tight letter spacing** - Negative spacing on display sizes for engineered feel
2. **Aggressive vertical rhythm** - High line height, dense columns
3. **Mono for technical** - Use JetBrains Mono for code, data, technical labels
4. **Case usage** - Title case for headings, sentence case for body
5. **Max width** - 75 characters for body text

---

## Spacing & Layout

### Grid System

- **Base unit:** 8px grid
- **Component spacing:** Multiples of 8 (8, 16, 24, 32, 48, 64)
- **Container max-width:** 1200px
- **Section padding:** 96px vertical

### Spacing Scale

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 16px;
--space-4: 24px;
--space-5: 32px;
--space-6: 48px;
--space-8: 64px;
--space-10: 96px;
--space-12: 128px;
```

---

## Component Branding

### Mission Control (ALPHA)

- **Background:** Cosmos (#08090A)
- **Surface:** Surface (#111113)
- **Accent:** Accent (#5E6AD2) - only on active states
- **Text:** Primary (#F6F8FB)
- **Style:** Grid-based, metrics-focused, dense information
- **Tone:** Professional, technical, precise

### MERLIN Assistant

- **Background:** Cosmos (#08090A)
- **Surface:** Surface (#111113)
- **Accent:** Success (#00E39A) - for AI responses
- **Text:** Primary (#F6F8FB)
- **Style:** Conversational, clean, terminal-like
- **Tone:** Helpful, intelligent, patient

### Agent Fleet

- **Background:** Cosmos (#08090A)
- **Surface:** Surface (#111113)
- **Accent:** Department-specific colors (single accent per agent)
- **Text:** Primary (#F6F8FB)
- **Style:** Status indicators, activity cards, compact
- **Tone:** Dynamic, operational, fleet-focused

---

## Product Branding

### Desktop (ALPHA)

- **Window Title:** "OWNEX ALPHA"
- **Icon:** Geometric mark (monochrome)
- **Color Scheme:** Cosmos + Accent
- **Window Frame:** Cosmos with thin accent border
- **UI Style:** Dense, keyboard-first, terminal aesthetic

### Mobile (OMEGA)

- **App Name:** "OWNEX OMEGA"
- **Icon:** Geometric mark (monochrome)
- **Color Scheme:** Cosmos + Accent
- **Navigation:** Bottom tab bar with accent indicators
- **UI Style:** Touch-optimized, clear hierarchy

---

## Web Branding

### GitHub README

- **Header:** OWNEX wordmark + "The Personalized Autonomous Operating System"
- **Background:** Cosmos (#08090A)
- **Text:** Off-white (#F6F8FB)
- **Accent:** Only on links and badges
- **Images:** Minimal, functional, no decoration

### Documentation

- **Logo:** Geometric mark (small, monochrome)
- **Background:** White/Cosmos toggle
- **Headings:** Cosmos color
- **Code Blocks:** Surface background
- **Style:** Reference-quality, technical

---

## Asset Generation

All brand assets are generated deterministically using the pipeline in `scripts/brand/`:

```bash
# Generate all logos
cd scripts/brand
python generate_premium_logos.py

# Generate banners
python generate_premium_banners.py

# Generate showcase visuals
python generate_showcase.py

# Convert SVG to PNG
python svg_to_png.py
python convert_banners.py
python convert_showcase.py
```

---

## Brand Compliance

### Do's

✅ Use official color palette
✅ Follow typography scale
✅ Maintain 8px grid alignment
✅ Use monochrome logos preferred
✅ High contrast (4.5:1 minimum)
✅ Functional color usage
✅ Consistent spacing
✅ Minimal, functional design

### Don'ts

❌ Add gradients or shadows
❌ Use decorative illustrations
❌ Mix multiple accent colors
❌ Modify logo proportions
❌ Use warm/cool gray tints
❌ Add decoration without purpose
❌ Break the 8px grid
❌ Use generated text in images

---

## Quality Criteria

Before finalizing any asset, verify:

1. **Does it look like a real tech company?** (Tesla, Linear, Vercel level)
2. **Would a professional developer trust this repository?**
3. **Do images explain the product or just decorate?**
4. **Does the identity work without the word "AI"?**
5. **Is every pixel intentional?**
6. **Is the restraint visible?**

If any answer is "no", refine.

---

## Brand Version

- **Version:** 2.0 (Premium Redesign)
- **Inspired by:** Linear, Vercel, Tesla
- **Last Updated:** 2026-08-01
- **Design Philosophy:** Extreme restraint, functional design, engineering precision

---

## Contact

For brand-related questions:
- Documentation: `.ai/OWNEX_PREMIUM_BRAND_IDENTITY.md`
- Design Tokens: assets/branding/design-tokens.json

---

**OWNEX Brand System v2.0**
**The Personalized Autonomous Operating System**
