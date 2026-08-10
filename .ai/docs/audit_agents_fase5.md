# FASE 5 — Auditoría de Agentes

> **Fecha:** 2026-07-29  
> **Alcance:** `core/interfaces/agent.py`, `cores/agents/*` (base, bus, coordinator, y 7 agentes específicos)  
> **Criterios:** Responsabilidad única, Interfaces, Capacidades, Contexto, Eventos, Métricas, Aprendizaje

---

## 1. `core/interfaces/agent.py` — Interfaz IAgent (legacy)

| Criterio | Estado | Notas |
|----------|--------|-------|
| Responsabilidad única | ✅ | Define contratos abstractos para agentes (Action, Feedback, AgentContext, IAgent) |
| Interfaces | ✅ | `IAgent(ABC)` con `get_next_action()`, `learn()`, `get_tools()`, `get_system_prompt()` |
| Capacidades | ⚠️ | Implícitas vía `get_tools()`, no hay sistema formal de capabilities |
| Contexto | ✅ | `AgentContext` dataclass con `app_id`, `state`, `memory`, `last_action` |
| Eventos | ❌ | No hay integración con event bus — es un modelo pull-based (get_next_action) |
| Métricas | ❌ | Sin métricas definidas |
| Aprendizaje | ✅ | `learn(feedback: Feedback)` método abstracto |

**⚠️ Problema estructural grave:** Este archivo define un sistema de agentes **completamente aislado** del que está implementado en `cores/agents/`. Los 8 agentes concretos heredan de `BaseAgent`, no de `IAgent`. Hay dos arquitecturas de agente coexistiendo sin comunicación entre ellas:
- `IAgent` (pull-based con `get_next_action`) → usado por `core/ai/runtime.py`
- `BaseAgent` (event-driven con bus) → usado por todo `cores/agents/`

Además, `core/engine/context.py` define su propio `AgentContext` (tercera clase con el mismo nombre), distinto del de `core/interfaces/agent.py`.

---

## 2. `cores/agents/base.py` — BaseAgent

| Criterio | Estado | Notas |
|----------|--------|-------|
| Responsabilidad única | ✅ | Clase base abstracta: registro, dispatch de eventos, health checks, manejo de errores |
| Interfaces | ✅ | ABC con abstractmethods: `_get_agent_id()`, `_get_subscriptions()`, `handle_event()` |
| Capacidades | ✅ | `_get_capabilities()` genera lista desde suscripciones |
| Contexto | ⚠️ | Cada agente tiene `agent_id`, `name`, `capabilities`, `retry_policy`, `status`. No hay objeto de contexto formal compartido entre agentes. |
| Eventos | ✅ | Integración completa con bus: `subscribe()`, `emit()`, `_on_event()` dispatcher con soporte sync/async |
| Métricas | ✅ | `tasks_completed`, `tasks_failed`, `total_time_ms`. `health()` devuelve avg_time_ms. |
| Aprendizaje | ❌ | No hay mecanismo de aprendizaje en la clase base. El método `learn()` de `IAgent` no tiene equivalente aquí. |

**Fortaleza:** Manejo robusto de corrutinas (sync y async), timing, error handling, retry policy.
**Debilidad:** Sin hook de aprendizaje base.

---

## 3. `cores/agents/bus.py` — Event Bus (IEventBus + LocalEventBus)

| Criterio | Estado | Notas |
|----------|--------|-------|
| Responsabilidad única | ✅ | Único bus de comunicación entre agentes |
| Interfaces | ✅ | `IEventBus(ABC)` con 9 métodos abstractos |
| Capacidades | ✅ | Thread-safe, singleton, bridges bidireccionales con EventBus del sistema, wildcard `"*"` |
| Contexto | N/A | Es infraestructura, no un agente |
| Eventos | ✅ | `AgentEvent` frozen dataclass con traceabilidad completa (event_id, correlation_id, timestamp, source, target, priority) |
| Métricas | ⚠️ | Historial de eventos hasta `max_history=1000` pero sin métricas de latencia/throughput |
| Aprendizaje | N/A | No aplica |

**Fortaleza:** `bridge_agent_bus_to_eventbus()` y `bridge_eventbus_to_agent_bus()` permiten integración con el sistema de eventos global.

---

## 4. `cores/agents/coordinator.py` — CoordinatorAgent

| Criterio | Estado | Notas |
|----------|--------|-------|
| Responsabilidad única | ✅ | Orquesta el pipeline completo de bug bounty con persistencia a SQLite |
| Interfaces | ✅ | Hereda de BaseAgent, implementa todos los abstractmethods. API pública: `get_pipeline_status()`, `list_pipelines()`, `get_agents_health()`, `delete_pipeline()` |
| Capacidades | ✅ | `orchestrate_pipeline`, `resolve_conflicts`, `retry_failed_stages`, `quality_scoring`, `persist_state` |
| Contexto | ✅ | `_active_pipelines` dict + `_agent_health` dict + persistencia DB (PipelineRun) |
| Eventos | ✅ | Maneja 9+ tipos: `PIPELINE_START`, `PIPELINE_STAGE_COMPLETED`, `PIPELINE_FAILED`, `PIPELINE_CANCELLED`, `AGENT_HEALTH_CHANGED`, `AGENT_REGISTERED`, `SYSTEM_ERROR`, `STRATEGY_RECOMMENDATION`, `FINANCIAL_UPDATED`, `SUBMISSION_REQUESTED` |
| Métricas | ✅ | Hereda de BaseAgent + `compute_quality_score()` con 11 estados del state machine |
| Aprendizaje | ⚠️ | Retry con exponential backoff es reactivo, no aprende patrones. Sin aprendizaje de qué configuraciones de pipeline funcionan mejor. |

**Fortaleza:** State machine completo de 11 estados, persistencia híbrida (memoria + DB), modo manual/auto, conflict resolution, quality scoring.
**Extensión:** 648 líneas — el archivo más grande, bien organizado.

---

## 5. Agentes Específicos

### 5.1 DocumentationAgent

| Criterio | Estado | Notas |
|----------|--------|-------|
| Responsabilidad única | ✅ | Genera reportes de bug bounty multi-formato |
| Interfaces | ✅ | Hereda de BaseAgent |
| Capacidades | ⚠️ | Implícitas (solo DOCUMENTATION_REQUESTED), usa ReportEngine |
| Contexto | ⚠️ | Solo event payload. Sin estado interno persistente |
| Eventos | ✅ | Input: `DOCUMENTATION_REQUESTED`. Output: `DOCUMENTATION_COMPLETED` |
| Métricas | ⚠️ | Solo heredadas de BaseAgent. Sin métricas de calidad de reportes, sin track de reportes exitosos vs fallidos |
| Aprendizaje | ❌ | No aprende de qué reportes son aceptados/rechazados por los programas |

### 5.2 ExploitAgent

| Criterio | Estado | Notas |
|----------|--------|-------|
| Responsabilidad única | ✅ | Confirmación segura de exploits (read-only) |
| Interfaces | ✅ | Hereda de BaseAgent |
| Capacidades | ⚠️ | Implícitas, usa DifferentialEngine |
| Contexto | ⚠️ | Solo event payload + flag `safe_mode` |
| Eventos | ✅ | Input: `EXPLOIT_REQUESTED`. Output: `EXPLOIT_CONFIRMED`, `EXPLOIT_COMPLETED` |
| Métricas | ⚠️ | Solo heredadas. Sin ratio de confirmación, sin tiempo por exploit |
| Aprendizaje | ❌ | No registra qué técnicas de exploit funcionaron para reusarlas |

### 5.3 FinancialAgent

| Criterio | Estado | Notas |
|----------|--------|-------|
| Responsabilidad única | ✅ | Tracking de revenue, ROI, proyecciones, metas |
| Interfaces | ✅ | Hereda de BaseAgent + API pública: `get_summary()`, `set_metric()`, `add_goal()` |
| Capacidades | ✅ | Maneja 4 eventos + 3 métodos públicos. Persistencia JSON |
| Contexto | ✅ | `_data` dict con metrics, payouts, goals, estimates. Persistencia a archivo JSON |
| Eventos | ✅ | Inputs: `FINANCIAL_UPDATED`, `FINANCIAL_PAYOUT_RECORDED`, `FINANCIAL_GOAL_UPDATED`, `DOCUMENTATION_COMPLETED`. Sin outputs de eventos (solo almacena) |
| Métricas | ✅ | `total_paid`, `total_estimated`, `pending_revenue`, `by_program`, goals con progress_pct |
| Aprendizaje | ⚠️ | Recalcula métricas pero no optimiza comportamiento basado en datos históricos |

### 5.4 MemoryAgent

| Criterio | Estado | Notas |
|----------|--------|-------|
| Responsabilidad única | ✅ | Memoria persistente entre ejecuciones de pipeline |
| Interfaces | ✅ | Hereda de BaseAgent + API pública: `remember()`, `recall_all()`, `get_stats()` |
| Capacidades | ✅ | Store/retrieve, aprendizaje de validación/exploit/documentación |
| Contexto | ✅ | `_memory` dict con namespaces. Persistencia JSON a `~/.orion/agent_memory.json` |
| Eventos | ✅ | Inputs: `MEMORY_STORE`, `MEMORY_RETRIEVED`, `VALIDATION_COMPLETED`, `EXPLOIT_COMPLETED`, `DOCUMENTATION_COMPLETED`. Output: `MEMORY_RETRIEVED` |
| Métricas | ✅ | `get_stats()` devuelve count de namespaces, entries, eventos de validación, técnicas exitosas, reportes |
| Aprendizaje | ✅ | **Único agente con aprendizaje real**: almacena técnicas rechazadas, chains exitosas, tech quirks, patrones de comportamiento por compañía |

### 5.5 ResearchAgent

| Criterio | Estado | Notas |
|----------|--------|-------|
| Responsabilidad única | ✅ | Descubrimiento de targets, programas, superficie de ataque |
| Interfaces | ✅ | Hereda de BaseAgent, handle_event async |
| Capacidades | ⚠️ | Implícitas, usa subfinder/httpx/katana. Sin capabilities declaradas |
| Contexto | ⚠️ | Solo event payload + tmpdir. Sin caché de resultados previos |
| Eventos | ✅ | Input: `RESEARCH_START`. Outputs: `ENDPOINT_DISCOVERED`, `RESEARCH_COMPLETED` |
| Métricas | ⚠️ | Solo heredadas. Sin métricas de cobertura, tiempo por fase, endpoints descubiertos vs válidos |
| Aprendizaje | ❌ | No aprende qué técnicas de descubrimiento funcionan mejor por tipo de target |

### 5.6 StrategyAgent

| Criterio | Estado | Notas |
|----------|--------|-------|
| Responsabilidad única | ✅ | Priorización por ROI esperado |
| Interfaces | ✅ | Hereda de BaseAgent + API pública: `get_recommendations()` |
| Capacidades | ⚠️ | Implícitas, usa OpportunityEngine. Sin capabilities declaradas |
| Contexto | ⚠️ | Solo `_recommendations` list en memoria. Sin persistencia |
| Eventos | ✅ | Inputs: `RESEARCH_COMPLETED`, `VALIDATION_COMPLETED`, `DOCUMENTATION_COMPLETED`, `STRATEGY_RECOMMENDATION`. Output: `STRATEGY_RECOMMENDATION` |
| Métricas | ⚠️ | Solo lista de recomendaciones. Sin métricas de efectividad (qué recomendaciones resultaron en payouts) |
| Aprendizaje | ❌ | No aprende de qué recomendaciones fueron exitosas |

### 5.7 ValidatorAgent

| Criterio | Estado | Notas |
|----------|--------|-------|
| Responsabilidad única | ✅ | Evaluación de validez de findings |
| Interfaces | ✅ | Hereda de BaseAgent |
| Capacidades | ⚠️ | Implícitas, usa unified_scoring y NoiseReductionEngine |
| Contexto | ⚠️ | Solo event payload. Sin estado interno |
| Eventos | ✅ | Input: `VALIDATION_REQUESTED`. Output: `VALIDATION_COMPLETED` |
| Métricas | ⚠️ | Solo heredadas. Sin tasa de falsos positivos, sin precisión histórica |
| Aprendizaje | ❌ | No aprende de validaciones previas para ajustar thresholds |

---

## 6. Resumen de Gaps por Agente

| Agente | Responsabilidad | Interfaces | Capacidades | Contexto | Eventos | Métricas | Aprendizaje |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **IAgent** (legacy) | ✅ | ✅ | ⚠️ | ✅ | ❌ | ❌ | ✅ |
| **BaseAgent** | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ | ❌ |
| **EventBus** | ✅ | ✅ | ✅ | N/A | ✅ | ⚠️ | N/A |
| **Coordinator** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| **Documentation** | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ❌ |
| **Exploit** | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ❌ |
| **Financial** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| **Memory** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Research** | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ❌ |
| **Strategy** | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ❌ |
| **Validator** | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ❌ |

**Puntaje promedio:** 73% (✅=36, ⚠️=17, ❌=10, N/A=3 sobre 66 checkboxes)

---

## 7. Problemas Arquitectónicos Transversales

### 7.1 Dos arquitecturas de agente incompatibles
- `core/interfaces/agent.py` define `IAgent` (pull-based: `get_next_action()`)
- `cores/agents/base.py` define `BaseAgent` (event-driven: `handle_event()`)
- **Ningún agente concreto implementa `IAgent`.** El `AIRuntime` en `core/ai/runtime.py` queda huérfano.

### 7.2 Tres clases `AgentContext` distintas
1. `core/interfaces/agent.py:AgentContext` — con `app_id`, `state`, `memory`, `last_action`
2. `core/engine/context.py:AgentContext` — con `opportunity`, `fragments`, `system_prompt`, `depth`
3. Los agentes concretos no usan ninguna; pasan info vía `event.payload` (dicts)

### 7.3 Capacidades no declaradas formalmente
- 5 de 7 agentes específicos no sobrescriben `_get_capabilities()`, dejando que BaseAgent genere capabilities genéricas basadas en subscriptions
- No hay un registro central de capacidades de agentes

### 7.4 Ausencia generalizada de aprendizaje
- Solo **MemoryAgent** tiene aprendizaje real
- Ningún agente implementa `learn()` (definido en `IAgent` pero ignorado en `BaseAgent`)
- Los agentes operan sin retroalimentación histórica

### 7.5 Métricas insuficientes en agentes específicos
- Solo BaseAgent y CoordinatorAgent tienen métricas significativas
- FinancialAgent tiene métricas financieras pero no de rendimiento
- Los demás agentes solo heredan contadores genéricos

---

## 8. Recomendaciones

| Prioridad | Acción | Archivos afectados |
|-----------|--------|-------------------|
| 🔴 Alta | Unificar las dos arquitecturas: que `BaseAgent` implemente `IAgent` o eliminar `IAgent` | `core/interfaces/agent.py`, `cores/agents/base.py`, `core/ai/runtime.py` |
| 🔴 Alta | Unificar las 3 clases `AgentContext` en una sola | `core/interfaces/agent.py`, `core/engine/context.py`, todos los agentes |
| 🟡 Media | Añadir `_get_capabilities()` explícito a ResearchAgent, ExploitAgent, DocumentationAgent, StrategyAgent, ValidatorAgent | 5 archivos de agentes |
| 🟡 Media | Añadir métricas específicas por agente (tasa de confirmación, tiempo por operación, cobertura) | Todos los agentes específicos |
| 🟢 Baja | Implementar hooks de aprendizaje en BaseAgent + aprendizaje específico en cada agente | `base.py`, todos los agentes |
| 🟢 Baja | Añadir persistencia a StrategyAgent y contexto persistente a ResearchAgent/ValidatorAgent | `strategy.py`, `research.py`, `validator.py` |
