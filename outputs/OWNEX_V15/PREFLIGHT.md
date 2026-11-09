# OWNEX V15 — PREFLIGHT

Medido el 2026-11-09 sobre el repositorio local, remoto `origin = https://github.com/AdriDob/OWNEX.git`.

## Punto de partida

| Dato | Valor |
|---|---|
| HEAD al iniciar V15 | `7db319ae` (`fix(frontend): auth.ts python-docstring syntax + remote_jobs action type`) |
| HEAD al cerrar Fase A | `14c6f7cb` (fixes de la auditoría Ponytail, ver `TEST_REPORT.md`) |
| Branch | `main`, limpia respecto de su upstream en ese momento |
| Python versionado | 2.570 archivos · 529.551 LOC |
| Tests | 240 archivos · 4.563 tests recogidos, 0 errores de recolección |

## Worktrees

| Ruta | HEAD | Rama | Estado |
|---|---|---|---|
| `/home/adriel/projects/Rastro` | `14c6f7cb` | `main` | árbol de trabajo principal |
| `/home/adriel/projects/Rastro/work/ownex-economy-active-earn` | `6dfad44c` | `ownex-economy-active-earn` | **intacto**, con cambios propios sin commitear (`.ai/CREDENTIALS_AUDIT.md`, `.ai/KNOWN_DEBT.md`, `.ai/MEMORY.md`) |
| `/home/adriel/projects/rastro-twin-tree` | `7db319ae` | `agent/twin-tree-consolidation` | trabajo del agente de consolidación |
| `/tmp/opencode/base`, `/tmp/opencode/headbase`, `/tmp/opencode/ownex-main` | varios | detached / `security/code-scanning-alerts` | prunables, ajenos a V15 |

## Trabajo concurrente detectado

Mientras corría V15 había **otro proceso commiteando sobre el mismo working tree**. Evidencia:
revertió los fixes #4 y #5 de la auditoría (el scheduler volvió a 472 líneas y reapareció el
`"…if False else …"`), y dejó `api/main.py:533` con `IndentationError` y
`core/opportunity/adapters/__init__.py:167` con un `try` sin `except`.

Consecuencia operativa: **la consolidación de `core/`+`cores/` no se ejecuta en V15** (ver
`FINAL_STATE.md`). Dos escritores sobre el mismo árbol convierten una migración en una carrera.

## Ramas divergentes

```
merge-base(main, release/win11-stable) = 898dcc7f2
commits exclusivos de main              = 57
commits exclusivos de release/win11-stable = 251
estado = DIVERGED
```

No se hizo merge, ni reset, ni force push. Hay 82 tags en el repo y releases v7.x publicados.

## Licencia: contradicción confirmada (estado en Fase A — ya resuelta)

> Estado **histórico**, tal como estaba al iniciar V15. El propietario eligió
> licencia privada el 2026-11-09; la resolución está en `LICENSE_DECISION.md`.

| Fuente | Dice |
|---|---|
| `LICENSE` | `MIT License` · `Copyright (c) 2026 Rastro` |
| `README.md` | `**Proprietary.** All rights reserved.` |

Historia: `LICENSE` se agregó **una sola vez**, en `5ae7280e` (2026-06-28, "ui: add product
screenshots and MIT license") y nunca cambió de contenido. Decisión: `LICENSE_DECISION.md`.

## Archivos basura en raíz: confirmados y eliminados

Ocho archivos de **0 bytes**, trackeados desde `b4a0e174` (2026-10-31):

`ACCEPTED`, `CLAIMED`, `DELIVERED`, `EARNED`, `ELIGIBILITY_VERIFIED`, `IN_PROGRESS`, `PAID`, `WITHDRAWN`

Verificado sin consumidores: no hay ningún literal `"PAID"` / `"WITHDRAWN"` / etc. que se abra
como ruta de archivo; los matches en `cores/direct_work_engine/payment_pipeline.py` son nombres
de estado (`ExecState.PAID`), no archivos. Eliminados en `5276a65f`.

## Cuarentena `core/cores/`

`core/cores/` ya **no está** en el árbol activo y no tiene imports
(`git grep "core\.cores"` vacío). La copia está en `.quarantine/core_cores_2026-11-09/`
(219 entradas, 13 MB). **No se borró**: contiene el backup.

## Paths accidentales

No se encontró `home/adriel/projects/Rastro/...` versionado. Lo que existe y es legítimo:
`work/ownex-economy-active-earn` (worktree independiente) y `.quarantine/` (cuarentena).
