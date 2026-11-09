# RELEASE_BRANCH_RECONCILIATION — `release/win11-stable` vs `main`

Audit date: 2026-11-09 · merge-base: `898dcc7f` (2026-09-01)

## Divergence (verified)

| Metric | Value |
|---|---|
| Commits exclusive to `main` | 59 |
| Commits exclusive to `release/win11-stable` | 251 |
| Last stable commit | `5ce8866b` (2026-10-28) — "merge: integrate 248 commits + our fixes" |
| Diff size | ~2,780 files, +247k/−152k lines |
| Stable-exclusive areas | `cores/` 921, `core/` 470, `frontend/` 449, `tests/` 306, `api/` 163, `apps/` 44, `android/` 29 |

Note: the `work/ownex-economy-active-earn` gitlink points at `5ce8866b` —
the stable tip. That worktree IS the stable line's checkout.

## What each side owns

**`main` (59 exclusive)**: V12 product work — financial connections
(IOL/PPI/Binance), remote-job matcher + feeds, income plan, MCP server,
governance docs, twin-tree audit, npm security fixes, frontend Discovery/
auth repairs. Product-forward, no Windows packaging focus.

**`release/win11-stable` (251 exclusive)**: Windows release engineering —
`build_desktop.py` contract alignment, Windows packaging chain repair
(8 defects), WSL path fixes, real Windows build CI evidence, health-system
API, session autoguardado, Vitest updates, Biome fix, dependency security
patches, UI violet accent. Last activity 2026-10-28 — predates all V12 work.

## Assessment

- The branches are **product-line divergent**, not merely behind: stable has
  ~251 commits of release/platform work that main lacks entirely (Windows
  installer chain, health API, session manager, android/ apps dir).
- Merging stable→main wholesale would import a parallel product state and
  almost certainly conflict across `core/`+`cores/` (the exact twin-tree
  problem, worse).
- Merging main→stable would import V12 features without Windows validation.

## Recommended strategy (no destructive action taken)

1. **Keep `release/win11-stable` frozen** as the last verified Windows build.
2. If a new Windows release is needed: branch `release/win11-stable-v2`
   FROM `main`, then **cherry-pick only the packaging/build commits**
   (`d5f8e389`, `9a9c912d`, `a8478d10`, `c1a36c7d`, `b52b99f4`, `a6ad9ae6`)
   after auditing each diff — they are the durable value.
3. Product features unique to stable (health API, session manager, android/)
   need individual porting decisions — several may already exist in evolved
   form on main (e.g. `cores/system/health*`, auth sessions).
4. Do NOT delete or rewrite the stable branch; its 251 commits are the only
   record of the Windows build knowledge.

## Blockers

- No Windows toolchain/SDK in this environment → cannot verify any build.
- 251-commit audit is a dedicated task, not a single session.
