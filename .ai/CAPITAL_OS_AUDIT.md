# CAPITAL_OS_AUDIT.md — Auditoría de sistemas de capital existentes en OWNEX

> **Regla 0**: Antes de implementar nada, auditar lo existente. Este documento mapea cada sistema relacionado con capital/payouts/revenue/income/wealth en el repositorio.

---

## 1. CAPITAL SSOT (Single Source of Truth)

### EXISTENTE: `cores/financial/truth_layer.py` ✅ PRODUCTION-READY
- **TruthLayer**: deriva estado financiero del ledger (append-only)
- **ValueCategory**: VERIFIED_REAL, PENDING, ESTIMATED, MANUAL_INPUT, UNKNOWN ✅
- **FinancialState**: verified_balance, pending_balance, withdrawn_balance, estimated_balance, manual_balance, disputed_balance
- **Propiedades derivadas**: `real_balance` (solo VERIFIED_REAL), `effective_balance` (verified + pending)
- **SyncHealth**: HEALTHY/DEGRADED/STALE/FAILED/NEVER_SYNCED
- **Confianza por fuente**: external_api=1.0, synced_cache=0.8, manual=0.6, estimate=0.3, seed=0.05
- **PlatformFinancialState**: por plataforma con verified/pending/withdrawn/estimated
- **Resumen**: items con label, amount, category, confidence, detail

### EXISTENTE: `cores/financial/dashboard.py` ✅ PRODUCTION-READY
- **get_dashboard()**: patrimonio_total, breakdown (bounty, crypto, takenos, atlas), liquidez, ingresos mes, objetivo libertad, precios, alertas
- **Patrimonio total**: crypto + platforms + takenos + atlas
- **Liquidez**: disponible/congelado/pendiente (con fórmulas de disponibilidad)
- **Ingresos mes**: desde ledger (últimos 30 días)
- **Objetivo Libertad**: meta $30k con progreso %
- **_get_atlas_total()**: usa factory get_configured_engine() con guard asyncio

### EXISTENTE: `/api/financial/capital/snapshot` ✅ IMPLEMENTADO
- Endpoint unificado en `api/routers/financial_truth.py:279`
- Consolida: bounty payouts, workbank, investment, atlas, crypto, expected_cash, payment_compat
- Usa `get_dashboard()` + truth_layer + workbank + investment + payment_compat

---

## 2. MONEY STATE MACHINE

### EXISTENTE: TruthLayer categorización ✅
- **Categorías**: VERIFIED_REAL, PENDING, ESTIMATED, MANUAL_INPUT, UNKNOWN
- **Regla**: state siempre derivado del ledger, nunca almacenado directo
- **PAYOUT_RECEIVED** → VERIFIED_REAL
- **BOUNTY_PENDING/APPROVED** → PENDING
- **BOUNTY_CREATED** → ESTIMATED
- **WITHDRAWAL_COMPLETED** → VERIFIED_REAL (withdrawn)
- **MANUAL_INPUT** → MANUAL_INPUT

### EXISTENTE: Revenue Pipeline states ✅
- `REVENUE_SUBMISSION_STATUSES`: draft, submitted, under_review, triaged, resolved, bounty_paid, rejected, informative, duplicate, closed
- **Solo PAID incrementa realized_income** (en pipeline: status == "bounty_paid")

### EXISTENTE: PayoutRecord status ✅
- `status`: "confirmed" | "pending"
- **Solo "confirmed" cuenta en revenue_summary()**

### ⚠️ GAP: No hay state machine unificada DISCOVERED→EXPECTED→PREPARED→SUBMITTED→REVIEWING→APPROVED→VERIFIED→PAID
- Existen estados dispersos en: TruthLayer, RevenuePipeline, PayoutRecord, WorkBank, ApplicationAssistant
- No hay validación de transiciones ilegales entre sistemas

---

## 3. CAPITAL SOURCES (Integraciones de payout methods)

### EXISTENTE: `cores/payment_compat/engine.py` ✅ PRODUCTION-READY
- **PaymentCompatibilityEngine**: evalúa si OWNEX puede cobrar un payout
- **Criterio**: method → region → currency → available accounts → compatible?
- **Regla de honestidad**: documentación requerida (llc/us_entity/us_residency/eu_residency/uk_entity) → incompatible con razón explícita
- **Cuentas configuradas**: persistidas en `~/.config/ownex/payment_network.json`
- **Enriquecimiento**: `payout_ref` → metadatos Argentina Payout Methods (reliability, fees, limits)
- **evaluate_chain()**: receive + off-ramp a ARS

### EXISTENTE: `cores/payment_compat/network.py` ✅
- **76 cuentas** en 5 capas: banking, processors, crypto, self_custody, withdrawal
- **Funciones**: primary, us_account, global, payout, local, backup, specialized
- **Incluye**: GrabrFi, Global66, Airtm, Takenos, DolarApp, Belo, Payoneer, Wise, AstroPay, MercadoPago, Revolut, N26, Paysera, ZEN, Deel, Remote, Airwallex, WorldFirst, remesas, Wallbit, bancos AR (Galicia, Santander, BBVA, Nación, Provincia, Ciudad, HSBC, ICBC, Macro, Supervielle, Comafi, Credicoop), exchanges (Binance, Kraken, Coinbase, OKX, Bybit, Bitget, Crypto.com), rampas AR (Bitso, Lemon, Belo, Buenbit, Ripio, SatoshiTango, Fiwind, Decrypto), autocustodia (MetaMask, Rabby, Trust, Safe, Phantom, Ledger, Trezor, Exodus, Coinbase/OKX Wallet)

### EXISTENTE: `cores/financial/takenos.connector.py` ✅
- Takenos connector con get_summary(), get_state(), health()

### EXISTENTE: Crypto sync manager ✅
- `cores/crypto/sync_manager.py` - wallets EVM/BTC/Solana/Tron/exchange/WalletConnect

### ⚠️ GAPS:
- **No hay conectores reales para la mayoría de bancos/processors** (solo catálogo)
- **No hay sync automático de balances** de cuentas bancarias/processors (solo crypto + takenos)
- **PayPal, Wise, Payoneer, etc.** están en catálogo pero sin sync real
- **No hay webhook/polling** para pagos entrantes en cuentas bancarias

---

## 4. CAPITAL DASHBOARD

### EXISTENTE: `/api/financial/capital/snapshot` ✅
- Consolida: bounty, workbank, investment, atlas, crypto, expected_cash, payment_compat
- **Gap**: No incluye liabilities, runway, cashflow velocity, forecasting

### EXISTENTE: `/api/revenue/capital-dashboard` ✅
- `RevenueMetrics.capital_dashboard()`: payout_summary, finding_pipeline, hot_targets, program_ranking, platform_speed, economic_memory

### EXISTENTE: `IncomeHome.vue` (CEO Command Center) ✅
- **Next Best Action** con EV/h, payoff range, cash speed, assessment required, zero experience
- **Ingreso potencial**: HOY/SEMANA/QUINCENA/MES con basis note (sin probabilidades inventadas)
- **ESPERADO ≠ REALIZADO**: Cobrado / Pendiente / 30d (desde /payment-tracker + /revenue/summary)
- **Automation**: qué hace OWNEX / Human Actions: cola this_week
- **Active Stack**: plataformas con rate documented, status

### EXISTENTE: `Capital.vue` ✅
- 7 tabs: overview, progressive-scaling, targets, programs, pipeline, platforms, settings
- KPIs: Capital Total, USD/Hora, Findings, Targets, Tasa Aceptación, Programas
- Hot Targets, Program Ranking, Pipeline, Platform Speed
- Settings: minEV, auto-refresh, notificaciones

### ⚠️ GAPS:
- **No hay runway engine** (monthly burn, essential/discretionary, runway days)
- **No hay capital allocation engine** (recomendaciones de asignación)
- **No hay risk engine** (concentration, liquidity, platform, counterparty, currency)
- **No hay income diversification tracking** (top source %, top 3 %)
- **No hay time-to-cash engine** por oportunidad
- **No hay capital forecasting** (P10/P50/P90)
- **No hay capital timeline** auditable
- **No hay capital journal** (decisiones + outcomes)

---

## 5. REVENUE / PAYOUT SYSTEMS

### EXISTENTE: `core/revenue/pipeline.py` ✅
- **RevenuePipeline**: finding → report → submit → sync payouts → record payout
- **Estados**: draft → submitted → under_review → triaged → resolved → bounty_paid → rejected
- **sync_platform_payouts()**: sync_earnings() → _record_payout() → ledger event + financial:payout_received
- **record_payout()**: manual entry → PayoutRecord + ledger event + financial:payout_received
- **revenue_summary()**: total_payouts, total_earned, pending_payouts, pending_amount, active_submissions, by_platform

### EXISTENTE: PayoutRecord model ✅
- platform, amount, currency, program, external_id, submission_record_id, status (pending/confirmed), paid_at

### EXISTENTE: RevenueEvent (audit log) ✅
- event_type, payload JSON, created_at

### EXISTENTE: FinancialSyncScheduler ✅
- `cores/financial/scheduler.py`: sync_platforms() cada 30 min → persiste en PayoutRecord con dedupe por external_id

### ⚠️ GAPS:
- **No hay webhook real** para pagos entrantes (solo polling cada 30 min)
- **No hay payment tracker real** (payment_tracker.py tiene webhook stub)
- **No hay sync de balances bancarios** (solo crypto + takenos + bounty platforms)

---

## 6. INCOME / WORK BANK

### EXISTENTE: WorkBank ✅
- **WorkBank**: descubre → filtra zero-barrier → prepara → almacena (JSON persistente)
- **daily_cycle()**: filtra strict + success_floor → prepara deliverables → ready_to_deliver / needs_access
- **Targets**: daily=10, weekly=100, monthly=1000
- **PLATFORM_ACCESS**: public / needs_api_key / needs_manual_setup
- **Entrega asistida**: prepare/approve delivery → mark_delivered → feedback loop

### EXISTENTE: DirectWorkEngine ✅
- **Discovery**: adapters (opire, issuehunt, freelancer, bugbounty, etc.)
- **Scoring**: ZeroBarrierScorer (15 factores, suma 1.0, enablers/blockers/reasoning)
- **Recommendation**: IntelligentRecommender con configs (balanced/fast_income/max_success)
- **Feedback loop**: apply_learning() desde RevenueTracker → platform_success_rates, category_success_rates

### EXISTENTE: Income Plan ✅
- **UnifiedIncomePlan**: FirstDayGuide + WorkBank + ApplicationAssistant
- **Tracks**: Active (First-Day + WorkBank) + Passive (AI-training applications)
- **Ranking**: Tier 0 (entrega lista) > Tier 1 (bootstrap) > Tier 2 (EV/h descendente)
- **Income Command Center**: today/week/fortnight/month con basis note
- **Expected cash / HTROI / confidence** en NextBestAction

### EXISTENTE: ApplicationAssistant ✅
- 5 plataformas: Outlier, Mercor, Alignerr, Mindrift, Fiverr
- Steps con detail/url/est_minutes, status tracking

---

## 6. INVESTMENT / WEALTH

### EXISTENTE: InvestmentManager ✅
- `core/investment/manager.py`: strategies deploy/pause, drawdown protection (15%), high-risk cap 25%
- Adapters: ccxt, freqtrade, hummingbot, polymarket, alpaca/ibkr, aave/lido/morpho/pendle, forex, futures, sports, memecoin, sentiment, onchain, quant
- **get_snapshot()**: total_value, strategies

### EXISTENTE: Trading Engine ✅
- `core/trading/`: copy_trading (masters, drawdown), trader_intelligence (scoring, backtest, discovery), reasoning (StrategyDNA, DecisionCorrelator, AutoParamOptimizer)
- **Freqtrade adapter**: config generation, download-data, backtest, hyperopt, dry-run
- **TradingIntelligence.vue**: 3 tabs (Copy Trading / Trader Intelligence / Strategy DNA)

### EXISTENTE: Atlas (Financial Intelligence) ✅
- `apps/atlas/`: Binance/Kraken/Coinbase/Yahoo/CSV/Freqtrade/Hummingbot connectors
- PortfolioEngine con get_configured_engine() factory

### ⚠️ GAPS:
- **No hay capital allocation engine** (qué hacer con capital disponible)
- **No hay runway engine** (burn rate, runway days)
- **No hay risk engine** (concentration, liquidity, platform, counterparty)
- **No hay income diversification tracking**
- **No hay forecasting** (P10/P50/P90)

---

## 7. EXECUTION QUEUE (NUEVO)

### EXISTENTE: `core/execution_queue/` ✅
- **State machine**: 13 estados (DISCOVERED→QUALIFIED→READY→QUEUED→EXECUTING→WAITING_HUMAN→SUBMITTED→VERIFICATION→PAID + REJECTED/BLOCKED/FAILED/DEAD_LETTER)
- **Transitions validadas**: `can_transition()`, `assert_transition()`
- **ExecutionQueueStore**: JSON atómico, history, transitions validadas
- **API Router**: `/api/execution-queue` (CRUD + transitions)
- **Scheduler jobs**: process_queue (1min), retry_failed (15min), move_to_dlq (hourly)
- **Driver**: process_queue → route to executor (browser/coder/assisted/freelancer/opire/issuehunt/algora/mindrift/outlier/autonomous)
- **Transitions**: QUEUED→EXECUTING→WAITING_HUMAN/SUBMITTED→VERIFICATION→PAID
- **Human gate**: WAITING_HUMAN para acciones que requieren aprobación
- **Payout event**: financial:payout_received al llegar a PAID

---

## 8. FRONTEND STATE

### EXISTENTE: IncomeHome.vue ✅
- NextBestAction con expected_cash/htroi/confidence_band
- Expected ≠ Realized band (cobrado/pendiente/30d)
- Automation + Human Actions
- Active Stack con rate_documented

### EXISTENTE: Capital.vue ✅
- 7 tabs, KPIs, Hot Targets, Program Ranking, Pipeline, Platform Speed
- Settings tab (checkboxes funcionales con v-model)

### ⚠️ GAPS FRONTEND:
- **No hay runway display** (burn, runway days, alertas)
- **No hay risk score display**
- **No hay capital allocation recommendations UI**
- **No hay forecasting display** (P10/P50/P90)
- **No hay capital timeline** (auditable)
- **No hay capital journal** (decisiones + outcomes)
- **No hay runway alerts** en mobile/watch
- **Mobile/Watch**: sin capital display específico

---

## 9. RESUMEN DE ESTADO POR REGLA

| Regla | Estado | Evidencia |
|-------|--------|-----------|
| 1. Capital SSOT | ✅ COMPLETO | TruthLayer + Dashboard + /capital/snapshot |
| 2. Money State Machine | ⚠️ PARCIAL | Categorías OK, falta state machine unificada cross-system |
| 3. Capital Sources | ⚠️ PARCIAL | Catálogo completo (76), sync real solo crypto/takenos/bounty |
| 4. Capital Dashboard | ✅ COMPLETO | /capital/snapshot + IncomeHome + Capital.vue |
| 5. Capital Velocity | ❌ FALTA | No hay daily/weekly/biweekly/monthly income velocity |
| 6. Runway Engine | ❌ FALTA | No monthly_burn, runway_days, alerts |
| 7. Capital Allocation | ❌ FALTA | No allocation engine con recommendations |
| 8. Risk Engine | ❌ FALTA | No concentration/liquidity/platform/counterparty risk |
| 9. Income Diversification | ❌ FALTA | No tracking top_source %, top 3 |
| 10. Income+Capital Engine | ⚠️ PARCIAL | WorkBank→RevenueTracker existe, falta Capital Allocation |
| 11. ROI del Tiempo | ⚠️ PARCIAL | EV/h en Income Plan, falta verified_income/h |
| 12. Time-to-Cash | ⚠️ PARCIAL | expected_cash existe, falta por oportunidad |
| 13. Opportunity Capital Value | ❌ FALTA | No OCV formula implementada |
| 14. Goal Engine | ❌ FALTA | No goal tracking con required_monthly/estimated_date |
| 15. Capital Forecasting | ❌ FALTA | No P10/P50/P90 forecast |
| 16. Reality Engine | ⚠️ PARCIAL | TruthLayer calibration existe, falta forecast accuracy tracking |
| 17. Capital Rules Engine | ❌ FALTA | No rules engine configurado |
| 18. Human Gates | ✅ COMPLETO | WAITING_HUMAN en execution queue, approve/reject en UI |
| 19. Mobile Capital | ❌ FALTA | No capital display en mobile |
| 20. Watch Capital | ❌ FALTA | No capital display en watch |
| 21. Capital Alert Engine | ❌ FALTA | No alert engine para capital |
| 22. Premium Frontend | ⚠️ PARCIAL | Capital.vue/IncomeHome OK, falta runway/risk/allocation UI |
| 23. Capital Timeline | ❌ FALTA | No timeline auditable |
| 24. Capital Journal | ❌ FALTA | No journal de decisiones |
| 25. Security | ⚠️ PARCIAL | Ledger/TruthLayer OK, falta audit específico capital |
| 26. Testing | ⚠️ PARCIAL | Tests unitarios existen, falta E2E capital flow |
| 27. Observability | ⚠️ PARCIAL | Logs/ledger OK, falta métricas capital-specific |
| 28. Data Integrity | ✅ COMPLETO | TruthLayer rules, ledger append-only, reconcile() |
| 29. Offline/Recovery | ⚠️ PARCIAL | JSON stores survive restart, falta replay-safe para capital |
| 30. Documentation | ⚠️ PARCIAL | CURRENT_STATE/DECISIONS OK, falta CAPITAL_OS_ARCHITECTURE |

---

## 10. RIESGOS CRÍTICOS IDENTIFICADOS

### 🔴 CRÍTICO
1. **No hay state machine unificada** - riesgo de doble contabilización (EXPECTED contado como REAL)
2. **No hay runway** - riesgo de quedarse sin cash sin alerta
3. **No hay risk engine** - concentración de ingresos/platform no visible
4. **No hay capital allocation** - capital idle sin dirección

### 🟡 MEDIO
5. **No hay forecasting** - decisiones basadas en esperanza no en datos
6. **No hay capital sources sync real** - balances bancarios desconocidos
7. **No hay forecasting/forecast accuracy** - Reality Engine incompleto

### 🟢 BAJO
8. **Mobile/Watch capital UI** - UX incompleta
9. **Capital timeline/journal** - auditoría limitada

---

## 11. RECOMENDACIÓN DE PRIORIDAD (ORDEN DE IMPLEMENTACIÓN)

### P0 - CRÍTICO (Semana 1-2)
1. **Unified Money State Machine** - unificar TruthLayer + RevenuePipeline + WorkBank + ExecutionQueue en una sola state machine con transiciones validadas
2. **Runway Engine** - monthly_burn (essential/discretionary), runway_days, alerts CRITICAL/WARNING/HEALTHY/STRONG
3. **Capital Allocation Engine** - KEEP_CASH/RESERVE/REINVEST/INVEST/DEBT_REDUCTION/GOAL_FUNDING con rationale
4. **Risk Engine** - concentration/liquidity/platform/counterparty/currency/crypto/income/opportunity/debt → RISK_SCORE 0-100

### P1 - ALTO (Semana 3-4)
5. **Capital Forecasting** - P10/P50/P90 usando historical paid + volatility + pipeline + time-to-cash
6. **Runway Alerts** - CRITICAL<1m, WARNING<3m, HEALTHY>=3m, STRONG>=6m
6. **Capital Allocation UI** - recommendations con rationale/amount/expected_impact/risk/confidence
7. **Runway Alerts UI** - en Capital.vue, IncomeHome, Mobile, Watch
8. **Risk Score UI** - en Capital.vue, IncomeHome, Mission Control

### P2 - MEDIO (Semana 5-6)
9. **Capital Forecasting UI** - P10/P50/P90 en Capital.vue + IncomeHome
10. **Income Diversification UI** - top source %, top 3, recommendations
10. **Time-to-Cash per Opportunity** - en WorkBank/Income Plan
11. **Opportunity Capital Value** - formula OCV en Income Plan ranking
11. **Goal Engine** - required_monthly/estimated_completion_date con Conservative/Base/Aggressive
12. **Reality Engine Integration** - forecast_accuracy, calibration tracking
12. **Capital Rules Engine** - IF/THEN rules configurables

### P3 - BAJO (Semana 7+)
13. **Capital Timeline** - timeline auditable con click→evidencia
14. **Capital Journal** - timestamp/inputs/decision/reason/confidence/user_action/result
15. **Mobile Capital** - Net Worth, Available, Income Today/7d, Pipeline, Runway, Risk, Alerts, Next Action
16. **Watch Capital** - Capital, Today, 7d, Runway, Risk, Alerts críticos
16. **Capital Alert Engine** - MONEY/RISK/GOALS/OPPORTUNITY con prioridades
17. **Mobile/Watch Alerts** - push notifications
17. **Capital Timeline UI** - click→evidencia
18. **Capital Journal UI** - timestamp/inputs/decision/reason/confidence/user_action/result
19. **Premium Frontend Polish** - skeleton loading, empty/error states, microinteracciones
20. **Security Audit Capital** - secrets, encryption, logs, PII, auth
21. **E2E Capital Flow Tests** - income discovered → paid → ledger → capital → allocation → mobile → watch
22. **CAPITAL_OS_ARCHITECTURE.md** - documentación completa
23. **Capital Timeline UI** - click→evidencia
24. **Capital Journal UI** - decisiones + outcomes

---

## 12. ARCHIVOS CLAVE A MODIFICAR/CREAR

### Nuevos módulos core:
- `cores/capital/state_machine.py` - Unified Money State Machine
- `cores/capital/runway.py` - Runway Engine
- `cores/capital/allocation.py` - Capital Allocation Engine
- `cores/capital/risk.py` - Risk Engine
- `cores/capital/forecasting.py` - Capital Forecasting (P10/P50/P90)
- `cores/capital/goals.py` - Goal Engine
- `cores/capital/rules.py` - Capital Rules Engine
- `cores/capital/timeline.py` - Capital Timeline
- `cores/capital/journal.py` - Capital Journal
- `cores/capital/alerts.py` - Capital Alert Engine
- `cores/capital/diversification.py` - Income Diversification
- `cores/capital/forecasting.py` - Capital Forecasting
- `cores/capital/velocity.py` - Capital Velocity
- `cores/capital/time_to_cash.py` - Time-to-Cash Engine
- `cores/capital/opportunity_value.py` - Opportunity Capital Value
- `cores/capital/rules.py` - Capital Rules Engine
- `cores/capital/reality.py` - Reality Engine integration

### Nuevos routers API:
- `api/routers/capital.py` - Capital SSOT endpoints
- `api/routers/runway.py` - Runway endpoints
- `api/routers/allocation.py` - Allocation recommendations
- `api/routers/risk.py` - Risk score endpoints
- `api/routers/forecasting.py` - Forecasting endpoints
- `api/routers/goals.py` - Goals endpoints
- `api/routers/timeline.py` - Capital Timeline
- `api/routers/journal.py` - Capital Journal
- `api/routers/alerts.py` - Capital Alerts

### Frontend nuevo/actualizado:
- `Capital.vue` - agregar runway, risk, allocation, forecasting tabs
- `IncomeHome.vue` - agregar runway, risk, forecasting en Income Command Center
- `MissionControl.vue` - risk score, runway alerts
- `MobileCompanion.vue` - capital display + alerts
- `WatchCompanion.vue` - capital minimal + alerts críticos
- Nuevos componentes: RunwayCard, RiskScoreCard, AllocationRecommendationCard, ForecastCard, GoalCard, TimelineCard, JournalCard, AlertCard

### Scheduler jobs nuevos:
- `runway_check` (daily)
- `risk_assessment` (daily)
- `capital_forecast` (daily)
- `capital_alerts` (hourly)

### Tests nuevos:
- `tests/test_capital_state_machine.py`
- `tests/test_runway_engine.py`
- `tests/test_allocation_engine.py`
- `tests/test_risk_engine.py`
- `tests/test_forecasting.py`
- `tests/test_goals.py`
- `tests/test_diversification.py`
- `tests/test_time_to_cash.py`
- `tests/test_capital_timeline.py`
- `tests/test_capital_journal.py`
- E2E: `tests/test_capital_flow_e2e.py`

---

## 13. DECISIONES ARQUITECTÓNICAS PENDIENTES

1. **¿State machine unificada en core/ o cores/?** → usar `cores/capital/` como SSOT (patrón DWE)
2. **¿Forecasting en core/capital/ o core/revenue/?** → `cores/capital/forecasting.py` (usa datos de revenue + truth + workbank)
3. **¿Risk engine en core/capital/ o core/risk/?** → `cores/capital/risk.py` (capital-specific)
4. **¿Capital Allocation en core/capital/ o core/investment/?** → `cores/capital/allocation.py` (decide sobre capital disponible, no inversión)
5. **¿Runway en core/capital/ o core/financial/?** → `cores/capital/runway.py` (capital-specific)
6. **¿Forecasting usa ML o estadística simple?** → estadística simple (historical paid + volatility + pipeline), ML solo si hay datos suficientes
7. **¿Alert engine en core/alerts/ o core/capital/alerts.py?** → `cores/capital/alerts.py` (capital-specific)

---

## 14. PRÓXIMO PASO INMEDIATO

**Crear `cores/capital/state_machine.py`** - Unified Money State Machine que unifica:
- TruthLayer.ValueCategory
- RevenuePipeline submission statuses
- PayoutRecord.status
- WorkBank WorkItem.status
- ExecutionQueue.ExecState
- ApplicationAssistant status

Con transiciones validadas, categorías VERIFIED_REAL/EXPECTED mutuamente excluyentes, y tests que previenen doble contabilización.

---

*Generado: 2026-08-25 | Basado en auditoría de código real (no docs)*