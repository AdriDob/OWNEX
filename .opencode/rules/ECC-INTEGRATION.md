# ECC Integration Rules — Rastro/OWNEX

> Reglas de integración del workflow ECC adaptado al proyecto Rastro/OWNEX.
> **`.ai/` sigue siendo la única fuente de verdad** (reglas, protocolos, decisiones).
> Este archivo NO duplica `.ai/`: define el workflow operativo de la capa ECC y
> referencia las reglas existentes.

## Workflow ECC (obligatorio para cambios)

1. **PLAN** — Usar el agente `planner` / command `/plan`. Leer `.ai/CURRENT_STATE.md`,
   `.ai/COMPLETED_FEATURES.json`, `.ai/TASK_QUEUE.md` y `.ai/DECISIONS.md` antes de
   proponer algo. Verificar que la feature no existe ya (Regla de Oro del
   `.ai/AGENT_CHARTER.md`).
2. **INSPECT** — Buscar implementaciones existentes (twin trees `core/` + `cores/`).
   Nunca reimplementar: clasificar la tarea como NO EXISTE / PARCIAL / COMPLETA /
   OBSOLETA (ciclo de verificación del `.ai/AGENT_CHARTER.md`).
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

Los subagentes usan el modelo del proyecto (`anthropic/claude-sonnet-4-5` vía FCC proxy)
con failover a Ollama local y OmniRoute. No se introducen modelos nuevos.

## No aplicable de ECC (descartado)

- **hooks-runtime**: el proyecto ya tiene `.githooks/pre-commit` + hook de ruff en
  `.pre-commit-config.yaml`. No duplicar hooks.
- **285 skills completas / 68 agents**: solo se seleccionaron los 5 subagentes y 3
  commands de arriba. La instalación masiva viola el Architecture Budget y la regla
  "no duplicar configuraciones existentes".
- **Commands npm/TS de ECC** (tdd, e2e, go-*, java-*): pertenecen a otro ecosistema.
- **Continuous learning / instinct de ECC**: el proyecto ya tiene `.ai/LESSONS.md` y
  `.ai/DECISIONS.md` como registro de aprendizaje.