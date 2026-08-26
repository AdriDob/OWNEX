# Release Checklist — OWNEX Alpha 1.0

> **Objetivo**: Confirmar que todos los criterios de release están cubiertos con evidencia.

## Architecture

| Item | Estado | Evidencia |
|---|---|---|
| API / Core como SSOT | ✅ | FastAPI monolito modular; EventBus unificado |
| Desktop canónico (Tauri v2) | ✅ | `src-tauri/`, convergencia 2026-08-24 |
| Mobile consolidado | ✅ | android/ APK + Companion pages |
| Watch via backend contract | ✅ | `/wear-os/*` endpoints vivos |
| Shared contracts (DTOs/enums/estados) | ✅ | `cores/work_taxonomy.py`, `core/execution_queue.py` |
| Backend authoritative | ✅ | Mobile/Watch consumen API, no inventan estado |

## Backend

| Item | Estado | Evidencia |
|---|---|---|
| Core flow discover→revenue | ✅ | `test_income_chain_e2e.py` 3/3 |
| Opportunity Engine | ✅ | `test_direct_work_engine.py` 35 passed |
| Work Bank | ✅ | `test_workbank.py` 21 passed |
| Application Assistant | ✅ | `test_application_assistant.py` 16 passed |
| Income Plan + Command Center | ✅ | `test_income_plan.py` 14 passed |
| Revenue ledger EXPECTED≠PENDING≠PAID | ✅ | Fix ghost money + E2E |
| Scheduler hardened | ✅ | Anti-overlap + flock + run ledger |
| Availability Intelligence | ✅ | `test_availability_engine.py` |
| Execution Queue v1 | 🟡 PARTIAL | State machine + store listo; wiring = 1.1 |
| Security (CORS/Auth/CSRF/Rate limit) | ✅ | 46 tests dedicados |

## Frontend

| Item | Estado | Evidencia |
|---|---|---|
| Typecheck | ✅ | `vue-tsc --noEmit` 0 errores |
| Unit tests | ✅ | `vitest run` 226 passed |
| Build | ✅ | `vite build` OK |
| Mission Control | ✅ | Good Morning panel + Direct Work Radar |
| Opportunity Radar | ✅ | `/direct-work/recommend` + Radar |
| Work Bank UI | ✅ | `/workbank` + `/deliver/pending` |
| Application Assistant | ✅ | Wizard 19 pasos + tracking |
| Income Home | ✅ | EXPECTED ≠ REALIZED band |
| Mobile pages | ✅ | MobileCompanion + Jarvis variant |
| Watch surface | ✅ | Consumida via `/wear-os/*` en Companion |

## Tauri (Desktop)

| Item | Estado | Evidencia |
|---|---|---|
| tauri.conf.json válido | ✅ | `cargo check` OK |
| Identifier/version | ✅ | `ai.rastro.app` / VERSION.txt sync |
| frontendDist | ✅ | `../frontend/dist` |
| externalBin sidecar | ✅ | `OWNEX-Backend.spec` ONEFILE |
| CSP dynamic ports | ✅ | `scripts/wsl/start_all.sh` |
| Icons/resources | ✅ | `assets/desktop/` |
| Permissions mínimo | ✅ | `allowlist` solo shell/fs necesarios |

## Revenue (Economic Engine)

| Item | Estado | Evidencia |
|---|---|---|
| EXPECTED / PENDING / PAID / FAILED separados | ✅ | `RevenueTracker._update_metrics` recompute |
| Ghost money eliminado | ✅ | `test_income_chain_e2e.py` |
| ACCEPTED no cuenta como cash | ✅ | `stage_from_payment_status` |
| Availability honesta | ✅ | UNKNOWN/STALE nunca inventan |
| HTROI / Confidence UNKNOWN-safe | ✅ | `test_economics_ssot.py` |
| Payment compatibility | ✅ | `test_payment_compat.py` 13 tests |
| Work Bank → Revenue pipeline | ✅ | E2E chain verify |

## Automation

| Item | Estado | Evidencia |
|---|---|---|
| Discover → Recommend → Work Bank | ✅ | E2E chain |
| Human gate (prepare ≠ deliver) | ✅ | `/deliver/prepare` + `/deliver/approve` |
| Execution Queue state machine | 🟡 v1 ready | `core/execution_queue.py` |
| Scheduler anti-overlap + ledger | ✅ | `core/scheduler/scheduler.py` |
| Availability-driven scoring | ✅ | `AvailabilityMonitor` → `TaskAvailability` |

## Critical E2E

| Flujo | Estado | Evidencia |
|---|---|---|
| Install → Launch → Health | 🟡 CI build pending | Tag push needed |
| Login → Dashboard → Data | ✅ | TestClient + auth |
| Discover → Score → Recommend | ✅ | `test_income_chain_e2e.py` |
| Select → Prepare → Human Gate | ✅ | WorkBank + deliver endpoints |
| Execute simulation → Result | ✅ | Approve → RevenueTracker PAID |
| Revenue recorded | ✅ | PAID counted, pending separate |
| Persistence (restart) | ✅ | Manual + income chain |
| Sync Desktop→Mobile→Watch | 🟡 Watch contract only | EventBus + `/wear-os/*` |
| Shutdown clean | ✅ | `OWNEX-Stop.ps1` + `stop_all.sh` |
| No orphan processes | ✅ | `setsid -w` + pkill guards |

## Packaging

| Item | Estado | Evidencia |
|---|---|---|
| Clean build from scratch | 🟡 CI pending | Tag → GitHub Actions |
| MSI/NSIS canonical | 🟡 CI pending | `OWNEX-Backend.spec` + `tauri build` |
| SHA256SUMS | 🟡 CI pending | Release artifact |
| Install Windows 11 | 🟡 Manual pending | User validates |
| Upgrade test (prev → 1.0) | 🟡 Manual pending | User validates |
| Uninstall clean | 🟡 Manual pending | User validates |
| SmartScreen behavior | 🟡 Manual pending | User validates |
| Paths `%LOCALAPPDATA%\OWNEX` | ✅ | `database/db.py:user_data_dir()` |

## Windows 11 + WSL Launcher

| Item | Estado | Evidencia |
|---|---|---|
| `OWNEX-Launcher.ps1` | ✅ | `scripts/win/OWNEX-Launcher.ps1` |
| `OWNEX-Stop.ps1` | ✅ | `scripts/win/OWNEX-Stop.ps1` |
| WSL `start_all.sh` | ✅ | E2E verified (UI 200 + API 200) |
| WSL `stop_all.sh` | ✅ | Clean shutdown |
| Health poll + timeout | ✅ | 120s max + log tail |
| UI open in browser | ✅ | `Start-Process $UiUrl` |
| CORS Tauri + WSL | ✅ | `configure_cors()` includes tauri origins |

## Security

| Item | Estado | Evidencia |
|---|---|---|
| CORS Tauri/WSL | ✅ | `api/main.py` configure_cors |
| Auth cookie httpOnly | ✅ | `ownex-session` |
| CSRF double-submit | ✅ | 17 tests |
| Rate limit per-identity | ✅ | 12 tests |
| Error handling 5xx | ✅ | `operation_id` + header |
| Secrets 0 in repo | ✅ | `.gitignore` + IdentityVault |
| Tauri permissions minimal | ✅ | `tauri.conf.json` allowlist |
| Path traversal | ✅ | Path resolved |

## Testing

| Suite | Estado | Evidencia |
|---|---|---|
| Backend fast | ✅ | 100/1 |
| Backend core income/workbank | ✅ | 214 passed |
| Backend full (excl flaky) | ✅ | 3706 passed |
| Frontend typecheck | ✅ | 0 errors |
| Frontend vitest | ✅ | 226 passed |
| Packaging guards | ✅ | 22 passed |
| Watch smoke | ✅ | 4/4 endpoints 200 |

## Documentation

| Archivo | Estado | Evidencia |
|---|---|---|
| FEATURE_COMPLETION_AUDIT.md | ✅ | 22 features con evidencia |
| RC_SIGNOFF.md | ✅ | Gates + métricas |
| DECISIONS.md | ✅ | Revenue metrics fix + zero-red |
| CHANGELOG.md | ✅ | Unreleased entries |
| CURRENT_STATE.md | ✅ | Session log Phase 1 |
| OWNEX_1_1_BACKLOG.md | ✅ | Capital OS + orthogonal |
| RELEASE_CHECKLIST.md | ✅ | Este archivo |

## Tri-Surface Decision Record

| Decisión | Justificación |
|---|---|
| Desktop = Tauri canónico | Convergencia 2026-08-24; pipeline único en tags v* |
| Mobile = android/ APK + Companion pages | android/ compila (ai.rastro.app); frontend pages consumen API real |
| Watch = solo backend contract (`/wear-os/*`) | AUD-14 descartó build WearOS (ROI negativo); contract vivo para Companion relay |
| Sync = EventBus + device identity | Supabase opcional; offline queue = 1.1 gap |

## Final Verdict

| Gate | Estado |
|---|---|
| Architecture | ✅ PASS |
| Backend | ✅ PASS |
| Frontend | ✅ PASS |
| Tauri | ✅ PASS |
| Revenue | ✅ PASS |
| Automation | ✅ PASS |
| Security | ✅ PASS |
| Testing | ✅ PASS |
| Packaging | 🟡 CI BUILD PENDING |
| Windows | 🟡 MANUAL VALIDATION PENDING |
| Persistence | ✅ PASS |
| Documentation | ✅ PASS |
| 24h Stability | 🟡 PENDING (requires Windows) |

**OVERALL**: **RC READY FOR HARDENING** — All automated gates pass. Physical Windows validation + 24h soak remaining for FINAL RELEASE GATE.