# Opportunity Engine vNext — ESPECIFICACIÓN (no implementar todavía)

> **Estado**: SPEC v1 — diseño aprobado para lectura. Ningún cambio de código
> deriva de este documento hasta que cada sección tenga evidencia de gap real
> (Agent Loop: auditar → clasificar → solo EXTEND/NEW justificado).
> **Idea central**: OWNEX no busca trabajos. Busca **problemas solucionables con
> dinero asociado** y los convierte en acciones ejecutables.

---

## 0. Principio rector

```
PROBLEMA VERIFICABLE + RECOMPENSA VERIFICABLE + ELEGIBILIDAD VERIFICABLE
  → PREPARACIÓN AUTOMÁTICA → HUMAN GATE → EJECUCIÓN → COBRO → APRENDIZAJE
```

Todo lo que el spec propone reutiliza lo existente:
`Opportunity` (`cores/direct_work_engine/models.py:469`) — que el §0-B
declara **contrato único**, no una taxonomía más —,
`LegacyOpportunityDweAdapter` (`api/adapters/legacy.py:29`, el wrapper que ya
convierte todo a `Opportunity`),
`WorkItem` (`workbank.py:162`, estados `preparing|ready_to_deliver|needs_access|delivered`),
`calibrate()` + `p_accept_estimate()` (`feedback.py`), modos del recommender
(`secure_income`, `near_guaranteed`, `high_upside_90d`, `jackpot`),
`submit_gate()` (`cores/auto_submit/submit_gate.py`), `money_loop` + `factory`
en mission overview. **Nada de esto se reescribe.**

## 0-A. Posicionamiento: el motor no piensa como hunter

El producto puede llamarse como sea (Hunter u otro), pero el motor piensa en:

> **capacidad técnica disponible → problemas pagables verificables.**

Bug bounty, AI evaluation, OSS, QA, DevOps son **sabores del mismo objeto**
(§0-B), no productos distintos. "Sin experiencia profesional" es un **filtro**
del engine, no una limitación del producto: el sistema busca problemas
pequeños, concretos, verificables, pagables y ejecutables por una persona
técnicamente competente sin historial formal.

## 0-B. Opportunity Contract v1 (P0-1: lo primero que existe)

**Un solo contrato universal.** Todos los adapters
(`OutlierAdapter`, `MindriftAdapter`, `AlgoraAdapter`, `HackerOneAdapter`, …)
convierten su información a esta misma estructura vía el patrón
`LegacyOpportunityDweAdapter`. Prohibido crear `AIopportunity`,
`OSSOpportunity`, `BountyOpportunity` paralelos.

```text
Opportunity {                       # físico: models.Opportunity (EXTEND, no nuevo)
    source, title, type, category, url
    reward, currency, reward_model   # reward_model: hourly | fixed | per_unit | bounty
    estimated_minutes, time_to_cash
    experience_required              # NONE | UNKNOWN | REQUIRED
    interview_required               # NONE | UNKNOWN | REQUIRED
    assessment_required + count      # 0 | 1 | >1 (+ difficulty/duration/cost: existen)
    portfolio_required               # existe
    country_access                   # VERIFIED | CONDITIONAL | UNKNOWN (deriva de allowed_countries)
    payment_access                   # VERIFIED | UNKNOWN (deriva de payment_compat rails)
    ai_policy                        # ALLOWED | LIMITED | PROHIBITED | UNKNOWN — NUEVO (§8)
    automation_level                 # ALLOWED | RESTRICTED | UNKNOWN — NUEVO (§1)
    competition, difficulty
    personal_fit, p_cash, p_acceptance            # DERIVADOS (scorer + calibrate)
    expected_net_cash, expected_net_cash_per_hour # DERIVADOS (economics)
    status                           # DISCOVERED…PAID (pipeline §8)
}
```

Campos NUEVOS reales: solo `ai_policy` y `automation_level`. Todo lo demás
ya existe como campo o como derivado. Si un adapter no puede llenar un campo
→ `UNKNOWN` visible, jamás inventado.

---

## 1. AI work (Mindrift / Outlier / Alignerr / micro1 y similares)

- Fuentes: extender `global_sources.py` + `source_registry.py` (patrón ya usado
  para OpenAI/Anthropic/Microsoft AI). Cada fuente nace `UNVERIFIED` + probe.
- `application_assistant.py` ya guía 5 plataformas: EXTENDER con assessment
  prep-packs (qué evalúan + respuestas sugeridas desde Profile Kit + tracking).
- Task-drop watcher: job scheduler que detecta tareas nuevas y notifica con
  fit-score. **Jamás auto-claim, jamás auto-assessment.**
- **Niveles de automatización por adapter** (un ban optimiza ingresos a cero):
  `AUTOMATION_ALLOWED | AUTOMATION_RESTRICTED | AUTOMATION_UNKNOWN`.
  Regla dura: `UNKNOWN → NO AUTO-ACTION` (solo lectura + notificación humana).
  Verificar ToS de polling/scraping/bots por plataforma antes de subir de nivel.
- Gate `secure_income` ya prioriza P(cobro); calibrar con outcomes reales.

## 2. Paid OSS (Algora, GitHub Sponsors, LFX y otras)

- `AlgoraExecutor` ya cierra claim→PR. Gap: polling merge→payout registrado.
- Nuevas fuentes solo con URL 200 verificada por probe (regla permanente).
- `repeatability` solo >0 con ventas/pagos reales (regla `asset_factory`).

## 3. Open-source issues (bugs, tests, integrations, migrations, docs, DevOps, AI)

- Taxonomía de familias (Software / AI / Security / Infraestructura, §5).
- Cada issue se modela como **problema**, no como empleo: recompensa,
  dificultad, criterios de aceptación claros, competencia observable.
- `plan_execution()` ya genera roadmap + EV; EXTENDER con `acceptance_criteria`.

## 4. Security (bug bounty + security fixes + hardening)

- Sin cambios: reasoners + submit_gate + repro harness + chain_analyzer +
  `money_loop` ya operan. vNext solo les **envía mejores candidatos**
  (problemas con impacto medido) y **recibe outcomes** para calibrar.

## 5. Company problems (cualquier tarea verificable con recompensa)

- Definición de entrada (las 3 deben ser verificables, no declaradas):
  1. recompensa observable (monto + medio de pago),
  2. criterio de aceptación observable (tests, review, merge),
  3. vía de acceso observable (URL pública, API, programa).
- Si falta una → la oportunidad vive como `UNKNOWN`, jamás como promesa.

## 6. Eligibility engine (EXTEND `Opportunity`, no nuevo modelo)

Campos ya existentes a reutilizar: `experience_required`, `interview_required`,
`technical_test_required`, `allowed_countries`, `payment_method`,
`assessment_difficulty/duration_min/cost_usd`. Agregar solo lo ausente:

```
EXPERIENCE:    NONE | UNKNOWN | REQUIRED       (→ experience_required)
INTERVIEW:     NONE | UNKNOWN | REQUIRED       (→ interview_required)
ASSESSMENT:    0 | 1 | >1                       (→ technical_test_required + count)
ARGENTINA:     VERIFIED | CONDITIONAL | UNKNOWN (→ allowed_countries + probe)
PAYMENT:       VERIFIED | UNKNOWN               (→ payment_compat rails reales)
AI-ASSISTANCE: ALLOWED | RESTRICTED | UNKNOWN   (→ nuevo; ver ToS por plataforma)
```

Regla: `UNKNOWN` filtra o etiqueta según modo (`secure_income` filtra,
`high_upside_90d` etiqueta). Nunca se inventa elegibilidad.

## 7. Economic engine (EXTEND `economics.py` + `feedback.py`, no nuevo motor)

Por oportunidad, siempre derivado, nunca inventado:

```
EXPECTED NET/HOUR = (reward × p_accept_slice − fees) / human_hours_est
TIME TO CASH      = payout_cadence observada (None = UNKNOWN)
P(CASH)           = p_accept_estimate(technique, program) — None hasta datos
REPEATABILITY     = calibrate() verdict (UNKNOWN/THIN/MEASURED)
```

**Corrección anti-precision-falsa:** `published_rate` JAMÁS equivale a
`personal_realized_rate`. Hasta tener resultados propios, la tarjeta muestra:

| Métrica                  | Estado           |
| ------------------------ | ---------------- |
| Publicado por plataforma | $X/h             |
| Elegibilidad             | VERIFIED/UNKNOWN |
| Assessment               | Sí/No            |
| Trabajo disponible       | UNKNOWN          |
| Horas asignadas          | UNKNOWN          |
| Aceptación               | UNKNOWN          |
| Cobro                    | $0               |
| Rate personal            | UNKNOWN          |

**Corrección Algora:** montos en oportunidades NO reclamadas son
`OPPORTUNITY VALUE`, nunca `EXPECTED CASH`. Pasan a cash solo tras
claim → work → PR → merge → payout → PAID (con evidencia en cada paso).

**Corrección bounty:** bug bounty NO es sueldo; es UPSIDE financiado por el
cashflow de AI work. Y ninguna plataforma se asume estable: **cada una se
calibra individualmente** (el motor debe poder descubrir `Outlier → 0` y
reasignar solo a `Mindrift → 2` + `OSS → 1 merge`).

Métrica reina: **NET CASH / HUMAN HOUR medido** (ya en mission overview).
Toda cifra sin outcomes lleva etiqueta HIPÓTESIS.

**Orden de financiación entre carriles:** AI WORK genera cashflow semanal que
financia tiempo en OSS/DEV; SECURITY es upside (nunca renta base hasta PAID
repetido). Los 3 carriles corren en paralelo — el usuario no elige uno, el
motor reparte la hora diaria por EV medido.

## 8. Execution preparation (EXTEND workbank + daily_loop, Human Gate intacto)

```
WorkItem.preparing → ready_to_deliver (OWNEX prepara todo)
  → needs_access (falta algo humano: assessment, credencial, claim)
  → delivered (humano ejecutó) → PAID solo con evidencia
```

Prohibido automatizar: claims que aceptan ToS, assessments, postulaciones con
identidad, envíos finales, cobros. Todo eso es `needs_access` + 1 clic humano.

**Distinción obligatoria (dos caminos distintos):**
- OSS / bug bounty: `prepare submission → HUMAN REVIEW → HUMAN APPROVE → submit`.
- Plataformas AI (`task → work → evaluation → submit`): verificar **qué
  asistencia de IA permite cada proyecto** antes de asistir. Política por
  proyecto en el contrato (§0-B):

```text
AI_POLICY: ALLOWED | LIMITED | PROHIBITED | UNKNOWN
```

Si es `UNKNOWN` → OWNEX NO asume automatización permitida (solo organiza y
prepara material observable). Un ban por asistencia indebida destruye el canal.

## 9. Personal calibration (ya existe: alimentar, no reconstruir)

`calibrate()` + `p_accept_estimate()` + `money_loop.funnel` + `ChannelEconomics`.
El trabajo es **generar outcomes** (10→THIN, 30→MEASURED), no más matemática.
Tras 30–50 outcomes el sistema responde con la tarjeta objetivo:

```text
AI security · attempts 7 · valid 3 · unique 2 · accepted 2 · paid 1
cash $750 · human hours 18.4 · NET CASH/HOUR $40.76 · time-to-cash 21d
```

## 10. Commercial extraction (límite explícito post-MVP)

- Decidido: **Desktop con licencia** (Ed25519 existente), cliente hunters/devs USD.
- Precios (Scout $0 / Hunter $19/mes / Anual $149 / Lifetime $349) son
  **HIPÓTESIS DE TEST**, no pricing definitivo. La Fase 0 valida antes del billing.
- El test de precio mide el funnel completo, no una pregunta:
  `visitor → understand → demo → profile → opportunity → click PRO →
  price selected → email` (más señal que "¿pagarías $19?").
- "Publicar gratis" = MVP infra-gratis + variables cubiertas por clientes
  (MoR fee por venta, sin costos fijos propios).
- Lo genérico y desacoplado (formato Opportunity, scoring, gates, funnel) es lo
  único extraíble a futuro — sea extending desktop tiers o SaaS separado.
- Nada se extrae antes de: (a) funcionar en el monorepo, (b) tener outcomes que
  lo validen, (c) quality gate del portfolio (BUILD+TESTS+DOC+LICENSE+sin secretos).

---

## ANEXO A — Tarjeta de oportunidad canónica (lo que ve el humano)

```text
ISSUE #4812 "Add missing OAuth refresh tests"
Reward $150 · Difficulty LOW · Time ~2h · Expected net/hour $75
EXPERIENCE NONE · INTERVIEW NO · ASSESSMENT 0 · ARGENTINA VERIFIED
PAYMENT VERIFIED · Competition 3 · Acceptance criteria CLEAR
Action: [Prepare] [Approve] [Reject]   ← preparar es auto, aprobar es humano
```

## ANEXO B — Ética operativa (límites duros, sin excepción)

1. **Nunca falsificar**: experiencia, identidad, credenciales, evaluaciones, autoría.
2. **Nunca automatizar lo prohibido**: assessments por el humano, claims con ToS,
   postulaciones con identidad, bypass de verificaciones (ID, cámara, biometría).
3. **Asistencia sí, suplantación no**: OWNEX prepara, redacta, organiza y calcula;
   el humano rinde, firma y envía.
4. **Evidencia o silencio**: sin prueba de recompensa/elegibilidad → UNKNOWN visible.
5. **Un ban destruye el canal**: ante duda de ToS, `needs_access` + consulta humana.

## ANEXO C — Presupuesto y prioridad de implementación (cuando se apruebe código)

- Máximo **2 archivos nuevos** por sección; resto EXTEND.
- Máximo **20 tests** por sección; reutilizar fixtures (`_make_finding`, workbank tmp).
- Orden por ROI/evidencia (corrige el orden anterior):
  - **AHORA (P0):** §0-B Contract → §6 eligibility → §8 ai_policy →
    §7 personal cash/hour model → cola de revisión unificada (existe: extender).
  - **P1:** §1 assessment prep + task watcher → §2 claim→PR→merge→PAID →
    §4 hunt→submission→PAID → notificaciones unificadas.
  - **P2:** §10 packaging → landing → pricing experiment → billing/MoR →
    license issuance → installer → distribución.
  - **Después:** §9 calibration → allocation automática → analytics comercial → team.
- §4 y §9: **cero código** (alimentar con outcomes, no reconstruir).
