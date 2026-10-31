# AI Runtime (OAR)

> OAR (*Ownex AI Runtime*) es el único punto de entrada para operaciones de IA en OWNEX. Ningún módulo de negocio llama a un proveedor directamente: todos pasan por OAR.

## Arquitectura

```mermaid
graph TD
    A[Módulo de negocio] -->|get_oar\(\).chat\(\)| B[OAR]
    B --> C{SmartRouter}
    C -->|score: health × capability × quota × cost| D[Provider Registry]
    D --> E[Circuit Breaker]
    E --> F1[LOCAL<br/>Ollama · LMStudio]
    E --> F2[FREE<br/>OpenCode · OmniRoute · FCC]
    E --> F3[CHEAP+<br/>Groq · OpenRouter · disabled by default]
    F1 & F2 & F3 --> G[AIResponse]
    G --> H[(Observability JSONL)]
```

## Componentes

| Componente | Archivo | Función |
|---|---|---|
| SmartRouter | `cores/ai/runtime/router.py` | Scoring ponderado (health, capabilities, tier, quota) |
| FailoverEngine | `cores/ai/runtime/failover.py` | Circuit breaker con threshold + cooldown + recuperación |
| QuotaTracker | `cores/ai/runtime/resilience.py` | Ventanas req/min + tokens/día; UNKNOWN → factor 0.85 |
| ErrorClassifier | `cores/ai/runtime/resilience.py` | HTTP/mensaje → HealthStatus + política de retry |
| DegradedMode | `cores/ai/runtime/resilience.py` | NORMAL → DEGRADED → OFFLINE_AI (EventBus `ai:mode_changed`) |
| CostTracker | `cores/ai/runtime/cost.py` | Presupuesto diario ($0 default), pricing por provider:model |
| SemanticCache | `cores/ai/runtime/cache.py` | TTL 3600s, hash de messages+model_class |
| LearningEngine | `cores/ai/runtime/learning.py` | Outcomes reales → preferencias por TaskType |
| ObservabilitySink | `cores/ai/runtime/observability.py` | JSONL con redacción de secretos + agregados |

## Task Types

OAR enruta por tipo de tarea (enum `TaskType`, 19 valores). Los más usados:

```text
CHAT · CODE · RESEARCH · ANALYSIS · REASONING · SUMMARIZATION
BUG_BOUNTY · SECURITY_ANALYSIS · REPORT · PLANNING
```

No necesitas elegir modelo: el router selecciona el mejor disponible según capacidades y salud.

## Provider Tiers

| Tier | Valor | Ejemplos | Default |
|---|---|---|---|
| LOCAL | 1 | Ollama, LMStudio | ✅ habilitado |
| FREE | 2 | OpenCode, OmniRoute, FCC, ollama_cloud, freecloudmodels | ✅ habilitado |
| CHEAP | 3 | Groq, Together, DeepInfra, Cerebras | 🔒 requiere key + budget > $0 |
| PREMIUM | 4 | OpenRouter, NVIDIA NIM | 🔒 idem |
| ENTERPRISE | 5 | Custom | 🔒 idem |

**Regla**: `daily_budget_usd = 0.0` por defecto. Tiers ≥ CHEAP están deshabilitados hasta que configures una API key y subas el budget.

## Cadena de fallback

```text
1. Cache (TTL 3600s)
2. Reglas deterministas (sin LLM)
3. LOCAL provider healthy
4. FREE provider healthy
5. FREE fallback (siguiente en cadena)
6. Paid (solo si habilitado explícitamente)
7. Degraded mode (reglas sin LLM)
```

Errores permanentes (401/403, contexto excedido, modelo inexistente) **no se reintentan**: saltan directo al siguiente provider.

## Cuotas

OWNEX nunca asume límites ilimitados:

- Límite conocido → factor proporcional al margen restante
- Límite UNKNOWN → factor fijo `0.85` (penalización leve honesta)
- Límite excedido → factor `0.0` (router lo descarta)

Los contadores se observan en tiempo real; los límites declarados pueden configurarse vía `QuotaTracker.set_declared_limit()`.

## Observabilidad

Cada llamada registra en `data/ai_observability.jsonl`:

```json
{"timestamp":"...","task":"CODE","provider":"opencode","model":"deepseek-v4-flash-free","success":true,"latency_ms":420,"tokens_in":120,"tokens_out":350,"cost_usd":0.0}
```

Secretos (`sk-*`, `Bearer`, `x-api-key`) se redactan antes de escribir. Agregados disponibles via `aggregate()`:

- `success_rate` / `fallback_rate` / `cache_hit_rate`
- `avg_latency_ms` / `tokens_total` / `cost_usd`
- Desglose `by_task` y `by_provider` (input del LearningEngine)

## API

```bash
GET /oar/status    # providers, health, costs, cache, learning, resilience
GET /oar/doctor    # diagnóstico completo
POST /oar/chat     # chat con routing automático
POST /oar/route    # decisión de routing sin ejecutar
```

## Uso programático

```python
from cores.ai.runtime import get_oar, TaskType

oar = get_oar()
response = await oar.chat(
    "Resume este finding",
    task_type=TaskType.SUMMARIZATION,
)
print(response.content)  # texto generado
print(response.provider_id)  # qué provider ejecutó
print(response.cost_usd)  # costo real (0.0 en free/local)
```

## Degraded Mode

Si todos los LLMs fallan o no hay red:

1. EventBus publica `ai:mode_changed` con modo `offline_ai`
2. El frontend muestra `IA OFFLINE — modo reglas`
3. Los motores deterministas (scoring, payment-compat, barriers) continúan operando
4. Al recuperarse un provider, el modo vuelve a `normal` automáticamente

Ver `/oar/status` → `resilience.mode` para inspección.
