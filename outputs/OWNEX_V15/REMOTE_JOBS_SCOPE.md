# OWNEX V15 — REMOTE JOBS SCOPE

Estado: **CORREGIDO Y PROBADO** · commit `5276a65f`

## Problema

El commit `9f42ca92` ("wire remote-job tracker into unified income plan") metió vacantes
`prepared`/`approved` en el ranking de ingresos sin distinguir qué tipo de relación laboral
ofrecen, y con dos afirmaciones inventadas:

1. `zero_experience: False` fijo para **todas** las vacantes.
2. `payoff_range = {"low": salary_min, "high": salary_min}` — un sueldo anunciado declarado
   como si fuera caja a cobrar.

Efecto: un contrato freelance de 3 meses competía contra entregas del Work Bank y bounties
que sí pagan, y el plan presentaba un salario mensual como payoff del día.

## Solución implementada

Un módulo nuevo, `cores/opportunity/employment.py` (196 líneas), y el track reescrito en
`cores/direct_work_engine/income_plan.py`.

### Vocabulario único

Reutiliza `cores/direct_work_engine.models.EmploymentType` (ya existía: `FULL_TIME`,
`PART_TIME`, `CONTRACT`, `FREELANCE`, `BOUNTY`, `MICROTASK`, `CHALLENGE`, `PRIZE`,
`OPEN_CALL`, `ROLLING`, `PROJECT`, `RETAINER`). **No se creó un segundo enum.**

Se agrupa en `RelationshipGroup`: `permanent_employment`, `temporary_employment`,
`independent_work`, `microtask`, `bounty`, `unknown`.

### Clasificación con evidencia, sin adivinar

| Orden | Fuente | `evidence` | `inferred` |
|---|---|---|---|
| 1 | campos `employment_type`, `job_type`, `contract_type`, `type` | `field:<nombre>` | `false` |
| 2 | keywords en `title`/`description`/`summary` | `keyword:<texto>` | `true` |
| 3 | nada | `none` → `RelationshipGroup.UNKNOWN` | `false` |

Cada acción publica `employment_type`, `relationship`, `relationship_evidence`,
`relationship_inferred` y `primary_eligible`.

### Regla de colocación

`PRIMARY_GROUPS = {permanent_employment}`. Por defecto solo el empleo permanente compite en el
ranking. `temporary_employment`, `independent_work`, `microtask`, `bounty` y `unknown` se
**cuentan** en `by_relationship` y quedan fuera del ranking.

Variable de escape, explícita: `OWNEX_REMOTE_JOBS_SCOPE=all` los reincorpora.
Valor por defecto: `permanent_only`. El scope vigente se informa en el payload (`track.scope`).

Los empleos remotos permanentes **no se eliminaron**: siguen disponibles en su categoría.

### Dinero: una vacante no es un ingreso

| Campo | Antes | Ahora |
|---|---|---|
| `salary_range` | no existía | `{low, high, currency, period, source: "feed_reported"}` o `None` |
| `payoff_range` | `{low: salary_min, high: salary_min}` | **`None`** |
| `zero_experience` | `False` fijo | `true` / `false` / **`null`** según el feed |

`zero_experience` se deriva de `zero_experience`, `accepts_beginner`, `no_experience_required`,
`experience_years`, `min_experience_years` o `years_required`. Si ninguno está, es `null`
(desconocido), nunca `false`.

### Frontend

`frontend/src/pages/ApplicationAssistant.vue` asumía booleano y renderizaba
`zero_experience ? 'NO requerida' : 'requerida'`, así que el valor desconocido se mostraba como
"requerida" — otra afirmación inventada. Ahora es tri-estado (`NO requerida` / `requerida` /
`sin dato`), muestra `tipo: <relationship>` y el tipo del campo pasó a `boolean | null`.
Biome: exit 0.

## Tests

`tests/test_income_plan.py` — 23 pasan. Los 4 relevantes:

| Test | Qué fija |
|---|---|
| `test_approved_remote_job_becomes_ranked_action` | acción permanente rankeada; `payoff_range is None`; `salary_range.low == 3000`; `salary_range.source == "feed_reported"` |
| `test_contract_and_freelance_stay_out_of_primary_ranking` | la vacante `job_type=contract` **no** entra; `excluded_non_permanent == 1`; `by_relationship[temporary_employment] == 1`; `scope == "permanent_only"` |
| `test_scope_all_puts_contract_back_in` | con `OWNEX_REMOTE_JOBS_SCOPE=all` vuelve a entrar; `excluded_non_permanent == 0` |
| `test_zero_experience_is_unknown_not_false` | sin dato en el feed, `zero_experience is None` |

## Lo que NO se hizo

- No se borró el Remote Job Matcher ni sus feeds (`cores/opportunity/job_tracker.py` intacto).
- No se tocó la persistencia de vacantes (`save_job`, `transition`, `gap_analysis` intactos).
- No se inventó salario, elegibilidad ni probabilidad de contratación: `access_probability`
  sigue en `"desconocida"`.
- No se agregó clasificación de idioma ni de capacitación: el feed actual no expone esos campos
  y derivarlos por keyword sería adivinar. Queda como pendiente con criterio de cierre
  (ver `FINAL_STATE.md`).
