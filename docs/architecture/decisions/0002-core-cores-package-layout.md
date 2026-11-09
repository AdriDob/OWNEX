# ADR 0002 — Target package layout for `core/` + `cores/` consolidation

- Status: PROPOSED
- Date: 2026-11-09
- Deciders: pending user/architect review
- Related: `docs/architecture/TWIN_TREE_AUDIT.md`, `TWIN_TREE_IMPORTERS.txt`, TD-01

## Context

`core/` (708 files) and `cores/` (1108 files) are one tangled system, not two
parallel trees: 317 `cores/` files import `core.*`, 94 `core/` files import
`cores.*`. `core/engine/` is the de-facto base library extended by
`cores/engine/`. `api/` consumes `cores.*` for infra but `core.scheduler.*`
for scheduling. 115 same-path files have divergent content.

## Problem

Two top-level packages for one domain cause: agents editing the wrong copy,
divergent duplicates of infra (two live event buses), and blocked refactors.

## Alternatives considered

### A. Everything → `cores/` (rename `core/` into `cores/`)

- Pros: `cores/` is larger (1108 vs 708), already the api-facing infra owner,
  naming already plural/canonical in most new code (connections, brokers,
  opportunity feeds).
- Cons: `core/` owns scheduler, engine base, investment, copilot, cycles —
  large rename surface; `core.scheduler` has deep internal imports.

### B. Everything → `core/` (rename `cores/` into `core/`)

- Pros: `core/` owns the engine base + scheduler; shorter name.
- Cons: `api/` + most infra already import `cores.*` — would rewrite the
  majority of consumers; `cores/` is the growing tree (all v12 work lives there).

### C. Keep both, freeze boundary (status quo + rules)

- Pros: zero migration risk.
- Cons: divergence continues; two event buses; every new module must pick a
  side arbitrarily. Rejected as permanent state, acceptable as transition.

### D. Phased: adjudicate divergent files first, then single codemod

- Keep both trees during adjudication; for each of the 115 divergent files
  pick canonical per `TWIN_TREE_IMPORTERS.txt` ext-counts + 12-criteria
  comparison; then ONE mechanical rewrite of all `core.X` → target.

## Decision (proposed)

**Alternative D with target = `cores/`** — i.e. `core/` is absorbed into
`cores/` over phases:

1. Phase A (this audit): importer matrix — DONE.
2. Phase B: per-file adjudication of the 115 divergent paths; where `core/`
   wins (scheduler, engine base, investment, copilot, cycles, health engine),
   the canonical content MOVES to `cores/` and `core/` path becomes a thin
   re-export shim temporarily.
3. Phase C: mechanical codemod rewriting all `core.*` imports → `cores.*`
   (including intra-`core/` imports), executed in dedicated worktree.
4. Phase D: delete `core/` tree; full pytest + build; ADR updated to ACCEPTED.

Rationale: `cores/` already owns the api surface and all v12+ work; making it
the single package avoids re-rewriting the newest code. `core/`'s unique
assets (scheduler, engine base) move INTO `cores/` rather than the reverse.

## Consequences

- ~400+ files touched by codemod — must be mechanical, reviewed, tested.
- Temporary compat shims (`core/X.py` → `from cores.X import *`) ease
  transition for stragglers like `api/routers/activity.py`.
- Dual event buses (`core.events.event_bus` vs `cores.events.event_bus`)
  require their own ADR before merge — they are different implementations,
  not copies.
- `.ai/`, `AGENTS.md`, `CANONICAL_COMPONENTS.md` must be updated when accepted.

## Modules affected

Repo-wide: `core/`, `cores/`, `api/`, `scripts/`, `tests/`, `extensions/`,
`desktop/` sidecar imports.
