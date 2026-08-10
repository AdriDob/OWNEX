# OWNEX Design System

## Philosophy

OWNEX visual identity is built on **precision, restraint, and clarity**. The design does not compete with the product—it elevates it through geometry, spacing, and hierarchy.

### Core Principles

1. **Product-First**: Visual presentation showcases real software. Brand artwork supports the product.
2. **No Redundancy**: Every asset has a unique purpose. No duplicates without explicit justification.
3. **Geometric Precision**: Logo, icons, and diagrams use exact geometry, not approximation.
4. **Negative Space**: Use generous whitespace. Don't fill every pixel.
5. **Consistency**: All visual elements belong to one coherent system.

---

## Brand Identity

### Logo System

**Primary Mark**: Abstract convergence symbol with orbital paths
- Represents: Intelligent navigation, opportunity discovery, autonomous routing
- Geometry: Concentric orbital rings + directional convergence paths + central node
- Recognition: Works independently without wordmark

**Wordmark**: "OWNEX" in modern sans-serif
- Font: Inter / system-ui / -apple-system / BlinkMacSystemFont / Segoe UI / Roboto
- Weight: 700 (bold)
- Letter-spacing: -2 (desktop), -1.5 (mobile)

**Lockup**: Mark + Wordmark combined
- Configuration: Mark left, Wordmark right
- Spacing: 12px gap between elements
- Minimum width: 200px

### Logo Variants

| Variant | Use Case | Format |
|---------|----------|--------|
| `ownex-lockup.svg` | Primary brand, README header | SVG |
| `ownex-lockup-white.svg` | Dark backgrounds | SVG |
| `ownex-lockup-black.svg` | Light backgrounds | SVG |
| `ownex-mark.svg` | Iconography, favicons, small sizes | SVG |
| `ownex-mark-white.svg` | Dark backgrounds, small sizes | SVG |
| `ownex-mark-black.svg` | Light backgrounds, small sizes | SVG |
| `ownex-wordmark.svg` | Typography-only applications | SVG |
| `favicon.svg` | Browser favicon | SVG (16×16) |

---

## Color Palette

### Primary Colors

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| **Black** | `#0B0B0B` | 11, 11, 11 | Primary background, text on light |
| **White** | `#FFFFFF` | 255, 255, 255 | Primary surface, text on dark |

### Accent Colors

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| **OWNEX Blue** | `#2D7FF9` | 45, 127, 249 | Primary accent, branding, links |
| **OWNEX Deep Blue** | `#1E40FF` | 30, 64, 255 | Secondary accent, gradients |

### Supporting Colors

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| **Gold Accent** | `#D4AF37` | 212, 175, 55 | Premium touches, highlights |
| **Dark Gray** | `#1A1A1A` | 26, 26, 26 | Surface borders, subtle separation |
| **Light Gray** | `#E5E5E5` | 229, 229, 229 | Secondary text, muted elements |

### Status Colors

| Name | Hex | Usage |
|------|-----|-------|
| Success | `#00C853` | Passing tests, healthy systems |
| Warning | `#FFAB00` | Pending, caution states |
| Error | `#FF1744` | Failed tests, errors |
| Info | `#2196F3` | Informational content |

### Color Usage Rules

- **Ownex Blue** is the only brand color used in badges, links, and UI accents
- **Gold Accent** is used sparingly—maximum 2 instances per hero/layout
- **No rainbow colors**—strict adherence to the defined palette
- **No neon cyberpunk**—colors are muted, professional, and restrained
- **Gradients** use only Ownex Blue → Ownex Deep Blue

---

## Typography

### Type Scale

| Size | Weight | Usage |
|------|--------|-------|
| 72px | 700 | Display, hero titles |
| 48px | 700 | Section headings |
| 36px | 600 | Subsection headings |
| 24px | 400 | Body copy, descriptions |
| 18px | 400 | Secondary text |
| 14px | 400 | Captions, metadata |
| 12px | 400 | Small text, labels |

### Font Stack

**Primary**: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
**Code**: 'Fira Code', 'JetBrains Mono', 'SF Mono', Consolas, monospace

### Typography Rules

- **No external fonts** in GitHub README—use system stack only
- **Letter-spacing**: -2 for headings, 0 for body, +2 for uppercase labels
- **Line-height**: 1.2 for headings, 1.6 for body
- **Text alignment**: Left for body, center for hero/branding

---

## Spacing System

### Spacing Scale

| Unit | Pixels | Usage |
|------|--------|-------|
| 4 | 4px | Micro spacing, icon padding |
| 8 | 8px | Small gaps, inline elements |
| 12 | 12px | Compact spacing, form elements |
| 16 | 16px | Standard spacing, cards |
| 24 | 24px | Section separation |
| 32 | 32px | Major section gaps |
| 48 | 48px | Large vertical spacing |
| 64 | 64px | Hero sections, major divisions |

### Spacing Rules

- **Consistent 8px grid**—all spacing is a multiple of 4px
- **Negative space**—don't fear whitespace
- **Section separation**—use 48px+ between major sections
- **Card padding**—minimum 24px internal padding

---

## Components

### Cards

- Background: `#0B0B0B` (dark) or `#FFFFFF` (light)
- Border: 1px solid `#1A1A1A` (dark) or `#E5E5E5` (light)
- Radius: 8px
- Padding: 24px
- Shadow: Subtle, none for flat design

### Badges

- Background: Ownex Blue `#2D7FF9`
- Text: White
- Radius: 4px
- Padding: 4px 12px
- Font: 12px, medium weight

### Screenshots

- Border: 1px solid `#1A1A1A` (dark) or `#E5E5E5` (light)
- Radius: 8px
- Width: 100% (responsive)
- Shadow: Subtle drop shadow for depth
- Caption: 14px, secondary text color

### Code Blocks

- Background: `#1A1A1A` (dark) or `#F5F5F5` (light)
- Border: 1px solid `#2D2D2D` (dark) or `#E0E0E0` (light)
- Radius: 4px
- Padding: 16px
- Font: 14px monospace

### Callouts

- Background: Transparent
- Border-left: 4px solid Ownex Blue
- Padding: 16px
- Font: 14px

---

## Imagery

### Image Hierarchy

**Level 1**: Hero / Brand
- Purpose: Establish identity
- Frequency: 1 per repository
- Reuse: Prohibited

**Level 2**: Product Screenshots
- Purpose: Show real software
- Frequency: 5-8 unique screens
- Reuse: Per section only

**Level 3**: Architecture Diagrams
- Purpose: Explain technical structure
- Frequency: 1-3 diagrams
- Reuse: Per documentation section

**Level 4**: Supporting Illustrations
- Purpose: Clarify concepts
- Frequency: Minimal
- Reuse: As needed

**Level 5**: Decorative Elements
- Purpose: Visual polish
- Frequency: Very minimal
- Reuse: Prohibited

### Screenshot Guidelines

- **Real software only**—no fake UI
- **Consistent viewport**—1920×1080 recommended
- **Representative state**—show typical usage
- **No personal data**—scrub credentials
- **Optimized size**—< 500KB per image
- **Descriptive filenames**—`mission-control.png`, not `screenshot1.png`

### Asset Format Rules

- **SVG** for: logos, icons, diagrams, decorative geometry
- **PNG** for: screenshots, photographic/raster assets
- **WebP** for: complex rendered artwork (optional)
- **Avoid** unnecessary rasterization of vector graphics

---

## Layout Patterns

### README Structure

```
[Logo Lockup]
[Tagline]
[Badges]

[Hero Banner]

[Navigation]

[Overview]

[Product Screenshots]

[Architecture]

[Quick Start]

[Documentation Links]

[Footer]
```

### Section Spacing

- Hero to content: 64px
- Section to section: 48px
- Within section: 24px
- Subsection to subsection: 16px

---

## Quality Standards

### Visual Quality Checklist

- [ ] No pixelation at any size
- [ ] No cropping errors
- [ ] No broken transparency
- [ ] No unexpected borders
- [ ] No color mismatches
- [ ] No compression artifacts
- [ ] No accidental text
- [ ] No misaligned elements
- [ ] No broken images
- [ ] No broken links

### Professional Design Standards

Reject designs that look like:
- Generic startup template
- Canva template
- AI-generated slop
- Stock illustration
- Generic cyberpunk
- Overloaded gradient
- Random neon
- Excessive glassmorphism
- Fake 3D
- Generic "AI brain"
- Generic robot
- Generic circuit
- Random glowing orb

Rely on:
- Geometry
- Spacing
- Typography
- Hierarchy
- Negative space
- Precision
- Restraint

---

## File Naming

### Naming Convention

Use deterministic, descriptive names:

**Good**:
- `ownex-hero-primary.svg`
- `ownex-logo-mark.svg`
- `mission-control.png`
- `opportunity-intelligence.png`

**Bad**:
- `final.png`
- `final2.png`
- `new.png`
- `image.png`
- `cool-banner.png`

### Versioning

Do not create:
- `hero-final`
- `hero-final2`
- `hero-final-v3`

Instead:
- Replace the canonical asset if design changes
- Update the asset registry
- Record significant changes in design documentation

---

## Implementation Guidelines

### Before Creating New Assets

1. **Search the registry**—does a suitable asset already exist?
2. **Check reuse policy**—is this asset allowed to be duplicated?
3. **Verify necessity**—does this asset solve a specific visual problem?
4. **Validate against design system**—does it match our standards?

### After Creating Assets

1. **Register in ASSET_REGISTRY.md**
2. **Update references** in README/documentation
3. **Run validation script** to check for broken links/duplicates
4. **Commit with descriptive message**

---

## Design Review Gate

Before accepting any visual asset, evaluate:

- [ ] Is it necessary?
- [ ] Is it unique?
- [ ] Does it communicate something?
- [ ] Does it reinforce OWNEX?
- [ ] Does it match the design system?
- [ ] Does it look professional?
- [ ] Does it improve the repository?

If the answer to any is **NO**: do not use the asset.

---

## Maintenance

### Regular Tasks

- **Weekly**: Review new assets for compliance
- **Monthly**: Audit for unused/duplicate assets
- **Quarterly**: Review design system for updates
- **Annually**: Refresh brand guidelines if needed

### When the Design System Changes

1. Update this document
2. Announce changes to team
3. Schedule migration of existing assets
4. Update ASSET_REGISTRY.md
5. Validate all references

---

## References

- **Asset Registry**: `ASSET_REGISTRY.md`
- **Brand Guidelines**: `BRAND_GUIDELINES.md`
- **Screenshot Guidelines**: `SCREENSHOT_GUIDELINES.md`
- **Validation Script**: `scripts/design/validate_assets.py`

---

## Version

**Current Version**: 1.0
**Last Updated**: 2025-01-10
**Status**: Active
