# OWNEX Design System — MASTER

> Single source of truth for all visual, interaction, and UX decisions across OWNEX.

## Philosophy

> **The complexity lives inside the system, never in the user's head.**

OWNEX must feel like:
- A quiet, fast, precise, minimal, intelligent system
- NOT an ERP, crypto dashboard, project manager, or terminal

Reference: Apple + Linear + Raycast + Stripe — but OWNEX identity.

## Color System

### Core Palette (TESLA — Pure Black + White + Neutral Grays)

| Token | Value | Usage |
|-------|-------|-------|
| `--color-background` | `#000000` | Page background |
| `--color-surface` | `#0a0a0a` | Panels, cards |
| `--color-surface-hover` | `#141414` | Hover states |
| `--color-border` | `#1f1f1f` | Default borders |
| `--color-border-light` | `#2e2e2e` | Elevated borders |
| `--color-foreground` | `#f5f5f5` | Primary text |
| `--color-muted-foreground` | `#8a8a8a` | Secondary text |
| `--color-muted` | `#4a4a4a` | Disabled, hints |

### Identity Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | `#ffffff` | Actions, selections |
| `--color-accent` | `#00d5ff` | Information, links |
| `--color-success` | `#16a34a` | Active, success |
| `--color-warning` | `#d97706` | Attention |
| `--color-destructive` | `#00d5ff` | Error, risk (blue, NOT red) |
| `--color-gold` | `#b45309` | Rewards, premium |

### Rules
- NO red in UI (directiva owner 2026-08-25)
- NO arbitrary RGB colors
- NO color gradients for decoration
- NO glows, neon, or AI-purple clichés
- Desaturated platform colors only

## Typography

### Font Stacks

| Token | Fonts | Usage |
|-------|-------|-------|
| `--font-sans` | Inter, DM Sans, system | Body, UI |
| `--font-mono` | JetBrains Mono, Fira Code | Code, metrics, money |
| `--font-display` | Space Grotesk, Orbitron | Hero KPIs |

### Type Scale

| Token | Size | Usage |
|-------|------|-------|
| `--text-display` | 2.5rem | Hero KPIs, NEXT ACTION amount |
| `--text-heading` | 1.25rem | Page/section headers |
| `--text-body` | 0.875rem | Default UI text |
| `--text-label` | 0.75rem | Uppercase labels, badges |
| `--text-caption` | 0.6875rem | Meta, timestamps |

### Numeric Display
- Use `font-mono` + `tabular-nums` for all money/metrics
- Class: `.money` applies mono + tabular figures

## Spacing (4px Grid)

| Token | Value |
|-------|-------|
| `--spacing-1` | 4px |
| `--spacing-2` | 8px |
| `--spacing-3` | 12px |
| `--spacing-4` | 16px |
| `--spacing-5` | 24px |
| `--spacing-6` | 32px |
| `--spacing-8` | 48px |
| `--spacing-10` | 64px |

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 6px | Badges, small elements |
| `--radius-md` | 10px | Cards, inputs |
| `--radius-lg` | 16px | Modals, panels |
| `--radius-xl` | 24px | Large containers |
| `--radius-full` | 9999px | Pills, dots |

## Shadows

| Token | Usage |
|-------|-------|
| `--shadow-sm` | Subtle elevation |
| `--shadow-md` | Cards, dropdowns |
| `--shadow-lg` | Modals, overlays |
| `--shadow-glow` | Focus, selection |

## Z-Index Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--z-status-bar` | 50 | Top bar |
| `--z-sidebar` | 40 | Side navigation |
| `--z-overlay` | 60 | Backdrops |
| `--z-modal` | 70 | Dialogs |
| `--z-toast` | 80 | Notifications |
| `--z-command-palette` | 100 | Cmd+K |

## Motion

| Token | Duration | Usage |
|-------|----------|-------|
| `--transition-fast` | 120ms | Micro-interactions |
| `--transition-base` | 200ms | Standard transitions |
| `--transition-slow` | 350ms | Page transitions |

- Respect `prefers-reduced-motion`
- No decorative animations
- Use for: state changes, loading, feedback, navigation

## Components

### Base Components (from ShadCN Vue)
- Button, Input, Select, Dialog, Sheet, Card, Badge, Tabs, Tooltip, Table

### OWNEX Components
- `OneActionCard` — Next Best Action display
- `PrimaryModeSelector` — LITE/FULL/CAPITAL switcher
- `NotificationCenter` — In-app notification center
- `CommandPalette` — Cmd+K quick actions
- `ModeIndicator` — Current mode badge

## Layout Dimensions

| Token | Value | Usage |
|-------|-------|-------|
| `--sidebar-width` | 280px | Expanded sidebar |
| `--sidebar-collapsed-width` | 64px | Collapsed sidebar |
| `--status-bar-height` | 40px | Top status bar |

## Responsive Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Mobile | 375px | Bottom nav, single column |
| Tablet | 768px | Collapsed sidebar |
| Desktop | 1024px | Full sidebar |
| Wide | 1440px+ | Multi-panel |

## Empty States
- NEVER show just "No data"
- Show context + next action
- Example: "No high-value opportunities yet. OWNEX is scanning."

## Error States
- Explain: WHAT happened, WHY, WHAT OWNEX is doing, WHAT the user needs to do
- Never show raw technical errors as sole explanation

## Loading States
- Use skeleton pulses
- Avoid eternal spinners
- Show progress when available

## Accessibility
- Minimum contrast: 4.5:1 for text
- Focus states on all interactive elements
- Keyboard navigation
- Touch targets: minimum 44x44px
- No color-only information conveyance

## Three Modes

### LITE — Earn More
- Minimal UI, focused on Next Best Action
- Shows: capital, income, progress, best opportunity, next action

### FULL — Operate Everything
- Complete system view
- Shows: all sections, agents, workflows, health

### CAPITAL — Keep & Compound
- Financial focus
- Shows: net worth, savings, investments, $1M progress

## Page Overrides

Place page-specific design rules in `design-system/pages/<page>.md`.
Only create overrides when MASTER.md rules are insufficient.
