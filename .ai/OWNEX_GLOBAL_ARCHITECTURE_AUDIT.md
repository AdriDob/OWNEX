# OWNEX Global Architecture Audit v10

**Fecha:** 2026-11-09
**Estado:** AUDIT v10 — evidencia medida (corrige borrador stale previo)
**Método:** graft repo map, `api/main.py` `include_router`, `frontend/src/router/index.ts`, conteo de imports `core.`/`cores.`, lecturas dirigidas de auth/frontend/backend.

---

## 1. FRONTEND — estado verificado

- **Canónico único:** `frontend/` (Vue 3 + TS + Vite + Tailwind v4). No crear segundo frontend.
- **`work/ownex-economy-active-earn`:** es un **gitlink** (`mode 160000`, commit `5ce8866b`) con su propio `git status` sucio (muchos `M`). Es un **worktree/check-out separado**, no parte del frontend canónico. **No borrar ni mergear sin decisión del owner.**
- **Router actual** (`frontend/src/router/index.ts`):
  - `/` = `CommandCenter.vue` (entry point único). `/income-home`, `/dashboard`, `/classic`, `/home`, `/welcome` redirigen a `/`.
  - 8 secciones: Command Center, Intelligence, Targets, Reports, Capital, Operations, Integrations, Copilot.
  - **Fuera de las 8 secciones** (rutas top-level): `/investments`, `/atlas/`, `/odyssey/`, `/aegis/`, `/polymarket`, `/trading`, `/trading/intelligence`, `/terminal`, `/baby-mode`, `/profile-kit`, `/knowledge`, `/quick-capture` (sin `component`), `/merlin`, `/chat`, `/work/:id`, `/revenue/center`, `/ai`, `/risk`.
  - **Fix aplicado:** `/home` estaba definido dos veces con destinos distintos (`/` y `/dashboard`); se eliminó el duplicado muerto. Biome OK.
- **Auth store** (`frontend/src/stores/auth.ts`): usa `/auth/users/login|register` (OWNEX account) y `/auth/login` (device autoLogin). `resolveApiUrl` antepone `/api` salvo `/direct-work`, `/mobile`, `/wear-os`.
- **P0 corregido:** el store enviaba `email`/`display_name` y esperaba `session.token`+`user`; `auth_users.py` exigía `username` y devolvía `access_token`. Ver §3.

## 2. BACKEND — estado verificado

- **Routers montados:** ~150 `app.include_router(...)` en `api/main.py` (accounts_hub, activity, agenda, agent_coordinator, agents_router, ai_security, alerts, assistant, atlas_app, atlas_cycle, attack, attack_surface, auth, auth_user, auth_users, authhub, auto_apply, auto_submit, bank_payout, bounty_pipeline, canonical, capability_expansion, career, commands, connections, contracts, control, copilot, credentials_rotation, crypto, cycles, daily, daily_digest, daily_mode, decision, device, devin, differential_intelligence, digest, direct_work, discovery, dispute, economic, endpoints, enhanced_personalization, evidence, evolution, execution, execution_queue, files, finance, financial_sync, financial_truth, findings, fiverr, forge_app, forge_cycle, hunt, hunter, hypotheses, identity, identity_center, idor, infinite_sources, intel, intelligence, investigations, investment, knowledge_bridge, license, life, life_management, market_intelligence, mercenary_filter, merlin, micro, mission, mobile, mobile_approvals, modes, notifications, oar, obsidian_sync, offensive, offensive_web3, onboarding, opensource, operations, opportunities, opportunity_feedback, opportunity_intelligence, opportunity_score, orchestrator, orion, orion_cli, osint, outlook, overview, payment_compat, personal_infrastructure, pipeline, platforms, productivity, profile_kit, progressive_scaling, project_dashboard, pulse_app, pulse_cycle, qa_cycle, quick_wins, recon, remote_control, report_pipeline, reports, reports_acceptance, reports_quality, result_based, revenue, revenue_app, revenue_multiplier, revenue_timeline, roi, sandbox, scans, screenshots, security_cycle, self_improvement, settings_ai, settings_runtime, settings_unified, setup, stability, supabase, sync, system, system_state, target_identity, targets, telegram_bot, terminal_ws, trading, ultra_fast_income, validation, vault_app, vault_cycle, verdicts, version, version_backup, voice, voice_commands, wear_os, webhooks, ws, zap, zero_barrier).
- **Imports mezclados:** en `api/` hay `from cores.*` ≈ 475 y `from core.*` ≈ 379. No hay un único árbol; la consolidación debe ser por dominio, no global.
- **Tamaños medidos:** `core/` = 1788 `.py`, `cores/` = 1089 `.py`, `core/cores/` = 1089 `.py` (untracked, copia casi idéntica de `cores/`).

## 3. AUTH / IDENTITY / CONNECTIONS — auditoría

| Pieza | Path | Rol real | Estado |
|---|---|---|---|
| OWNEX Account (user/pass) | `api/routers/auth_users.py` → `/api/auth/users/*` | Registro/login/refresh/me/logout, PBKDF2, email verify, cookie+Bearer | **CANÓNICO** (frontend lo usa) |
| Device session | `api/routers/auth.py` → `/api/auth/*` | `device_id` login, refresh, `/me`, devices, secure-token | **CANÓNICO** para autoLogin/sesión local |
| Legacy user auth | `api/routers/auth_user.py` → `/auth/*` | email/password vía `cores.auth.user_auth` | **P1 duplicado/legacy**: prefijo `/auth` sin `/api`; `resolveApiUrl` no lo root-mountea (solo `/direct-work`,`/mobile`,`/wear-os`), así que el frontend no lo alcanza por el client normal |
| AuthHub | `api/routers/authhub.py` → `/api/authhub/*` | OAuth/messaging providers (Gmail, WhatsApp) | **No es** conexión de plataformas de trabajo; dominio distinto |
| Identity Center | `api/routers/identity_center.py` → `/api/identity-center/*` | Estado de credenciales de plataformas bug-bounty (HackerOne, Bugcrowd, Intigriti, YesWeHack, Synack) | Parcial; solo 5 plataformas hardcodeadas |
| Identity manager | `api/routers/identity.py` → `/api/identity/*` | Identidad/dispositivos/preferencias | Complementario |
| Connections | `api/routers/connections.py` | Payout accounts + `get_best_methods_for_argentina()` | Pagos, no auth de fuentes |

**P0 corregido (auth contract):**
- Antes: `loginWithCredentials`/`register` enviaban `{email,password[,display_name]}` y esperaban `{session:{token,expires_at}, user}`; backend exigía `{username,password}` y devolvía `{access_token,refresh_token}`.
- Ahora `auth_users.py`:
  - `LoginRequest` acepta `username` **o** `email` (+`password`); lookup por cualquiera.
  - `RegisterRequest` acepta `username` opcional + `display_name`; si falta `username` se deriva del email/display_name y se hace único.
  - `TokenResponse` añade `session.token`/`session.expires_at` y `user` (sin romper `access_token`/`refresh_token`).
- Tests: `tests/test_auth_users.py` = **14 passed** (incluye `test_login_with_email`, `test_register_frontend_shape`, `test_login_requires_identifier`). Ruff OK.

## 4. INCONGRUENCIAS PRIORIZADAS

### P0
- ~~OWNEX Account login/register roto por contrato frontend↔backend~~ → **CORREGIDO** (§3).

### P1
1. **`core/cores/` = copia accidental de `cores/`** (untracked, 1066/1082 archivos idénticos). Solo referencia interna `core/cores/direct_work_engine/manager.py`; no hay imports externos `core.cores`. Candidato a cuarentena/borrado **tras backup + confirmación** (no eliminado aún).
2. **`work/ownex-economy-active-earn` = worktree separado** con frontend/backend duplicados y cambios propios. No es canónico; decidir destino con el owner.
3. **Auth triplicado:** `auth_users.py` (canónico user) + `auth.py` (device) + `auth_user.py` (legacy `/auth` root). Unificar contrato de sesión y deprecar `auth_user.py` tras verificar consumidores mobile/desktop.
4. **Connection Manager incompleto:** no hay un único manager de conexiones externas con estados `NOT_CONNECTED/CONNECTING/CONNECTED/EXPIRED/ERROR/REVOKED/MANUAL_SETUP/UNSUPPORTED`; hay `identity_center` (5 plataformas), `connections`, `authhub`, `useExternalConnectionManager` (frontend) y adapters sueltos.
5. **Investment/Crypto sin cuentas reales:** `InvestmentHub`/`Wallets`/`Trading` tienen UI y endpoints, pero sin OAuth/exchanges conectados ni operaciones autorizadas; riesgo de "funcionalidad declarada completa que no funciona".
6. **Scheduler/handlers:** verificar que cada job montado tenga handler real y que `core/scheduler` vs `cores/scheduler` no diverjan (ver duplicación).

### P2
- Mezcla `core.`/`cores.` en `api/` (475 vs 379 imports) sin SSOT por dominio.
- `cores/financial_intelligence/argentina_payout_methods.py` (base completa) vs `cores/financial/payout_recommender.py` (subset rankeado usado por `connections.py`): documentar relación, no son duplicados exactos.
- `core/financial_intelligence/` existe en paralelo a `cores/financial_intelligence/`; mapear imports antes de consolidar.
- Enumeraciones/tipos inconsistentes (`method_type` string vs enums, `provider`/`platform`, estados de fuente `ELIGIBLE/CONDITIONAL/UNKNOWN` vs `FULLY_ELIGIBLE/INELIGIBLE`).
- `/api/health`, `/api/status` con múltiples implementaciones.

### P3
- Rutas top-level fuera de las 8 secciones (`/investments`, `/atlas/`, `/odyssey/`, `/aegis/`, `/polymarket`, `/trading`, `/terminal`, etc.) rompen la "única navegación" si no se integran o se marcan como apps micro explícitas.
- `/quick-capture` sin `component`.
- Estados de error/loading/stale/disconnected no uniformes en todas las páginas.

## 5. SSOT preliminar por dominio (evidencia, no borrado)

| Dominio | SSOT propuesto | Evidencia |
|---|---|---|
| Direct Work Engine | `cores/direct_work_engine` | `api/routers/direct_work.py` lo importa (37 refs); tests DWE pasan |
| Argentina payout methods | `cores/financial_intelligence/argentina_payout_methods.py` | Usado por `cores/payment_compat/engine.py`, `cores/direct_work_engine/cashflow.py`, tests |
| Payout ranked subset | `cores/financial/payout_recommender.py` | Usado por `api/routers/connections.py`, `cores/financial_hub/*` |
| OWNEX Account auth | `api/routers/auth_users.py` + `cores/auth/auth.py` + `database.models.User` | Frontend store + tests |
| Device session auth | `api/routers/auth.py` + `cores/auth/auth_manager` + `session_validator` | autoLogin + tests |
| Source catalog/families/adaptation | `cores/opportunity/*` | Trabajo reciente verificado (176 fuentes, 164 tests) |
| Discovery→WorkBank runtime | `core/opportunity/*` + `core/scheduler/jobs.py` | Scheduler runtime + tests discovery_to_workbank |

## 6. PRÓXIMOS CORTES (orden v10)

1. **Connection Manager único** (prioridad 2): unificar `identity_center` + `connections` + `useExternalConnectionManager` con estados y sin secretos en localStorage.
2. **Deprecar `auth_user.py`** tras verificar consumidores; mantener `auth_users.py` + `auth.py`.
3. **Mapear imports `core.`/`cores.` por dominio** y migrar a SSOT sin borrar (ver `OWNEX_DUPLICATION_CONSOLIDATION.md`).
4. **Investment/Crypto:** conectar market data + portfolio tracking reales antes de trading; marcar lo no integrado como `UNKNOWN/BLOCKED` en UI.
5. **Scheduler:** inventario job→handler→router con evidencia; cerrar gaps.
6. **Frontend:** integrar rutas top-level en las 8 secciones o declararlas apps micro; eliminar `/quick-capture` sin componente.

**Directiva:** no detenerse en diagnóstico; los P0/P1 anteriores se corrigen en cortes verticales con tests.
