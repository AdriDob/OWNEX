# OWNEX Quality Gates (v1.0)

Commands every agent must run before declaring work done. Canonical debt/roadmap live in `.ai/` — this file defines the *gates*.

## Backend

```bash
.venv/bin/python -m ruff check <touched files>     # lint — must pass
.venv/bin/python -m ruff format <touched files>    # format
.venv/bin/python -m pytest <relevant test files> -x -q
python scripts/dev test          # full suite (excludes test_security.py)
python scripts/dev test-fast     # smoke subset
```

## Frontend

```bash
cd frontend
npx biome check <touched files>   # lint/format
npx vue-tsc --noEmit -p tsconfig.app.json   # typecheck (note: pre-existing errors in parallel WIP — check only touched files)
npx vite build                   # production build must pass
```

## Git

- Small atomic commits; never commit unrelated/parallel-session files.
- No force push, no history rewrite, no secrets.
- Push to `origin main` only when worktree state is understood (autostash for dirty parallel files is acceptable).

## Honesty gates (non-negotiable)

- No MOCK presented as real integration.
- No "connected/synced" claims without a real provider response.
- Financial actions require explicit human approval — always.
- UNKNOWN data scores neutral, never as compatible.
- Report PASS/FAIL/BLOCKED/NOT_TESTED honestly.

## Debt & decisions

- Register debt in `.ai/TECHNICAL_DEBT.md` / `.ai/KNOWN_DEBT.md` (canonical).
- Architecture decisions → `docs/architecture/decisions/` ADR or `.ai/DECISIONS.md`.
