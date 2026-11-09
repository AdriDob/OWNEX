# OWNEX V15 — REPOSITORY CLEANUP

Estado: **CORREGIDO** (commit `5276a65f`) · alcance deliberadamente acotado

## Eliminado

Ocho archivos de 0 bytes en la raíz, trackeados desde `b4a0e174` (2026-10-31):

```
ACCEPTED  CLAIMED  DELIVERED  EARNED
ELIGIBILITY_VERIFIED  IN_PROGRESS  PAID  WITHDRAWN
```

**Verificación previa a borrar:**

| Chequeo | Resultado |
|---|---|
| ¿Tamaño? | 0 bytes los ocho |
| ¿Cuándo entraron? | `b4a0e174`, un único commit ("consolidate baseline audit…") |
| ¿Alguien los abre como ruta? | No: `git grep -E "\"(PAID|WITHDRAWN|…)\""` solo devuelve nombres de estado de `ExecState` en `cores/direct_work_engine/payment_pipeline.py` |
| ¿Son marcadores funcionales? | No: el pipeline usa el enum `ExecState`, no archivos marcadores |

Eran residuo de un `git checkout`/redirección en el commit de consolidación.

## Verificado sin cambios (a propósito)

| Elemento | Estado | Por qué no se tocó |
|---|---|---|
| `.quarantine/core_cores_2026-11-09/` | 219 entradas, 13 MB | es el backup de `core/cores/`; borrarla destruiría la única copia |
| `work/ownex-economy-active-earn` | worktree en `ownex-economy-active-earn` @ `6dfad44c`, con cambios propios sin commitear | es trabajo independiente del propietario; la especificación prohíbe copiarlo o limpiarlo |
| `core/cores/` en el árbol activo | ya no existe; sin imports (`git grep "core\.cores"` vacío) | ya estaba resuelto antes de V15 |
| `frontend/` | intacto como frontend canónico | no se creó otra app |
| `release/win11-stable` | **no modificada** | divergida, ver `ARCHITECTURE_DECISIONS.md` |

## No hecho

- **No se borró ningún duplicado de los 306 archivos byte-idénticos** salvo los que se
  verificaron sin importadores (`cores/app_registry.py`, ver `ARCHITECTURE_DECISIONS.md`).
  El resto requiere la adjudicación por dominio.
- No se tocaron `backups/`, `checksums/`, `dist/`, `desktop-legacy/`, `Sprints/`, `docs/`.
- No se ejecutó `git clean`, `git reset --hard`, ni force push.

## Protección contra reaparición

No se agregó un `.gitignore` para esos nombres: no son artefactos que se generen, fueron un error
puntual de un commit. Un `.gitignore` no protege contra volver a commitearlos y sí podría ocultar
archivos legítimos futuros. La protección real es que ahora no existen y el commit que los
introdujo está identificado.
