# NEXT 30 DAYS PLAN — ORION v4.6.0

> Plan de ejecución priorizado por ROI: probabilidad de encontrar vulnerabilidades, calidad de evidencia, probabilidad de aceptación, automatización, reducción de trabajo manual.

---

## Priorización

Cada tarea puntúa en 5 dimensiones (1-5):

| Dimensión | Peso |
|---|---|
| Detección de vulnerabilidades | x3 |
| Calidad de evidencia | x2 |
| Probabilidad de aceptación | x2 |
| Automatización | x1.5 |
| Reducción de trabajo manual | x1.5 |

---

## Sprint 1 — Weeks 1-2 (Julio 20 - Agosto 2)

### P0: AttackPlanner + Scheduler Integration

**Score**: 4.8/5

**Qué**: Conectar AttackPlanner.execute_plan() al scheduler en la etapa VALIDATE. Cuando el scheduler tenga hipótesis con confidence > 0.6, ejecutar probe real contra el target.

**Archivos**: `api/scheduler.py`, `core/offensive/probe/engine.py`

**Checklist**:
- [ ] En VALIDATE stage, obtener hipótesis de alta prioridad
- [ ] Ejecutar AttackPlanner.plan() para cada una
- [ ] Ejecutar ProbeEngine.execute_plan() con auth del target
- [ ] Si confirmed → crear finding automáticamente
- [ ] Log: `[ATTACK] Probed {endpoint} — confirmed={bool} confidence={score}`

**Esfuerzo**: 1 día → **$ impacto**: ⭐⭐⭐⭐⭐

---

### P0: Sistema de Notificaciones

**Score**: 4.5/5

**Qué**: Cuando ORION encuentre algo importante mientras el usuario no está, debe poder avisar.

**Canales**: Discord webhook (ya existe), notificación desktop

**Eventos críticos**:
- Finding confirmado con confidence > 0.7
- Nuevo programa de alto valor (> $5000)
- Submission aceptada
- Error del sistema

**Esfuerzo**: 2 días → **$ impacto**: ⭐⭐⭐⭐⭐

---

### P0: RewardLearner Persistence Fix

**Score**: 4.2/5

**Qué**: `cores/intelligence/reward_learning.py:229` — `_load_adjustments()` itera un dict vacío después de restart. Los pesos aprendidos se pierden.

**Fix**: Persistir `_vuln_adjustments` a SQLite o JSON.

**Esfuerzo**: 30 min → **$ impacto**: ⭐⭐⭐⭐

---

## Sprint 1 — Week 2

### P1: Nuevos Reasoners (CSRF, LFI, CMDi)

**Score**: 4.0/5

**Qué**: Agregar reasoners para CSRF, Local File Inclusion, Command Injection. Cada uno necesita:
- Reasoner en `core/offensive/reasoners/`
- AttackPlanner en `core/offensive/attack_planner.py`
- Payloads específicos
- Detector en `core/offensive/probe/engine.py`

**Esfuerzo**: 3-4 días → **$ impacto**: ⭐⭐⭐⭐

---

### P1: Report Templates por Plataforma

**Score**: 3.8/5

**Qué**: Templates markdown optimizados para HackerOne, Bugcrowd, Intigriti. Cada plataforma tiene formato, secciones y tono diferente.

**Archivos**: `core/reports/templates/`

**Esfuerzo**: 1-2 días → **$ impacto**: ⭐⭐⭐⭐⭐

---

### P1: Auto-Submission Pipeline

**Score**: 3.5/5

**Qué**: Cuando un finding tiene confidence > 0.8, quality_score > 0.8, y el template está listo → enviar automáticamente con confirmación humana opcional.

**Dependencias**: Templates por plataforma (arriba)

**Esfuerzo**: 3 días → **$ impacto**: ⭐⭐⭐⭐⭐

---

## Sprint 2 — Weeks 3-4

### P1: HTTP Probe Automático en Scheduler

**Score**: 3.5/5

**Qué**: Completar la integración iniciada en Sprint 1. Asegurar que el scheduler pueda ejecutar probes sin intervención humana, con rate limiting y manejo de errores.

**Esfuerzo**: 2 días → **$ impacto**: ⭐⭐⭐⭐

---

### P2: Screenshots Automáticos

**Score**: 3.0/5

**Qué**: Usar Playwright o similar para tomar screenshots de las respuestas HTTP durante el probe. La evidencia visual aumenta drásticamente la tasa de aceptación.

**Esfuerzo**: 2 días → **$ impacto**: ⭐⭐⭐⭐

---

### P2: Auto-Backup Nocturno

**Score**: 2.8/5

**Qué**: Systemd timer o scheduler job para `python run.py --backup` con rotación de 7 días.

**Esfuerzo**: 1 día → **$ impacto**: ⭐⭐

---

### P2: Frontend AttackPlanner

**Score**: 2.5/5

**Qué**: Página Vue para ver planes de ataque, ejecutarlos, y ver resultados. Actualmente solo accesible via API.

**Esfuerzo**: 2 días → **$ impacto**: ⭐⭐⭐

---

## Resumen 30 Días

| Semana | Tareas | Esfuerzo | $ Impacto |
|---|---|---|---|
| 1 | AttackPlanner → Scheduler, Notificaciones, RewardLearner fix | 3.5 días | ⭐⭐⭐⭐⭐ |
| 2 | Nuevos reasoners (3), Templates reportes, Auto-submission pipeline | 7-9 días | ⭐⭐⭐⭐⭐ |
| 3 | HTTP probe automático completo, Screenshots automáticos | 4 días | ⭐⭐⭐⭐ |
| 4 | Auto-backup, Frontend AttackPlanner | 3 días | ⭐⭐⭐ |

**Total estimado**: 17-19 días hábiles
**Cobertura**: 80% del gap de autonomía
**Riesgo principal**: Dependencias externas (APIs de plataformas bug bounty)

---

## Lo que NO está en este plan

| Feature | Motivo |
|---|---|
| GraphQL reasoner | Baja probabilidad de encontrar vs esfuerzo |
| Race Condition reasoner | Difícil de automatizar correctamente |
| Mobile companion app | No impacta revenue directamente |
| PWA improvements | No impacta revenue |
| Tauri desktop | Ya existe, no mejora revenue |
| New integrations (Synack, etc.) | Baja prioridad vs cerrar pipeline existente |
