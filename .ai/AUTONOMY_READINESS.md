# AUTONOMY READINESS — ORION v4.6.0

> ¿Puede ORION trabajar mientras el usuario duerme?
> Auditoría de capacidades autónomas. Julio 2026.

---

## Score de Autonomía por Área

| Área | % | Estado |
|---|---|---|
| Discovery automation | 85% | ✅ Scrapea periódicamente, pero no alerta |
| Intelligence automation | 80% | ✅ Reasoners generan hipótesis sin intervención |
| Planning automation | 70% | ✅ AttackPlanner genera TestPlan, no integrado en scheduler |
| Validation automation | 40% | 🟡 Probe existe, no se ejecuta automáticamente |
| Evidence automation | 85% | ✅ EvidenceComposer genera bundle completo |
| Report automation | 60% | 🟡 Draft automático, submission manual |
| Learning automation | 40% | 🟡 Feedback loop existe, pocos datos reales |
| Financial automation | 80% | ✅ Sync automático de balances y crypto |
| Maintenance automation | 50% | 🟡 Backup manual, WAL checkpoint automático |
| Notification automation | 0% | ❌ No hay sistema de alertas |

**Overall Autonomy Score: 59%** — ORION puede trabajar sin supervisión en modo parcial, pero no puede ejecutar un ciclo completo discovery→submission sin intervención humana.

---

## ¿Qué puede hacer ORION sin supervisión?

### Mientras dormís (24/7):

```
1. Discovery: Encontrar nuevos programas y targets ✅
2. Intelligence: Analizar tecnologías y generar hipótesis ✅
3. Planning: Generar planes de ataque (si hay hipótesis) ✅
4. Financial Sync: Actualizar balances y precios crypto ✅
5. Maintenance: WAL checkpoint, event pruning ✅
6. Learning: Registrar eventos y métricas ✅
```

### Lo que NO puede hacer sin humano:

```
7. Ejecutar probes HTTP contra targets reales ❌
8. Promover findings a reports ❌
9. Enviar submissions a plataformas ❌
10. Evaluar calidad de evidencia ❌
11. Tomar decisiones de alto riesgo ❌
12. Notificar al usuario cuando encuentra algo ❌
```

---

## Gaps de Autonomía Críticos

### Gap 1: Sin integración AttackPlanner → Scheduler

**Problema**: El scheduler tiene etapa VALIDATE pero no usa AttackPlanner ni execute_plan().

**Solución**: En la etapa VALIDATE del scheduler, para cada hipótesis con confidence > 0.6:
1. Ejecutar AttackPlanner.plan()
2. Ejecutar ProbeEngine.execute_plan() contra el target real
3. Si confirmed → promover a finding automáticamente

**Archivos**: `api/scheduler.py`, `core/offensive/attack_planner.py`, `core/offensive/probe/engine.py`

**Esfuerzo**: 1 día

### Gap 2: Sin sistema de notificaciones

**Problema**: ORION no puede avisar al usuario cuando encuentra algo importante.

**Solución**: Sistema multicanal:
- Discord webhook (ya existe `cores/notifications/discord.py`)
- Telegram bot
- Notificaciones locales (desktop)
- Email (Outlook connector existe)

Eventos a notificar:
- Finding confirmado con confianza > 0.7
- Nuevo programa de alto valor (> $5000)
- Error crítico del sistema
- Submission aceptada/rechazada

**Esfuerzo**: 2-3 días

### Gap 3: Sin auto-submission pipeline

**Problema**: El reporte se genera pero el hunter debe copiar/pegar manualmente.

**Solución**: 
- Auto-submit cuando confidence > 0.8 y quality_score > 0.8
- Submission con confirmation humana para casos borderline
- Tracking automático de estado

**Esfuerzo**: 3-5 días

### Gap 4: Sin mantenimiento automático nocturno

**Problema**: Backup, compactación DB, limpieza de logs son manuales.

**Solución**: Jobs nocturnos:
- 02:00 AM: WAL checkpoint + vacuum
- 03:00 AM: Backup automático con rotación de 7 días
- 04:00 AM: Limpieza de logs > 30 días
- 05:00 AM: Health check completo + reporte

**Esfuerzo**: 1 día

---

## Escenario Nocturno Ideal

```
00:00 — Discovery: Buscar nuevos programas
00:30 — Intelligence: Analizar targets existentes
01:00 — Hypothesis: Reasoners generan hipótesis nuevas
01:30 — Priority: ORION NextAction prioriza
02:00 — Maintenance: WAL checkpoint + vacuum
02:30 — Attack: Ejecutar probes de alta prioridad (confidence > 0.7)
03:00 — Evidence: Componer evidencia para findings confirmados
03:30 — Financial: Sync balances + precios crypto
04:00 — Backup: Backup automático con rotación
04:30 — Report: Generar drafts para findings confirmados
05:00 — Learning: Analizar resultados del ciclo
06:30 — Notification: Resumen nocturno al usuario
```

**Estado actual**: Solo se ejecutan Discovery, Intelligence, Hypothesis, Financial sync y maintenance. El resto requiere intervención humana.

---

## Próximos Pasos para Autonomía

### Sprint 1 (Esta semana)
1. Conectar AttackPlanner al scheduler (VALIDATE stage)
2. Agregar notificaciones Discord para eventos críticos
3. Job nocturno de backup automático

### Sprint 2 (Próxima semana)
4. Auto-submission pipeline para findings con confianza > 0.8
5. Limpieza automática de datos temporales
6. Health check nocturno con reporte

### Sprint 3 (Siguiente)
7. Ciclo nocturno completo (escenario ideal)
8. Sistema de alertas multicanal
9. Dashboard de autonomía (qué se ejecutó automáticamente)
