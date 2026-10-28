
## Sesión 2026-10-05 — CONSOLIDACIÓN CERRADA + 2 P0 (bypass de auth, promoter muerto)

> **PEDIDO OWNER:** "todo" — commit de la deuda, los 85 rojos, y la deuda abierta (#32/#33/#30/`/oar/doctor`).
> **VEREDICTO: la deuda de 4 días estaba bloqueada por el hook, no olvidada.** Al validarla aparecieron **2 P0 de producto** que ningún diff delata. Commit `4daef0f9` (354 archivos) + push.

### Los 2 P0 (ninguno visible en un diff)

**1. Bypass de auth en 51 rutas.** `AuthMiddleware._register_mounted()` guardaba el path **con plantilla** (`/workbank/{item_id}/deliver/approve`) y el dispatch lo comparaba contra el path **concreto** (`/workbank/1/…`): nunca coinciden ⇒ la rama "asset o SPA route" se los llevaba y pasaban **sin credencial**. Medido en vivo, anónimo: `GET /mobile/reject/1` → **405** (llegó al router) vs `GET /today` → 401. Afectaba `POST /mobile/approve/{id}` y `POST /mobile/reject/{id}`. Fix: matchear `route.path_regex`, indexado por primer segmento literal. 15 tests nuevos + a prueba de fallo.

**2. El flujo validation → Finding estaba muerto.** `promoter.promote()` usaba `ConfidenceEngine().evaluate(result)` — alias de `ConfidenceScorer`, cuyo `calculate()` exige 3 args — con **un** arg ⇒ `TypeError` en cada llamada. `ValidationEngine.run()` tenía la misma llamada. **Estaba oculto porque los 11 tests que lo probaban figuraban como "baseline conocido" en #36: eran el spec de un módulo sin implementar.** Fix: `ConfidenceScore.from_validation_result()` (pesos explícitos que suman 1.0; sin baseline/probes ⇒ 0 con gap explícito). Promoter y engine usan la misma función.

### El rojo era ruido de medición, no de producto

**104 → 30.** No eran 104 bugs: 26 tests median 401 por no autenticar contra root-mounted · 19 heredaban `no such table` porque dos fixtures hacían `drop_all` **sin filtro** y dejaban la base sin tablas (pasan aislados) · 3 heredaban 403 por un `os.environ.pop` sin teardown · el resto fijaban contratos ya decididos en otro sentido. Cada uno se arregló contra la API real, **no creando funciones para satisfacer al test**.

### Por qué la consolidación llevaba 4 días sin commitear

**No era olvido: el hook la rechazaba.** `.pre-commit-config.yaml` corre `ruff`, `ruff-format`, `pytest` (fast) y `frontend-build`. 31 violaciones de ruff bloqueaban el commit — y **2 eran bugs reales**: `__all__` de `reward_probability.py` declaraba `EXTERNAL_REWARD_PRIORS` y `RewardPrior`, que no existen ⇒ `import *` reventaba.

Corregido de paso: `make check` **no** corre ruff pese a que AGENTS.md lo describe así. Y `git commit` con archivos unstaged hace que el hook los stashee y su restore es de fiar **NO** — perdió `promoter.py` completo (277→11 líneas) y 4 `VulnType`. Recuperado y documentado en KNOWN_DEBT #73.

### Verificación

```
suite serial completa   6176 passed · 30 failed · 0 errors
make check              fast 103 passed / 1 skipped  (baseline INTACTO)
ruff + ruff-format      156 archivos: All checks passed
vue-tsc                 exit 0
vite build              OK 13.25s
import api.main         BOOT OK, 1728 rutas
```

### Verificado y YA cerrado (no tocar)

- **`/oar/doctor` tiene consumidor vivo**: `router/index.ts:60` → `UnifiedChat.vue:616` → `ProviderHealthPanel.vue:138`. El item de CURRENT_STATE que decía "0 consumidores" quedó viejo.
- **#33** lo cerró el flujo concurrente en `a355001b`/`9b9712c2` (39 endpoints + guard).

### Pendiente owner

1. **Validación física Windows/Android (W1–W12)** → veredicto STABLE. Nada de lo de esta sesión se medió en hardware real.
2. **Los 30 rojos restantes**: triados por causa en KNOWN_DEBT #36/#71/#72. `secure_income`(5), `opportunity_cycle`(4), resto 1-2 — son de domina complemento, no de los 2 P0.
3. **Decidir Code4rena / Immunefi** (KNOWN_DEBT #71): adapter escrito, cableado en ningún registro. ¿carril vivo o se borra? Los tests ahora affirmations su ausencia y avisan si alguien los cablea.
4. `ConfidenceEngine = ConfidenceScorer` sigue siendo un alias mentiroso (`confidence.py:235`): borrarlo cuando se migrate el dominio viejo.
# Session Checkpoint — Agosto 2026

> v7.7.7 — SESIÓN 2026-10-01 (**CIERRE FINAL DE PRODUCCIÓN**): **4 endpoints que devolvían 500 con credencial válida → 200**, 5 stubs "for backward compatibility" implementados, y un bug que perdía findings en silencio. La sesión anterior había declarado `NOTIFY-EVERYTHING` DONE con 16/16 verdes y el código nunca aterrizó (commit `a0e11ac1` con `add -A` se lo llevó). Verificado midiendo, no leyendo. Detalle: `.ai/CURRENT_STATE.md` + `.ai/DECISIONS.md` 2026-10-01.
> **Verificación:** suites tocadas **440/440** · `make test-fast` **103/1** (intacto) · suite serial completa **5845 passed · 85 failed · 0 errors** · ruff limpio en 30 archivos · `import api.main` OK · a prueba de fallo 2 veces.
> **Los 85 rojos restantes NO son de esta sesión** (triage archivo por archivo en KNOWN_DEBT #36): 6 baseline documentado · 13 drift del flujo concurrente · 9 contaminación de orden (pasan aislados) · 3 red.
> **Pendiente owner:** commit+push (371 entradas sin commitear, mayormente del flujo concurrente), validación física Windows W1–W12 → veredicto STABLE.

> v7.7.7 — SESIÓN 2026-09-14 (re-aplicada): **CONSOLIDACIÓN FINAL — `core/` ELIMINADO** (656 archivos; verificación completa 0 refs `core.`; Makefile+orion/priority migrados antes del borrado; un flujo paralelo lo revirtió al comitear y fue re-aplicado + re-verificado). Deuda barrida: test_orion_core (`event_type`), test_daily_brief fixture + `save_brief` acepta dict (bug real del job scheduler), dead code eliminado en brief.py. Features de sesión ya commiteadas por el flujo paralelo: HelpCenter+AlertsCenter+/api/help/*+/api/alerts/sweep+plan diario, purga de plataformas low-value. Verificación: fast 102/1, api.main OK, suites afectadas verdes, ruff limpio. Detalles: `.ai/DECISIONS.md`/`CURRENT_STATE.md`/`KNOWN_DEBT.md` 2026-09-14. **Pendiente owner**: commit+push, validación física Windows W1–W12 → veredicto STABLE.

> v7.7.7 — SESIÓN 2026-09-10: UNIVERSAL FUNNEL WIRING (Phase 6-9) + MOBILE GAP (3 reasoners) + MOBILE ON-DEVICE (validador) cerrados + pusheados. Siguiente: validación física Windows W1–W12 → veredicto STABLE. Ver `.ai/CURRENT_STATE.md` sesiones "MOBILE ON-DEVICE", "MOBILE GAP" y "UNIVERSAL FUNNEL WIRING".
