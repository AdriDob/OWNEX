# Unified Memory — ORION Persistent Memory Subsystem

> El "cerebro externo" del proyecto. Memoria estructurada, por namespace, persistente en SQLite, accesible por todos los agentes (OpenCode, Hermes, Cline) y apps ORION.

## Arquitectura

```
UnifiedMemoryStore (core/memory/store.py)
├── 10 namespaces fijos
├── CRUD por namespace + key
├── Tags, prioridad, expiración
├── Búsqueda por texto (ILIKE)
├── Embedding column (schema-ready, semántica futura)
└── Singleton global (get_memory_store())

MerlinMemory (core/merlin/memory.py)
└── Wrapper estratégico sobre UnifiedMemoryStore
    ├── Daily briefs
    ├── Decisiones
    ├── User preferences
    └── Strategic goals
```

## Namespaces (10 fijos)

| Namespace | Propósito | Quién escribe |
|-----------|-----------|---------------|
| `global` | Memoria compartida entre todos los subsistemas | Cualquiera |
| `cateye` | Bug bounty operations (findings, targets, programs) | CATEYE engine |
| `atlas` | Financial intelligence (payouts, revenue, portfolios) | ATLAS engine |
| `odyssey` | Predictive markets | ODYSSEY engine |
| `hermes` | Automation actions, system state | Hermes engine |
| `copilot` | COPILOT conversations, decisions, context | COPILOT engine |
| `merlin` | Strategic briefs, goals, preferences | MerlinMemory |
| `user` | User preferences, working style, learned patterns | Agentes |
| `projects` | Project-level memory, cross-subsystem state | Agentes |
| `decision_history` | Append-only log of decisions | Copilot / agents |

## API Pública

```python
from core.memory.store import get_memory_store

store = get_memory_store()

# Guardar
store.store(namespace="user", key="preferred_language", content="es",
            tags=["preference"], priority=2.0)

# Leer
entry = store.get("user", "preferred_language")  # dict | None

# Buscar
results = store.query(namespace="cateye", tags=["finding", "critical"],
                      search="IDOR", limit=10)

# Eliminar
store.delete("user", "temporal_data")

# Contar
total = store.count()
by_ns = store.count(namespace="cateye")

# Estadísticas
stats = store.get_stats()
# {"total_entries": ..., "namespaces": ..., "expired_entries": ...}
```

### Campos de un MemoryEntry

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `namespace` | str | Agrupación lógica |
| `key` | str | Identificador único dentro del namespace |
| `content` | str | El contenido principal |
| `metadata` | dict | Datos estructurados adicionales |
| `tags` | list[str] | Etiquetas para filtrado |
| `priority` | float | 0.0-3.0 (más alto = más importante) |
| `expires_at` | datetime | Auto-cleanup al hacer query |
| `embedding` | list[float] \| None | Vector para búsqueda semántica futura |

## MerlinMemory (Capa Estratégica)

Úsala para memoria de alto nivel que debe sobrevivir reinicios:

```python
from core.merlin.memory import MerlinMemory

mm = MerlinMemory()

mm.store_brief("Escaneados 3 targets nuevos en HackerOne. 2 IDORs encontrados.")
mm.store_decision("h1_priorization", {"reason": "high_ev", "targets": [...]})
mm.set_preferences({"language": "es", "verbosity": "terse"})
mm.set_goals({"q3_2026": "5 bounties accepted", "revenue_target": 3000})

context = mm.get_strategic_context()
```

## Persistencia

- Backend: SQLite vía `core/database/manager.py` (DB_ID = "memory")
- Archivo: `memory.db` en el directorio de datos del proyecto
- Sobrevive reinicios del backend
- No requiere migraciones manuales (auto-migration vía `_ensure_db()`)

## Embeddings y Búsqueda Semántica (FUTURE)

- Schema listo: columna `embedding` (Text, nullable) en `core_memory`
- Métodos preparados: `store_embedding()`, `get_without_embeddings()`
- Falta: generación de embeddings + búsqueda por similitud de coseno
- Estrategia: diferido hasta que UnifiedMemoryStore tenga >1000 entradas y haya un consumidor real (agente preguntando semánticamente). Cuando llegue ese momento, usar Ollama embeddings API + numpy cosine similarity — sin dependencias nuevas.

## Cómo Usan la Memoria los Agentes

### OpenCode (vía AGENTS.md + opencode.json)
- Lee `.ai/` como fuente de verdad documental
- No escribe directamente a UnifiedMemoryStore (es runtime)
- Las decisiones que toma se registran en DECISIONS.md y SESSION_CHECKPOINT.md

### Hermes
- `memory_enabled: true` en `~/.hermes/config.yaml`
- `~/.hermes/memories/MEMORY.md` y `USER.md` para facts del usuario
- Puede invocar `UnifiedMemoryStore` vía `run.py --hermes` o COPILOT bridge

### Agentes Futuros / COPILOT
- Deben llamar `get_memory_store().query()` para recuperar contexto de sesiones anteriores
- Deben llamar `MerlinMemory().get_strategic_context()` para brief ejecutivo

## Lecturas Relacionadas

- `core/memory/store.py` — Implementación del store
- `core/memory/models.py` — Modelo SQLAlchemy
- `core/merlin/memory.py` — MerlinMemory wrapper
- `tests/test_unified_memory.py` — Tests (24 tests, 186 líneas)
