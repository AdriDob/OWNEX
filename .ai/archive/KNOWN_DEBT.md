## 22. Twins `file.py` ↔ `dir/` en `cores/` (2026-09-28) — 1 RESUELTO (P0), resto P2/P3

- **Causa raíz:** cuando existen `X.py` y `X/`, Python resuelve el **paquete**; el módulo queda inalcanzable. Los importadores que expectation el módulo fallan con `ImportError`. El precedente es `core/`→`cores/` (commit `50abfd1c` / `6eb35fbc`).
- **Auditoría de los 3 twins vivos:** `observability` (**P0, resuelto**), `commander`, `platform_connectors`.
- **RESUELTO (P0):** `cores/observability.py` (módulo con `timer`/`record`/`get_metrics`) estaba sombreado por `cores/observability/`. `cores/system_health.py` importaba `get_metrics` del paquete → `ImportError` → **`GET /api/system/status` devolvía 500**: los self-diagnostics estaban caídos, elExactamente el fallo que §27 prohíbe. El timing API se movió a `cores/observability/timing.py` y se re-exporta; el módulo sombreado se borró. Además la lectura de métricas quedó best-effort (una señal opcional ya no puede tumbar el endpoint).
- **Regla permanente:** antes de borrar un módulo `X.py`, grep de `X/`; y todo import opcional dentro de un self-diagnostic va dentro de su propio `try` (el bloque de intelligence ya lo estaba, el de metrics no).

## 23. `cores/self_update/` importaba 2 módulos borrados → recovery muerto (2026-09-28) — RESUELTO (P1)

- **Evidencia:** `cores/self_update/__init__.py` re-exportaba `SelfUpdateEngine`/`UpdateStatus` desde `engine.py` y `UpdateInfo`/`UpdateResult` desde `models.py`. **Ambos archivos fueron borrados** en `50abfd1c`; el directorio solo conserva `__init__.py` + `system.py`. Resultado: `import cores.self_update` → `ModuleNotFoundError`, lo que mataba en silencio a los 2 consumidores vivos de `ProcessManager`:
  - `cores/recovery/engine.py::_action_restart_api` → la acción de healing `restart_api_server` **nunca pudo ejecutarse** (log: `API restart unavailable: No module named 'cores.self_update.engine'`).
  - `api/routers/system.py` (`/api/system/restart`).
- **Fix:** `__init__.py` re-exporta la API real y viva de `system.py` (`SelfUpdateSystem`, `get_self_update_system`, `ProcessManager`, `GitUpdater`, `DependencyInstaller`, `SelfUpdateError`). Verificado: import OK y `ProcessManager.restart_application` existe. **No se invocó el reinicio** (sólo se comprobó la resolutions).
- **Mismo defecto, 2º sitio:** `cores/self_heal/engine.py` listaba 3 rutas con el prefijo borrado `core/` (`core/revenue/engine.py`, `core/self_heal/engine.py`, `core/self_update/engine.py`) → el self-diagnostic reportaba **"missing" archivos que sí existen** y un módulo "broken" inexistente. Reapuntadas a `cores/...`; `cores.self_update.engine` → `cores.self_update`. Tras el fix: **0 módulos broken**.
- **Regla permanente:** un `__init__.py` que re-exporta es un contrato; si borra el módulo, borra también el re-export o rompe toda la cadena de imports en silencio (el síntoma aparece lejos de la causa).

## 17. ✅ core/ eliminado (2026-09-14) — cierra §16
## 32. Gate de admisión de fuentes era sólo P1 (2026-09-30) — RESUELTO

- **Causa:** `source_gate()` sólo verificaba entrevista + $/h (P1). Los criterios **P0** del owner (trabajo técnico verificable, recompensa documentada, entregable claro) no se evaluaban: con 138+ fuentes, una plataforma de servicios genéricos pasaba el gate.
- **Fix:** `admit_source()` en `source_registry.py` deriva los P0 de campos que YA existen en `SourceDefinition` (0 deps, 0 campos nuevos). Veredictos: `ACTIVE` · `CONDITIONAL` · `LOW_VALUE` · `BLOCKED`. Corregido dentro de `source_gate` (P0 corre antes del P1, no lo desactiva).
- **Regla conservada:** datos ausentes = `CONDITIONAL`, **nunca** `BLOCKED` — "no sé si es trabajo técnico" ≠ "sé que no lo es" (misma distinción que scope).
- **Bug bonus cerrado:** `get_status()` leía el store **antes** de `_HARD_EXCLUDED`, así que un canal duro-excluido (workana) podía resucitar con un POST — el store tenía `workana: active` pese al purge 2026-09. Una exclusión permanente del owner ya no admite override por HTTP.

## 31-RESUELTO. Denominador `human_hours` para security work (2026-09-30)

- **Causa:** `net_cash_per_hour` = `net_cash / human_hours`, y `human_hours` se deriva SÓLO de `WorkItem.human_minutes_actual` (`cores/economic_feedback/engine.py:137-146`). Los *programas* de bug bounty se excluyeron del banco (no son tareas), así que security work quedaba sin denominador.
- **Fix (camino documentado, hallazgo→tarea):** `ValidationPromoter._register_security_task()` crea un `WorkItem` cuando un hallazgo se promueve: id `sec-{finding_id}`, `reward=0.0` (nunca inventa la recompensa), `access_status` tomado de `PLATFORM_ACCESS` (si el programa no es accesible sin credencial ⇒ `needs_manual_setup`), deliverables = borrador de reporte + PoC + review. Best-effort total: nunca raisea ni bloquea la promoción.
- **Efecto:** la métrica reina `NET CASH / HUMAN HOUR` ya tiene denominador para seguridad. Hasta que haya horas registradas sigue `UNKNOWN` — que es lo correcto.
- **Regla permanente:** el trabajo de seguridad entra al banco por **hallazgo→tarea**, nunca por discovery de programas.

## 40. Gate de admisión: 166 fuentes marcadas mal por un bug de alcance (2026-10-01) — RESUELTO

- **Bug:** `payout_evidence()` (source_registry.py:147) caía a `PAYOUT_NEGOTIATED` sólo si `"bounty" in src.type`. El campo `type` **nunca** contiene esa palabra: vale `platform`/`job_board`/`aggregator`/`forum`/`direct_api`. **La rama era inalcanzable** y `PAYOUT_NEGOTIATED` no lo consumía nadie.
- **Consecuencia medida:** las 166 fuentes sin experiencia/entrevista caían en `CONDITIONAL` con el motivo *"paga pero sin cifra publicada"*. Para **bug bounty / dev bounty eso es estructuralmente falso**: la cifra va por programa, no por fuente.
- **Fix:** `PER_OUTCOME_CATEGORIES = {bug_bounty, dev_bounty, oss_bounties}` (o el flag explícito `pays_per_outcome`) ⇒ `PAYOUT_NEGOTIATED`, que el gate ya admitía. `UNKNOWN` queda reservado a categorías que de verdad no declaran pago (AI evaluation sin cifra, etc.).
- **Efecto medido:** sin experiencia/entrevista, de **14 ACTIVE → 143 ACTIVE** (37 CONDITIONAL, 12 BLOCKED, 2 LOW_VALUE). El gate P1 de admisión ya admitting 178 fuentes.
- **Regla permanente:** *un valor de enum que nadie consume y una rama que ninguna entrada puede alcanzar no son features, son afirmaciones.* Y: *"no sé cuánto paga"* ≠ *"no sé si paga"* — para bounty son preguntas distintas y confundirlas下山ó 129 plataformas legítimas del ranking.
- **A prueba de fallo:** quitar la rama per-outcome ⇒ `test_bounty_sin_cifra_es_negotiated_no_unknown` falla. 19/19 en `test_source_admission.py`.

## 41. Outlier y Alignerr: barrera contradictoria + rate desactualizado (2026-10-01) — RESUELTO

- **Bug de catálogo:** ambas filas declaraban `entry_barrier="CREDENTIALS"` mientras la **misma fila** decía `requires_experience=False, requires_portfolio=False, requires_interview=False`. El valor explícito gana en `entry_barrier()` y las bloqueaba del ranking.
- **Verificado en vivo (2026-10-01):**
  · **Alignerr**: la propia página dice *"No experience needed, flexible hours"* y publica JSON-LD con rates **"$10-35/hr" … "$170-200/hr"**. El catálogo decía `$8/h` (error por debajo del piso publicado) y `CREDENTIALS` (falso) → corregido a `ASSESSMENT` + `$10/h` como low bound conservador.
  · **Outlier**: entrada = *"selecting your areas of expertise, completing skill screenings"* + onboarding general ⇒ `ASSESSMENT`, no credenciales. **Matiz honesto:** la página también dice que por proyecto *"minimum qualifications typically require undergraduate-level expertise"*, así que el screening por proyecto puede ser exigente; el gate de plataforma no es por credenciales. Corregido a `ASSESSMENT` con la nota.
- **Efecto:** ambas pasan a `LOW_VALUE` (bajo el piso de $15/h) — **entran al ranking** con motivo visible, en vez de estar `BLOCKED`. El gate nunca las excluye; las marcaba mal.
- **Mercor NO se cambió de estado**, y la razón quedó documentada en el código: entrada por *AI interview* (excede el criterio "assessment sí, entrevista no") **y** `rail_pays_in_argentina=FALSE` (Stripe no cubre Argentina). Son dos motivos reales e independientes, no la etiqueta `CREDENTIALS`.
- **Corrección al adapter:** `direct_work_ai_eval.py` comentaba que Mercor paga por "Wise/PayOneer" — **suposición mía, sin dato**. El catálogo dice `stripe`. Comentario alineado al dato real.

## 42. Bounties de GitHub sin un solo pago: $5.810 de pipeline inexistente (2026-10-01) — RESUELTO

**Medido contra la API de GitHub, no por lectura:** los 4 repos que el discovery había trayendo al banco (`zhangjiayang6835-cyber/bounty-plaza`, `warpspeedopen-source/warpspeed-bounties`, `claude-builders-bounty/claude-builders-bounty`, `Vikingr2023/awesome-agent-bounties`) tienen **0 PRs mergeadas** sobre 30+ PRs cerradas cada uno. `warpspeed` además promete literalmente *"Payment is made only after the pull request is approved and merged"* — sin merge, sin pago. La etiqueta `bounty` y la cifra publicada **no son evidencia de que alguien haya pagado**.

- **Fix:** `repos_without_paid_evidence()` (adapter) consulta la API de GitHub y devuelve SÓLO los repos con cero merges; `WorkBank.mark_unpaid_sources()` los pasa a `status="unpaid_evidence"` con el motivo verificable. **Marca, no borra** (destruiría la evidencia de qué se descubrió). Un `delivered` real nunca se toca.
- **Bug secundario encontrado al verificar:** el summary y `_rank_ready()` filtraban por el **flag** `ready_to_deliver`, no por `status`. El item quedaba marcado pero **seguía contando como pipeline** (`ready_to_deliver: 9`). Ahora ambos exigen el status ⇒ un flag obsoleto no reimprime dinero.
- **Efecto:** `ready_to_deliver 9 → 0`, `unpaid_evidence: 9`, pipeline mensual **$5.810 → 0**. Los 9 `needs_access` (fiverr, pago real) intactos.
- **A prueba de fallo:** 3 invariantes comprobados reintroduciendo el bug (2 tests caen). 12/12 en `tests/test_unpaid_bounty_evidence.py`.
- **Regla permanente:** *una etiqueta no es un pago.* Para prometer dinero hace falta **al menos un merge pagado**; sin evidencia, `UNKNOWN` con el motivo visible. Y: el guard de un detector de fraude **no debe acusar a quien no tiene datos** — `torvalds/linux` (con merges reales) no se marca.

## 43. `parents[3]` escribía 7 stores FUERA del repo (2026-10-01) — RESUELTO

- **Bug:** `_default_store_path()` usaba `Path(__file__).resolve().parents[3] / "data"`, pero el archivo vive en `<repo>/cores/direct_work_engine/` ⇒ `parents[2]` es el repo y `parents[3]` **sube un nivel de más**. El dev escribía en `~/projects/data/` mientras el sistema real usa `OWNEX_DATA_DIR` (`~/.ownex/`): **dos bancos distintos, divergiendo en silencio**.
- **Impacto medido:** 7 stores de estado escribían fuera del repo (`workbank.json`, `profile_kit.json`, `market_kb.json`, `quick_captures.json`, `fiverr_assets.json`, `fiverr_funnel.json`, `predictive_forecast.json`). El `workbank.json` del repo **no existía** — el banco "real" en dev era una copia huérfana con los 3 items de Algora 404.
- **Fix:** `parents[3]` → `parents[2]` en `workbank.py`. Los datos se migraron a `data/` (gitignored) antes de cambiar la ruta, para no perderlos. `profile_kit.py` y `maximum_potential.py` tienen el mismo off-by-one (**NO tocados**: fuera del alcance de esta sesión, y sus datos ya están en el destino correcto).
- **Bug de clase encontrado por el test:** `WorkBank.__init__` acepta `store_path: str | Path` pero **nunca lo normalizaba a `Path`**, así que cualquier llamador que pasara un string perdía `_load`/`_save` **en silencio** (solo un `logger.warning`). Corregido.
- **Regla permanente:** *un `parents[N]` es un supuesto sobre la profundidad del árbol.* Preferir un ancla explícita (`OWNEX_DATA_DIR`, o un constant de repo) sobre un índice que se rompe en cuanto el archivo se mueve de nivel.

