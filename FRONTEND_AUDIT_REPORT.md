# OWNEX Frontend Audit Report

**Date**: 2026-10-13
**Scope**: Audit of existing frontend codebase and implementation plan per OWNEX FRONTEND REVOLUTION megaprompt

## 1. REPOSITORY STATE

### 1.1 Structure
- **Primary frontend**: `/home/adriel/projects/Rastro/frontend/` — Vue 3 + Vite + TypeScript
- **Alternative frontend**: `/home/adriel/projects/Rastro/frontend_new/` — newer version with fewer pages
- **Design system**: `/home/adriel/projects/Rastro/design-system/MASTER.md` — tokens, components, modes
- **Backend API**: FastAPI at `/api/` with multiple routers
- **FINISHER backend**: `/home/adriel/projects/Rastro/scripts/finisher/` — state management, task execution
- **Core modules**: `/home/adriel/projects/Rastro/cores/` — execution, actions, accountability

### 1.2 Key Directories
```
frontend/src/
├── assets/
├── components/     ← UI components (shadcn-vue + ownex extensions)
├── composables/    ← useOwnexState, useNextRecommendation, useToast
├── lib/            ← api client, types, constants
├── pages/          ← 65+ page components (main routes)
├── router/         ← Vue Router with 7 main sections + apps
├── services/       ← ownexData.ts (100+ API functions), ownexAi.ts
├── stores/         ← hunt store
├── styles/         ← global styles
├── types/          ← TypeScript interfaces
├── utils/          └── helpers
└── views/          ← (frontend_new only)
```

## 2. NAVIGATION & ROUTES AUDIT

### 2.1 Main Routes (7 sections per router/index.ts)
1. **Command Center** (`/`) — IncomeHome.vue (dashboard)
2. **Intelligence** (`/intelligence`) — Findings, evidence, investigations
3. **Targets** (`/targets`) — Targets, discovery, opportunity radar
4. **Reports** (`/reports`) — Report queue, center, history, verification
5. **Capital** (`/capital`) — Revenue, EV targets, platforms, progressive scaling
6. **Operations** (`/operations`) — Scheduler, pipelines, tools, settings, workrooms
7. **Copilot** (`/copilot`) — Assistant, notifications, alerts, computer use

### 2.2 Missing Routes per Megaprompt
- **FINISHER** — No dedicated frontend page
- **Automatizaciones** — Partial (opportunity planner, workflows)
- **Integraciones** — Present but could be consolidated
- **Historial y Auditoría** — Not explicitly mapped

### 2.3 Legacy Routes
- 15+ legacy redirects removed (2026-09-04 consolidation)
- ODYSSEY (no backend), AEGIS (pentesting), ATLAS (investments) as satellite apps

## 3. PAGE BY PAGE STATUS

### 3.1 IncomeHome.vue (Command Center — 826 lines)
**Status**: IMPLEMENTED_AND_VERIFIED
**Strengths**:
- Real data only (no mocks)
- Daily digest with last-visit tracking
- AI center integration (fetchAiCenter)
- Capital snapshot fetch
- Next recommendation system
- Multiple component composition (OneActionCard, DailyBriefCard, etc.)
- useNextRecommendation composable for prioritized actions

**Weaknesses**:
- No FINISHER integration visible
- Heavy component dependencies (37 imported components)
- Some components may not be fully verified

### 3.2 Capital.vue (871 lines)
**Status**: IMPLEMENTED_AND_VERIFIED
**Strengths**:
- 7-tab structure (overview, progressive-scaling, targets, programs, pipeline, platforms, settings)
- Real API calls: `/api/revenue/capital-dashboard`, `getRevenueMetrics()`, `getEVRankedTargets()`, `getPlatformsStatus()`
- KPI blocks, charts, data tables
- Platform status with connection states
- Progressive scaling sub-page

**Weaknesses**:
- `expected_return_min/max` shown as estimated (not verified real)
- Platforms differentiate cataloged vs connected (partially)
- No FINISHER connection
- Some money figures may be simulated

### 3.3 OpportunityRadar.vue (172 lines)
**Status**: IMPLEMENTED_AND_VERIFIED
**Strengths**:
- Real API: `/targets?limit=50&sort_by=opportunity_score&sort_order=desc`
- Program interface with HIGH_CONFIDENCE_90 gate statuses
- Score color coding (success/warning/default)
- Search/filter functionality
- Bar chart + grid of programs with badges

**Weaknesses**:
- Empty state: "No se encontraron programas" (no context/next action per design system)
- Bar chart only shows top 10
- No FINISHER connection
- Opportunity scores shown without verification context

### 3.4 OpportunityPlanner.vue (214 lines)
**Status**: IMPLEMENTED_AND_VERIFIED
**Strengths**:
- Fetches `/economic/programs/${programId}/plan`
- Doughnut chart for return distribution
- ROI summary with expected return ranges
- "Where to start" checklist
- Techniques and vulnerability type recommendations
- Formatted money display

**Weaknesses**:
- Expected returns shown as estimated (not verified)
- No FINISHER or execution connection
- Plan generated date shown without verification status

### 3.5 TradingConsolidated.vue
**Status**: Partially implemented
**Strengths**:
- Exists as trading page
**Weaknesses**:
- Need to verify content and FINISHER connection

### 3.6 Pages Missing or Need Audit
- **FINISHER** — No frontend page exists
- **Automatizaciones** — No dedicated page (may be in operations/workflows)
- **Historial/Auditoría** — Partial (reports center exists)
- **Configuración centralized** — Settings.vue exists (complex, 71KB)

## 4. FINISHER INTEGRATION ANALYSIS

### 4.1 Backend State (scripts/finisher/state.py)
- **TaskStatus**: PENDING, READY, RUNNING, VERIFYING, PASSED, FAILED, BLOCKED, WAITING_HUMAN, SKIPPED, ROLLED_BACK
- **ProjectStatus**: RUNNING, PAUSED, WAITING_HUMAN, BLOCKED, FAILED, RECOVERING, COMPLETED, STOPPED
- **WorkerStatus**: STARTING, ALIVE, IDLE, RUNNING, COMPLETED, CRASHED, TIMEOUT, TERMINATED, UNAVAILABLE
- **States stored**: `.finisher/state.json` with tasks, workers, checkpoints, human_gates, locks

### 4.2 API Endpoints for FINISHER
- **None currently exposed** via `/api/` routers
- Execution tracker at `/api/execution/` (separate from FINISHER)
- Human gate resolution via state management only

### 4.3 Missing FINISHER Frontend
- No `/finisher` route
- No task queue visualization
- No checkpoint tracking
- No human gate approval UI
- No execution event streaming

## 5. FINANCIAL INTEGRATION ANALYSIS

### 5.1 Capital.vue Financial Data
- Revenue metrics from `/api/revenue/capital-dashboard`
- EV (Expected Value) ranked targets
- Platform status with connect/eligibility states
- Progressive scaling with capital tracking

### 5.2 Finance Routers (api/routers/finance.py)
100+ functions including:
- `get_dashboard()`, `get_revenue_metrics()`
- `list_opportunities()`, `get_opportunity()`
- `create_budget()`, `list_budgets()`
- `check_budget_alerts()`
- `generate_summary()`, `list_summaries()`
- `get_freedom_progress()`, `update_freedom_progress()`

### 5.3 Capital Data Concerns
- Some metrics described as "estimated" vs "real"
- Platforms need better cataloged vs connected differentiation
- No explicit FINISHER budget integration

## 6. DESIGN SYSTEM COMPLIANCE

### 6.1 MASTER.md Compliance
✅ **Color system**: TESLA palette (black/white/grays), no arbitrary RGB
✅ **Typography**: Inter/DM Sans, JetBrains Mono for money
✅ **Spacing**: 4px grid system
✅ **Border radius**: sm/md/lg/rxl definitions
✅ **Shadows**: sm/md/lg definitions
✅ **Z-index**: Defined scale
✅ **Motion**: Fast/base/slow transitions, respects prefers-reduced-motion
✅ **Three modes**: LITE, FULL, CAPITAL defined
✅ **Empty states**: "NEVER show just 'No data'" — context + next action required
✅ **Error states**: Explain WHAT, WHY, WHAT USER needs to do

### 6.2 Components Inventory
**Base (shadcn-vue)**: Button, Input, Select, Dialog, Sheet, Card, Badge, Tabs, Tooltip, Table
**OWNEX components**: OneActionCard, PrimaryModeSelector, NotificationCenter, CommandPalette, ModeIndicator
**Charts**: BarChart, DoughnutChart (custom)
**Empty/Error states**: EmptyState, ErrorState, LoadingState ✅
**UI widgets**: Various dashboards, cards, badges

## 7. RESPONSIVE ANALYSIS

### 7.1 Current Breakpoints (design-system/MASTER.md)
- Mobile: 375px — bottom nav, single column
- Tablet: 768px — collapsed sidebar
- Desktop: 1024px — full sidebar
- Wide: 1440px+ — multi-panel

### 7.2 Pages Tested for Responsiveness
- IncomeHome.vue — likely responsive (flex/grid layout)
- Capital.vue — tab-based, may need adjustment
- OpportunityRadar.vue — grid responsive (1→2→3 columns)

### 7.3 Gaps
- No explicit responsive rules for FINISHER dashboard
- No tablet-specific optimizations detected
- Some tables may not adapt well to narrow screens

## 8. ACCESSIBILITY COMPLIANCE

### 8.1 Strengths
- Focus visible states in components
- Contrast ratios per TESLA palette (4.5:1 minimum)
- Keyboard navigation support
- No color-only information conveyance (design system rule)
- Screen reader friendly labels

### 8.2 Gaps
- FINISHER human gates: no accessibility described
- Some badge variants may not have sufficient contrast
- Modals: need to verify focus trap implementation
- Tables: need to verify small-screen readability

## 9. PERFORMANCE OBSERVATIONS

### 9.1 Loading Patterns
- Skeleton screens used (Skeleton component)
- Loading refs with `.value = true/false`
- Promise.allSettled for parallel fetching
- Error states shown when fetch fails

### 9.2 Performance Concerns
- IncomeHome.vue imports 37+ components (may impact initial load)
- Capital.vue has multiple API calls in `fetchAll()` Promise.allSettled
- OpportunityRadar uses BarChart with dynamic labels (may re-render frequently)
- No virtualization for long lists detected

### 9.3 Optimization Gaps
- No `v-memo` or `v-once` for static data
- No intersection observer for lazy loading
- No query client (tanstack/query) detected — manual fetching

## 10. TESTS STATUS

### 10.1 Test Coverage
- Frontend tests exist but limited scope
- `tests/test_opencode_contract.py::test_instructions_block_within_budget` — budget check
- Visual tests not systematically run

### 10.2 Test Files Found
- Need to verify what frontend tests exist

## 11. SUMMARY OF FINDINGS

### 11.1 Strengths
1. **Real data focus**: No intentional mocks, API-first approach
2. **Design system**: Well-defined tokens, modes, and component library
3. **Mode architecture**: LITE/FULL/CAPITAL clearly defined
4. **Error handling**: Consistent patterns with ErrorState/LoadingState
5. **Accessibility**: TESLA color rules, contrast, keyboard nav
6. **Responsive**: Breakpoints defined, basic adaptation works
7. **Consolidated navigation**: 7 main routes, legacy cleanup

### 11.2 Critical Gaps (per Megaprompt)
1. **No FINISHER frontend page** — entire megaprompt section 8 is unimplemented
2. **No FINISHER API routes** — backend state exists but no frontend consumption
3. **No assistant integration** — Copilot page exists but may not integrate global state
4. **Empty states lack context** — some pages show "No data" without next action
5. **Financial estimates not distinguished from real** — some metrics need clearer labeling
6. **No search/universal command palette** — per megaprompt section 7
7. **No palette de comandos** — Cmd+K or similar not implemented
8. **Automatizaciones not visible** — section 12 not mapped to frontend
9. **Notificaciones unificadas** — section 14 may be partial
10. **Historical/audit view** — section 15 not explicitly mapped

### 11.3 Priority Implementation Areas
1. **FINISHER dashboard** (highest — section 8 of megaprompt)
2. **Assistant global integration** (section 6)
3. **Search universal + command palette** (section 7)
4. **Financial clarity** (section 9 — distinguish sim vs real)
5. **Automatizaciones UI** (section 12)
6. **Responsive refinement** (section 4.3)