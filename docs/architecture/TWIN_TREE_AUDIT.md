# Twin-Tree Audit — `core/` vs `cores/` (verified 2026-11-09)

Status: AUDIT COMPLETE — consolidation NOT executed (requires dedicated worktree + per-file adjudication).

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
- `api/routers/activity.py` imports `core.events.event_bus.get_core_event_bus` — a **different bus** than `cores.events.event_bus` (177 vs 313 lines). Both event buses are live; not necessarily a bug, but two buses is architectural debt.
- Scheduler runtime: `core/scheduler/jobs.py` is canonical (cores copy stale/absent).
- Import counts (non-quarantine): ~844 files reference `core.*`, ~714 reference `cores.*` — heavily entangled, NOT a clean split.

## Divergent files requiring per-file adjudication (115)

Critical infrastructure (highest risk if wrong copy edited):

- `events/event_bus.py` + `events/__init__.py` — TWO live event buses
- `credentials/vault.py`, `credentials/{adapter_helpers,health}.py`
- `capabilities/registry.py`, `app_registry.py`
- `opportunity/{engine,models,scoring,source_payment_docs}.py`, `opportunity/adapters/__init__.py`, `opportunity/adapters/forge/opire.py`, `opportunity/executors/*`
- `finance/models.py`, `investment/{manager,models,allocation}.py`, `investment/adapters/*` (7 adapters)
- `knowledge/{graph,models}.py`, `cycles/*` (9 files), `copilot/*` (7 files), `autonomy/*` (3), `ai_router/engine.py`
- `health/engine.py`, `osint/engine.py`, `discovery/importer.py`, `engine/learning.py`, `execution/request_mutator.py`, `extension/*`, `integrations/registry.py`, `integration/orchestrator.py`, `merlin/memory.py`, `validation/*`, `reports/quality/scorer.py`, `target_intelligence/prioritizer.py`, `sensors/base.py`, `pipeline/hypothesis_bridge.py`, `auto_submit/pipeline.py`, `evidence/composer.py`

(Full list: `comm -12` of both trees minus identical files — regenerate with the commands below.)

## Non-goals / warnings

- Do **NOT** blanket-merge or symlink the trees: 115 divergent files mean real behavioral differences; `core.events.event_bus` and `cores.events.event_bus` are distinct live systems.
- `.quarantine/core_cores_2026-11-09/` already contains a prior consolidation snapshot — review before re-doing work.
- `work/ownex-economy-active-earn/` is a stale copy — noncanonical.

## Recommended consolidation order (for dedicated worktree)

1. Inventory which of the 115 divergent files have live importers on each side (script: grep imports per file).
2. For each: pick canonical by the 12-criteria comparison in `INTEGRATION_PROTOCOL.md` §4.
3. Migrate stragglers (e.g. `api/routers/activity.py` if `core` bus is deprecated).
4. Delete losing copies only after zero-importer verification + tests.
5. Candidates likely safe to delete first: `core/` files with zero importers and stale content.

## Regeneration commands

```bash
comm -12 <(cd core && find . -name '*.py' | sort) <(cd cores && find . -name '*.py' | sort) > /tmp/common.txt
# per-file diff:
while read f; do diff -q "core/$f" "cores/$f" >/dev/null || echo "$f"; done < /tmp/common.txt
```
