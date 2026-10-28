# FRONTEND MAP — OWNEX (2026-09-30)

## Structure Overview

```
frontend/
├── src/
│   ├── main.ts                    # Entry point
│   ├── App.vue                    # Root component
│   ├── router/
│   │   └── index.ts              # 97 routes, 0 collisions, 0 redirect chains
│   ├── stores/ (9 pinia)
│   ├── composables/ (21 .ts)
│   ├── components/ (128 .vue)
│   ├── pages/ (64 .vue)
│   ├── services/ (6 .ts)
│   ├── composables/ (21 .ts)
│   ├── lib/
│   │   ├── api.ts (1337 LOC, 70 importers)
│   │   ├── backend.ts (333 LOC, ROOT_MOUNTED_PREFIXES)
│   │   ├── offline.ts (355 LOC, 0 importers - DEAD)
│   │   └── utils.ts (6 LOC, cn() helper)
│   ├── styles/
│   │   ├── design/tokens.css (265 lines, 127 CSS vars)
│   │   ├── styles/glass.css, motion.css, responsive.css
│   │   └── styles/tesla-jarvis-theme.css
│   └── tests/
├── dist/                          # Production build
├── public/                        # Static assets
├── spa-server.cjs                 # Zero-dep static server (fixed)
├── playwright.config.ts           # 28 E2E tests
├── vitest.config.ts               # 17 test files, 191 tests
├── package.json
├── vite.config.ts                 # Proxy to 27 root-mounted prefixes
└── package.json                   # v7.7.7
```

---

## Route Map (97 routes, 0 duplicates, 0 redirect chains)

### Route Categories

| Category | Routes | Example |
|----------|--------|---------|
| Setup/Auth | 6 | `/setup/personalization`, `/activation`, `/verify` |
| Command Center | 5 | `/`, `/welcome`, `/dashboard`, `/classic`, `/home` |
| Intelligence | 7 | `/intelligence`, `/intelligence/evidence`, `/intelligence/investigations` |
| Targets | 7 | `/targets`, `/targets/list`, `/targets/discovery`, `/targets/attack-surface`, `/targets/prioritization`, `/targets/:id`, `/targets/endpoints/:id` |
| Reports | 6 | `/reports`, `/reports/:id`, `/reports/verification` |
| Capital/Security | 4 | `/capital`, `/capital/progressive-scaling`, `/security`, `/security/executive` |
| Operations | 27 | `/operations`, `/operations/health`, `/operations/settings`, `/operations/work-queue`, `/public-work`, `/operations/first-money`, `/mission`, `/operations/platforms/:platform?`, `/operations/ledger`, `/operations/ecommerce`, `/operations/clients`, `/operations/content`, `/operations/local-jobs`, `/operations/work-room/:id`, `/operations/worker`, `/setup/checklist`, `/operations/agenda`, `/operations/pipelines`, `/operations/pipelines/:id`, `/operations/scheduler`, `/operations/tools`, `/operations/applications`, `/operations/workflows`, `/operations/replay`, `/operations/version-backup`, `/operations/self-healer`, `/operations/logs` |
| Integrations | 9 | `/integrations`, `/integrations/connections`, `/integrations/wallets`, `/integrations/accounts`, `/integrations/platforms`, `/integrations/sync`, `/integrations/outlook`, `/integrations/identity` |
| Copilot/Help | 8 | `/copilot`, `/copilot/computer-use`, `/copilot/notifications`, `/copilot/alerts`, `/help`, `/copilot/assistant`, `/copilot/memory`, `/copilot/learning`, `/copilot/recommendations` |
| Apps/Satellites | 8 | `/atlas/`, `/atlas/settings`, `/odyssey/`, `/odyssey/settings`, `/aegis/`, `/aegis/settings`, `/trading` |
| Special | 7 | `/terminal`, `/baby-mode`, `/faqs`, `/profile-kit`, `/knowledge`, `/knowledge/graph`, `/quick-capture` |

**Redirects (21)**: All resolve to component routes, 0 chains.

**Auth Guard**: In `main.ts:48-67` — `beforeEach` checks `meta.public`, then `auth.isAuthenticated`, then `auth.autoLogin()` (device-id based). No login page — fails silently.

---

## Component Inventory

| Category | Total | Active | Dead | Duplicated |
|---------|-------|--------|------|------------|
| **Total .vue** | 128 | 87 | 41 (32%) | 6 pairs |
| Pages | 64 | 64 | 0 | 0 |
| Components | 128 | 87 | 41 | 6 pairs |
| Layout | 9 | 9 | 0 | 0 |

### Dead Components (41, zero importers)

| Component | Path |
|-----------|------|
| `AgentFleet` | `components/agents/AgentFleet.vue` |
| `PixelAvatar` | `components/assistant/PixelAvatar.vue` |
| `TodayBriefing` | `components/autopilot/TodayBriefing.vue` |
| `AutomationStrip` | `components/daily/AutomationStrip.vue` |
| `ReportPipeline` | `components/dashboard/ReportPipeline.vue` |
| `RevenueSnapshot` | `components/dashboard/RevenueSnapshot.vue` |
| `ThroughputCore` | `components/dashboard/ThroughputCore.vue` |
| `WorkCyclesGrid` | `components/dashboard/WorkCyclesGrid.vue` |
| `FirstDayGuide` | `components/guided-mode/FirstDayGuide.vue` |
| `IncomeGuidanceAssistant` | `components/guided-mode/IncomeGuidanceAssistant.vue` |
| `ModeSelector` | `components/guided-mode/ModeSelector.vue` |
| `KnowledgeFeed` | `components/knowledge/KnowledgeFeed.vue` |
| `Breadcrumbs` | `components/layout/Breadcrumbs.vue` |
| `ModernNavbar` | `components/layout/ModernNavbar.vue` |
| `StatusBar` (layout) | `components/layout/StatusBar.vue` |
| `WorkspaceTabs` | `components/layout/WorkspaceTabs.vue` |
| `NotificationCenter` | `components/notifications/NotificationCenter.vue` |
| `ApprovalBadge` | `components/ui/ApprovalBadge.vue` |
| `CardDescription` | `components/ui/CardDescription.vue` |
| `CardFooter` | `components/ui/CardFooter.vue` |
| `CopyHelper` | `components/ui/CopyHelper.vue` |
| `StatusBar` (ui) | `components/ui/StatusBar.vue` |
| `Timeline` | `components/ui/Timeline.vue` |
| `WidgetWrapper` | `components/widgets/WidgetWrapper.vue` |
| 10 `WidgetWrapper` children | `components/widgets/widgets/*.vue` |
| `WorkStateBadge` | `components/work/WorkStateBadge.vue` |
| 6 `TradingLab*` | `components/trading/TradingLab*.vue` (behind dead barrel) |
| `MissionControlView` | `mission-control/MissionControlView.vue` |
| `GoodMorning` | `mission-control/components/GoodMorning.vue` |
| `PrepareButton` | `mission-control/components/PrepareButton.vue` |
| `ReadinessMeter` | `mission-control/components/ReadinessMeter.vue` |
| `ServiceGrid` | `mission-control/components/ServiceGrid.vue` |
| `AnimatedCounter` | `shared/components/AnimatedCounter.vue` |
| `DepthLayer` | `shared/components/DepthLayer.vue` |
| `StatusDot` (shared) | `shared/components/StatusDot.vue` |
| `OrionHome` | `shell/OrionHome.vue` |
| `OrionSidebar` | `shell/OrionSidebar.vue` |
| `StartupGate` | `startup/StartupGate.vue` |
| `LogoReveal` | `startup/components/LogoReveal.vue` |
| `ParticleField` | `startup/components/ParticleField.vue` |
| `TransitionOverlay` | `startup/components/TransitionOverlay.vue` |
| `usePreloadData` | `startup/composables/usePreloadData.ts` |
| `useStartupSequence` | `startup/composables/useStartupSequence.ts` |

### Broken Components (won't compile)

| File | Issue |
|------|-------|
| `components/ui/index.ts` | Exports `OwnexInput`, `OwnexKPI` — files don't exist |
| `components/mobile-companion/index.ts` | Starts with Python `"""` — invalid TS |

---

## State Management (9 Pinia Stores)

| Store | File | Consumers | Status |
|-------|------|-----------|--------|
| `auth` | `stores/auth.ts` | 3 (`main.ts`, `App.vue`, `CommandPalette`) | ACTIVE |
| `discovery` | `stores/discovery.ts` | 1 (`Discovery.vue`) | ACTIVE |
| `findings` | `stores/findings.ts` | 0 (only tests) | **DEAD** |
| `hunt` | `stores/hunt.ts` | 3 (`AppSidebar`, `CommandPalette`, `IncomeHome`) | ACTIVE |
| `notifications` | `stores/notifications.ts` | 10 | ACTIVE |
| `report` | `stores/report.ts` | 0 (only tests) | **DEAD** |
| `settings` | `stores/settings.ts` | 5 | ACTIVE |
| `ui` | `stores/ui.ts` | 6 | ACTIVE |
| `accessibility` | `stores/accessibility.ts` | 2 | ACTIVE |

---

## Composables (21 active + 3 test)

| Status | Count | Files |
|--------|-------|-------|
| ACTIVE | 12 | `useAssistant`, `useContextMenu`, `useGlobalShortcuts`, `useI18n`, `useOwnexState`, `useOwnVoice`, `usePrimaryMode`, `useThemeEngine`, `useToast`, `useGlobalShortcuts`, `useGuidedMode` |
| DEAD | 9 | `useAudio`, `useBountyStream`, `useCompanion`, `useCopyHelper`, `useFirstDayGuide`, `useGlobalHotkeys`, `useMicroInteractions`, `useMotion`, `useMultiSelect` |
| DEAD (transitive) | 2 | `useGuidedMode` (consumed by dead `FirstDayGuide`, `ModeSelector`) |

### Shared Composables (5, all dead)

| Composable | Reason |
|------------|--------|
| `useAnimatedCounter` | 0 importers |
| `useInViewport` | 0 importers |
| `useReducedMotion` | 4 importers (all dead) |
| `useSequentialReveal` | 0 importers |
| `useSpringAnimation` | 1 importer (dead) |

---

## Services & Lib

| File | Lines | Importers | Status |
|------|-------|-----------|--------|
| `services/ownexData.ts` | 3,104 | 29 | ACTIVE (core data layer) |
| `services/ownexAi.ts` | 297 | 1 | ACTIVE |
| `services/chatSemantics.ts` | 39 | 1 | ACTIVE |
| `services/knowledge.ts` | 242 | 1 | ACTIVE |
| `services/controlPanel.ts` | 1,530 | 0 | **DEAD** |
| `services/moneyprinter.ts` | 139 | 0 | **DEAD** |
| `lib/api.ts` | 1,337 | 70 | ACTIVE (core HTTP client) |
| `lib/backend.ts` | 333 | 6 | ACTIVE (URL resolution, WS) |
| `lib/offline.ts` | 355 | 0 | **DEAD** |
| `lib/utils.ts` | 6 | 19 | ACTIVE (`cn()` helper) |

### ownexData.ts (Core Data Layer)
- 3,104 lines
- 149 exported interfaces/types
- 144 exported functions (90 `fetch*`, 54 others)
- 29 importers (7 dead)

---

## Design System

### CSS Tokens (`frontend/src/design/tokens.css`)
- 265 lines, 127 unique CSS custom properties
- **0 raw hex in .vue/.ts** (discipline enforced)
- 41 raw hex in .css files (tokens.css: 25, accessibility.css: 8, tesla-jarvis-theme.css: 8)
- **Violations**: 58 Tailwind `red-*` in 10 files (violates "cero rojo" rule)
- **Undefined CSS vars**: 43 distinct (e.g., `--ownex-bg-elevated` used 18x, undefined)
- `style.css:27` self-referential: `--color-border: var(--color-border)`

### Component State Coverage

| Component | Loading | Empty | Error | Offline | Notes |
|-----------|---------|-------|-------|---------|-------|
| `IncomeHome` | ✅ | ❌ | ⚠️ (shared, correct) | ❌ | Uses `shared/ErrorState` correctly |
| `Mission` | ⚠️ | ⚠️ | 🔴 (wrong props) | ❌ | `LoadingState message=` wrong, `ErrorState` wrong props |
| `Capital` | 🔴 | ⚠️ | 🔴 | ❌ | `Skeleton` not imported, `ErrorState` wrong props |
| `FirstMoney` | ⚠️ | ⚠️ | 🔴 | ❌ | |
| `Ledger` | ⚠️ | ✅ | 🔴 | ❌ | |
| `Ecommerce` | ⚠️ | ✅ | 🔴 | ❌ | |
| `WorkQueue` | ✅ | ✅ | ✅ | ❌ | All 3 canonical components |
| `PublicWork` | ⚠️ | ⚠️ | ⚠️ | ❌ | Inline states |
| `OpportunityRadar` | ✅ | ❌ | ⚠️ | ❌ | Skeleton only |
| `ProgramCatalog` | ✅ | ⚠️ | ⚠️ | ❌ | Skeleton only |
| `TradingConsolidated` | ⚠️ | ⚠️ | ⚠️ | ❌ | Inline |
| `AccountsHub` | ⚠️ | ⚠️ | ⚠️ | ❌ | Inline |
| `Settings` | ⚠️ | ⚠️ | ⚠️ | ✅ | Fallback catalog |

**OFFLINE state: 0 pages implement it** — `lib/offline.ts` (355 LOC) has 0 consumers.

---

## State Component Prop Bugs (24 instances)

| Component | Used | Expected | Broken Instances |
|-----------|------|----------|------------------|
| `LoadingState` | `message="..."` | `text="..."` | 11 (Content, Clients, FirstMoney, LocalJobs, PlatformOnboarding ×2, Mission ×2, Ecommerce, Ledger, AvailabilityIntelligenceCard) |
| `ErrorState` (shared) | `:message @retry` | `:error :on-retry` | 11 (same 11 files) |
| `ErrorState` (ui) | `:message @retry` | `title/description/onRetry` | 2 (Capital, AvailabilityIntelligenceCard) |
| `EmptyState` | `icon="X"` | slot `#icon` | 13 (Capital ×11, DashboardAegis ×2) |

---

## Unresolved Identifiers in Templates (6 files, 21 instances)

| File | Missing | Instances |
|--------|---------|-----------|
| `IncomeHome.vue` | `useHuntStore` | 1 (line 142) |
| `IncomeHome.vue` | `api` | 5 (lines 97, 98, 176, 245, 246) |
| `IncomeHome.vue` | `Card` | 9 (line 334, 361, 394, 518, 692, 705, 741) |
| `IncomeHome.vue` | `Badge` | 4 (lines 558, 649) |
| `Capital.vue` | `Skeleton` | 2 (lines 400, 402) |
| `Capital.vue` | `Link2` | 1 (line 749) |
| `Connections.vue` | `DoughnutChart` | 1 (line 390) |
| `OutlookCalendar.vue` | `CardContent` | 12 (lines 111-264) |
| `Settings.vue` | `Cog`, `Zap` | 2 (lines 398, 829) |
| `FixPlansList.vue` | `ApprovalBadge` | 1 (line 23) |

**Also**: `IncomeHome.vue:445` malformed `aria-label="Trigger New Customevent('Toggle Copilot'"` (unbalanced quote).

---

## Test Coverage (191 tests, 17 files)

| Directory | Files | Tests |
|-----------|-------|-------|
| `__tests__/` | 1 | 4 |
| `components/ui/` | 2 | 33 |
| `composables/__tests__/` | 3 | 22 |
| `composables/` (inline) | 2 | 17 |
| `lib/__tests__/` | 1 | 12 |
| `pages/__tests__/` | 4 | 19 |
| `stores/__tests__/` | 6 | 66 |
| **TOTAL** | **19** | **191** |

**Broken test imports** (2):
- `pages/__tests__/Dashboard.test.ts:4` → `@/pages/Dashboard.vue` (MISSING)
- `pages/__tests__/Findings.test.ts:4` → `@/pages/Findings.vue` (MISSING)

**Test Setup**: `test-setup.ts` stubs 49 Lucide icons, `router-link`/`router-view`, no `fetch`/`WebSocket`/`IntersectionObserver` stubs.

---

## Build & CI Status

| Check | Status |
|-------|--------|
| `npm run build` | ✅ (12-15s) |
| `npx vue-tsc --noEmit` | ✅ 0 errors |
| `npm run test` | 17/17 passed (191 tests) — 2 pre-existing failures (Dashboard/Findings test imports) |
| `npm run lint` | ✅ (Biome) |
| CI | `test.yml` runs build; `ci.yml` runs lint+build; **0 workflows run vue-tsc, vitest, or playwright** |

---

## Design System Violations

| Issue | Count | Files |
|-------|-------|-------|
| Tailwind `red-*` palette | 58 | 10 files |
| Undefined CSS vars (`var(--xxx)`) | 43 distinct | 43 files |
| `style.css:27` | Self-referential `--color-border: var(--color-border)` | 1 |
| Gradients/glows | 71 in 26 .vue | 26 |
| `style.css` legacy utilities | Gradients, glows, phosphor effects | 1 file |

---

## Largest Files (Top 10)

| File | Lines |
|------|-------|
| `ProgressiveScaling.vue` | 1,741 |
| `Settings.vue` | 1,159 |
| `VersionBackup.vue` | 1,020 |
| `PersonalizationWizard.vue` | 978 |
| `Connections.vue` | 898 |
| `Capital.vue` | 862 |
| `Knowledge.vue` | 821 |
| `IncomeHome.vue` | 782 |
| `ModeManagerPanel.vue` | 727 |
| `CommandPalette.vue` | 724 |

---

## Build Output (Production)

```
dist/
├── index.html (1,615 bytes)
├── assets/
│   ├── index-*.js (186-458 KB gzipped)
│   ├── cytoscape*.js (46-443 KB)
│   ├── xterm-*.js (283 KB)
│   └── fonts (woff2)
└── favicon.ico
```

---

## Imports of Non-Existent Files (4)

| File | Line | Import |
|------|------|--------|
| `components/ui/index.ts` | 2 | `OwnexInput` (MISSING) |
| `components/ui/index.ts` | 3 | `OwnexKPI` (MISSING) |
| `pages/__tests__/Dashboard.test.ts` | 4 | `@/pages/Dashboard.vue` |
| `pages/__tests__/Findings.test.ts` | 4 | `@/pages/Findings.vue` |

---

## Broken Test Imports (2)

| Test File | Missing Import |
|-----------|----------------|
| `pages/__tests__/Dashboard.test.ts:4` | `@/pages/Dashboard.vue` |
| `pages/__tests__/Findings.test.ts:4` | `@/pages/Findings.vue` |

Both pages were consolidated into `IntelligenceConsolidated.vue` and `TargetsPage.vue` respectively.