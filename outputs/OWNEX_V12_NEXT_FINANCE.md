# OWNEX V12 - FASE 0: Revenue Ledger y Financial Hub Report

**Generated:** 2026-11-09T19:49:52.356561

## Revenue Ledger Structure
The Revenue Ledger strictly separates:

### Categories (Non-overlapping)
- **Potencial** - Opportunities with expected value but not yet realized
- **Proyección** - Forecasted based on trends and pipelines
- **Estimación** - Rough calculations without firm basis
- **Aprobado** - Human-gate approved opportunities
- **Pendiente** - Awaiting human gate decision
- **Pagado** - Money actually received
- **Retirado** - Abandoned or cancelled opportunities
- **Verificado** - Independently confirmed income

### Money Separation Rule
⚠️ El dinero cobrado debe estar separado del dinero potencial.

### Movement Records
Each financial movement must have:
- Importe (float, no hardcoded ARS quotes)
- Moneda (USD, EUR, ARS, etc. with source + timestamp)
- Fecha (ISO format)
- Origen (adapter_name, platform, manual_action)
- Destino (bank_account, crypto_wallet, payment_method)
- Tipo (bonus, payout, referral, refund, fee)
- Estado (pending, completed, failed, refunded)
- Comisiones (float, percentage or fixed amount)
- Evidencia (URL, receipt, transaction ID)
- Verificación (bool, human-verified flag)

⚠️ No utilizar cotizaciones ARS hardcodeadas para operaciones reales.
⚠️ Las cotizaciones deben incluir fuente y timestamp.

## Financial Hub Status
- ✅ Structure defined with 8 categories
- ✅ Movement schema designed
- ❌ Integration with human gate: pending
- ❌ Real-time tracking: pending
- ✅ Test coverage: 60/60 tests passing

## FASE 1 Priorities
- [ ] Human gate → Revenue Ledger integration
- [ ] Track: submissions/day, approvals/day, approval rate
- [ ] Implement currency with source+timestamp
- [ ] Build dashboard: potential vs approved vs paid separation
- [ ] P0 task: Measure baseline revenue (manual-only month prior)

## FASE 2+ Actions
- Deploy automated payout tracking
- Integrate with bank APIs (where authorized)
- Build crypto wallet payout tracking
- Implement expense categorization
- Create SLA breach alerts for human gate
