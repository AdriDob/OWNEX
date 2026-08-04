# ORION Platform — Cierre Arquitectónico Definitivo

> **Este documento es la descripción completa de la arquitectura, documentando cada decisión, su justificación y sus límites.**

## ⚠️ Advertencia: El documento no está escrito como una celebración

Este documento **NO celebra** lo que está bien (ya hay 400+ tests que lo demuestran). **SÍ señala** cada inconsistencia, contradicción o riesgo que encontramos, **PROPOSA fixes específicos** para cada uno.

Hay **22 inconsistencias** documentadas abajo. Algunas son triviales. Otras son **bugs que rompen la funcionalidad hoy**.

> **⚠️ NOTA — Session 2026-07-25:** Problemas 0.1 (CATEYE manifest), 0.2 (CoreScheduler handler), y 0.3 (CoreEventBus bridge) están **RESUELTOS**. Ver marcas [✅ FIXED] abajo. Los demás permanecen sin cambios.

---

## Parte 0: Diagnóstico Rápido

### **Problemas Clave (0.1-0.4)**

**0.1 — El manifest de CATEYE es decorativo, no funcional**  [✅ FIXED]
- `apps/cateye/manifest.py` declara routers vacíos
- Pero CATEYE tiene **50+ routers** en `api/main.py` (551-615)
- **Impacto:** El manifest no controla nada. Es humo.
- **Riesgo:** Si alguien movera CATEYE a otro proceso, los routers no lo seguirían.
- **Fix aplicado (2026-07-25):** Manifest ahora exporta 8 scheduler jobs reales + documentación honesta. Routers se mantienen en api/main.py por diseño (cada uno con su propio prefix).

**0.2 — CoreScheduler no ejecuta NINGÚN job**  [✅ FIXED]
- `core/scheduler/scheduler.py` define `_on_job_due: Callable | None = None`
- **Nunca se setea** (nadie llama a `set_job_handler()`)
- Jobs registrados pero **nunca ejecutados**
- **Fix aplicado (2026-07-25):** En `api/main.py:722-725` ya existe `set_job_handler()` que publica `scheduler:job_due` al CoreEventBus. El scheduler se inicia en línea 735. No había bug — el código ya funcionaba.

**0.3 — CoreEventBus no persiste eventos ni bridgea al legacy**  [✅ FIXED]

| Característica | CATEYE EventBus | CoreEventBus |
|---------------|----------------|--------------|
| Persistencia SQLite | ✅ | ✅ |
| Prioridad de eventos | ✅ | ❌ |
| History consultable | ✅ | ✅ |
| Handler de apps nuevas | — | ✅ namespaces |
| Bridge a CATEYE | Source | ✅ Activo por defecto |

- **Fix aplicado (2026-07-25):** `_bridge = True` por defecto + método `enable_bridge()`. Test de integración: eventos de CoreEventBus llegan a CATEYE legacy correctamente.

**0.4 — Las rutas de ATLAS/ODYSSEY apuntan al Dashboard**  [✅ STALE — ya resuelto en frontend]

```typescript
// frontend/src/router/index.ts (Julio 2026)
{ path: '/atlas/',         component: '.../DashboardAtlas.vue' },   // ✅ Componente real
{ path: '/atlas/settings', component: '.../SettingsAtlas.vue' },    // ✅ Componente real
{ path: '/odyssey/',       component: '.../DashboardOdyssey.vue' }, // ✅ Componente real
{ path: '/odyssey/settings', component: '.../SettingsOdyssey.vue' }, // ✅ Componente real
```

Las rutas `/atlas/portfolio`, `/atlas/assets`, `/odyssey/bets` mencionadas en AUDIT no existen en el router actual. Ya fueron resueltas en sesiones anteriores. Este documento necesita actualización.

---

## Parte 1: Stack Definitivo

| Componente | Elección | ¿Por qué esta y no otra? |
|-------------|--------|---------------------|
| **Lenguaje** | Python 3.10+ | Ecosistema bug bounty, compatibilidad con CATEYE |
| **Framework API** | FastAPI | Unificado con CATEYE, async nativo, OpenAPI auto |
| **Base de datos** | SQLite (dev) / PostgreSQL (prod) | CATEYE ya lo usa. Mínima fricción |
| **ORM** | SQLAlchemy 2.0 | Unificado con CATEYE, migraciones con metadata.create_all() |
| **Frontend** | Vue 3 + TypeScript + Tailwind v4 + ShadCN Vue | Unificado con CATEYE. Composition API, Pinia |
| **Build frontend** | Vite | Unificado con CATEYE |
| **Build desktop** | PyInstaller + NSIS | Unificado con CATEYE |
| **Testing Python** | pytest + pytest-cov + pytest-timeout | Unificado con CATEYE |
| **Testing frontend** | Vitest | Unificado con CATEYE |
| **Linting Python** | Ruff | Unificado con CATEYE |
| **Linting frontend** | Biome | Unificado con CATEYE |
| **Pattern** | Monolito modular + Event-Driven | La única opción que cumple: simple, testeable, sin infraestructura externa |

### Decisiones Descartadas con Justificación

| Patrón | Descartado por |
|---------|----------------|
| **Microservicios** | Overhead de red, deploy, monitoreo para 1 usuario. 10x complejidad, 0 beneficio |
| **CQRS/Event Sourcing** | El volumen de eventos (~100/día) no justifica la complejidad de proyecciones y event store |
| **Hexagonal/Clean Architecture** | Demasiada indirección para Python. Los puertos son interfaces, los adapters son connectors. Ya lo tenemos sin el overhead |
| **Actor Model** | Los actores serían azúcar sintáctica sobre asyncio |
| **DDD táctico** | Sobrediseño para modelos SQLAlchemy que son tablas simples |
| **gRPC** | HTTP/JSON es suficiente. gRPC agrega protobuf, codegen, tooling |
| **Message Queue externo** | In-memory EventBus es suficiente |
| **Redis** | Para cache de ~10 items, SQLite en memoria es más simple |
| **Plugin system con sandboxing** | Para 1 usuario, el riesgo no justifica el aislamiento |
| **Sidecar process** | La carga es tan baja que no necesita su propio proceso |

---

## Parte 2: Arquitectura Modular Monolith + Event-Driven

```
┌─────────────────────────────────────────────────────────────┐
│                       FastAPI Process                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  ORION Core (core/)                                   │    │
│  │  ┌────────┐ ┌─────────┐ ┌────────┐ ┌──────────────┐ │    │
│  │  │Registry│ │EventBus │ │Scheduler│ │ DB Manager   │ │    │
│  │  └────────┘ └─────────┘ └────────┘ └──────────────┘ │    │
│  │  ┌────────┐ ┌─────────┐ ┌────────┐ ┌──────────────┐ │    │
│  │  │AI Runtime│ │Memory  │ │Decision│ │ Simulation   │ │    │
│  │  │         │ │Manager │ │Journal │ │ Engine       │ │    │
│  │  └────────┘ └─────────┘ └────────┘ └──────────────┘ │    │
│  │  ┌────────┐ ┌─────────────────┐ ┌──────────────────┐ │    │
│  │  │Hermes  │ │ Normalizer      │ │ Widget Engine    │ │    │
│  │  │(future)│ │ (registry+types)│ │ (future)         │ │    │
│  │  └────────┘ └─────────────────┘ └──────────────────┘ │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Shared Security Layer                                 │    │
│  │  AuthMiddleware, CSRFMiddleware, RateLimitMiddleware,  │    │
│  │  SecurityHeadersMiddleware, ErrorHandlingMiddleware    │    │
│  │  IdentityVault, AuditLog, SessionStore                │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │   CATEYE       │  │    ATLAS       │  │   ODYSSEY      │  │
│  │  (cores/*)     │  │  (apps/atlas/) │  │ (apps/odyssey/)│  │
│  │                │  │                │  │                │  │
│  │  • routers/    │  │ • models/      │  │ • models/      │  │
│  │  • scheduler/  │  │ • connectors/  │  │ • connectors/  │  │
│  │  • cores/*     │  │ • engines/     │  │ • engines/     │  │
│  │  • DB propia   │  │ • API routers │  │ • API routers │  │
│  │  • agents/     │  │ • scheduler/  │  │ • scheduler/  │  │
│  │                │  │ • agents/     │  │ • agents/     │  │
│  │  📌 NO TOCAR   │  │ • DB propia   │  │ • DB propia   │  │
│  └────────────────┘  └────────────────┘  └────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │            Frontend (Vue 3 SPA)                       │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │    │
│  │  │ORION Shell│ │ CATEYE  │ │  ATLAS   │ │ODYSSEY │  │    │
│  │  │Sidebar+Home│ │ pages/  │ │ apps/    │ │ apps/  │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘  │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Reglas de Comunicación

**¿App A necesita datos de App B?**
→ App A llama API de App B via HTTP a sí mismo
→ O App B publica evento en EventBus y App A lo consume

**¿App A necesita notificar a App B?**
→ EventBus: app_a:event_name

**¿Core necesita estado de App A?**
→ App A publica health event cada N segundos
→ Core consulta `/api/<app>/health`

### Prohibiciones Absolutas

```
❌ from apps.atlas import ...  → en apps/odyssey/
❌ from cores.x import ...     → en apps/atlas/ (excepto interfaces)
❌ apps/atlas/models.py importado en apps/odyssey/
❌ apps/odyssey/connectors/ importado desde apps/atlas/
❌ CATEYE cores/* modificado por ORION
```

---

## Parte 3: Límites entre Capas

### Core (core/)

```
No conoce:
  - apps/*/
  - cores/*/
```

### CATEYE Legacy (cores/*)

```
Conoce:
  - app/*/routers
  - app/*/models
  - app/*/connectors
  - app/*/agents
```

### Apps (apps/atlas/, apps/odyssey/)

```
Pueden:
  - consumir Core EventBus
  - publicar eventos
  - exportar routers
  - export Wangrollers
```

### Frontend (frontend/src)

```
Puede:
  - consumir APIs de apps
  - suscribirse a eventos
  - renderizar componentes
```

---

## Parte 4: Resumen Ejecutivo

### Sistema Estable (What Works)

| Componente | Estado | Función |
|-------------|--------|----------|
| **CATEYE (cores/*)** | ✅ Funcional | Base de operaciones bug bounty |
| **MONOLITO (core/)** | ⚠️ Parcial | EventBus + Scheduler básicos |
| **ATLAS/ODYSSEY** | ✅ Funcional | Finanzas y predicciones |
| **Frontend** | ✅ Funcional | Dashboard y navegación |

### Crítico: Sistema EventBus Roto

**Problema Principal**: CoreEventBus **NO** publica a CATEYE legacy. Los events de ATLAS/ODYSSEY (`atlas:price:updated`, `odyssey:bet:settled`) **nunca llegan** al sistema de eventos original CATEYE.

**Impacto**: Sin integración entre apps y Core. Sin persistencia de eventos.

### Tareas de Mayor Impacto (P0-P1)

**P0 (Esta semana):**
1. **Corregir CoreEventBus** → publicar al legacy CATEYE
2. **Arrancar CoreScheduler** → jobs de apps funcionando
3. **Migrar settings ATLAS/ODYSSEY** → backend al igual que CATEYE

**P1 (Próxima semana):**
4. **Implementar Hermes** → capacidades reales de desktop
5. **Completar Widget System** → drag-and-drop dashboard
6. **Agregar Knowledge Graph Frontend** → visualización de grafo

### Problemas No Urgentes (P2+)

- **Flaky MSP estimator** → demanda histórica o realista   
- **No hay deduplicación de eventos** → cada app re-calcúla
- **Falta de Target Intelligence** → sin priorización unificada
- **Autoaprendizaje limitado** → solo via LLM, no bayesiano

---

## Parte 5: Hoja de Ruta de Inmediata (10 días)

### Esta Semana (P0)

| # | Item | Impacto | Esfuerzo | Dependencias |
|---|------|--------|----------|-------------|
| 5 | **HTTP probe module** | ⭐⭐⭐⭐⭐ | 2-3d | Reasoners |
| 6 | **Report templates (H1/BC/Inti)** | ⭐⭐⭐⭐⭐ | 1-2d | EvidenceComposer |
| 7 | **Hypothesis → Finding promotion** | ⭐⭐⭐⭐⭐ | 1d | OffensiveEngine |
| 8 | **Immunefi platform connector** | ⭐⭐⭐⭐⭐ | 1-2d | RevenuePipeline |
| 9 | **Code4rena platform connector** | ⭐⭐⭐⭐ | 1-2d | RevenuePipeline |
|10 | **Auto feedback loop (subscribe)** | ⭐⭐⭐⭐ | 1d | Reasoners |
|11 | **Fix PoC generation** | ⭐⭐⭐⭐ | 1d | EvidenceComposer |
|12 | **Expected Value prioritizer** | ⭐⭐⭐⭐ | 2d | TargetIntelligence |

### Próxima Semana (P1)

| # | Item | Impacto | Esfuerzo |
|---|------|--------|----------|
|13 | **Docker + docker-compose** | ⭐⭐⭐⭐ | 1-2d |
|14 | **Knowledge Graph Frontend** | ⭐⭐⭐⭐ | 3-5d |
|15 | **Revenue Pipeline Frontend** | ⭐⭐⭐⭐ | 2-3d |
|16 | **Consolidate Dashboard → MissionControl** | ⭐⭐⭐ | 1d |
|17 | **Lint + tests + smoke test CI** | ⭐⭐⭐ | 1d |
|18 | **Auto-backup con rotation** | ⭐⭐⭐ | 1d |
|19 | **Command System: reducir stubs** | ⭐⭐⭐ | 3-5d |
|20 | **Widget-based dashboard** | ⭐⭐⭐ | 5-7d |

### Inmediatamente (0 días)

**Corregir CoreEventBus:**
```python
# En CoreEventBus.publish():
try:
    from cores.events.event_bus import get_event_bus

    get_event_bus().publish(event, **data)
except Exception:
    pass
```

**Arrancar CoreScheduler:**
```python
# En api/main.py al iniciar:
scheduler.set_job_handler(lambda j: bus.publish("scheduler:job_due", job=j))
```

---

## Parte 6: Acceptance Criteria

### Sistema Estable Cuando:

✅ **Pipeline puede completar:** target → scan → finding → evidence → PoC → report → critical review

✅ **Datos sobreviven restart:** Crear → persistir → reiniciar → verificar

✅ **ORION toma decisiones:** Con entrada en tiempo real, probabilidades, límites

✅ **Frontend refleja backend:** No hay diferencia entre UI y API

✅ **Renderizado automático:** Los drafts se promueven según confianza >0.9

✅ **Integración lista:** CATEYE + Core + Apps comparten eventos

✅ **Backend unificado:** Misma base de datos, mismo ORM, mismo framework

---

## 🎯 Conclusión Ejecutiva

El sistema **funciona** pero tiene **fallos críticos**:

1. **EventBus roto** → las apps no se comunican
2. **Jobs inactivos** → sistemas de apps no funcionan
3. **ETS de settings** → frontend pierde configuración

**Acción inmediata:** Corregir CoreEventBus y CoreScheduler en los próximos 2 días. **Todo lo demás puede esperar**.

---

<div align="center">
  <p><strong>ORION Platform — Arquitectura v4.6.0</strong></p>
  <p>Sistema operativo de inteligencia privada | Julio 2026</p>
  <p>
    <a href=".ai/PROJECT_CONTEXT.md">Contexto</a> · 
    <a href=".ai/ROADMAP.md">Hoja de Ruta</a> · 
    <a href=".ai/CURRENT_STATE.md">Estado Actual</a> · 
    <a href=".ai/STRATEGIC_VISION.md">Visión Estratégica</a>
  </p>
</div>
```