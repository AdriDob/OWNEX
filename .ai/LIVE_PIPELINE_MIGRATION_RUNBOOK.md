# Runbook: Live Pipeline Survival — cores/ → core/ consolidation

> Estado: **LISTO PARA EJECUTAR** cuando el agente termine su consolidación twin-tree.
> Regla: NO ejecutar mientras el índice tenga unmerged entries ni mientras `database/models.py` siga duplicando tablas.

## Contexto verificado (2026-11-19)

El agente consolidación es **selectivo/adjudicado**: borra solo duplicados byte-idénticos donde `core/` ya tiene la versión canónica. Los archivos únicos de revenue en `cores/` **sobrevivieron**:

| Archivo | Estado | Dependencias `cores.*` |
|---|---|---|
| `cores/opportunity/live_pipeline.py` | sobrevive (mi scorer incluido) | `cores.direct_work_engine.{models,workbank}`, `cores.opportunity.revenue_ledger`, `cores.opportunity.sources_expansion` |
| `cores/opportunity/live_connections.py` | sobrevive | `cores.opportunity.live_pipeline` |
| `cores/opportunity/revenue_ledger.py` | sobrevive | `cores.availability` |
| `cores/opportunity/sources_expansion/` (9 archivos) | sobrevive | `cores.*` (verificar post-merge) |
| `cores/opportunity/adapters/security/` (12 adapters) | sobrevive | `cores.credentials.vault`, `cores.opportunity.adapters` (base), cross-imports |
| `cores/direct_work_engine/` (44 archivos) | sobrevive | — (es la dependencia raíz del Work Bank) |
| `cores/availability/`, `cores/credentials/vault.py` | sobreviven | — |

`core/` ya tiene equivalentes parciales: `core.credentials.vault`, `core.opportunity.adapters` (OpportunityAdapter/RawOpportunity), forge fetchers. **NO tiene**: `direct_work_engine`, `availability`, `live_*`, `revenue_ledger`, `sources_expansion`, security adapters.

## Verificación post-consolidación (checklist)

```bash
# 1. Índice limpio
git ls-files -u | wc -l          # debe ser 0
git status --short | grep -c "^D "  # consolidación commiteada

# 2. pytest baseline
.venv/bin/python -m pytest tests/test_live_pipeline.py -x -q   # 53 tests

# 3. Imports reales
.venv/bin/python -c "from cores.opportunity.live_pipeline import rank_opportunities; print('ok')"
.venv/bin/python -c "from cores.opportunity.live_connections import connection_report; print('ok')"
.venv/bin/python -c "from cores.opportunity.revenue_ledger import RevenueLedger; print('ok')"
```

## Escenario A — `cores/` queda como paquete para módulos únicos (más probable)

La adjudicación ya demostró que `cores/` retiene lo que `core/` no tiene. En ese caso:

1. Actualizar imports INTERNOS de los archivos que migraron: si `cores.direct_work_engine` se movió a `core/`, cambiar `from cores.direct_work_engine` → `from core.direct_work_engine` en live_pipeline.
2. `live_connections.py` y security adapters: cambiar `cores.credentials.vault` → `core.credentials.vault` (core ya es canónico).
3. `adapters/security/*`: cambiar base `cores.opportunity.adapters` → `core.opportunity.adapters`.
4. Correr `tests/test_live_pipeline.py` + smoke `rank_opportunities` sobre `data/live_opportunities.json`.
5. Commit atómico "revenue pipeline import realignment".

## Escenario B — `cores/` se elimina por completo

Solo si el agente mueve TODO (incl. direct_work_engine, availability, credentials). Entonces:

1. `git mv` mental de los 5 módulos a `core/opportunity/` + `core/availability.py` + `core/credentials/vault.py` (ya existe — merge manual).
2. Reescribir todos los `cores.*` imports del closure (lista arriba).
3. Redirect shims NO — imports directos a `core.*`.
4. Suite completa antes de commit.

## Lo que NO hacer

- No mover archivos ahora (el índice está envenenado y la adjudicación en curso).
- No crear shims `cores→core` "por las dudas" (duplica el problema twin).
- No commitear con el índice del agente — usar `GIT_INDEX_FILE` aislado si urge.

## Señales de que ya se puede ejecutar

- `git ls-files -u` = 0
- `pytest tests/test_live_pipeline.py` colecciona sin error de tablas
- `git log` muestra commit de consolidación del agente
