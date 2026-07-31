# DAILY WORKFLOW — CATEYE v4.6.0

> Rutina diaria, semanal y mensual para usar CATEYE en bug bounty real.
> Este es el documento más consultado después de meses de uso.

---

## Rutina Diaria

### 08:00 — Abrir CATEYE

```
http://127.0.0.1:8000 → Mission Control
```

En 30 segundos chequeá:

| Qué mirar | Dónde | Por qué |
|---|---|---|
| Oportunidades | Widget "Top Opportunities" | Programas nuevos o mejor rankeados |
| Próxima acción | `GET /api/orion/next-action` | ORION te dice qué hacer hoy |
| Discovery status | Discovery Monitor widget | Programas nuevos descubiertos durante la noche |
| Scheduler status | Pipeline Monitor | Última ejecución, resultados |

### 08:15 — Elegir target del día

ORION ya priorizó. Si hay un target recomendado:

```
POST /api/targets/{id}/scan?mode=FAST
```

Si no, revisá `GET /api/orion/next-action` para elegir.

### 08:20 — Lanzar recon

Mientras CATEYE scanea, prepará el entorno:

- Repasá el scope del programa
- Revisá si hay programas similares en el historial
- Leé los últimos reportes del programa (si los hay)

### 09:00 — Revisar resultados

Cuando el scan termine:

1. `/attack-surface` → Endpoints descubiertos
2. `/hypotheses` → Hipótesis generadas automáticamente
3. Findings de nuclei → Validar manualmente si son críticos

### 09:30 — Validar

```
POST /api/validation/validate
{ "endpoint_id": "...", "hypothesis_type": "idor" }
```

O en batch:

```
POST /api/validation/batch
```

### 10:00 — Findings

- Revisar findings generados
- Confirmar o marcar como false positive
- Findings confirmados → auto-report genera borrador

### 10:30 — Reportes

- Editar borrador automático
- Exportar
- Enviar a plataforma

### 11:00 — Cierre

- Revisar estado de submissions previas
- Chequear earnings del día
- Anotar observaciones para ORION

---

## Rutina Semanal

### Lunes — Planificar

```
GET /api/opportunity/top
GET /api/orion/next-action
```

Elegir 2-3 programas para la semana. Anotar objetivos.

### Miércoles — Revisión

```
GET /api/findings?status=open     # Findings pendientes
GET /api/hypotheses                # Hipótesis sin validar
POST /api/validation/batch         # Validación batch
```

### Viernes — Cierre

```
GET /api/reports                   # Reportes de la semana
GET /api/financial/state           # Estado financiero
GET /api/stats                     # Métricas
```

---

## Rutina Mensual

### Revisión de sistema

```
GET /api/system/status
GET /api/system/state
GET /api/health
```

### Revisión ORION

```
GET /api/orion/context
```

ORION aprendió de tus resultados del mes. Verificá:
- ¿Las prioridades tienen sentido?
- ¿Los ajustes de RewardLearner reflejan tu experiencia real?
- ¿Hay patrones que ORION debería ignorar?

### Limpieza

- Targets inactivos → reconsiderar
- Findings viejos → archivar
- Reports cerrados → revisar si hay lecciones aprendidas

---

## Lo que CATEYE hace automáticamente

| Automatización | Cada | Qué hace |
|---|---|---|
| Discovery Monitor | 24h | Descubre nuevos programas |
| Scheduler DISCOVER | 1h | Busca programas nuevos |
| Scheduler RECON | 30min | Escanea targets priorizados |
| Scheduler HYPOTHESIS | 15min | Genera hipótesis sobre endpoints |
| Scheduler VALIDATE | 2h | Valida findings abiertos |
| Scheduler REPORT | 1h | Genera reportes |
| Financial Sync | 30min | Sincroniza earnings |
| Health Monitor | 8s | Monitorea salud del sistema |
| Auto-report | Evento | Borrador al confirmar finding |

---

## Lo que NUNCA debés esperar de CATEYE

- ❌ Que envíe reportes automáticamente
- ❌ Que gaste dinero
- ❌ Que explote vulnerabilidades
- ❌ Que reemplace tu criterio en findings
- ❌ Que sea multi-usuario
- ❌ Que funcione sin conexión a internet (parcialmente)
