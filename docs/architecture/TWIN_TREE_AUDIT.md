# Twin-Tree Audit — `core/` vs `cores/` (verified 2026-11-09)

Status: AUDIT COMPLETE — consolidation NOT executed (requires dedicated worktree + repo-wide codemod).

## Verified numbers

| Metric | Value |
|---|---|
| `core/` Python files | 708 |
| `cores/` Python files | 1108 |
| Paths present in BOTH | 421 |
| Identical content | 306 |
| Divergent content | 115 |
| Only in `core/` | 287 |
| Only in `cores/` | 687 |

## Runtime ownership evidence

- `api/main.py`, `api/lifespan.py`, `api/scheduler.py`, `api/routers/*` import **`cores.*`** for infra (learning, targets, orchestrator, events, health, optimization, recovery, agents, operations, system_health, prometheus).
- `api/lifespan.py` + `core/api/routers.py` + `core/orion/*` import **`core.scheduler.*`** — `cores/` has **no scheduler package**; scheduler is `core/`-only.
- `api/routers/activity.py` imports `core.events.event_bus.get_core_event_bus` — a **different bus** than `cores.events.event_bus` (177 vs 313 lines). Both event buses are live; two buses is architectural debt.
- Scheduler runtime: `core/scheduler/jobs.py` is canonical.
- Import counts (non-quarantine): ~844 files reference `core.*`, ~714 reference `cores.*`.

## CRITICAL finding — the trees are cross-wired, not parallel

Verified import counts (excluding `__pycache__`, `.quarantine/`, `work/`):

- **317 files inside `cores/` import `core.*`** (e.g. `cores/engine/{strategy,evolution,knowledge_graph,registry,classification,validation,identity,learning}.py` all do `from core.engine.base import Engine`; `cores/credentials/*` import `core.credentials.*`).
- **94 files inside `core/` import `cores.*`**.
- `core/engine/__init__.py` is a 1-line docstring — `core/engine/` acts as the **base library** that `cores/engine/` extends (which adds hypothesis/, unified_scoring, risk_model, etc.).

**Conclusion**: `core/` + `cores/` are ONE tangled system split across two top-level packages, not two parallel implementations. "Consolidation" is therefore a repo-wide import rewrite (~400+ files touched), not a per-file merge. It MUST be done as a mechanical codemod in a dedicated worktree with the full test suite — never in the shared working tree.

## Phase 1 complete — importer matrix (verified)

Full data: `docs/architecture/TWIN_TREE_IMPORTERS.txt` (115 rows, format `path|core_ext:N core_int:N|cores_ext:N cores_int:N` — ext = importers outside the twin trees i.e. `api/`, `scripts/`, `extensions/`, `tests/`; int = importers inside own tree).

Key findings:

- **53/115 divergent files have ZERO importers on either side** (incl. tests/) — mostly `__init__.py` twins; only 2 are real modules (`engine/learning.py`, `integration/orchestrator.py`). Dead-duplicate candidates pending dynamic-import verification.
- **`cores/` wins external consumers** for: `events/event_bus` (11 ext vs 1), `finance/models`, `execution/request_mutator`, `merlin/memory`, `validation/confidence`, `opportunity/engine` (slight).
- **`core/` wins external consumers** for: `health/engine` (7 vs 0), `capabilities/registry` (5 vs 0), `credentials/vault` (4 vs 0), `investment/*` (manager/allocation/models/adapters), `knowledge/graph`, `reports/quality/scorer`, `sensors/base`, `target_intelligence/prioritizer`, `pipeline/hypothesis_bridge`, `discovery/importer`, `extension/registry`, `integrations/registry`, `copilot/*`, `cycles/*`, `autonomy/*`, `ai_router/engine`.
- **Pattern**: each tree is a largely self-contained ecosystem; `api/` is the decisive boundary. Most divergent files are only consumed inside their own tree.

## Divergent files requiring per-file adjudication (115)

Critical infrastructure (highest risk if wrong copy edited):

- `events/event_bus.py` + `events/__init__.py` — TWO live event buses
- `credentials/vault.py`, `credentials/{adapter_helpers,health}.py`
- `capabilities/registry.py`, `app_registry.py`
- `opportunity/{engine,models,scoring,source_payment_docs}.py`, `opportunity/adapters/__init__.py`, `opportunity/adapters/forge/opire.py`, `opportunity/executors/*`
- `finance/models.py`, `investment/{manager,models,allocation}.py`, `investment/adapters/*` (7 adapters)
- `knowledge/{graph,models}.py`, `cycles/*` (9 files), `copilot/*` (7 files), `autonomy/*` (3), `ai_router/engine.py`
- `health/engine.py`, `osint/engine.py`, `discovery/importer.py`, `engine/learning.py`, `execution/request_mutator.py`, `extension/*`, `integrations/registry.py`, `integration/orchestrator.py`, `merlin/memory.py`, `validation/*`, `reports/quality/scorer.py`, `target_intelligence/prioritizer.py`, `sensors/base.py`, `pipeline/hypothesis_bridge.py`, `auto_submit/pipeline.py`, `evidence/composer.py`

## Non-goals / warnings

- Do **NOT** blanket-merge or symlink the trees: 115 divergent files mean real behavioral differences; `core.events.event_bus` and `cores.events.event_bus` are distinct live systems.
- `.quarantine/core_cores_2026-11-09/` already contains a prior consolidation snapshot — review before re-doing work.
- `work/ownex-economy-active-earn/` is a stale copy — noncanonical.

## Recommended consolidation order (for dedicated worktree)

1. ~~Inventory which of the 115 divergent files have live importers~~ DONE → `TWIN_TREE_IMPORTERS.txt`.
2. Decide target package layout first (e.g. everything → `cores/`, or `core/` absorbs `cores/`) — this determines the codemod direction. Evidence currently favors `cores/` for api-facing infra, `core/` for engine-base + scheduler + investment.
3. Write a mechanical import-rewrite codemod (`core.X` → `cores.X` or vice versa per adjudicated map) — never hand-edit 400 files.
4. Migrate stragglers (e.g. `api/routers/activity.py` if `core` bus is deprecated; dual event buses need an ADR first — `docs/architecture/decisions/`).
5. Delete the 2 zero-importer modules + losing copies only after zero-importer verification + full pytest.
6. Run full quality gates (`QUALITY_GATES.md`) before merge.

## Regeneration commands

```bash
comm -12 <(cd core && find . -name '*.py' | sort) <(cd cores && find . -name '*.py' | sort) > /tmp/common.txt
# per-file diff:
while read f; do diff -q "core/$f" "cores/$f" >/dev/null || echo "$f"; done < /tmp/common.txt
```
