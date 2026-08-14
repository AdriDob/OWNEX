# OWNEX Screenshot Guidelines

## Philosophy

OWNEX screenshots must show **real software functionality**. No fake UI, no generated dashboards, no promotional renders. The actual application is the only acceptable source.

---

## Screenshot Pipeline

### Prerequisites

1. **Application Running**: Backend and frontend must be running
2. **Representative State**: Screens should show typical usage, not empty states
3. **No Personal Data**: Scrub credentials, tokens, emails, before capture
4. **Consistent Viewport**: Use standard 1920×1080 for desktop, 390×844 for mobile

### Capture Tool

Use **Playwright** for automated screenshot capture:

```bash
python scripts/capture_real_screenshots.py
```

This script:
- Launches headless browser
- Navigates to each route
- Waits for animations to complete
- Captures full-page or viewport screenshots
- Saves to `docs/assets/screenshots/desktop/`

---

## Screenshot Requirements

### Technical Requirements

| Requirement | Value | Notes |
|-------------|-------|-------|
| Resolution | 1920×1080 (desktop), 390×844 (mobile) | Standard viewport sizes |
| Format | PNG | Lossless compression |
| File Size | < 500KB | Optimize after capture |
| Naming | `{screen-name}.png` | Descriptive, not generic |
| Transparency | No | Opaque backgrounds only |

### Content Requirements

- **Real Application**: Must be actual UI, not mockups
- **Representative State**: Show typical usage with data
- **No Personal Data**: Scrub all credentials and PII
- **No Debug Info**: Hide console, dev tools, debug overlays
- **Consistent Theme**: Use dark theme for consistency

---

## Screenshot Categories

### Level 1: Core Surfaces (Required)

These screenshots are essential for the README:

| Screen | Route | Purpose | Frequency |
|--------|-------|---------|-----------|
| Mission Control | `/mission-control` | Central operational surface | 1 |
| Intelligence | `/intelligence` | Information processing | 1 |
| Targets | `/targets` | Target prioritization | 1 |
| Capital | `/capital` | Revenue tracking | 1 |
| MERLIN | `/merlin` | AI assistant | 1 |
| Agents | `/agents` | Agent center | 1 |
| Reports | `/reports` | Report center | 1 |
| Settings | `/settings` | Configuration | 1 |

### Level 2: Supporting Surfaces (Optional)

These may be added for specific documentation:

| Screen | Route | Purpose | Frequency |
|--------|-------|---------|-----------|
| Evidence | `/evidence` | Evidence management | As needed |
| Discovery | `/discovery` | Opportunity discovery | As needed |
| Execution | `/execution` | Work execution queue | As needed |

### Level 3: Mobile (Optional)

Mobile screenshots for mobile-specific documentation:

| Screen | Route | Purpose | Frequency |
|--------|-------|---------|-----------|
| Mission Control | `/mission-control` | Mobile dashboard | As needed |

---

## Capture Procedure

### 1. Prepare Application State

```bash
# Start backend
python run.py &

# Start frontend
cd frontend && npm run dev &
```

Wait for both to be fully operational (~30-60 seconds).

### 2. Ensure Representative Data

Before capturing:
- Log in with test credentials
- Populate with sample data if needed
- Navigate to target screen
- Ensure state is typical (not empty, not error)

### 3. Capture Screenshot

**Automated** (recommended):
```bash
python scripts/capture_real_screenshots.py
```

**Manual** (if needed):
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto("http://localhost:5173/mission-control")
    page.wait_for_load_state("networkidle")
    page.screenshot(path="docs/assets/screenshots/desktop/mission-control.png")
    browser.close()
```

### 4. Review and Optimize

After capture:
- Review for quality and content
- Check file size (should be < 500KB)
- Optimize if needed using ImageMagick or Sharp
- Register in ASSET_REGISTRY.md

---

## Naming Convention

### Pattern

`{screen-name}.png`

### Examples

**Good**:
- `mission-control.png` ✅
- `intelligence.png` ✅
- `targets.png` ✅
- `capital.png` ✅

**Bad**:
- `screenshot1.png` ❌
- `dashboard.png` ❌
- `final.png` ❌
- `new-capture.png` ❌

### Rules

- Use lowercase
- Use hyphens for spaces
- Be descriptive of the screen's purpose
- No version numbers (e.g., `v2`, `final`)

---

## Optimization

### PNG Optimization

After capture, optimize file size:

```bash
# Using pngquant (recommended)
pngquant --quality=85-95 --output docs/assets/screenshots/desktop/mission-control.png docs/assets/screenshots/desktop/mission-control.png

# Using optipng
optipng -o2 docs/assets/screenshots/desktop/mission-control.png
```

### Size Targets

| Type | Target Size | Maximum |
|------|-------------|---------|
| Desktop screenshot | < 300KB | 500KB |
| Mobile screenshot | < 200KB | 300KB |
| Hero image | < 500KB | 1MB |

---

## Privacy and Security

### Data Scrubbing

Before capturing, ensure:
- No API keys visible
- No tokens visible
- No email addresses visible
- No passwords visible
- No IP addresses visible (unless public)
- No internal URLs visible

### Environment

- Use test/staging environment when possible
- Use demo accounts when possible
- Never capture production data with real user information

---

## Registration

### After Capture

1. **Add to ASSET_REGISTRY.md**:
   ```yaml
   - id: screenshot-mission-control
     file: docs/assets/screenshots/desktop/mission-control.png
     type: screenshot
     purpose: Mission Control showcase
     dimensions: 1920×1080
     format: PNG
     status: approved
     reuse: prohibited
   ```

2. **Update README.md** (if needed):
   ```markdown
   ### Mission Control
   > Central operational surface for monitoring opportunities, agents and active work.

   <p align="center">
     <img src="docs/assets/screenshots/desktop/mission-control.png" alt="Mission Control" width="100%"/>
   </p>
   ```

3. **Run validation**:
   ```bash
   python scripts/design/validate_assets.py
   ```

---

## Quality Checklist

Before finalizing a screenshot:

- [ ] Application is running
- [ ] Screen shows real functionality
- [ ] State is representative (not empty)
- [ ] No personal data visible
- [ ] No debug tools visible
- [ ] Resolution is correct (1920×1080 or 390×844)
- [ ] File size is optimized (< 500KB)
- [ ] Naming follows convention
- [ ] Asset is registered in ASSET_REGISTRY.md
- [ ] Reference is added to README/docs

---

## Common Issues

### Blurry Screenshots

**Cause**: Low DPI scaling
**Fix**: Set device scale factor in Playwright:
```python
page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
```

### Incomplete Loading

**Cause**: Screenshot captured before animations complete
**Fix**: Add explicit wait:
```python
page.wait_for_load_state("networkidle")
time.sleep(3)  # Wait for animations
```

### Wrong Theme

**Cause**: Light theme instead of dark
**Fix**: Ensure theme preference is set in localStorage or configuration

### Too Large File Size

**Cause**: Unoptimized PNG
**Fix**: Run pngquant or optipng optimization

---

## Screenshot Refresh

### When to Refresh

Refresh screenshots when:
- UI changes significantly
- New features are added
- Data model changes
- Theme updates
- Quarterly review (at minimum)

### Process

1. Capture new screenshot
2. Replace existing file
3. Update ASSET_REGISTRY.md (if needed)
4. Update README.md references (if needed)
5. Run validation script
6. Commit with message: `chore: refresh {screen-name} screenshot`

---

## Validation

### Automated Validation

Run the validation script to check:
```bash
python scripts/design/validate_assets.py
```

This checks:
- All registered screenshots exist
- No unregistered screenshots
- File size constraints
- Format constraints
- Broken references in README.md

### Manual Validation

- Open README.md in GitHub
- Check dark mode rendering
- Check light mode rendering
- Check mobile rendering (390px width)
- Verify all images load correctly

---

## Troubleshooting

### Application Won't Start

**Issue**: Backend or frontend fails to start
**Check**:
- Port conflicts (try different ports)
- Missing dependencies
- Database issues
- Environment variables

### Playwright Fails

**Issue**: Script crashes or timeout
**Check**:
- Playwright is installed: `pip install playwright`
- Browsers are installed: `playwright install chromium`
- Application is running and accessible
- URLs are correct

### Screenshot Looks Wrong

**Issue**: Visual errors in capture
**Check**:
- Viewport size is correct
- Theme is applied
- No console errors
- Page is fully loaded

---

## References

- **Design System**: `DESIGN_SYSTEM.md`
- **Asset Registry**: `ASSET_REGISTRY.md`
- **Brand Guidelines**: `BRAND_GUIDELINES.md`
- **Validation Script**: `scripts/design/validate_assets.py`
- **Capture Script**: `scripts/capture_real_screenshots.py`

---

## Version

**Current Version**: 1.0
**Last Updated**: 2025-01-10
**Status**: Active
