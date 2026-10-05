# OWNEX — FRONTEND RELEASE AUDIT (2026-09-30)

> Auditoría técnica completa del frontend + release HTTP + QA automatizado con Playwright.
> **DoD cumplido.** Evidencia medida, no declarada.

---

## 0. Decisiones tomadas sobre las preguntas abiertas

Las 4 preguntas del audit **no fueron respondidas** por el owner (la respuesta fue
*"crea un archivo .md con tus preguntas y un resumen de la auditoría"*, que es una
redirección, no una decisión). El owner delegó luego: *"hacelo como te parezca mejor"*.

**Resueltas por medición, no por opinión.** Cada una tiene evidencia.

| # | Decisión | Fundamento |
|---|---|---|
| **Q1** | Auth bypass: **documentar, no tocar** el backend | Radio de impacto alto sobre un sistema vivo; mitigado por bind `127.0.0.1` + CSRF + single-user. Detalle + receta de fix en `KNOWN_DEBT #32`. |
| **Q2** | `vue-tsc = PASS` → moot | **El baseline ya era 0.** La pregunta era innecesaria; el riesgo real era que nunca se ejecutara en CI, y eso sí se corrigió. |
| **Q3** | 2 tests: **borrar, no repuntar** | Verifiqué que **ninguno** de sus strings existe en ningún `.vue` del árbol. Repuntarlos habría creado tests que pasan sin afirmar nada. |
| **Q4** | Static server: **cero dependencias** | Gastar 0 de las 1 dependencias del presupuesto. `express` no está instalado y sumaría un paquete para ~200 líneas. |

### HALLAZGO CRÍTICO derivado de Q2 — el type-check NO ve esta clase de bug

Al cerrar Q2 medí algo que **no estaba en el prompt** y que cambia cómo hay que mirar
todo lo demás:

```
Con el import `useHuntStore` BORRADO de IncomeHome.vue (el P0-A reintroducido):

  vue-tsc --noEmit   → exit 0        ← NO lo detecta
  vitest run         → 17/17 passed  ← NO lo detecta
  npm run build      → ✓ passes      ← NO lo detecta
  Playwright E2E     → FALLA         ← ÚNICO que lo detecta
```

Motivo: las referencias del template en `<script setup>` compilan a lookups en runtime
(`_ctx.x`), no a errores de tipo. Un identificador sin importar no es un error de
TypeScript; es un `ReferenceError` en el navegador.

**Consecuencia operativa:** el type-check y los unit tests **no son** un guard válido
para "la página monta". **El E2E es el único guard de esa clase**, y por eso el job
`test-e2e` quedó en el gate de `verify` de CI (§B). Intentar cubrirlo con un unit test
de montaje se fight-ea con el teardown asíncrono de `load()` en jsdom y no aporta: el
E2E lo cubre en ~2 min de forma determinista.

Corolario para futuros agentes: **no confiar en `vue-tsc` verde como prueba de que una
vista renderiza.** Sólo un navegador lo demuestra.

---

## Veredicto

```
RELEASE READY (frontend)
```

> ⚠️ **Alcance:** `RELEASE READY` aplica **al frontend**. **No** declara que el backend
> sea seguro: queda abierto **Q1**, un P0 de auth (264 rutas root-mounted sin credencial)
> documentado en `KNOWN_DEBT #32` con su receta de fix, deliberadamente **no** aplicado
> por radio de impacto sobre el sistema vivo. Las 4 preguntas de la auditoría están
> resueltas por medición en §0.

El frontend **no era utilizable** al empezar: la ruta raíz `/` (Command Center) no montaba.
Ahora arranca por HTTP, se conecta al backend real, y tiene QA automatizado que **falla
de verdad** cuando el código se rompe.

| Gate | Antes | Después |
|---|---|---|
| `npm run build` | ✅ pasaba | ✅ pasa |
| `vue-tsc --noEmit` | ⚠️ nunca se ejecutó en CI | ✅ **0 errores** (y ahora corre en CI) |
| Frontend por HTTP | ❌ sin static server funcional | ✅ `http://127.0.0.1:8080` |
| Ruta `/` monta | ❌ **ReferenceError en setup()** | ✅ |
| `autoLogin` funciona | ❌ **nunca** (contrato roto) | ✅ |
| Playwright arranca | ❌ **webServer apuntaba fuera del repo** | ✅ |
| Playwright detecta bugs | ❌ **0 de 8 tests podían fallar** | ✅ **28/28, verificado que falla** |
| `vitest` | ❌ 2 suites rojas | ✅ **17/17, 191 tests** |
| `make test-fast` | ✅ 103/1 | ✅ **103/1** (sin regresión) |
| CI corre typecheck/unit/E2E | ❌ 0 de 5 workflows | ✅ 3 gates nuevos |

---

## A. Estado anterior — qué NO funcionaba

### P0-A · La ruta raíz no montaba

`frontend/src/pages/IncomeHome.vue` es el componente de `/` (`router/index.ts:82`).
Usaba identificadores **sin importar**:

| Identificador | Ubicación | Efecto |
|---|---|---|
| `useHuntStore` | `IncomeHome.vue:143` (top-level de `setup()`) | **ReferenceError** |
| `api` | 5 call sites | **ReferenceError** |
| `Card` / `Badge` | 9 + 4 usos en template | elemento desconocido |

Sin auto-import (`vite.config.ts` no tiene `unplugin-auto-import`) ni registro global
(`main.ts` no tiene `app.component()`), no había forma de que resolvieran.

**Por qué nadie lo vio:** `vite build` **no** resuelve identificadores de template/script,
y el CI corría build pero nunca `vue-tsc`. El bug atravesó el CI entero.

### P0-B · `autoLogin` nunca podía tener éxito

Contrato roto en las dos puntas:

- **Backend** `api/routers/auth.py:46` → `ok(result)` → envelope
  `{"version","schema","data":{"token",…},"error","timestamp"}` (verificado en vivo con `curl`).
- **API client** `lib/api.ts:163` → `return res.json()`, **sin desenvolver el envelope**.
- **Frontend** `stores/auth.ts:73` leía **`res.session.token`** → `undefined` para siempre.

⇒ `setToken()` nunca se llamaba ⇒ `CATEYE-token` nunca se escribía ⇒ `isAuthenticated` false.

`loginWithCredentials` / `register` fallaban antes: mandaban `{email,password}` pero
`LoginRequest` exige **`username`** (`auth_users.py:80-82`) → **422**. Y leían
`res.session.token` cuando la respuesta real es un `TokenResponse` plano con `access_token`.

**Por qué ningún test lo cazó:** `stores/__tests__/auth.test.ts` mockeaba
`{ session: { token: 'auto-token' } }` — una forma que **ningún endpoint emite**.
Era un test de fidelidad de mock, no de contrato.

### P0-C · El QA existente no podía arrancar ni fallar

**(a)** `playwright.config.ts:18` → `npm run dev --prefix ../frontend`, que desde la raíz
resuelve a `/home/adriel/projects/frontend` — **verificado: no existe**. El runner no
podía levantar su propio frontend.

**(b)** Los 8 tests existentes eran vacíos por construcción:

| Aserción | Por qué nunca falla |
|---|---|
| `toBeGreaterThanOrEqual(0)` (×6) | un conteo siempre es ≥ 0 |
| `bodyText.length > 0` (×6) | pasa igual con una pantalla de error |
| `waitForTimeout(300)` | el anti-patrón de sincronización exacto |

**(c)** `retries: 0` + `trace: 'on-first-retry'` → el trace **nunca** se retenía.

### P1 · Otros defectos corregidos

| # | Hallazgo | Corrección |
|---|---|---|
| P1-A | `/today` root-mounted en backend (200 en vivo) pero **sin proxy de Vite** ⇒ en browser devolvía el HTML del SPA donde se esperaba JSON | agregado al proxy + **guard** que probé que falla si se reintroduce |
| P1-C | `CapitalSnapshot` declarado **2 veces** con formas incompatibles; **ninguno** de los 9 campos de dinero coincidía con la respuesta real del backend ⇒ $0 silencioso | tipo wire real + mapper que deja ausente = `null` (UNKNOWN), no 0 |
| Q3 | 2 suites importaban páginas **borradas** (`Dashboard.vue`, `Findings.vue`); sus strings ("Centro de Inteligencia OWNEX", "Findings Pipeline") **no existen en ningún `.vue`** | borradas (repuntearlas habría inventado tests que no significan nada) |

---

## B. Cambios realizados

### Frontend — P0 (bloqueaban la app)

| Archivo | Cambio |
|---|---|
| `frontend/src/pages/IncomeHome.vue` | +`useHuntStore`, +`api`; `<Card>`→`<OwnexCard>` (9), `<Badge>`→`<OwnexBadge>` (4) |
| `frontend/src/pages/Capital.vue` | +`Skeleton`, +`Link2`; `<EmptyState icon=…>` → slot `#icon` |
| `frontend/src/pages/Connections.vue` | +`DoughnutChart` |
| `frontend/src/pages/OutlookCalendar.vue` | +`CardContent` (12 usos) |
| `frontend/src/pages/Settings.vue` | +`Cog`, +`Zap` |
| `frontend/src/components/self-healer/FixPlansList.vue` | +`ApprovalBadge` |

### Frontend — contrato de auth (P0-B)

| Archivo | Cambio |
|---|---|
| `frontend/src/stores/auth.ts` | `autoLogin` lee **`res.data.token`**; `loginWithCredentials(username,…)` y `register(username,email,…)` usan el **`TokenResponse`** real; devuelven `boolean` en vez de rechazar |
| `frontend/src/types/index.ts` | `DeviceLoginEnvelope` / `DeviceLoginData` / `TokenResponse` reales; **eliminado** el `LoginResponse` que ningún endpoint emitía |
| `frontend/src/lib/api.ts` | `login()` alineado al envelope real |
| `frontend/src/stores/__tests__/auth.test.ts` | **reescrito con las formas reales** + guarda de regresión: un envelope sin `data.token` **no** autentica (12→13 tests) |

### Contrato API (P1)

| Archivo | Cambio |
|---|---|
| `frontend/src/services/ownexData.ts` | `CapitalSnapshotWire` (forma real) + `CapitalSnapshot` (vista con `null`=UNKNOWN) + mapper; **eliminada** la declaración duplicada |
| `frontend/vite.config.ts` | `/today` al proxy (27 prefijos) |
| `tests/test_frontend_api_contract.py` | **nuevo** `test_vite_dev_proxy_covers_every_root_mounted_prefix` (probado: reintroduce el bug ⇒ falla con `['/today']`) |

### HTTP + QA

| Archivo | Cambio |
|---|---|
| `frontend/spa-server.cjs` | **reescrito sin dependencias** (el anterior `require('express')`, que **no está instalado**): estático + fallback SPA + proxy HTTP + **proxy WebSocket** + 502 explícito en rutas de backend + bloqueo de path traversal |
| `playwright.config.ts` | webServer corregido (`--prefix frontend`), puerto parametrizable, `retries`/`trace`/`screenshot`/`video` coherentes |
| `playwright.prod.config.ts` | **nuevo**: E2E contra el build de producción servido por HTTP |
| `e2e/smoke.spec.ts` | **reescrito**: 13 tests con asserts reales |
| `e2e/navigation.spec.ts` | **reescrito**: 6 tests (shell, deep-link, 404, atrás/adelante, click-navega) |
| `e2e/flows.spec.ts` | **nuevo**: 9 tests de flujos + contrato + fallos |
| `package.json` | `typecheck`, `qa`, `test:e2e:ui/headed/report/prod`, `serve:dist` |
| `.github/workflows/ci.yml` | `test-frontend` ahora corre **typecheck + unit + build**; **nuevo** `test-e2e` con backend + artefactos; ambos en el gate de `verify`; eliminado `--cov=core` (dir borrado el 2026-09-14) |
| `.gitignore` | artefactos de Playwright |

---

## C. HTTP — cómo levantar

### Dev (frontend + backend)
```bash
npm run dev          # backend :8000 + vite :5173 (con proxy)
```

### Producción (build real servido por HTTP)
```bash
npm run build
npm run serve:dist -- --port 8080 --proxy http://127.0.0.1:8000
# → http://127.0.0.1:8080
```

`--proxy` es necesario: en browser (no-Tauri) la app llama a `/api` same-origin
(`lib/backend.ts:159`), así que sin proxy vería 502 en cada fetch.

---

## D. Playwright

| Item | Valor |
|---|---|
| Versión | `@playwright/test` 1.62.1 (**ya estaba instalado** — se reutilizó, no se instaló) |
| Ubicación | raíz del repo (`e2e/`, `playwright.config.ts`) — **ya existía** |
| Tests | **28** (13 smoke · 6 navegación · 9 flujos) |
| Dev server | **28/28 ✅** |
| Build de producción | **28/28 ✅** (`npm run test:e2e:prod`) |
| Flaky | 0 observados en 3 corridas consecutivas de cada suite |

**La prueba de que los tests sirven:** reintroduje el bug P0-A (borré el import de
`useHuntStore`) y la suite **falló** con el error exacto:

```
[ErrorBoundary] ReferenceError: useHuntStore is not defined
    at setup (…/IncomeHome.vue:93:18)
```

Esto reveló algo no obvio y que valía la pena encontrar: un `ReferenceError` en
`<script setup>` **no** dispara `pageerror` — el `ErrorBoundary` del proyecto lo captura y
lo reporta por `console.error`, dejando la zona afectada **vacía** mientras el resto de la
app sigue renderizando. Por eso el guard `#main-content` daba **falso verde**, y por eso
el test ahora filtra `console.error` además de `pageerror`. Sin este paso, la suite
habría dado verde con el Command Center roto.

---

## E. Flujos críticos

| Flujo | Estado | Evidencia |
|---|---|---|
| Command Center monta | ✅ | test "renderiza sus bloques de estado" |
| Navegación / deep-link / atrás-adelante | ✅ | 6 tests |
| 404 sin crash | ✅ | test dedicado |
| Paleta Ctrl+K | ✅ | test |
| `/today` responde JSON real | ✅ | test (cueba el fix de P1-A) |
| P(CASH) con 0 PAID = UNKNOWN | ✅ | test: rechaza un porcentaje numérico |
| Pipeline ≠ caja | ✅ | test sobre `/direct-work/revenue-ledger` |
| Backend caído no rompe el render | ✅ | test con `route.abort` |
| Respuesta vacía no rompe | ✅ | test con `{}` |
| 8 rutas principales sin errores | ✅ | parametrizado |

**No cubierto por E2E (y por qué):** los 38 endpoints inexistentes (§H), los
Human Gate (requieren acción humana) y el login con credenciales reales
(`/auth/users/*` requiere un `User` en DB; el flujo vivo es device-login).

---

## F. Regresión

```
vue-tsc --noEmit      0 errores
vitest                17 files / 191 tests passed  (antes: 2 suites rojas)
npm run build         ✓ built in ~13-15s
make test-fast        103 passed, 1 skipped   ← baseline del proyecto, intacto
contract + endpoints  40 passed
Playwright (dev)      28/28
Playwright (prod)     28/28
```

**Trading: 0 archivos tocados** (verificado con `git status`).
**Semántica económica: intacta.** `EXPECTED ≠ PAID` sigue vigente; el E2E la verifica
en vez de cambiar nada.

---

## G. Performance (medido, sin cambios)

| Señal | Valor | Acción |
|---|---|---|
| Bundle principal | 458 kB (149 kB gzip) | sin cambios |
| Cytoscape | 443 kB (142 kB gzip) | se carga en la vista Knowledge Graph |
| xterm | 283 kB (70 kB gzip) | sólo en `/terminal` |
| `IncomeHome.load()` | **7 etapas `await` serializadas, 13 requests**, re-pide `/revenue/summary` dos veces | → POST_RELEASE (§H) |
| Sin `AbortController` | 0 en todo `src` | → POST_RELEASE |
| `OneActionCard.vue:212` | `setInterval` **sin `clearInterval`** | → POST_RELEASE |

No apliqué optimizaciones: ninguna era bloqueante de release y todas tocan código
estable. Están medidas y documentadas.

---

## H. Known debt — lo que quedó FUERA (decisión explícita, §35)

Nada de esto se implementó. Todo está medido con `file:line`.

| # | Deuda | Tamaño | Por qué fuera |
|---|---|---|---|
| 1 | **Auth bypass**: `api/middleware/auth_middleware.py:49-50` retorna temprano para todo path que **no** empieza con `/api/` ⇒ los 28 namespaces root-mounted (264 rutas, **148 mutantes**) no requieren auth | seguridad | Radio de impacto alto sobre el sistema vivo. Decidido: documentar con receta de fix (`KNOWN_DEBT #32`). Mitigado por bind `127.0.0.1` + CSRF + single-user |
| 2 | 38 llamadas a endpoints inexistentes: `/aegis` (5) y `/odyssey` (3) — routers existen pero **no están montados** en `api/main.py`; `/trading-lab` (6) — el namespace no existe; + 14 más; + 9 con método incorrecto (405) | contrato | Corrección de producto, no de release |
| 3 | 95 call sites usan `fetch`/`axios` crudo, salteando auth, `resolveApiUrl`, 401-handler y el loading counter | refactor | Cambio amplio, no bloqueante |
| 4 | 41 componentes sin consumidores (32% de `components/`), 9 composables, 2 stores, 2 servicios (`controlPanel.ts` = 1530 líneas) | limpieza | §35 |
| 5 | 91 `catch` silenciosos + 4 vacíos; `IncomeHome:95-115` envuelve una promesa async en `try/catch` síncrono (el `catch` es inalcanzable) | calidad | §35 |
| 6 | 43 custom properties CSS **no definidas** vía `var()` (`--ownex-bg-elevated` en 18 archivos, incl. los 3 componentes de estado); `style.css:27` es autorreferencial | visual | §35 |
| 7 | `IncomeHome` muestra UNKNOWN como `$0` en 9 sitios (`:369,373,379,383,387,670,674,678`); `Mission.vue:37-42` ya lo hace bien (`'—'`, `'UNKNOWN'`) | honestidad | Prioridad: la UNKNOWN-as-0 más Riesgosa queda como P2, documentada |
| 8 | `<LoadingState message>` pero el prop es `text` (11 sitios); `<ErrorState :message @retry>` con props inexistentes (13); `<EmptyState icon=…>` cuando `icon` es slot (13) | UX | El texto de carga y el botón de retry nunca renderizan |
| 9 | Handshake WebSocket `/api/ws` → **403 del backend** (preexistente, verificado con `curl` directo). El proxy WS del static server funciona; el 403 es del backend | — | Preexistente, documentado, testeado como condición conocida |
| 10 | 3 de 3 vars `VITE_*` en uso están **sin declarar** en `.env.example`; 2 de 2 declaradas están **sin usar**; no hay interfaz `ImportMetaEnv` | config | §35 |

---

## I. Seguridad

- **Sin secretos** introducidos. `.env.example` no se tocó.
- **Path traversal** bloqueado y verificado (`/../package.json`, `%2e%2e`, `../../etc/passwd` → 404 o index, nunca contenido fuera de `dist/`).
- **Rutas de backend sin proxy** devuelven **502 JSON explícito**, no HTML: el cliente nunca
  parsea HTML como si fuera un success.
- **Auth**: `autoLogin` ahora persiste el token; el envelope ya no se confunde.
  El bypass del ítem H-1 **sigue abierto** y está documentado, no escondido.
- **Sin contaminación de datos**: los E2E son read-only salvo el device-login
  (token en memoria del navegador). No tocan `database/catseye.db`.

---

## J. Release

```
Versión: 7.7.7   (sin cambio — el SSOT ya era consistente en las 6 superficies)
```

Sin bump: no se agregó funcionalidad de producto, se reparó la que ya estaba.
Bump recién cuando el owner cierre el ítem H-1 (auth) o seatiansWorkspace H-2.

### Checklist (§31)

```
[x] frontend build              [x] rutas principales        [x] Playwright smoke
[x] vue-tsc                     [x] Command Center            [x] Playwright flujos críticos
[x] HTTP startup (dev)          [x] Work / Opportunities       [x] Playwright de fallos
[x] HTTP startup (producción)    [x] Revenue / Capital         [x] E2E sobre build de producción
[x] backend startup             [x] Mission / settings        [x] sin errores de consola críticos
[x] API connectivity            [x] estados de carga          [x] sin contaminación de datos
[x] auth (device-login)         [x] estados de error          [x] sin secretos expuestos
[x] navegación / deep-link      [x] estados vacíos            [x] trading sin cambios
[x] Command Palette             [x] responsive / 404          [ ] accessibility formal (axe)
```

`accessibility` queda como P3: no había `axe-core` y agregar un suite WCAG excede
esta misión (§23 lo marca explícitamente como "no un proyecto de certificación").

---

## Reglas permanentes que dejó esta sesión

1. **Un `ReferenceError` en `<script setup>` no lanza `pageerror`.** El `ErrorBoundary`
   lo degrada a `console.error` y deja la zona vacía. Un smoke test que sólo comprueba
   "el layout montó" da **falso verde**. Hay que afirmar contenido específico.
2. **Un mock de test que no copia la forma real del backend es una mentira con tests.**
   El test de auth pasó 12/12 mientras `autoLogin` fallaba en producción.
3. **`vite build` no valida identificadores de template.** Sin `vue-tsc` en CI, un archivo
   puede no montar durante meses sin que nada se entere.
4. **Un dev proxy sin test que lo compare con la lista real se desincroniza solo.**
   `/today` faltó porque nadie leía `vite.config.ts`.
5. **UNKNOWN no es 0.** Un tipo con todos los campos opcionales sobre una respuesta que no
   los manda produce `$0` sin un solo error de tipos.
6. **Un test que no puede fallar no es QA.** `toBeGreaterThanOrEqual(0)` sobre un conteo.
7. **`vue-tsc` verde NO prueba que una vista renderice.** Medido: con el import
   `useHuntStore` borrado de `IncomeHome.vue`, el type-check da **exit 0**, `vitest` da
   **17/17** y `vite build` **pasa**. Sólo el E2E en navegador lo detecta. Las referencias
   del template en `<script setup>` compilan a lookups runtime (`_ctx.x`), no a errores de
   tipo. **El E2E es el único guard de "la página monta"** — por eso `test-e2e` está en el
   gate de `verify`.

---

## Comandos

```bash
npm run qa              # typecheck + unit + e2e  (el gate completo)
npm run typecheck       # vue-tsc --noEmit
npm run test            # vitest (191)
npm run test:e2e        # Playwright vs dev server
npm run test:e2e:ui     # modo interactivo
npm run test:e2e:headed # ver el navegador
npm run test:e2e:report # abrir el HTML report
npm run build && npm run test:e2e:prod   # E2E contra el build real
npm run serve:dist -- --port 8080 --proxy http://127.0.0.1:8000
make test-fast          # 103/1 baseline backend
```
