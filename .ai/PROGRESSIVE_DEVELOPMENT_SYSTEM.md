# OWNEX — Progressive Development & Preservation System (v1.0)

> Directiva universal de desarrollo acumulativo. Gobierna TODO el trabajo
> en este repo: backend, frontend, agentes, integraciones, datos, docs.
> Fuente de verdad del método; los mecanismos concretos ya existen y se
> referencian aquí — no se duplican.

## Principio central

Cada avance aceptado se convierte en parte protegida de la base. El
siguiente trabajo se construye sobre él, sin perder funcionalidades,
datos, arquitectura ni decisiones. El progreso se mide por
**funcionalidades terminadas, integradas, probadas y utilizables** —
nunca por líneas de código ni cantidad de módulos.

## Mecanismos existentes que implementan esta directiva

| Requisito de la directiva | Mecanismo canónico |
|---|---|
| Inspección de base estable antes de trabajar | `INTEGRATION_PROTOCOL` §1 pre-flight + `git status`/worktrees |
| Preservación de trabajo ajeno | `.agents/AGENT_REGISTRY.md` ownership + regla "un write-owner por archivo" |
| Operaciones destructivas prohibidas | `accidental-data-loss-prevention` skill + PRODUCTION_RULES |
| Incrementos pequeños y atómicos | Commits atómicos + completion report (INTEGRATION_PROTOCOL §3) |
| Registro único de progreso | **`.ai/PROGRESS.md`** + `scripts/progress.py` (ledger por módulo con %, estado, evidencia, bloqueo) |
| Checkpoints y trazabilidad | Git commits + `.ai/CURRENT_STATE.md` + `SESSION_CHECKPOINT.md` |
| Quality gates | `docs/engineering/QUALITY_GATES.md` + ruff/mypy/pytest/biome/vitest |
| Estados de funcionalidad | `INTEGRATION_PROTOCOL` §2: IMPLEMENTED/VERIFIED/PARTIAL/BLOCKED/NOT_IMPLEMENTED/MOCK/UNKNOWN (+ VERIFIED/ACCEPTED del ledger) |
| Datos protegidos | Migraciones versionadas + backups antes de transformaciones + evidence-gated `paid` en RevenueLedger |
| Coordinación multi-agente | `.agents/TASK_BOARD.md` + `AGENT_REGISTRY.md` + INTEGRATION_PROTOCOL |
| % de completitud honesto | `scripts/progress.py` — parsea PROGRESS.md, reporta delta vs `.ai/progress_snapshot.json` |

## Reglas operativas (resumen vinculante)

1. **Preservar antes de avanzar**: inspeccionar HEAD/status/stash/WIP
   paralelo antes de cada tarea. Nunca asumir que un informe anterior
   sigue siendo el estado actual.
2. **Prohibido sin autorización específica**: `git reset --hard`,
   `git clean` destructivo, force push, stash indiscriminado, borrar
   directorios para reemplazar, reescribir historial, eliminar
   migraciones/datos, deshabilitar tests/hooks para pasar validación.
3. **IMPLEMENTED ≠ TERMINADO**: una funcionalidad solo cuenta como
   aceptada con criterios cumplidos + evidencia. `UNKNOWN` nunca se
   convierte en PASS automáticamente.
4. **Checks por dominio**: ruff+pytest (backend), biome+vue-tsc+vitest
   (frontend), tests de integración para contratos, evidencia real para
   claims de integración (nunca mocks presentados como real).
5. **Ledger al cerrar sesión**: actualizar la fila del módulo en
   `.ai/PROGRESS.md` y correr `python3 scripts/progress.py --update`.
   El delta entre snapshots es el progreso medible.
6. **Bloqueos humanos explícitos**: credenciales, cuentas, pagos,
   entregas externas y acciones irreversibles quedan listados como
   `BLOCKED` con la acción humana necesaria — nunca disimulados como
   trabajo de código pendiente.
7. **Sin reescrituras de conveniencia**: reemplazar un componente
   exige identificar el canónico, migrar consumidores y verificar
   regresión. No duplicaciones permanentes, pero tampoco borrados sin
   prueba de migración.
8. **% global con madurez**: 0-49 construcción · 50-69 funciones
   principales · 70-84 integración/validación · 85-94 avanzado con
   pendientes · 95-99 detalles no bloqueantes · 100 alcance acordado +
   quality gates. Bloqueantes críticos impiden declarar terminado aunque
   el promedio sea alto.

## Informe de progreso por fase (obligatorio)

Base de código, commit inicial/final, funcionalidades preservadas,
cambios, archivos afectados, tests + resultados reales, evidencias,
% antes/después, bloqueos, deuda, próxima fase, riesgos.
Separar siempre: realizado / pendiente / propuesto.

## Definición de versión definitiva

Versión estable, completa y usable del alcance aprobado — con
limitaciones externas documentadas si existen. No "sin bugs para
siempre": estable = los flujos acordados funcionan y están probados.
Post-release, el desarrollo continúa acumulativo sobre la estable.
