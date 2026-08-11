# OWNEX AI Image Generation Prompts — GitHub Repository Assets

## Design Language Reference

**Color Palette (from design-tokens.json):**
- `space_black` #05060A — Deep space background
- `cyber_cyan` #00D5FF — Intelligence accent (electric blue)
- `deep_blue` #1E40FF — Primary intelligence
- `emerald` #00E39A — Progress/success
- `decision` #FF7A1A — Decision/action orange
- `surface` #111318 — Card backgrounds
- `stroke` #2A2E37 — Borders
- `white` #FFFFFF — Primary text
- `muted` #8B8D98 — Secondary text

**Typography:**
- Display: Space Grotesk (geometric, technical)
- Body: Inter (clean, readable)
- Mono: JetBrains Mono (code/terminal)

**Visual Style:**
- Tesla dark aesthetic: pure black backgrounds
- No gradients on backgrounds — solid #05060A
- Subtle glows only on accent elements
- Hairline borders (rgba(255,255,255,0.06))
- Sharp geometric precision
- No noise, no grain, no "neon" effects
- Professional, mission-control aesthetic

---

## Asset Generation Prompts

### 1. HERO BANNER (2400×900)
```
OWNEX Autonomous Work Operating System hero banner, 2400x900, pure black background #05060A, 
centered "The Aperture Nexus" mark: octagonal ring with intersecting diagonal bars forming an X, 
center square node, cyan-to-blue gradient #00D5FF→#1E40FF, subtle outer ring, 
wordmark "OWNEX" in Space Grotesk bold tracking-wide below, 
tagline "Autonomous Work Operating System" in Inter light, 
no glow effects, no particles, professional mission control aesthetic, 
high resolution, commercial product photography quality
```

### 2. LOGO VARIANTS (512×512 each)
```
A. OWNEX Mark - Alpha (Desktop): Octagonal ring with intersecting diagonal bars forming X, 
center square node, cyan-to-blue gradient #00D5FF→#1E40FF, subtle outer ring stroke, 
transparent background, vector-perfect geometry, 512x512

B. OWNEX Mark - Omega (Mobile): Same geometry, emerald-to-cyan gradient #00E39A→#00D5FF, 
transparent background, 512x512

C. OWNEX Mark - Mono White: White #FFFFFF on transparent, bold variant, 512x512

D. OWNEX Mark - Mono Black: Space black #05060A on transparent, bold variant, 512x512

E. OWNEX Lockup - Horizontal: Mark + wordmark "OWNEX" in Space Grotesk 700, 
proportional spacing, cyan gradient, transparent background, 1024x512
```

### 3. PRODUCT SCREENSHOTS (Dark/Light pairs, 1600×1000@2x)

**Mission Control:**
```
Dark: Mission Control dashboard, pure black #05060A background, 
left sidebar navigation with icons, center: agent fleet status cards with 
cyan #00D5FF accent borders, right: opportunity radar with ranked cards, 
top bar: system health score with emerald #00E39A indicator, 
bottom: activity timeline with hairline dividers, 
Space Grotesk headers, Inter body, JetBrains Mono for metrics, 
professional SaaS dashboard quality, 1600x1000

Light: Same layout, #FFFFFF background, #F6F8FB surfaces, 
#1E40FF primary accent, #FF7A1A decision accent, 
dark text #05060A, same visual hierarchy
```

**Intelligence (Findings/Hypotheses):**
```
Dark: Intelligence panel, black background, 
left: hypothesis queue with confidence bars (cyan→blue gradient), 
center: evidence graph visualization nodes connected by hairlines, 
right: differential analysis panel with emerald success / decision orange failure, 
bottom: contradiction engine output, technical precision aesthetic
```

**Targets (Attack Surface):**
```
Dark: Target intelligence view, black background, 
top: target selector with domain badges, 
center: attack surface map — endpoints as nodes, vulnerability types as colored rings 
(cyan=IDOR, blue=SSRF, emerald=XSS, orange=Auth Bypass), 
right: scan queue with progress rings, bottom: prioritized findings table
```

**Capital (Revenue Dashboard):**
```
Dark: Financial intelligence, black background, 
top row: 4 KPI cards — USD/hr (cyan), Monthly (emerald), Pending (orange), Platforms (blue), 
center: platform performance table with sparklines, 
right: payout timeline Gantt chart, bottom: ROI waterfall chart
```

**MERLIN (AI Assistant):**
```
Dark: MERLIN chat interface, black background, 
left: collapsible sidebar with memory/notes/quick actions, 
center: conversation thread with user (emerald) / MERLIN (cyan) messages, 
input bar at bottom with voice/mic/icon, 
top: status "SYSTEM ONLINE" with pulsing emerald indicator, 
retro-office aesthetic: monospace font, subtle scanlines
```

**Agents (Fleet View):**
```
Dark: Agent fleet grid, black background, 
12 agent cards in 3×4 grid: Security, Coding, QA, Debug, Documentation, 
Research, Product, Revenue, Automation, Infrastructure, Evolution, Orchestrator, 
each: icon, status ring (idle=gray, working=cyan pulse, complete=emerald, error=orange), 
current task, progress bar, Space Grotesk labels
```

**Reports (Report Center):**
```
Dark: Report pipeline, black background, 
left: report queue with stages (draft→evidence→review→submitted→paid), 
center: selected report preview with evidence bundles, 
right: platform submission status (H1, BC, Intigriti, YesWeHack, Synack), 
bottom: acceptance probability gauge with cyan needle
```

**Settings (Configuration):**
```
Dark: Settings panel, black background, 
tabs: AI Providers, Credentials, Scheduler, Integrations, Appearance, 
each tab: card-based form with toggles, inputs, selectors, 
cyan focus states, emerald success toasts, orange warning states
```

---

## Mobile App Illustrations (OMEGA Companion)

### 1. OMEGA Mobile - Home/Dashboard
```
OWNEX OMEGA mobile app home screen, iPhone 15 Pro frame, 
pure black #05060A background, 
top: system health pill — "● ONLINE" emerald pulsing, 
center: "TODAY" card — large metric "$2,400 potential" cyan, 
"3 high-EV opportunities" emerald, "83% automatable" blue, 
primary action button: "Execute Top Pick" full-width cyan gradient, 
bottom nav: Home (active), Opportunities, MERLIN, Agents, Settings, 
Space Grotesk headers, Inter body, hairline separators, 
native iOS feel, premium app store quality
```

### 2. OMEGA Mobile - Opportunities List
```
OWNEX OMEGA opportunities list, iPhone frame, black background, 
search bar at top with cyan focus ring, 
list of opportunity cards: each — platform badge (H1/BC/Intigriti), 
title, reward amount cyan, effort hours, EV score, 
swipe actions: "Prepare" (cyan), "Defer" (gray), "Dismiss" (orange), 
pull-to-refresh with emerald spinner, native iOS list behavior
```

### 3. OMEGA Mobile - MERLIN Chat
```
OWNEX OMEGA MERLIN chat, iPhone frame, black background, 
top bar: "MERLIN" with pulsing emerald status dot, 
messages: user bubbles right (emerald #00E39A), MERLIN bubbles left (cyan #00D5FF), 
message timestamps muted, bottom: voice input button (hold to talk), 
text input with send, mic permission indicator, native keyboard feel
```

### 4. OMEGA Mobile - Agent Fleet Status
```
OWNEX OMEGA agent fleet, iPhone frame, black background, 
horizontal scrolling agent cards: 12 agents, 
each card: icon, name, status ring with pulse animation, 
current task one-liner, progress bar, 
tap to expand: full conversation, decisions, actions, 
smooth 60fps scroll, haptic feedback on tap
```

### 5. OMEGA Mobile - Push Notification
```
OWNEX OMEGA push notification on iOS lock screen, 
black background, OWNEX mark small top-left, 
title: "High-EV Opportunity Ready", body: "OpenAI bug bounty — $1,200 — 2.3h prep", 
actions: [Prepare] [Dismiss], emerald accent on primary action, 
native iOS notification style, clean typography
```

### 6. OMEGA Mobile - Apple Watch Companion
```
OWNEX OMEGA Apple Watch Ultra face, 49mm, 
black always-on display, 
complication slots: top-left: system health (emerald ring = online), 
top-right: next action count (cyan number), 
center: "EXECUTE TOP PICK" large cyan button (tap → haptic → confirm), 
bottom: MERLIN micro-status "ANALYZING" pulsing, 
digital crown scroll: opportunities / agents / notifications, 
always-on optimized, high contrast, wearable-grade legibility
```

---

## Architecture Diagrams

### 1. System Architecture (Mermaid-ready, render as diagram)
```
Full system architecture diagram, dark theme, 
boxes: Presentation (Mission Control, OMEGA Mobile, Tauri Desktop, MERLIN), 
Core Platform (EventBus, Scheduler, Unified Memory, Decision Journal, Identity Vault, Health Center), 
Work Cycles (Security, Forge, Pulse, Vault, Atlas, QA, Direct Work), 
Engines (Direct Work, Revenue, Opportunity, Validation, Evolution, OAR AI, Career), 
AI Providers (OAR Smart Router → Ollama, FCC Proxy, OpenRouter), 
connections: clean arrows, cyan for data flow, emerald for control, orange for decisions, 
Space Grotesk labels, pure black background, professional architecture diagram style
```

### 2. Mobile Architecture (OMEGA)
```
OMEGA mobile architecture, dark theme, 
left: Capacitor Android app (WebView + native plugins), 
center: Expo/React Native OMEGA (iOS/Android), 
right: Wear OS companion (Compose), 
connections: WebSocket to backend :8000, 
native plugins: mic, notifications, biometrics, secure storage, 
labels: "Native Mic", "Push Notifications", "Secure Enclave", "Health Sync", 
cyan/emerald/orange accent arrows, professional mobile architecture
```

---

## Social / Open Graph (1200×630)

```
OWNEX OG image, 1200x630, pure black #05060A, 
centered Aperture Nexus mark large (200px), 
below: "OWNEX" Space Grotesk 700 tracking-wide cyan gradient, 
tagline: "Autonomous Work Operating System" Inter light, 
bottom: 3 capability badges — "Bug Bounty" "Dev Bounty" "AI Work" with hairline borders, 
subtle vignette, no noise, high contrast for social feeds
```

---

## Usage Instructions

### For AI Image Generators (Midjourney, DALL-E 3, Stable Diffusion)

**Base negative prompt (always include):**
```
neon, glow, particles, lens flare, bloom, grain, noise, gradient background, 
colorful, rainbow, cartoon, illustration, sketch, watermark, text artifacts, 
blurry, low quality, amateur, busy, cluttered, hologram, sci-fi, cyberpunk, 
matrix, code rain, terminal aesthetic, hacker, dark web
```

**Style keywords (always include):**
```
professional product photography, commercial SaaS dashboard, 
mission control center, Tesla design language, Apple design language, 
clean geometric precision, high contrast, sharp focus, 8k resolution, 
commercial quality, product marketing, hero shot
```

**Aspect ratios:**
- Hero banner: `--ar 8:3`
- Logo: `--ar 1:1`
- Screenshots: `--ar 16:10`
- Mobile: `--ar 9:19.5`
- OG: `--ar 1.91:1`
- Architecture: `--ar 16:9`

### Recommended Settings

**Midjourney v6:**
```
--v 6.0 --style raw --q 2 --stylize 250 --ar [ratio]
```

**DALL-E 3:**
```
hd quality, natural style, 1792x1024 (landscape) or 1024x1792 (portrait)
```

**Stable Diffusion XL:**
```
--steps 30 --cfg 7 --sampler dpmpp_2m --refiner
```

---

## File Naming Convention

```
docs/assets/github/
├── hero/
│   ├── hero-banner-dark.png
│   ├── hero-banner-light.png
│   └── hero-banner-og.png
├── logo/
│   ├── mark-alpha.png
│   ├── mark-omega.png
│   ├── mark-mono-white.png
│   ├── mark-mono-black.png
│   ├── lockup-horizontal.png
│   └── favicon-32.png
├── screenshots/
│   ├── mission-control-dark.png
│   ├── mission-control-light.png
│   ├── intelligence-dark.png
│   ├── intelligence-light.png
│   ├── targets-dark.png
│   ├── targets-light.png
│   ├── capital-dark.png
│   ├── capital-light.png
│   ├── merlin-dark.png
│   ├── merlin-light.png
│   ├── agents-dark.png
│   ├── agents-light.png
│   ├── reports-dark.png
│   ├── reports-light.png
│   ├── settings-dark.png
│   └── settings-light.png
├── mobile/
│   ├── omega-home-dark.png
│   ├── omega-home-light.png
│   ├── omega-opportunities.png
│   ├── omega-merlin.png
│   ├── omega-agents.png
│   ├── omega-notification.png
│   └── omega-watch.png
├── architecture/
│   ├── system-architecture.png
│   ├── mobile-architecture.png
│   └── data-flow.png
└── social/
    └── og-image.png
```

---

## Generation Checklist

- [ ] Hero banner (dark + light + OG)
- [ ] 5 logo variants
- [ ] 8 product screenshots × 2 (dark/light) = 16
- [ ] 7 mobile illustrations
- [ ] 2 architecture diagrams
- [ ] 1 OG image
- **Total: ~35 high-quality assets**

---

## Brand Consistency Rules

1. **Never** use neon colors (#00FFFF, #FF00FF, #FFFF00)
2. **Never** use glow/bloom on backgrounds
3. **Never** use gradient backgrounds — solid #05060A or #FFFFFF only
4. **Only** accent gradients on the mark itself
5. **Always** hairline borders (1px, rgba(255,255,255,0.06-0.12))
6. **Always** Space Grotesk for headers, Inter for body
7. **Always** JetBrains Mono for code/metrics
8. **Always** 8px spacing grid
9. **Always** pure black #05060A for dark mode backgrounds
10. **Always** professional, calm, mission-control aesthetic