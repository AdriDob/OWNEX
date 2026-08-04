# OWNEX v6 — Informe Final + Plan de Implementación

> FASE 12 del plan OWNEX v6 — Documento de cierre
> Fecha: 2026-07-29
> Diseños: 12 fases completadas

---

## Resumen Ejecutivo

OWNEX v6 evoluciona de un orquestador de agentes de bug bounty a un **Sistema Operativo de Trabajo Autónomo Universal** compuesto por **14 motores secuenciales + 2 motores transversales**, conectados por un pipeline unificado.

### La transformación

| De (v5) | A (v6) |
|---------|--------|
| Descubrimiento pasivo (scraper BB) | Universal Sensor Network (30+ sensores) |
| Oportunidades como unidad atómica | Observaciones como unidad atómica |
| Contexto implícito en prompts | ContextEngine → contexto estructurado |
| Estrategia fija (BB primero) | StrategyEngine → decisión dinámica |
| Aprendizaje crudo en logs | LearningEngine → patrones persistentes |
| Relaciones en tablas SQL | KnowledgeGraph → grafo de relaciones |
| Solo bug bounty | 7+ ciclos de trabajo (security, dev, ai, freelance, data, content, research) |

---

## Arquitectura Completada (14 + 2 Motores)

```
Pipeline principal (14 motores en secuencia):
  │
  1.  SENSOR NETWORK  → 2.  OBSERVATION ENGINE  → 3.  NORMALIZATION ENGINE
  4.  IDENTITY ENGINE  → 5.  CLASSIFICATION ENGINE → 6.  OPPORTUNITY ENGINE
  7.  STATE ENGINE     → 8.  CONTEXT ENGINE       → 9.  STRATEGY ENGINE
  10. PLANNING ENGINE  → 11. PREPARATION ENGINE   → 12. EXECUTION ENGINE
  13. VALIDATION ENGINE→ 14. LEARNING ENGINE      → 15. EVOLUTION ENGINE
                                                          │
                                                  vuelve al paso 1
                                                          │
Motores transversales (siempre activos):
  A. CAPABILITY ENGINE — catálogo de capacidades del sistema
  B. KNOWLEDGE GRAPH — grafo de relaciones entre todo
```

### Documentos de diseño creados

| Archivo | Contenido | Líneas |
|---------|-----------|--------|
| `OWNEX_ARCHITECTURE.md` | Doc canónico — arquitectura completa, interfaces, flujos | 886 |
| `OWNEX_NORMALIZATION_IDENTITY.md` | Normalization Engine + Identity Engine | 732 |
| `OWNEX_STATE_ENGINE.md` | Máquina de 10 estados con transiciones | 531 |
| `OWNEX_CLASSIFICATION_CAPABILITY.md` | Clasificación + Catálogo de capacidades | ~500 |
| `OWNEX_CONTEXT_STRATEGY.md` | Context Engine + Strategy Engine | ~600 |
| `OWNEX_EXECUTION_PIPELINE.md` | Planning → Preparation → Execution | ~500 |
| `OWNEX_VALIDATION_LEARNING_EVOLUTION.md` | Bucle de validación + aprendizaje + evolución | ~650 |
| `OWNEX_KNOWLEDGE_GRAPH.md` | Grafo de relaciones, queries, población | ~800 |

---

## Plan de Implementación

### Filosofía de implementación

1. **Preservar PipelineEngine v5 al 100%** — no se toca
2. **Construir alrededor, no sobre** — cada motor nuevo es un módulo independiente
3. **Implementar en orden de dependencias**: sensores primero, ejecución al final
4. **Cada motor con test** — pytest obligatorio antes de declarar completo
5. **EventBus como integración** — los motores se comunican por eventos, no por imports directos

### Fase 1: Fundación (Semana 1)

**Crear:** `Rastro/core/engine/` — directorio base para los motores

```
Rastro/core/engine/
  ├── __init__.py
  ├── base.py           # Motor base: clase abstracta con lifecycle (init/start/stop/health)
  ├── event_bus.py      # EventBus extendido con tipado de eventos
  ├── registry.py       # Registry de motores (singleton)
  └── contracts.py      # Contratos compartidos (dataclasses)
```

```python
# base.py — Ejemplo de la interfaz base
from abc import ABC, abstractmethod


class Engine(ABC):
    """Base class for all OWNEX v6 engines."""

    name: str = ""

    @abstractmethod
    async def initialize(self):
        """Called once at startup."""
        pass

    @abstractmethod
    async def health(self) -> dict:
        """Return engine health status."""
        pass

    async def start(self):
        """Called when engine should begin processing."""
        pass

    async def stop(self):
        """Called on shutdown."""
        pass
```

### Fase 2: Sensor Network (Semana 1-2)

**Crear:** `Rastro/core/sensors/`

```
Rastro/core/sensors/
  ├── __init__.py
  ├── base.py            # Interfaz Sensor abstracta
  ├── sensor_registry.py # Registry de sensores
  ├── observation.py     # Modelo Observation (dataclass)
  ├── scheduler.py       # Scheduler de sensores (cadencia)
  ├── cache.py           # Observation cache (dedup temporal)
  │
  # Adaptadores existentes que se envuelven como sensores:
  ├── adapters/
  │   ├── __init__.py
  │   ├── hackerone.py   # Envuelve el scraper BB existente
  │   ├── bugcrowd.py    # Ídem
  │   ├── github.py      # Dev bounties
  │   └── generic.py     # Web scraping genérico
  │
  └── tests/
```

```python
# base.py — Interfaz Sensor concreta
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Observation:
    """A raw observation from the world.

    This is the atomic unit of OWNEX.
    Not an opportunity — just a signal.
    """

    id: str
    sensor_id: str
    source_type: str  # "bug_bounty", "dev_bounty", "ai_work"
    source_name: str  # "hackerone", "github", "mindrift"
    external_id: str  # ID on the platform
    title: str
    description: str
    raw_data: dict
    observed_at: str  # ISO timestamp
    url: str | None = None
    estimated_reward_min: float = 0.0
    estimated_reward_max: float = 0.0
    tags: list[str] | None = None


class Sensor(ABC):
    """A single sensor in the Universal Sensor Network."""

    id: str = ""
    name: str = ""
    cadence_seconds: int = 3600  # default 1h

    @abstractmethod
    async def fetch(self) -> list[Observation]:
        """Fetch observations from the sensor source."""
        pass

    async def health(self) -> dict:
        return {"id": self.id, "status": "active"}
```

**Acción concreta:** Envolver el scraper BB existente (`cores/bounty_scraper/scraper.py`) como un Sensor:

```python
# adapters/hackerone.py — Sensor que envuelve el scraper legacy
from cores.bounty_scraper.scraper import BountyScraper
from core.sensors.base import Sensor, Observation


class HackerOneSensor(Sensor):
    """Wraps the existing HackerOne scraper as a Sensor."""

    id = "hackerone_sensor"
    name = "HackerOne Programs Sensor"
    cadence_seconds = 1800  # 30 min

    def __init__(self):
        self.scraper = BountyScraper()

    async def fetch(self) -> list[Observation]:
        """Use legacy scraper, emit Observations."""
        results = await self.scraper.run_async()  # hypothetical async wrapper
        return [
            Observation(
                id=f"h1:{p['id']}",
                sensor_id=self.id,
                source_type="bug_bounty",
                source_name="hackerone",
                external_id=str(p["id"]),
                title=p.get("program_name", p.get("name", "Unknown")),
                description=p.get("description", ""),
                raw_data=p,
                observed_at=datetime.now(timezone.utc).isoformat(),
                url=p.get("url", ""),
                estimated_reward_min=p.get("reward_min", 0),
                estimated_reward_max=p.get("reward_max", 0),
            )
            for p in results
        ]
```

### Fase 3: Observation Engine (Semana 2)

**Crear:** `Rastro/core/engine/observation_engine.py`

Coordina los sensores: arranque, parada, recolección, cacheo.

```python
class ObservationEngine(Engine):
    """Coordinates all sensors."""
    
    name = "observation_engine"
    
    def __init__(self):
        self.sensors: dict[str, Sensor] = {}
    
    def register(self, sensor: Sensor):
        self.sensors[sensor.id] = sensor
    
    async def collect(self) -> list[Observation]:
        all_observations = []
        for sensor in self.sensors.values():
            try:
                obs = await sensor.fetch()
                all_observations.extend(obs)
            except Exception as e:
                logger.error(f"Sensor {sensor.id} failed: {e}")
        return all_observations
```

### Fase 4: Normalization + Identity (Semana 2-3)

**Crear:** `Rastro/core/engine/normalization.py`, `Rastro/core/engine/identity.py`

**Acción clave:** Mapear los nombres de campos actuales en Rastro a los campos normalizados de OWNEX v6. La tabla de mapeo está en `OWNEX_NORMALIZATION_IDENTITY.md`.

```python
# normalization.py
class NormalizationEngine(Engine):
    """Normalizes observations to a canonical format."""
    
    FIELD_MAP = {
        # Format: {source_type: {source_field: canonical_field}}
        "bug_bounty": {
            "reward_min": "estimated_reward_min",
            "min_bounty": "estimated_reward_min",
            "reward_max": "estimated_reward_max",
            "max_bounty": "estimated_reward_max",
        },
        "dev_bounty": {
            "reward": "estimated_reward_max",
            "amount": "estimated_reward_max",
        },
    }
    
    async def normalize(self, obs: Observation) -> NormalizedObservation:
        # Map fields, then return normalized version
        pass
```

### Fase 5: Classification + Opportunity + State (Semana 3-4)

**Crear:** `Rastro/core/engine/classification.py`, `Rastro/core/engine/opportunity.py`, `Rastro/core/engine/state.py`

**Acción clave:** Implementar el clasificador (reward → scope → actionable → type), la máquina de 10 estados, y el opportunity scoring.

### Fase 6: Context + Strategy (Semana 4-5)

**Crear:** `Rastro/core/engine/context.py`, `Rastro/core/engine/strategy.py`

**Acción clave:** Implementar el ContextSource que consulta fuentes (platform docs, user history, learning patterns) y el StrategyEngine que decide qué oportunidad ejecutar ahora.

### Fase 7: Planning + Preparation + Execution (Semana 5-6)

**Extender:** `Rastro/core/pipeline/` — agregar PlanningEngine y PreparationEngine antes de Execution.

**Acción clave:** No modificar PipelineEngine.run_pipeline(). Agregar wrappers que decoren la ejecución con planificación y preparación previas.

### Fase 8: Validation + Learning + Evolution (Semana 6-7)

**Crear:** `Rastro/core/engine/validation.py`, `Rastro/core/engine/learning.py`, `Rastro/core/engine/evolution.py`

**Acción clave:** LearningEngine usa SQLite (o la DB que ya existe). EvolutionEngine se ejecuta diariamente como cron job.

### Fase 9: Knowledge Graph (Semana 7)

**Crear:** `Rastro/core/engine/knowledge_graph.py`

**Acción clave:** SQLite-based graph. Grafo POBLADO AUTOMÁTICAMENTE por EventBus. Cada vez que un motor produce un resultado, el GraphPopulator lo registra.

### Fase 10: Integration + QA (Semana 8)

**Wiring:** Conectar todos los motores vía Registry + EventBus.

**Tests:** pytest para cada motor, integración end-to-end.

---

## Archivos a crear (resumen)

```
Rastro/core/engine/
  ├── __init__.py                   # Export público
  ├── base.py                       # Engine base
  ├── event_bus.py                  # EventBus extendido
  ├── registry.py                   # Engine registry (singleton)
  ├── contracts.py                  # Dataclasses compartidas
  ├── observation_engine.py         # Observation Engine
  ├── normalization.py              # Normalization Engine
  ├── identity.py                   # Identity Engine
  ├── classification.py             # Classification Engine
  ├── opportunity.py                # Opportunity Engine (scoring)
  ├── state.py                      # State Engine (10 estados)
  ├── context.py                    # Context Engine
  ├── strategy.py                   # Strategy Engine
  ├── planning.py                   # Planning Engine
  ├── preparation.py                # Preparation Engine
  ├── execution.py                  # Execution Engine (extiende PipelineEngine)
  ├── validation.py                 # Validation Engine
  ├── learning.py                   # Learning Engine
  ├── evolution.py                  # Evolution Engine
  └── knowledge_graph.py            # Knowledge Graph

Rastro/core/sensors/
  ├── __init__.py
  ├── base.py                       # Interfaz Sensor
  ├── sensor_registry.py            # Sensor registry
  ├── observation.py                # Observation dataclass
  ├── scheduler.py                  # Sensor scheduler
  ├── cache.py                      # Observation dedup cache
  ├── adapters/
  │   ├── __init__.py
  │   ├── hackerone.py              # Sensor HackerOne (envuelve scraper)
  │   ├── bugcrowd.py               # Sensor Bugcrowd
  │   ├── github.py                 # Sensor GitHub (dev bounties)
  │   └── generic.py                # Web scraping genérico
  └── tests/
```

Total: ~30 archivos nuevos, ~1 dependencia (ninguna nueva si ya tienes httpx/sqlite3).

---

## Lo que NO cambia

| Componente | Razón |
|-----------|-------|
| `PipelineEngine` (`core/pipeline/engine.py`) | Completamente funcional, se extiende no se reescribe |
| `config/engine.yaml` | Pipeline config sigue igual |
| `cores/bounty_scraper/scraper.py` (995 líneas) | Legacy que se envuelve como sensor, no se modifica |
| `core/adapters/` | Todos los adapters existentes siguen funcionando |
| `core/quality/estimator.py` | Quality estimator se mantiene |
| `EventBus` | Misma interfaz, se extienden los eventos |
| `HealingOrchestrator` | Sigue igual |
| `Scheduler` | Sigue igual |
| `Cron Jobs` | Sin cambios |
| `cateye.py` | App CATEYE sigue igual |

---

## Revenue Impact Assessment

| Pregunta | Respuesta |
|----------|-----------|
| ¿Qué parte aumenta detección? | Universal Sensor Network (más fuentes, no solo BB) + mejor clasificación |
| ¿Qué parte reduce falsos positivos? | Normalization + Identity + Confidence scoring en Classification |
| ¿Qué parte mejora aceptación? | Validation Engine (calidad antes de submit) + Learning (patrones que funcionan) |
| ¿Qué parte mejora aprendizaje? | LearningEngine + EvolutionEngine (bucle completo) |
| ¿Qué parte mejora autonomía? | StrategyEngine (decide solo) + ContextEngine (no necesita prompts manuales) |
| ¿Qué parte mejora Expected Revenue? | StrategyEngine (siempre decide la mejor EV) + multi-ciclo ($ no solo de BB) |
| ¿Qué parte solo mejora arquitectura? | Knowledge Graph (habilitante, no direct revenue) |

---

## Próximos pasos inmediatos

1. Aprobar este informe
2. Crear `Rastro/core/engine/` con `base.py`, `contracts.py`, `event_bus.py`
3. Crear `Rastro/core/sensors/` con `base.py`, `observation.py`
4. Envolver scraper BB como HackerOneSensor
5. Implementar ObservationEngine
6. Continuar con motores subsiguientes según orden de dependencias

---

## Apéndice: Diagrama de dependencias entre motores

```
KnowledgeGraph ──── transversal ────► todos los motores (población automática)
CapabilityEngine ── transversal ────► Classification, Planning, Execution

SensorNetwork ───► Observation ───► Normalization ───► Identity
                                                          │
                                                          ▼
                                                     Classification
                                                          │
                                                          ▼
                                                     Opportunity
                                                          │
                                                          ▼
                                                     StateEngine ◄──── ContextEngine
                                                          │               │
                                                          ▼               │
                                                     StrategyEngine ─────┘
                                                          │
                                                          ▼
                                                     PlanningEngine
                                                          │
                                                          ▼
                                                     PreparationEngine
                                                          │
                                                          ▼
                                                     ExecutionEngine
                                                          │
                                                          ▼
                                                     ValidationEngine
                                                          │
                                                          ▼
                                                     LearningEngine
                                                          │
                                                          ▼
                                                     EvolutionEngine ────► StrategyEngine
                                                                          (feedback loop)
```

Cada motor depende solo del anterior en la cadena. No hay dependencias circulares en el pipeline principal. El feedback loop (Evolution → Strategy) es asíncrono y manejado por EventBus.
