# ARCHITECTURE MAP — OWNEX (2026-09-30)

## High-Level Topology

```
OWNEX/
├── api/                    # FastAPI backend (241 .py, 52K LOC)
│   ├── routers/ (199 files, 1846 endpoints)
│   ├── adapters/ (22 files)
│   └── middleware/ (6)
├── cores/                  # Core business logic (1,514 .py, 357K LOC)
│   ├── opportunity/ (83 files, 24.8K LOC)
│   ├── direct_work_engine/ (61 files, 23.4K LOC)
│   ├── trading/ (42 files, 12.3K LOC)
│   ├── ai/ (45 files, 11.3K LOC)
│   ├── engine/ (34 files, 9.9K LOC)
│   ├── offensive/ (44 files, 8.9K LOC)
│   ├── execution/ (54 files, 8.3K LOC)
│   └── ... 193 subpackages total
├── frontend/               # Vue 3 + TypeScript (217 .vue, 80 .ts)
│   ├── src/
│   │   ├── pages/ (64)
│   │   ├── components/ (128 .vue, 41 dead)
│   │   ├── stores/ (9, 2 dead)
│   │   ├── composables/ (21, 9 dead)
│   │   ├── services/ (6, 2 dead)
│   │   └── lib/ (api, backend, offline)
│   └── dist/ (production build)
├── desktop/                # Tauri v2 + PySide6 legacy
│   ├── src-tauri/ (Rust + Tauri v2)
│   └── native/ (PySide6, 888 LOC)
├── desktop/                # Legacy PySide6 (archived)
├── database/               # SQLAlchemy + Alembic (21 tables, NO financial tables)
├── tests/                  # 359 files, 5,887 tests
├── scripts/                # Build, migration, deployment
├── .ai/                    # Source of truth (docs, decisions, state)
└── dist/                   # Frontend production build
```

## Module Boundaries & Inversions

| Direction | Count | Severity |
|-----------|-------|----------|
| `cores/` → `api/` | 14 inverted imports | HIGH (layering violation) |
| `api/` → `desktop/` | 2 | MEDIUM |
| `desktop/` → `cores/` | 2 | LOW |
| `apps/` → `cores/` | 46 | MEDIUM |

**Critical inversion**: `api/main.py:443` monkey-patches `app.include_router` to discard `prefix`/`tags` — all prefixes baked into router definitions.

## Router Topology

- **201** `include_router` calls in `api/main.py`
- **29** root-mounted routers (no `/api` prefix) → 282 endpoints, 148 mutating without auth
- **165** under `/api/` prefix
- **1,846** distinct backend paths (1,835 path+method pairs)
- **1** collision: `GET /api/trading/dashboard/summary` (trading.py vs trading_dashboard.py)

---

## Dead Code Inventory

| Category | Count | Impact |
|----------|-------|--------|
| Dead components (0 importers) | 41/128 (32%) | Bundle bloat |
| Dead stores | 2/9 | Unused state |
| Dead composables | 9/21 (43%) | Bundle bloat |
| Dead services | 2/6 | Unused logic |
| Dead pages | 0/64 | Clean |
| Dead backend routers | 0 | Clean (all 201 mounted) |
| Untested core subpackages | 74/193 | 45K LOC untested |

---

## Duplicate Implementations (Critical)

| Domain | Count | Details |
|--------|-------|---------|
| Opportunity discovery | 4 parallel layers | `cores/opportunity/adapters/`, `executors/`, `api/adapters/`, `direct_work_engine/` |
| Validation | 6 implementations | `cores/validation/`, `engine/validation`, `execution/validation`, `cycles/stages/validation_executor`, `api/routers/validation`, `offensive/*` |
| Scheduling | 10 scheduler classes | 3 job registries (canonical + LifeScheduler + inline) |
| Revenue tracking | 6 implementations | `revenue/`, `revenue_tracker/`, `economic_feedback/`, `financial/`, `ledger/`, `revenue_multiplier/` |
| RevenueState enum | 2 declarations | `revenue/ledger.py:22` + `revenue_tracker.py:30` |
| RevenueMetrics class | 2 declarations | `revenue/metrics.py:28` + `revenue_tracker.py:321` |
| RevenueEngine class | 2 declarations | `revenue/engine.py:20` + `revenue/engine.py:165` |

Platform adapters duplicated across layers: Opire (4), Pulse (5), Forge (4), Algora (3), Code4rena (3), Immunefi (3), IssueHunt (3), Freelancer (3), OpenCollective (3), Atlas (3), Vault (3), Security (5).

---

## Data Stores (5 distinct roots, no clear ownership)

| Root | Files | Owner |
|------|-------|-------|
| `~/.ownex/` | 11,437 files | Multiple (workbank, payment_pipeline, projects, etc.) |
| `~/.orion/` | 88 refs | Legacy |
| `~/.config/ownex/` | 67 refs | Config |
| `<repo>/data/` | 56 .json | Dev-only |
| `database/catseye.db` | 1 | ORM (dev) |

**Critical**: 190 distinct store filename literals in source. No registry, no clear ownership. Test pollution: 11,057 `knowledge_graph_kg_test_*.db` in `~/.ownex/database/`.