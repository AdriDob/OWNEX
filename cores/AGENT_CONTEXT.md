# AGENT_CONTEXT.md — Protocolo de Coordinación Multi-IA

## Última actualización
2026-06-30

## Roles asignados

| Asistente | Rol | Puede ejecutar código en el repo |
|-----------|-----|-----------------------------------|
| OpenCode (VS Code) | Único motor de ejecución. Escribe, corre y commitea código. | SÍ — único autorizado |
| Claude | Arquitecto y coordinador. Revisa reportes, diseña prompts, detecta riesgos. | NO |
| GPT | Segunda opinión técnica puntual, debugging contrastado. | NO |
| Grok | Brainstorming de producto, ideas de features, contexto de mercado. | NO |
| Qwen (Brave) | Consultas rápidas de sintaxis/comandos del día a día. | NO |
| Meta AI | Recordatorios y agenda personal. Sin relación con el código. | NO |

## Regla de oro

NINGÚN asistente que no sea OpenCode debe generar código que se
ejecute directamente sobre este repositorio. Si otro asistente (GPT,
Grok, Qwen) sugiere una idea o un cambio, esa sugerencia debe pasar
primero por revisión humana o por Claude antes de convertirse en un
prompt para OpenCode. Esto evita trabajo duplicado, contradictorio,
o huérfano (ej: el caso de la carpeta Vue duplicada que fue integrada
como frontend/ principal recién después de decisión del dueño).

## Antes de crear cualquier archivo o carpeta nueva

OpenCode debe:
1. Verificar si ya existe algo equivalente en el repo
   (buscar por nombre similar, por funcionalidad, por convención)
2. Si la tarea implica una reestructuración grande (nuevo frontend,
   nuevo framework, nueva carpeta de nivel raíz), confirmar
   explícitamente con el usuario antes de proceder, aunque el prompt
   no lo haya pedido en detalle
3. Registrar en este archivo, en la sección "Decisiones recientes",
   cualquier adición estructural significativa

## Decisiones recientes

- 2026-06-30 — `vue-frontend/` (Vue 3 + ShadCN) reemplazó a
  `frontend/` (React) como frontend principal del proyecto. El React
  original se archivó en `archive_cleanup/frontend-react_20260630/`.
- 2026-06-30 — Se unificaron los routers `api/routers/orion.py` y
  `api/routers/orion_context.py` (eliminado) que duplicaban el
  endpoint `GET /api/orion/context`. El endpoint de sistema completo
  se movió a `GET /api/orion/context/system`.
- 2026-06-30 — Se identificó `database/orion.db` como posible
  duplicado de `database/rastro.db` (mismas 30 tablas, mucho menor
  tamaño: 462KB vs 1.3GB). Pendiente de decisión del dueño.
- 2026-06-30 — Integración de OWASP ZAP (modo pasivo) completada:
  - `core/recon/zap_runner.py` — runner que habla con ZAP daemon
  - `core_engines/engine/hypothesis/zap_generator.py` — convierte
    alertas ZAP en hipótesis con campos didácticos
  - `api/routers/zap.py` — endpoints REST para ZAP (solo pasivo)
  - `Hypothesis` dataclass extendido con campos didácticos
    (what_is_this, why_suspected, real_world_impact, how_to_verify,
    estimated_difficulty, estimated_time_minutes, estimated_reward_range)
  - Nuevos VulnerabilityType: MISSING_CSP, MISSING_HSTS, MISSING_XFO,
    COOKIE_NO_FLAGS, TLS_WEAK, CACHEABLE_HTTPS, AUTOFILL_SENSITIVE
  - Nueva fuente `HypothesisSource.ZAP`
- 2026-06-30 — VerificationGuide.vue creado: flujo guiado de validación
  paso a paso con wizard, progreso, y registro de resultados.

## Stack oficial del proyecto (no debe haber alternativas paralelas)

- Backend: FastAPI + SQLAlchemy + SQLite (PostgreSQL planeado a futuro)
- Frontend: Vue 3 + TypeScript + Vite + Tailwind v4 + Pinia +
  ShadCN Vue + Lucide
- IA: agente híbrido OpenRouter (cloud, free tier) con fallback a
  Ollama local (qwen3:14b)
- Empaquetado desktop: PyInstaller, build nativo en Windows

## Cómo retomar trabajo en una nueva sesión

Cualquier IA (especialmente OpenCode al iniciar una tarea nueva) debe
leer este archivo completo antes de proponer cambios. Si el archivo
contradice lo que la IA cree saber del proyecto, este archivo tiene
prioridad porque refleja el estado real verificado, no el estado
asumido.
