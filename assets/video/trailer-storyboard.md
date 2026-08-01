# OWNEX — Product Trailer (90s) — Storyboard

> Structure for a 90-second cinematic product trailer.
> Art direction: Space Black + Cyber Cyan, precise geometry, no humanoids, no AI clichés.
> All scenes render from the brand pipeline (`scripts/brand/`) — no stock footage.

**Spec:** 1080p (1920×1080) · 24 fps · H.264 + AAC · Safe margins: 5% all sides

---

## Scene Map

| # | Time | Scene | Asset | Audio |
|---|------|-------|-------|-------|
| 1 | 00:00–00:07 | **Awakening** — Aperture Nexus mark assembles (ring segments draw in, rays converge, node ignites) on space black. Wordmark `OWNEX` types in below with mono caption. | `assets/logos/ownex-mark.svg` | Deep sub-bass pulse, single hit at node ignition |
| 2 | 00:07–00:18 | **System Boot** — Boot sequence concept: verification list ticks off (`VERIFYING SYSTEM`, `INITIALIZING AGENTS`, `MISSION CONTROL ONLINE`) | `assets/concepts/boot-sequence.png` | Layered UI ticks, rising filter sweep |
| 3 | 00:18–00:36 | **ALPHA Desktop** — Mission Control concept pans slowly; KPI counters tick, agent statuses pulse | `assets/concepts/mission-control.png` | Minimal ambient pad, soft interface blips |
| 4 | 00:36–00:48 | **MERLIN** — Assistant concept; voice rings expand, brief card fades in ("3 opportunities scored high EV") | `assets/concepts/mission-control.png` (Next Best Action panel) | Calm voiceover intro, gentle chime |
| 5 | 00:48–00:60 | **Agents at work** — Architecture concept: layers flow top to bottom; execution arrows pulse | `assets/concepts/architecture.png` | Syncopated tech pulse, workflow ticks |
| 6 | 00:60–00:72 | **OMEGA Android** — Phone mockup slides in with approval notification; MERLIN card replies | `assets/concepts/mobile-omega.png` | Notification sound, haptic-like ticks |
| 7 | 00:72–00:80 | **Wear OS** — Watch close-up: approval swipe completes, status flips to CONNECTED | `assets/concepts/mobile-omega.png` (watch) | Wrist-haptic feel, confirm blip |
| 8 | 00:80–00:90 | **Ecosystem** — Product overview: satellites light one by one, lines draw to core; logo lockup + tagline `AUTONOMOUS PERSONAL OPERATING SYSTEM`; end card | `assets/concepts/product-overview.png`, `assets/logos/ownex-lockup.png` | Full mix swell, final impact + tail |

**Total:** 90 seconds · 8 scenes

---

## Production Notes (open source toolchain)

1. **Stills** — already rendered at 2x: `assets/concepts/*.png`, `assets/banners/hero-banner.png`.
2. **Motion** — Ken Burns (slow pans/zooms) + fade-through-black transitions; SVG source files
   allow true vector animation in any SVG motion tool (Lottie-compatible export from
   `assets/logos/*.svg`, `assets/concepts/*.svg`).
3. **Compositing** — free tools: DaVinci Resolve / Kdenlive; or programmatic with ffmpeg
   zoompan + xfade (see `assets/video_generation/` for the ffmpeg pipeline).
4. **Audio** — synthesize with ffmpeg/sox or free pads (ccMixter / freesound CC0).
5. **Voiceover** — Piper TTS (local, already integrated in OWNEX) for the MERLIN line.
6. **Color** — final grade: lift blacks to #05060A, cyan highlights, 0.45 gamma curve.

## Acceptance

- [ ] Scene 1 mark assembles on black within 7s
- [ ] All captions use JetBrains Mono, letter-spaced
- [ ] Single art direction across scenes (same grid, same palette)
- [ ] 90s ± 2s, 1080p, < 30MB
