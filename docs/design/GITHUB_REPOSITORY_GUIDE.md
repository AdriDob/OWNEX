# OWNEX GitHub Repository — Definitive Presentation Design

> **Version**: 1.0
> **Status**: Active
> **Asset Policy**: No SVG, no real screenshots — 100% AI-generated images (consistent, high quality, faithful to the product).

---

## 1. Repository Mission

OWNEX presents itself as **"Autonomous Work Operating System"** — a personal mission control that runs automated wealth-generation cycles (bug bounty, dev bounty, direct work, AI work, revenue).

The GitHub repository is the **first contact** for potential users, contributors, and the operator's own daily reference.

**Design principles:**

1. **Tesla dark aesthetic** — pure black `#05060A`, white primary, cyan `#00D5FF`/blue `#1E40FF` accents, emerald `#00E39A` success, orange `#FF7A1A` decisions
2. **No noise** — no neon, no glow, no particles, no background gradients
3. **High fidelity** — every image depicts the real product surfaces (from code, not from imagination)
4. **Consistency** — all assets follow the design tokens (`assets/branding/themes/tesla.json`)

---

## 2. Asset Architecture

All repository images live under `docs/assets/github/`:

```
docs/assets/github/
├── hero/
│   ├── hero-banner-dark.png      # 2400×900 — top of README
│   ├── hero-banner-light.png     # Same layout, light variant
│   └── hero-banner-og.png        # 1200×630 — Open Graph
├── logo/
│   ├── mark-alpha.png            # 1024×1024 — cyan/blue mark on black
│   ├── mark-omega.png            # 1024×1024 — emerald/cyan mark (mobile)
│   ├── mark-mono-white.png       # 1024×1024 — white mark, transparent
│   ├── mark-mono-black.png       # 1024×1024 — black mark, transparent
│   └── lockup-horizontal.png     # 2048×512 — mark + wordmark
├── desktop/
│   ├── mission-control.png       # 1600×1000 dark
│   ├── intelligence.png
│   ├── targets.png
│   ├── capital.png
│   ├── merlin.png
│   ├── agents.png
│   ├── cycles.png
│   ├── manuals.png
│   ├── reports.png
│   ├── direct-work.png
│   ├── daily-companion.png
│   ├── work-bank.png
│   ├── executive-dashboard.png
│   ├── voice.png
│   ├── calendar.png
│   ├── threat-intel.png
│   ├── notifications.png
│   └── settings.png
├── mobile/
│   ├── omega-home.png            # 1290×2796 — iPhone 15 Pro frame
│   ├── omega-opportunities.png
│   ├── omega-opportunity-detail.png
│   ├── omega-merlin.png
│   ├── omega-agents.png
│   ├── omega-settings.png
│   ├── omega-notification.png    # iOS lock screen
│   ├── omega-watch.png           # Apple Watch Ultra 49mm
│   └── omega-hero.png            # App Store hero (3 panels)
├── architecture/
│   ├── system.png                # 1600×900 — full system diagram
│   ├── mobile.png                # Mobile/OMEGA architecture
│   └── data-flow.png             # EventBus flow
└── social/
    └── og-image.png              # 1200×630
```

**Total: 37 AI-generated assets** (dark-first; OG 1200×630 derived from hero via `render_og`).

---

## 3. Generation Pipeline

> **Implemented (2026-08-10)**: deterministic pipeline [`scripts/brand/generate_github_assets.py`](../../scripts/brand/generate_github_assets.py)
> — PIL only, no GPU, no network, no API. Run `python scripts/brand/generate_github_assets.py` from the repo root;
> it regenerates all 37 assets in `docs/assets/github/`. The Midjourney workflow below remains as alternative
> art direction (organic look) if the vector look is ever replaced.

Complete prompt library: [`docs/design/AI_IMAGE_PROMPTS.md`](AI_IMAGE_PROMPTS.md)

### Recommended tool: **Midjourney v6** (`--style raw --q 2 --stylize 250`)

### Batch generation order (optimized for consistency)

| Batch | Assets | Shared style seed |
|-------|--------|-------------------|
| 1 | All 5 logos + hero | Mark geometry described once |
| 2 | Desktop surfaces × 18 | Same layout template |
| 3 | Mobile × 9 | iPhone 15 Pro frame |
| 4 | Architecture × 3 | Diagram conventions |
| 5 | OG + social | Hero reuse |

### Negative prompt (always)

```
neon, glow, particles, lens flare, bloom, grain, noise, gradient background,
colorful, rainbow, cartoon, illustration, sketch, watermark, text artifacts,
blurry, low quality, amateur, busy, cluttered, hologram, sci-fi, cyberpunk,
matrix, code rain, terminal aesthetic, hacker, dark web
```

---

## 4. README Integration

### 4.1 Logo (no SVG)

Replace the `<picture>` SVG block with a single PNG (dark is the brand default):

```html
<p align="center">
  <img src="docs/assets/github/logo/lockup-horizontal.png" alt="OWNEX" width="400"/>
</p>
```

### 4.2 Product surfaces (no real screenshots)

Each product section uses one AI image + endpoint links. **No `<picture>` dual-variant** — dark only, since the product is dark-first:

```html
<p align="center">
  <img src="docs/assets/github/desktop/mission-control.png" alt="Mission Control" width="100%"/>
</p>
```

### 4.3 OMEGA Mobile section

After the desktop surfaces, a full mobile section with the OMEGA images — already implemented in the README under `## OMEGA Mobile 📱`:

- 6 phone illustrations (home, opportunities, merlin, agents, notification, watch)
- Feature list (Today View, Opportunities, MERLIN Voice, Agent Fleet, Rich push, Watch Companion, Biometric, Offline-first)
- Link to `docs/development/OMEGA_MOBILE_SPEC.md`

---

## 5. Mobile App (OMEGA) Presentation Copy

### Tagline

> The pocket command center for your autonomous work system.

### Elevator pitch

> OMEGA is the mobile companion for OWNEX. Every morning it answers: *"What is the single highest-EV action I can take today?"* — with one-tap execution, voice-first MERLIN, agent fleet monitoring, and an Apple Watch companion.

### Feature list (README / App Store)

- 🎯 **Today View** — top pick, quick metrics, fleet status
- 💼 **Opportunities** — swipeable work bank, prepare/defer/dismiss
- 🗣️ **MERLIN Voice** — hold-to-talk, streaming TTS replies
- 🤖 **Agent Fleet** — status + control from your pocket
- 🔔 **Rich push** — prepare/dismiss actions, deep links
- ⌚ **Watch Companion** — execute from your wrist
- 🔐 **Biometric unlock** — FaceID/TouchID, SecureStore
- 📴 **Offline-first** — mutation queue, optimistic UI, background sync

### Visual identity

- Pure black `#05060A` background, Tesla-dark aesthetic
- Cyan `#00D5FF` primary actions, emerald `#00E39A` success, orange `#FF7A1A` decisions
- Space Grotesk headers / Inter body / JetBrains Mono metrics
- 8px grid, hairline separators, no background gradients

---

## 6. Repository Documents (the "written development")

| Doc | Path | Purpose |
|-----|------|---------|
| **Mobile spec** | `docs/development/OMEGA_MOBILE_SPEC.md` | Complete OMEGA development spec: architecture, screens, APIs, data models, build/deploy, testing, security, performance budgets |
| **AI prompts** | `docs/design/AI_IMAGE_PROMPTS.md` | Full AI image generation prompt library (37 assets) |
| **This guide** | `docs/design/GITHUB_REPOSITORY_GUIDE.md` | Asset architecture + README integration |
| **Asset registry** | `docs/design/ASSET_REGISTRY.md` | Registry of all repo assets |

---

## 7. Open Graph / Social

- **OG image**: `docs/assets/github/social/og-image.png` (1200×630)
- **Social preview**: GitHub uses the OG image automatically when it exists in the repo
- **Repo topics** (suggested):

  ```
  autonomous-agents  bug-bounty  fastapi  vue3  tauri  react-native
  expo  ai-agents  revenue-engine  mission-control  security-tools
  ```

---

## 8. Quality Checklist

- [ ] All 37 assets exist under `docs/assets/github/`
- [ ] No SVG references remain in README
- [ ] No broken `<picture>` blocks (dark-only images)
- [ ] OMEGA section present with 6+ mobile illustrations
- [ ] `OMEGA_MOBILE_SPEC.md` linked from README
- [ ] OG image correct size (1200×630)
- [ ] Hero image compresses < 500KB
- [ ] All images follow design tokens (no neon, no glow, black bg)

---

*Document Version: 1.0 | Last Updated: 2026-08-10 | Author: OWNEX Engineering*