# ORION Platform — Arquitectura Definitiva (RFC-001)

> **Estado**: Aprobado  
> **Versión**: 4.0.0-dev  
> **Fecha**: Julio 2026  
> **Autor**: OpenCode (auditoría arquitectónica)

---

## 0. Resumen Ejecutivo

ORION Platform es un **monolito modular** que aloja aplicaciones independientes
(CATEYE, ATLAS, ODYSSEY, y futuras) en un solo proceso Python + Vue 3.

**Fortalezas actuales:**
- Apps con DB, API, schemas, y schedulers propios
- Zero imports cruzados entre apps
- Namespace de eventos por app
- Interfaces abstractas en `core/interfaces/`
- CATEYE intacto — envuelto, no modificado

**Debilidades críticas detectadas (arreglar antes de seguir):**
1. CoreScheduler no ejecuta jobs — `_on_job_due` nunca se setea
2. CoreEventBus no persiste eventos ni se conecta al EventBus legacy
3. No existe ciclo de vida de apps (start/stop/enable/disable)
4. Frontend: todas las rutas de ATLAS/ODYSSEY apuntan al Dashboard — las sub-vistas no existen
5. Sin contratos de comunicación inter-app
6. CATEYE no está integrado via manifest — sus routers siguen hardcodeados en `api/main.py`
7. Hermes no existe
8. Sin tests de integración ORION

**Riesgo a 1-2 años:** El lifespan en `api/main.py` creció a 50+ steps envueltos en `try/except` — un fallo silencioso no detectado puede degradar el sistema sin que el usuario lo sepa.

---

## 1. Stack Definitivo

| Capa | Tecnología | Justificación |
|---|---|---|
| Lenguaje | Python 3.10+ | El ecosistema bug bounty es Python |
| Framework API | FastAPI | Unificado con CATEYE |
| Base de datos | SQLite (dev) / PostgreSQL (prod) | Misma estrategia que CATEYE |
| ORM | SQLAlchemy 2.0 | Unificado con CATEYE |
| Frontend | Vue 3 + TypeScript + Tailwind v4 | Unificado con CATEYE |
| Build | Vite + PyInstaller + NSIS | Unificado con CATEYE |
| Testing | pytest + vitest | Unificado con CATEYE |
| Linting | Ruff (Python) + Biome (frontend) | Unificado con CATEYE |

**Decisiones descartadas:**
- ❌ Microservicios — complejidad innecesaria para 1-3 developers
- ❌ RabbitMQ / Kafka — EventBus in-process es suficiente
- ❌ Redis — una dependencia más que no aporta vs SQLite
- ❌ Kubernetes / Docker Compose — overhead sin beneficio para desktop app
- ❌ gRPC — HTTP/REST es más simple y debuggeable
- ❌ WebAssembly plugins — no hay caso de uso real
- ❌ CQRS / Event Sourcing — sobreingeniería para el volumen actual

---

## 2. Filosofía Arquitectónica

### Modular Monolith + Event-Driven

```
┌─────────────────────────────────────────────────┐
│                  FastAPI App                     │
│                                                   │
│  ┌──────────────┐  ┌──────────┐  ┌──────────┐   │
│  │    CATEYE     │  │  ATLAS   │  │ ODYSSEY  │   │
│  │  (envuelto)   │  │ (plugin) │  │ (plugin) │   │
│  └──────┬───────┘  └────┬─────┘  └────┬─────┘   │
│         │               │             │          │
│  ┌──────┴───────────────┴─────────────┴──────┐   │
│  │              ORION Core                    │   │
│  │  Registry │ EventBus │ Scheduler │ AI      │   │
│  │  DB Mgr   │ Normalizer │ Simulation        │   │
│  │  Decision Journal │ Storage                 │   │
│  └─────────────────────────────────────────────┘   │
│                                                   │
│  ┌─────────────────────────────────────────────┐   │
│  │          Shared Middleware                    │   │
│  │  Auth │ CSRF │ RateLimit │ Security Hdrs    │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Principios de ingeniería (obligatorios)

1. **Nunca importes código de otra app.** Cero imports cruzados entre `apps/*/`.
2. **Comunicación solo via EventBus o Core API.** Apps no se llaman directo.
3. **Cada app es dueña de su DB.** No compartir tablas entre apps.
4. **Core no conoce detalles de apps.** Solo interfaces y eventos.
5. **Toda integración externa es opcional.** El sistema funciona sin APIs de terceros.
6. **CATEYE no se modifica.** Solo se envuelve. Los 393 tests deben seguir pasando.
7. **Un solo proceso.** No microservicios. No hilos separados.
8. **Persistencia en SQLite.** No Redis, no memoria volátil para estado crítico.

---

## 3. Auditoría de 30 Puntos

### 3.1 Arquitectura completa — FORTALEZA
El patrón de monolito modular con EventBus es correcto para el tamaño del proyecto.
CATEYE quedó bien envuelto. Las apps tienen buena separación.

**Riesgo**: El CoreEventBus y el EventBus legacy de CATEYE coexisten sin bridging.
Si un evento `atlas:price:updated` necesita que CATEYE reaccione, no llega.
**Fix**: Conectar CoreEventBus.publish → legacy EventBus.publish mediante un bridge.

### 3.2 Core — DÉBIL
**Problemas detectados:**
- `CoreScheduler.set_job_handler()` nunca es llamado → los jobs registrados NO se ejecutan
- `CoreEventBus` no tiene persistencia (CATEYE sí persiste a SQLite)
- `AIRuntime` está creado pero nunca se registran agentes (agent_class=None en todos los manifests)
- El `DatabaseManager` no tiene `_ensure_core_db()` llamado en startup

### 3.3 Separación de responsabilidades — CORRECTO
Cada app tiene su `manifest.py`, sus modelos, su API, sus connectors, sus engines.
No hay imports cruzados entre `apps/atlas/` y `apps/odyssey/`.

### 3.4 Límites entre apps — CORRECTO
El límite DB + API + EventBus es suficiente. Cada app opera en su propio namespace.

### 3.5 Contratos entre módulos — DÉBIL
**Core interfaces** están bien definidas (`IConnector`, `IEventBus`, etc.).
Pero **no existe un contrato de eventos** — qué eventos publica cada app y quién los consume.
**Fix**: Crear `EVENT_CONTRACTS.md` con event catalog.

### 3.6 Escalabilidad — ADECUADO
Un solo proceso Python escala hasta ~500 conexiones concurrentes. Suficiente para uso individual.
Si se necesita multi-usuario, ahí sí habría que repensar (pero está fuera del scope).

### 3.7 Mantenibilidad — MEDIO
**Problema**: `api/main.py` tiene 818 líneas con 50+ init steps. Es frágil.
**Fix**: Delegar init a cada módulo via hooks. Core llama `app.on_startup()`.

### 3.8 Riesgo de monolito — BAJO
El modular monolith es intencional y controlado. Mientras se respeten los límites
(sin imports cruzados, eventos como única comunicación), no hay riesgo real.

### 3.9 Organización de carpetas — CORRECTA

```
orion/
├── core/         → infra compartida (interfaces, event bus, scheduler, db, normalizer, sim)
├── apps/
│   ├── cateye/   → wrapper de CATEYE (solo manifest.py)
│   ├── atlas/    → inversiones
│   └── odyssey/  → betting analytics
├── api/          → FastAPI app + routers legacy de CATEYE
├── cores/        → CATEYE legacy (NO TOCAR)
├── frontend/
│   ├── src/
│   │   ├── apps/ → frontend de cada app
│   │   ├── shell/→ ORION shell (sidebar, home)
│   │   ├── components/layout/  → AppSidebar (modificado)
│   │   ├── stores/ → notifications (extendido)
│   │   └── router/ → 35+ rutas CATEYE + 12 ORION
└── .ai/          → single source of truth
```

### 3.10 Sistema de plugins — BÁSICO
`AppRegistry.discover()` escanea `apps/*/manifest.py` y registra automáticamente.
**Falta**: lifecycle hooks (`on_enable`, `on_disable`, `on_startup`, `on_shutdown`).
**Falta**: hot-reload de apps (no crítico ahora).

### 3.11 Sistema de Providers — CORRECTO
Cada app lista sus providers en `providers.py`. El manifest los expone.
**Falta**: Un Integration Center en la UI que muestre estado (✓ configurado / ⚪ no configurado).

### 3.12 AI Runtime — SHELL
El `AIRuntime` existe pero `agent_class=None` en todos los manifests.
**Fix**: Implementar los agentes reales una vez que la arquitectura esté cerrada.

### 3.13 Sistema de agentes — SHELL
`AtlasInvestorAgent` y `OdysseyBettingAgent` son placeholders vacíos.
`IAgent` interface está bien definida. Pendiente implementación real.

### 3.14 Dashboard — MEDIO
`OrionHome.vue` con widgets dinámicos funciona. Carga apps desde `/api/core/apps`.
**Problema**: Si el backend no responde, el shell se queda en skeleton loading sin mensaje claro.

### 3.15 EventBus — PROBLEMA CRÍTICO
**CoreEventBus** (nuevo):
- No persiste eventos (CATEYE sí — SQLite)
- No tiene history real (`_recent` es lista en memoria de clase)
- No publica al EventBus legacy de CATEYE
- `subscribe_app()` funciona pero apps legacy no lo usan

**Fix:**
1. CoreEventBus debe delegar `publish()` también al EventBus legacy
2. Persistir eventos core en `orion.db`
3. Bridge bidireccional core ↔ legacy

### 3.16 Scheduler — PROBLEMA CRÍTICO
`CoreScheduler`:
- `_on_job_due` nunca se setea → jobs registrados NUNCA se ejecutan
- En `api/main.py` línea 367-382 se registran apps y DBs, pero los jobs nunca se asignan al scheduler

**Fix:**
```python
scheduler = get_core_scheduler()
scheduler.set_job_handler(lambda job: bus.publish("scheduler:job_due", job=job))
for job in registry.get_scheduler_jobs():
    scheduler.add_job(job)
await scheduler.start()
```

### 3.17 Base de datos — CORRECTO
Multi-SQLite con un engine por app. Pragmas WAL, foreign_keys, busy_timeout.
**Falta**: Backup centralizado de todas las DBs. Migraciones con Alembic.

### 3.18 Memoria — NO IMPLEMENTADO
`core/ai/runtime.py` tiene `AgentContext` pero no hay memoria persistente.
El sistema legacy de CATEYE sí tiene memoria `(cores/memory/)`.
**Fix**: Core debería exponer `IMemory` interface para que apps la usen.

### 3.19 Configuración — DISPERSO
CATEYE usa env vars + `cores/env/config.py`. ORION apps no tienen config propia.
**Fix**: Cada app debería tener `config.py` con defaults, validación y schema.

### 3.20 Seguridad — CORRECTO
Auth, CSRF, rate limiting, security headers — todo compartido via middleware.
Apps heredan la seguridad de CATEYE automáticamente.

### 3.21 Sincronización — NO IMPLEMENTADO
No hay mecanismo para que apps sincronicen estado compartido.
Si CATEYE paga un bounty, ATLAS debería saberlo.
**Fix**: Eventos cross-app publicados en EventBus.

### 3.22 Backups — PARCIAL
CATEYE tiene `python run.py --backup`. ORION apps no están incluidas.
**Fix**: Backup debe incluir `atlas.db` y `odyssey.db`.

### 3.23 Migraciones — PARCIAL
`DatabaseManager.run_migrations()` crea tablas via `metadata.create_all()`.
**Riesgo**: En producción, `create_all` es inseguro (no altera tablas existentes).
Para la fase actual (SQLite + schema estable) es aceptable.

### 3.24 Installer — IDÉNTICO
Se usa el mismo PyInstaller + NSIS que CATEYE. No hay cambios necesarios.
Ver `scripts/build_windows.ps1`.

### 3.25 Desktop — IDÉNTICO
Se usa pywebview igual que CATEYE. No hay cambios necesarios.

### 3.26 Estrategia de releases — SUGERENCIA
```
v3.0.x — CATEYE standalone (bug fixes only)
v4.0.0 — ORION Platform (current)
  - Core stabilizado
  - ATLAS beta, ODYSSEY beta
v4.6.0 — Agentes reales + Hermes
v4.2.0 — Integration Center UI + feedback loop
```

### 3.27 Estrategia de testing — DÉBIL
17 tests vs 393 de CATEYE.
**Mínimo requerido antes de v4.0.0:**
- [ ] EventBus bridge test (core ↔ legacy)
- [ ] Scheduler job execution test
- [ ] App lifecycle test (discover → register → mount)
- [ ] Cross-app event delivery test
- [ ] Database manager isolation test

### 3.28 Estrategia de documentación — DISPERSA
`.ai/` está bien, pero no hay docs de API para apps ORION.
**Fix**: Swagger ya expone `/docs` con los routers montados. Suficiente.

### 3.29 Estrategia de crecimiento 5 años — ANÁLISIS

**Escenario positivo:** 5-6 apps en el mismo proceso. Se mantiene modular.
**Límite:** ~10 apps antes de que el startup sea lento (>10s).
**Si supera ese límite:** Extraer apps como procesos separados con EventBus remoto.
Pero no antes.

### 3.30 Lo que no preguntaste pero importa

**1. pyproject.toml aún se llama "cateye":**
```toml
name = "cateye"
```
Debería ser `orion-platform` o similar.

**2. No hay versión de core:**
`core/__init__.py` dice `4.0.0-dev` pero no hay forma de verificar compatibilidad
entre core y apps.

**3. Dos EventBus = dos verdades:**
El legacy EventBus persiste eventos con clasificación por prioridad.
El CoreEventBus no persiste nada. Cuando alguien pregunta "qué pasó",
hay que revisar dos buses.

**4. CATEYE manifest es decorativo:**
`apps/cateye/manifest.py` tiene `routers=[]`, `scheduler_jobs=[]`.
No integra CATEYE al sistema de plugins — solo existe para que el AppRegistry
lo muestre en la UI. Los 50+ routers de CATEYE siguen hardcodeados en `api/main.py`.

---

## 4. Problemas a 1-2 Años

| # | Problema | Riesgo | Cuándo duele |
|---|---|---|---|
| 1 | Scheduler no ejecuta jobs | 🔴 Alto | Ahora — los jobs registrados no corren |
| 2 | CoreEventBus no persiste | 🔴 Alto | Primer reinicio — se pierde history de apps |
| 3 | CoreEventBus no bridgea al legacy | 🟡 Medio | Cuando apps necesiten interoperar |
| 4 | Sin lifecycle hooks | 🟡 Medio | Al agregar la 4ta app |
| 5 | Frontend sub-vistas no existen | 🟡 Medio | Al navegar a /atlas/portfolio |
| 6 | AIRuntime sin agentes | 🟡 Medio | Cuando quieras agentes reales |
| 7 | Sin Integration Center | 🟢 Bajo | Molestia diaria del usuario |
| 8 | lifespan monolítico (818 líneas) | 🟡 Medio | Primer bug de init |
| 9 | pyproject.toml dice "cateye" | 🟢 Bajo | Confusión en builds |
| 10 | Sin memoria core para apps | 🟢 Bajo | Cuando ATLAS quiera recordar |

---

## 5. Decisiones Finales

### Arquitectura
✅ **Monolito modular** — la opción correcta para el tamaño del proyecto.
✅ **EventBus in-process** — sin dependencias externas.
✅ **SQLite por app** — simple, aislado, backup facil.
✅ **FastAPI + Vue 3** — unificado con CATEYE.

### Nombre del multisistema
**ORION Platform**.

ORION ya es el nombre del core. Es el sistema operativo que coordina CATEYE,
ATLAS, ODYSSEY, y futuras apps. Tiene sentido mantenerlo como nombre umbrella.

Justificación:
- Ya existe en el código como `orion.core`, `orion.shell`, etc.
- No compite con CATEYE (bug bounty), ATLAS (inversiones), ODYSSEY (apuestas)
- Es neutral — funciona como plataforma sin sesgo hacia ninguna app
- La metáfora "ORION = constelación = plataforma que agrupa sistemas" funciona

### CATEYE
✅ Congelado. Solo fixes de seguridad y bugs. No más features.

### ATLAS
✅ Puede crecer. Pendiente: agentes reales, Integration Center, sub-vistas.

### ODYSSEY
✅ Puede crecer. Pendiente: agentes reales, Integration Center, sub-vistas.

### Hermes
⏳ Pendiente. Agente transversal para automatización local.
No implementar hasta que ORION Core esté estable.

---

## 6. Roadmap Técnico

### Ahora — Hotfixes críticos (1-2 días)
1. Conectar `CoreScheduler.set_job_handler()` → los jobs se ejecutan
2. Bridge CoreEventBus → legacy EventBus
3. Persistir eventos core en `orion.db`
4. Frontend: sub-vistas reales para ATLAS (PortfolioView, etc.)
5. Frontend: sub-vistas reales para ODYSSEY (BankrollView, etc.)

### Semana 1-2 — Estabilización
6. App lifecycle hooks en `IAppPlugin`
7. Integration Center UI
8. Tests de integración ORION
9. Backup multi-DB
10. Hermes v1 (solo comandos básicos del sistema)

### Semana 3-4 — Agentes
11. AtlasInvestorAgent real
12. OdysseyBettingAgent real
13. Feedback loop agente → Decision Journal → Reward

### Mes 2 — Maduración
14. Memoria persistente para apps
15. Event catalog documentado
16. Health unified (eliminar los 3 sistemas legacy)

---

## 7. Checklist de Validación

Pre-flight para considerar ORION Platform "terminada":

- [ ] CoreScheduler ejecuta jobs de todas las apps
- [ ] EventBus core → legacy bridge funcional
- [ ] Eventos core persisten en SQLite
- [ ] AppRegistry tiene lifecycle hooks (start/stop/enable/disable)
- [ ] Sub-vistas de ATLAS/ODYSSEY existen en frontend
- [ ] Hermes v1 responde comandos
- [ ] Integration Center UI muestra estado de cada provider
- [ ] 30+ tests de integración ORION
- [ ] `python run.py --backup` incluye DBs de apps
- [ ] `pyproject.toml` actualizado a `orion-platform`
- [ ] 393 tests de CATEYE siguen pasando
- [ ] Ruff clean
- [ ] vite build sin errores

---

## 8. Reglas Obligatorias (para pegar en AGENTS.md)

```
## Reglas Arquitectónicas ORION Platform

1. **CERO imports cruzados entre apps.** `apps/atlas/` no importa `apps/odyssey/`.
2. **Toda comunicación inter-app via EventBus.** No llamadas directas.
3. **Cada app tiene su propia DB.** No compartir tablas.
4. **Toda integración externa es opcional.** El sistema funciona sin APIs.
5. **Core no conoce detalles de apps.** Solo interfaces y eventos.
6. **CATEYE no se modifica.** Solo se envuelve. Tests legacy deben pasar.
7. **Un solo proceso.** No microservicios.
8. **Estado crítico siempre persiste en SQLite.** No en memoria volátil.
9. **Decision Journal es append-only.** No se editan decisiones pasadas.
10. **Simulation Engine nunca toca dinero real.** Solo what-if.
```

---

## 9. Resumen para el usuario

```
ESTADO ACTUAL:
✅ Arquitectura de ORION Platform diseñada y codificada
✅ ATLAS y ODYSSEY con connectors, engines, APIs, schedulers
✅ Frontend shell con sidebar, dashboards, settings
✅ CATEYE intacto (393 tests pasan)

⚠️ PROBLEMAS CRÍTICOS (arreglar AHORA):
1. Scheduler no ejecuta jobs registrados
2. CoreEventBus no persiste ni bridgea al legacy
3. Frontend sub-vistas no existen (todo apunta al Dashboard)

❌ PENDIENTE:
4. Hermes (agente transversal)
5. Integration Center UI
6. Agentes reales (AtlasInvestorAgent, OdysseyBettingAgent)
7. Tests de integración ORION
8. Backup multi-DB

📛 NOMBRE: ORION Platform
   ├── ORION = plataforma / sistema operativo
   ├── CATEYE = hunter (bug bounty)
   ├── ATLAS = gestor patrimonial
   ├── ODYSSEY = laboratorio de riesgo
   └── Hermes = agente transversal
```
