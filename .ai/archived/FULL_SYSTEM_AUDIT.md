# FULL SYSTEM AUDIT — ORION v4.6.0

> Auditoría de madurez real del sistema. Julio 2026.
> Basada en inspección de código, tests, endpoints, frontend y documentación.

---

## Resumen de Madurez

| Dimensión | Score | Notas |
|---|---|---|
| Discovery Automation | 85% | Universal Discovery activo, falta auto-sync de nuevos programas |
| Intelligence Automation | 80% | Reasoners funcionan, AttackPlanner nuevo, falta más tipos de vuln |
| Validation Automation | 70% | ProbeEngine.execute_plan() multi-payload, pero requiere host manual |
| Evidence Automation | 85% | EvidenceComposer completo, PoC, curl, timeline |
| Report Automation | 75% | Templates existen, Quality Gate nuevo, falta auto-submission real |
| Learning Automation | 50% | RewardLearner existe, FeedbackTuner existe, pocos datos reales |
| Financial Automation | 80% | Sync automático, dashboard, CoinGecko, Takenos |
| Autonomy (nocturna) | 60% | Scheduler corre, pero pipelines no ejecutan AttackPlanner automáticamente |
| Documentation Sync | 85% | Acabamos de actualizar docs/ a v4.6.0 |
| Testing Coverage | 85% | 1400+ tests, cubren módulos core |

**Overall Maturity Score**: 75% — Sistema operativo funcional, gap principal es el loop de revenue real.

---

## Feature Audit Matrix

| Feature | Existe? | Runtime? | Conectado? | Documentado? | Tests? | Revenue Impact |
|---|---|---|---|---|---|---|
| **Discovery Universal** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐⭐⭐ |
| **Target Intelligence** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐⭐⭐⭐ |
| **Reasoners (5 tipos)** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **AttackPlanner** | ✅ | ✅ | ✅ | NEW | ✅ | ⭐⭐⭐⭐⭐ |
| **ProbeEngine.probe()** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **ProbeEngine.execute_plan()** | ✅ | ✅ | ✅ | NEW | NEW | ⭐⭐⭐⭐⭐ |
| **EvidenceComposer** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐⭐⭐⭐ |
| **Finding Promotion** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐⭐⭐⭐ |
| **Report Quality Gate** | ✅ | ✅ | ✅ | ✅ | NEW | ⭐⭐⭐⭐⭐ |
| **Revenue Pipeline** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **Mission Widget** | ✅ | ✅ | ✅ | NEW | ✅ | ⭐⭐⭐ |
| **NextAction Engine** | ✅ | ✅ | ✅ | NEW | ✅ | ⭐⭐⭐⭐ |
| **Knowledge Graph** | ✅ | ✅ | ✅ | NEW | ✅ | ⭐⭐⭐ |
| **Evolution Engine** | ✅ | ✅ | ✅ | NEW | ✅ | ⭐⭐⭐ |
| **Command System** | ✅ | ✅ | ✅ | NEW | ✅ | ⭐⭐ |
| **COPILOT Agent** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐⭐⭐⭐ |
| **Hermes Automation** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐⭐ |
| **Financial Dashboard** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐⭐⭐ |
| **Health Center** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐⭐ |
| **EventBus** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐⭐⭐ |
| **Secrets Manager** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐⭐⭐ |
| **Extension SDK** | ✅ | ✅ | ✅ | ✅ | ✅ | ⭐ |
| **Offensive API** | ✅ | ✅ | ✅ | NEW | ✅ | ⭐⭐⭐⭐⭐ |

---

## Pipeline Walkthrough

### 1. Discovery → Target Intelligence

```
INPUT: Nuevo programa público
PROCESO: Discovery universal scrapea plataformas
OUTPUT: Targets creados con score, tecnologías, scope
ESTADO: ✅ Automatizado
GAP: No hay alerta cuando aparece un programa nuevo de alto valor
```

### 2. Target Intelligence → Hypothesis

```
INPUT: Target analizado
PROCESO: Reasoners generan hipótesis por endpoint
OUTPUT: Hipótesis con confidence score, tipo de vuln, parámetros
ESTADO: ✅ Automatizado
GAP: Reasoners solo cubren 5 tipos (IDOR, SSRF, XSS, SQLi, Auth Bypass)
```

### 3. Hypothesis → Attack Plan

```
INPUT: Hypothesis
PROCESO: AttackPlanner.plan() genera TestPlan multi-payload
OUTPUT: TestPlan con baseline + N AttackSteps
ESTADO: ✅ Automatizado (NUEVO)
GAP: Falta planner para CSRF, LFI, CMDi, GraphQL
```

### 4. Attack Plan → Probe

```
INPUT: TestPlan
PROCESO: ProbeEngine.execute_plan() envía requests HTTP reales
OUTPUT: ProbeResult con evidencia, confidence, detección
ESTADO: ✅ Automatizado (NUEVO)
GAP: Requiere host/base_url manual. No hay integración con scheduler automático
```

### 5. Probe → Evidence

```
INPUT: ProbeResult
PROCESO: EvidenceComposer genera bundle profesional
OUTPUT: EvidenceBundle con PoC, curl, timeline, CVSS, CWE
ESTADO: ✅ Automatizado
GAP: Evidencia de screenshots no se genera automáticamente
```

### 6. Evidence → Finding

```
INPUT: EvidenceBundle
PROCESO: POST /api/offensive/promote crea finding en DB + KG
OUTPUT: Finding con evidencia completa
ESTADO: ✅ Automatizado
GAP: No hay validación humana antes de promover
```

### 7. Finding → Report

```
INPUT: Finding confirmado
PROCESO: Report templates + auto-report subscriber
OUTPUT: Draft report listo para submission
ESTADO: ✅ Automatizado
GAP: Templates específicos por plataforma (H1, BC, Inti) no implementados
```

### 8. Report → Submission

```
INPUT: Draft report
PROCESO: Revenue Pipeline submit + sync
OUTPUT: Submission status tracking
ESTADO: 🟡 Semi-automatizado
GAP: No hay auto-submission. Hunter debe revisar y enviar manualmente
```

### 9. Submission → Learning

```
INPUT: Outcome (accepted/rejected/duplicate)
PROCESO: FeedbackTuner.analyze() + RewardLearner.analyze()
OUTPUT: Ajuste de pesos por tipo de vuln y programa
ESTADO: 🟡 Semi-automatizado
GAP: Pocos datos reales de feedback. Loop no está cerrado con datos de producción
```

---

## Gaps Identificados

### P0 — Bloquean Revenue

| # | Gap | Impacto | Solución propuesta |
|---|---|---|---|
| 1 | **Sin HTTP probe automático en scheduler** | El scheduler genera hipótesis pero no las prueba | Conectar VALIDATE stage con AttackPlanner + execute_plan |
| 2 | **Sin auto-submission a plataformas** | Hunter debe copiar/pegar reportes manualmente | Auto-submit via API de H1/BC cuando confidence > 0.8 |
| 3 | **RewardLearner no persiste ajustes** | Los pesos se pierden al reiniciar | Arreglar `_load_adjustments()` (P0.2 en TASK_QUEUE) |

### P1 — Aumentan Productividad

| # | Gap | Impacto | Solución propuesta |
|---|---|---|---|
| 4 | **Solo 5 tipos de vulnerabilidad** | CSRF, LFI, CMDi, GraphQL, Race Conditions no cubiertos | Nuevos reasoners + planners |
| 5 | **Sin notificaciones proactivas** | ORION no avisa cuando hay algo importante | Sistema de alertas (Discord/Telegram/notif local) |
| 6 | **Sin simulación de ROI antes de investigar** | Se pierde tiempo en targets de bajo valor | ExpectedValue prioritizer con simulación |
| 7 | **Templates de reporte genéricos** | No optimizados por plataforma | Templates H1/BC/Inti con formatos específicos |

### P2 — Mejoran Experiencia

| # | Gap | Impacto | Solución propuesta |
|---|---|---|---|
| 8 | **Sin screenshots automáticos** | Evidencia sin captura visual | Headless browser screenshot en probe |
| 9 | **Sin frontend para AttackPlanner** | Solo accesible via API | UI para ver planes y ejecutarlos |
| 10 | **Dashboard sin widget de revenue trends** | No se ve evolución mensual | Sparklines en Revenue Dashboard |

---

## Autonomía Real (Puede trabajar mientras dormís?)

| Aspecto | Estado | Detalle |
|---|---|---|
| Scheduler corre 24/7 | ✅ | Pipeline cíclico cada 30-120 min |
| Discovery automático | ✅ | Scrapea plataformas periódicamente |
| Hipótesis automáticas | ✅ | Reasoners generan sin intervención |
| Pruebas automáticas | 🟡 | Probe.execute_plan() existe pero no integrado en scheduler |
| Reportes automáticos | 🟡 | Auto-report subscriber existe, falta template por plataforma |
| Aprendizaje automático | 🟡 | FeedbackTuner funciona con datos, pero pocos datos reales |
| Notificaciones | ❌ | No hay sistema de alertas cuando encuentra algo |
| Backups automáticos | 🟡 | `python run.py --backup` existe, no hay schedule automático |
| Mantenimiento DB | ✅ | WAL checkpoint, vacuum disponibles |

---

## Documentación por Feature

| Feature | docs/ | .ai/ | README | Screenshot |
|---|---|---|---|---|
| Discovery | ✅ | ✅ | ✅ | ❌ |
| AttackPlanner | NEW | ❌ | ❌ | ❌ |
| ProbeEngine | ✅ | ✅ | ❌ | ❌ |
| EvidenceComposer | ✅ | ✅ | ❌ | ❌ |
| Mission Widget | NEW | ✅ | ❌ | ❌ |
| Knowledge Graph | NEW | ✅ | ❌ | ❌ |
| Revenue Pipeline | NEW | ✅ | ❌ | ❌ |
| COPILOT | ✅ | ✅ | ❌ | ❌ |
| Hermes | ✅ | ✅ | ✅ | ❌ |
| Financial | ✅ | ✅ | ❌ | ❌ |

---

## Prioridades para Siguiente Sprint

```
P0:
1. Conectar AttackPlanner + execute_plan al scheduler (VALIDATE stage)
2. Arreglar persistencia de RewardLearner (P0.2 TASK_QUEUE)
3. Sistema de notificaciones proactivas

P1:
4. Reasoners + planners para CSRF, LFI, CMDi
5. Templates de reporte por plataforma (H1, BC, Inti)
6. Auto-submission pipeline con confirmation humana

P2:
7. Frontend para AttackPlanner (visualizar planes, ejecutar)
8. Screenshots automáticos en probe
9. Dashboard de revenue trends
```
