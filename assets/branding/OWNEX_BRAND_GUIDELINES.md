# OWNEX OMEGA — Brand Guidelines v1.0

> **Premium Autonomous Work Operating System**
> *"Dark Command Center, not Cyberpunk Hacker"*

---

## 1. Brand Identity

### Name
**OWNEX OMEGA**

### Slogan
**"Autonomous Work Operating System"**

### Tagline
**"Your personal AI-powered workforce"**

### Mission
Enable individuals to build financial independence through autonomous software, automation, and intelligent systems.

### Vision
A world where anyone can deploy a fleet of AI agents that work 24/7 to generate revenue, learn continuously, and execute complex workflows autonomously.

### Values
- **Autonomy over control** — Empower users to own their automated workflows
- **Results over activity** — Measure by revenue generated, not tasks completed
- **Intelligence over complexity** — Smart systems that hide complexity from users
- **Quality over quantity** — Premium execution over feature bloat
- **Transparency over opacity** — Users always understand what their agents are doing

### Elevator Pitch
OWNEX OMEGA is an autonomous operating system that deploys AI agents to work bug bounty, execute development tasks, manage revenue, and learn continuously—while you sleep.

### One-liner
Autonomous AI workforce for bug bounty, development, and revenue generation.

### Brand Voice
- **Professional** — Technical but accessible, confident but not arrogant
- **Precise** — Every word has purpose, no fluff
- **Minimal** — Say more with less
- **Confident** — We know what we're building
- **Technical but human** — Engineering excellence with empathy

---

## 2. Visual Philosophy

### What We Are NOT
- ❌ CRT/phosphor/terminal aesthetic (that was ORION)
- ❌ Green military/matrix/hacker aesthetic (visual fatigue, zero productivity)
- ❌ Excessive technical lines/borders/panels (visual noise = cognitive load)
- ❌ Generic SaaS dashboard with 47 cards (nobody looks at 47 cards)

### What We Are
A personal operating system that converts dispersed opportunities into executable cycles.

### 6 Guiding Principles
1. **Clarity over complexity** — If it's not understood in 3 seconds, it doesn't exist
2. **Action over information** — UI suggests next action, doesn't just show data
3. **Cycles over pages** — Work lives in cycles, not separate pages
4. **Outcomes over activity** — $ earned > requests sent > time invested
5. **Agents over tools** — Users see agents working, not models/AI
6. **Throughput over metrics** — Real value velocity > vanity metrics

---

## 3. Color System

### Primary Palette

| Color | Variable | Hex | RGB | Usage |
|-------|----------|-----|-----|-------|
| 🔵 **OWNEX Blue** | `--ownex-blue` | `#3B82F6` | 59, 130, 246 | Primary actions, selection, navigation, intelligence, links |
| ⚪ **OWNEX White** | `--ownex-white` | `#F0F0F0` | 240, 240, 240 | Titles, important information, results, primary text |
| 🟡 **OWNEX Gold** | `--ownex-gold` | `#F59E0B` | 245, 158, 11 | Money, rewards, achievements, premium opportunities, value highlights |

### Background Palette (Near-Black)

| Color | Variable | Hex | Usage |
|-------|----------|-----|-------|
| **Deep** | `--bg-deep` | `#050505` | Canvas base - almost pure black |
| **Base** | `--bg-base` | `#080808` | Main surfaces |
| **Surface** | `--bg-surface` | `#0F1117` | Cards, panels, elevated surfaces |
| **Elevated** | `--bg-elevated` | `#14161E` | Modals, dropdowns, tooltips |

### Status Colors (Strictly 3)

| Color | Variable | Hex | Usage |
|-------|----------|-----|-------|
| 🟢 **Success** | `--status-success` | `#22C55E` | Active / Success / Confirmed |
| 🔴 **Error** | `--status-error` | `#EF4444` | Error / Risk / Rejected |
| 🟡 **Warning** | `--status-warn` | `#F59E0B` | Attention / Pending / In progress |

**Rule:** NO other status colors. No blue for info, no purple for warning, no orange for anything else. 3 states = cognitive clarity.

### Text Colors

| Color | Variable | Hex | Usage |
|-------|----------|-----|-------|
| **Primary** | `--text-primary` | `#F0F0F0` | OWNEX White - titles, main content |
| **Secondary** | `--text-secondary` | `#9CA3AF` | Medium gray - labels, metadata, help |
| **Muted** | `--text-muted` | `#6B7280` | Soft gray - placeholders, disabled, timestamps |
| **Inverse** | `--text-inverse` | `#050505` | On light backgrounds (gold/blue) |

### Border Colors

| Color | Variable | Hex | Usage |
|-------|----------|-----|-------|
| **Subtle** | `--border-subtle` | `#1A1A2E` | Subtle blue-black - dividers, cards |
| **Active** | `--border-active` | `#3B82F6` | OWNEX Blue - focus, active, hover |
| **Error** | `--border-error` | `#EF4444` | Red - error states |

### CSS Variables

```css
:root {
  /* Primary */
  --ownex-blue: #3B82F6;
  --ownex-white: #F0F0F0;
  --ownex-gold: #F59E0B;

  /* Backgrounds */
  --bg-deep: #050505;
  --bg-base: #080808;
  --bg-surface: #0F1117;
  --bg-elevated: #14161E;

  /* Status */
  --status-success: #22C55E;
  --status-error: #EF4444;
  --status-warn: #F59E0B;

  /* Text */
  --text-primary: #F0F0F0;
  --text-secondary: #9CA3AF;
  --text-muted: #6B7280;
  --text-inverse: #050505;

  /* Borders */
  --border-subtle: #1A1A2E;
  --border-active: #3B82F6;
  --border-error: #EF4444;
}
```

---

## 4. Typography

### Font Stack

```css
/* Primary (UI, body, interface) */
--font-sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 
             "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;

/* Display (headings, hero, large type) */
--font-display: "Space Grotesk", "Inter", ui-sans-serif, system-ui, 
                 -apple-system, sans-serif;

/* Mono (code, data, technical) */
--font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, 
              "Liberation Mono", "JetBrains Mono", monospace;
```

### Type Scale

| Size | Variable | Rem | Pixels | Usage |
|------|----------|-----|--------|-------|
| **XS** | `--text-xs` | 0.75rem | 12px | Labels, tags, timestamps |
| **SM** | `--text-sm` | 0.875rem | 14px | Secondary body, metadata |
| **Base** | `--text-base` | 1rem | 16px | Primary body |
| **LG** | `--text-lg` | 1.125rem | 18px | Subheadings, important cards |
| **XL** | `--text-xl` | 1.25rem | 20px | Section headers |
| **2XL** | `--text-2xl` | 1.5rem | 24px | Page titles |
| **3XL** | `--text-3xl` | 2rem | 32px | Hero, splash |

### Font Weights

| Weight | Variable | Value | Usage |
|--------|----------|-------|-------|
| **Normal** | `--font-normal` | 400 | Body text, descriptions |
| **Medium** | `--font-medium` | 500 | Emphasis, labels |
| **Semibold** | `--font-semibold` | 600 | Headings, important text |
| **Bold** | `--font-bold` | 700 | Logo, strong emphasis |

### Letter Spacing

| Context | Value | Usage |
|---------|-------|-------|
| **Logo** | 4-6px | OWNEX wordmark |
| **Tagline** | 5-7px | Small caps, uppercase labels |
| **Headings** | -0.02em | Tight tracking for display |
| **Body** | 0 | Normal tracking |
| **Uppercase** | 0.05em | Slight increase for readability |

### Line Height

| Context | Value | Usage |
|---------|-------|-------|
| **Tight** | 1.1 | Headings, display |
| **Normal** | 1.5 | Body text |
| **Relaxed** | 1.75 | Long-form content |

---

## 5. Spacing System

### 8px Base Grid

| Size | Variable | Rem | Pixels | Usage |
|------|----------|-----|--------|-------|
| **1** | `--space-1` | 0.25rem | 4px | Micro spacing |
| **2** | `--space-2` | 0.5rem | 8px | Base unit |
| **3** | `--space-3` | 0.75rem | 12px | Small elements |
| **4** | `--space-4` | 1rem | 16px | Standard spacing |
| **5** | `--space-5` | 1.25rem | 20px | Medium spacing |
| **6** | `--space-6` | 1.5rem | 24px | Large spacing |
| **8** | `--space-8` | 2rem | 32px | Section spacing |
| **10** | `--space-10` | 2.5rem | 40px | Major sections |
| **12** | `--space-12` | 3rem | 48px | Page sections |
| **16** | `--space-16` | 4rem | 64px | Hero spacing |

---

## 6. Border Radius

| Size | Variable | Rem | Pixels | Usage |
|------|----------|-----|--------|-------|
| **SM** | `--radius-sm` | 0.25rem | 4px | Buttons, chips, small elements |
| **MD** | `--radius-md` | 0.5rem | 8px | Cards, inputs, dropdowns |
| **LG** | `--radius-lg` | 0.75rem | 12px | Modals, panels, elevated surfaces |
| **XL** | `--radius-xl` | 1rem | 16px | Splash, major containers |
| **Full** | `--radius-full` | 9999px | Pills, badges, avatars |

---

## 7. Shadows & Elevation

### Shadow System

| Size | Variable | CSS | Usage |
|------|----------|-----|-------|
| **1** | `--shadow-1` | `0 1px 2px 0 rgb(0 0 0 / 0.3)` | bg-surface |
| **2** | `--shadow-2` | `0 4px 6px -1px rgb(0 0 0 / 0.4)` | bg-elevated |
| **3** | `--shadow-3` | `0 10px 15px -3px rgb(0 0 0 / 0.5)` | Modals, dropdowns |
| **Glow** | `--shadow-glow` | `0 0 0 1px var(--ownex-blue), 0 0 20px rgb(59 130 246 / 0.3)` | Focus ring |

**Rule:** Depth by layers, not by "glow". Elevation and subtle border only.

---

## 8. Logo System

### Logo Variations

| File | Format | Usage |
|------|--------|-------|
| `ownex-logo-horizontal-premium.svg` | SVG | Primary horizontal logo (dark) |
| `ownex-logo-horizontal-light.svg` | SVG | Horizontal logo (light backgrounds) |
| `ownex-logo-vertical.svg` | SVG | Vertical stacked version |
| `ownex-isotype.svg` | SVG | Symbol only (O with orbitals) |
| `ownex-isotype-monochrome.svg` | SVG | Monochrome version for print |
| `ownex-app-icon-512.svg` | SVG | App icon (512x512) |
| `ownex-launcher-adaptive.svg` | SVG | Android adaptive icon (108x108) |
| `ownex-favicon.svg` | SVG | Favicon (64x64) |

### Logo Usage Rules

1. **Minimum clear space**: Equal to the height of the "O" symbol
2. **Minimum size**: 120px width for horizontal, 80px for isotype
3. **Background**: Always use on dark backgrounds when possible
4. **Don't**: Stretch, rotate, add effects, change colors
5. **Do**: Maintain aspect ratio, use approved variations only

### Logo Construction

The OWNEX logo consists of:
- **Logomark**: Stylized "O" with orbital rings suggesting autonomy and intelligence
- **Logotype**: "OWNEX" in Inter/SF Pro Display, weight 600, tracking 4px
- **Tagline**: "AUTONOMOUS WORK OS" in Inter, weight 500, tracking 6px
- **Accent**: Gold dot positioned at top-right of O, suggesting value/wealth

---

## 9. Iconography

### Icon Principles

- **Minimal**: Every line has purpose
- **Geometric**: Consistent stroke widths, rounded corners
- **Consistent**: All icons follow the same visual language
- **Scalable**: Works at 16px and 512px
- **Monoline**: 1.5px stroke weight at 24px base

### Icon Categories

```
icons/
├── work-cycles/     # Mission, Security, Forge, Pulse, Vault, Atlas
├── agents/          # Research, Execution, Memory, Security, Analyst
└── ui/              # Navigation, actions, status, indicators
```

### Icon Usage

- **Size**: 16px, 20px, 24px, 32px, 48px
- **Color**: OWNEX White (primary), OWNEX Blue (active), OWNEX Gold (accent)
- **Stroke**: 1.5px at 24px base
- **Radius**: 2px corners on all strokes

---

## 10. Animation Principles

### Animation Values

| Property | Value | Usage |
|----------|-------|-------|
| **Duration** | 150-300ms | Micro interactions |
| **Duration** | 300-500ms | State changes |
| **Duration** | 500-800ms | Complex transitions |
| **Easing** | `cubic-bezier(0.4, 0, 0.2, 1)` | Standard ease |
| **Easing** | `cubic-bezier(0.16, 1, 0.3, 1)` | Emphasized |

### Animation Types

- **Micro**: Hover states, button presses (150ms)
- **State**: Modal open/close, card expand (300ms)
- **Complex**: Page transitions, major reflows (500ms)

### Animation Rules

1. **Purpose-driven**: Every animation has a functional purpose
2. **Subtle**: Never distract from content
3. **Consistent**: Same duration for similar interactions
4. **Performant**: 60fps minimum, use transforms/opacity

---

## 11. Layout System

### Grid System

- **Columns**: 12-column grid
- **Gutter**: 24px (1.5rem)
- **Margins**: 32px (2rem) on desktop, 16px (1rem) on mobile
- **Max-width**: 1400px for main content

### Container Sizes

| Breakpoint | Max-width | Columns |
|------------|-----------|---------|
| **Mobile** | 100% | 4 |
| **Tablet** | 768px | 8 |
| **Desktop** | 1024px | 12 |
| **Wide** | 1400px | 12 |

---

## 12. Component Principles

### Card Design

```css
.ownex-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-1);
  padding: var(--space-6);
}
```

### Button Design

```css
.ownex-button-primary {
  background: var(--ownex-blue);
  color: var(--text-inverse);
  border-radius: var(--radius-sm);
  padding: var(--space-3) var(--space-6);
  font-weight: var(--font-medium);
  transition: all 150ms ease;
}
```

### Input Design

```css
.ownex-input {
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: var(--space-3) var(--space-4);
  color: var(--text-primary);
}
```

---

## 13. Voice & Tone

### Writing Style

- **Direct**: Say what you mean, no fluff
- **Active**: Active voice, present tense
- **Precise**: Specific terminology, no ambiguity
- **Confident**: We know our system
- **Human**: Technical but accessible

### Example Headlines

❌ "Leveraging AI-powered autonomous agents for optimal workflow automation"
✅ "Autonomous agents that work while you sleep"

❌ "Comprehensive bug bounty platform with advanced vulnerability detection"
✅ "Find vulnerabilities. Get paid. Sleep."

### Microcopy

- **Buttons**: Action-oriented ("Execute", not "Submit")
- **Errors**: Helpful, not technical ("Connection failed", not "ERR_CONNECTION_REFUSED")
- **Empty states**: Actionable ("No agents deployed. Deploy one →", not "No data available")

---

## 14. Brand Applications

### GitHub Repository

- **README**: Use hero banner with horizontal logo
- **Description**: "Autonomous AI workforce for bug bounty, development, and revenue generation"
- **Topics**: autonomous-ai, bug-bounty, automation, revenue, python, vue, typescript
- **Social preview**: Use OG image with isotype + tagline

### Documentation

- **Headers**: Use OWNEX Blue for emphasis
- **Code blocks**: Use OWNEX Gold for highlights
- **Callouts**: Use status colors for notes/warnings

### Marketing Materials

- **Headlines**: OWNEX White on Deep background
- **Subheadlines**: OWNEX Blue for emphasis
- **CTAs**: OWNEX Gold for primary actions
- **Backgrounds**: Near-black palette only

---

## 15. Do's and Don'ts

### Do ✅

- Use the approved color palette only
- Maintain clear space around logos
- Follow the 8px spacing grid
- Use Inter/system fonts for UI
- Keep animations subtle and purposeful
- Write direct, active copy
- Prioritize clarity over cleverness

### Don't ❌

- Add gradients to backgrounds
- Use green/purple/pink for anything
- Stretch or rotate logos
- Add glow effects to everything
- Use display fonts for body text
- Write passive or verbose copy
- Sacrifice clarity for aesthetics

---

## 16. Brand Assets

### File Locations

```
assets/branding/
├── logo/
│   ├── ownex-logo-horizontal-premium.svg
│   ├── ownex-logo-horizontal-light.svg
│   ├── ownex-logo-vertical.svg
│   ├── ownex-isotype.svg
│   ├── ownex-isotype-monochrome.svg
│   ├── app-icons/
│   │   ├── ownex-app-icon-512.svg
│   │   └── ownex-launcher-adaptive.svg
│   └── favicons/
│       └── ownex-favicon.svg
├── banner/
│   ├── hero-banner.svg
│   ├── hero-banner-dark.svg
│   └── hero-banner-light.svg
├── screenshots/
│   ├── mission-control.png
│   ├── terminal.png
│   ├── dashboard.png
│   ├── voice.png
│   ├── agents.png
│   ├── mobile.png
│   ├── wearos.png
│   ├── boot-sequence.png
│   └── installer.png
├── social/
│   ├── twitter-card.png
│   ├── og-image.png
│   └── linkedin-banner.png
├── wallpapers/
│   ├── ownex-wallpaper-4k.svg
│   └── ownex-wallpaper-mobile.svg
├── icons/
│   ├── work-cycles/
│   ├── agents/
│   └── ui/
└── press-kit/
    ├── logo-pack.zip
    ├── brand-guidelines.pdf
    └── color-palette.ase
```

---

## 17. Contact & Licensing

### Brand Inquiries

For brand partnerships, licensing, or media inquiries:
- **GitHub**: [AdriDob/rastrohunteralpha](https://github.com/AdriDob/rastrohunteralpha)
- **License**: MIT License

### Brand Usage

OWNEX OMEGA is open source under MIT License. You may:
- Use the logo for attribution
- Use brand assets for non-commercial purposes
- Modify the software under MIT terms

You may not:
- Use the brand for commercial purposes without permission
- Register trademarks using OWNEX name or logo
- Imply endorsement or partnership

---

**OWNEX OMEGA Brand Guidelines v1.0**
*Last updated: 2026-07-31*
*Version: 7.0.0*