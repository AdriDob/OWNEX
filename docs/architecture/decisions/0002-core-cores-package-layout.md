# ADR 0002 — Target package layout for `core/` + `cores/` consolidation

- Status: PROPOSED (v2 — corrected 2026-11-09 after V15 audit feedback)
- Date: 2026-11-09
- Deciders: pending user/architect review
- Related: `docs/architecture/TWIN_TREE_AUDIT.md`, `TWIN_TREE_IMPORTERS.txt`,
  `.ai/OWNEX_DUPLICATION_CONSOLIDATION.md`, TD-01, V15 spec §1
- Supersedes: v1 of this ADR ("everything → `cores/`")

## Context

`core/` (708 files) and `cores/` (1108 files) are one tangled system, not two
parallel trees: 317 `cores/` files import `core.*`, 94 `core/` files import
`cores.*`. `core/engine/` is the de-facto base library extended by
`cores/engine/`. `api/` consumes `cores.*` for infra but `core.scheduler.*`
for scheduling. 115 same-path files have divergent content.

**v1 error**: it proposed absorbing ALL of `core/` into `cores/`. The importer
evidence in `.ai/OWNEX_DUPLICATION_CONSOLIDATION.md` contradicts that:
`core/` DOMINATES ~20 domains (`database` 44·0, `extension` 37·0,
`credentials` 77·7, `copilot` 62·5, `opportunity` 154·67, `cycles` 35·12,
`investment` 24·1, `decision_journal` 17·1, `polymarket` 31·0, `sensors`,
`reports`, `trading`, `autonomy`, `capabilities`…). Forcing those into
`cores/` would rewrite the majority of their consumers — backwards migration.

## Problem

Two top-level packages for one domain cause: agents editing the wrong copy,
divergent duplicates of infra (two live event buses), silent singleton
splits (verified: `database.manager` module-level `_manager` produced two
instances and broke `get_session("cycles")` when imports were mixed), and
blocked refactors.

## Decision (proposed, corrected)

**Domain-based bidirectional consolidation — NOT a global rename.**

For each domain, the side with dominant external consumers + functional
superiority is canonical (per `OWNEX_DUPLICATION_CONSOLIDATION.md` SSOT table
and the 12-criteria comparison). Identical files are absorbed toward THEIR
domain's canonical side — which may be `core/` for ~20 domains and `cores/`
for the rest. Divergent files are adjudicated per-file; never deleted on
name similarity.

Execution order (safe → risky):

1. **Phase 0 (done)**: importer matrix + this ADR correction.
2. **Phase 1 (in progress, worktree `agent/twin-tree-consolidation`)**:
   conservative codemod `scripts/codemod_twin_tree.py` absorbing ONLY
   byte-identical modules whose ENTIRE package chain is untainted (no
   divergent sibling), importable under `cores/` (no namespace shadowing),
   stateless (no module-level singletons/registries), and not referenced
   inside surviving `core/` files. `core/` internals are never rewritten —
   `cores/*/__init__.py` eagerly imports `core.*`, so intra-`core/` rewrites
   create circular imports. Verified: 4517 tests pass, 0 failures
   (4 env-dependent deselects: missing `frontend/dist`, worktree dir name).
3. **Phase 2**: per-domain adjudication of the 115 divergent files
   (scheduler stays `core/`-canonical; `cores/` gets a compat path).
4. **Phase 3**: domain-by-domain import migration with re-export shims,
   tests per domain, then removal of losing copies.
5. **Phase 4**: `core/` survives ONLY for domains where it is canonical;
   evaluate whether a final rename is even desirable (may legitimately be
   a permanent mixed layout documented here).

## Hard rules discovered during Phase-1 verification

- **Singleton/stateful modules can never be split** across trees
  (`database.manager`, both event buses, registries). They require a single
  canonical path + facade, per ADR-0003.
- **Divergent package `__init__.py` taints the whole subtree**: rewriting
  `core.PKG.sub` → `cores.PKG.sub` activates `cores`' divergent `__init__`
  while other consumers still load `core`'s — mixing two implementations
  (verified: duplicate `kyc_records` SQLAlchemy table).
- **Namespace shadowing**: `cores/autonomy.py` shadows `cores/autonomy/`
  (no `__init__.py`) — modules under it are unimportable as `cores.*`.
- **`core/` internals stay untouched** until `cores/*/__init__.py` eager
  cross-imports are made lazy or redirected.

## Consequences

- Phase 1 deletes far fewer files than the naive 306 — by design. Safety
  over cosmetic consolidation.
- Domains dominated by `core/` may keep `core/` permanently; the end state
  is "one canonical implementation per responsibility", not "one folder".
- ADR-0003 (event buses) remains a prerequisite for any `events/` merge.
- `.ai/`, `AGENTS.md`, `CANONICAL_COMPONENTS.md` must be updated when each
  domain phase lands.

## Modules affected

Repo-wide: `core/`, `cores/`, `api/`, `scripts/`, `tests/`, `extensions/`,
`desktop/` sidecar imports.
