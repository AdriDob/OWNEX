# Apuntes de Programación — OWNEX

> Apuntes personales de programación aprendidos durante el desarrollo de OWNEX.
> Errores reales con causa raíz, gotchas por stack, patrones del proyecto y comandos.
> Objetivo: no repetir errores. Fuentes: `.ai/LESSONS.md`, `.ai/DECISIONS.md`, `.ai/CURRENT_STATE.md`.

## 1. Errores y fixes con causa raíz (los que rompieron runtime)

### PyInstaller + SQLite: conexión en import-time crashea el bundle
- **Síntoma**: la app Windows moría ~9s después del launch, exit code 1, ventana invisible. PyInstaller windowed → stderr=None → traceback perdido.
- **Causa raíz**: `db.SessionLocal()` en import-time → `sqlite3.OperationalError: unable to open database file` — el bundle no incluye el dir `database/` y `_ensure_db_dir()` corría demasiado tarde (solo en `init_db()`).
- **Fix**: `_ensure_db_dir()` a nivel de módulo, antes de `create_engine`. Vale para cualquier instalación fresca (portable, copias manuales).
- **Lecciones extra**: (1) lanzado desde WSL interop (CWD UNC) la app abría la DB del repo vía 9p → `database is locked`; (2) los diálogos modales PySide6 dejan el proceso vivo → diagnosticar por MainWindowTitle + UI Automation.

### Stub incompleto vs twin con API completa
- **Síntoma**: crash en arranque del desktop: `AttributeError: 'UnifiedMemoryStore' object has no attribute 'set'`.
- **Causa raíz**: `cores/memory/system.py` era un stub (solo `__init__`/`_make_key`) mientras `core/memory/store.py` tiene la API completa. El desktop importa `cores.*`; la web usa `core.*` → la web nunca se enteró.
- **Fix**: completar el stub con persistencia SQLite (`memory_records`, upsert por category+key, TTL ISO, métodos tolerantes a fallos → el bundle nunca crashea).
- **Lección**: los árboles twin no son espejos. Verificar la API real del árbol que importa cada consumidor.

### Imports de árbol equivocado (4 bugs latentes que rompían runtime en silencio)
- `cores.events.event_types` → no existe; `EventType` vive en `cores/agents/types.py` (el `_copilot_hook` del scheduler lanzaba ImportError en cada stage).
- `cores.models` → no existe; los modelos están en `database/models.py` (`/mobile/status` → 500).
- `Target.status` → la columna es `active` (500 en `/mobile/status`).
- `core.ORION_DIR` → solo existe `OWNEX_DIR` (ImportError en `cores/backup.py`).
- **Smoke barato**: `import api.main` después de cada cambio. Detecta estos bugs sin correr nada.

### SQLAlchemy: columna Text con JSON string vs schema dict
- **Síntoma**: `GET /api/cycles` → 500 `ResponseValidationError` — la DB guarda config como JSON string en columna Text pero el schema espera dict.
- **Fix**: `field_validator(mode="before")` en el schema (`parse_config`) → 200 con configs como dict.
- **Lección**: cualquier columna Text que guarde JSON necesita un validator "before" en el Pydantic schema.

### Datetime aware vs naive en SQLite
- **Síntoma**: `TypeError` comparando datetime aware (Python) contra la columna (SQLite guarda strings naive sin offset).
- **Fix**: filtrar en SQL (`started_at < cutoff`), nunca traer a Python y comparar. Matchea correctamente.

### TestClient module-scoped: el jar de cookies autentica tests siguientes
- **Síntoma**: `test_me_unauthenticated` pasaba autenticado (falso negativo en el test).
- **Causa raíz**: la cookie de sesión quedaba en el TestClient compartido entre tests del mismo módulo.
- **Fix**: fixture que limpia las cookies del jar.

### Vistas PySide6 con kwargs extra → QWidget
- **Síntoma**: `AttributeError: 'section' is not a Qt property`.
- **Causa raíz**: vistas (findings/system/surface) pasaban kwargs propios (`section`/`label`/`icon`) a `QWidget.__init__`.
- **Fix**: `BaseView.__init__` hace `kwargs.pop(...)` antes de `super().__init__(**kwargs)`.

### Tests que escriben en la DB real
- **Síntoma**: la suite insertaba targets `test-target.example.com` en `database/catseye.db`.
- **Fix**: en `tests/conftest.py`, forzar `DATABASE_URL=sqlite:////tmp/cateye_test_<pid>.db` ANTES de cualquier import de `database.db`, con guard `RuntimeError` si aparece `catseye.db` + cleanup por sesión. Validado: hash de la DB real idéntico antes/después de la suite.

### Scheduler con jobs definidos pero nunca ejecutados
- **Síntoma**: los 26 jobs de `core/scheduler/jobs.py` registrados pero ninguno corría su handler.
- **Causa raíz**: `_on_job_due` nunca seteado; además `api/main.py` accedía por índice sobre objetos `JobDefinition` (no subscriptables) → TypeError tragado como non-fatal.
- **Fix**: `_resolve_handler()` (module:attr, module.attr, module.Class.method) + `_run_job()` + suscripción a `scheduler:job_due`; `isinstance(job_def, JobDefinition)` en el loop.

### Scans `running` colgados para siempre
- **Síntoma**: 25 scan_runs quedaron en `running` tras caídas del proceso; el scheduler esperaba scans fantasma.
- **Fix**: `recover_stale_scans(max_age_hours=6.0)` marca `running` viejos → `failed` con `finished_at` y outputs; hookeada en boot y en cada tick del scheduler.

### Scraper que inventaba dominios
- **Síntoma**: `convert_to_targets` generaba `{slug}.com` cuando el programa no tenía dominio real.
- **Fix**: skip honesto de programas sin dominio/wildcard real; `_source_status` por fuente (`ok`/`degraded`/`failed`) expuesto en `/api/discovery/stats`.

### Lockfile duplicado engañaba a Dependabot
- **Síntoma**: 10 alertas npm (nanoid 3.3.15, postcss 8.5.16, undici 7.28.0...) mientras el lockfile raíz del workspace ya resolvía versiones corregidas.
- **Causa raíz**: `frontend/package-lock.json` era un artefacto pre-workspaces que Dependabot escaneaba.
- **Fix**: eliminar el duplicado → un solo lockfile (One Source of Truth). `npm audit` → 0 vulns.

### `nohup` no bloquea SIGTERM
- **Síntoma**: el FCC Proxy "se caía solo"; nohup bloquea SIGHUP pero no SIGTERM (el Bash tool de OpenCode lo enviaba al expirar timeout).
- **Fix**: `setsid -w` (nuevo process group, inmune a señales del padre).

### `side_effect` insuficiente en mocks
- **Síntoma**: `StopIteration` en `test_full_scoring_workflow`: el mock proveía 3 lookups pero el engine hace 8 (`on_accept`/`on_reject` hacen sus propios `query().first()`).
- **Lección**: el `side_effect` de un mock debe cubrir TODOS los lookups DB reales del código bajo test.

## 2. Gotchas por stack

### Python / FastAPI
- **Routers lazy**: `app.routes` devuelve stubs `_IncludedRouter` (9 rutas); la verdad está en `app.openapi()['paths']`. Routers usan prefix `/api/<name>`.
- **No exponer `detail=str(e)`**: 245 ocurrencias en 26 routers filtraban internals. Handler global: 5xx → `{"detail": "Internal server error", "operation_id": ...}` + header `X-Operation-Id`; detalle crudo solo al log.
- **CSRF double-submit**: cookie + header `X-CSRF-Token`; excepciones mínimas (health/license/auth); WebSocket bypass: `if scope["type"]=="websocket": return await call_next(request)`. Opt-out explícito: `CATEYE_CSRF_DISABLED=1`.
- **Rate limit por identidad**: Bearer → sub; token inválido → fallback IP; `NO_LIMIT_PREFIXES` (health/version/docs) nunca 429.
- **Enums en payloads**: strings crashean en dataclasses con enums (`AttributeError: 'str' object has no attribute 'name'`); decimales → `Decimal(str(...))` (ej. `/copy/ingest`).
- **Boot con red**: `asyncio.wait_for(opp_engine.discover_all(), timeout=30)` — un discover de red sin timeout congela el boot.
- **No llamar a descubrimientos de red desde el hilo de UI** (freeze en Windows).

### Testing
- Aislamiento de DB en conftest (ver §1).
- Fakes sin red: `_FakeTransport` (httpx module-level, 401→re-login con cola), `_FakeApi`, `_FakeMission`; inyectar vía atributo privado si la property es read-only.
- Qt offscreen: `QT_QPA_PLATFORM=offscreen` ANTES del import de PySide6; `qapp` session-scoped.
- Suite fast determinista: excluir `test_security.py`, `test_vision_gateway.py`, `test_scheduler.py` (red/flaky). `make test-fast` = smoke del dev loop.
- Tests contra la DB real → contaminación. Siempre env var + guard.

### Frontend (Vue 3 + TypeScript + Tailwind 4)
- Tailwind 4: NO `@apply` con opacity modifiers (rompe build).
- Vue SFC: un solo `<script setup>` por componente.
- **Mandate TESLA**: negro puro de fondo, blanco primario, rojo Tesla `#e82127` como ÚNICO acento saturado, colores de estado desaturados, sin glows ni gradientes de color. 0 colores RGB arbitrarios.
- JSON servido como HTML: el fetch de `/assets/branding/themes/{id}.json` caía al SPA fallback (HTML 200) → `SyntaxError: Unexpected token '<'` → guard de `content-type` al cargar.
- Router anidado por sección (la navegación es arquitectura, no cosmética).
- Code splitting: webpackChunkName por sección + lazy loading.

### Desktop (PySide6 / PyInstaller)
- Windowed app: stderr=None → traceback perdido. Capturar con `Start-Process -RedirectStandardError`.
- Bundles sin `database/` → SQLite no puede crear el archivo (ver §1).
- `connect()` con health cache (1.5s/5s) para no pegarle al backend en cada refresh.
- Sidecar con fallback honesto: si no está en el bundle, loguea y no crashea.
- Tauri: campo muerto `plugins.shell.sidecar` panikeaba al arrancar → quitarlo.

### Scheduler / async
- Cooldown por target (1h) + priorización por RewardLearner (la contención previene más bugs que la validación).
- Jobs cron con `croniter` (no corren cada 5s).
- Scans colgados → recovery hookeada en boot + tick.
- Handlers que corren `asyncio.run` desde thread propio (seguro para jobs sync).
- Stage pipeline: cada stage con `_safe()`/try-except → un engine caído no rompe el ciclo; nunca re-score de datos ya calibrados.

## 3. Patrones del proyecto

- **Twin trees `core/` + `cores/`**: el runtime usa AMBOS simultáneamente (~20 wrappers cruzados, 307 archivos byte-idénticos). Editar AMBOS cuando aplique. El scheduler runtime usa SOLO `core/scheduler/jobs.py` (`cores/` es copia vieja). No consolidar sin SSOT demostrado.
- **One Source of Truth**: `.ai/` gana ante cualquier conflicto; manifests apuntan a módulos reales (verificar que los provider strings resuelvan por importlib); un solo lockfile, un solo registro, un solo catálogo (referencias via `payout_ref`, nunca copias).
- **Dual-mode (remoto/local)**: la rama remota mapea contratos HTTP con `getattr` (campos que no existen localmente); la rama local usa `session.query` real. La remota nunca raise → fallback a local.
- **Degradación defensiva**: motor caído → defaults/vacío, NUNCA 500. Cada bloque con try/except.
- **Estabilizar antes que expandir**: progreso = cerrar loops completos funcionales, no agregar features. Si una feature ya existe y funciona → NO tocar (Regla de Oro).
- **Pipeline E2E**: stages conectados y visibles (si no es visible, no existe); todo lo que se construye debe tener endpoint o UI.
- **Auth por device**: auto-login con `device_id` persistido (sin registro manual); cookie httpOnly `ownex-session` como segunda vía (Bearer gana, migración incremental).
- **Scraper honesto**: fuente primaria de datos curada + APIs directas al final (degraded nunca rompe el scrape).
- **Coordinación entre procesos**: otro agente puede correr `git reset --hard` o dejar stashes/conflictos — verificar `git status`/`git diff` antes de testear; un conflict marker en un módulo central rompe la colección de TODA la suite.

## 4. Comandos útiles

| Goal | Command |
|------|---------|
| Tests | `python scripts/dev test` (o `make test`) — excluye `test_security.py` |
| Fast smoke | `python scripts/dev test-fast` / `make test-fast` |
| Lint + typecheck + fast tests | `python scripts/dev check` / `make check` |
| Lint (write fixes) | `python scripts/dev fmt` / `make fmt` |
| Type check (scoped) | `python scripts/dev typecheck-fast` / `make typecheck-fast` |
| Smoke de imports | `.venv/bin/python -c "import api.main"` |
| Lint | `.venv/bin/python -m ruff check .` |
| Backup | `python run.py --backup` |
| Migración PC→PC | `python run.py --migrate-export` / `--migrate <zip>` |
| Health | `curl http://localhost:8000/api/health` |
| Rutas reales de la API | consultar `app.openapi()['paths']` (no `app.routes`) |

## 5. Metodología (lo que funciona)

- **Debuggear por capas**: 1) ¿el servicio responde? 2) ¿formato correcto? 3) ¿ruta? 4) ¿modelo? 5) ¿auth? Los 404 casi nunca significan "no encontrado".
- **Evidencia antes que cambios**: leer `.ai/CURRENT_STATE.md`, `COMPLETED_FEATURES.json` y escanear el código ANTES de escribir (una feature al 80% desconectada produce cero — conectar lo construido vale más que construir).
- **El guard vive donde se ejecuta la acción**: sentinel file + check in-process, no en un script externo.
- **Cambios pequeños y verificables**: 30 líneas > 500; extender antes que reescribir; ruff + pytest después de cada cambio; `import api.main` smoke.
- **Migrar, nunca romper**: conservar compatibilidad (ej. cookie httpOnly coexistente con Bearer).
- **Consolidación > expansión**: fusionar páginas duplicadas con tabs, eliminar lockfiles duplicados, un solo pipeline de branding.

---

*Apuntes de programación OWNEX — compilados 2026-08-17*
