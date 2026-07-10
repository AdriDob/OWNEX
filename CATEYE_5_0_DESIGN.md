# CATEYE 5.0 — Architecture Redesign & Roadmap

> **⚠️ DOCUMENTO ASPIRACIONAL — Este documento describe el diseño objetivo para CATEYE v5.0.**
> **La versión actual es v3.0.0. Ninguno de los hitos descritos aquí ha sido implementado.**
>
> Ver `SYSTEM.md` para la arquitectura real y `RELEASE_NOTES_v3.0.0.md` para el estado actual.
> Este documento permanece como guía de dirección futura, no como descripción del sistema.

---

## Principio Rector

CATEYE no crece por expansión. CATEYE crece por **consolidación**.

---

## FASE 0: Diagnóstico Final

### 23 hallazgos arquitectónicos (8 CRÍTICOS, 6 ALTOS, 7 MEDIOS, 4 BAJOS)

Ver `SYSTEM.md` sección 4 para lista completa.

### Resumen de acción requerida:

| Tipo | Cantidad | Acción |
|------|----------|--------|
| CRÍTICO | 8 | Deben resolverse antes del freeze |
| ALTO | 6 | Resolver en Hito 1-2 |
| MEDIO | 7 | Resolver en Hito 3-6 |
| BAJO | 4 | Resolver en Hito 8 o póstumo |

---

## Hito 0: Correcciones PRE-FREEZE (no negociables)

Antes de declarar CATEYE 5.0 Stable, deben resolverse estos 8 hallazgos críticos:

### 0.1 Eliminar Pipeline class muerto
- **Archivo**: `cores/orchestrator/pipeline.py` (476 líneas)
- **Acción**: Mover a `archive_cleanup/` por si se necesita recuperar lógica. No eliminar permanentemente sin verificación.
- **Riesgo**: Bajo — 0 imports en todo el código. Solo arrastra dependencias.

### 0.2 Eliminar evidence_service.py muerto
- **Archivo**: `cores/pipeline/evidence_service.py`
- **Acción**: Mover a `archive_cleanup/`

### 0.3 Eliminar scanning/ muerto
- **Archivo**: `cores/scanning/` (256 líneas)
- **Acción**: Mover a `archive_cleanup/`

### 0.4 Eliminar o conectar knowledge/
- **Archivo**: `cores/knowledge/` (14 archivos)
- **Acción**: Decisión: ¿se conecta al runtime o se elimina? Si se conecta, integrar en `api/main.py` lifespan. Si no, archivar.
- **Razón**: No puede quedar código huérfano de 14 archivos en un sistema frozen.

### 0.5 Eliminar TargetRadar muerto
- **Archivo**: `cores/targeting/radar.py`
- **Acción**: Mover a `archive_cleanup/`

### 0.6 Corregir scheduler bug
- **Archivo**: `api/scheduler.py:205-209`
- **Acción**: Corregir argumentos de `launch_scan()`. Pasar `session` explícitamente.

### 0.7 Corregir runtime bugs
- **Archivo**: `api/main.py:590` (boot_time), `api/main.py:605` (collect_health dataclass)
- **Acción**: Fixear ambos.

### 0.8 Decidir CoordinatorAgent vs Scheduler
- Dos state machines independientes sin sincronización.
- **Opción A**: Eliminar CoordinatorAgent (archivar en `archive_cleanup/`), la lógica de lifecycle del pipeline la maneja el scheduler.
- **Opción B**: Hacer que el scheduler publique eventos que CoordinatorAgent consuma.
- **Recomendación**: Opción A. El scheduler es time-based, el agente es event-driven. No hay necesidad de dos orquestadores para un solo usuario.

---

## Hito 1: Correcciones de Arquitectura (post-freeze, día 1-3)

### 1.1 Unificar 3 health systems → 1
- `cores/health/engine.py` + `cores/recovery/health_monitor.py` + `desktop/watchdog.py`
- Crear `UnifiedHealthMonitor` único
- Watchdog se convierte en cliente HTTP ligero

### 1.2 Dar persistencia a OpportunityEngine
- `cores/opportunity/engine.py` — pasar de `_opportunities: dict` en RAM a SQLite
- Salvar/restaurar estado en boot

### 1.3 Unificar 3 EventBuses → 1
- EventBus central se queda
- AgentBus se convierte en wrapper que publica directamente en EventBus con namespace `agent:*`
- EventSystem en intelligence/ se elimina (bridgear o morir)

### 1.4 Reestructurar intelligence/ (19 archivos)
- Mover event_system.py → eliminar
- Mover cache.py → eliminar
- Mover observability.py → eliminar (duplica cores/observability.py)
- Mover unified_orchestrator.py → eliminar
- Mover bounty_intel.py → cores/bounty_scraper/
- Mover export.py → utilidad general
- Mover adaptive_memory, pattern_registry, historical_analyzer, trend_detector → cores/learning/
- Mover priority_engine → cores/orion/ (es el que debe priorizar)
- Mover reward_learning → cores/orion/ (es parte de ORION)
- Mover recommendation_engine → cores/orion/
- Mover learning_snapshot → cores/memory/

---

## Hito 2: Unificaciones (día 4-7)

### 2.1 Unificar tool layers (2 → 1)
- `cores/recon/` + `cores/tools/` → ToolRegistry único

### 2.2 Unificar vaults (2 → 1)
- `cores/target_auth/vault.py` → namespace en `cores/identity_vault.py`

### 2.3 Unificar routers (65 → ~35)
- Merge opportunities + opportunity_intelligence
- Merge settings_ai + settings_runtime + settings_unified
- Merge identity + identity_center + target_identity
- Merge financial_sync + financial_truth + bank_payout + economic + crypto + accounts_hub + micro + connections → 3-4 routers
- Merge orion + intelligence + orchestrator
- Merge system + system_state
- Merge auth + auth_users

### 2.4 Unificar ranking engines (5 → 1)
- OpportunityEngine + PriorityEngine + RecommendationEngine → un solo sistema de ranking
- TargetRadar eliminado (código muerto)
- AdaptivePrioritizer se mantiene como overlay de perfil de usuario

---

## Hito 3: Correcciones de DB y Tests (día 8-10)

### 3.1 Alembic migration fix
- Sincronizar migraciones con modelos actuales
- Eliminar drops de target_intel/target_scopes si los modelos se quedan

### 3.2 Fix boolean inconsistency
- Unificar todos los Boolean columns a tipo Boolean SQLAlchemy

### 3.3 Tests
- Tests para scheduler, middleware, health, knowledge (si sobrevive), OpportunityEngine persistente
- Frontend tests (Vitest)
- Unskip test existente

---

## Hito 4: Hito 9: Freeze Final (día 11)

### 4.1 Verificaciones pre-freeze
- [ ] pytest suite completo (sin --ignore, sin xfail no documentado)
- [ ] ruff check . — 0 warnings
- [ ] Flujo E2E manual: abrir → detectar → recon → hipótesis → validar → reportar
- [ ] Verificar que no haya advertencias nuevas en runtime
- [ ] Verificar que OpportunityEngine persiste tras restart
- [ ] Verificar que UnifiedHealthMonitor es el único health system
- [ ] Verificar que EventBus es el único bus
- [ ] Verificar que no hay módulos huérfanos

### 4.2 Tag
```bash
git tag -a v5.0-stable -m "CATEYE 5.0 Stable — Arquitectura congelada"
git push origin v5.0-stable
```

### 4.3 Rama de mantenimiento
```bash
git checkout -b release/5.0-stable
git push origin release/5.0-stable
```

A partir de aquí, solo mejoras incrementales (5.1, 5.2...) que:
- Resuelvan un problema real
- Simplifiquen el sistema
- Aumenten autonomía
- Aumenten estabilidad
- No rompan la arquitectura

---

## Apéndice: Acciones por Archivo

### ELIMINAR (mover a archive_cleanup/):
| Archivo | Razón |
|---------|-------|
| `cores/orchestrator/pipeline.py` | 0 imports, 476 líneas muertas |
| `cores/pipeline/evidence_service.py` | 0 imports |
| `cores/scanning/` | 0 imports externos |
| `cores/targeting/radar.py` | Nadie lo alimenta ni consume |
| `mobile/` | Reemplazado por android/ |
| Root stubs: AGENT_CONTEXT.md, CLINE_SETUP.md, GUIA.md, INFORME.md, PLAN.md, RELEASE_REPORT.md, ROADMAP.md, SYSTEM_INVENTORY.md, finalroadmap.md | 93 bytes cada uno, obsoletos |

### DEPRECAR (código reemplazado):
| Archivo | Reemplazo |
|---------|-----------|
| `cores/agents/coordinator.py` | Scheduler (si se elige Opción A) |
| `cores/intelligence/event_system.py` | EventBus |
| `cores/intelligence/cache.py` | Ninguno (no necesario) |
| `cores/intelligence/observability.py` | cores/observability.py |
| `cores/intelligence/unified_orchestrator.py` | Pipeline/Scheduler |
| `cores/intelligence/bounty_intel.py` | cores/bounty_scraper/ |
| `cores/ai/assistant.py` | cores/ai/orion_agent.py |
| `api/routers/system_state.py` | api/routers/system.py |
| `api/routers/auth_users.py` | api/routers/auth.py |

### CORREGIR (bugs):
| Archivo | Bug |
|---------|-----|
| `api/main.py:590` | `getattr(state, "boot_time", None)` — siempre None |
| `api/main.py:605` | `health_data.get("pipelines", [])` — crash (dataclass) |
| `api/scheduler.py:205-209` | Argumentos incorrectos a launch_scan() |
| `alembic/versions/` | Mismatch con modelos actuales |
| `tests/test_scheduler.py` | Unskip test |
| `tests/test_e2e_flow.py` | Fix pagination |

### REFACTORIZAR (unificación):
| Archivos | Destino |
|----------|---------|
| `cores/health/engine.py` + `cores/recovery/health_monitor.py` + `desktop/watchdog.py` + `cores/system_health.py` | `cores/health/unified.py` |
| `cores/recon/*.py` + `cores/tools/*.py` | `cores/tools/registry.py` |
| `cores/agents/bus.py` | Wrapper de EventBus |
| `cores/target_auth/vault.py` | Namespace en IdentityVault |
| `cores/analysis/duplicate_detector.py` + `cores/dedup.py` | Unificar |
| `cores/opportunity/engine.py` | Agregar persistencia SQLite |
| `cores/intelligence/*` | Re-distribuir en learning/, orion/, bounty_scraper/ |
| 65 routers | ~35 routers |

---

## Reglas de Evolución Post-5.0

1. **No crear nuevos subpaquetes en `cores/`** sin aprobación explícita.
2. **No agregar nuevos routers** sin verificar que no exista funcionalidad equivalente.
3. **Todo código nuevo debe tener tests** — sin excepciones.
4. **Cero regresiones** — cualquier cambio debe mantener la suite verde.
5. **ORION sigue siendo READ-ONLY** — nunca controla el pipeline directamente.
6. **Cada módulo debe tener una única responsabilidad** — si hace más de una cosa, dividir.
7. **Cada dato debe tener una única fuente de verdad** — no duplicar estado.

---

*Julio 2026 — CATEYE v2.0.0 → v5.0 Architecture Roadmap*
