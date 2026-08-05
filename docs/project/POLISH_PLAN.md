# OWNEX — PLAN DE PULIDO (detalles a pulir, priorizados)

Auditoría del 2026-08-04. Verificado contra el repo (no suposiciones).
Objetivo: dejar el proyecto sin deuda operativa y con CI determinista para
operar "a full" la semana próxima.

---

## P1 — CRÍTICO: Drift de árboles gemelos (core/ vs cores/)

**Hallazgo:** 32 archivos `.py` reales difieren entre `core/` y `cores/`
(scheduler, event_bus, opportunity, copilot/providers, knowledge, osint…).
El runtime importa de `core/`, pero la cobertura y tests también cubren
`cores/` (`--cov=cores --cov=core`). Dos fuentes de verdad → bugs por drift.

**Decisión pendiente (elegir UNA):**
- (A) Sincronizar `cores/` ← `core/` y quitar drift (duplicado mecánico).
- (B) Eliminar `cores/` y hacer que todo use `core/` ("Delete Don't Comment").
- (C) Marcar `cores/` como alias oficial a `core/` (solo init stub).

**Esfuerzo:** A es mecánico (cp + diff). B/C requieren revisar imports en
`apps/`, `api/`, tests y el Makefile (`--cov`, TEST_ARGS). Riesgo medio-alto.

**Precedente:** la veta de revenue ya sincroniza AMBOS (core+cores) cada vez;
el resto del repo no lo hace.

---

## P2 — ALTO: `make test` completo con fallos preexistentes

**Hallazgo:** `make test` (suite completa ~3000 tests) sale EXIT=2.
Fallos NO relacionados con la veta de revenue:
- `tests/test_desktop_release.py` → 4 errores.
- `tests/test_e2e_copilot.py` → 1 error.

**Acción:** root-cause y arreglar, o marcar xfail con justificación, para que
el gate de instalación esté 100% verde.

---

## P3 — ALTO: Tests de red no deterministas

**Hallazgo:** la suite emite 403/404/flakiness reales de fuentes externas
(BountyTargetsData 404, HackerOne 400, Bugcrowd 404, OpenBug 403) → el suite
no es reproducible offline. El target `test` dice "excluye network-flaky"
pero algunos se cuelan.

**Acción:** mockear/responses en los tests de scraper/oportunidad, o marcarlos
`@pytest.mark.network` y excluirlos del target `test` (solo correr en CI con
red). Resultado: suite determinista y rápida.

---

## P4 — MEDIO: Todo/impedancia de Playwright sensor

**Hallazgo:** en startup, `'Playwright' object has no attribute 'new_context'`
(np. falla, pero la capability solo/WebView está rota). Algo llama
`new_context()` que no existe en la API de Playwright instalada.

**Acción:** usar `playwright.async_api` / `browser.new_context()` o actualizar
la API correcta. Nos capitalizaría: el sensor de navegador sería real.

---

## P5 — MEDIO: Deuda de TODOs (123 en el repo)

**Hallazgo:** 123 `TODO/FIXME/HACK` repartidos (osint 7, scraper 6, hackerone 6,
vault 4, events 4, verify_system 4…). Viola "zero debt / delete don't comment".

**Acción:** barrido por módulo; cada TODO → tarea concreta, fix, o eliminado.

---

## P6 — BAJO: Config mágica / calidad

**Hallazgo (a confirmar en scan):** números mágicos, credenciales en `.env`,
duplicación de config (regla "Zero Magic" / "One Source of Truth").

**Acción:** mover a constantes/registry; revisar `.env.example`.

---

## P7 — Operativo: corrida backend limpia + instalación limpia
(ítems 4–6 de la lista previa, ya pendientes)

- Corrida secuencial del backend sin concurrencia para separar falsos fallos.
- Probar instalación limpia: `pip install -r requirements.txt` + `npm install`
  en un venv/dir vacío (garantiza el QUICKSTART).

---

## Priorización de ejecución

1. P1 (drift) — decide A/B/C antes de tocar. Máximo riesgo de romper imports.
2. P3 y P2 — CI determinista + gate verde, bloquean "instalar a full".
3. P4, P5 — mejoras de capital y limpieza.
4. P7 — verificación final del QUICKSTART.
5. P6 — deuda fina, continuo.

## Regla de oro
Cada cambio: ruff + mypy + pytest objetivo. Sincronizar core+cores cuando
toques archivos que existan en ambos árboles.