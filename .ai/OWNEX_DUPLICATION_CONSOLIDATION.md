# OWNEX Duplication Consolidation v10

**Fecha:** 2026-11-09
**Estado:** AUDIT + PLAN — nada eliminado (regla: no borrar sin dependencias verificadas)

## Medición real

| Árbol | `.py` | Nota |
|---|---:|---|
| `core/` | 1788 | Incluye `core/cores/` anidado |
| `cores/` | 1089 | SSOT candidato global (TASK_QUEUE previo) |
| `core/cores/` | 1089 | **untracked**, copia casi idéntica de `cores/` |
| `work/ownex-economy-active-earn` | gitlink `160000` @ `5ce8866b` | worktree separado con cambios propios; **no canónico** |

### `core/cores/` vs `cores/` (hash SHA256)

- common = 1082 · identical = **1066** · different = 16 · only_core_cores = 7 · only_cores = 7
- Imports externos `core.cores`: **0** (solo interno `core/cores/direct_work_engine/manager.py`).
- Veredicto: **copia accidental anidada**. Candidato a cuarentena/borrado **tras backup + confirmación del owner**. No eliminado en esta sesión.

### `work/ownex-economy-active-earn`

- Gitlink con `git status` propio sucio (decenas de `M`). Contiene frontend/backend duplicados.
- No es parte del frontend canónico ni del backend en ejecución. Decidir con el owner: conservar como worktree de experimentación, mergear selects, o archivar. **No borrar.**

## SSOT por dominio (evidencia → decisión preliminar)

| Dominio | SSOT propuesto | Evidencia | Acción |
|---|---|---|---|
| Direct Work Engine | `cores/direct_work_engine` | `api/routers/direct_work.py` (37 refs), tests DWE verdes | Migrar referencias `core/cores/direct_work_engine` → `cores/` |
| Argentina payout methods (base) | `cores/financial_intelligence/argentina_payout_methods.py` | Usado por `payment_compat/engine.py`, `cashflow.py`, tests | Mantener; `core/financial_intelligence/` es paralelo/legacy |
| Payout ranked subset | `cores/financial/payout_recommender.py` | Usado por `connections.py`, `financial_hub/*` | Mantener como subset documentado (no duplicado exacto) |
| OWNEX Account auth | `api/routers/auth_users.py` + `cores/auth/auth.py` + `database.models.User` | Frontend store + `test_auth_users.py` (14) | **Canónico**; `auth_user.py` legacy a deprecar |
| Device session auth | `api/routers/auth.py` + `cores/auth/auth_manager` + `session_validator` | autoLogin + tests security | **Canónico** para sesión local/device |
| Source catalog/families/adaptation | `cores/opportunity/*` | 176 fuentes, 164 tests recientes | Mantener |
| Discovery→WorkBank runtime | `core/opportunity/*` + `core/scheduler/jobs.py` | scheduler runtime + `test_discovery_to_workbank.py` | Mantener; verificar `cores/scheduler` divergencia |
| Financial intelligence routers | `cores.financial_intelligence.*` | `progressive_scaling`, `ultra_fast_income`, `infinite_sources`, `alerts`, `auto_apply`, `modes` importan `cores.` | Migrar `core/financial_intelligence` → `cores/` tras mapa de imports |

## Imports migrados

- **Ninguno aún** (esta fase es auditoría + plan). El único cambio de código fue eliminar la ruta duplicada `/home` del router frontend (no es duplicación backend).

## Archivos conservados por compatibilidad

- `api/routers/auth_user.py` — **DEPRECATED/unmounted** (2026-11-09): root `/auth/*` legacy, 0 consumidores canónicos verificados; conservado como referencia, no remontar sin auditoría.
- `cores/financial/payout_recommender.py` — subset rankeado usado por `connections.py`; no eliminar.
- `core/` completo — runtime scheduler/discovery usa `core/opportunity` y `core/scheduler`; no tocar sin mapa.

## Archivos candidatos a eliminación (NO eliminados)

1. `core/cores/` — copia accidental de `cores/` (untracked). Requiere backup + confirmación.
2. `work/ownex-economy-active-earn` — worktree separado; decisión del owner.
3. `api/routers/auth_user.py` — tras verificar que nadie lo consume.
4. Posibles re-exports/compat en `core/` una vez migrados los imports.

## Riesgos

- Borrar `core/cores/` sin backup pierde trabajo untracked (aunque sea copia).
- `work/` gitlink tiene cambios propios; tratarlo como repo independiente.
- Mezcla `core.`/`cores.` en `api/` (475 vs 379 imports): borrado global rompe runtime.
- `core/financial_intelligence` vs `cores/financial_intelligence`: verificar imports antes de consolidar.

## Tests de regresión ejecutados

- `tests/test_auth_users.py` → **14 passed** (incluye nuevo contrato email/session/user).
- Suite catálogo/familias/adaptación → **164 passed** (sesión previa, sin regresión).
- `ruff check api/routers/auth_users.py tests/test_auth_users.py` → OK.
- `npx biome check src/router/index.ts` → OK.

## Checklist

- [x] Medir duplicados (`core/`, `cores/`, `core/cores/`, `work/`).
- [x] Identificar SSOT por dominio con evidencia.
- [x] No eliminar archivos por nombre parecido.
- [x] Mapear imports `core.`/`cores.` por dominio (evidencia generada, ver §Mapa de imports).
- [ ] Ejecutar migración por dominio hacia el SSOT (orden abajo).
- [ ] Cuarentena/borrado de `core/cores/` tras backup + confirmación.
- [ ] Decisión del owner sobre `work/ownex-economy-active-earn`.
- [x] Deprecar `api/routers/auth_user.py` (0 consumidores canónicos; desmontado de `main.py`, archivo conservado).
- [ ] Regresión completa (`make check` / suite fast) tras cada migración.

## Mapa de imports `core.`/`cores.` por dominio (evidencia)

Conteo de archivos externos que importan cada árbol por módulo (mayor = árbol dominante). Generado 2026-11-09; `api/` mezcla ≈475 `cores` vs ≈379 `core` → **no hay reemplazo global seguro**.

**`cores.*` dominante (SSOT = `cores/`):**
`direct_work_engine` 105·0 · `events` 105·15 · `agents` 52·1 · `ai` 38·5 · `tools` 37·0 · `identity_vault` 33·0 · `validation` 32·15 · `financial` 30·0 · `memory` 26·20 · `crypto` 24·0 · `notifications` 23·10 · `intelligence` 23·0 · `license` 22·0 · `engine` 46·28 (mixto, cores algo mayor).

**`core.*` dominante (SSOT = `core/`):**
`opportunity` 154·67 (mixto, core mayor) · `credentials` 77·7 · `offensive` 64·3 · `copilot` 62·5 · `interfaces` 49·7 · `database` 44·0 · `execution` 43·9 · `extension` 37·0 · `cycles` 35·12 · `capabilities` 33·2 · `reports` 31·1 · `polymarket` 31·0 · `setup` 28·8 · `investment` 24·1 · `autonomy` 24·4 · `revenue` 22·5 · `sensors` 19·1 · `trading` 19·2 · `decision_journal` 17·1.

**Mixtos que requieren mapa por archivo antes de tocar:** `opportunity`, `auth`, `financial_intelligence`, `engine`, `execution`, `cycles`, `investment`, `events`, `knowledge`, `recon`, `reporting`, `setup`, `sync`, `system_state`, `validation`, `workflows`, `automation`, `integrations`, `evidence`, `learning`, `platform`, `pipeline`.

## Orden de migración propuesto (seguro → riesgoso)

1. **Dominios `cores`-only con 0-3 imports `core`**: `direct_work_engine`, `tools`, `identity_vault`, `financial`, `crypto`, `intelligence`, `license`, `agents`, `ai` → consolidar en `cores/`; el `core/cores/` anidado ya es copia, ignorar.
2. **Dominios `core`-only con 0-7 imports `cores`**: `database`, `extension`, `polymarket`, `credentials`, `offensive`, `copilot`, `interfaces`, `reports`, `sensors`, `trading`, `decision_journal`, `autonomy`, `investment` → consolidar en `core/`.
3. **Mixtos** (`opportunity`, `auth`, `financial_intelligence`, `engine`, `execution`, `cycles`, `events`, `validation`, `memory`, `notifications`, `knowledge`, `recon`, `reporting`, `setup`, `sync`, `system_state`, `workflows`, `automation`, `integrations`, `evidence`, `learning`, `platform`, `pipeline`): migrar archivo por archivo solo tras verificar imports + tests; nunca `core.`→`cores.` global.

**Regla:** cada migración = (a) elegir SSOT por dominio, (b) re-export temporal si hace falta, (c) migrar imports, (d) tests, (e) recién ahí evaluar borrado. `core/cores/` y `work/` gitlink quedan congelados hasta decisión del owner.
