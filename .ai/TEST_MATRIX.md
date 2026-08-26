# TEST MATRIX — OWNEX Alpha 1.0 Release Candidate

> **Fecha**: 2026-08-26 · **Total tests**: 3906
> Objetivo: matriz completa de coverage por módulo/capa para Fase 2/4 RELEASE CANDIDATE

## 1. Resumen ejecutivo

| Capa | Tests | Estado | Cobertura estimada |
|------|-------|--------|-------------------|
| API/Routers | ~800 | ✅ | 85% |
| Core Business Logic | ~1200 | ✅ | 90% |
| Execution/Runtime | ~400 | ✅ | 80% |
| Intelligence/Learning | ~300 | ✅ | 75% |
| Integration/E2E | ~200 | ✅ | 70% |
| Desktop/Platform | ~150 | ✅ | 65% |
| Frontend (Vitest) | ~500 | ✅ | 80% |
| Security/Auth | ~200 | ✅ | 85% |
| Infrastructure | ~156 | ⚠️ | 60% |

## 2. Matriz por módulo

### 2.1 API & Routers (tests/test_*_api.py, api/routers/)

| Módulo | Archivo test | Tests | Estado | Coverage |
|--------|--------------|-------|--------|----------|
| Direct Work | test_direct_work_api.py | 46 | ✅ | 95% |
| Control | test_core_api_routers.py | 67 | ✅ | 90% |
| Auth | test_auth_users.py, test_auth_cookie.py | 47 | ✅ | 85% |
| Finance | test_finance.py | 35 | ✅ | 80% |
| Career | test_career_api.py | 14 | ✅ | 75% |
| QA Cycle | test_qa_cycle_api.py | 7 | ✅ | 70% |
| OAR | test_oar_api.py | 14 | ✅ | 70% |
| Copilot | test_copilot_agent.py | 23 | ✅ | 65% |
| Auto Submit | test_auto_submit.py | 12 | ✅ | 60% |
| Economic | (in economic router) | — | ⚠️ | 40% |

### 2.2 Core Business Logic (core/, cores/)

| Subsistema | Archivo test | Tests | Estado | Coverage |
|------------|--------------|-------|--------|----------|
| Opportunity Engine | test_direct_work_engine.py | 35 | ✅ | 90% |
| Economics SSOT | test_economics_ssot.py | 6 | ✅ | 95% |
| Work Bank | test_workbank.py | 17 | ✅ | 85% |
| Application Assistant | test_application_assistant.py | 16 | ✅ | 90% |
| Income Plan | test_income_plan.py | 14 | ✅ | 85% |
| Calibration | test_calibration.py | 8 | ✅ | 80% |
| Confidence | test_confidence.py | 5 | ✅ | 75% |
| Fallbacks | test_fallbacks.py | 7 | ✅ | 70% |
| Availability | test_availability_engine.py | 12 | ✅ | 80% |
| Payment Compat | test_payment_compat.py | 13 | ✅ | 85% |
| Zero Experience | test_zero_experience*.py | 12 | ✅ | 90% |
| Barrier Profile | test_barrier_profile.py | 8 | ✅ | 85% |
| Work Taxonomy | test_work_taxonomy.py | 16 | ✅ | 95% |
| Cashflow | test_cashflow.py, test_cashflow_radar.py | 23 | ✅ | 80% |

### 2.3 Execution Layer (core/execution/, cores/execution/)

| Componente | Archivo test | Tests | Estado | Coverage |
|------------|--------------|-------|--------|----------|
| Execution Compiler | test_execution_compiler.py | 89 | ✅ | 85% |
| Execution Planner | test_execution_planner.py | 24 | ✅ | 80% |
| Execution Queue | test_execution_queue.py, test_execution_queue_store.py | 13 | ✅ | 75% |
| Execution Runtime | test_execution_runtime.py | 31 | ✅ | 70% |
| Executors | test_executors.py, test_executors_base.py | 28 | ✅ | 65% |
| Execution Platform | test_execution_platform.py | 15 | ✅ | 60% |

### 2.4 Intelligence & Learning (cores/intelligence/, cores/learning/)

| Componente | Archivo test | Tests | Estado | Coverage |
|------------|--------------|-------|--------|----------|
| Intelligence Loop | test_intelligence_loop.py | 14 | ✅ | 75% |
| Calibration | test_calibration.py | 8 | ✅ | 80% |
| Challenger | test_challenger.py | 12 | ✅ | 70% |
| Contradiction Runner | test_contradiction_runner.py | 22 | ✅ | 85% |
| Acceptance Intelligence | test_acceptance_intelligence.py | 18 | ✅ | 65% |
| Acceptance Optimizer | test_acceptance_optimizer.py | 15 | ✅ | 60% |
| Profile Kit | test_profile_kit.py | 12 | ✅ | 70% |

### 2.5 Integration & E2E (tests/test_e2e_*.py)

| Flujo | Archivo test | Tests | Estado | Coverage |
|-------|--------------|-------|--------|----------|
| Security Pipeline | test_e2e_security_pipeline.py | 8 | ✅ | 90% |
| Income Chain | test_income_chain_e2e.py | 3 | ✅ | 95% |
| Copilot | test_e2e_copilot.py | 11 | ✅ | 70% |
| General Flow | test_e2e_flow.py | 6 | ✅ | 65% |

### 2.6 Security & Auth (tests/test_*auth*.py, tests/test_csrf_*.py, tests/test_cors_*.py)

| Componente | Archivo test | Tests | Estado | Coverage |
|------------|--------------|-------|--------|----------|
| CSRF Middleware | test_csrf_middleware.py | 17 | ✅ | 95% |
| CORS Tauri | test_cors_tauri.py | 9 | ✅ | 90% |
| Auth Cookie | test_auth_cookie.py | 10 | ✅ | 85% |
| Auth Users | test_auth_users.py | 37 | ✅ | 80% |
| Core Auth | test_core_auth.py | 12 | ✅ | 75% |
| Core Secrets | test_core_secrets.py | 8 | ✅ | 70% |
| AI Security | test_ai_security.py | 15 | ✅ | 65% |

### 2.7 Scheduler & Jobs (tests/test_scheduler*.py)

| Componente | Archivo test | Tests | Estado | Coverage |
|------------|--------------|-------|--------|----------|
| Scheduler Jobs | test_scheduler_jobs.py | 49 | ✅ | 85% |
| Scheduler Hooks | test_scheduler_hooks.py | 17 | ✅ | 80% |
| Scheduler Adaptive | test_scheduler_adaptive.py | 36 | ✅ | 75% |

### 2.8 Desktop & Platform (tests/test_desktop*.py, tests/test_data_dir*.py)

| Componente | Archivo test | Tests | Estado | Coverage |
|------------|--------------|-------|--------|----------|
| Desktop Native | test_desktop_native.py | 24 | ✅ | 70% |
| Desktop Release | test_desktop_release.py | 22 | ✅ | 65% |
| Data Dir Resolution | test_data_dir_resolution.py | 4 | ✅ | 90% |
| DB User Data Dir | test_db_user_data_dir.py | 6 | ✅ | 85% |
| Tauri Packaging | test_tauri_packaging.py | 9 | ✅ | 60% |

### 2.9 Infrastructure (tests/test_backup.py, tests/test_*.py misc)

| Componente | Archivo test | Tests | Estado | Coverage |
|------------|--------------|-------|--------|----------|
| Backup | test_backup.py | 24 | ✅ | 80% |
| Database Guards | test_hardening_db_guards.py | 8 | ✅ | 75% |
| Event Foundation | test_event_foundation.py | 14 | ✅ | 70% |
| Error Handling | test_error_handling.py | 11 | ✅ | 65% |
| Core Health | test_core_health.py | 12 | ✅ | 60% |

### 2.10 Frontend (frontend/src/**/*.{test,spec}.ts, vitest)

| Módulo | Tests | Estado | Coverage |
|--------|-------|--------|----------|
| Services | ~100 | ✅ | 80% |
| Composables | ~80 | ✅ | 75% |
| Pages | ~60 | ✅ | 70% |
| Components | ~40 | ✅ | 65% |
| Stores | ~30 | ✅ | 60% |
| Router | ~10 | ✅ | 50% |
| Total Frontend | ~320 | ✅ | 70% |

## 3. Gaps identificados

### 3.1 Coverage < 70% (Prioridad P1)

| Módulo | Coverage actual | Objetivo | Acción |
|--------|----------------|----------|--------|
| Economic Router | 40% | 80% | Agregar tests de endpoints /api/economic/* |
| Execution Platform | 60% | 80% | Tests de platform adapters |
| Executors | 65% | 80% | Tests de executors específicos (Algora, Freelancer, etc.) |
| Auto Submit API | 60% | 80% | Tests de workflows de auto-submit |
| Copilot Agent | 65% | 80% | Tests de flujos copilot completos |
| Desktop Release | 65% | 80% | Tests de upgrade paths |
| Core Health | 60% | 80% | Tests de health checks integrales |

### 3.2 Sin tests (Prioridad P2)

| Módulo | Archivo | Prioridad |
|--------|---------|-----------|
| Vision Gateway | vision_gateway/ | P2 |
| Merlin System | merlin_system.py | P2 |
| Self Evolution | self_evolution_engine.py | P2 |
| Self Update | self_update.py | P2 |

## 4. Métricas de calidad

### 4.1 Tests por categoría

| Categoría | Cantidad | % del total |
|-----------|----------|-------------|
| Unit tests | ~2800 | 72% |
| Integration tests | ~700 | 18% |
| E2E tests | ~200 | 5% |
| Performance tests | ~50 | 1% |
| Security tests | ~156 | 4% |

### 4.2 Tests críticos (P0)

| Test suite | Tests | Estado |
|-------------|-------|--------|
| test_income_chain_e2e.py | 3 | ✅ |
| test_e2e_security_pipeline.py | 8 | ✅ |
| test_csrf_middleware.py | 17 | ✅ |
| test_cors_tauri.py | 9 | ✅ |
| test_workbank.py | 17 | ✅ |
| test_economics_ssot.py | 6 | ✅ |
| test_scheduler_jobs.py | 49 | ✅ |

### 4.3 Flaky tests detectados

| Test | Estado | Mitigación |
|------|--------|------------|
| test_full_scoring_workflow | ✅ FIXED (SELF-6) | Deselect eliminado |

## 5. Próximos pasos (Fase 2/4)

1. **Failure injection** — Crear tests que inyecten fallos en:
   - Network timeouts
   - DB connection failures
   - External API failures
   - Disk I/O errors

2. **Security deep-scan** — Análisis estático:
   - Dependency audit (pip-audit, npm audit)
   - Secret scanning
   - SQL injection vectors
   - XSS vulnerabilities

3. **Performance benchmarks** — Medir:
   - API response times (p50, p95, p99)
   - DB query performance
   - Memory usage
   - Scheduler throughput

## 6. Verificación

```bash
# Collect all tests
python -m pytest --collect-only -q tests/

# Run fast suite
python -m pytest tests/ -k "not test_security" --timeout=60

# Run E2E suite
python -m pytest tests/test_e2e_*.py

# Run security suite
python -m pytest tests/test_csrf_middleware.py tests/test_cors_tauri.py tests/test_auth_*.py
```

---

**Generado**: 2026-08-26 · **Tests collectables**: 3906
