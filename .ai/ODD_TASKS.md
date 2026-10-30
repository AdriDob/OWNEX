# ODD Tasks — patrones portados de gentle-shell (docs-only, sin runtime Pi)

> gentle-shell (`Gentleman-Programming/gentle-shell`, MIT) es un harness del agente
> Pi (`pi.dev`). Rastro NO usa Pi → NO se instala el paquete. Solo se portan 3
> patrones como convenciones sobre el SSOT existente. Nada acá crea una segunda
> cola de tareas, un segundo gate ni un segundo formato de skill.

## 1. Archivo de tarea ODD (scratch por tarea, SSOT intacto)

Usar UN archivo `odd/tasks/<feature>.md` solo para trabajo sustancial en curso
(una feature que dura varios turnos). Trabajo chico/read-only: sin archivo.
Al cerrar, lo vigente se pliega a `.ai/TASK_QUEUE.md` / `SESSION_CHECKPOINT.md`
y el scratch se borra. Prohibida doble cola: si está en TASK_QUEUE, el odd file
solo lo referencia, jamás lo duplica.

Template:

```md
# <feature> — ODD task file (scratch, borrar al cerrar)

## Objetivo / problema / por qué
## Scope / constraints (qué NO se toca: DO_NOT_TOUCH.md)
## Tareas (checkboxes, máx. 1 in_progress)
## Evidencia (comandos + output real, no intención)
## Progreso (qué está verde AHORA)
## Siguiente paso (una sola acción)
## Cambios aceptados (qué entró al SSOT y por qué)
```

## 2. Review de candidato congelado (mapea a Human Gate)

Antes de aprobar un diff: congelar el candidato (commit/stash/`git diff` guardado)
y revisar ESE diff, no la rama en movimiento. Checklist mínimo:

1. El diff es lo que se aprobó (hash/rango citado en la aprobación).
2. Riesgo acotado: ¿qué rompe si esto está mal? (tests que lo pinean, citados).
3. Sin secretos ni migraciones silenciosas.
4. Aprobación = Human Gate existente (`cores/automation/safety.py`); esta lista
   no es un gate nuevo, es cómo ejercerlo.

## 3. Contrato de skill (mapea a `.opencode/skills/*/SKILL.md`)

Toda skill: `name` + `description` (cuándo se activa) + ubicación del SKILL.md.
Sin descripción de activación precisa → la skill no existe (el agente no sabe
cuándo cargarla). Ver skills vivas: `agent-loop`, `bee-monitor`.

## 4. Evidencia TDD (mapea a TESTING_POLICY.md)

En trabajo con tests nuevos, registrar la secuencia por fix:
`RED (test que falla) → GREEN (fix mínimo) → TRIANGULATE (2º caso) → REFACTOR`.
La política de qué testear no cambia (ver TESTING_POLICY.md); esto solo fija
cómo se evidencia en el task file / commit.
