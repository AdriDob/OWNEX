# ADR 0003 — Dual event buses: `core.events` vs `cores.events`

- Status: PROPOSED
- Date: 2026-11-09
- Related: `docs/architecture/TWIN_TREE_AUDIT.md`, ADR-0002, TD-01

## Context

Two independent event bus implementations are live simultaneously:

| | `core/events/event_bus.py` | `cores/events/event_bus.py` |
|---|---|---|
| Class | `CoreEventBus` (implements `core.interfaces.event_bus.IEventBus`) | module-level `get_event_bus()` |
| Features | namespaces, wildcard patterns, SQLite `core_event_log` table, legacy EventBus bridge, in-memory deque(1000) | `EventPriority` classification (critical→ignore), asyncio+threading safe, persisted via `EventBusEntry`, priority map for ~30 event types |
| Singleton alias | `get_core_event_bus()` | `get_core_event_bus = get_event_bus` (line 313) |
| Size | 177 lines | 313 lines |

## Verified consumer split

**`core.events.event_bus` consumers** (the "core bus"):
- `api/routers/activity.py` — aggregates recent events for UI
- `cores/operations.py`, `cores/tool_registry.py`, `cores/secure_vault.py`,
  `cores/thinking_system.py`, `cores/memory.py`,
  `cores/platform_connectors/universal_connector(s).py`,
  `cores/notifications/event_bridge.py`, `core/setup/steps/test_step.py`,
  `core/cycles/events.py` docstring references

**`cores.events.event_bus` consumers** (the "main bus"):
- `api/lifespan.py`, `api/scheduler.py`, `api/routers/{findings,targets,system,auto_submit,mobile,mobile_approvals,system_state}.py`
- `cores/{commander,voice_interface,dashboard,discovery_engine,autonomy}.py`,
  `cores/investment/manager.py`, `cores/decision_journal/journal.py`,
  `cores/copilot/publisher.py`, `cores/offensive/publisher.py`,
  `cores/revenue{,_multiplier}/`, `cores/cycles/events.py`,
  `cores/evidence/composer.py`, `cores/ai_router/engine.py`,
  ~44 files total

Because the singleton names collide (`get_core_event_bus` exists in BOTH
modules but returns DIFFERENT buses), events published via
`core.events.event_bus.get_core_event_bus()` are **invisible** to
`cores.events.event_bus` subscribers and vice versa. Example risk:
`cores/memory.py` publishes on the core bus while `cores/dashboard.py`
subscribes on the cores bus — cross-subsystem events may silently drop.

## Problem

Two buses = split-brain eventing. Neither is a superset:

- cores bus has priority classification + async safety + wider adoption.
- core bus has namespaces/wildcards + `IEventBus` interface + legacy bridge
  + the `core_event_log` table that `activity.py` reads.

## Alternatives

### A. cores bus becomes canonical; core bus becomes adapter

Port namespace/persistence needs into `cores.events.event_bus`, then make
`core.events.event_bus` a thin facade delegating to it (keeping
`core_event_log` writes for `activity.py` or migrating that endpoint).
- Pros: single bus, keeps api contract, incremental migration.
- Cons: cores bus must gain namespace/wildcard + legacy-bridge features.

### B. core bus becomes canonical; migrate cores consumers

- Pros: core bus already implements `IEventBus` and has persistence table.
- Cons: 44+ consumers to migrate; loses priority engine unless ported;
  `cores.events` is where all new v12 code publishes.

### C. Event bridge/sync between buses

- Pros: zero consumer changes.
- Cons: doubles delivery, ordering hazards, still two sources of truth.
  Rejected except as temporary transition.

## Decision (proposed)

**Alternative A** — `cores.events.event_bus` is canonical (wider adoption,
priority engine, async-safe, all new code targets it). `core.events.event_bus`
becomes a compatibility facade that forwards `publish()`/`subscribe()` to the
cores bus while still writing `core_event_log` rows for `activity.py` until
that endpoint is migrated to the cores bus history API.

Prerequisites before execution:
1. This ADR accepted.
2. Feature-gap analysis: namespaces/wildcards + `IEventBus` methods used by
   core-bus consumers must exist or be shimmed in cores bus.
3. Execute inside the twin-tree consolidation worktree (ADR-0002) — bus merge
   is part of that codemod, not a standalone change.

## Consequences

- `api/routers/activity.py` needs a migration path off `core_event_log`.
- `tests/test_orion_core.py::TestCoreEventBus` tests the core bus directly —
  must keep passing via facade or be updated.
- Until merged: **rule for agents — publish system events on
  `cores.events.event_bus`; `core.events.event_bus` is legacy-compat only.**
