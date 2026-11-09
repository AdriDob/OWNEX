# Ponytail Audit — OWNEX / Rastro

Fecha: 2026-11-09 · Protocolo: `/ponytail-audit` (DietrichGebert/ponytail @ 96608e0)
Auditoría: lectura solamente. La ejecución de los fixes se registra abajo.

## Estado tras la ejecución (commit `0703c15b`)

| Métrica | Antes | Después |
|---|---|---|
| Módulos de test que no se recogen | 7 | **0** |
| Tests recogidos | 4.485 | **4.560** |
| Ruff (core+cores+api+database) | 93 | **48** |
| `F821` nombres indefinidos | 17 | **0** |
| `F811` redefiniciones | 24 | **0** |
| `cores/financial/scheduler.py` | 472 líneas | **292** |
| `if False` en rutas de dinero | 2 | **0** |
| Gemelos de `app_registry` | 2 | **1** |

Ejecutado: #1 (imports pegados), #4 (evento de retiro + rama muerta de HTROI), #5 (bloque
pay-on-merge muerto, −180 líneas), #3 (los 16 `F821`, borrando los duplicados locales de
los tres adaptadores `direct_work_*`: −145 líneas), y el piloto de #2 borrando
`cores/app_registry.py`, que no importaba nadie.

No ejecutado: el resto de #2 (306 gemelos byte-idénticos + 107 imports de `core/`).
Requiere una migración módulo por módulo sobre los ADR-0002/0003 ya propuestos
(`docs/architecture/TWIN_TREE_AUDIT.md`), y hay otro proceso commiteando sobre el mismo
working tree, así que un cambio de esa superficie se pisaría a mitad de camino.

Verificación de esta ejecución: `ruff` limpio en los archivos tocados, `pytest` 96 tests
en las suites afectadas (financiero, conexiones, cola de ejecución, payment pipeline,
voice), y `--collect-only` completo sin errores (4.560).

## Qué hace este repo

Plataforma de trabajo autónomo de un solo operador (bug bounty + trabajo freelance +
finanzas + voz), empaquetada como desktop (Tauri/PyInstaller) con backend FastAPI
local y frontend Vue 3.

**Carga asumida:** un usuario, un proceso backend en `127.0.0.1`, SQLite local,
sin multi-tenant. Todo lo que se marca como "escala" se juzga con ese supuesto:
un solo operador, no miles de usuarios concurrentes.

## Mapa medido

| Área | Dato |
|---|---|
| Python versionado | 2.570 archivos · 529.551 LOC |
| Tests | 240 archivos · 4.485 tests recogidos · **7 módulos no se pueden recoger** |
| Backend vivo | `cores/` (1.105 archivos, 246.304 LOC) — `api/` lo importa 233 veces |
| Backend gemelo | `core/` (708 archivos, 133.978 LOC) — `api/` lo importa 107 veces |
| Frontend | `frontend/` Vue (247 componentes, 78 páginas, 22 tests) |
| Segundo frontend | `omega/` React/TS (18 archivos, fuera de CI) |
| Dependencias | `requirements.txt` 43 líneas · `pyproject.toml` declara **1** |
| Ruff (core+cores+api+database) | 93 errores · 17 `F821` · 24 `F811` |
| Vulture ≥90% confianza | 60 hallazgos |
| Marcadores `shortcut:`/`ponytail:` | 0 |

---

# Must fix

### 1. Un bloque de imports pegado a nivel 0 rompe 7 módulos de test — `core/execution_queue/driver.py:63-68`

- **Qué es:** dentro de `_process_item()` (línea 61) se pegó un bloque de 6 líneas
  `from cores.direct_work_engine.payment_pipeline import (...)` con indentación 0.
- **Problema:** `IndentationError: unexpected indent` en la línea 68. `pytest` no puede
  importar el módulo, y con eso caen `test_execution_queue.py`,
  `test_execution_queue_store.py`, `test_execution_mirror.py`, `test_payment_pipeline.py`,
  `test_state_convergence.py`, `test_mobile_copilot.py` y `test_profile_kit.py`.
  Además los 6 símbolos importados (`record_human_gate_entry`, `record_human_approval`,
  `record_human_rejection`, `record_human_block`, `record_ultimate_paid`) **no se usan
  en ningún punto del archivo** (`grep` vacío).
- **Fix:** borrar las 6 líneas. No indentarlas: no se usan.
- **Si no se hace:** 7 módulos de test siguen invisibles; cualquier regresión en la cola
  de ejecución o en el pipeline de pago pasa sin detección.

### 2. Dos árboles gemelos con 421 módulos del mismo nombre — `core/` vs `cores/`

- **Qué es:** 421 rutas relativas existen en ambos árboles. **306 son byte-idénticas
  (59.760 LOC duplicados literalmente)**; 115 ya divergieron.
  Los imports van en las dos direcciones: `cores → core` 530 veces, `core → cores` 64,
  `api → core` 107.
- **Problema:** no es solo peso. Cada módulo con estado global existe dos veces, así que
  hay **dos singletons del mismo registro**. Caso concreto: `api/main.py:668` importa
  `core.app_registry.get_app_registry()`, mientras `cores/app_registry.py` (94 LOC)
  también define `get_app_registry` (versión de 108 LOC en `core/`, 22 líneas de
  diferencia). Quien registre una app por una puerta no la ve por la otra.
  Lo mismo aplica a `EventBus`, caches y contadores de salud.
- **Fix:** elegir `cores/` como árbol único (es el que importa `api/` de forma dominante
  y el que usa el scheduler en runtime), y migrar los 107 imports de `core/` módulo por
  módulo; borrar el archivo gemelo en cada paso. Empezar por los módulos con estado
  global (`app_registry`, `event_bus`, `health`), que son los que producen bugs.
- **Si no se hace:** el estado del sistema sigue partido en dos; los bugs de "el panel
  dice X y el scheduler dice Y" no tienen causa visible y cada fix hay que aplicarlo
  dos veces.

### 3. 17 nombres indefinidos (`F821`) = `NameError` garantizado si se ejecuta la rama

- **Qué es:** Ruff `F821` en 17 lugares, sin ningún `# noqa` que documente una razón.
  Casos: `api/adapters/direct_work_alignerr.py:113,114,219,222` (`_PAYMENT_METHOD_ALIASES`,
  `_resolve_alignerr_platform`, `_Alignerr_CATEGORY`), lo mismo en
  `direct_work_codeforai.py:108,109,222` y `direct_work_datannotation.py:109,110,215`;
  `api/routers/sessions.py:18` (`Any`); `cores/agenda/__init__.py:145`
  (`get_forecasting_engine`); `core/mcp_bridge.py:539,555`
  (`MultiplierStrategy`, `DailyEarnings`); `cores/source_intelligence/intelligence.py:151`
  y `renewal.py:86`.
- **Problema:** los tres adaptadores `direct_work_*` salieron de copiar-pegar una
  plantilla y quedaron nombres a medio renombrar (`_Alignerr_CATEGORY` *dentro* del
  archivo de Alignerr). `_payment_method_for_source` referencia un alias que no existe
  en ese módulo, así que **toda** llamada a ese camino explota.
- **Fix:** en cada archivo, apuntar a los nombres reales del módulo (para los alias,
  `_PAYMENT_METHOD_ALIASES` vive en `api/adapters/own_work_catalog_adapter.py`). Si un
  adaptador está sin terminar, borrarlo en vez de dejarlo importable y roto.
- **Si no se hace:** el descubrimiento de esas tres fuentes falla en runtime con un
  traceback que no dice nada de la causa real.

### 4. Un retiro de dinero publica el evento equivocado — `api/routers/financial_truth.py:207`

- **Qué es:** `publish_financial_event("financial:withdrawal_completed" if False else "financial:sync_completed", ...)`
  dentro del handler que crea el `Withdrawal`.
- **Problema:** la rama muerta `if False` hace que **todo retiro emita
  `financial:sync_completed`**. Cualquier suscriptor que espere
  `financial:withdrawal_completed` (ledger, reconciliación, dashboard de capital)
  nunca se entera de que el dinero salió.
- **Fix:** `publish_financial_event("financial:withdrawal_completed", ...)`.
- **Si no se hace:** los retiros existen en la DB pero no en el flujo de eventos;
  el saldo de capital queda desincronizado justo en la ruta donde hay dinero real.

### 5. El gate de pago por merge está muerto y tiene un bug de zona horaria — `cores/financial/scheduler.py:263-458`

- **Qué es:** dos bloques, "Pay-on-Merge Helpers" (263-344: `_get_pending_payouts`,
  `_trigger_instant_payout`) y "Pay-on-Merge Detection" (360-458:
  `_check_merged_deliverables`, `_check_merge_status`): ~195 LOC que implementan
  "pagar apenas se mergea el deliverable".
- **Problema:** (a) `_check_merged_deliverables` **no se llama desde ningún lugar**
  (`grep` en todo el árbol: solo la definición en 363), así que el gate nunca corre y
  `_get_pending_payouts` solo se usa desde el código muerto.
  (b) Adentro, `_check_merge_status:415-416` compara `datetime.fromisoformat(confirmed)`
  (naive, viene de columna DB) contra `datetime.now(UTC)` (aware) → `TypeError:
  can't subtract offset-naive and offset-aware datetimes`. `_trigger_instant_payout:325`
  y `_check_merged_deliverables:394` escriben `datetime.utcnow()` (naive) en el mismo
  bloque. (c) Ningún test toca esas tres funciones.
- **Fix:** decidir una cosa: o se borra el bloque entero (es lo más barato y no cambia
  el comportamiento de hoy), o se cablea y se arregla normalizando a UTC-aware en la
  lectura (`fromisoformat(...)` + `if dt.tzinfo is None: dt = dt.replace(tzinfo=UTC)`),
  con un test que cubra un `delivery_confirmed_at` naive. No dejarlo en medio.
- **Si no se hace:** ~195 LOC que parecen una feature de pago instantáneo, no lo son, y
  el primero que la cablee se come el `TypeError` con dinero de por medio.

---

# Should fix

### 6. `pip install .` produce una instalación rota — `pyproject.toml:6-8`

- **Qué es:** `dependencies = ["prometheus-client>=0.19.0"]`, una sola dependencia.
- **Problema:** el código importa `fastapi` (204 veces), `httpx` (118), `pydantic` (84),
  `sqlalchemy` (79), `cryptography` (8). Están en `requirements.txt` (43 líneas), no en
  `pyproject.toml`. Instalar el paquete deja un import que falla en el primer arranque.
  Son dos fuentes de verdad para lo mismo.
- **Fix:** que `pyproject.toml` sea la fuente y `requirements.txt` se genere de ahí
  (`pip-compile` o `uv export`), o al revés — pero una sola.
- **Si no se hace:** cualquier instalación limpia (otra PC, CI, recovery) falla sin
  explicar por qué.

### 7. 152 excepciones tragadas (`except ...: pass/continue`)

- **Qué es:** bloques `except Exception:`/`except BaseException:` cuyo cuerpo es
  `pass` o `continue`, en `cores/`, `core/` y `api/`.
- **Problema:** error invisible. El caso caro es justo el patrón que ya se ve en
  `cores/financial/scheduler.py:177,449` y en `connection_manager.py`, donde un fallo de
  red queda como "sin datos" y el panel muestra un cero que parece un hecho.
- **Fix:** no reescribir los 152. Priorizar los de rutas de dinero, auth y sync
  (financiero, conexiones, brokers), y ahí cambiar `pass` por `logger.warning(...)` o
  `raise`. El resto puede esperar.
- **Si no se hace:** los fallos de conexión siguen disfrazados de "no hay datos", que es
  exactamente la confusión configurado ≠ autenticado ≠ sincronizado.

### 8. 24 redefiniciones (`F811`) — dos definiciones del mismo nombre, gana la última

- **Qué es:** `api/adapters/legacy.py` (17 errores), `cons/…` no: son
  `cores/direct_work_engine/payment_pipeline.py` (12) y los `direct_work_*` (10-11 c/u).
- **Problema:** una función o import definido dos veces significa que la primera
  definición es código que nadie ejecuta, y que quien lea el archivo va a razonar sobre
  la versión equivocada. En `payment_pipeline.py` (archivo nuevo, +138 LOC en el diff)
  hay 12.
- **Fix:** borrar la definición vieja; si las dos versiones hacen cosas distintas, decidir
  cuál vale y borrar la otra.
- **Si no se hace:** el comportamiento real no coincide con lo que se lee.

### 9. Migración de esquema sin dueño claro

- **Qué es:** `database/db.py:202` hace `Base.metadata.create_all(bind=engine)` en el
  boot, y a la vez existe `alembic/` con **1 sola migración** (`alembic/versions/`).
- **Problema:** dos caminos para el mismo esquema. `create_all` crea tablas nuevas pero
  —como dice el propio comentario en `database/db.py:172`— no agrega columnas a tablas
  existentes; con 1 migración para todo el proyecto, una instalación vieja se queda con
  columnas que el código nuevo espera.
- **Fix:** una sola vía. Si Alembic es la elegida, `create_all` queda solo para tests.
- **Si no se hace:** el bug aparece solo en máquinas que ya tenían la DB, no en la tuya.

### 10. `omega/` es un segundo frontend que nada construye — `omega/`

- **Qué es:** app React/TS de 18 archivos (`DashboardScreen.tsx`, `services/api.ts`,
  stores), `package.json` `private: true`, sin referencias en `.github/workflows/`.
- **Problema:** 18 archivos que envejecen contra una API que cambia, sin build ni test
  que avise cuando se rompe. `frontend/` (Vue) es la que se construye.
- **Fix:** o entra al CI con su build, o se borra. Mantenerla "por si" es lo más caro.
- **Si no se hace:** cuando se retome, va a estar rota en varios lugares y nadie lo sabrá
  hasta ese día.

### 11. 13 `TODO` en código de producción, sin fecha ni dueño

- **Qué es:** `api/routers/market_intelligence.py:213`, `core/closed_loop.py:90`,
  `core/payment_tracker.py:193`, `core/polymarket/backtest/engine.py:119`,
  `core/scheduler/ev_engine.py:254,273`, `core/investment/strategist.py:50`,
  `core/autonomy/code_generator.py:563`, entre otros.
- **Problema:** varios están en rutas de dinero/EV. `market_intelligence.py:213`
  devuelve `opportunities = []  # TODO: load from stored signals`, o sea un endpoint
  que responde vacío y parece "no hay oportunidades".
- **Fix:** los de rutas de dinero, convertir en issue con trigger o borrar la función
  que devuelve vacío. Los cosméticos, borrar el comentario.
- **Si no se hace:** sigue contradiciendo la regla 5 de AGENTS.md (cero TODO sin fecha).

---

# Nice to have

### 12. 60 hallazgos de código muerto (`vulture` ≥90%) duplicados por el árbol gemelo

- **Qué es:** variables y parámetros que nadie lee. Ejemplos:
  `api/routers/orion_cli.py:21,32,54,66` (`detalles`), `core/cycles/qa.py:379`
  (`include_regression`), y en `core/investment/adapters/onchain_analytics_adapter.py:194-206`
  los métodos `track_whales(min_balance_usd=1_000_000)` y
  `detect_large_transfers(min_value_usd, time_window_hours)` **son stubs que hacen
  `return []`**.
- **Problema:** son métodos con firma terminada y cuerpo vacío. Quien los llame recibe
  una lista vacía y no puede distinguir "no hay ballenas" de "esto no está
  implementado" — exactamente el patrón mock-que-parece-real que la directiva prohíbe.
- **Fix:** borrar los stubs (o levantarlos con `NotImplementedError` para que griten) y
  borrar las variables sin uso; el resto de los 60 hallazgos, borrar.
- **Si no se hace:** el panel de inversión puede mostrar "sin ballenas detectadas" como
  si fuera un resultado del mercado.

### 13. `api/routers/__init__.py:6` — expresión suelta `sessions_router,`

- **Qué es:** línea 6 es un nombre suelto seguido de coma, resto de un rename.
- **Problema:** no falla al importar (es una expresión válida) pero `F821`: si alguien
  hace `from api.routers import sessions_router` explota.
- **Fix:** borrar la línea 5-6 (comentario incluido).
- **Si no se hace:** trampa para el próximo import.

### 14. HTROI ignora `days_to_cash` — `api/routers/direct_work.py:269`

- **Qué es:** `expected_income_usd=float(expected_cash["days_to_cash"] or 0) if False else float(ranked.expected_value)`.
- **Problema:** la rama muerta tiene el bug (`days_to_cash` no es un ingreso, es un
  plazo); la viva es correcta pero queda ruido que sugiere una intención abandonada.
- **Fix:** borrar la rama `if False` y dejar `float(ranked.expected_value)`.
- **Si no se hace:** el próximo que lo lea va a "arreglar" la rama equivocada.

### 15. Dos `datetime` conviviendo: 110 `utcnow()`, 1.362 `now(UTC)`

- **Qué es:** mezcla de naive y aware en todo el proyecto.
- **Problema:** cualquier comparación o resta entre los dos grupos lanza `TypeError`
  (ver hallazgo 5).
- **Fix:** `utcnow()` → `datetime.now(UTC)` con `ruff`/`sed` por archivo, y en las
  lecturas de DB normalizar con `replace(tzinfo=UTC)` cuando falte.
- **Si no se hace:** bugs intermitentes que dependen de la ruta.

### 16. `frontend/`: 78 páginas para un solo operador

- **Qué es:** `frontend/src/pages/*.vue` = 78 páginas, 247 componentes, 22 archivos de test.
- **Problema:** 78 pantallas es más superficie de la que un operador puede usar; varias
  van a estar sin link y sin test. No es un bug, es inventario que hay que podar.
- **Fix:** listar las páginas alcanzables desde el router y comparar; las que no estén en
  el router, borrarlas.
- **Si no se hace:** sigue creciendo el costo de mantener y de navegar.

---

## Veredicto

El sistema funciona y la disciplina de lint en los módulos tocados recientemente es
buena (voz, financiero, conexiones: Ruff limpio), pero el repo tiene **una fractura
estructural** — dos copias de 421 módulos con imports en ambas direcciones, que ya
produjo dos singletons del mismo registro — y **una capa de código que se ve terminado
y no lo está**: 17 `NameError` garantizados, un retiro que emite el evento equivocado,
un gate de pago que nunca corre, y 7 módulos de test que no se pueden ni importar.
Nada de eso es teórico: cada uno tiene archivo, línea y caso.

Lo bueno: **cero marcadores `shortcut:`**. La deuda que hay no está declarada, está
escondida — por eso aparece como `if False`, imports pegados a nivel 0 y nombres a medio
renombrar.

Orden de ataque sugerido: 1 (7 líneas) → 4 (1 línea) → 5 (borrar 140 o cablear) →
3 (17 nombres) → 2 (la migración, por módulos con estado global primero).

**Lean: -60.000 líneas** (306 gemelos byte-idénticos) **-195 líneas** (gate de pago
muerto) **-7 líneas** (imports pegados) — y **-0 dependencias**: todo lo que se importa
se usa, el problema es que `pyproject.toml` declara una sola de las 43.

## Deuda declarada (`/ponytail-debt`)

**No shortcut debt. Clean ledger.** Grep de `shortcut:`/`ponytail:` en `*.py`,
`*.vue`, `*.ts`: 0 marcadores. La deuda real del repo no está declarada con marcadores,
así que no hay triggers que cosechar: los 13 `TODO` del hallazgo 11 son lo más parecido,
y ninguno nombra un límite ni un upgrade.

## Ganancias (`/ponytail-gain`)

Benchmark publicado de Ponytail 5 — **39 tareas, Opus 5.5, 5 corridas, contra el mismo
agente sin el skill**. Es un promedio de benchmark, **no** una medición de este repo:
aquí no hay versión "sin ponytail" contra la cual restar, así que no existe número de
ahorro medido para OWNEX.

```
Líneas de código       [###############-------------]  47%   (-53%)
Tokens de salida       [#################-----------]  55%   (-45%)
Costo                  [#######################-----]  74%   (-26%)
Tiempo                 [##################----------]  59%   (-41%)
Checks ocultos OK      [############################]  97%   (sin skill 96%)
Tests donde hacen falta [############################] 98%   (sin skill 68%)
```

Para números reales de este repo: el ledger de arriba (0 marcadores) y los hallazgos de
"lean" de esta auditoría (-60.202 líneas posibles).

## No revisado

- `cognee/` (2.258 archivos `.py`, vendor/submódulo) y `.venv/` — fuera de alcance.
- Los 4.485 tests no se ejecutaron, solo se recogieron: el pase/fallo real de la suite
  no forma parte de esta auditoría.
- Contenido de los 306 pares byte-idénticos: se comparó byte a byte, no se leyó cada uno.
- Rutas de pago externas reales (IOL/PPI/Binance contra sus APIs): se verificó el código
  cliente y los contratos en tests, no se hicieron llamadas autenticadas.
- `android/`, `src-tauri/`, `installer/`, `Sprints/`, `docs/`.
- El frontend se midió en tamaño y tests, no se leyó componente por componente.
