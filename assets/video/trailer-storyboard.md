# OWNEX — Product Trailer (90s) — Storyboard

> Structure for a 90-second cinematic product trailer.
> Art direction: Space Black + Cyber Cyan, clean geometric precision, refined motion.
> All scenes render from the brand pipeline (`scripts/brand/`) — deterministic vector source.

**Spec:** 1080p (1920×1080) · 24 fps · H.264 + AAC · Safe margins: 5% all sides

---

## Scene Map

| # | Time | Scene | Asset | Audio |
|---|------|-------|-------|-------|
| 1 | 00:00–00:07 | **Signal Emerges** — The Signal mark forms from center: two diagonals cross with precise negative gap, subtle ring draws in, center node pulses | `assets/logos/ownex-mark.svg` | Deep sub hit, crystalline chime at node pulse |
| 2 | 00:07–00:18 | **System Initialize** — Boot sequence: clean checkmarks tick (VERIFYING CORE, AGENTS ONLINE, MEMORY SYNC, MISSION CONTROL READY) | `assets/concepts/boot-sequence.png` | Layered UI clicks, rising filter sweep |
| 3 | 00:18–00:36 | **ALPHA Desktop** — Mission Control pans slowly: KPI counters animate, agent statuses pulse green, opportunities flow | `assets/concepts/mission-control.png` | Minimal ambient pad, soft interface blips |
| 4 | 00:36–00:48 | **MERLIN Assistant** — Chat interface expands, voice rings emanate, brief card: "3 high-EV opportunities scored" | `assets/concepts/mission-control.png` (Next Best Action) | Calm voiceover, gentle chime |
| 5 | 00:48–00:60 | **Architecture Flow** — Six layers animate top-down: Core → Departments → Agents → Execution → Learning → Evolution | `assets/concepts/architecture.png` | Syncopated tech pulse, workflow ticks |
| 6 | 00:60–00:72 | **OMEGA Mobile** — Phone frame slides in: approval notification, MERLIN reply, system health card | `assets/concepts/mobile-omega.png` | Notification sound, haptic-like ticks |
| 7 | 00:72–00:80 | **Wear OS** — Watch close-up: swipe to approve, status flips CONNECTED, pulse animation | `assets/concepts/mobile-omega.png` (watch) | Wrist-haptic feel, confirm blip |
| 8 | 00:80–00:90 | **Ecosystem** — Product overview: six satellites orbit core, lines draw, lockup + tagline `AUTONOMOUS PERSONAL OPERATING SYSTEM` | `assets/concepts/product-overview.png`, `assets/logos/ownex-lockup.png` | Full mix swell, final impact + tail |

**Total:** 90 seconds · 8 scenes

---

## Production Notes (open source toolchain)

1. **Stills** — already rendered at 2x: `assets/concepts/*.png`, `assets/banners/hero-banner.png`.
2. **Motion** — Ken Burns (slow pans/zooms) + fade-through-black transitions; SVG source files
   allow true vector animation in any SVG motion tool (Lottie-compatible export from
   `assets/logos/*.svg`, `assets/concepts/*.svg`).
3. **Compositing** — free tools: DaVinci Resolve / Kdenlive; or programmatic with ffmpeg
   zoompan + xfade.
4. **Audio** — synthesize with ffmpeg/sox or free pads (ccMixter / freesound CC0).
5. **Voiceover** — Piper TTS (local, integrated in OWNEX) for MERLIN line.
6. **Color** — final grade: lift blacks to #05060A, cyan highlights, 0.45 gamma curve.

## Acceptance

- [ ] Scene 1 mark assembles on black within 7s
- [ ] All captions use JetBrains Mono, letter-spaced
- [ ] Single art direction across scenes (same grid, same palette)
- [ ] 90s ± 2s, 1080p, < 30MB