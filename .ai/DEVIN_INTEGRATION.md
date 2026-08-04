# Devin CLI Integration — Tool Gratuito de Desarrollo

## Overview

**Devin CLI** es una herramienta gratuita de desarrollo de Cognition que permite:
- Ejecutar tareas de desarrollo autónomas
- Refactor de código
- Debugging
- Generación de tests
- Optimización de rendimiento
- Code review
- Planificación de features

OWNEX OMEGA integra Devin CLI como un provider de IA gratuito para tareas de desarrollo.

## Archivos

- `cores/ai/devin_tool.py` — Tool principal para ejecutar comandos de Devin CLI
- `api/routers/devin.py` — API endpoints para usar Devin desde OWNEX
- `core/ai/model_router.py` — Devin agregado como ProviderTier y modelos

## Features

### DevinTool

**Comandos disponibles:**
- `run_task()` — Ejecutar tarea de desarrollo
- `refactor_code()` — Refactor código
- `implement_feature()` — Implementar feature
- `debug_code()` — Debug código
- `generate_tests()` — Generar tests
- `optimize_code()` — Optimizar código
- `code_review()` — Code review
- `plan_feature()` — Planificar feature

**Modelos disponibles:**
- `anthropic/claude-sonnet-4-5` — Modelo principal de Claude
- `opencode/deepseek-v4-flash-free` — Modelo gratuito de DeepSeek
- `opencode/nemotron-3-ultra-free` — Modelo gratuito de Nemotron
- `opencode/mimo-free` — Modelo gratuito de Mimo

### API Endpoints

- `GET /api/devin/status` — Verificar si Devin CLI está disponible
- `POST /api/devin/run` — Ejecutar tarea de desarrollo
- `POST /api/devin/refactor` — Refactor código
- `POST /api/devin/implement` — Implementar feature
- `POST /api/devin/debug` — Debug código
- `POST /api/devin/test` — Generar tests
- `POST /api/devin/optimize` — Optimizar código
- `POST /api/devin/review` — Code review
- `POST /api/devin/plan` — Planificar feature
- `GET /api/devin/tasks/{task_id}` — Obtener tarea por ID
- `GET /api/devin/tasks` — Obtener tareas con filtro
- `GET /api/devin/models` — Obtener modelos disponibles
- `GET /api/devin/command-types` — Obtener tipos de comandos

### ModelRouter Integration

Devin CLI está integrado en el ModelRouter como:
- **ProviderTier.DEVIN** — Tier 5 (Free Development Tool)
- **Modelos:**
  - `devin-claude-sonnet` — Claude Sonnet 4.5 (code, refactor, debug, test, optimize, review, plan)
  - `devin-deepseek` — DeepSeek V4 Flash Free (code, analysis, chat)

**Prioridad en ModelRouter:**
- TaskType.CODE: `devin-claude-sonnet` (primera opción)
- TaskType.ANALYSIS: `devin-claude-sonnet` (primera opción)
- TaskType.RESEARCH: `devin-claude-sonnet` (primera opción)
- TaskType.VALIDATION: `devin-claude-sonnet` (primera opción)

## Uso

### Desde OWNEX Backend

```python
from cores.ai.devin_tool import get_devin_tool

tool = get_devin_tool()

# Refactor código
task = tool.refactor_code(file_path="path/to/file.py", refactor_prompt="Improve code quality and performance")

# Implementar feature
task = tool.implement_feature(feature_description="Add user authentication", files=["src/auth.py", "src/user.py"])

# Debug código
task = tool.debug_code(error_description="Fix segmentation fault in data processing", files=["src/processing.py"])
```

### Desde API

```bash
# Refactor código
curl -X POST http://localhost:8000/api/devin/refactor \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "path/to/file.py",
    "refactor_prompt": "Improve code quality"
  }'

# Implementar feature
curl -X POST http://localhost:8000/api/devin/implement \
  -H "Content-Type: application/json" \
  -d '{
    "feature_description": "Add user authentication",
    "files": ["src/auth.py", "src/user.py"]
  }'
```

### Desde ModelRouter

```python
from core.ai.model_router import get_model_router

router = get_model_router()

# El router automáticamente usará Devin para tareas de código
decision = router.route_task(task_type=TaskType.CODE, prompt="Implement user authentication", privacy_required=False)

# decision.selected_model será "devin-claude-sonnet"
```

## Ventajas

1. **Gratuito** — Sin costos por uso
2. **Alta calidad** — Usa Claude Sonnet 4.5
3. **Autónomo** — Devin maneja todo el proceso de desarrollo
4. **Versátil** — Soporta refactor, debug, tests, optimización, review
5. **Integrado** — Disponible desde ModelRouter y API

## Limitaciones

1. **Solo desarrollo** — Focused en tareas de código
2. **Dependencia de CLI** — Requiere Devin CLI instalado
3. **Timeout** — Tasks pueden tardar mucho tiempo
4. **No interactivo** — No soporta conversación interactiva

## Requisitos

- Devin CLI instalado en el sistema
- `opencode` command disponible en PATH
- Acceso a internet (para modelos de Claude vía Cognition)

## Configuración

```env
# Opcional: Path de Devin CLI si no está en PATH
DEVIN_CLI_PATH=/usr/local/bin/opencode

# Timeout por defecto para tareas (segundos)
DEVIN_DEFAULT_TIMEOUT=300
```

## Ejemplos de Uso

### Refactor de Código

```python
tool = get_devin_tool()

task = tool.refactor_code(file_path="src/processing.py", refactor_prompt="Improve performance and add error handling")

print(f"Task status: {task.status}")
print(f"Output: {task.output}")
```

### Implementación de Feature

```python
tool = get_devin_tool()

task = tool.implement_feature(
    feature_description="Add user authentication with JWT tokens",
    files=["src/auth.py", "src/user.py", "src/middleware.py"],
    working_dir="/path/to/project",
)
```

### Debugging

```python
tool = get_devin_tool()

task = tool.debug_code(
    error_description="Fix infinite loop in data processing", files=["src/processing.py"], model=DevinModel.DEEPSEEK_V4
)
```

### Generación de Tests

```python
tool = get_devin_tool()

task = tool.generate_tests(file_path="src/auth.py", test_framework="pytest", working_dir="/path/to/project")
```

## Monitoring

DevinTool mantiene tracking de todas las tareas:
- Task ID único
- Timestamps (created, started, completed)
- Status (pending, running, completed, failed)
- Output y error
- Duration

```python
tool = get_devin_tool()

# Obtener tareas recientes
recent_tasks = tool.get_recent_tasks(limit=10)

# Obtener tareas por estado
running_tasks = tool.get_tasks_by_status("running")
completed_tasks = tool.get_tasks_by_status("completed")
```

## Futuro

- [ ] Integración con agentes autónomos para desarrollo
- [ ] Workflow de desarrollo autónomo completo
- [ ] Integración con MERLIN para planificación de desarrollo
- [ ] Notificaciones push cuando tareas completan
- [ ] Dashboard de tareas de Devin en frontend
