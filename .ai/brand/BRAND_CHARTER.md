# Brand Department Charter — OWNEX OMEGA

> **Premium Autonomous Work Operating System**
> *"Dark Command Center, not Cyberpunk Hacker"*

---

## Department Mission

The Brand Department is responsible for maintaining and evolving the visual identity of OWNEX OMEGA to ensure it communicates as a premium, professional autonomous operating system comparable to Tesla, Apple, Linear, Vercel, and Anthropic.

---

## Brand Department Structure

### 1. Art Director
**Responsibility:** Overall visual direction, quality control, and consistency
- Approves all visual assets before production
- Ensures alignment with brand guidelines
- Maintains visual coherence across all touchpoints
- Makes final decisions on design direction

### 2. Brand Designer
**Responsibility:** Core brand identity and visual system
- Maintains and evolves brand guidelines
- Designs color systems, typography, and visual language
- Creates brand assets (logos, icons, patterns)
- Ensures brand consistency across all materials

### 3. Logo Designer
**Responsibility:** Logo system and wordmark
- Creates logo variations (horizontal, vertical, isotype)
- Ensures scalability across all sizes (16px to 256px+)
- Designs monochrome and animated versions
- Maintains logo construction guidelines

### 4. README Designer
**Responsibility:** GitHub repository presence
- Designs hero README sections
- Creates landing page-style documentation
- Optimizes for GitHub's markdown rendering
- Ensures impact and clarity at first glance

### 5. Hero Designer
**Responsibility:** Hero banners and key visuals
- Creates hero banners for README and landing pages
- Designs social media visuals
- Creates marketing and promotional materials
- Ensures hero visuals communicate core value proposition

### 6. Illustration Designer
**Responsibility:** Custom illustrations and diagrams
- Creates system architecture diagrams
- Designs workflow illustrations
- Creates explanatory visuals for documentation
- Maintains illustration style consistency

### 7. Icon Designer
**Responsibility:** Icon system and iconography
- Designs UI icons (navigation, actions, status)
- Creates work cycle icons (Security, Forge, Pulse, Vault, Atlas)
- Maintains icon consistency (stroke weight, corner radius, sizing)
- Ensures scalability across all sizes

### 8. Motion Designer
**Responsibility:** Animation and motion design
- Creates logo animations
- Designs UI motion patterns
- Creates loading animations and transitions
- Maintains motion consistency with brand guidelines

### 9. Prompt Engineer
**Responsibility:** AI image generation
- Writes optimized prompts for ComfyUI/FLUX
- Iterates on prompts for quality improvement
- Maintains prompt library for reproducibility
- Tests and validates AI-generated assets

### 10. Visual QA
**Responsibility:** Quality assurance and consistency
- Reviews all visual assets before release
- Checks for brand guideline compliance
- Ensures technical correctness (SVG, PNG, sizing)
- Maintains asset library and organization

---

## Design Philosophy

### What We Are NOT
- ❌ CRT/phosphor/terminal aesthetic (that was ORION)
- ❌ Green military/matrix/hacker aesthetic (visual fatigue, zero productivity)
- ❌ Excessive technical lines/borders/panels (visual noise = cognitive load)
- ❌ Generic SaaS dashboard with 47 cards (nobody looks at 47 cards)
- ❌ Gamer aesthetic or cyberpunk exaggeration
- ❌ Saturated colors or neon effects

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

## Visual Reference Points

### Inspiration (Not Imitation)
- **Linear** — Minimalist, premium, developer-focused
- **Arc Browser** — Elegant, powerful, opinionated
- **Raycast** — Keyboard-first, efficient, professional
- **Vercel** — Clean, modern, developer-centric
- **Tesla** — Premium, futuristic, autonomous
- **Apple** — Minimalist, refined, consistent
- **Stripe** — Professional, trustworthy, elegant
- **Anthropic** — Thoughtful, research-driven, premium
- **Nothing** — Bold, distinctive, premium
- **Figma** — Collaborative, professional, intuitive

### Design Principles to Extract
- **Minimalism** — Every element has purpose
- **Negative space** — Much whitespace, breathing room
- **Typography hierarchy** — Clear visual hierarchy through type
- **Subtle gradients** — Never primary, always secondary
- **Monochrome base** — Works in black and white first
- **Scalability** — Works at 16px and 256px
- **Professionalism** — Feels like a $1B+ company
- **Consistency** — One visual language across everything

---

## Color System

### Primary Palette
```css
--ownex-blue:   #3B82F6;  /* Primary actions, selection, navigation, intelligence, links */
--ownex-white:  #F0F0F0;  /* Titles, important information, results, primary text */
--ownex-gold:   #F59E0B;  /* Money, rewards, achievements, premium opportunities, value highlights */
```

### Background Palette (Near-Black)
```css
--bg-deep:      #050505;  /* Canvas base - almost pure black */
--bg-base:      #080808;  /* Main surfaces */
--bg-surface:   #0F1117;  /* Cards, panels, elevated surfaces */
--bg-elevated:  #14161E;  /* Modals, dropdowns, tooltips */
```

### Status Colors (Strictly 3)
```css
--status-success: #22C55E;  /* 🟢 Active / Success / Confirmed */
--status-error:   #EF4444;  /* 🔴 Error / Risk / Rejected */
--status-warn:    #F59E0B;  /* 🟡 Attention / Pending / In progress */
```

**Rule:** NO other status colors. No blue for info, no purple for warning, no orange for anything else. 3 states = cognitive clarity.

---

## Typography System

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
```css
--text-xs:   0.75rem;  /* 12px - Labels, tags, timestamps */
--text-sm:   0.875rem; /* 14px - Secondary body, metadata */
--text-base: 1rem;     /* 16px - Primary body */
--text-lg:   1.125rem; /* 18px - Subheadings, important cards */
--text-xl:   1.25rem;  /* 20px - Section headers */
--text-2xl:  1.5rem;   /* 24px - Page titles */
--text-3xl:  2rem;     /* 32px - Hero, splash */
```

---

## Image Generation Pipeline

### Tool Selection: ComfyUI + FLUX Dev/Schnell

**Rationale:**
- **Quality:** FLUX Dev produces highest quality open-source images
- **Speed:** FLUX Schnell for rapid iteration
- **Control:** ComfyUI provides node-based control over generation
- **Community:** Large ecosystem of custom nodes and workflows
- **Future-proof:** Active development and model updates

### Installation Requirements
- NVIDIA GPU with 8GB+ VRAM (12GB+ recommended)
- CUDA 11.8+
- Python 3.10
- 15-65GB disk space per model
- ComfyUI with ComfyUI-Manager

### Model Selection
- **FLUX.1 Dev** (24GB VRAM, highest quality, non-commercial)
- **FLUX.1 Schnell** (16GB VRAM, very fast, Apache 2.0 commercial)
- **FLUX.2 Klein 4B** (12GB VRAM, very fast, Apache 2.0 commercial)

### Workflow Templates
- Logo generation workflow
- Hero banner workflow
- Icon generation workflow
- Illustration workflow
- Screenshot enhancement workflow

---

## Asset Organization

```
.ai/brand/
├── BRAND_CHARTER.md              # This file
├── PROMPT_LIBRARY.md             # Prompt templates and variations
├── ASSET_REGISTRY.md             # All brand assets with metadata
├── DESIGN_DECISIONS.md           # Rationale for design decisions
├── QUALITY_CHECKLIST.md          # QA checklist for all assets
├── generation_pipeline/          # ComfyUI workflows and configs
│   ├── workflows/
│   ├── prompts/
│   └── output/
├── concepts/                     # Generated concepts (10 each category)
│   ├── logos/
│   ├── heroes/
│   ├── github_covers/
│   ├── readmes/
│   ├── splash_screens/
│   ├── icons/
│   └── wallpapers/
└── approved/                     # Final approved assets
    ├── logos/
    ├── heroes/
    ├── icons/
    └── marketing/
```

---

## Quality Metrics

Each design must be scored on:

1. **Minimalism** (0-10) — How essential is every element?
2. **Legibility** (0-10) — How clear is the information?
3. **Scalability** (0-10) — Does it work at 16px and 256px?
4. **Professionalism** (0-10) — Does it feel like a premium product?
5. **Consistency** (0-10) — Does it match brand guidelines?
6. **Memorability** (0-10) — Is it distinctive and memorable?
7. **Impact** (0-10) — Does it create immediate impression?
8. **Elegance** (0-10) — Is it refined and sophisticated?

**Passing Score:** 7.0+ average across all metrics
**Excellent Score:** 8.5+ average across all metrics

---

## Workflow Process

### 1. Concept Generation Phase
- Generate 10 concepts per category
- Use prompt library for consistency
- Score each concept objectively
- Select top 3 for refinement

### 2. Refinement Phase
- Iterate on top 3 concepts
- Apply brand guidelines strictly
- Test scalability and versatility
- Score refined versions

### 3. Approval Phase
- Art Director reviews final concepts
- Visual QA checks technical correctness
- Brand Designer ensures consistency
- Select final version

### 4. Production Phase
- Generate final assets in all required formats
- Create variations (light/dark, sizes, animations)
- Document generation parameters
- Archive in approved/ directory

### 5. Integration Phase
- Update all touchpoints with new assets
- Ensure consistency across codebase
- Update documentation
- Archive old assets

---

## Brand Evolution Protocol

### When to Evolve
- Major version release (e.g., 7.0.0 → 8.0.0)
- Strategic pivot in product direction
- Significant expansion of target audience
- Brand guideline inconsistencies detected

### Evolution Process
1. Audit current brand assets
2. Identify inconsistencies and opportunities
3. Research design trends and competitors
4. Propose evolution strategy
5. Generate and test concepts
6. Get stakeholder approval
7. Roll out evolution gradually
8. Monitor feedback and iterate

### Version Control
- All brand assets versioned
- Old versions archived with rationale
- Prompts and parameters documented
- Reproducible generation pipeline

---

## Success Metrics

### Brand Metrics
- Recognition score (user surveys)
- Professionalism perception (user surveys)
- Consistency score (automated checks)
- Asset reuse rate (internal tracking)

### Product Metrics
- GitHub stars growth
- Repository visit duration
- README engagement (scroll depth)
- Social media engagement

### Design Metrics
- Concept generation time
- Asset approval rate
- Revision iteration count
- Cross-platform consistency

---

**Brand Department Charter v1.0**
*Last updated: 2026-07-31*
*Version: 7.0.0*