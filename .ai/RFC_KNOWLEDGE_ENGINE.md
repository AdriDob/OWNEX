# RFC: Knowledge Engine

> **Estado**: DRAFT — especificado, no implementado.
> **Fase OWNEX**: Fase 6 (post-Work Cycles)
> **Criterio de activación**: El sistema genera más conocimiento del que un humano puede releer.

## Problema

Hoy el sistema de memoria funciona así:

```
Sesión → Humano/Agente decide qué es importante → .ai/*.md
```

Esto escala hasta ~1 sesión/día. Cuando OWNEX ejecute múltiples Work Cycles en paralelo, el volumen de conocimiento generado (findings, decisiones, reportes, logs, debugging) superará la capacidad de filtrado manual.

Sin un sistema automático que decida **qué guardar, qué resumir, qué promover y qué descartar**, la memoria se convierte en un cementerio de datos.

## Arquitectura Propuesta

```
INPUT                               PROCESSING                          OUTPUT
│                                                                       │
├── Conversaciones                  ┌──────────────┐                   ├── MEMORY.md
├── Reportes              ───────→  │ Classifier   │  ───────────────→  ├── DECISIONS.md
├── Findings                        │ (LLM +       │                   ├── LESSONS.md
├── Decisiones                      │  rules)      │                   ├── PROJECT_STATE.md
├── TODOs                           └──────┬───────┘                   ├── SESSION_CHECKPOINT.md
├── Logs                                  │                           └── UnifiedMemoryStore
├── Código                                │
└── Debugging                             │
                                          ▼
                                 ┌────────────────┐
                                 │  Permanente    │ → .ai/*.md + UnifiedMemoryStore (priority high)
                                 │  Temporal      │ → UnifiedMemoryStore (priority low, expires 30d)
                                 │  Descartable   │ → Se ignora
                                 └────────────────┘
                                          │
                                          ▼
                                 ┌────────────────┐
                                 │   Summarizer   │ → Resúmenes periódicos
                                 └───────┬────────┘
                                          │
                                          ▼
                                 ┌────────────────────┐
                                 │   Promotion Gate   │ → ¿Es permanente?
                                 └────────────────────┘
                                          │
                                   ┌──────┴──────┐
                                   ▼             ▼
                             MEMORY.md      DECISIONS.md
```

## Componentes

### 1. Classifier

Toma un fragmento de entrada y lo clasifica en una de tres categorías:

| Categoría | Acción | Almacenamiento |
|-----------|--------|----------------|
| **Permanente** | Se guarda en `.ai/*.md` + UnifiedMemoryStore | MEMORY.md, DECISIONS.md, LESSONS.md |
| **Temporal** | Se guarda en UnifiedMemoryStore con expiración | UnifiedMemoryStore (30d, priority baja) |
| **Descartable** | Se ignora | Ninguno |

**Criterios de clasificación:**

- **Permanente si**: Cambia la arquitectura, establece una preferencia del usuario, documenta una lección aprendida, registra una decisión con alternativas, define un nuevo patrón de ataque que funcionó
- **Temporal si**: Debugging momentáneo, log de una ejecución, error conocido y resuelto, experimento fallido sin lecciones nuevas
- **Descartable si**: Conversación trivial, ruido, información duplicada, contenido que ya existe en forma más completa

### 2. Summarizer

Cuando la entrada es larga (>500 tokens) o hay múltiples entradas relacionadas:

- Genera un resumen ejecutivo (3-5 líneas)
- Extrae puntos clave como viñetas
- Identifica si contiene decisiones, lecciones, o cambios de estado

### 3. Promotion Gate

Evaluación periódica (diaria/semanal) del contenido temporal:

- ¿Este contenido temporal merece ser permanente?
- ¿Ha sido consultado múltiples veces? → promover
- ¿Sigue siendo relevante? → extender expiración
- ¿Nunca fue leído? → descartar

### 4. Consolidation Scheduler

Ejecuta el pipeline de consolidación en segundo plano:

- Cada 24h: ejecutar Promotion Gate sobre entradas temporales
- Cada 7d: regenerar resúmenes de la semana
- Cada 30d: archivar contenido temporal no promovido

## Integración con el Ecosistema

```
OWNEX Core
    │
    ├── UnifiedMemoryStore (storage layer)
    │
    ├── Knowledge Engine (classification + promotion)
    │       │
    │       ├── Classifier
    │       ├── Summarizer
    │       ├── Promotion Gate
    │       └── Consolidation Scheduler
    │
    ├── .ai/*.md (curated permanent memory)
    │
    └── Embeddings (Fase 7 — cuando haya volumen)
```

## No Implementar Ahora

Esto queda explícitamente fuera del alcance de esta RFC:

- **Código**: No se escribe código. Esto es un blueprint.
- **Embeddings**: La Fase 7 (vectorial) depende de que la Fase 6 exista y tenga volumen.
- **UI**: No hay interfaz. La Knowledge Engine es un proceso de fondo.
- **Auto-escritura de .ai/*.md**: El RFC no especifica el mecanismo de escritura — puede ser sugerencia al agente o escritura directa. Se decide en implementación.

## Criterio de Activación

La Fase 6 (implementación) comienza cuando se cumple AL MENOS UNO:

1. OWNEX ejecuta >3 Work Cycles en paralelo
2. UnifiedMemoryStore supera 1000 entradas
3. Un agente (Humano/IA) pasa >10 min/semana buscando información que ya existe en el sistema
4. Hay más de 5 decisiones/semana que deberían estar en DECISIONS.md pero no se registran

## Preguntas Abiertas (para resolver en implementación)

1. ¿El Classifier es un LLM call o un modelo pequeño (classifier fine-tuned)?
2. ¿El Summarizer es el mismo LLM o uno separado?
3. ¿Cómo se evita el loop: agente escribe → KE clasifica → agente relee?
4. ¿La escritura a .ai/*.md la hace la KE directamente o sugiere al agente?
5. ¿Qué logging/métricas tiene la KE para auditar sus decisiones?

## Referencias

- `.ai/MEMORY.md` — Documentación del UnifiedMemoryStore
- `.ai/LESSONS.md` — Lección #6: "La memoria sin un consumidor es un cementerio de datos"
- `.ai/TASK_QUEUE.md` — OWNEX Roadmap (Fase 6)
- `.ai/DECISIONS.md` — Decisión 2026-07-26: Knowledge Engine RFC
