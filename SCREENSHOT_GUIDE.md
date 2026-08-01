# OWNEX Screenshot Guide

Guidelines for capturing and organizing OWNEX application screenshots.

## Screenshot Standards

### Technical Requirements

- **Format**: PNG (lossless)
- **Resolution**: Minimum 1920x1080 (desktop), 1080x1920 (mobile)
- **Scale**: 100% (no scaling)
- **Compression**: None (PNG)
- **Background**: Clean, no clutter

### Content Guidelines

1. **Context**: Show relevant UI elements
2. **State**: Use realistic data (not "Lorem Ipsum")
3. **Lighting**: Consistent ambient lighting
4. **Focus**: Sharp, no blur
5. **Alignment**: Properly aligned windows

## Screenshot Categories

### Desktop Screenshots (ALPHA)

#### Mission Control
- `mission-control-dashboard.png` - Main dashboard view
- `mission-control-agents.png` - Agent fleet status
- `mission-control-opportunities.png` - Opportunities list
- `mission-control-revenue.png` - Revenue analytics

#### Core Operations
- `core-scheduler.png` - Scheduler interface
- `core-workflows.png` - Workflow execution
- `core-memory.png` - Memory browser
- `core-settings.png` - System settings

#### MERLIN Assistant
- `merlin-chat.png` - Chat interface
- `merlin-memory.png` - Memory context
- `merlin-settings.png` - MERLIN configuration

### Mobile Screenshots (OMEGA)

#### Main Interface
- `omega-dashboard.png` - Mobile dashboard
- `omega-notifications.png` - Notification center
- `omega-approvals.png` - Approval requests
- `omega-settings.png` - App settings

#### MERLIN Mobile
- `omega-merlin-chat.png` - Mobile chat
- `omega-merlin-voice.png` - Voice interface

## Screenshot Capture Process

### Desktop Screenshots

1. **Preparation**
   - Clean desktop (no personal files)
   - Set theme to Dark Mode
   - Disable notifications
   - Use realistic test data

2. **Capture**
   - Use system screenshot tool (Cmd+Shift+4 / Win+Shift+S)
   - Capture full window (including shadows)
   - Maintain proper window sizing
   - Include status bar if relevant

3. **Post-Processing**
   - Crop to content area (no extra space)
   - Ensure proper resolution
   - Add subtle drop shadow if needed
   - Save as PNG with descriptive name

### Mobile Screenshots

1. **Preparation**
   - Clean device screen
   - Set device to airplane mode
   - Use test account
   - Enable developer options

2. **Capture**
   - Use device screenshot (Power+Volume)
   - Or use Android Studio emulator
   - Capture full screen
   - Include status bar

3. **Post-Processing**
   - Remove status bar if desired
   - Add device frame if needed
   - Ensure proper resolution
   - Save as PNG with descriptive name

## File Naming Convention

### Format

```
[edition]-[component]-[view]-[state].png
```

### Examples

- `alpha-mission-control-dashboard-active.png`
- `alpha-merlin-chat-typing.png`
- `omega-dashboard-idle.png`
- `omega-approvals-pending.png`

### Naming Rules

- Use lowercase letters
- Use hyphens as separators
- Be descriptive but concise
- Include state information when relevant

## Screenshot Organization

### Directory Structure

```
assets/screenshots/
├── desktop/
│   ├── mission-control/
│   ├── core-operations/
│   ├── merlin/
│   └── settings/
└── mobile/
    ├── dashboard/
    ├── notifications/
    ├── approvals/
    └── merlin/
```

### Metadata

Each screenshot should include a metadata file:

```json
{
  "filename": "alpha-mission-control-dashboard.png",
  "edition": "ALPHA",
  "component": "Mission Control",
  "view": "Dashboard",
  "state": "Active",
  "resolution": "1920x1080",
  "date": "2026-08-01",
  "version": "7.0.0"
}
```

## Screenshot Usage

### Documentation

- Use in README.md and guides
- Include alt text for accessibility
- Maintain consistent sizing
- Add captions describing functionality

### Marketing

- Use in website hero sections
- Include in app store listings
- Create feature highlights
- Add to presentation decks

### Internal

- Use in design reviews
- Document UI states
- Test visual regression
- Share with stakeholders

## Screenshot Maintenance

### Regular Updates

- Update screenshots when UI changes
- Maintain version consistency
- Archive old screenshots
- Update metadata files

### Quality Control

- Review for consistency
- Check for visual defects
- Verify proper resolution
- Ensure brand compliance

## Tools & Resources

### Capture Tools

- **macOS**: Built-in screenshot (Cmd+Shift+4)
- **Windows**: Snipping Tool, Win+Shift+S
- **Linux**: Spectacle, Flameshot
- **Mobile**: Device screenshot, Android Studio

### Editing Tools

- **macOS**: Preview, Pixelmator
- **Windows**: Paint.NET, GIMP
- **Linux**: GIMP, Krita
- **Online**: Canva, Figma

### Automation

```bash
# Automated screenshot script
python scripts/capture_screenshots.py --edition alpha --component mission-control
```

## Screenshot Checklist

Before finalizing a screenshot:

- [ ] Resolution meets minimum requirements
- [ ] Content is relevant and clear
- [ ] UI state is appropriate
- [ ] No personal information visible
- [ ] Consistent with brand guidelines
- [ ] Proper file naming convention
- [ ] Metadata file created
- [ ] Organized in correct directory

## Troubleshooting

### Common Issues

**Blurry screenshots**
- Ensure 100% scaling
- Check resolution settings
- Use proper capture method

**Incorrect colors**
- Calibrate display
- Use consistent color profile
- Check theme settings

**Window shadows missing**
- Enable window shadows in OS
- Use full window capture
- Add shadows in post-processing

**Status bar inclusion**
- Decide if needed for context
- Remove if distracting
- Keep consistent across screenshots

## Contact

For screenshot-related questions:
- Email: design@ownex.ai
- Documentation: SCREENSHOT_GUIDE.md
- Assets: assets/screenshots/

---

**OWNEX Screenshot Guide v1.0**
**Autonomous Personal Operating System**
