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
| `brand-logo-primary` | `docs/assets/branding/logo/ownex-lockup.svg` | logo | Primary brand identity | 600×120 | SVG | approved | allowed | README.md | Main lockup for all branding |

### Logo Variants

| ID | File | Type | Purpose | Dimensions | Format | Status | Reuse | References | Notes |
|----|------|------|---------|------------|--------|--------|-------|------------|-------|
| `brand-logo-dark` | `docs/assets/branding/logo/ownex-lockup-white.svg` | logo | Dark backgrounds | 600×120 | SVG | approved | allowed | README.md | Use on dark surfaces |
| `brand-logo-light` | `docs/assets/branding/logo/ownex-lockup-black.svg` | logo | Light backgrounds | 600×120 | SVG | approved | allowed | README.md | Use on light surfaces |
| `brand-logo-dark-png` | `docs/assets/branding/logo/ownex-lockup-white.png` | logo | Dark backgrounds (PNG fallback) | 600×120 | PNG | approved | allowed | - | PNG fallback for SVG |
| `brand-logo-light-png` | `docs/assets/branding/logo/ownex-lockup-black.png` | logo | Light backgrounds (PNG fallback) | 600×120 | PNG | approved | allowed | - | PNG fallback for SVG |
| `brand-mark-primary` | `docs/assets/branding/logo/ownex-mark.svg` | logo | Iconography, small sizes | 512×512 | SVG | approved | allowed | favicon.svg | Convergence symbol only |
| `brand-mark-dark` | `docs/assets/branding/logo/ownex-mark-white.svg` | logo | Dark backgrounds, small | 512×512 | SVG | approved | allowed | - | Mark on dark surfaces |
| `brand-mark-light` | `docs/assets/branding/logo/ownex-mark-black.svg` | logo | Light backgrounds, small | 512×512 | SVG | approved | allowed | - | Mark on light surfaces |
| `brand-mark-dark-png` | `docs/assets/branding/logo/ownex-mark-white.png` | logo | Dark backgrounds (PNG fallback) | 512×512 | PNG | approved | allowed | - | PNG fallback for SVG |
| `brand-mark-light-png` | `docs/assets/branding/logo/ownex-mark-black.png` | logo | Light backgrounds (PNG fallback) | 512×512 | PNG | approved | allowed | - | PNG fallback for SVG |
| `brand-wordmark` | `docs/assets/branding/logo/ownex-wordmark.svg` | logo | Typography-only | 400×80 | SVG | approved | conditional | - | Use when mark alone is insufficient |
| `brand-wordmark-dark` | `docs/assets/branding/logo/ownex-wordmark-white.svg` | logo | Typography-only (dark) | 400×80 | SVG | approved | conditional | - | Use on dark backgrounds |
| `brand-wordmark-light` | `docs/assets/branding/logo/ownex-wordmark-black.svg` | logo | Typography-only (light) | 400×80 | SVG | approved | conditional | - | Use on light backgrounds |
| `brand-wordmark-dark-png` | `docs/assets/branding/logo/ownex-wordmark-white.png` | logo | Typography-only (dark PNG) | 400×80 | PNG | approved | conditional | - | PNG fallback for SVG |
| `brand-wordmark-light-png` | `docs/assets/branding/logo/ownex-wordmark-black.png` | logo | Typography-only (light PNG) | 400×80 | PNG | approved | conditional | - | PNG fallback for SVG |

### Favicon

| ID | File | Type | Purpose | Dimensions | Format | Status | Reuse | References | Notes |
|----|------|------|---------|------------|--------|--------|-------|------------|-------|
| `brand-favicon` | `docs/assets/branding/logo/favicon.svg` | favicon | Browser tab icon | 16×16 | SVG | approved | allowed | frontend/public/ | Works at 16×16 scale |
| `brand-favicon-png` | `docs/assets/branding/logo/ownex-favicon.png` | favicon | Browser tab icon (PNG) | 16×16 | PNG | approved | allowed | - | PNG fallback for SVG |

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

### Desktop Screenshots (Real Application)

| ID | File | Type | Purpose | Dimensions | Format | Status | Reuse | References | Notes |
|----|------|------|---------|------------|--------|--------|-------|------------|-------|
| `screenshot-mission-control` | `docs/assets/screenshots/desktop/mission-control.png` | screenshot | Mission Control showcase | 1920×1080 | PNG | approved | prohibited | README.md | Real application screen |
| `screenshot-intelligence` | `docs/assets/screenshots/desktop/intelligence.png` | screenshot | Intelligence surface | 1920×1080 | PNG | approved | prohibited | README.md | Real application screen |
| `screenshot-targets` | `docs/assets/screenshots/desktop/targets.png` | screenshot | Target prioritization | 1920×1080 | PNG | approved | prohibited | README.md | Real application screen |
| `screenshot-capital` | `docs/assets/screenshots/desktop/capital.png` | screenshot | Capital dashboard | 1920×1080 | PNG | approved | prohibited | README.md | Real application screen |
| `screenshot-merlin` | `docs/assets/screenshots/desktop/merlin.png` | screenshot | MERLIN copilot | 1920×1080 | PNG | approved | prohibited | README.md | Real application screen |
| `screenshot-agents` | `docs/assets/screenshots/desktop/agents.png` | screenshot | Agent center | 1920×1080 | PNG | approved | prohibited | README.md | Real application screen |
| `screenshot-settings` | `docs/assets/screenshots/desktop/settings.png` | screenshot | Settings surface | 1920×1080 | PNG | approved | prohibited | README.md | Real application screen |

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
