# LEGACY MAP — OWNEX (2026-09-30)

## Classification Criteria

| Status | Definition | Action |
|--------|------------|--------|
| **ACTIVE** | Used in production, maintained | Keep, maintain |
| **PARTIAL** | Partially implemented, has gaps | Complete or deprecate |
| **DUPLICATED** | Multiple implementations of same concept | Consolidate |
| **LEGACY** | Superseded, kept for compatibility | Migrate → deprecate |
| **DEPRECATED** | Scheduled for removal | Remove in next major |
| **ORPHANED** | No consumers, unclear purpose | Investigate → delete |
| **DEAD** | Code exists but never executes | Remove |
| **BROKEN** | Known non-functional | Fix or remove |
| **PLACEHOLDER** | Stub/unfinished | Complete or remove |
| **EXPERIMENTAL** | Unvalidated, unstable | Stabilize or remove |
| **UNKNOWN** | Cannot determine | Investigate |

---

## Component Classification

### Frontend (128 components)

| Status | Count | Examples |
|--------|-------|----------|
| **ACTIVE** | 87 | Core UI (Button, Card, Modal, CommandPalette, etc.) |
| **DEAD** | 41 (32%) | `AgentFleet`, `PixelAvatar`, `TodayBriefing`, `AutomationStrip`, `ReportPipeline`, `RevenueSnapshot`, `ThroughputCore`, `WorkCyclesGrid`, `FirstDayGuide`, `IncomeGuidanceAssistant`, `ModeSelector`, `KnowledgeFeed`, `Breadcrumbs`, `ModernNavbar`, `StatusBar` (layout), `WorkspaceTabs`, `NotificationCenter`, `ApprovalBadge`, `CardDescription`, `CardFooter`, `CopyHelper`, `StatusBar` (ui), `Timeline`, `WidgetWrapper`, 10 `WidgetWrapper` children, `WorkStateBadge`, 6 `TradingLab*` (behind dead barrel), `MissionControlView`, `GoodMorning`, `PrepareButton`, `ReadinessMeter`, `ServiceGrid`, `AnimatedCounter`, `DepthLayer`, `StatusDot`, `OrionHome`, `OrionSidebar`, `StartupGate`, `LogoReveal`, `ParticleField`, `TransitionOverlay`, `usePreloadData`, `useStartupSequence` |
| **DUPLICATED** | 6 pairs | `ErrorState` (2), `StatusBar` (2), `StatusDot` (2) |
| **DUPLICATED (barrel-only)** | 6 | `TradingLab*` (behind dead `trading/index.ts`) |
| **BROKEN** | 2 | `ui/index.ts` (exports non-existent `OwnexInput`, `OwnexKPI`), `mobile-companion/index.ts` (Python `"""` syntax) |
| **ORPHANED** | 3 | `WidgetRegistry` (0 importers, drives 10 dead widgets), `trading/index.ts` (0 importers) |

### Pages (64 total)

| Status | Count |
|--------|-------|
| ACTIVE (routed) | 64 |
| ORPHANED | 0 |

### Stores (9 pinia)

| Status | Stores |
|--------|--------|
| ACTIVE | `auth`, `discovery`, `hunt`, `notifications`, `settings`, `ui`, `accessibility` |
| DEAD | `findings` (0 consumers), `report` (0 consumers) |

### Composables (21)

| Status | Count |
|--------|-------|
| ACTIVE | 12 |
| DEAD | 9 (`useAudio`, `useBountyStream`, `useCompanion`, `useCopyHelper`, `useFirstDayGuide`, `useGlobalHotkeys`, `useMicroInteractions`, `useMotion`, `useMultiSelect`) |
| DEAD (transitive) | 2 (`useGuidedMode` → dead components) |

### Services (6)

| Status | Files |
|--------|-------|
| ACTIVE | `ownexData.ts` (3104 LOC, 29 importers), `ownexAi.ts`, `chatSemantics.ts`, `knowledge.ts` |
| DEAD | `controlPanel.ts` (1530 LOC, 0 importers), `moneyprinter.ts` (139 LOC, 0 importers) |

### Lib (4 modules)

| Status | Files |
|--------|-------|
| ACTIVE | `api.ts` (70 importers), `backend.ts` (6), `utils.ts` (19) |
| DEAD | `offline.ts` (355 LOC, 0 importers) |

---

## Backend Legacy Classification

### Routers (201 mounted, 0 dead)

| Status | Count | Notes |
|--------|-------|-------|
| ACTIVE | 198 | All mounted |
| ARCHIVED | 5 | `api/routers/_archived/` (excluded from ruff, not imported) |

### Core Subpackages (193)

| Status | Count | LOC | Examples |
|--------|-------|-----|----------|
| ACTIVE | ~119 | ~312K | `opportunity`, `direct_work_engine`, `trading`, `ai`, `engine` |
| UNTESTED/DEAD | 74 | 45,288 | `autopilot`, `personal_infrastructure`, `revenue_multiplier`, `ledger`, `mission`, `pillars`, `autopilot`, `discovery_engine`, `obsidian`, `onboarding`, `wear_os`, etc. |
| DUPLICATED | 6 domains | ~70K | Opportunity, Validation, Scheduling, Revenue, Scheduling, Revenue |

### Dead/Unused Core Subpackages (74, 45K LOC)

| Package | LOC | Files | Reason |
|---------|-----|-------|--------|
| `cores/autopilot` | 3,822 | 13 | No consumers, related to dead UI |
| `cores/personal_infrastructure` | 2,603 | 8 | Dead feature |
| `cores/revenue_multiplier` | 2,194 | 11 | Duplicate revenue system |
| `cores/pillars` | 1,807 | 5 | Unknown purpose |
| `cores/market_intelligence` | 1,652 | 7 | Unused |
| `cores/merlin` | 1,484 | 4 | Legacy AI |
| `cores/platform_connectors` | 1,340 | 4 | Unused |
| `cores/merlin` | 1,484 | 4 | Dead |
| `cores/differential_intelligence` | 1,111 | 6 | Dead |
| `cores/economy` | 1,106 | 6 | Duplicate of revenue |
| `cores/assistant` | 1,101 | 6 | Dead |
| `cores/target_auth` | 1,084 | 7 | Dead |
| `cores/zero_barrier_engine` | 1,047 | 6 | Dead |

### Archived Routers (5, excluded from build)

| File | Reason |
|------|--------|
| `api/routers/_archived/acceptance.py` | Superseded |
| `api/routers/_archived/dashboard.py` | Superseded |
| `api/routers/_archived/execution_engine.py` | Superseded |
| `api/routers/_archived/financial_hub.py` | Superseded |
| `api/routers/_archived/opportunity.py` | Superseded |

### Dead Stores (2/9 pinia)

| Store | Reason |
|-------|--------|
| `findings` | 0 consumers, only tested in `stores/__tests__/findings.test.ts` |
| `report` | 0 consumers, only tested in `stores/__tests__/report.test.ts` |

### Dead Services (2/6)

| Service | LOC | Reason |
|---------|-----|--------|
| `controlPanel.ts` | 1,530 | 0 importers, only a comment in `backend.ts:211` |
| `moneyprinter.ts` | 139 | 0 importers |

### Broken Code (will not compile)

| File | Issue |
|--------|-------|
| `frontend/src/components/ui/index.ts` | Exports `OwnexInput` and `OwnexKPI` — files don't exist |
| `frontend/src/components/mobile-companion/index.ts` | Starts with Python `"""` — invalid TS |

---

## Apps (8, all with manifests)

| App | Status | API Mounted? | Notes |
|-----|--------|--------------|-------|
| `aegis` | ACTIVE | ❌ | 31 router files, own dashboard |
| `atlas` | ACTIVE | ❌ | 16 router files, dashboard |
| `odyssey` | ACTIVE | ❌ | 16 router files, dashboard |
| `hermes` | ACTIVE | ❌ | No api/routers.py |
| `vault` | ACTIVE | ❌ | No api/routers.py |
| `pulse` | ACTIVE | ❌ | No api/routers.py |
| `forge` | ACTIVE | ❌ | No api/routers.py |
| `cateye` | ACTIVE | ❌ | No api/routers.py |

**Note**: No `apps/*/api/routers.py` are mounted in `api/main.py` (grep = 0 hits). All 8 apps have manifests but only 3 expose routers.

---

## Deprecated / Archived (Intentionally Removed)

| Item | Location | Replaced By |
|-------|----------|-------------|
| `api/routers/acceptance.py` | `_archived/` | `reports/` flow |
| `api/routers/dashboard.py` | `_archived/` | `command_center` |
| `api/routers/execution_engine.py` | `_archived/` | `execution/` pipeline |
| `api/routers/financial_hub.py` | `_archived/` | `financial/` |
| `api/routers/opportunity.py` | `_archived/` | `opportunity/` engine |
| `core/` (singular) | Deleted 2026-09-14 | `cores/` (plural) |
| `tests/test_desktop_release.py` | Pre-existing failure | N/A |
| `tests/test_e2e_copilot.py` | Pre-existing failure | N/A |
| `tests/test_security.py` | Pre-existing failure | Known flaky |

---

## Deprecated (Scheduled for Removal)

| Item | Location | Target Removal |
|-------|----------|----------------|
| Fiverr source | `api/routers/fiverr.py`, `api/adapters/direct_work_fiverr.py`, `cores/opportunity/adapters/forge/fiverr.py` | Phase 4 |
| Workana source | `api/routers/workana.py` (if exists), adapters | Phase 4 |
| Freelancer platform | `adapters/freelancer.py`, `forge/freelancer.py`, `executors/freelancer_executor.py` | Phase 4 |
| `cores/trading/` (6 components) | `frontend/src/components/trading/` | Keep but isolate |
| `cores/revenue_multiplier/` | 11 files, 2,194 LOC | Phase 3 |
| `cores/ledger/` | 2 files, 334 LOC | Phase 3 (merge into revenue) |
| `cores/autopilot/` | 3,822 LOC, 13 files | Phase 8 |
| `cores/personal_infrastructure/` | 2,603 LOC | Phase 3 |
| `cores/revenue_multiplier/` | 2,194 LOC | Phase 3 |
| `cores/ledger/` | 334 LOC | Phase 3 (merge) |
| `cores/validation/` vs `engine/validation` vs `execution/validation` | 6 implementations | Phase 2 (consolidate) |

---

## Unknown / Needs Investigation

| Item | Location | Questions |
|--------|----------|-----------|
| `cores/engine/` (34 files, 9.9K LOC) | `cores/engine/` | What does it orchestrate? |
| `cores/offensive/` (44 files, 8.9K LOC) | `cores/offensive/` | Red team? Validation? |
| `cores/execution/` (54 files, 8.3K LOC) | `cores/execution/` | Overlaps with `direct_work_engine`? |
| `cores/offensive/` (44 files) | `cores/offensive/` | Red team tools? |
| `cores/agents/` (7 files) | `cores/agents/` | What agents? |
| `cores/swarm/` (6 files) | `cores/swarm/` | Agent swarm? |
| `cores/mission/` (3 files) | `cores/mission/` | Duplicate of `cores/mission-hub`? |
| `cores/identity/` | `cores/identity/` | Auth-related? |
| `cores/observability/` | `cores/observability/` | Metrics/logging? |