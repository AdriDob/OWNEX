# OWNEX Architecture

> Maximizar ingresos verificables mediante automatización progresiva del trabajo digital.

## Identity

OWNEX no es una aplicación. Es un **sistema operativo personal de generación de ingresos**. Las plataformas (HackerOne, Upwork, Freelancer.com, etc.) son simplemente "drivers" o "fuentes de trabajo" intercambiables. El sistema permanece; las plataformas cambian.

**Regla fundamental**: Nunca depender de un solo tipo de trabajo.

**Objetivo del proyecto**: Maximizar ingresos verificables mediante automatización progresiva del trabajo digital.

---

## Las 4 Capas del Sistema

```
Internet
      │
      ▼
┌─────────────────────────────────────────────────────┐
│                    EXPLORER                          │
│  Busca oportunidades.                                │
│  GitHub issues, bug bounty programs, freelancing,   │
│  crypto opportunities, AI work tasks, new platforms │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                   EVALUATOR                          │
│  Puntúa riesgo, dinero, tiempo, probabilidad.       │
│  Output: "Estas son las 5 mejores para hoy."        │
│  Score: $ esperado × (1 - dificultad) × prob.       │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                    OPERATOR                          │
│  Realiza el trabajo.                                 │
│  Recon → Explotación → Validación → Reporte →       │
│  Envío → Cobro (por ciclo)                          │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                KNOWLEDGE ENGINE                      │
│  Extrae conocimiento permanente.                     │
│  Patrones, qué funcionó, qué no, cómo mejorar.      │
│  Alimenta al Evaluator para la próxima iteración.   │
└─────────────────────────────────────────────────────┘
```

---

## Los 3 Motores Centrales

### 📈 Opportunity Score Engine

No mostrar 1000 oportunidades. Mostrar:

> "Estas son las 5 mejores para vos hoy."

Score basado en:
- dinero esperado
- dificultad
- tiempo requerido
- probabilidad de aceptación
- competencia estimada
- experiencia previa en tipo similar
- historial propio (acceptance rate, velocidad, USD/h)

### 🧠 Personal Learning Engine

Cada trabajo deja información:

```
Encontramos un IDOR → Se aceptó → ¿Qué patrones tenía? → Guardar conocimiento.
```

Esto alimenta todos los ciclos:
- Rastro aprende qué findings se aceptan más
- Forge aprende qué tipo de bounties paga mejor
- Pulse aprende qué tareas pagan más USD/h
- Vault aprende qué inversiones funcionan

### 📊 Executive Dashboard

No técnico. Tipo CEO:

```
Hoy
Ingresos potenciales    $430
Trabajo encontrado      18
Alta prioridad          5
Automatizado            87%
Tiempo humano requerido 52 min
```

---

## Work Cycles

Cada Work Cycle implementa las 4 capas. Pero **solo un ciclo se consolida completamente antes de expandir al siguiente**.

### 🔵 Rastro — Security (Bug Bounty)
- **Estado**: ✅ En consolidación (ciclo primario)
- **Backend**: Core CATEYE existente
- **Plataformas**: HackerOne, Bugcrowd, Intigriti, YesWeHack, Immunefi
- **Pipeline**: Recon → Hipótesis → Validación → Reporte → Envío → Pago
- **Automatización**: Alta (recon automático, priorización por EV, reportes automáticos)
- **Prioridad**: CERRAR el ciclo completo antes de tocar otros ciclos

### 🟣 Forge — Dev Bounty
- **Estado**: 📝 Diseño (pospuesto hasta que Rastro esté sólido)

### 🟢 Pulse — AI Work
- **Estado**: 📝 Diseño (pospuesto)

### 🟡 Vault — Wealth
- **Estado**: ⚠️ Parcial (se expande junto con Rastro cuando afecte al pipeline de ingresos)

### ⚪ Atlas — Intelligence
- **Estado**: 📝 Diseño (se construye después de los ciclos productivos)

### 🤖 Orion — Coordinator
- **Estado**: ✅ Existe (orquestación base funcional)

---

## Estrategia de Expansión

```
FASE 0: OWNEX Branding + UX/UI       ← ESTAMOS AQUÍ
FASE 1: Opportunity Score Engine      ← SIGUIENTE
FASE 2: Knowledge Engine              ← Knowledge Engine
FASE 3: Cerrar Rastro (Security) E2E  ← Un ciclo completo
FASE 4: Forge Adapter                 ← Siguiente ciclo
FASE 5: Pulse Adapter                 ← Siguiente ciclo
FASE 6: Memoria Semántica             ← Entre ciclos
FASE 7: Multiagentes                  ← Cuando todos los ciclos funcionen
```

No expandir hasta que el ciclo anterior esté consolidado y midiendo resultados reales.

---

## Execution Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        OWNEX                                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                EXPLORER                                │   │
│  │  Oportunity Radar · Crawlers · Platform Discoverers   │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │                EVALUATOR                              │   │
│  │  Opportunity Score · Risk/Difficulty/Time/Prob.      │   │
│  │  Output: top 5 oportunidades para hoy                │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │                OPERATOR                               │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐   │   │
│  │  │Rastro│ │ Forge│ │ Pulse│ │ Vault│ │  Atlas   │   │   │
│  │  └──┬───┘ └──────┘ └──────┘ └──┬───┘ └──────────┘   │   │
│  └──────┼──────────────────────────┼────────────────────┘   │
│         │                          │                        │
│  ┌──────▼──────────────────────────▼────────────────────┐   │
│  │                KNOWLEDGE ENGINE                       │   │
│  │  Patrones · Aprendizaje · Feedback · Mejora continua  │   │
│  │  Alimenta al Evaluator y al Explorer                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────┐  ┌──────────┐  ┌───────────────────────┐  │
│  │   Orion      │  │Scheduler │  │  Executive Dashboard   │  │
│  │  Coordinator │  │ Runtime  │  │  (CEO view, no técnico)│  │
│  └──────────────┘  └──────────┘  └───────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          Shared Infrastructure                        │   │
│  │  Auth │ IdentityVault │ Memory │ KG │ Health │ Platform│  │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Shared Infrastructure (ya existe)

| Component | Status | Description |
|-----------|--------|-------------|
| EventBus | ✅ | Comunicación entre capas |
| Scheduler | ✅ | Ejecución de tareas planificadas |
| Execution Runtime | ✅ | Pipeline worker engine |
| Copilot | ✅ | Asistente IA, decisiones, planificación |
| Knowledge Graph | ✅ | Memoria relacional del sistema |
| Unified Memory | ✅ | Memoria persistente con namespaces |
| Health Center | ✅ | Monitoreo de salud del sistema |
| IdentityVault | ✅ | Bóveda de credenciales (AES-256-GCM) |
| Integration Center | ✅ | Registry de 23 integraciones |
| Secrets Manager | ✅ | Gestión de API keys |

---

## Integration Model

Cada plataforma externa se integra como un **Platform Adapter**:

```python
class PlatformAdapter:
    """Base class for all platform integrations"""
    
    cycle: WorkCycle       # Which cycle this belongs to
    platform_id: str       # Unique identifier
    name: str              # Display name
    
    async def discover_tasks(self) -> list[Task]
    async def evaluate_task(self, task: Task) -> Score
    async def submit_work(self, task: Task, result: Any) -> SubmissionResult
    async def check_status(self, submission_id: str) -> Status
    async def verify_payment(self, submission_id: str) -> PaymentInfo
```

---

## Color System

```
OWNEX Palette:
  Background:  #050505 (near-black)
  Surface:     #0a0a0f (slightly lighter)
  Border:      #1a1a2e (subtle blue-black)
  Primary:     #3b82f6 (blue accent)
  Text:        #f0f0f0 (off-white)
  Muted:       #6b7280 (gray)
  Gold:        #f59e0b (highlights)
  
Status colors (only for indicators):
  Success:     #22c55e (green)
  Warning:     #f59e0b (amber)
  Error:       #ef4444 (red)
```

---

## Naming

| Concept | OWNEX Name | Legacy Name |
|---------|-----------|-------------|
| Ecosistema | OWNEX | ORION Platform |
| Bug Bounty | Rastro | CATEYE |
| Dashboard central | Mission Control | Mission Control |
| Asistente | Orion | COPILOT |
| Configuración | Settings | Operations |
| Ciclo de trabajo | Work Cycle | Section |
| Seguridad | Security | — |
| Dev Bounty | Forge | — |
| AI Work | Pulse | — |
| Wealth | Vault | Capital |
| Inteligencia | Atlas | Intelligence |
| Jobs | — | — |

---

## Plataformas investigadas — resumen

### Dev Bounty — Top 3
1. **Superteam Earn** (8.6) — API para agentes, $30K+ disponible
2. **TaskBounty** (8.2) — API-first, construido para IA agents
3. **Opire** (7.8) — API pública sin auth

### AI Work — Top 3
1. **Outlier** (6.2) — coding global, sin entrevista
2. **DataAnnotation** (6.6) — $40-65/hr, US/UK/AU/CA
3. **Mindrift** (6.6) — $32-90/hr code eval, global

### Wealth — Top 3
1. **CoinGecko** (9.6) — ya integrado
2. **Firefly III** (9.0) — self-hosted, REST API
3. **Zerion** (8.4) — crypto multi-chain portfolio

### Jobs — Integraciones aprobadas
1. **Freelancer.com** — concurso + API REST pública
2. **LinkedIn** — solo Services Marketplace / job discovery (sin API pública)

---

## Prioridades

1. ✅ OWNEX Branding + UX/UI
2. ⬜ Opportunity Score Engine
3. ⬜ Knowledge Engine
4. ⬜ Cerrar Rastro E2E (ciclo completo)
5. ⬜ Forge Adapter
6. ⬜ Pulse Adapter
7. ⬜ Memoria Semántica entre ciclos
8. ⬜ Multiagentes

Consolidar antes de expandir. Un ciclo funcionando perfectamente > 5 ciclos a medias.
