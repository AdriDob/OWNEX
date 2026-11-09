# OWNEX V15 — FINAL STATE

Fecha: 2026-11-09 · Base: `7db319ae` → HEAD `5276a65f` · Rama: `main` (sin push)

---

## 1. Corregido y probado

| # | Qué | Evidencia |
|---|---|---|
| 1 | 8 archivos basura de 0 bytes en la raíz eliminados | `5276a65f`; verificado sin consumidores |
| 2 | Remote jobs: clasificación de relación laboral (permanente / temporal / independiente / microtarea / bounty / desconocido) | `cores/opportunity/employment.py`, reusa `EmploymentType` |
| 3 | Empleo permanente queda en el ranking; contrato/freelance/microtarea se cuentan y se excluyen (escape: `OWNEX_REMOTE_JOBS_SCOPE=all`) | `test_contract_and_freelance_stay_out_of_primary_ranking`, `test_scope_all_puts_contract_back_in` |
| 4 | Una vacante ya no se declara caja: `payoff_range = None`, salario en `salary_range` con moneda y periodicidad | `test_approved_remote_job_becomes_ranked_action` |
| 5 | `zero_experience` ya no es `False` fijo: tri-estado con `null` = sin dato | `test_zero_experience_is_unknown_not_false` |
| 6 | Frontend deja de mostrar "requerida" cuando el dato es desconocido | `ApplicationAssistant.vue`, Biome exit 0 |
| 7 | 16 `NameError` (`F821`) y 24 redefiniciones (`F811`) a cero; 7 módulos de test que no se recogían ahora sí | `14c6f7cb`; 4.563 tests recogidos, 0 errores |
| 8 | Un retiro dejó de publicar `financial:sync_completed` | `14c6f7cb`, `financial_truth.py` |
| 9 | Bloque "pay-on-merge" muerto eliminado (−180 líneas, contenía un `TypeError` naive/aware latente) | `14c6f7cb` |

Verificación: `115 passed` en las suites tocadas · `F821=0`, `F811=0` · 4.563 tests recogidos.

---

## 2. Analizado y entregado, sin ejecutar

| Tema | Documento | Por qué no se ejecutó |
|---|---|---|
| ADR-0002 (`core/` + `cores/`) | `ARCHITECTURE_DECISIONS.md` | 421 rutas compartidas, dependencia **bidireccional** (267 y 49 archivos), y el scheduler operativo vive en `core/`. Requiere adjudicación por dominio, no reemplazo global. Además había otro proceso commiteando sobre el mismo árbol. |
| ADR-0003 (bus de eventos dual) | `ARCHITECTURE_DECISIONS.md` | Cambio de superficie alta; necesita inventario de productores/consumidores y tests de entrega única antes de tocar nada. |
| `release/win11-stable` | `ARCHITECTURE_DECISIONS.md` | DIVERGED: 57 exclusivos de `main`, 251 de la estable. Fusionar a ciegas destruiría trabajo. Requiere clasificar los 251 y una matriz Windows 11. |

---

## 3. Bloqueado

| Tema | Bloqueo |
|---|---|
| **Licencia** | Decisión del propietario. `LICENSE` es MIT desde `5ae7280e` (2026-06-28) y el repo se distribuyó desde entonces; el README dice Proprietary. Cambiar el archivo no revoca los permisos ya concedidos. **No se tocó ninguno de los dos.** Ver `LICENSE_DECISION.md`. |
| **Android / Wear OS** | No hay SDK de Android ni emulador en este entorno. No puedo compilar Gradle, ni instalar un APK, ni verificar flujos. Declarar la app "actualizada" sin instalarla sería exactamente lo que la especificación prohíbe. |
| **Release Windows 11** | Sin toolchain Windows ni build verificable. |

---

## 4. Pendiente (con dueño y criterio de cierre)

| Pendiente | Prioridad | Criterio de cierre |
|---|---|---|
| Adjudicar los 115 archivos divergentes (`core/` vs `cores/`) | Alta | matriz completa + tests del dominio en verde + runtime cargando el canónico |
| Borrar los gemelos byte-idénticos sin importadores (subconjunto de 306) | Alta | `git grep` de importadores vacío por archivo, igual que `app_registry` |
| Resolver la licencia en el README | Alta | `LICENSE` y README dicen lo mismo |
| Reescribir el README con matriz VERIFIED / BUILD_VERIFIED / INTEGRATION_PENDING / EXPERIMENTAL / PLANNED / BLOCKED | Alta | cada fila con un comando o test que la respalde |
| Unificar el bus de eventos | Media | tests de entrega única y sin pérdida |
| Clasificar idioma y capacitación en vacantes | Media | sólo con campos reales del feed; no por keyword adivinada |
| Migrar el scheduler a ubicación canónica | Media | depende de la adjudicación |
| 19 `F401`, 8 `UP035` restantes | Baja | `ruff check --fix` revisado archivo por archivo |

---

## 5. Advertencia operativa

Durante V15 hubo **dos escritores sobre el mismo working tree**. Efectos observados: revert de
dos fixes ya aplicados, un `IndentationError` en `api/main.py` y un `try` sin `except` en
`core/opportunity/adapters/__init__.py`. Los tres se corrigieron, pero el hecho es el riesgo:
cualquier migración de `core/`+`cores/` ejecutada en ese estado se pierde o se aplica a medias.

**Recomendación:** serializar agentes antes de la Fase C del plan. Un worktree por agente
(`git worktree add`), integración secuencial, y una sola persona mergeando.

---

## 6. Métricas de V15

| Métrica | Valor |
|---|---|
| Commits | 2 (`14c6f7cb`, `5276a65f`) |
| Líneas netas | −180 (pay-on-merge) − 145 (duplicados en adaptadores) − 8 archivos vacíos + 196 (employment.py) + 61 (income_plan) + 57 (tests) |
| `F821` | 16 → **0** |
| `F811` | 24 → **0** |
| Módulos de test no recogidos | 7 → **0** |
| Tests recogidos | 4.485 → **4.563** |
| Tests nuevos sobre remote jobs | 3 |
| Capacidades declaradas sin verificar | **0** (nada se declaró funcionando sin test o lectura de código) |

## 7. Lo que este documento NO afirma

- No afirma que la suite completa pase: solo las suites listadas en `TEST_REPORT.md`.
- No afirma que OWNEX esté listo para producción.
- No afirma que la arquitectura esté resuelta: está diagnosticada y con estrategia, sin ejecutar.
- No afirma que el README describa el producto: **no se reescribió**, y no puede hacerse
  honestamente mientras la sección de licencia contradiga `LICENSE`.
