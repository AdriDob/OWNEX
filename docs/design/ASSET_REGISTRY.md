# OWNEX Asset Registry

> **Rule**: Every visual asset must be registered here. No asset may exist without a registry entry.
> **Rule**: Check this registry before creating new assets. Reuse when possible.

---

## Registry Format

Each asset has:
- `id`: Unique identifier
- `file`: Relative path from repository root
- `type`: Asset category
- `purpose`: Design function
- `dimensions`: Width × Height (pixels)
- `format`: File format
- `status`: approved, deprecated, pending
- `reuse`: allowed, prohibited, conditional
- `references`: Files that reference this asset
- `notes`: Usage instructions or constraints

---

## Brand Assets

### Logo Primary

| ID | File | Type | Purpose | Dimensions | Format | Status | Reuse | References | Notes |
|----|------|------|---------|------------|--------|--------|-------|------------|-------|
| `brand-logo-primary` | `docs/assets/branding/logo/ownex-symbol-wordmark.svg` | logo | Primary brand identity | 600×120 | SVG | approved | allowed | README.md | Main lockup for all branding |
| `brand-lockup-horizontal` | `docs/assets/branding/logo/ownex-horizontal-lockup.svg` | logo | Horizontal lockup with descriptor | 800×160 | SVG | approved | allowed | - | Horizontal format with descriptor |
| `brand-lockup-vertical` | `docs/assets/branding/logo/ownex-vertical-lockup.svg` | logo | Vertical lockup (stacked) | 400×500 | SVG | approved | allowed | - | Vertical format for tall spaces |

### Logo Variants

| ID | File | Type | Purpose | Dimensions | Format | Status | Reuse | References | Notes |
|----|------|------|---------|------------|--------|--------|-------|------------|-------|
| `brand-symbol-only` | `docs/assets/branding/logo/ownex-symbol-only.svg` | logo | Symbol only | 512×512 | SVG | approved | allowed | - | Use when wordmark not needed |
| `brand-wordmark-only` | `docs/assets/branding/logo/ownex-wordmark-only.svg` | logo | Custom wordmark only | 400×80 | SVG | approved | allowed | - | Path-based custom wordmark |
| `brand-wordmark-custom` | `docs/assets/branding/logo/ownex-wordmark-custom.svg` | logo | Custom wordmark (font-based) | 400×80 | SVG | approved | conditional | - | Sora-based with O/X geometry |
| `brand-logo-dark` | `docs/assets/branding/logo/ownex-dark-mode.svg` | logo | Dark backgrounds | 600×120 | SVG | approved | allowed | README.md | Use on dark surfaces |
| `brand-logo-light` | `docs/assets/branding/logo/ownex-light-mode.svg` | logo | Light backgrounds | 600×120 | SVG | approved | allowed | README.md | Use on light surfaces |
| `brand-mark-primary` | `docs/assets/branding/logo/ownex-mark.svg` | logo | Iconography, small sizes | 512×512 | SVG | approved | allowed | favicon.svg | Convergence symbol only |
| `brand-mark-dark` | `docs/assets/branding/logo/ownex-mark-white.svg` | logo | Dark backgrounds, small | 512×512 | SVG | approved | allowed | - | Mark on dark surfaces |
| `brand-mark-light` | `docs/assets/branding/logo/ownex-mark-black.svg` | logo | Light backgrounds, small | 512×512 | SVG | approved | allowed | - | Mark on light surfaces |
| `brand-monochrome` | `docs/assets/branding/logo/ownex-monochrome.svg` | logo | Single color version | 600×120 | SVG | approved | allowed | - | For single-color applications |
| `brand-symbol-wordmark` | `docs/assets/branding/logo/ownex-symbol-wordmark.svg` | logo | Symbol + wordmark | 600×120 | SVG | approved | allowed | README.md | Primary lockup |
| `brand-symbol-wordmark-descriptor` | `docs/assets/branding/logo/ownex-symbol-wordmark-descriptor.svg` | logo | Symbol + wordmark + descriptor | 600×160 | SVG | approved | allowed | - | Full lockup with descriptor |

### Favicon

| ID | File | Type | Purpose | Dimensions | Format | Status | Reuse | References | Notes |
|----|------|------|---------|------------|--------|--------|-------|------------|-------|
| `brand-favicon` | `docs/assets/branding/logo/favicon.svg` | favicon | Browser tab icon | 16×16 | SVG | approved | allowed | frontend/public/ | Works at 16×16 scale |
| `brand-favicon-png` | `docs/assets/branding/logo/ownex-favicon.png` | favicon | Browser tab icon (PNG) | 16×16 | PNG | approved | allowed | - | PNG fallback for SVG |
| `brand-favicon-svg` | `docs/assets/branding/logo/ownex-favicon.svg` | favicon | Browser tab icon (variant) | 16×16 | SVG | approved | allowed | - | Alternative favicon |

### Wordmark Custom Variants

| ID | File | Type | Purpose | Dimensions | Format | Status | Reuse | References | Notes |
|----|------|------|---------|------------|--------|--------|-------|------------|-------|
| `brand-wordmark-path` | `docs/assets/branding/logo/ownex-wordmark-path.svg` | logo | Path-based wordmark | 400×80 | SVG | approved | allowed | - | No font dependency |
| `brand-wordmark-path-white` | `docs/assets/branding/logo/ownex-wordmark-path-white.svg` | logo | Path-based wordmark (white) | 400×80 | SVG | approved | allowed | - | White on dark |
| `brand-wordmark-path-black` | `docs/assets/branding/logo/ownex-wordmark-path-black.svg` | logo | Path-based wordmark (black) | 400×80 | SVG | approved | allowed | - | Black on light |
| `brand-wordmark-path-blue` | `docs/assets/branding/logo/ownex-wordmark-path-blue.svg` | logo | Path-based wordmark (blue) | 400×80 | SVG | approved | allowed | - | Blue accent |
| `brand-wordmark-custom` | `docs/assets/branding/logo/ownex-wordmark-custom.svg` | logo | Sora-based custom wordmark | 400×80 | SVG | approved | conditional | - | Font-based with O/X geometry |
| `brand-wordmark-custom-white` | `docs/assets/branding/logo/ownex-wordmark-custom-white.svg` | logo | Custom wordmark (white) | 400×80 | SVG | approved | conditional | - | White on dark |
| `brand-wordmark-custom-black` | `docs/assets/branding/logo/ownex-wordmark-custom-black.svg` | logo | Custom wordmark (black) | 400×80 | SVG | approved | conditional | - | Black on light |
| `brand-wordmark-custom-blue` | `docs/assets/branding/logo/ownex-wordmark-custom-blue.svg` | logo | Custom wordmark (blue) | 400×80 | SVG | approved | conditional | - | Blue accent |
| `brand-descriptor` | `docs/assets/branding/logo/ownex-descriptor.svg` | logo | Descriptor text | 500×30 | SVG | approved | allowed | - | AUTONOMOUS WORK OPERATING SYSTEM |

### Legacy Assets (Deprecated)

| ID | File | Type | Purpose | Dimensions | Format | Status | Reuse | References | Notes |
|----|------|------|---------|------------|--------|--------|-------|------------|-------|
| `legacy-mark-mono` | `docs/assets/branding/logo/ownex-mark-mono.svg` | logo | Legacy monochrome | 512×512 | SVG | deprecated | prohibited | - | Do not use in new content |
| `legacy-mark-mono-png` | `docs/assets/branding/logo/ownex-mark-mono.png` | logo | Legacy monochrome (PNG) | 512×512 | PNG | deprecated | prohibited | - | Do not use in new content |
| `legacy-mark-omega` | `docs/assets/branding/logo/ownex-mark-omega.svg` | logo | Legacy variant | 512×512 | SVG | deprecated | prohibited | - | Do not use in new content |
| `legacy-mark-omega-png` | `docs/assets/branding/logo/ownex-mark-omega.png` | logo | Legacy variant (PNG) | 512×512 | PNG | deprecated | prohibited | - | Do not use in new content |
| `legacy-wordmark-mono` | `docs/assets/branding/logo/ownex-wordmark-mono.svg` | logo | Legacy wordmark monochrome | 400×80 | SVG | deprecated | prohibited | - | Do not use in new content |
| `legacy-wordmark-mono-png` | `docs/assets/branding/logo/ownex-wordmark-mono.png` | logo | Legacy wordmark monochrome (PNG) | 400×80 | PNG | deprecated | prohibited | - | Do not use in new content |
| `legacy-horizontal` | `docs/assets/branding/legacy/ownex-logo-horizontal.svg` | logo | Old branding | 400×80 | SVG | deprecated | prohibited | - | Historical reference only |
| `legacy-favicon-32` | `docs/assets/branding/legacy/favicon-32.svg` | favicon | Legacy favicon | 32×32 | SVG | deprecated | prohibited | - | Historical reference only |
| `legacy-logo-mark` | `docs/assets/branding/legacy/ownex-logo-mark.svg` | logo | Legacy mark | 512×512 | SVG | deprecated | prohibited | - | Historical reference only |

---

## Hero Assets

### Primary Hero

| ID | File | Type | Purpose | Dimensions | Format | Status | Reuse | References | Notes |
|----|------|------|---------|------------|--------|--------|-------|------------|-------|
| `hero-primary` | `docs/assets/branding/banners/ownex-hero-banner.svg` | hero | GitHub README header | 2400×900 | SVG | approved | prohibited | README.md | Only for repository header |
| `hero-primary-png` | `docs/assets/branding/banners/ownex-hero-banner.png` | hero | GitHub README header | 2400×900 | PNG | approved | prohibited | README.md | PNG fallback for SVG |

---

## Social Assets

### Social Preview

| ID | File | Type | Purpose | Dimensions | Format | Status | Reuse | References | Notes |
|----|------|------|---------|------------|--------|--------|-------|------------|-------|
| `social-preview` | `docs/assets/branding/social/ownex-social-preview.svg` | social | Open Graph image | 1200×630 | SVG | approved | prohibited | - | For social sharing only |
| `social-preview-png` | `docs/assets/branding/social/ownex-social-preview.png` | social | Open Graph image | 1200×630 | PNG | approved | prohibited | - | PNG fallback for OG tags |

---

## Screenshot Assets

### Desktop Screenshots (Demo)

| ID | File | Type | Purpose | Dimensions | Format | Status | Reuse | References | Notes |
|----|------|------|---------|------------|--------|--------|-------|------------|-------|
| `screenshot-mission-control` | `docs/assets/screenshots/desktop/mission-control-demo.png` | screenshot | Mission Control showcase | 1920×1080 | PNG | approved | prohibited | README.md | Demo SVG screenshot |
| `screenshot-intelligence` | `docs/assets/screenshots/desktop/intelligence-demo.png` | screenshot | Intelligence surface | 1920×1080 | PNG | approved | prohibited | README.md | Demo SVG screenshot |
| `screenshot-targets` | `docs/assets/screenshots/desktop/targets-demo.png` | screenshot | Target prioritization | 1920×1080 | PNG | approved | prohibited | README.md | Demo SVG screenshot |
| `screenshot-capital` | `docs/assets/screenshots/desktop/capital-demo.png` | screenshot | Capital dashboard | 1920×1080 | PNG | approved | prohibited | README.md | Demo SVG screenshot |
| `screenshot-merlin` | `docs/assets/screenshots/desktop/merlin-demo.png` | screenshot | MERLIN copilot | 1920×1080 | PNG | approved | prohibited | README.md | Demo SVG screenshot |
| `screenshot-agents` | `docs/assets/screenshots/desktop/agents-demo.png` | screenshot | Agent center | 1920×1080 | PNG | approved | prohibited | README.md | Demo SVG screenshot |
| `screenshot-reports` | `docs/assets/screenshots/desktop/reports-demo.png` | screenshot | Reports tracking | 1920×1080 | PNG | approved | prohibited | README.md | Demo SVG screenshot |
| `screenshot-settings` | `docs/assets/screenshots/desktop/settings-demo.png` | screenshot | Settings surface | 1920×1080 | PNG | approved | prohibited | README.md | Demo SVG screenshot |

### Legacy Screenshots (Pending Review)

| ID | File | Type | Purpose | Dimensions | Format | Status | Reuse | References | Notes |
|----|------|------|---------|------------|--------|--------|-------|------------|-------|
| `legacy-agent-center` | `docs/assets/screenshots/desktop/agent-center.png` | screenshot | Old agent view | 1920×1080 | PNG | pending | prohibited | - | Evaluate if still needed |
| `legacy-capital-dashboard` | `docs/assets/screenshots/desktop/capital-dashboard.png` | screenshot | Old capital view | 1920×1080 | PNG | pending | prohibited | - | Evaluate if still needed |
| `legacy-executive-dashboard` | `docs/assets/screenshots/desktop/executive-dashboard.png` | screenshot | Old executive view | 1920×1080 | PNG | pending | prohibited | - | Evaluate if still needed |
| `legacy-good-morning` | `docs/assets/screenshots/desktop/good-morning.png` | screenshot | Old morning view | 1920×1080 | PNG | pending | prohibited | - | Evaluate if still needed |
| `legacy-operations` | `docs/assets/screenshots/desktop/operations.png` | screenshot | Old operations view | 1920×1080 | PNG | pending | prohibited | - | Evaluate if still needed |

### Mobile Screenshots

| ID | File | Type | Purpose | Dimensions | Format | Status | Reuse | References | Notes |
|----|------|------|---------|------------|--------|--------|-------|------------|-------|
| `screenshot-mobile-mission-control` | `docs/assets/screenshots/mobile/mission-control.png` | screenshot | Mobile mission control | 390×844 | PNG | approved | prohibited | - | Real mobile application |

---

## Reuse Policies

### Allowed Reuse

These assets may appear multiple times in the repository:
- `brand-logo-primary` — Main brand lockup
- `brand-logo-dark` — Dark background variant
- `brand-logo-light` — Light background variant
- `brand-mark-primary` — Icon for small sizes
- `brand-favicon` — Browser favicon

### Prohibited Reuse

These assets must NOT be duplicated or reused in multiple contexts:
- `hero-primary` — Only for README header
- `hero-primary-png` — Only for README header
- `social-preview` — Only for Open Graph
- `social-preview-png` — Only for Open Graph
- All screenshots — Each screen is unique to its purpose

### Conditional Reuse

These assets may be reused with specific justification:
- `brand-wordmark` — Use only when mark alone is insufficient (e.g., documents where full lockup is too large)

---

## Asset Hierarchy

### Level 1: Brand Identity (Highest Priority)
- `brand-logo-primary`
- `brand-logo-dark`
- `brand-logo-light`
- `brand-mark-primary`

### Level 2: Hero / Visual Statement
- `hero-primary`
- `hero-primary-png`

### Level 3: Product Evidence
- All screenshots (desktop + mobile)

### Level 4: Social / Distribution
- `social-preview`
- `social-preview-png`

### Level 5: Supporting Elements
- `brand-favicon`
- `brand-wordmark`

---

## Pending Actions

### Clean Up
- [ ] Review legacy assets for deletion or migration
- [ ] Remove `legacy-mark-mono.svg` if unused
- [ ] Remove `legacy-mark-omega.svg` if unused
- [ ] Remove `legacy-horizontal.svg` if unused
- [ ] Evaluate 5 legacy screenshots for relevance

### New Screenshots Needed
- [ ] Evidence center screenshot
- [ ] Opportunity discovery screenshot
- [ ] Agent activity log screenshot

### Optimization
- [ ] Compress large PNG files (currently ~500KB each)
- [ ] Consider WebP format for screenshots to reduce size
- [ ] Verify all SVGs are optimized (no unnecessary paths)

---

## Asset Creation Rules

### Before Creating New Assets

1. **Search this registry** — Does a suitable asset already exist?
2. **Check reuse policy** — Is duplication allowed for this asset type?
3. **Verify necessity** — Does this asset solve a specific visual problem?
4. **Validate against DESIGN_SYSTEM.md** — Does it match our standards?

### After Creating Assets

1. **Add entry to this registry** — Complete all fields
2. **Update references** — Add to README.md or documentation
3. **Run validation script** — `python scripts/design/validate_assets.py`
4. **Commit with descriptive message** — Include asset ID in commit

### Asset Naming Convention

Use this pattern: `{category}-{specific-purpose}.{format}`

**Examples**:
- `ownex-hero-primary.svg` ✅
- `mission-control.png` ✅
- `social-preview.png` ✅

**Anti-patterns**:
- `final.png` ❌
- `new-banner.svg` ❌
- `screenshot1.png` ❌
- `cool-hero.png` ❌

---

## Validation

Run this command to validate all assets:

```bash
python scripts/design/validate_assets.py
```

This checks:
- All registered assets exist
- No unregistered assets in docs/assets/
- No broken image references in README.md
- No duplicate assets (SHA-256 hash)
- File size constraints
- Format constraints

---

## Statistics

- **Total Assets**: 40
- **Brand Assets**: 8 (primary) + 3 (legacy)
- **Hero Assets**: 2
- **Social Assets**: 2
- **Screenshots**: 8 (active) + 5 (legacy) + 1 (mobile)
- **SVG Format**: 22
- **PNG Format**: 18
- **Approved**: 18
- **Deprecated**: 3
- **Pending**: 5

---

## Version

**Current Version**: 1.0
**Last Updated**: 2025-01-10
**Last Audit**: 2025-01-10
**Next Audit**: 2025-02-10
