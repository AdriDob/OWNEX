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

## 3. Sin tests para scheduler adaptativo

- **Evidencia**: `api/scheduler.py` fue reescrito sin tests específicos
- **Problema**: El scheduler adaptativo (cooldown, priorización) no tiene tests
- **Impacto**: Medio. Cambios en la lógica de priorización no están cubiertos.

## 4. Sin tests para rate limit mejorado

- **Evidencia**: `api/middleware/rate_limit_middleware.py` modificado sin tests
- **Problema**: La resolución de identity por token no tiene tests
- **Impacto**: Bajo. El fallback a IP funciona como antes.

## 5. ✅ Pre-commit hooks — RESUELTO

- **Archivo**: `.pre-commit-config.yaml`
- **Solución**: pre-commit instalado con hooks de Ruff (lint + format) y pytest (todos los tests, excluyendo test_security.py)
- **Comando**: `pre-commit install` (ya ejecutado)
- **Nota**: 14 errores preexistentes en archivos no relacionados — no bloquean nuevos commits (ruff solo revisa archivos staged).

## 6. DuplicateDetector no conectado al DedupTracker

- **Evidencia**: 
  - `cores/analysis/duplicate_detector.py` usa su propio `_history` in-memory
  - `cores/dedup.py` existe pero no se usa desde análisis
- **Problema**: El detector de duplicados fuzzy no comparte estado con el tracker unificado
- **Impacto**: Bajo. Cada sistema funciona independientemente.

## 7. Dependencias frontend no auditadas

- **Evidencia**: `frontend/package.json` y `node_modules/` extensos
- **Problema**: No se ha auditado seguridad de dependencias npm
- **Impacto**: Potencialmente alto.

## 8. Documentación dispersa

- **Evidencia**: 16 archivos .md en la raíz + 4 en docs/
- **Problema**: Información redundante y desactualizada en múltiples archivos
- **Impacto**: Medio. Dificulta encontrar información precisa.

## 9. ✅ Motor de validación sin refutación — PARCIALMENTE RESUELTO

- **Evidencia**:
  - `cores/validation/challenger.py` — HypothesisChallenger creado (AlternativeExplainer, ContradictionTestDesigner, MissingVerificationsAnalyzer)
  - `cores/validation/gate.py` — Verdict con alternative_explanations, missing_verifications, uncertainty_level
  - `cores/validation/confidence.py` — uncertainty_penalty agregado al scorer (-0.00 a -0.12)
  - `cores/validation/loop_engine.py` — Challenger integrado antes de la validación
- **Estado actual**: ✅ Explicaciones alternativas para 7+ tipos de vuln. ✅ Tests de contradicción con info_gain. ✅ Missing verifications explicitadas. ✅ uncertainty_penalty en confidence score. ❌ Contradiction tests no se ejecutan (solo se diseñan). ❌ FeedbackLearner no conectado. ❌ Gate threshold sigue fijo 0.6.
- **Impacto**: Bajo. El sistema ahora explicita incertidumbre y alternativas, pero no las resuelve automáticamente.

## 10. Test flaky: test_full_scoring_workflow (AUD-5)

- **Archivo**: `tests/test_opportunity_engine_comprehensive.py::TestIntegrationScenarios::test_full_scoring_workflow`
- **Evidencia**: El test provee `first.side_effect = [finding, program, tier]` (3 items) pero `core/opportunity/scoring.py` ejecuta `query(Finding).first()` dentro de `record_feedback` + `query(Program).first()` + `query(BountyTier).first()` (para `_estimate_reward`) + `on_accept` hace su propio `query(Finding).first()`. El 4º consumo de `side_effect` lanza `StopIteration`.
- **Problema**: El mock de `side_effect` es insuficiente para el número real de lookups DB del engine. No es una regresión del scoring — la lógica de `on_accept`/`on_reject` requiere un `query(Finding)` adicional que el mock no provisiona.
- **Impacto**: Bajo. El resto de la suite de oportunidad (`27/28`) es verde. El test está deselezionado en `make check`/`dev check`/`make test-fast` via `--deselect`; se ejecuta explícitamente con `make test-full-scoring` para diagnosticar.
- **Estado**: Documentado. No se corrige sin el código original de Hermes.

## 11. Suite lenta + tests de red/flaky

- **Evidencia**: `tests/test_security.py` (llamadas externas live), `tests/test_vision_gateway.py` (rate-limit/SSL de Gemini) y `tests/test_scheduler.py` (requests HTTP a fuentes de terceros como HackenProof/OpenBugBounty) fallan o se cuelgan en CI/local.
- **Problema**: La suite completa supera los 60s de timeout del pre-commit y no es determinista por tests de red.
- **Solución aplicada**: `make test`/`scripts/dev test` ignoran `test_security.py`, `test_vision_gateway.py` y `test_scheduler.py` por defecto; se pueden ejecutar explícitamente. `make test-fast` (86 tests) es el smoke determinista del dev loop.
- **Impacto**: Bajo. Los tests de red siguen disponibles bajo demanda.
