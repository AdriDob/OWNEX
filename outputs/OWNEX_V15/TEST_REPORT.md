# OWNEX V15 — TEST REPORT

Todos los comandos se ejecutaron en `/home/adriel/projects/Rastro` con `.venv`.

## Resultados

| Check | Comando | Resultado |
|---|---|---|
| Lint backend | `ruff check cores/ api/ core/ database/` | **54 errores**, `F821 = 0`, `F811 = 0` |
| Recogida de tests | `pytest --collect-only -q` | **4.563 tests, 0 errores** |
| Suites tocadas | `pytest` (6 archivos) | **115 passed** |
| Income plan | `pytest tests/test_income_plan.py -q` | **23 passed** |
| Lint frontend | `biome check src/pages/ApplicationAssistant.vue` | **exit 0** |

### Desglose de los 54 errores de Ruff

```
19  F401  imports sin usar
 8  UP035  imports desde typing deprecados
 4  SIM110  loop que puede ser any()
 3  N805    primer argumento de método no se llama self
 3  E402    import no al tope del archivo
 2  SIM102  if anidado colapsable
```

Ninguno es un bug de ejecución: son deuda de estilo. `F821` (nombre indefinido → `NameError`) y
`F811` (redefinición) están en cero, que era el objetivo de la Fase C.

## Suites que se ejecutaron y por qué

| Archivo | Motivo |
|---|---|
| `test_income_plan.py` | cubre el cambio de remote jobs (4 tests nuevos/actualizados) |
| `test_financial_scheduler_persist.py`, `test_financial_connections.py` | cubren el scheduler donde se borró el bloque pay-on-merge |
| `test_execution_queue.py`, `test_payment_pipeline.py` | eran 2 de los 7 módulos que no se podían ni importar |
| `test_voice_engram_commands.py` | control de no regresión del subsistema de voz |

## Lo que NO se ejecutó

| Check | Motivo | Consecuencia |
|---|---|---|
| Suite completa (`make test`) | 4.563 tests; tiempo y escritura concurrente en el árbol | **no puedo afirmar que la suite completa pase**. Solo las suites listadas arriba. |
| `mypy` | el propio `pyproject.toml` lo tiene en modo no-strict con `follow_imports = "skip"` y 15 módulos con `ignore_errors` | el type-checking configurado no prueba nada; no lo reporto como gate |
| `vue-tsc` | typecheck del frontend completo, minutos, con errores preexistentes | no verificado; el cambio de `.vue` es de template + interfaz y pasó Biome |
| Vitest | no toqué lógica de frontend, solo un binding de presentación | no ejecutado |
| Android / Wear OS (Gradle) | no hay SDK de Android en este entorno | **BLOCKED**, ver `FINAL_STATE.md` |
| Build Windows 11 | no hay toolchain Windows | **BLOCKED** |
| Escaneo de secretos | no ejecutado en esta pasada | pendiente |

## Regla aplicada

Ningún test se debilitó, desactivó ni se sustituyó por mocks para aparentar que algo funciona.
Cuando el contrato cambió a propósito (salario ya no es payoff), **el assert se actualizó para
fijar el comportamiento nuevo** (`payoff_range is None`, `salary_range` separado), no para tapar
el viejo.
