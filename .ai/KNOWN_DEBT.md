# Known Debt — Deuda Técnica Conocida

> Deuda identificada durante el audit arquitectónico. Cada entrada incluye evidencia de su existencia.

## 1. ✅ Tres sistemas de salud superpuestos — RESUELTO

- **Archivos**: `core/health/engine.py`, `core/health/checks.py`
- **Solución**: HealthCenter es ahora el único sistema que ejecuta checks. HealthMonitor y Watchdog delegan sus checks a HealthCenter. Se agregaron 4 checks faltantes (agent_bus, agents_health, memory, cpu) para cubrir todo el espectro. HealthCenter persiste snapshots vía SystemState. Endpoint unificado `/api/core/health/summary`.
- **Tests**: 25 tests en test_core_health.py (18 originales + 7 nuevos).
- **Verificación**: Ruff clean, tests verdes.

## 2. ✅ Sin tests para CSRF middleware — RESUELTO

- **Evidencia**: `api/middleware/csrf_middleware.py` existe y ahora tiene cobertura completa
- **Solución**: `tests/test_csrf_middleware.py` (SELF-2) — 17 tests que cubren los contratos del middleware:
  - GET setea la cookie de CSRF (doble-envío) y no la reescribe si ya existe
  - POST/PUT/PATCH/DELETE sin cookie o sin header → 403
  - Token mismatch → 403; cookie+header matching → 200
  - Métodos seguros (GET/HEAD/OPTIONS/TRACE) exentos
  - `EXEMPT_PATHS` (health, license, auth) sin CSRF
  - `CATEYE_CSRF_DISABLED=1` (opt-out explícito) desactiva
  - WebSocket scope bypass (probado con Starlette puro, ya que FastAPI 0.141/Starlette 1.3.1 no inyecta el WebSocket en rutas `@app.websocket` de forma compatible)
- **Verificación**: 17/17 passed, ruff limpio, `import api.main` OK, sin regresiones (e2e_flow + csrf = 29 passed)**

## 3. ✅ Sin tests para scheduler adaptativo — RESUELTO

- **Evidencia**: `api/scheduler.py` fue reescrito sin tests específicos
- **Solución (SELF-3, 2026-08-11)**: `tests/test_scheduler.py::TestScanSchedulerAdaptive` — 7 tests que cubren el comportamiento de `_stage_recon` con fakes (sin red):
  - `test_recon_skips_target_in_cooldown` — cooldown activo → no se llama a `_recon_target`
  - `test_recon_scans_when_cooldown_expired` — sin cooldown → el target se escanea
  - `test_recon_priority_order_high_first` — orden por prioridad RewardLearner (mayor primero)
  - `test_scan_stamps_cooldown` — el scan sella el cooldown del target
  - `test_no_rescan_within_hour` — segundo ciclo salta el target recién escaneado
  - `test_reward_learner_adjustments_reach_prioritizer` — adjustments del RewardLearner llegan al TargetPrioritizer
  - `test_cycle_purges_stale_cooldowns` — cooldowns viejos se purgan al final del ciclo
- **Verificación**: 7/7 passed, ruff limpio en el archivo, suite fast 89 passed / 1 skipped (sin regresiones)
- **Impacto**: Alto (era el item #1 de prioridad OWNEX del backlog autónomo). Cobertura del cooldown por target, priorización y purga.

## 4. ✅ Sin tests para rate limit mejorado — RESUELTO

- **Evidencia**: `api/middleware/rate_limit_middleware.py` modificado sin tests
- **Solución (SELF-4, commit `971dbda7c`)**: `tests/test_rate_limit_middleware.py` — 12 tests que cubren el middleware completo:
  - `_resolve_identity`: sin auth → IP; Bearer válido → `sub`; token inválido/excepción → fallback a IP
  - `NO_LIMIT_PREFIXES` (health/version/docs/openapi/redoc): nunca 429 (50 requests cada uno)
  - Enforcement: burst (2) agotado → 429; `X-RateLimit-Remaining: 0` en 429; header presente en éxito
  - Aislamiento por identidad: u1 agota su bucket → 429; u2 con bucket intacto → 200
- **Verificación**: 12/12 passed, ruff limpio, sin regresiones (suite fast 89 passed / 1 skipped)
- **Impacto**: Bajo. El fallback a IP funciona como antes.

## 5. ✅ Pre-commit hooks — RESUELTO

- **Archivo**: `.pre-commit-config.yaml`
- **Solución**: pre-commit instalado con hooks de Ruff (lint + format) y pytest (todos los tests, excluyendo test_security.py)
- **Comando**: `pre-commit install` (ya ejecutado)
- **Nota**: 14 errores preexistentes en archivos no relacionados — no bloquean nuevos commits (ruff solo revisa archivos staged).

## 6. ✅ DuplicateDetector no conectado al DedupTracker — RESUELTO

- **Evidencia**: 
  - `cores/analysis/duplicate_detector.py` usa su propio `_history` in-memory
  - `cores/dedup.py` existe pero no se usa desde análisis
- **Problema**: El detector de duplicados fuzzy no comparte estado con el tracker unificado
- **Impacto**: Bajo. Cada sistema funciona independientemente.
- **Estado**: ✅ RESUELTO (SELF-7, 2026-08-11) — `DuplicateDetector` ahora comparte el session tracker unificado: `load_history()` (ya existía) filtra contra `get_session_tracker()`; nuevo `fingerprint()` como SSOT del fingerprint (misma normalización de IDs que `cores.dedup`); `assess()` marca el finding evaluado en el tracker compartido → cualquier consumidor del pipeline ve el finding como procesado en la sesión y no lo reprocesa. Verificado: `tests/test_duplicate_detector.py` 9 passed (4 tests nuevos de shared state), ruff limpio, 38 tests dedup/duplicate sin regresión.

## 7. ✅ Dependencias frontend no auditadas — RESUELTO

- **Evidencia**: `frontend/package.json` y `node_modules/` extensos
- **Solución (SELF-1, 2026-08-11)**: `npm audit` = 0 vulnerabilities (workspace raíz: nanoid 3.3.18, postcss 8.5.26, undici 7.29.0, brace-expansion corregidos). La causa de las alertas Dependabot era el lockfile duplicado `frontend/package-lock.json` (artefacto pre-workspaces) → eliminado; el lockfile raíz del workspace es el único (One Source of Truth).
- **Pendiente**: 1 alerta Dependabot open sin fix (glib 0.18.5, medium, GHSA-wrw7-89jp-8q8g) — riesgo aceptado y documentado (app desktop local single-user; gtk-rs 0.20 no adoptado aún por el ecosistema tauri).

## 8. ✅ Documentación dispersa — RESUELTO

- **Evidencia**: 16 archivos .md en la raíz + 4 en docs/ (estado original, 2026-07)
- **Problema**: Información redundante y desactualizada en múltiples archivos
- **Impacto**: Medio. Dificulta encontrar información precisa.
- **Estado**: ✅ RESUELTO (SELF-8, 2026-08-11) — la raíz quedó consolidada a 5 archivos con rol claro (AGENTS.md tooling, README.md hub, SECURITY.md convención GitHub, CHANGELOG.md, ROADMAP.md = puntero al SSOT). La duplicación real detectada (root `ROADMAP.md` era una copia obsoleta en inglés de `.ai/ROADMAP.md` — ciclos/estados viejos, violaba One Source of Truth) se reemplazó por un hub que apunta a `.ai/ROADMAP.md`; `docs/KNOWN_LIMITATIONS.md` referenciaba el archivo raíz → apunta a `.ai/`. `docs/README.md` es el hub de docs/ (36+ links, incluye `docs/archived/` para legacy). Verificado: 0 referencias rotas a ROADMAP.md raíz fuera de archived/.

## 9. ✅ Motor de validación sin refutación — PARCIALMENTE RESUELTO

- **Evidencia**:
  - `cores/validation/challenger.py` — HypothesisChallenger creado (AlternativeExplainer, ContradictionTestDesigner, MissingVerificationsAnalyzer)
  - `cores/validation/gate.py` — Verdict con alternative_explanations, missing_verifications, uncertainty_level
  - `cores/validation/confidence.py` — uncertainty_penalty agregado al scorer (-0.00 a -0.12)
  - `cores/validation/loop_engine.py` — Challenger integrado antes de la validación
- **Estado actual**: ✅ Explicaciones alternativas para 7+ tipos de vuln. ✅ Tests de contradicción con info_gain. ✅ Missing verifications explicitadas. ✅ uncertainty_penalty en confidence score. ✅ Contradiction tests ejecutados con umbral info_gain (SELF-5). ❌ FeedbackLearner no conectado. ❌ Gate threshold sigue fijo 0.6.
- **Estado**: ✅ Parcialmente resuelto (SELF-5, 2026-08-11) — la parte "Contradiction tests no se ejecutan" está cerrada: `cores/validation/contradiction_runner.py` ejecuta el `next_best_test` del Challenger dentro del loop cuando `status=="confirmed"` y `info_gain >= "alta"`; la refutación downgradea a "inconclusive" con razón explícita y el outcome se persiste en `data/learning/contradictions.jsonl` (JSONL separado, `get_contradiction_stats`). Verificado: `tests/test_contradiction_runner.py` 22/22 passed, ruff limpio, 199 validation tests sin regresión, suite fast 89 passed / 1 skipped, `import api.main` OK. **Sigue pendiente**: FeedbackLearner aún no consume los outcomes (solo se registran), y el gate threshold sigue fijo en 0.6.

## 10. ✅ Test flaky: test_full_scoring_workflow — RESUELTO

- **Archivo**: `tests/test_opportunity_engine_comprehensive.py::TestIntegrationScenarios::test_full_scoring_workflow`
- **Evidencia**: El test provee `first.side_effect = [finding, program, tier]` (3 items) pero `core/opportunity/scoring.py` ejecuta `query(Finding).first()` dentro de `record_feedback` + `query(Program).first()` + `query(BountyTier).first()` (para `_estimate_reward`) + `on_accept` hace su propio `query(Finding).first()`. El 4º consumo de `side_effect` lanza `StopIteration`.
- **Problema**: El mock de `side_effect` es insuficiente para el número real de lookups DB del engine. No es una regresión del scoring — la lógica de `on_accept`/`on_reject` requiere un `query(Finding)` adicional que el mock no provisiona.
- **Impacto**: Bajo. El resto de la suite de oportunidad (`27/28`) es verde. El test estaba deseleccionado en `make check`/`dev check`/`make test-fast` via `--deselect`.
- **Estado**: ✅ RESUELTO (SELF-6, 2026-08-11) — el `side_effect` fue extendido a los 8 lookups reales (finding/program/tier para accept + finding/program/tier para reject + on_accept + on_reject) en el commit `eade07f87`; el test pasa determinísticamente (verificado 4 corridas seguidas + dentro de `make test-fast`). Eliminado el `FLAKY_DESELECT` del Makefile; `make test-full-scoring` sigue disponible como target de diagnóstico.

## 11. Suite lenta + tests de red/flaky

- **Evidencia**: `tests/test_security.py` (llamadas externas live), `tests/test_vision_gateway.py` (rate-limit/SSL de Gemini) y `tests/test_scheduler.py` (requests HTTP a fuentes de terceros como HackenProof/OpenBugBounty) fallan o se cuelgan en CI/local.
- **Problema**: La suite completa supera los 60s de timeout del pre-commit y no es determinista por tests de red.
- **Solución aplicada**: `make test`/`scripts/dev test` ignoran `test_security.py`, `test_vision_gateway.py` y `test_scheduler.py` por defecto; se pueden ejecutar explícitamente. `make test-fast` (86 tests) es el smoke determinista del dev loop.
- **Impacto**: Bajo. Los tests de red siguen disponibles bajo demanda.
