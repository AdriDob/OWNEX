---
name: ecc-workflow
description: Úsala ANTES de tocar código en OWNEX/Rastro. Define el workflow obligatorio de 8 pasos (PLAN → INSPECT → IMPLEMENT → TEST → REVIEW → SECURITY → VERIFY → DOCUMENT) y los gates de calidad. Las reglas viven en .ai/ — este skill sólo define el orden operativo. Úsala cuando la tarea sea implementar, refactorizar o corregir algo en cores/, api/, database/, frontend/ o src-tauri/.
compatibility: opencode
metadata:
  audience: developer
  workflow: required
---

# ECC Integration Rules — Rastro/OWNEX

> Reglas de integración del workflow ECC adaptado al proyecto Rastro/OWNEX.
> **`.ai/` sigue siendo la única fuente de verdad** (reglas, protocolos, decisiones).
> Este archivo NO duplica `.ai/`: define el workflow operativo de la capa ECC y
> referencia las reglas existentes.
>
> Ubicación: antes vivía en `.opencode/rules/ECC-INTEGRATION.md`, que **nunca fue
> leído por ningún agente** — OpenCode no tiene concepto de `.opencode/rules/`
> (docs/rules: sólo `AGENTS.md` + `CLAUDE.md` + el glob `instructions` de
> `opencode.json`). Como skill entra al `skill` tool con matching por descripción.

## Workflow ECC (obligatorio para cambios)

1. **PLAN** — Usar el agente `planner` / command `/plan`. Leer `.ai/CURRENT_STATE.md`,
   `.ai/COMPLETED_FEATURES.json`, `.ai/TASK_QUEUE.md` y `.ai/DECISIONS.md` antes de
   proponer algo. Verificar que la feature no existe ya (Regla de Oro del
   `.ai/AGENT_CHARTER.md`).
2. **INSPECT** — Buscar implementaciones existentes. **Regla de Oro del
   `.ai/AGENT_CHARTER.md`**: si ya existe y está bien implementado, NO se escribe
   código nuevo, NO se refactoriza, NO se reemplaza — sólo se registra la
   verificación y se pasa a la siguiente tarea. Clasificar la tarea como
   NO EXISTE / PARCIAL / COMPLETA / OBSOLETA.
   *Nota: `core/` fue eliminado el 2026-09-14; el árbol canónico es `cores/` sólo.*
   Usar `graft` (`graft ask`, `graft grep`, `graft callers <sym> --depth 2`)
   antes que `grep -rn`: devuelve `file:line` exactos y detecta duplicación.
3. **IMPLEMENT** — Cambios pequeños y atómicos. Respetar:
   - `.ai/PRODUCTION_RULES.md` (no refactorizar por estética, solo extender)
   - `.ai/CODE_QUALITY.md` (PEP-8, ruff, type hints, sin magic values)
   - `.ai/DO_NOT_TOUCH.md` (license, IdentityVault, auth, CSRF, error handling, audit log)
   - Architecture Budget: máx. 2 archivos nuevos, 1 dependencia, 1 evento, 1 capability,
     1 contrato, 20 tests por feature.
   - Revenue Rule: la feature debe aumentar detección, calidad de evidencia,
     probabilidad de aceptación, o aprendizaje.
4. **TEST** — `ruff check .` + `python scripts/dev test-fast` (o `make check`).
   Tests nuevos con pytest siguiendo `tests/conftest.py` (aislamiento de DB).
   Frontend: `vue-tsc --noEmit` + `npx vite build`. Rust: `cargo check` si toca `src-tauri/`.
5. **REVIEW** — Agente `code-reviewer` / `python-reviewer` / `rust-reviewer` sobre el diff.
6. **SECURITY** — Agente `security-reviewer` / command `/security`. Checklist OWASP:
   secrets, auth/JWT/device_id, IDOR/BOLA, SQLi, command injection, path traversal,
   CSRF, CORS, XSS, rate limiting, dependencias, WSL/Windows paths, Tauri IPC.
   Reglas detalladas en `.ai/SECURITY_POLICY.md`.
7. **VERIFY** — Command `/verify`: ruff + tests fast + (si aplica) vue-tsc/vite/cargo.
   Criterio DONE del `.ai/AGENT_CHARTER.md` §4: corre en runtime, produce output
   observable, persiste, no rompe otros módulos, pasa flujo end-to-end.
8. **DOCUMENT** — Actualizar `.ai/CURRENT_STATE.md`, `.ai/COMPLETED_FEATURES.json` o
   `.ai/DECISIONS.md` con evidencia. No crear documentación duplicada.

## Gates de calidad (antes de terminar)

- [ ] ruff check limpio
- [ ] suite fast verde (sin regresiones)
- [ ] imports sin errores (`import api.main` OK)
- [ ] sin secretos en el diff
- [ ] sin duplicación de código (twin trees sincronizados si aplica)
- [ ] `.ai/` actualizado si hubo decisión o feature nueva

## Subagentes disponibles

| Agente | Uso | Tools |
|--------|-----|-------|
| `planner` | Plan de implementación (fases + riesgos) | read, bash |
| `code-reviewer` | Review general de calidad/seguridad | read, bash |
| `python-reviewer` | Review Python (FastAPI, SQLAlchemy, pytest) | read, bash |
| `rust-reviewer` | Review Rust (Tauri v2, src-tauri/) | read, bash |
| `security-reviewer` | Review de seguridad (OWASP + stack) | read, bash |

## Commands disponibles

| Command | Agente | Uso |
|---------|--------|-----|
| `/plan` | planner | Crear plan de implementación |
| `/verify` | (agente actual) | Verificación: ruff + tests + build |
| `/security` | security-reviewer | Security review del diff |

## Modelos

Los subagentes **no pinean modelo**: sin `model:` en su frontmatter heredan el
modelo de la sesión primaria. Razón medida: pinear un id lo deja stale en
cuanto el config global cambia, y un id inexistente rompe el subagent en
silencio (fue lo que pasó con `anthropic/claude-sonnet-4-5`, que el config global
ya tiene en `disabled_providers`). La selección de modelo es un problema de
configuración global, no del skill.

## Correcciones aplicadas al mover este archivo (2026-09-30)

Este skill afirmaba dos cosas falsas. Se corrigen acá porque el skill es ahora
la única copia y una afirmación falsa en un SSOT se propaga:

| Afirmación vieja | Realidad | Por qué importa |
|---|---|---|
| "twin trees `core/` + `cores/`" | `core/` se eliminó el 2026-09-14; hay un solo árbol `cores/` | Una regla de INSPECT basada en trees inexistentes hace fallar el paso 2 |
| "usan `anthropic/claude-sonnet-4-5` vía FCC" | config global tiene `anthropic` en `disabled_providers`; el id tampoco existe en el catálogo | Un modelo pineado inexistente rompe el subagent en silencio |

## No aplicable de ECC (descartado)

- **hooks-runtime**: el proyecto ya tiene `.githooks/pre-commit` + hook de ruff en
  `.pre-commit-config.yaml`. No duplicar hooks.
- **285 skills completas / 68 agents**: solo se seleccionaron los 5 subagentes y 3
  commands de arriba. La instalación masiva viola el Architecture Budget y la regla
  "no duplicar configuraciones existentes".
- **Commands npm/TS de ECC** (tdd, e2e, go-*, java-*): pertenecen a otro ecosistema.
- **Continuous learning / instinct de ECC**: el proyecto ya tiene `.ai/LESSONS.md` y
  `.ai/DECISIONS.md` como registro de aprendizaje.