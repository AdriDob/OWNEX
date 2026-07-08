# CATEYE 5.0 — Freeze Checklist

> **Checklist definitivo para declarar CATEYE v5.0 STABLE.**
> Cada ítem debe estar VERIFICADO antes del freeze.
> No avanzar al siguiente ítem si el anterior falla.

---

## Fase 0: Correcciones PRE-FREEZE

### 0.1 Código muerto → archivar

- [ ] `cores/orchestrator/pipeline.py` → mover a `archive_cleanup/`
- [ ] `cores/pipeline/evidence_service.py` → mover a `archive_cleanup/`
- [ ] `cores/scanning/` → mover a `archive_cleanup/`
- [ ] `cores/targeting/radar.py` → mover a `archive_cleanup/`
- [ ] `mobile/` → mover a `archive_cleanup/`
- [ ] Root docs stubs (AGENT_CONTEXT.md, CLINE_SETUP.md, GUIA.md, INFORME.md, PLAN.md, RELEASE_REPORT.md, ROADMAP.md, SYSTEM_INVENTORY.md, finalroadmap.md) → eliminar

### 0.2 Decisión: knowledge/ (14 archivos)

- [ ] Opción A: Conectar al runtime (integrar en `api/main.py` lifespan)
- [ ] Opción B: Archivar en `archive_cleanup/`

### 0.3 Decisión: CoordinatorAgent

- [ ] Opción A: Eliminar CoordinatorAgent, scheduler maneja lifecycle
- [ ] Opción B: CoordinatorAgent se sincroniza con scheduler vía eventos

### 0.4 Bugs críticos

- [ ] `api/main.py:590` — Fix `boot_time` (SystemState no expone ese atributo)
- [ ] `api/main.py:605` — Fix `collect_health()` dataclass crash
- [ ] `api/scheduler.py:205-209` — Fix argumentos de `launch_scan()`
- [ ] `alembic/versions/` — Sincronizar migraciones con modelos actuales

### 0.5 Tests

- [ ] `tests/test_scheduler.py` — Unskip `test_hypothesis_without_endpoints_does_not_crash`
- [ ] `tests/test_e2e_flow.py` — Fix pagination en `test_04_get_target_list`
- [ ] `pytest suite` — Pasa completo (sin `--ignore`, sin xfail no documentado)

---

## Fase 1: Verificación Arquitectónica

### 1.1 Estado de módulos

- [ ] Todos los módulos CORE existen y tienen una única responsabilidad
- [ ] Todos los módulos EXTENSIÓN están documentados como tales
- [ ] Todos los módulos EXPERIMENTALES están documentados como tales
- [ ] No queda ningún módulo MUERTO en el árbol principal
- [ ] No queda ningún archivo del que no se pueda responder: "Si lo borro, ¿qué funcionalidad se pierde?"

### 1.2 Único Pipeline

- [ ] Solo `ScanScheduler` (`api/scheduler.py`) es el pipeline oficial
- [ ] `Pipeline` class (`orchestrator/pipeline.py`) está archivado
- [ ] SCOPE_CHECK stage definido como "no implementado" o eliminado
- [ ] CoordinatorAgent está deprecado o sincronizado

### 1.3 Único Health System

- [ ] `UnifiedHealthMonitor` existe y es el único health system
- [ ] `SystemHealthEngine` es wrapper (no independiente)
- [ ] `HealthMonitor` es wrapper (no independiente)
- [ ] `Watchdog` es cliente HTTP (no independiente)
- [ ] Solo un thread de health running en boot

### 1.4 Único EventBus

- [ ] `cores/events/event_bus.py` es el único EventBus del sistema
- [ ] `AgentBus` es wrapper liviano de EventBus
- [ ] `EventSystem` en intelligence/ está eliminado o bridgeado
- [ ] No hay eventos invisibles (todos los eventos pasan por EventBus)

### 1.5 Único Ranking Engine

- [ ] `OpportunityEngine` + `ORION` forman el único sistema de ranking
- [ ] `OpportunityEngine` persiste su estado en SQLite
- [ ] `PriorityEngine` está fusionado con ORION
- [ ] `TargetRadar` está archivado

### 1.6 Único Tool Layer

- [ ] `ToolRegistry` existe y unifica `cores/recon/` + `cores/tools/`
- [ ] Todos los runners usan ToolRegistry
- [ ] Pipeline y scheduler usan ToolRegistry exclusivamente

### 1.7 ORION

- [ ] ORION es read-only (solo RewardLearner escribe learning_state)
- [ ] ORION no ejecuta scans
- [ ] ORION no modifica targets/endpoints/findings/reports
- [ ] ORION no envía reportes
- [ ] ORION no reemplaza decisión humana

---

## Fase 2: Validación Técnica

### 2.1 Lint

- [ ] `ruff check .` — 0 errores
- [ ] `ruff check .` — 0 warnings (o todos documentados como pre-existentes)

### 2.2 Tests

- [ ] `pytest` (sin ignores) — todos pass (xfail documentados)
- [ ] Cobertura mínima en módulos CORE: ~60%
- [ ] Tests de middleware (CSRF, rate limit) agregados
- [ ] Tests de scheduler adaptativo agregados
- [ ] Tests de OpportunityEngine persistente agregados

### 2.3 Type check

- [ ] `mypy cores/ api/ database/ desktop/` — sin errores nuevos

### 2.4 Runtime

- [ ] Backend inicia sin errores
- [ ] Frontend carga sin errores
- [ ] WebSocket conecta
- [ ] EventBus publica eventos
- [ ] Scheduler inicia su loop

---

## Fase 3: Validación de Flujo E2E

### 3.1 Ciclo completo (manual)

- [ ] `Abrir CATEYE` → Login/activación funciona
- [ ] `Detectar programas` → Discovery (bounty_scraper) encuentra targets
- [ ] `Elegir cuáles seguir` → UI permite seleccionar targets
- [ ] `Recon automático` → Scheduler ejecuta RECON stage
- [ ] `Ejecutar herramientas` → launch_scan() funciona correctamente
- [ ] `Validar findings` → ValidationLoopEngine evalua findings
- [ ] `Eliminar duplicados` → DedupTracker funciona
- [ ] `Generar reporte` → create_report_from_findings() funciona
- [ ] `Enviar reporte (o dejarlo listo)` → Draft generado, pendiente de aprobación humana
- [ ] `Seguir estado` → Pipeline state visible en UI
- [ ] `Registrar pago` → Financial TruthLayer registra
- [ ] `Actualizar historial` → Ledger actualizado
- [ ] `ORION aprende` → RewardLearner analiza outcomes

### 3.2 Persistencia post-restart

- [ ] Targets sobreviven restart
- [ ] Endpoints sobreviven restart
- [ ] Findings sobreviven restart
- [ ] Reports sobreviven restart
- [ ] Opportunidades persisten (después de fix)
- [ ] Health snapshots persisten
- [ ] EventBus history persiste
- [ ] Sesiones de auth persisten

### 3.3 Sin regresiones

- [ ] Mismos resultados que antes de las unificaciones
- [ ] No hay nuevos warnings en runtime
- [ ] No hay nuevos errores en logs

---

## Fase 4: Freeze Final

### 4.1 Documentación

- [ ] `SYSTEM.md` actualizado y verificado contra código
- [ ] `CATEYE_5_0_DESIGN.md` actualizado y verificado contra código
- [ ] `FREEZE_CHECKLIST.md` completado
- [ ] No hay documentación contradictoria en el repo

### 4.2 Git

```bash
# Commit final
git add .
git commit -m "CATEYE 5.0 Stable — freeze arquitectónico

- Código muerto archivado (pipeline, evidence_service, scanning, TargetRadar)
- Bugs críticos corregidos (scheduler args, boot_time, collect_health)
- Unificaciones: health (1), eventbus (1), tools (1), ranking (1)
- Módulos clasificados: CORE / EXTENSION / EXPERIMENTAL / MUERTO
- SYSTEM.md actualizado como constitución definitiva
- Todos los tests pasan
- Flujo E2E verificado manualmente"

# Tag
git tag -a v5.0-stable -m "CATEYE 5.0 Stable — Arquitectura congelada"

# Rama de mantenimiento
git checkout -b release/5.0-stable
git push origin v5.0-stable
git push origin release/5.0-stable
```

### 4.3 Post-freeze

- [ ] Tag `v5.0-stable` creado y pusheado
- [ ] Rama `release/5.0-stable` creada y pusheada
- [ ] `main` queda abierta para mejoras 5.1, 5.2...

---

## Fase 5: Mantenimiento (5.1, 5.2...)

A partir del freeze, solo se permiten cambios que cumplan TODAS estas reglas:

- [ ] Resuelven un problema real (no especulación)
- [ ] Simplifican el sistema (no agregan complejidad)
- [ ] Aumentan autonomía del sistema
- [ ] Aumentan estabilidad (no introducen regresiones)
- [ ] No rompen la arquitectura definida en SYSTEM.md
- [ ] Tienen tests
- [ ] Están documentados en CHANGELOG.md

Si un cambio propuesto no cumple todas, se rechaza.

---

## Criterios de Aceptación para el Freeze

El freeze se declara oficialmente cuando:

1. **No existe código del que no se pueda responder "¿qué funcionalidad implementa?"**
2. **No hay dos módulos haciendo lo mismo**
3. **No hay estado duplicado en múltiples sistemas**
4. **No hay módulos que nadie llama**
5. **No hay bugs conocidos sin plan de corrección**
6. **El flujo E2E funciona de punta a punta**
7. **Los tests pasan**
8. **La documentación refleja el código**

Cuando se cumplan estos 8 criterios:

> **CATEYE v5.0 STABLE — Listo para uso privado diario durante años.**

---

*Julio 2027 — CATEYE v5.0 Freeze Checklist*
