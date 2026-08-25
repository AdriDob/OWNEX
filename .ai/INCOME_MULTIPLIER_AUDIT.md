# INCOME MULTIPLIER AUDIT — FASE 0 (diagnóstico, sin implementar)

> Fecha: 2026-08-25 · HEAD: post v1.0.0-alpha · Método: código ejecutable = autoridad #1.
> Alcance: matriz del sistema económico actual, gaps vs modelo canónico objetivo, plan por fases.

## 1. Matriz de sistemas existentes

| Sistema | Archivo | Propósito | Usado | SSOT | Estado |
|---|---|---|---|---|---|
| **economics.py** | cores/direct_work_engine/economics.py | ÚNICO contrato EV + TaskAvailability Known/Unknown | Recommender + EVScorer delegan (spy test) | ✅ SSOT | **IMPLEMENTADO** (`b21c3b62`) |
| ZeroBarrierScorer | cores/direct_work_engine/scoring.py:23-133 | Score continuo 15 factores | Recommender, WorkBank gate ≥60 | ✅ | IMPLEMENTADO |
| IntelligentRecommender | recommendation.py | Ranking multi-modo (balanced/fast_income/max_success) | API /recommend, workbank | ✅ | IMPLEMENTADO |
| EVScorer (discovery) | autonomous_discovery.py | EV por hora para ranking discovery | Delegaa economics ✅ | parcial | IMPLEMENTADO (priors etiquetados) |
| StrictFilter | filters.py:25-54 | Hard-reject ×5 (pago<\$2, unpaid≥4h, no-remote, gift-card, proceso excesivo) | WorkBank daily_cycle | ✅ | IMPLEMENTADO |
| PaymentCompatibilityEngine | cores/payment_compat/engine.py | Cobrabilidad pre-ejecución AR/global | recommender ×(compat/100) piso 0.3 | ✅ | IMPLEMENTADO |
| CASH_SPEED_FACTORS | max_daily_income.py:42-89 | Velocidad de caja por categoría | ultra_fast mode | ✅ | IMPLEMENTADO (+6 aliases muertos a limpiar) |
| Work Bank | workbank.py | Acumula ready_to_deliver; PLATFORM_ACCESS honesto | daily_cycle cron 06:15 + UI | ✅ | IMPLEMENTADO |
| UnifiedIncomePlan | income_plan.py (409L, concurrente) | Agrega deliver+first-day+applications → UN plan | CLI next_action + income-plan endpoint | ✅ nuevo | IMPLEMENTADO (revisar tests) |
| next_action CLI | scripts/next_action.py + cores/orion/next_action.py | "Qué hago ahora" desde terminal | usuario | ✅ | IMPLEMENTADO |
| ApplicationAssistant | core/application_assistant.py | Postulación Outlier/Mercor/Alignerr/Mindrift/Fiverr paso-a-paso | UI + overview.next_action | ✅ | IMPLEMENTADO (0% pasos hechos aún) |
| FeedbackLoop | direct_work_engine/feedback.py | Solo outcomes TERMINALES (accepted/paid) pliegan perfil | acceptance_probability | ✅ nunca inventa | IMPLEMENTADO |
| RevenueTracker | cores/revenue_tracker/revenue_tracker.py | Payouts reales; PaymentStatus | usd_per_hour, feedback | ✅ | PARCIAL (ver gap G4) |
| BarrierLevel | models.py:156-160 | VERY_LOW/LOW/MEDIUM/HIGH (**sin ZERO ni EXPERT**) | scorer._determine_barrier_level | ⚠️ | PARCIAL |
| UltraFast mode | ultra_fast_income.py (default BALANCED) | cash_speed≥0.85, targets 500/día | max_daily_income | ✅ | IMPLEMENTADO |

## 2. GAPS vs modelo canónico objetivo (prompt §3-13)

| ID | Gap | Evidencia | Severidad |
|---|---|---|---|
| G1 | **p(task_available) sin señal real** — Unknown explícito existe en economics pero NINGÚN adapter la provee | rg task_available → solo economics | ALTA (ya mitigada: no se asume 1.0, se marca UNKNOWN) |
| G2 | **BarrierProfile explicativo ausente** — hay score pero no "por qué es zero barrier" factor-por-factor | scoring genera reasoning genérico, no checklist §7 | MEDIA |
| G3 | **Estados de pipeline incompletos**: falta DISCOVERED/QUALIFIED/IN_PROGRESS/SUBMITTED/REJECTED como máquina formal | revenue_tracker solo ACCEPTED/PAID; WorkBank usa ready_to_deliver/needs_access propios | ALTA (contabilidad honesta §10) |
| G4 | **CashDelay/ExpectedCashDate no proyectado por oportunidad** | payment_compat da score pero no fecha; argentina_payout_methods tiene días por método sin conectarse a forecast | MEDIA |
| G5 | **AI-training sub-categorías no separadas** (DATA_ANNOTATION vs AI_EVALUATION vs RLHF…) | taxonomía canónica tiene AI_EVALUATION/DATA_ANNOTATION pero rates/availability UNKNOWN | BAJA (data-curation) |
| G6 | **HumanTimeAdjustedROI compuesto no existe como campo único** (ingredientes sí: EV, acceptance, compat; falta fórmula agregada versionada) | — | MEDIA |
| G7 | **Automation multiplier por oportunidad no medido** (execution_planner estima human_minutes pero no se pliega al ranking) | execution_planner.py existe desconectado del scorer | MEDIA |
| G8 | **Calibration loop de predicción**: feedback pliega outcome pero no registra prediction_error (predicho vs real \$h) | feedback.py guarda amount/time, no comparación contra EV predicho | MEDIA (§13) |
| G9 | **Fallbacks automáticos**: recommender rankea pero no emite primary/fallback#1..#3 con triggers de degradación | — | BAJA |
| G10 | **Confidence engine**: EVScorer tiene confidence ad-hoc (0.5+bonos); unificado en economics? No | autonomous_discovery:240-252 | BAJA |

## 3. Lo que NO se tocará (ya correcto)

- Regla "nunca inventar tasas": priors cold-start 0.5 documentados; curated tables fuera del ranking.
- Separación potential/expected: MoneyValue kinds + EV parcial con warning UNKNOWN.
- Seguridad económica §39: auto-submit requiere TrustEngine + aprobación humana (diseño vigente).
- Gen3 stack intacto.

## 4. Plan por fases (checkpoints separados, orden ROI×feasibility)

| Fase | Entregable | Gap que cierra | Est. |
|---|---|---|---|
| **A. Pipeline states + cashflow** | enum OpportunityStage (8 estados §10) en revenue_tracker + mapeo WorkBank; ExpectedCashDate = payout_method.days desde payment_compat | G3,G4 | M |
| **B. BarrierProfile explicativo** | barrier_factors dict por oportunidad (registration/interview/portfolio/experience/capital/geo booleans del modelo existente) + texto generado; BarrierLevel gana ZERO (score≥85 ∧ 0 flags verificados) | G2 | S-M |
| **C. HumanTimeAdjustedROI + automation fold-in** | economics.compute_htroi() versionado v1: numerador=EV·accept·avail(if known)·compat·confidence; denominador=human_hours+qualification_hours; automation_ratio desde execution_planner plegado al ranked output | G6,G7 | M |
| **D. Prediction calibration** | feedback.record_outcome compara EV predicho vs real → data/learning/calibration.jsonl + ajuste multiplicativo por plataforma (clamp 0.5-2.0) | G8 | M |
| **E. Confidence engine SSOT** | economics.confidence(): source_reliability·freshness·history·missing_fields | G10 | S |
| **F. Fallbacks + estrategia personalizada** | recommend() emite {primary, fallbacks[3]} con triggers; strategy FAST_INCOME/LONG_TERM según perfil horas/país | G9 | S |
| **G. Frontend**: Income Command Center v2 consume todo lo anterior (MoneyValue kinds + StatusBadge ya listos) | §18-20 | L |
| **H. Data curation AI-training subcategorías** | global_sources entries con rates source="platform" documentadas | G5 | M (research) |

## 5. Riesgos
- WIP concurrente activo en economics/models/scoring/result_based → fases A-D requieren coordinación/rebase antes de editar esos archivos.
- No romper contratos API existentes (/recommend, /income-plan, /workbank) — additive only.

## 6. Orden inmediato propuesto (próximo checkpoint)
Fase A (states+cashflow) → B (barrier explicativo) → C (HTROI). Cada una con test-first y commit atómico.
