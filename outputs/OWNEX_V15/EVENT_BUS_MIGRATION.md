# EVENT_BUS_MIGRATION — OWNEX V15

**Date:** 2026-11-09 · **Status:** AUDITED — migration NOT yet executed
**Related:** `docs/architecture/decisions/0003-dual-event-buses.md`, ADR-0002 v2

## 1. Evidence (corrects ADR-0003's premise)

ADR-0003 assumed two independent buses with `get_core_event_bus` resolving to
different objects. The real picture is worse and better than that:

### The alias trap

`cores/events/event_bus.py:313` contains:

```python
get_core_event_bus = get_event_bus
```

So `from cores.events.event_bus import get_core_event_bus` returns the **cores
`EventBus` singleton** — while `from core.events.event_bus import
get_core_event_bus` (or `core.events`) returns the **`CoreEventBus`
singleton**. The same symbol name resolves to two different objects depending
on import path. ~40 call sites use the cores alias; ~10 use the real
`CoreEventBus`.

### The two implementations are NOT equivalent

| Capability | `core.events.CoreEventBus` (177 LOC) | `cores.events.EventBus` (313 LOC) |
|---|---|---|
| Singleton getter | `get_core_event_bus()` (real) | `get_event_bus()`; `get_core_event_bus` = alias |
| Namespaces `app:event` | ✅ `app_event()`, `subscribe_app()` | ❌ |
| Wildcards `prefix:*` | ✅ `_match()` | ❌ exact-match only |
| `subscribe()` return | unsubscribe callable | `None` (has `unsubscribe()`) |
| Async handlers | ❌ | ✅ `subscribe_async` + loop dispatch |
| Thread safety | ❌ no lock | ✅ `threading.Lock` |
| Priority engine | ❌ | ✅ `EventPriority` + `classify_event` + `priority_engine.ingest_*` |
| In-memory history | deque, `get_history(app_id, limit)` | list[500] |
| Persistence | own `_PERSIST_BASE` → `orion_core.db` → table `core_event_log` | `database.models.EventBusEntry` → main DB → `event_bus_history` |
| Bridge | ✅ `_bridge_to_legacy()` → publishes to cores bus (one-way) | ❌ no reverse bridge |
| Consumers | `api/routers/activity.py`, `cores/{operations,tool_registry,secure_vault,thinking_system,memory,platform_connectors/universal_connectors,notifications/event_bridge}.py`, `core/setup/steps/test_step.py`, `tests/test_orion_core.py` | ~100 call sites across `core/`, `cores/`, `api/` |

`core/events/{types,store,correlation}.py` are **byte-identical** to
`cores/events/` counterparts — only `event_bus.py` and `__init__.py` diverge.
`core/events/__init__.py` already re-exports `cores.events.store/types` —
the trees are partially merged here already.

### Consequence (event loss, confirmed by code reading)

- Publish on `CoreEventBus` → auto-bridged to cores bus ✅ (subscribers on
  both sides receive it — but **cores subscribers get it without priority
  classification applied at publish time**; classification happens inside
  cores `publish()`, so bridged events DO get classified — ok).
- Publish on cores `EventBus` → **never reaches `CoreEventBus` subscribers**
  ❌. `api/routers/activity.py` reads `CoreEventBus.get_history()` → the
  Mission Control activity feed misses every event published through the
  ~100 cores-bus call sites (the majority).
- Dual persistence: `core_event_log` (orion_core.db) vs `event_bus_history`
  (main DB) — two audit trails, neither complete.

## 2. Migration plan (canonical = cores.events.EventBus, extended)

Rationale for cores canonical (matches ADR-0003): it already has priority
classification, async handlers, thread lock, and the larger consumer base.
It must be **extended**, not replaced — the CoreEventBus API surface is
richer in namespaces/wildcards/history.

### Phase E1 — extend cores bus (additive, no breakage)

1. Add wildcard subscription: `subscribe("app:*", handler)` — dispatch on
   `event_type.startswith(prefix)`; keep exact-match fast path.
2. Add `subscribe_app(app_id, handler)` + `app_event(app_id, event)` helpers.
3. Add `get_history(app_id=None, limit=100)` returning records shaped like
   CoreEventBus history (`{"event","data","timestamp","app_id"}`) so
   `api/routers/activity.py` keeps working unchanged.
4. Keep `subscribe_async`, priority map, `EventBusEntry` persistence as-is.

### Phase E2 — facade `core.events.event_bus`

Replace `CoreEventBus` internals with a facade over `cores.events.get_event_bus()`:

- `publish(event, app_id=?, **data)` → normalize to `event_type` (+`app_id`
  in payload), call cores `publish()`.
- `subscribe(event, handler)` → wildcard-aware subscribe on cores bus;
  return unsubscribe callable (cores `subscribe` currently returns `None` —
  Phase E1 must make it return one).
- `get_history(app_id, limit)` → delegate to cores `get_history`.
- `disable_persistence/disable_bridge/enable_bridge` → no-ops or mapped to
  cores equivalents (bridge becomes unnecessary — single bus).
- `clear()` → cores equivalent.
- **Remove `_bridge_to_legacy`** — with one bus it would double-publish.
- Keep `get_core_event_bus()` name in `core.events` returning the facade so
  all 10 CoreEventBus consumers keep working with zero changes.

### Phase E3 — alias cleanup (optional, cosmetic)

`cores/events/event_bus.py:313 get_core_event_bus = get_event_bus` keeps
working (it IS the canonical bus). Optionally deprecate the alias name in
favor of `get_event_bus` in new code; do NOT mass-rewrite 40 call sites —
the alias is harmless once both resolve to the same object.

### Phase E4 — persistence reconciliation

- Canonical history: `event_bus_history` (main DB, `EventBusEntry`).
- `core_event_log` in `orion_core.db`: stop writing; keep table for
  historical reads. `api/routers/activity.py` uses in-memory history only —
  verify no reader queries `core_event_log` directly
  (`grep -rn "core_event_log" --include="*.py"` → only `core/events/`).
- Migration of old `core_event_log` rows into `event_bus_history`: optional,
  low value (dev DB) — document as skipped unless production data exists.

## 3. Mandatory tests (per V15 §2)

New file `tests/test_event_bus_unification.py`:

- [ ] publish via `core.events.get_core_event_bus()` → received by
      `cores.events.get_event_bus().subscribe()` handler (cross-tree).
- [ ] publish via cores bus → received by `core.events` facade subscriber.
- [ ] wildcard `subscribe("cycle:*", h)` receives `cycle.created`,
      `cycle.updated`, not `other:x`.
- [ ] `subscribe_app("opportunity", h)` receives `opportunity:found`.
- [ ] priority classification still applied (`system:error` → critical,
      reaches priority_engine ingest path without error).
- [ ] async handler (`subscribe_async`) fires on publish.
- [ ] persistence: published event appears in `EventBusEntry` /
      `get_history()`.
- [ ] no duplicate delivery: one publish → handler called exactly once
      (guards against facade+bridge double-publish).
- [ ] unsubscribe callable removes handler.
- [ ] legacy import paths still work: `from core.events import
      get_core_event_bus`, `from cores.events.event_bus import
      get_event_bus`, `from cores.events.event_bus import
      get_core_event_bus` — all functional.

Existing `tests/test_orion_core.py::TestCoreEventBus` must keep passing
(singleton identity, subscribe/publish) against the facade.

## 4. Risks

- `CoreEventBus.publish` signature `(event, app_id=None, **data)` vs cores
  `(event_type, **payload)` — facade must not leak `app_id` into payload
  keys consumers don't expect; store it in history record only.
- `get_history` record shape differs (`data` vs `payload`) — facade maps.
- `api/routers/activity.py` `_classify` expects `rec["event"]` /
  `rec["data"]` / `rec["timestamp"]` — preserve exactly.
- Priority `ignore` events: cores bus drops them post-persist — facade
  subscribers on ignored types won't fire; acceptable (matches cores
  semantics) but document.
- Do NOT touch `core/cores/` quarantine or `work/ownex-economy-active-earn`.

## 5. Status

- [x] Producer/consumer audit (this doc)
- [x] API diff documented
- [x] Canonical choice justified (cores + extension)
- [x] Phase E1 implemented: wildcard patterns (`app:*`, `*`), `subscribe`/
      `subscribe_async` return unsubscribe callables, `subscribe_app`/
      `app_event` helpers, `get_history(app_id=)` filter — all in
      `cores/events/event_bus.py`
- [x] Phase E2 implemented: `core/events/event_bus.py` rewritten as
      `CoreEventBus` facade over canonical bus (namespaces, wildcards,
      `app_id` history shape preserved; `_bridge_to_legacy` and
      `core_event_log` writes removed — single bus, no double-publish);
      `get_event_bus` alias exported fixing latent ImportError in
      `cores/platform_connectors/universal_connector.py`
- [x] Phase E3: `get_core_event_bus = get_event_bus` alias kept (harmless —
      both names now resolve to the same canonical singleton)
- [x] Phase E4: `core_event_log` writes stopped; table left in place for
      historical data; `event_bus_history` is the single audit trail
- [x] Tests: `tests/test_event_bus_unification.py` (15 tests — cross-tree
      delivery both directions, wildcards, namespaces, no-dup, unsubscribe,
      persistence/history, legacy imports, async) — all pass;
      `test_orion_core.py` + event-related subset (298 tests) green
- [ ] `api/routers/activity.py` end-to-end verification against running
      backend (unit-level covered by history-shape tests)
