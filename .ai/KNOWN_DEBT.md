> **Rotas entradas resueltas**: el histórico completo está en `.ai/archive/KNOWN_DEBT.md` (11,832 B, 9 secciones). Este archivo conserva 34 de 39.
> **Regla**: grepeá `.ai/archive/KNOWN_DEBT.md` antes de contradecir una regla histórica.

## 32. Auth bypass en los 28 namespaces root-mounted (2026-09-30) — P0 seguridad, decisión del owner

**Evidencia:** `api/middleware/auth_middleware.py:49-50` retorna temprano para todo path que
**no** empieza con `/api/`:

```python
if not path.startswith("/api/"):
    return await call_next(request)
```

Como 28 routers se montan **en raíz** (sin prefijo `/api`), sus **264 rutas — 148 de ellas
mutantes (POST/PUT/PATCH/DELETE)** — no requieren credencial. Incluye, sin autenticación:

- `GET /direct-work/revenue-ledger` (el ledger de ingresos)
- `POST /direct-work/workbank/{id}/deliver/approve` (40 rutas mutantes en ese prefijo solo)
- `POST /finance/*`, `POST /first-money/*`, `POST /mission-hub/*`, `POST /wear-os/*`, …

**Mitigación actual:** el backend binds sólo `127.0.0.1`, así que no está expuesto a la LAN.
Además el CSRF middleware sí cubre el caso, y el desktop/companion son single-user.

**Por qué no se arregló en la auditoría frontend (2026-09-30):** es un cambio de backend con
radio de impacto alto (puede bloquear la app en ejecución y a los clientes desktop/companion,
que llaman justo esas rutas root-mounted). Queda como **decisión explícita del owner**, no como
pendiente olvidado. Ver `.ai/FRONTEND_RELEASE_AUDIT.md` §H-1.

**Acción futura:** extender el gate de auth a los root-mounted, con un allowlist explícito de
las rutas públicas (mismo patrón que `PUBLIC_PATHS`), y verificar que el Tauri/Android
sigan funcionando antes de dar el cambio por cerrado.

**Receta de fix (evaluada el 2026-09-30; NO aplicada a propósito):** reemplazar el
early-return de `auth_middleware.py:49-50` por una allowlist de prefijos públicos,
dejando pasar WS y OPTIONS como hoy:

```python
# REFERENCIA — el cambio NO fue aplicado. Requiere los 4 checks de abajo.
if not path.startswith("/api/") and not path.startswith(tuple(PUBLIC_ROOT_PREFIXES)):
    return await call_next(request)
```

**Por qué es riesgoso — los 4 checks obligatorios antes de darlo por cerrado:**
1. Los 5 exempt de `PUBLIC_PATHS` deben seguir respondiendo sin credencial.
2. `/api/ws` y `/auth/*` deben seguir abiertos (el login fluye por ahí).
3. **Los clientes desktop/companion son el riesgo real:** llaman rutas root-mounted
   (`/direct-work`, `/mission-hub`, `/mobile`, `/wear-os`). Si autentican sólo con la
   cookie `ownex-session` —que es `SameSite=Lax` desde un origen `tauri://localhost`,
   o sea cross-site— el gate nuevo los rompe. Hay que verificar Bearer vs. cookie en vivo.
4. Re-correr el E2E completo: `e2e/flows.spec.ts` lee `/today` y
   `/direct-work/revenue-ledger`, ambos root-mounted.

**Recomendación: sesión propia, con esos 4 checks como criterio de DONE.**

## 33. 38 llamadas del frontend a endpoints inexistentes (2026-09-30) — P1/P2, deuda de producto

**Evidencia (475 pares método/ruta resueltos contra los 201 routers montados):**
**330 coinciden · 30 ruta inexistente · 9 método incorrecto (405) · 106 dinámicas.**

Causas raíz verificadas:

| Grupo | Llamadas | Causa |
|---|---|---|
| `/aegis/*`, `/odyssey/*` | 8 | Los routers **existen** (`apps/aegis/api/routers.py:18`, `apps/odyssey/api/routers.py:16`) pero **no están en `api/main.py`** (`grep aegis\|odyssey api/main.py` → 0). Garantizado 404 en rutas vivas `/aegis/` y `/odyssey/`. |
| `/trading-lab/*` | 6 | El namespace **no existe** en el backend. Ya documentado como #25; las 6 funciones de `ownexData.ts` siguen sin consumidor. |
| `/setup/enhanced-personalization/*` | 3 | El frontend llama bajo `/api/setup/…`, pero la ruta real es root-mounted en `/enhanced-personalization/*`. |
| `/api/system/readiness` | 1 | Se llamaba en **cada arranque**; la ruta nunca existió (sólo existe `/api/system/status`). |
| Otros (`/hypotheses` GET, `/identity` GET, `/learning/progress`, `/files/list`, `/atlas/health`, `/modes/*`, `/wear-os/approval-request`, …) | 12 | Rutas que el backend nunca expose con ese verbo/path. |
| 405 (`/progressive-scaling/*`, `/self-healer/scan`, `/alerts/resolve`, `/modes/set`, `/ultra-fast-income/set-mode`, `/autopilot/one-action`) | 9 | El frontend usa GET donde el backend define POST (o al revés). |

**Nota:** `/api/profile-kit` y `/api/quick-capture` son 307 de `redirect_slashes`, no 404 duros.

**Por qué no se corrigió:** es corrección de producto (montar routers, renombrar llamadas,
borrar UI muerta), no de release. Ver `.ai/FRONTEND_RELEASE_AUDIT.md` §H-2.

## 34. UNKNOWN renderizado como `$0` en el Command Center (2026-09-30) — P2 honestidad

**Evidencia:** cuando un fetch falla, `IncomeHome.vue` lo convierte en `$0` en vez de
UNKNOWN, lo que hace indistinguible "no sé" de "gané cero":

- `IncomeHome.vue:369,373,379` — `realized?.total_earned || 0` ⇒ la banda **REALIZADO** muestra `$0`
- `IncomeHome.vue:670,674,678` — `capital.total_usd ?? 0`
- `IncomeHome.vue:383,387` — `|| '$0'` (string literal)
- `Capital.vue:184` — `usd_per_hour || 0` ⇒ la métrica reina `NET $/H` lee 0
- `ownexAi.ts:110-113` — fabrica ceros y deriva `hasAny=false` a partir de ellos

**El patrón correcto ya existe en el árbol:** `Mission.vue:37-42` y `PublicWork.vue:37-46`
renderizan `'—'` / `'UNKNOWN'`. El Command Center no lo sigue.

**Por qué no se corrigió:** cambiar la presentación de dinero es decisión de producto y
excede el alcance de "hacer la release funcional". Es el ítem de mayor riesgo residual de
esta auditoría. Ver `.ai/FRONTEND_RELEASE_AUDIT.md` §H-7.

## 35. `spa-server.cjs` no tenía servidor WebSocket ni proxy (2026-09-30) — P2, ya PARCIAL

**Resuelto en esta auditoría:** el script original `require('express')`, que **no está
instalado** en ningún `node_modules`, así que no había forma de servir `dist/` por HTTP.
Se reescribió con módulos nativos + proxy HTTP + upgrade WebSocket.

**Pendiente:** el handshake a `/api/ws` recibe **403 del propio backend** (verificado con
`curl` directo contra `:8000`, no es del proxy). `AuthMiddleware` deja pasar los websockets
("handled by their own auth") pero el endpoint no acepta el upgrade sin token. La app
funciona igual (los eventos en vivo son degradables), pero el canal de notificaciones
push no está operativo en browser.

## 28. FIRST PAID bloqueado por credenciales del owner (2026-09-30) — P0 externo, NO automatizable

El camino al primer PAID quedó **construido, testeado y bloqueado correctamente en el Human Gate**. Falta sólo lo que la máquina no puede tener:

| # | Bloqueo | Dónde | Quién lo resuelve |
|---|---|---|---|
| 1 | **`GITHUB_TOKEN` vacía** ⇒ los 8 READY (`github`, $5,087) no se pueden enviar | `~/.config/ownex/opportunity.env` (`GITHUB_TOKEN=`) | **owner** (1 paste) |
| 2 | **Rails de cobro sin configurar** ⇒ `P(CASH)` queda UNKNOWN y `/today` devuelve "Configurá 1 método de cobro" como paso 1 | `POST /api/payment-compat/configured` (10 min) | **owner** |
| 3 | `HACKERONE/BC/INTIGRITI/YESWEHACK_API_KEY` vacías ⇒ los programas siguen no ejecutables | `opportunity.env` | owner, o se aceptan como no-ejecutables |

**El adaptador ya existe y falla cerrado** (`cores/opportunity/executors/auto_submit.py::GitHubBountyAdapter`): sin token devuelve `state="needs_access"`, `attempted_external_action: false`, `human_gate: "required_before_send"`. **Nunca envía por su cuenta**; la apertura del PR delega en `PRBuilder.create_pr(require_approval=True)`.

**Regla:** preparatory ≠ envío. La automatización llega hasta el Human Gate y ahí se detiene; enviar un bounty es acción externa bajo nombre del usuario.

## 29. `/api/direct-work/workbank` NO existe (montado en raíz) (2026-09-30) — P1, causa de un diagnóstico falso

- **Evidencia:** el router `direct_work` se monta **en raíz** (`include_router(direct_work_router)`, sin prefijo `/api`). `GET /api/direct-work/workbank` → **404**; la real es `GET /direct-work/workbank` → 200.
- **Costo real:** en esta sesión se leyó ese 404 como si fueran datos y se reportó "WorkBank ready = 0" cuando el banco tenía **12** `ready_to_deliver`. El mismo error está pineado en `frontend/src/lib/backend.ts::ROOT_MOUNTED_PREFIXES` para el cliente, pero cualquier llamada manual a un namespace root-mounted por `/api` produce este 404 silencioso.
- **Mitigación aplicada:** todas las verificaciones de Fase 2-3 se hicieron contra `/direct-work/workbank` y `/unified-income/*` con el prefijo correcto.
- **Regla permanente:** antes de afirmar "0" contra la API, confirmar el status code. **404 y 0 no son lo mismo**, y OWNEX tiene routers root-mounted *y* bajo `/api`.

## 30. `omniroute` sigue `activating` y OAR lo reporta `healthy` (2026-09-29) — P2 (ver #27, mecanismo cerrado)

Sin cambios en esta fase (decisión del owner: fuera de alcance). Se mantiene documentado: `systemctl --user is-active omniroute` = `activating` hace días. **Actualización 2026-10-04:** el mecanismo que lo reportaba `healthy` con `latency_ms: 0.0` ya fue corregido (ver #27 cerrado) — hoy se reporta `UNKNOWN`, no verde. **Lo que sigue abierto es sólo que el servicio systemd no levanta.**

## 24. `/api/trading/dashboard/summary` — el test daba confianza falsa (2026-09-28) — P3, decidido

- **Evidencia nueva (la sesión anterior no la tenía):**
  - **0 callers** en frontend, Android, Tauri y `apps/` (el path sólo aparece en un comentario de `usePreloadData.ts` que habla de *otro* path).
  - La app real sirve el payload del **ganador** (`by_type/by_cycle/categories/enabled/disabled/job_ids/total_jobs`, sin `copy`) — verificado en vivo. El handler "muerto" es inalcanzable.
  - `GET /api/trading/overview` (la superficie que el front **sí** usa) es **superconjunto**: trae `copy`, `masters`, `reasoning` + `jobs`/`metrics`/`mode`/`pending_config`.
  - `tests/test_trading_intelligence.py::test_dashboard_summary_route` monta un app **aislado** con sólo `trading.router`, por eso pasa y verifica un payload que en la app real no existe → **falso positivo de cobertura**.
- **Decisión:** borrar el handler inalcanzable (opción c del #19) cuando el árbol esté limpio; es borrado muerto, no destructivo. **No se hizo en este cierre**: 0 beneficio para el usuario, y `ownexData.ts`/3 tests están en un árbol con 297 entradas sin commitear de flujos concurrentes.
- **Regla permanente:** un test de ruta debe correr contra la **app completa** (o al menos contra el orden real de `include_router`); un app aislado no prueba alcanzabilidad.

## 26. `FREELLMAPI_MODEL=auto` puede elegir un clasificador, no un chat model (2026-09-29) — P2,规避 hasta que se valide un model id

- **Evidencia (live):** `POST /v1/chat/completions {"model":"auto"}` devolvió `model=meta-llama/llama-prompt-guard-2-86m` y el body fue un score (`0.000563…`), no una respuesta al prompt. El catálogo del gateway expone **253 modelos** e incluye familias de clasificadores (`llama-prompt-guard-2-22m`, `-2-86m`, `gpt-oss-safeguard-20b`) mezcladas con chat models reales (`gemini-2.5-flash`, `gpt-oss-20b`).
- **Por qué importa aunque hoy no duela:** `freellmapi` está **opt-in** (fuera de `enabled_providers`), así que hoy **no** entra al routing del día a día. El día que se encienda, un CODE task podría aterrizar en un clasificador que "responde 200" y no sirve → **fallo silencioso**, el peor modo de fallo.
- **Regla permanente:** provider nuevo entra **opt-in y con `model` explícito**, nunca `auto`/`best` de un catálogo heterogéneo. La doc de `create_freellmapi_adapter` dice `model="auto"` por defecto: **no dejarlo así al encender**.
- **Acción al encender:** setear `FREELLMAPI_MODEL=<model id validado por tarea>` (medir con el mismo prompt que usa el hunter), y **verificar capabilities declaradas** (`TOOL_CALLING`/`EMBEDDING` se declaran sin probar → misma familia de mentira que el P2 de capabilities de colibri).

## 27. OAR reporta un provider `healthy` mientras su servicio systemd no levantó (2026-09-29) — P2 — **MECANISMO CERRADO 2026-10-04**

- **Evidencia original:** `omniroute` lleva ~14 h en `systemctl --user is-active` = **`activating`** (nunca `active`), y sin embargo `/oar/doctor` lo lista en `providers.healthy` con `latency_ms: 0.0` y `last_error: "Missing API key or base URL"`.
- **Por qué importaba:** el self-diagnostic afirmaba salud que no podía comprobar. Un provider con `latency_ms=0.0` no fue contactado nunca; eso debía ser `unknown`/`degraded`, nunca `healthy`.
- ✅ **CERRADO 2026-10-04 (el mecanismo, no el servicio).** `health.py:96` pisaba el status del propio adapter con `_determine_status()`, que no exigía contacto real: `latency_ms == 0.0` + `success_count == 0` + `error_rate == 0.0` devolvía **`HEALTHY`**. Ahora `_check_provider` **respeta** el status que el adapter ya calculó, y cuando viene `UNKNOWN` aplica **piso de contacto**: sin éxito y sin latencia ⇒ `UNKNOWN`, nunca `HEALTHY`. Verificado con el mismo escenario que loEUA，产生 (omniroute sin credencial) antes reportaba verde.
- **Lo que sigue abierto es #30** (el servicio systemd nunca levanta), que es un problema distinto: esta entrada nunca afirma que `omniroute` esté sano hoy, ya no puede.
- **Bono colateral de la misma sesión:** el failover de OAR era **código muerto para todo error HTTP** (`adapters.py` devolvía en vez de lanzar ⇒ `record_success` ⇒ circuit breaker nunca abría ⇒ el mapa 429 de `resilience.py:87` inalcanzable). Arreglado: `finish_reason == "error"` ahora es fallo y hace `continue` al siguiente provider. Sin ese fix, activarle 4 providers free no habría protegido nada.
- **Regla permanente:** *un health check que no exige contacto real no es un health check, es un eco.* Y *`latency == 0` con `success_count == 0` significa "nunca se preguntó", que es `UNKNOWN` — no `HEALTHY`.*

## 25. `trading-lab/*` = 8 funciones muertas en `ownexData.ts` (2026-09-28) — P3, PENDIENTE

- **Evidencia:** 8 funciones llaman `/trading-lab/*` (7 llamadas) y el backend tiene **0 rutas** `trading-lab` (verificado sobre `app.routes` runtime) → cada llamada es un 404 garantizado.
- **Pero 0 impacto visible:** las 8 funciones tienen **0 referencias fuera de `ownexData.ts`** (ni `.vue` ni `.ts`) → ninguna pantalla las renderiza, ningún usuario ve el 404. Baja de P1 a **P3**.
- **Acción post-stable:** borrar las 8 funciones (dead code) junto con los tipos asociados. No se hizo en el cierre por el mismo motivo de riesgo del #24.
- **Regla permanente:** un cliente de API sin consumidor es deuda, no un bug visible; pero namespace completo inexistente en backend = superficie muerta que hay que podar, noinality documentar para siempre.

## 19. 1 ruta API duplicada cross-router (ship-day 2026-09-28) — PENDIENTE DECISIÓN OWNER

- **Hallazgo (runtime, no openapi lazy):** 7 duplicados reales (mismo path+método). FastAPI resuelve por **orden de registro** → el 2º handler es **inalcanzable por HTTP** = código muerto.
- **Resueltos (6, con evidencia por contrato, cero cambio de comportamiento):**
  | Path | Motivo de la eliminación |
  |---|---|
  | `mission` 2º `/stale` | body **idéntico** al ganador |
  | `mission` 2º `/{mission_id}/checkpoint` | body **idéntico** al ganador |
  | `availability` alias `/max-task-hours` | alias explícito del ganador |
  | `api.main` inline `/version` | payload **subconjunto estricto** del router; el único cliente lee `.version` (ambos lo dan) |
  | `revenue_app` `/summary` | devuelve `{summary,stats}`; el front consume `total_earned`/`pending_amount`, que **solo** da el ganador |
  | `control` `/obsidian/sync` | sin body, superado: el winner lee `{path, content, title}` = lo que manda `controlPanel.ts` |

  Rutas 1856 → **1850**.
- **Pendiente (1):** `/api/trading/dashboard/summary` GET → winner `trading_dashboard:trading_dashboard_summary` (estado de jobs) · muerto `trading:dashboard_summary` (copy + masters + intelligence + reasoning).
  **No se borró a propósito:** el muerto es **más rico** que el ganador y **ningún caller del repo lo consume** (el front solo usa `/trading/overview` y `/trading/copy/*`). Borrarlo destruiría capacidad que un cliente externo (Tauri/Android) podría necesitar. Decidir: (a) dejar el winner, (b) darle un path propio, o (c) eliminarlo.
- **Guard:** `tests/test_api_route_duplicates.py` (2 tests) falla si aparece cualquier duplicado nuevo Y si el pendiente desaparece sin actualizar el allowlist.
- **Regla permanente**: un path+método, un handler. Si dos routers sirven lo mismo, uno se archiva explícitamente.

## 21. `/api/dashboard/summary` era un 404 en cada arranque (P0, corregido)

- **Evidencia:** `frontend/src/startup/composables/usePreloadData.ts` hacía `fetch('/api/dashboard/summary')` en el preload de arranque. Ese router (`api/routers/dashboard.py`) fue **archivado** en el polish del 2026-09-28, y **nunca tuvo** endpoint `/summary` (sus rutas eran `/status`, `/models`, `/ws/logs`; `/keys` y `/sessions` comentadas) → el fetch era un **404 preexistente**, no una regresión del archivado.
- **Consumidor:** `cache.summary` no lo leía nadie (`preloadCache` solo se provide-eaba, sin lecturas de `.summary`).
- **Fix:** se eliminó el fetch muerto y `summary` pasó a opcional con `@deprecated` en `PreloadCache`. Restaurar el endpoint "por el llamador" habría sido inventar contrato.
- **Regla permanente**: al archivar un router, grepear sus paths en el front antes de darlo por muerto; al quitar un caller, confirmar que el dato no tenía consumidor.

## 20. Backup loguea fallos al empaquetar `-wal`/`-shm` transitorios (P2, no rompe)

- Al crear backup, `_scan_files` puede listar `orion.db-wal`/`-shm` que desaparecen antes del `zf.write` → `logger.warning("Failed to add ... to backup")`. Best-effort: el backup se crea igual, solo es ruido en log.
- No corregido en ship-day (P2, sin impacto en restore: los 39 tests de backup/migrate/recovery pasan con aislamiento tmp).

## 18. Contract drift frontend↔backend (audit §17, 2026-09-15; re-audit polish 2026-09-28)

### 18b. Clusters B/D/E CERRADOS (2026-09-28) — 11 llamadas muertas a rutas reales

- **B — WorkRoom reescrito al contrato real** (`frontend/src/components/work/WorkRoom.vue`): 980 → 320 líneas. Las 11 llamadas ficticias (`workbank/{id}/files`, `/evidence`, `/deliverables`, `GET|PUT workbank/{id}`, `GET workbank/{id}`) **no existen en el backend**; la sala nunca funcionó. Ahora usa solo lo real: `GET /direct-work/workbank` (busca el item), `POST .../deliver/prepare`, `GET|PUT .../file/{filename}`, `POST .../deliver/approve`, `POST .../submit`. Se eliminaron las tabs/pipeline de etapas, actividad de agentes y CRUD de evidencia/entregables (todo inventado). Tabs reales: Visión general · Entrega · Archivos.
- **D — CommandPalette (4 búsquedas)**: `/memory/query` → `/knowledge/search` (misma forma `{results[]}`); `/hypotheses?search=` → `/offensive/hypotheses?max_results=20` + filtro por texto en cliente (no hay search server-side); `/direct-work/queue` → `/direct-work/workbank` + filtro local; `/scheduler/jobs` **eliminado** (no existe router de scheduler; no hay reemplazo honesto).
- **E — Connections + Wallets**: `POST /connections/sync-all` y `POST /connections/sync/{provider}` no existen (el sync real corre en el scheduler) → los botones ahora refrescan estado real y se renombraron "Actualizar" (antes prometían sincronizar). `GET /identity-center/wallets` (405: solo hay POST) → `GET /identity-center` con normalización dict→lista; `PUT /identity-center/wallets/{id}` (405) → `POST /identity-center/wallets` con body `{key: address}`.
- **Guard de regresión** (`tests/test_frontend_api_contract.py`): 3 tests nuevos que pinean que las rutas muertas NO vuelvan y que los reemplazos reales estén cableados.

### 18c. Descubierto en el mismo audit, NO arreglado (scopeowner = cluster 3)

Inventario medido de llamadas frontend sin ruta backend (verificado contra `app.routes` runtime, matcher con dualidad `/api` ↔ raíz):

| Namespace | Llamadas dead | Nota |
|---|---|---|
| `trading-lab/*` | 6 (`ownexData.ts`: capital/snapshot, dashboard, engines, risk/summary, strategies/{id}, strategies/rankings, validation/status) | **El namespace entero no existe en el backend.** Superficie de producto, no typo |
| `wear-os` | 3 (`approval-request`, `approvals/pending`, `approval/{id}/respond`) | El router `/wear-os` existe con 7 rutas, pero no las de aprobación que llama el front |
| `worker` | 1 (`/worker/${action}` en `WorkerControl.vue` → real es `/api/worker/*`) | Drift de prefijo |
| `files` | 1 (`/api/files/list`) | No existe; hay `/api/obsidian/files` y `/api/reports/...` |
| `zap/alerts` | 1 | Path continúa con template → verificar antes de tocar |

**Régimen**: estos quedan como deuda explícita de superficie de producto (no bugs de un archivo). `trading-lab` es la más grande: 6 llamadas a un namespace inexistente = 6 features mortas en la UI. **No se arreglan sin decisión de owner** (¿se reconstruye el namespace o se quita la UI?).

## 18. Contract drift frontend↔backend (audit §17, 2026-09-15; re-audit polish 2026-09-28)

- **2026-09-28: drift real encontrado y fixeado** — `ROOT_MOUNTED_PREFIXES` tenía 6 de 27 namespaces root (Mission/Career/OAR/Voice + 17 más daban 404 en browser y Tauri). Fix caller-side: lista 27 + normalize-then-match + `/auth` excluido deliberado + 3 callers raw migrados a `api.*` + guard reescrito al invariante real (ver DECISIONS 2026-09-28).
- **Contexto original**: auditoría completa de las 222 llamadas `api.*` del frontend contra las rutas reales del backend (fuente de verdad `app.routes` runtime, no openapi lazy). Resultado: 165 matchean, **57 no responden** (55 por ruta inexistente + 2 por método 405).
- **Resuelto en el audit (P0/P1)**:
  - **Cluster A — prefix drift (11 rutas → 404)**: `first-money`, `result-based`, `platform-guides` se montan en **raíz** en `api/main.py` (`include_router(router)` sin `/api`) pero `frontend/src/lib/backend.ts::resolveApiUrl` los resolvía bajo `/api/*` → FirstMoney, ResultBased y PlatformGuides NUNCA funcionaron desde el frontend. Fix: `ROOT_MOUNTED_PREFIXES` ahora incluye `['/direct-work','/mobile','/wear-os','/first-money','/result-based','/platform-guides']`. Nuevo guard de regresión `tests/test_frontend_api_contract.py` (3 tests) pin que cada router root-mounted del backend tiene contraparte en el front.
  - **Cluster E (método 405)**: `ownexData.ts::updateFinding` llamaba `PUT /api/findings/{id}` pero el backend expone `PATCH /{finding_id}` → migrado a `api.patch`. `updateFindingStatus` ya usa `PUT /{id}/status` (correcto).
  - **Dead code §12**: eliminado `cores/intelligence/next_best_action.py` (219 líneas, 0 callers/imports/tests/exports/packaging — verificado exhaustivamente) y `frontend/src/services/capitalApi.ts` (274 líneas, 29 llamadas a rutas inexistentes, 0 imports).
- **Documentado, NO arreglado (decisión: estabilidad > novelty, no expandir)**:
  - **Cluster B — WorkRoom** (`frontend/src/components/work/WorkRoom.vue`, ruta `/operations/work-room/:id`): 10 sub-recursos ficticios (`PUT/POST/DELETE /workbank/{id}`, `/files`, `/evidence`, `/deliverables`). El backend solo expone `/workbank/{id}/file/{filename}` (GET/PUT) + `/deliver/*`. La sala nunca funcionó; no es parte del flujo diario crítico. Opciones: reescribir WorkRoom al contrato real (`file/{filename}` existente) o quitar la ruta — diferido, no bloquea.
  - **Cluster D — CommandPalette muertas (4)**: `/api/memory/query` (no existe), `/api/hypotheses` GET (solo POST `/{target_id}`), `/direct-work/queue` (no existe), `/api/scheduler/jobs` (no existe). Son comandos de búsqueda/atajos no críticos; fallan silencioso.
  - **Cluster E resto**: `Connections.vue` `/api/connections/sync-*` (no existen), `Wallets.vue` `PUT /identity-center/wallets/{id}` (solo POST), y los 8 endpoints de `capitalApi.ts` que vivían bajo `/api/economic|revenue|financial` pero el módulo ya fue eliminado.
- **Régimen**: cada nueva ruta frontend debe existir en el backend (o prefijo dinámico); el guard `test_frontend_api_contract.py` pin los root-mounted; los clusters B/D/E quedan como deuda explícita de frontend legacy, no como jobs/fixes de producción.

## 31. Denominador de `human_hours` ausente para security work (2026-09-30) — P1, creado por la corrección del banco

- **Evidencia:** `ChannelEconomics.human_hours` se deriva **sólo** de `WorkItem.human_minutes_actual` (`cores/economic_feedback/engine.py:139-146`), y `net_per_hour = net_cash/human_hours` (`:198-199`). Pero los *programas* de bug bounty se excluyeron del banco de entregables (no son tareas, ver DECISIONS 2026-09-30 FIRST PAID), así que **el trabajo de seguridad hoy no tiene `WorkItem`** y por lo tanto **no tiene denominador de horas humanas**.
- **Consecuencia:** `NET CASH / HUMAN HOUR` — la métrica reina del proyecto (§77 del megaprompt security) — **no es computable para seguridad** hasta que exista un `WorkItem` por tarea de seguridad real.
- **No es un bug:** es la consecuencia honesta de una corrección correcta (un programa no es una tarea). El riesgo real sería que alguien leyera `net_per_hour` como si fuera security.
- **Acción (NO automatizable desde acá):** el trabajo de seguridad de verdad entra al banco por la vía **hallazgo→tarea** (el promotion path que ya existe en `cores/validation/promoter.py:50`), no por discovery de programas. Cada bounty报告会 que seard's确实reportada debe crear su `WorkItem` con `human_minutes_actual` para que el denominador exista.
- **Regla permanente:** antes de reportar `NET CASH/HUMAN HOUR` de un carril, verificar que ese carril **produce WorkItems**. Sin denominador, la métrica es UNKNOWN — no 0.

## 33. Fiverr: fuera del núcleo pero NO borrado (2026-09-30) — decisión

- **Hallazgo que corrige la premisa:** Fiverr en OWNEX **no es un marketplace competidor** — es el motor de gigs propio (`cores/fiverr/`, `legacy.py:226` "internal engine, solution-based gigs, no external API"). El usuario vende su propio producto; no compite por precio con otros freelancers.
- **Decisión:** `_DEFAULT_STATUS["fiverr"]` ACTIVE → **PAUSED** (sale del discovery núcleo; la tesis es "trabajo técnico verificable"). **Reversible con un click** (`POST .../freelance/{channel}`) porque es ingreso propio.
- **Workana:** ya `EXCLUDED` (purge 2026-09) y ahora sin override por HTTP (#32).

## 34. Fiverr revivido como carril OPCIONAL de commerce (2026-09-30) — decisión

- **Owner:** revivir Fiverr pero **opcional**, junto al módulo de ecommerce. Foco del proyecto = **DEV/tech de nicho** (dev_bounty, oss, security, AI/tech).
- **Estado:** `ACTIVE` (revivido). No se excluye porque `cores/fiverr/` es el motor de gigs **propio** (solución completa, no horas) ⇒ es ingreso propio, no un marketplace donde competimos por precio. A diferencia de Workana (`EXCLUDED`, `_HARD_EXCLUDED` sin override).
- **Opcionalidad real:** `POST .../freelance/fiverr {"status":"paused"}` lo saca del discovery sin perder nada.
- **Contexto:** DECISIONS 2026-09-14 había dejado fiverr ACTIVE; esta sesión lo pasó a PAUSED y el owner decidió revertirlo a opcional. Registrado para que no se vuelva a cambiar por intuición.

## 35. Lote de 40 plataformas de seguridad (2026-09-30)

- **+40 `SourceDefinition` de dato** (0din, Patchstack, Wordfence, SlowMist, Certora, Secure3, Hashlock, ZDI, CyberTalents, Detectify, WhiteHub, Secuna, Secur0, Vulbox, etc.) del catálogo de disclosures citado por el owner. Total: **138 → 178 fuentes**.
- **Nacen `last_verified="unverified"`**: hasta que corra `source_registry.probe_all_sources()` (job diario 05:00) no se afirma que estén vivas. Es la misma regla que evitó el incidente de las 890 fuentes fabricadas.
- **NO se rellenó hasta 100 con URLs inventadas.** Llenar un número con dominios no verificados es exactamente el error ya pagado (CURRENT_STATE 2026-09-16). El gate de admisión (#32) descarta lo que no sirve con motivo visible, que es lo que mejora señal/ruido.

## 36. 85 tests rojos post-cierre (2026-10-01) — P1/P2, NO de la sesión de cierre

- **Medido:** suite serial completa (`make test` sin los 3 flaky de red) = **5845 passed · 85 failed · 0 errors** en 28 archivos. El gate `make test-fast` quedó **103/1** (intacto) y las 20 suites tocadas por el cierre quedaron **432/432**.
- **Clasificación verificada archivo por archivo** (no declarada):

| Categoría | # archivos | Qué son |
|---|---:|---|
| Baseline ya documentado | 6 | `validation_engine` (11), `e2e_copilot` (10), `self_healer`, `prompt_guard`, `verdict_learner` (strings `core.` de una suite que quedó afuera), `trading_front_contract` (KNOWN_DEBT #19/#24) |
| Drift de contrato del flujo concurrente | 13 | p.ej. `cores/commander/__init__.py` importa 2 módulos que nunca fueron commiteados (`git ls-files cores/commander/` → 3 archivos); `api/scheduler.py:601` ahora pasa 4 args a `prioritize()`; `test_executors_base` espera `algora`/`outlier` que se movieron a propósito; `test_web3_direct_work` espera `immunefi`/`code4rena` desregistrados por el probe del 2026-09-11 |
| **Contaminación de orden (pasan aislados)** | 9 | Verificado archivo por archivo: `outlook_sync` 14/14 · `memory_system` 12/12 · `new_integrations` 45/45 · `opportunity_feedback` 10/10 · `live_probe_loop` 10/10 · `worker_core_e2e_golden` 4/4 · `oar_api` 7/7 · `command_center` 8/8 · `solver`+`mobile_copilot` 15/15. Ninguno lo introduce la sesión de cierre. |
| Red / externo | 3 | `test_direct_work_algora` pega al API real de Algora.io (devuelve `[]`; coherente con `CURATED_BOUNTIES=[]`); `test_desktop_release` (2 HWID order-dependent, 94/10/2 aislado); `solver`+`mobile_copilot` (timeout de LLM, ~5 min) |

- **Por qué NO se arregló en el cierre:** §7 del charter. Ninguno de los 85 toca código de la sesión de cierre; varios son de un flujo concurrente activo en el mismo árbol (371 entradas sin commitear). "Arreglar" un drift ajeno exigiría adivinar la intención del otro flujo — exactamente lo que este cierre-interestadocumentar en vez de tapar.
- **Condición de re-apertura:** cuando el flujo concurrente aterrice, arrastrar estas 22 (13 + 9 de contaminación) con el mismo método del cierre: triage archivo por archivo + `make test-fast` como baseline innegociable.
- **Advertencia operativa:** con `-n 4` un worker puede morir (OOM) y **abortar la corrida completa** sin que pytest lo diga en el resumen (`INTERNALERROR` en 165 líneas, 1.449 tests sin correr). Para un conteo confiable hay que correr **serial**.

## 37. `notify-everything` re-landado tras perderse en un commit (2026-10-01) — P1 proceso

- **Qué pasó:** la sesión del 2026-09-16 registró `NOTIFY-EVERYTHING` DONE con 16/16 verdes. Al abrir el árbol el 2026-10-01, de esos 16 solo sobrevivían 2 símbolos (`cores/notifications/emit.py` y `api/lifespan._emit_job_failed`): los 7 call sites de `emit()`, los 13 keys de `EVENT_PUSH_MAP` y el endpoint `/api/notifications/pending-config` **nunca aterrizaron**. 12 tests en rojo lo delataron.
- **Causa:** el commit `a0e11ac1`/`47a82daa` usó `add -A` sobre un working tree compartido; el trabajo sin commitear de la sesión paralela se llevó puesto lo suyo y lo ajeno a la vez.
- **Fix:** re-landado (12 keys del mapa + 5 eventos de bounty + submitted/confirmed/DLQ + killswitch on/off + finding + report + payout + `pending-config`). **16/16**, verificado a prueba de fallo.
- **Regla permanente:** *un `class X: pass` con docstring "for backward compatibility" es una capability declarada, no un detalle pendiente.* El de `ExecutionPolicy` medía 6 líneas y tumbaba 10 endpoints. Cuando algo que el motor llama no tiene cuerpo, es P0 aunque el archivo sea trivial.
- **Corolario de proceso:** antes de escribir `DONE` en `.ai/`, **verificar que el código está en el árbol**. La evidencia mínima es una request autenticada al endpoint, no un test verde de la sesión anterior.

## 38. `test_notify_everything` dependía de que otro test creara la tabla `targets` (2026-10-01) — cerrado

- **Síntoma:** en la suite completa fallaba con `sqlite3.OperationalError: no such table: targets`; aislado pasaba 16/16.
- **Causa:** el test no crea el schema que necesita; `test_command_center.py` dropea `targets` de la DB compartida y este test heredaba esa dependencia.
- **Fix:** `Base.metadata.create_all(bind=engine, tables=[Target.__table__, Finding.__table__])` dentro del test. Verde aislado (16/16) y junto al culpable (24/24).
- **Regla permanente:** un test que depende del orden es un test que reporta bugs falsos. La suite serial completa es el gate, no el test aislado.

## 39. Lane AI-eval: Mercor cableado, Turing bloqueado por anti-bot (2026-10-01) — P1

**Contexto:** el objetivo del owner es maximizar fuentes/adapters **sin experiencia ni entrevista**. La auditoría encontró que el catálogo ya tenía **194 de 196 fuentes** con esa condición: lo que faltaba no era catálogo sino el **adapter** que las trajera a discovery. `cores/pulse/` (documentado como existente) **no existe**.

- **Mercor VERIFICADO y cableado** (`api/adapters/direct_work_ai_eval.py`): lee el payload `__NEXT_DATA__` que el sitio ya publica (sin API pública, sin bypass). **331 listings, 97 tech, rate real** (`rateMin`/`rateMax`/`payRateFrequency`). Top observado **$200/h** (Legacy Codebase Migration, Cybersecurity Research). Se filtran 2 cosas, ambas medidas: dominios no técnicos (medicina/legal no son comparables) y listings `eligibleLocation` restringidos a países bloqueados (**20 de 68** eran solo-USA). Los 37 con `eligibleLocation: []` son Remote sin restricción.
- **Turing NO implementado, a propósito:** `turing.com/jobs` devuelve **1055 bytes** con protección anti-bot y `/api/jobs` da 404. No es scrapeable de forma fiable. No se implementa un adapter que devolvería 0 y parecería "integrado".
- **Filtro corregido:** `StrictFilter` rechazaba todo rol con `payment == 0` como `unclear_payment`, pero en un contrato por hora `payment` es 0 **por construcción** y el dinero está en `hourly_rate_usd`. Sin el fix, los 97 roles de Mercor se rechazaban. La regla ahora distingue "sin precio publicado" de "precio por hora".
- **`_is_programmable_dev_work` NO se tocó, a propósito:** el WorkBank es el banco de **entregables con PR**; un rol de AI-eval no es un PR. Forzarlos a `ready_to_deliver` sería mentir sobre la forma de cobro. Quedan en el radar con motivo `not_programmable_dev_work` visible, que es la conducta honesta.
- **Pendiente humano:** sin 1 rail de cobro y sin cuenta Mercor, los 97 roles son **visibles pero no cobrables**. El adapter no acelera el primer cobro; hace que cuando exista la cuenta, el sistema muestre dónde están en vez de buscarlas a mano.

## 44. `git checkout` durante una prueba de fallo revirtió trabajo previo (2026-10-01) — proceso

- **Qué pasó:** al probar un bug invertí `api/adapters/direct_work_github_bounty.py` y restauré con `git checkout <archivo>`. El archivo tenía **cambios sin commitear de esta misma sesión** que no estaban en HEAD: `_normalize_keywords`, keywords OR-group en `_build_queries`, `_MAX_SANE_REWARD_USD`/`_first_amount` (techo de $10M que evita `$1e82`) y la entrada `mercor` del audit. Todo revivido desde la lectura de los tests que fallaban.
- **Lección:** `git checkout <file>` **NO** es una restauración: es una reversión a HEAD. Para deshacer una prueba de fallo se usa un backup explícito (en esta sesión: `/tmp/opencode/wb_ok.py`) o `git stash`/`git diff` — nunca `checkout` sobre un archivo con WIP.
- **Detectado por:** los tests que ya existían (`test_curated_sources.py`, `test_night_session_fixes.py`)fallen de golpe. Un suite verde es también un detector de que rompiste algo.

## 45. Fiverr/freelance vetado por el owner + adapters de las 145 fuentes ACTIVE (2026-10-01)

- **Decisión del owner:** *"al final no quiero trabajar en fiverr ni en freelance"*. Invierte la del 2026-09-30 (fiverr ACTIVE y opcional). **El carril completo queda hard-excluded** (`_HARD_EXCLUDED` += `fiverr`, `freelance`): no admite override por HTTP, así que un clic no puede devolver a la cola un carril vetado. El motor de gigs sigue en el árbol (`cores/fiverr/`) por si el owner cambia de opinión. 9 items de fiverr eliminados del banco; adapter desregistrado.
- **Consecuencia honesta:** con fiverr fuera, el banco accionable quedó en **0**. Fiverr era el único "pago real" que quedaba. Las lanes reales son ahora AI-eval, bug bounty y dev bounty.
- **Adapter nuevo — directorio de bug bounty** (`api/adapters/direct_work_bug_bounty_directory.py`): lee el **directorio público de programas** de cada plataforma (la misma página que abre un researcher; sin auth, sin bypass). Cubre la lane más densa del catálogo: **77 fuentes bug-bounty**, sin experiencia y sin entrevista.
  · **Intigriti verificado:** 3 programas con rango publicado y atribuible (Adobe $15k, Nvidia $15k, Coveo $5.5k). Se reporta el **techo** del rango, no el piso (`$75 – $15,000` ⇒ $15.000).
  · **Bugcrowd EXCLUIDO:** la página devuelve 200/111 KB pero no publica figura por programa parseable.
  · **YesWeHack EXCLUIDO:** 200/366 KB con rangos, pero el markup **no aísla un programa por link** (distancia link→cifra medida: 1.017–24.624 chars) ⇒ una cifra puede pertenecer a otro programa. Atribuirlo sería exactamente la fabricación que esta sesión viene eliminando. Re-add cuando la página sea parseable.
- **Dos bugs de parseo encontrados midiendo, no leyendo:** (1) una ventana fija de búsqueda **roba la cifra del programa vecino** — se divide por link, que sí aísla la tarjeta; (2) el primer importe de `$75 – $15,000` es el **piso**, y reportarlo como "hasta $X" subestima.
- **Regla permanente:** *una cifra que no se puede atribuir a un programa no se publica.* Un adapter que devuelve 0 es inútil; uno que devuelve cifras ajenas es peor.
- **Verificación:** 15/14 guards nuevos, **3 bugs reintroducidos ⇒ la suite cae** (ventana fija / piso-como-techo / emitir-sin-rango). 205 en las suites afectadas, `test-fast` 103/1, ruff limpio.

## 49. Dos `ApprovalGate` vivos con el MISMO nombre (2026-10-04) — P0 semántico, huérfano decorando el canónico

**Descubierto midiendo el blast radius de autonomía, no leyendo.**

`cores/approval/gate.py` (565 L) y `cores/approval/gates.py` (204 L) definen
**ambos** `class ApprovalGate` **y** ambos `get_approval_gate()`. Un import
equivocado resuelve en silencio a la política equivocada.

| | `gate.py` | `gates.py` |
|---|---|---|
| Nivel de autonomy | `AutonomyPolicy` LITE/FULL/CAPITAL | `ApprovalLevel` AUTO/NOTIFICATION/CONFIRMATION/FULL_REVIEW |
| Riesgo | `RiskLevel` LOW/MEDIUM/HIGH/CRITICAL | — |
| `ActionType` | 10 acciones | 8 acciones |
| Overlap de `ActionType` | **sólo `submit_report`** | |
| Consumidor de producción | **0** | `api/routers/approvals.py` ×3 |

**El riesgo real:** `gate.py` tiene los **3 modos del producto** (LITE/FULL/CAPITAL,
los mismos que `usePrimaryMode.ts:3` y `settings_runtime.py:56`) y una taxonomía
de riesgo de 4 niveles que `gates.py` no tiene. No es un duplicado: es **media
política perdida**.

**Bug adyacente (menor):** `api/routers/settings_runtime.py:56` re-valida la lista
a mano — `valid_modes = ["lite","full","capital"]` — en vez de usar
`AutonomyPolicy`. El enum no es la fuente de verdad; el router sí. Un cuarto modo
added al enum no sería aceptado por la API.

**Por qué NO se arregla acá:** borrar `gate.py` rompe `test_approval_gate.py`
(verde hoy, 0 consumidores de producción). Y decidir cuál de las dos políticas
gana — si el gate canónico tiene niveles de riesgo, si tiene los modos — es
**decisión de producto**, no limpieza. Un MERGE mal hecho aquí cambia qué acciones
requieren aprobación: es un cambio de seguridad.

**Regla permanente:** *dos módulos con el mismo nombre exportado y semántica
distinta no son duplicado, son un landmine.* Y *un enum que nadie consulta
no es la SSOT aunque esté definido* — el hardcode paralelo en el router es la
prueba de que no lo es.

## 48. ✅ CERRADO 2026-10-04 — 44 variables CSS sin definir (P2)

**Resuelto en paralelo por otro flujo** con una migración de 132 líneas en
`frontend/src/design/tokens.css` (tokens component-scoped + `--cycle-*`).

**Medido hoy tras la migración:** 310 tokens definidos, 183 usados,
**0 referenciadas sin definir**. Los 44 casos se repartían entre los que el padre
inyecta por inline style (`--badge-color`, `--mode-color`, `--confidence-color`
— ahora con default en el token) y los que faltaban de verdad (`--ownex-bg-elevated`,
`--ownex-border`, `--ownex-primary`, los `--cycle-*`).

**El número "43" del audit frontend 2026-09-30 y el "44" que medí son el mismo
fenómeno con distinto criterio de conteo.** La cifra real dependía de si se
contaban los `var(--x)` con default inline.

**Guard:** ninguno específico (no hay medición de vars colgantes en la suite), pero
`test_no_arbitrary_hex_in_vue_components` falla si un `.vue` reintroduce un hex
fuera del SSOT, y `test_no_red_in_any_live_stylesheet` cubre cualquier
stylesheet. **Deuda de tooling, no de CSS**: falta el guard que cuente
`var(--x)` usadas contra las definidas.

## 50. FASE 0 — consolidación: 4.166 líneas muertas borradas, 3 bugs de producción destapados (2026-10-04)

**Borrado (11 módulos `.py` sombreados, 4.166L, 0 imports verificados uno por uno):**
`cores/{commander,memory,autonomy,discovery_engine,platform_connectors,execution_queue,backup}.py` + `cores/opportunity/adapters/{forge,pulse,security}.py` + `apps/odyssey/providers.py`. Todos tenían un paquete hermano con `__init__.py`, así que Python resolvía el **paquete** y el `.py` era inalcanzable. Backup en `/tmp/opencode/backup_f0/`. Tras el borrado: `import api.main` OK y `test-fast` 103/1 sin cambios.

**3 bugs REALES destapados al arreglar los imports rotos** (ninguno era cosmético):
1. **`cores/commander/` era inimportable.** `__init__.py` re-exportaba `AgentRegistry` y `CapabilityRegistry` desde `agent_registry`/`capability_registry`, que **nunca fueron commiteados** (`git log` vacío). El canónico de capacidades es `cores/capabilities/registry.py:61`; se quitó el re-export en vez de inventar las clases.
2. **`context_engine.py:26` importaba `cores.ai_router.failover`**, ruta que no existe (el módulo tiene `engine.py` y `provider_store.py`). Canónico: `cores/ai/runtime/failover.py`.
3. **`context_engine` leía una API inexistente de `FailoverEngine`** (`failover_chain`, `_history`, `get_history`): el `try/except` tragaba el `AttributeError` y el bloque "failover" salía **siempre con error** en silencio. Ahora lee `_failure_counts`/`_circuit_open` reales.
4. **`create_autonomous_workflow()` reventaba** al pasarle `None` a `AlgoraExecutor`, que exige `AlgoraConfig` — el contrato que el propio registry documenta ("never a plain dict"). `AttributeError: 'NoneType' has no attribute 'work_dir'`.

**Resultado medido:** `tests/test_e2e_copilot.py` pasó de **10 rojos a 33/33 verdes**. Los 10 eran baseline documentado como "ajeno/concurrente"; Resultó ser drift real y encadenado — cada fix destapaba el siguiente.

**Tests actualizados por estar viejos (no porConveniencia):**
- `test_1_coder_agent_imports` pineaba `config.model`, campo que la arquitectura eliminó: el modelo se resuelve por OAR dentro de `CodeGenerator._llm_complete`. Ahora verifica `require_approval_for_pr` (el gate real).
- `test_3_opportunity_orchestrator` pineaba `forge_adapters`, que murió con el orquestador original de `core/`. La clase es hoy un wrapper sobre `OpportunityEngine`; el test verifica esa API.

**NO se borró (deuda, no código muerto):**
- `cores/contracts/api.py` — 594L con 47 contratos declarados y **0 imports**. El paquete `contracts` sí se usa (`normalizers`, `validator`), pero este módulo es la API de diseño que nunca se cableó. Contiene el `Opportunity` que duplica el canónico de `direct_work_engine/models.py:491`. Decidir: cablearlo o borrarlo.
- `cores/scheduler/jobs/bug_bounty.py` — `register_bb_jobs()` existe y nadie lo llama. Depende de `LifeScheduler` (uno de los 8 schedulers, no el canónico `CoreScheduler`). Conectarlo exigiría decidir cuál scheduler es real.

**Regla permanente:** *un paquete que promete módulos que nunca se commitearon es peor que uno sin módulos* — deja el árbol inimportable y esconde el código que sí existe.

## 51. FASE 1 — 7 `VulnType` declarados sin generador, y 3 sin precio (2026-10-04) — P0 revenue, CERRADO

**El hallazgo de revenue de la sesión de los 10 posts, verificado leyendo (no por
el post).**

`cores/validation/models.py:29-50` declara **21** clases de vulnerabilidad.
`cores/offensive/reasoners/` tenía **13 archivos**. La diferencia son 7 clases que
el sistema **declaraba支持 y no generaba jamás**:

| VulnType | Tenía precio (`VULN_PAYOUT_MULTIPLIER`) | Tenía acceptance (`BASE_ACCEPTANCE`) | EV medido |
|---|---|---|---|
| `csrf` | 0.6 | 0.35 | 0.21 |
| `lfi` | 1.2 | 0.50 | 0.60 |
| `cmdi` | **2.0** | 0.60 | **1.20** ← mayor EV |
| `race_condition` | 1.0 | **faltaba** | — |
| `cors` | 0.5 | **faltaba** | — |
| `open_redirect` | 0.3 | **faltaba** | — |
| `generic` | 0.5 | 0.30 | 0.15 |

**Por qué era dinero, no cosmética:** `race_condition`, `cors` y `open_redirect`
tenían multiplier pero **ningún precio de aceptación** ⇒ `BASE_ACCEPTANCE.get(v,
0.3)` caía al default ⇒ **no participaban en el ranking económico**. El sistema
tenía 3 clases que no sabía cuánto pagaban.

**✅ CERRADO 2026-10-04.** 6 reasoners nuevos (`cmdi`, `lfi`, `race_condition`,
`cors`, `csrf`, `open_redirect`) + `generic` implementado como detector real de
anomalías (no bucket vacío). `BASE_ACCEPTANCE` y `VALIDATION_EFFORT_MINUTES`
completos para los 3 que faltaban. **21/21 `VulnType` con generador y con
precio.**

**`generic` NO se borró aunque parecía código muerto:** es el fallback de **8
módulos** (`planner.py:373`, `curiosity.py:178`, `attack_planner.py:74`,
`probe/engine.py:699`, `contradiction.py:247`, `challenger.py:381`). Borrarlo
hubiera roto 8 call sites. Se implementó como detector de anomalías real
(parámetros sospechosos, headers de seguridad faltantes, stack traces en la
respuesta, path traversal, endpoints admin/debug).

**Regla permanente:** *un enum que declara 21 miembros no es una capability: es
una promesa. La capability es la razón que produce una hipótesis para cada
miembro.* Y *si algo tiene multiplier pero no acceptance, no está en el ranking
— está decorado.*

## 52. El failover de OAR era código muerto para todo error HTTP (2026-10-04) — P0, CERRADO

**Cadena medida leyendo (no opinando):**
```
adapters.py:359-369   non-200 → return AIResponse(finish_reason="error")   ← NO lanza
__init__.py:286       await provider.chat(...)                             ← no hay excepción
__init__.py:289-291   → record_success(provider_id)                        ← circuit nunca abre
resilience.py:87      429: ("quota_exceeded", CIRCUIT)                     ← inalcanzable
```
El adapter **devolvía** en vez de lanzar ⇒ el runtime veía éxito ⇒
`record_success` ⇒ `failover.py:57` **nunca abría el circuito**. Y
`__init__.py:321` clasificaba el error **sin `status_code`** y **descartaba** el
`RetryPolicy` calculado. El mapa 429 era código muerto.

**Consecuencia económica:** el free tier de Groq (30 rpm) **no tenía salida**.
"2 providers + fallback en 429" era imposible de aplicar — y los free tiers son
exactamente los que dan 429.

**✅ CERRADO 2026-10-04.** `finish_reason == "error"` se trata como fallo:
`record_failure(provider_id, ProviderError(...))` + `continue` al siguiente
provider. El adapter **no** se cambió a lanzar (rompería el contrato público de
`chat()`). Sólo después de este fix se activaron `groq`, `cerebras`, `together`,
`deepinfra` — que tenían factory escrita desde antes (`adapters.py:497,563,517,540`)
pero no estaban en `enabled_providers`.

**Regla permanente:** *un failover que nunca se ejecutó no es un failover: es un
`try/except` decorativo.* Y *un adapter que traga sus errores y los devuelve como
respuesta successfully-shape hace el circuit breaker inalcanzable para toda la
clase de errores HTTP* —incluida la que más importa en free tiers.

## 53. `/api/system/tools` no existía: la pestaña "Herramientas" mentía (2026-10-04) — P2, CERRADO

`frontend/src/stores/settings.ts:479` llama `GET /system/tools`. Ese endpoint
**no existía** en `api/routers/system.py` ⇒ 404 ⇒ **Settings → Herramientas
mostraba las 10 herramientas como no instaladas, siempre**. El endpoint correcto
ya existía y estaba cableado en otro sitio (`/api/stability/tools`,
`stability.py:48`, → `ecosystem.inventory()`).

**✅ CERRADO 2026-10-04.** Un endpoint nuevo en `api/routers/system.py` que
reutiliza `get_tool_ecosystem().inventory()` (20 tools, sin lógica duplicada).
Devuelve 401 sin credencial (= existe, requiere auth) en vez de 404 (= no existe).

**Corolario del mismo carril:** `/oar/doctor` sigue con **0 consumidores en el
frontend** — el fetch existe (`ownexData.ts:1598` guarda en `AiCenterState.oar`)
pero **ningún componente lee `ai.oar`**. El dato se descarga y se descarta. Queda
abierto: es cableado de UI, no bug de backend.

## 54. FASE 0 — data layer unificado: 63 `fetch()` crudos migrados al cliente `api` (2026-10-04)

**Por qué no era limpieza cosmética:** `fetch()` crudo **no manda `Authorization`** ni resuelve el puerto del sidecar. Al cerrar el P0 de auth (139 rutas root-mounted ahora exigiendo sesión), cada uno de esos call sites pasó a devolver **401**. El frontend tenía dos capas de datos compitiendo y 71 llamadas crudas por fuera de las dos.

- **Migrados 63 de 71** al cliente `api` (`frontend/src/lib/api.ts`), que ya centraliza token, resolución de puerto (Tauri), `resolveApiUrl` para root-mounted, refresh de backend y 401 con logout de sesión.
- **8 quedan, y cada uno con razón** (no son deuda):
  · `ReportDetail.vue` + `stores/report.ts` — downloads **blob** (export PDF); el cliente devuelve JSON.
  · `ComputerUse.vue` — mismo puerto pero con `apiBase` propio y flujo de Computer Use.
  · `useThemeEngine.ts` — assets estáticos (`/assets/branding/themes/*.json`), sin auth por diseño.
  · `useOwnVoice.ts` — TTS con su propio manejo de audio y token.
  · `moneyprinter.ts` — **servicio externo** (`MPT_BASE_URL`), no es nuestro backend.
- **Bug encontrado por el build, invisible para tsc y los tests:** la migración dejó un `})` huérfano en `AlertPopup.vue` ⇒ `Missing catch or finally clause`. `vue-tsc --noEmit` dio 0 y los 191 tests pasaron; lo cazó `vite build`. Por eso el build es gate, no un extra.
- **También en FASE 0:** `withGlobalTauri: false` (los 3 comandos IPC ya no son alcanzables desde cualquier JS de la página), 3 deps muertas fuera (`@supabase/supabase-js`, `class-variance-authority`, `xterm` v5 — se usa `@xterm/xterm`), y `frontend/tauri.config.json` (v1 obsoleto, schema de Tauri v2, 0 referencias) borrado.

**Verificación:** backend `test-fast` 103/1 · frontend 191/191 · `vue-tsc` 0 · `vite build` 12.1s · `import api.main` OK.

**Regla permanente:** *dos capas de datos compitiendo no es arquitectura, es dos verdades sobre si el usuario está autenticado.* Y: *el gate que atrapa un error de sintaxis es el que compila, no el que chequea tipos* — `vue-tsc` dio 0 con un bloque `try` sin `catch`.

## 56. ✅ CERRADO 2026-10-04 — 2 bugs P0 en la cadena GITHUB_TOKEN → submission → revenue

Auditado eslabón por eslabón al dejar el `GITHUB_TOKEN` pendiente. Los tres
eslabones existen, pero **dos de ellos tenían un agujero que hacía que pegar el
token no hubiera funcionado**.

**Bug 1 — el fail-closed del adapter era código muerto.**
`_execute_submission` hacía `raise ValueError("No API key configured")` cuando
`_get_api_key` no encontraba nada. Pero `GitHubBountyAdapter.submit_work()`
tiene un camino `needs_access` fail-closed escrito exactamente para ese caso
(`requirement` con el path exacto, `human_gate: required_before_send`,
`attempted_external_action: false`) — y **nunca se alcanzaba**. Peor: `_get_api_key`
sólo consultaba `IdentityVault`, así que un token pegado en
`~/.config/ownex/opportunity.env` — que es exactamente donde el propio adapter
dice pegarlo — era **ignorado**, y el item iba a DLQ tras 3 reintentos con esperas.

*Fix:* el motor ahora usa el mismo orden de resolución que los adapters
(`env → credentials vault → IdentityVault`, en `_ENV_KEY_NAMES` /
`_VAULT_ATTR_BY_PLATFORM` — SSOT compartido), y no aborta antes de darle la
oportunidad al adapter de resolver su propia credencial o devolver su
`needs_access`. El DLQ real se preserva para plataformas sin adapter.

**Bug 2 — un envío fallido se registraba como enviado.**
`record.status = SubmissionStatus.SUBMITTED` se seteaba incondicionalmente,
*antes* de mirar `result["success"]`. Consecuencias medidas:
1. el revenue bridge recibía `SUBMITTED` → `REVIEWING` (`execution_bridge:8,182`),
   un estado pendiente que **no ocurrió**;
2. `_find_submission` (línea del skip) contaba el item como ya-enviado para
   siempre, salvo `force=True` — **el reintento quedaba muerto**.

*Fix:* `SUBMITTED` sólo dentro de la rama `success`. Un fallo queda `FAILED`
mientras reintenta y `DLQ` al agotar, con `submitted_at = None`.

**Guard:** `tests/test_github_token_readiness.py` — 10/10, con 3 mutaciones
verificadas (revertir el fix del `raise` → 4 tests caen; revertir la resolución
por env → 1 cae; revertir el status condicional → 3 caen).

**Nota de método:** `SubmissionStatus.FAILED` existía en el enum y **nunca se
usaba** en el loop de reintentos. El bug 2 no era un descuido de una línea: era
un estado entero del sistema que nadie había recorrido.

## 55. El MERGE de `cores/validation/` está BLOQUEADO por migración en curso (2026-10-04) — proceso

**El solapamiento sí está medido** (`docs/PRODUCT_MAP.md` §3.2): 4 clases
compitiendo — `ValidationBridge` (316 L), `ValidationEngine` (460 L),
`ValidationLoopEngine` (282 L), `ValidationPlanner` (493 L). La API usa
`LoopEngine` (6) y `Bridge` (2); las otras dos sólo las consumen sus tests.

**El merge NO se ejecuta ahora** porque `cores/validation/` tiene **5 ficheros
modificados sin commitear** (231 líneas): migración de
`ConfidenceScorer.calculate()` para el piloto LAYA. Su consecuencia medible:
**11 tests rojos** en `test_validation_engine.py` + `test_validation_bridge.py`,
que `make test-fast` **no cubre** (sigue 103/1).

**Por qué importa el Procedimiento:** con 11 rojos de otro cambio en el mismo
módulo, un rojo más sería **imposible de atribuir**. El dato no es "el módulo
está roto" — es "no sé qué parte del módulo está rota y por quién".

**Orden requerido antes de intentar el merge:**
1. El otro flujo commitea la migración LAYA y sus 11 tests vuelven a verde.
2. `make test` (no `test-fast`) para el conteo real de la suite completa.
3. `graft callers <symbol> --depth 2` por clase, para decidir `REMOVE` vs
   `DEPRECATE` de `ValidationEngine` y `ValidationPlanner`.

**Regla permanente:** *un merge es correcto cuando los tests del módulo están
verdes y el módulo no tiene trabajo sin commitear. Mientras haya reds de otro
cambio en el mismo módulo, tocarlo es trabajar a ciegas.* Y corolario:
*`test-fast` verde no es evidencia de que el módulo esté sano — es evidencia de
que el gate no lo cubre.*

