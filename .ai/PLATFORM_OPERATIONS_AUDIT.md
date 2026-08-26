# PLATFORM OPERATIONS AUDIT — Capacidades existentes vs gaps reales

> Auditoría previa a la implementación del Platform Operations Engine.
> Regla: NO duplicar motores existentes. Consolidar lo fragmentado.

---

## 1. LO QUE YA EXISTE Y SE REUTILIZA

### 1a. Platform Metadata / Knowledge

| Capacidad | Archivo | Estado | Notas |
|-----------|---------|--------|-------|
| Catálogo curado 139 fuentes | `cores/opportunity/global_sources.py` | ✅ COMPLETO | SourceDefinition con argentina_ok, requires_interview/portfolio/assessment, pay_range, payout_cadence_days, time_to_first_work_hours, entry_mechanism |
| Entry model matcher | `find_curated_entry_model()` en global_sources.py | ✅ | Devuelve hourly_rate_usd documentado, assessment bool, time_to_first_work |
| PLATFORM_ACCESS tiers | `cores/direct_work_engine/workbank.py:71-92` | ✅ | public/needs_api_key/needs_manual_setup por plataforma + requirement text |
| Payment accounts (76) | `cores/payment_compat/network.py` | ✅ COMPLETO | OwnAccount con layer/function/regions/currencies/methods/payout_ref |
| Payout methods AR | `cores/financial_intelligence/argentina_payout_methods.py` | ✅ | 55+ métodos con fees/reliability/limits |
| Payment Compatibility Engine | `cores/payment_compat/engine.py` | ✅ | evaluate() → compatible/viable/score/matches/off_ramp/honest_notes |
| Application Assistant catálogo | `core/application_assistant.py:51-105` | ✅ | 5 plataformas (outlier/mercor/alignerr/mindrift/fiverr) con pay_range, payout cadence, why |

### 1b. Playbooks / Steps (ya existen!)

| Capacidad | Archivo | Estado | Detalle |
|-----------|---------|--------|---------|
| Steps por plataforma | `core/application_assistant.py:_steps_catalog()` | ✅ PARCIAL | Outlier (6 pasos), Mercor (3), Alignerr (?), Mindrift (?), Fiverr (?) — cada paso tiene id/title/detail/est_minutes/fields |
| Setup checklist items | `core/setup/checklist.py:_catalog()` | ✅ | 10 ítems (profile_kit, payment_accounts, bounty_api_key, outlier_onboarding, mindrift_onboarding, freelance_profile...) |
| Guided onboarding lessons | `cores/onboarding/guided_system.py` | ✅ PARCIAL | Day 1-7 lecciones con contenido personalizado |

**GAP**: Solo 5 plataformas tienen steps detallados. Faltan playbooks para bug bounty platforms, OSS bounties, freelancer.

### 1c. Execution State Machine

| Capacidad | Archivo | Estado |
|-----------|---------|--------|
| ExecState (13 estados) | `core/execution_queue/models.py` | ✅ DISCOVERED→QUALIFIED→READY→QUEUED→EXECUTING→WAITING_HUMAN→SUBMITTED→VERIFICATION→PAID + REJECTED/BLOCKED/FAILED/DEAD_LETTER |
| Transitions validadas | `can_transition()` / `assert_transition()` | ✅ |
| MoneyState (40 estados) | `cores/capital/state_machine.py` | ✅ Unifica TruthLayer + RevenuePipeline + WorkBank + ExecQueue + AppAssistant |
| Human Gate | WAITING_HUMAN state + approve/reject endpoints | ✅ |

### 1d. Next Action Engine

| Capacidad | Archivo | Estado |
|-----------|---------|--------|
| UnifiedIncomePlan.build() | `cores/direct_work_engine/income_plan.py:63-117` | ✅ Rankea acciones por tier (deliver > bootstrap > EV/h) y retorna next_action |
| IncomeHome NEXT BEST ACTION | `frontend/src/pages/IncomeHome.vue` | ✅ Renderiza next_action con ev/h, payoff range, cash speed, assessment required |
| WorkBank ready_to_deliver queue | `workbank.best_ready()` + delivery endpoints | ✅ |
| Daily Companion | `cores/direct_work_engine/daily_companion.py` | ✅ briefing consolidado |

### 1e. Personal Performance / Learning

| Capacidad | Archivo | Estado |
|-----------|---------|--------|
| LearningRecord | `cores/direct_work_engine/feedback.py:31` | ✅ platform, category, accepted, amount, time_to_payout_days |
| apply_learning() | `feedback.py:41` | ✅ Actualiza platform_success_rates, category_success_rates, avg_time_to_payment |
| build_history_from_revenue_tracker() | `feedback.py:77` | ✅ Deriva records desde RevenueTracker real |
| RevenueTracker metrics per platform | `cores/revenue_tracker/revenue_tracker.py` | ✅ total_earnings, pending, by platform |
| EconomicMemory per-program ROI | `core/revenue/economic_memory.py` | ✅ orion_score, usd_per_hour from confirmed payouts |
| Calibration factor | `calibration.py` JSONL predicho-vs-real + platform_factor mediana clampada | ✅ |

**GAP**: No hay "Personal Platform Score" unificado que combine economics × acceptance × efficiency × reliability.

### 1f. Evidence

| Capacidad | Archivo | Estado |
|-----------|---------|--------|
| Evidence Composer | `cores/offensive/evidence_composer.py` o similar | ✅ Para findings de bug bounty |
| SubmissionRecord | `database/models.py:740-752` | ✅ report_id, platform, external_id, status, submitted_at |
| RevenueEvent audit log | `database/models_economic.py:190-198` | ✅ event_type, payload JSON, created_at |
| Capital Timeline | `cores/capital/timeline.py` | ✅ TimelineEvent con evidence_urls, tags, amount |

**GAP**: Evidence no está vinculado por-ejecución (solo por-finding). Falta screenshot+URL+metadata por step del workflow.

### 1g. Voice / Chat

| Capacidad | Archivo | Estado |
|-----------|---------|--------|
| Voice commands | `cores/voice/advanced_commands.py` + `command_executor.py` | ✅ Comandos estructurados (scan, submit, status) |
| Opportunity evaluator | `cores/voice/opportunity_evaluator.py` | ✅ Evalúa si vale la pena |
| TTS engine | `cores/voice/voice_engine.py` (Piper) | ✅ calm_operator personality |
| Copilot chat API | `/api/copilot/chat` | ✅ Con provider chain 24/7 |
| MERLIN interface | `frontend/src/pages/MerlinJarvis.vue` | ✅ Chat UI |

**GAP**: No hay conversación libre por voz conectada al copilot. El voice actual solo procesa comandos estructurados.

### 1h. Frontend surfaces

| Superficie | Archivo | Muestra |
|-----------|---------|---------|
| IncomeHome CEO Command Center | `IncomeHome.vue` | next_action, potencial HOY/SEM/QUINCENA/MES, esperado≠realizado |
| Application Assistant | ¿Page? | Plan de postulación con pasos |
| WorkBank radar | `DirectWorkRadar.vue` en MissionControl | Top pick, metas, ready_to_deliver |
| Trading Intelligence | `TradingIntelligence.vue` | Copy trading, scoring, DNA |
| Capital Dashboard | `Capital.vue` | 12 tabs (overview, runway, risk, allocation...) |
| Good Morning panel | `GoodMorning.vue` | Setup progress, important_tasks, opportunities |

---

## 2. GAPS REALES (lo que falta construir)

| # | Gap | Esfuerzo | Prioridad |
|---|-----|----------|-----------|
| G1 | **Platform Onboarding State persistente** — NOT_STARTED→REGISTERED→...→ACTIVE por plataforma, con detección automática de qué falta | S | P0 |
| G2 | **Playbooks adicionales** — extender `_steps_catalog()` para HackerOne/Bugcrowd/IssueHunt/Freelancer/Algora | M | P0 |
| G3 | **Submission Checklist generator** — pre-submit checklist por oportunidad (requirements ✓ tests ✓ evidence ✓ format ✓ deadline ✓ payment ✓) derivado del playbook | M | P0 |
| G4 | **Personal Platform Score** — fórmula única que combine opportunity_economics × personal_acceptance × efficiency × payment_reliability; neutral si insufficient_data | M | P1 |
| G5 | **Platform Ranking** — "¿En qué plataforma me conviene trabajar AHORA?" rankeando por effective $/h con personal history | S | P1 |
| G6 | **Staleness detection** — marcar VERIFIED/RECENT/STALE/UNKNOWN en metadata de plataformas con timestamps | S | P1 |
| G7 | **Platform detail page** — vista frontend con entry/readiness/current_opportunity/now/next/payment/risk/history + Open Playbook | M | P1 |
| G8 | **Voice conversacional** — conectar copilot chat a STT/TTS pipeline para charla libre | S | P2 |
| G9 | **Change detection** — detectar cambios en eligibility/payment/rules entre scans | M | P2 |
| G10 | **Evidence por-ejecución** — vincular screenshot/artifact a cada step del execution queue | M | P2 |

---

## 3. DUPLICACIONES A CONSOLIDAR

| Duplicación | Solución |
|-------------|----------|
| Application Assistant steps vs Setup Checklist items vs Guided Onboarding lessons | Todos apuntan a las mismas plataformas. Consolidar: ApplicationAssistant._steps_catalog() es el SSOT de playbooks; checklist y onboarding referencian esos steps. |
| MoneyState vs ExecState | MoneyState ya mapea EXEC_STATE_TO_MONEY_STATE. Usar MoneyState como canónico. |
| PLATFORM_ACCESS en workbank vs global_sources SourceDefinition | Ambos definen barrier/access. Usar global_sources como metadata SSOT; workbank referencia. |

---

## 4. CONTRATOS EXISTENTES

| Contrato | Endpoint(s) | Formato |
|----------|------------|---------|
| Income plan | GET `/applications/income-plan` | `{next_action, phases{now,this_week,waiting}, tracks{active,passive}, income_command_center}` |
| Application plan | GET `/api/applications/plan` | `{platforms:[{key,name,url,status,steps:[{id,title,detail,done,est_minutes}]}]}` |
| WorkBank | GET `/direct-work/workbank` | `{items[], targets{}, weekly_best[]}` |
| Payment compat | POST `/payment-compat/evaluate` | `{compatible,viable,score,matches[],off_ramp[],missing[],honest_notes[]}` |
| Execution Queue | POST `/execution-queue` + transitions | `{item_id,state,payload,history}` |
| Revenue summary | GET `/revenue/summary` | `{total_earned,pending_amount,by_platform,usd_per_hour}` |
| Copilot chat | POST `/copilot/chat` | `{response,provider,model}` |
| Voice assistant | POST `/voice/assistant` | `{worth_it,score,reasoning,suggested_action}` |

---

## 5. PLAN DE IMPLEMENTACIÓN (orden mínimo)

### Slice 1 — PlatformOnboardingEngine (G1 + G2)
- Extender `ApplicationAssistant` con estados de onboarding persistentes
- Agregar playbooks para las plataformas faltantes
- Exponer readiness % + next missing step

### Slice 2 — Submission Checklist (G3)
- Generator que produce checklist desde playbook + opportunity
- Endpoint `GET /platform/{key}/submission-checklist?opp={id}`

### Slice 3 — Personal Score + Ranking (G4 + G5)
- `compute_personal_platform_score()` en economics.py (SSOT)
- `rank_platforms_for_user()` que responde "¿dónde trabajo ahora?"

### Slice 4 — Staleness + Change Detection (G6)
- Timestamps en metadata + `get_freshness()` helper
- Alert cuando info > N días sin verificar

### Slice 5 — Frontend Platform Detail (G7)
- Vista con NOW/NEXT/PAYMENT/RISK/HISTORY + Playbook expandible
- Integrar en IncomeHome o nueva ruta `/platform/:key`

---

*Generado: 2026-08-26 | Basado en lectura de código real*
