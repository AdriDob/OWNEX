# OWNEX 1.0 — camino real hasta `revenue_events >= 1`

> **Medido el 2026-10-04 contra APIs vivas, no inferido.** Estado verificado por
> ejecución, no por lectura de docs. Cuando el token llegue, este documento es el
> que dice qué falta.

---

## A. Estado actual

```
GITHUB_TOKEN              vacío  (en ~/.config/ownex/opportunity.env)
targets                     722
pipeline_runs             1.621
endpoints                  9.922
scan_runs                   378
missions                      6     ← del 2026-08-30, sin opportunity_id
cycle_opportunities           0    ← schema sin NINGÚN escritor
submission_records            0
revenue_events                0
revenue_payouts               0
```

## B. El primer punto bloqueado **NO es el token**

La premisa de partida era *"el bloqueo es `GITHUB_TOKEN`"*. Medido, es **el
último** de cuatro huecos:

```
#1. DISCOVERY   ¿hay una oportunidad real?        → ver C: SÍ, hay 4.424
#2. PREPARACIÓN ¿hay trabajo real preparado?      → NO. Todo lo que hay es fixture
#3. SUBMISSION  ¿se puede enviar?                 → NO. Requiere token + Human Gate
#4. PAGO        ¿se registra el resultado?         → NO. Requiere evidencia del pago
```

Con el token pegado y nada más, el loop **seguiría sin correr**: no hay
oportunidad admitida ni trabajo real que enviar.

### Los paquetes que existen son fixtures

`~/ownex/submissions/` contiene **1.351 paquetes**, todos de prueba:

| Prefijo | Cantidad | Contenido |
|---|---:|---|
| `deliv-1_*` | 968 | "Fix a public OSS issue" · `[Add implementation details here]` |
| `e2e-1_*` | 257 | "Fix login rate-limit bypass" · `reward_verified: $120.00` · `url: ""` |
| `wire-1_*` | 125 | idem |

Ninguno tiene implementación. El `$120.00` es un string del fixture, con la URL
vacía — no es un bounty verificado.

## C. Lo que SÍ funciona hoy, medido en vivo

**El discovery de bounties de GitHub funciona ahora mismo, sin token:**

```
GET https://api.github.com/search/issues?q=is:issue is:open label:bounty
  HTTP 200 · total_count = 4.424
    - "[radar] SN open bounty 2026-10-05T00:47"  labels=['radar','sn','bounty']
    - "Inflation Sprites and SFX"                  labels=['Bounty']
```

Y el código lo pide exactamente así:
`api/adapters/direct_work_github_bounty.py:200` → `GET {GITHUB_API_BASE}/search/issues`.
El token sólo sube el rate limit (10/min anónimo → 30/min con token). **No es lo
que habilita el discovery.**

## D. Lo que está roto, medido

Los adapters de discovery apuntan a endpoints muertos:

| Fuente | Endpoint que el adapter llama | Resultado real |
|---|---|---|
| IssueHunt | `api.issuehunt.io/v1/bounties` | **HTTP 404** — `Something went wrong with the request.` |
| Opire | `api.opire.dev/api/bounties` | **HTTP 404** — página de error |
| Algora | `console.algora.io/api/bounties` | **HTTP 200 pero devuelve HTML** (30 KB), no JSON |

**Ninguno de los tres puede devolver una oportunidad hoy.** Y todos los tests de
adapters usan mocks (`monkeypatch httpx.AsyncClient`), así que "discovery
funciona" nunca se probó contra el mundo real.

## E. Camino mínimo a `revenue_events >= 1`

Ordenado por dependencia, no por dificultad:

```
1. ADMITIR una oportunidad real
   Usar GitHub bounty discovery (funciona, §C). Elegir por probabilidad de
   completar el loop, NO por prestigio:
     · reward explícito y verificable en el body
     · sin barrieras: sin entrevista, portfolio, test técnico ni invitación
     · repo sano (no archivado, issues abiertas)
     · Argentina elegible
     · tech stack que ya manejo

2. PREPARAR trabajo real
   Sin placeholders. Un PR que resuelva el issue de verdad.

3. GITHUB_TOKEN  ← el owner lo pega
   Da rate limit para discovery + habilita el push.

4. HUMAN GATE — abrir el PR
   `PRBuilder.create_pr(..., require_approval=True)` exige `approval_token`
   de un solo uso. Irreversible ⇒ humano.

5. EVIDENCIA DE PAGO
   `record_bounty_paid(submission_id, amount_usd, payout_ref)` exige monto > 0
   y referencia. Sin evidencia devuelve `None` — nunca inventa.

6. `revenue_events = 1`  → OWNEX 1.0
```

**Los pasos 3-6 ya están codificados y testeados.** Los bugs que los rompían
(§56) están cerrados. Lo que falta es **contenido**: paso 1 y 2.

## F. Bugs de la cadena economics — CERRADOS (`KNOWN_DEBT #56`)

| Bug | Efecto si el owner pegaba el token |
|---|---|
| `raise ValueError` antes del adapter | el `needs_access` fail-closed era **código muerto** |
| `_get_api_key` sólo miraba `IdentityVault` | el token en `opportunity.env` era **ignorado** → DLQ tras 3 intentos |
| `status = SUBMITTED` incondicional | un envío fallido se registraba **como enviado** y no se reintentaba |

Guard: `tests/test_github_token_readiness.py` — 10/10, 3 mutaciones verificadas.

## G. Bloqueo actual: coordination, no capacidad

> El otro flujo está modificando **actualmente** el camino económico completo.

```
M api/adapters/direct_work_github_bounty.py     ← el discovery que funciona
M api/routers/revenue_app.py
M cores/direct_work_engine/{economics,models,filters,workbank,...}.py   (12)
M cores/revenue/ledger.py
M cores/revenue_multiplier/{models,metrics/}.py
M cores/revenue_tracker/execution_bridge.py      ← record_bounty_paid = EL GATE
M cores/opportunity/global_sources.py             ← el catálogo de 195 fuentes
?? cores/direct_work_engine/source_registry.py    ← el gate de admisión, nuevo
?? api/routers/economic_trajectory.py · cores/economic_trajectory/
```

`record_bounty_paid` —la única puerta a PAID— se está editando ahora mismo.
Por la regla de coordinación (megaprompt §13/§33) **este trabajo no entra ahí**
hasta que el otro flujo commitee.

## H. Qué NO se hace

- Arreglar los endpoints muertos de IssueHunt/Opire/Algora: fuera del camino
  mínimo. GitHub basta para el primer pago.
- Mover `product-map.md` ni consolidar los 15 overlaps: es Fase C, posterior a PAID.
- Migrar a OpenCode V2: no desbloquea el pago.

## I. Regla permanente

> *Una plataforma que responde 200 no es una plataforma que devuelve datos.*
> Y al revés: *un test con `monkeypatch(httpx)` no prueba que el discovery
> funcione* — sólo prueba que el código llama a `httpx`.

Un guard que merezca el nombre tiene que haber verificado una respuesta real
alguna vez. Los tres adapters muertos lo demostraron: 200 con HTML, y 404.