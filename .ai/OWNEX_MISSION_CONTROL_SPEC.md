# OWNEX Mission Control v1 — Pre-Implementation Spec

> Estado: Auditoría completada.
> Próximo: Implementación Sprint.

---

## 1. Hallazgo crítico

**MissionControl.vue ya existe pero no funciona con datos reales.**

Todos los sub-componentes del dashboard (`ThroughputCore`, `AgentFleet`, `OpportunityRadar`, `NextBestAction`, `WorkCyclesGrid`, `KnowledgeFeed`) usan **props estáticas con `withDefaults`**. El `fetch` a `/api/mission/status` existe en el padre pero los datos **no se pasan a los hijos**.

El backend ya tiene **todo lo necesario**. No se requieren nuevos endpoints para v1.

---

## 2. Mapa Backend → Dashboard

| Bloque Dashboard | Endpoint Backend | Existe |
|-----------------|------------------|--------|
| **Throughput Core** | `GET /api/mission/status` (ingress) + `GET /api/overview` (pipeline stages, counts) | ✅ |
| **Opportunity Radar** | `GET /api/opportunity/top` + `GET /api/opportunity-score/top5` | ✅ |
| **Agent Fleet** | `GET /api/system/state` (services) + `GET /api/agents/health` | ✅ |
| **Work Cycles** | `GET /api/mission/status` (apps) + `GET /api/pipeline/stages` | ✅ |
| **Next Best Action** | `GET /api/orion/next-action` + `GET /api/orchestrator/next-action` | ✅ |
| **Knowledge Feed** | `GET /api/activity` (72h feed) + `GET /api/operations/timeline` | ✅ |
| **Health Score** | `GET /api/core/health/summary` (ya usado por widget) | ✅ |
| **Revenue Snapshot** | `GET /api/economic/financial-summary` + `GET /api/revenue/summary` | ✅ |

**Cero endpoints nuevos.** Todos los datos ya están servidos por el backend.

---

## 3. Mapa Frontend Existente

### Lo que se reutiliza

| Componente | Archivo | Uso |
|-----------|---------|-----|
| OWNEX shell | `AppLayout.vue`, `AppSidebar.vue` | Layout completo, navegación |
| Theme | `style.css` | Design system OWNEX completo |
| KPIBlock | `components/ui/KPIBlock.vue` | KPIs animados (número, moneda, porcentaje) |
| StatusDot | `components/ui/StatusDot.vue` | Indicador 🟢🟡🔴 con ping |
| Card | `components/ui/Card.vue` | Contenedor de tarjetas |
| Timeline | `components/ui/Timeline.vue` | Línea de tiempo de eventos |
| LoadingState | `components/ui/LoadingState.vue` | Estado de carga |
| ErrorState | `components/ui/ErrorState.vue` | Estado de error |
| EmptyState | `components/ui/EmptyState.vue` | Estado vacío |
| Skeleton | `components/ui/Skeleton.vue` | Placeholder de carga |
| WidgetDashboard | `components/widgets/WidgetDashboard.vue` | Sistema de widgets con data fetching |
| WidgetRegistry | `components/widgets/WidgetRegistry.ts` | 10 widgets con dataSources y refresh |
| Charts | `components/charts/` | BarChart, DoughnutChart, LineChart |
| API client | `lib/api.ts` | Cliente centralizado con auth |
| Stores | `stores/` | Pinia stores: findings, hunt, notifications |

### Lo que se modifica

| Componente | Archivo | Cambio necesario |
|-----------|---------|-----------------|
| **MissionControl.vue** | `pages/MissionControl.vue` | Pasar datos reales a hijos, agregar nuevos bloques |
| **ThroughputCore.vue** | `components/dashboard/ThroughputCore.vue` | Recibir props reales en vez de defaults |
| **AgentFleet.vue** | `components/dashboard/AgentFleet.vue` | Fetch real a `/api/system/state` |
| **OpportunityRadar.vue** | `components/dashboard/OpportunityRadar.vue` | Fetch real a `/api/opportunity/top` |
| **NextBestAction.vue** | `components/dashboard/NextBestAction.vue` | Fetch real a `/api/orion/next-action` |
| **KnowledgeFeed.vue** | `components/dashboard/KnowledgeFeed.vue` | Fetch real a `/api/activity` |

### Lo que NO se toca

- `AppLayout.vue`, `AppSidebar.vue`, `OrionSidebar.vue` — estables
- `style.css` — theme OWNEX completo
- Router, stores, API client — funcionan
- Componentes UI (Card, Button, Badge, etc.) — reutilizables
- Widget system — alternativa si se prefiere grid dinámico
- Health Center (`HealthCenter.vue`) — ya funcional con datos reales

---

## 4. Arquitectura del Dashboard

```
MissionControl.vue
│
├── Header: greeting, timestamp, health score, refresh
│
├── ROW 1: Throughput
│   ├── KPIs: findings, reports, targets, revenue (KPIBlock)
│   └── Pipeline stages: detected → validated → confirmed → reported
│
├── ROW 2: Intelligence
│   ├── Opportunity Radar (top 5, con reward/confidence/action)
│   └── Agent Fleet (5 agents con status + last heartbeat)
│
├── ROW 3: Action
│   ├── Next Best Action (recomendación principal)
│   └── Work Cycles (5 tarjetas con estado)
│
├── ROW 4: Knowledge
│   ├── Activity Timeline (últimos eventos)
│   └── Revenue Snapshot (USD/h, este mes, pendiente)
│
└── Footer: Quick Actions (HUNT, Security, Reports, Health)
```

### Layout responsivo

- Desktop (>1024px): 4 rows, columnas 2/3 + 1/3
- Tablet (>640px): 2 columns
- Mobile: 1 column, apilado

---

## 5. Flujo de datos por componente

### ThroughputCore
- **Props**: `{ findings_total, findings_confirmed, findings_pending, reports_total, targets_active, revenue_total, revenue_pending, pipeline_stages }`
- **Fetch**: `GET /api/mission/status` + `GET /api/overview`
- **Refresh**: 30s

### AgentFleet
- **Props**: `{ agents: [{ name, status, last_heartbeat, provider }] }`
- **Fetch**: `GET /api/system/state` → `services` array
- **Refresh**: 15s
- **Estados**: 🟢 online / 🟡 degraded / 🔴 offline / ⚪ unknown

### OpportunityRadar
- **Props**: `{ opportunities: [{ title, reward, confidence, type, action }] }`
- **Fetch**: `GET /api/opportunity/top?limit=5`
- **Refresh**: 60s

### NextBestAction
- **Props**: `{ action: { title, reason, effort, reward, type } }`
- **Fetch**: `GET /api/orion/next-action`
- **Refresh**: 60s (o on-demand)

### WorkCyclesGrid
- **Props**: `{ cycles: [{ id, name, status, description }] }`
- **Fetch**: `GET /api/mission/status` → `apps`
- **Refresh**: 60s
- **Ciclos**: Security 🟢, Forge ⚪, Pulse ⚪, Vault 🟡, Atlas ⚪

### KnowledgeFeed (renamed to ActivityTimeline)
- **Props**: `{ events: [{ type, description, timestamp, target }] }`
- **Fetch**: `GET /api/activity?hours=24`
- **Refresh**: 30s

### Revenue Snapshot (new)
- **Props**: `{ usd_per_hour, monthly_total, pending_total, best_platform }`
- **Fetch**: `GET /api/economic/financial-summary`
- **Refresh**: 60s

---

## 6. Riesgos

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|------------|
| `/api/mission/status` no tiene todos los campos necesarios | Alta | Extender endpoint en backend (cambio pequeño en `mission.py`) |
| Dashboard components esperan props que no existen | Media | Typescript interfaces en `types/index.ts` |
| WidgetDashboard duplica funcionalidad | Baja | Usar MissionControl layout custom, no widget grid |
| Test de MissionControl desactualizado | Media | Actualizar test después de implementación |
| Auth token expirado durante sesión | Baja | `api.ts` ya maneja 401 → redirige a login |

---

## 7. Orden de implementación

```
Sprint 1: Base
1. Actualizar types/index.ts con interfaces de Mission Control
2. Modificar ThroughputCore.vue para recibir props reales
3. Modificar AgentFleet.vue para fetch real
4. Conectar MissionControl.vue: pasar datos a hijos

Sprint 2: Contenido
5. Modificar OpportunityRadar.vue para fetch real
6. Modificar NextBestAction.vue para fetch real
7. Agregar Revenue Snapshot component
8. Modificar KnowledgeFeed → ActivityTimeline con fetch real

Sprint 3: Pulido
9. Responsive layout
10. Estados de carga/error/vacío en cada componente
11. Actualizar tests
12. Verificar post-restart
```

---

## 8. Lo que NO se hace en v1

- ❌ No crear nuevos endpoints de backend
- ❌ No tocar router, stores, layout, sidebar
- ❌ No agregar nuevas dependencias npm
- ❌ No migrar a widget system (se puede evaluar en v2)
- ❌ No conectar APIs externas (HackerOne, etc.)
- ❌ No modificar el theme/design system
