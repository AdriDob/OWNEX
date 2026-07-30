# TECH DEBT — OWNEX OMEGA v7.0

**Technical debt with evidence, not estimates. Updated per session.**

---

## Active Debt (Must Fix Before Release)

| ID | Debt | Evidence | Effort | Blocker |
|----|------|----------|--------|---------|
| ~~TD-01~~ | ~~Security Cycle test fails~~ | ~~`tests/test_security_cycle.py:16` expects `category=="security"`, core creates `"offensive"`~~ | ~~10 min~~ | **✅ FIXED 2026-07-30** |
| TD-02 | Scheduler no Security Cycle bootstrap | `api/scheduler.py` has 10 stages, no security cycle init | 30 min | Sprint 1 |
| TD-03 | GamingConsole hardcoded fake data | `frontend/src/pages/GamingConsole.vue:39-48` `activityLog = [...]` | 20 min | Sprint 1 |
| TD-04 | Desktop never built | `src-tauri/` exists, `npm run tauri build` untested | 30-60 min | Sprint 2 |
| TD-05 | 216 modified files uncommitted | `git status --short` shows 216 M + 50 ?? | 2 hrs | — |
| TD-06 | No CI/CD pipeline | No `.github/workflows/`, no `.gitlab-ci.yml` | 1 hr | — |

---

## Structural Debt (Refactor When Time)

| ID | Debt | Evidence | Effort | Risk |
|----|------|----------|--------|------|
| TD-07 | Monolithic FastAPI process | All cores imported in `api/main.py`, single uvicorn | 2-3 days | Medium |
| TD-08 | In-memory EventBus | `cores/events/event_bus.py` dict-based, no persistence | 1-2 days | High |
| TD-09 | Scheduler stages hardcoded | `STAGE_INTERVALS` dict in `api/scheduler.py`, not pluggable | 1 day | Medium |
| TD-10 | Config scattered | `~/.orion/config.sh`, `~/.bashrc`, `cores/env/config.py`, `.env` | 4 hrs | Low |
| TD-11 | Agents import EventBus directly | `cores/agents/*.py` → `from cores.events.event_bus import get_event_bus` | 1 day | Medium |
| TD-12 | No feature flags | All features always on | 2 days | Low |
| TD-13 | Single-process scheduler | No distributed lock, no HA | 2-3 days | High |
| TD-14 | SQLite only in dev | PostgreSQL models exist but untested | 4 hrs | Medium |

---

## Code Quality Debt (Ruff Clean)

| ID | Debt | Evidence | Count |
|----|------|----------|-------|
| TD-15 | Bare `except:` clauses | FASE_6 fixed 32, but more may exist | ~10 |
| TD-16 | Unused imports | FASE_21 fixed 12 Ruff SIM114/B007/B024 | ~5 |
| TD-17 | `create_task` not tracked | FASE_6 fixed 3 orphans, more possible | ~3 |
| TD-18 | `ensure_future` without error handling | FASE_6 added logging, may need more | ~5 |
| TD-19 | `open()` without `with` | FASE_6 fixed 1 in auth, more possible | ~3 |

---

## Testing Debt

| ID | Debt | Evidence | Priority |
|----|------|----------|----------|
| TD-20 | No scheduler E2E test | Pipeline stages tested individually, not full cycle | High |
| TD-21 | No desktop smoke test | Build never run | High |
| TD-22 | No WebSocket terminal test | `api/terminal_ws.py` untested | Medium |
| TD-23 | No extension load stress test | `verify_extensions.py` only validates structure | Low |
| TD-24 | No evolution proposal test | `core/evolution/` has 0 tests | Low |
| TD-25 | No multi-agent race test | Agents share EventBus, no coordination test | Medium |

---

## Documentation Debt (This System Fixes)

| ID | Debt | Evidence | Fixed By |
|----|------|----------|----------|
| TD-26 | TASK_QUEUE.md was 291 chars stale | Rewritten 2026-07-30 | ✅ This session |
| TD-27 | ROADMAP.md was 288 chars high-level | Rewritten 2026-07-30 | ✅ This session |
| TD-28 | No ARCHITECTURE.md | Created 2026-07-30 | ✅ This session |
| TD-29 | No MODULE_INDEX.md | Created 2026-07-30 | ✅ This session |
| TD-30 | No DECISIONS.md | Created 2026-07-30 | ✅ This session |
| TD-31 | No KNOWN_LIMITATIONS.md | Created 2026-07-30 | ✅ This session |
| TD-32 | No PROGRESS.md | Creating this session | ✅ This session |
| TD-33 | No SESSION_HISTORY.md | Creating this session | ✅ This session |
| TD-34 | No NEXT_PRIORITIES.md | Creating this session | ✅ This session |
| TD-35 | No CHANGELOG.md | Creating this session | ✅ This session |

---

## Dependency Debt

| Dependency | Version | Risk | Action |
|------------|---------|------|--------|
| FastAPI | 0.115+ | Low | Pin in requirements |
| Vue | 3.4+ | Low | Pin in package.json |
| Tauri | 2.0 | Medium | Build test first |
| Rust | 1.97.0 | Low | Stable |
| Python | 3.14.4 | **High** | Pre-release! Downgrade to 3.11/3.12 for prod |
| SQLite | 3.45+ | Low | WAL mode OK |
| SQLAlchemy | 2.0+ | Low | Async OK |

**Critical:** Python 3.14.4 is pre-release. Production must use 3.11 or 3.12.

---

## Debt Paydown Strategy

| Sprint | Focus | Debt IDs |
|--------|-------|----------|
| **Sprint 1** (Now) | Security Cycle E2E + GamingConsole + AgentFleet | TD-02, TD-03, TD-05 (partial) |
| **Sprint 2** | Desktop Release | TD-04, TD-05 (partial) |
| **Sprint 3** | Repo Hygiene + CI/CD | TD-05, TD-06 |
| **Sprint 4** | Config + Feature Flags | TD-10, TD-12 |
| **Sprint 5** | EventBus + Scheduler Decoupling | TD-08, TD-09 |
| **Sprint 6** | Agent Isolation + HA | TD-07, TD-11, TD-13 |
| **Ongoing** | Ruff clean + Test coverage | TD-15 to TD-25 |

---

## Debt That Is NOT Debt (Intentional)

| Item | Why It's Fine |
|------|---------------|
| 13 extensions not integrated | Revenue Rule gate — correctly deferred |
| 9 evolution modules stubbed | Infrastructure investment, not product |
| No mobile app | ORION vision, separate from OWNEX core |
| No crypto/trading bots | Separate revenue streams, evaluated separately |
| Python 3.14 in dev | Bleeding edge for local only, prod pins 3.11 |
| Forge/Pulse cycles not built | OMEGA architecture - Sprint 4/5 |
| 12 OMEGA agents not created | Sprint 6 |
| Self-Repair not built | Sprint 7 |
| Post-Cycle Learning not built | Sprint 7 |