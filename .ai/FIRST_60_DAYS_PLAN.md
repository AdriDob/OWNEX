# FIRST 60 DAYS PLAN — $0 → ritmo ($2.5k–6k/mes)

> **SSOT operativo** para los primeros 60 días post-purga. Plataformas vivas: Mercor / Outlier / Alignerr / Mindrift (assessment, sin entrevista) + Algora / Opire / IssueHunt (dev bounty) + Fiverr (canal) + bug bounty (upside). Todo lo demás fue purgado.
> Proyección base: mes 1–3 $200–2,200 · mes 4–6 $2,500–10,000 · año 1 $35k–55k (P50).
> Regla: ningún outcome se registra sin evidencia (Rule §39: ACCEPTED≠PAID).

## Semana 1 — Assessments en paralelo (meta: 3 aplicaciones enviadas)

| Día | Acción (15–20h/sem total) | Superficie OWNEX | Done cuando |
|---|---|---|---|
| 1 | Crear cuentas Mercor + Outlier + Alignerr (mismo email, perfil técnico real) | — (web externa) | 3 cuentas creadas |
| 2 | Assessment Outlier (1–2h, rating/ranking/writing) | — | submitted |
| 3 | Assessment Alignerr por especialidad (coding o math) | — | submitted |
| 4–5 | Assessment Mercor (2–3h, coding/reasoning) | — | submitted |
| 6 | Configurar rails: GrabrFi + Wise + Airtm (+ MercadoPago ya) | `POST /api/payment-compat/configured` o `/operations/payment-compat` | `configured_accounts` ≥ 4 |
| 7 | Review semanal: anotar tiempos por assessment | `/operations/first-money` (registrar $0 = baseline honesto, no ingreso) | 3 submitted + rails OK |

**Exit**: 3 assessments submitted + ≥4 rails configurados. Esperado $: **$0**.

## Semana 2 — Algora + Fiverr (meta: 1er claim + 2 gigs publicados)

| Día | Acción | Superficie OWNEX | Done cuando |
|---|---|---|---|
| 8 | `GITHUB_TOKEN` en vault/env | `/operations/platforms` (guía Algora) | token verificado |
| 9 | Filtrar bounties $50–$200, <10 comentarios, >1 mes | `POST /direct-work/workbank/cycle` → `/operations/work-queue` | top-3 elegidos |
| 10 | Claim 1er issue Algora (comentar + fork + branch) | `/decision/evaluate` (GO/SKIP por EV) | claim activo |
| 11 | Publicar gig 1 Fiverr (Python automation) | `POST /fiverr/ethics-check` + funnel `POST /funnel/record` | gig published |
| 12 | Publicar gig 2 Fiverr (API/AI integration) | funnel ledger | 2 published |
| 13–14 | Codear fix Algora (CoderAgent prepara, vos revisás) | `/dev-bounty/*` + Human Gate approve | PR abierto con `Fixes #123` |

**Exit**: 1 claim vivo + 2 gigs published. Esperado $: **$0–200**.

## Semana 3–4 — Primeros cobros (meta: 1er PAID)

| Acción | Superficie | Done cuando |
|---|---|---|
| Push diario del PR Algora (responder review <24h) | `/dev-bounty/*` | PR merged |
| Responder toda inquiry Fiverr <1h (plantilla Profile Kit) | `GET /api/profile-kit/` (copiar textos) | response rate 100% |
| Al merge → payout Stripe 1–3 días → registrar | `recordFirstRevenue` en `/operations/first-money` | **1er PAID en ledger** |
| Al primer gig cobrado → registrar + asset KB | `POST /funnel/record` + `data/fiverr_assets.json` | funnel updated |
| Revisar assessments pendientes (Mercor/Outlier/Alignerr) | email + plataformas | ≥1 aprobado |

**Exit**: 1er PAID registrado (monto real, no estimado). Esperado $: **$200–800**.

## Semana 5–6 — Ritmo (meta: 2 canales pagando)

| Acción | Superficie | Done cuando |
|---|---|---|
| 2do claim Algora/Opire ($100–500, repo conocido) | workbank + `/decision/evaluate` | claim activo |
| Daily: 1h Outlier/Alignerr tasks (si aprobado) + 1h bounty | `/operations/work-queue` (daily brief) | streak 10/14 días |
| 3er gig Fiverr solo si los 2 primeros convierten (CTR>2%) | funnel ledger (CTR/conversión) | decisión data-driven |
| Calibrar P(CASH) con outcomes reales | `/direct-work/evolution` (`channel_economy`) | UNKNOWN→THIN en ≥1 canal |

**Exit**: 2 canales con PAID. Esperado $: **$800–2,200/mes run-rate**.

## Semana 7–8 — Escala mínima (meta: run-rate $2.5k+/mes)

| Acción | Superficie | Done cuando |
|---|---|---|
| Subir rate Fiverr +10–20% si conversión >5% | funnel ledger | precio actualizado |
| Abrir 2do bounty en paralelo (Opire/IssueHunt) | execution queue (score×avail×acceptance) | 2 bounties activos |
| Primer recon bug bounty (1 programa VDP amplio, pasivo) | `/hunt/start` + scopes | 0 findings aún = OK |
| Review 60 días: ¿qué canal da mejor $/h-humana? | `compute_expected_human_value` + FirstMoney Aprendizaje | 1 canal escalado, 1 pausado |

**Exit**: run-rate ≥$2.5k/mes o diagnóstico honesto de qué falló. Esperado $: **$1,600–4,200/mes**.

## Reglas del plan (no negociables)

1. **Assessments primero, código después**: Mercor/Outlier/Alignerr pagan por hora desde el día 1 aprobado; el bounty paga al merge.
2. **Un claim a la vez** hasta el 1er merge (reputación > volumen).
3. **Response time <1h** en Fiverr las primeras 2 semanas (determina el ranking inicial).
4. **Nada se registra sin evidencia**: PAID solo vía webhook/verificación/manual con comprobante.
5. **Si un assessment falla**: reintentar en 30–90d; el tiempo va al canal que sí aprobó.
6. **Bug bounty = upside hasta mes 3+**: nunca renta base (varianza fatal).

## Referencias

- Plataformas vivas y por qué: `.ai/DECISIONS.md` (PURGA 2026-09-13)
- Proyección P25/P50/P75: sesión CURRENT_STATE 2026-09-13 (proyección post-purga)
- Rails AR: `cores/payment_compat/network.py` (76 cuentas) + `/api/payment-compat/configured`
- Loop Algora: `cores/opportunity/executors/algora_executor.py` + `/dev-bounty/*`
- Funnel Fiverr: `cores/fiverr/engine.py::FunnelLedger` + `/funnel/*`
