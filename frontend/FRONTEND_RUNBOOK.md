# OWNEX Frontend — Runbook (App Shell V2.1 finalization)

> Scope: `frontend/` only. Backend contract unchanged. Last verified: 2026-11-23.

## What changed (this session)

| File | Change |
|---|---|
| `src/components/layout/AppLayout.vue` | Real `<router-view>` inside `ErrorBoundary` + `Transition`; removed duplicated notification toolbar (moved into `TitleBar`); emit renamed to kebab-case `toggle-copilot`; `prefers-reduced-motion` support; `overflow-hidden` on main + inner scroll container |
| `src/components/layout/AppSidebar.vue` | App Shell V2.1 — 8 sections (Command Center, Opportunities, Work Bank, Engineering Factory, Investment Hub, Financial Hub, Integrations, Settings); all sections expanded by default; `bg-background/80` instead of `bg-deep/80` |
| `src/design/tokens.css` | `:root { }` wrapper restored — custom properties were leaking to `:root`-less scope and breaking theme vars |
| `tauri.config.json` | Deleted — obsolete Tauri v1 config, 0 references (see `.ai/KNOWN_DEBT.md` in economy worktree) |
| `qa/` | Playwright capture/dom-check/debug scripts + screenshot baselines |

No routes were removed — every existing path remains reachable; the sidebar is a curated entry-point layer.

## Verify

```bash
cd frontend
npm run dev          # vite dev server :5173 (proxies /api → :8000)
npm run lint         # biome check src/
npm test             # vitest run — 226 tests
npm run build        # vite build → dist/
```

Backend must be up for authenticated flows: `python run.py` or the systemd `ownex-backend` service (`:8000`).

## QA visual captures

```bash
# Unauthenticated baseline (public routes only)
node qa/capture.cjs http://localhost:5173 qa/screenshots

# Authenticated captures — needs a session token (localStorage key: CATEYE-token)
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/users/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"<user>" ,"password":"<pass>"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['session']['token'])")
QA_TOKEN="$TOKEN" node qa/capture.cjs http://localhost:5173 qa/screenshots-auth
```

Outputs: `qa/screenshots{,-auth}/<route>-<viewport>.png` + `capture-report.json` (console errors, pageerrors, failed requests per route/viewport).

DOM smoke check (text length, nav items, h1) without screenshots:

```bash
node qa/dom-check.cjs /,/operations/work-queue,/capital
```

## Known issues / honest status

- Unauthenticated captures show expected `401`s on `/api/*` calls — not defects.
- `capture-report.json` (unauth baseline) recorded one `PAGEERROR: Cannot read properties of undefined (reading 'name')` on a satellite route — re-check on next capture run; if it persists, bisect with `qa/debug-errors.cjs`.
- `src/design/OWNEX_DesignSystem.md` is the single design-system reference (tracked). The older `OWNEX_Design_System_Documentation.md` duplicate was deleted, and the unused `src/components/health/` + `ui/LoadingSkeleton.vue` additions were removed in favour of `pages/HealthCenter.vue` and `ui/Skeleton.vue`.
