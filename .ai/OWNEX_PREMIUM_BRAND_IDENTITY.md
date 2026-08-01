# OWNEX Premium Brand Identity v2.0

## Brand Philosophy

OWNEX represents precision, autonomy, and evolution. The brand communicates engineering excellence through extreme restraint, mathematical precision, and functional design.

**Inspired by:** Linear, Vercel, Tesla
**Core principle:** Every pixel has purpose. Decoration is latency made visible.

---

## Visual Identity

### Logo System

#### Primary Wordmark
**Usage:** Headers, hero sections, primary brand expression

```
OWNEX
```

- **Font:** Inter Display, weight 600-700
- **Letter spacing:** -0.02em (tight, engineered feel)
- **Color:** Off-white (#F6F8FB) on dark, black (#08090A) on light
- **Clear space:** 1x height minimum around all sides

#### Geometric Mark
**Usage:** Favicon, app icon, constrained spaces

- **Shape:** Abstract "O" with internal geometric division
- **Metaphor:** Autonomous loop, intelligence cycle, system precision
- **Construction:** Two geometric forms creating negative space
- **Scalability:** Optimized for 16px to 512px
- **Variants:** Monochrome preferred (black/white)

#### Lockup
**Usage:** Social media, documentation headers, cards

```
[Geometric Mark] OWNEX
```

- **Spacing:** 0.5x mark width between mark and wordmark
- **Alignment:** Baseline aligned
- **Scale:** Mark at 60% of wordmark height

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
--ownex-accent: #5E6AD2;        /* Primary action, links, active states */
--ownex-accent-hover: #7B85E0;   /* Hover state */
--ownex-accent-subtle: rgba(94, 106, 210, 0.15); /* Subtle backgrounds */

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
font-family: 'Inter Display', 'Inter', system-ui, sans-serif;

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

## Asset Generation Pipeline

### Tools

1. **Vector Design:** Inkscape (SVG logo creation)
2. **Visual Generation:** ComfyUI (Flux model for concept art)
3. **UI Design:** Penpot (design system, components)
4. **Diagrams:** Mermaid (architecture), Excalidraw (sketches)

### Generation Rules

1. **No generated text in images** - All text in Markdown
2. **Consistent style** - Same aesthetic across all assets
3. **Functional over decorative** - Every image must explain the product
4. **Vector-first** - SVG for logos, PNG for raster assets
5. **Optimization** - Web-optimized PNGs, responsive SVGs

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

### Don'ts

❌ Add gradients or shadows
❌ Use decorative illustrations
❌ Mix multiple accent colors
❌ Modify logo proportions
❌ Use warm/cool gray tints
❌ Add decoration without purpose
❌ Break the 8px grid

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

**OWNEX — The Personalized Autonomous Operating System**
