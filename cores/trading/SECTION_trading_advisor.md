# how OWNEX uses TradingAdvisor + Backtest (calibration surface)

> **Fuente de verdad**: `cores/trading/advisor.py` (TradingAdvisor) y `cores/trading/backtest.py` (run_backtest/parameter_sweep/BacktestConfig/run_backtest/BacktestConfig).
> Estado: **ACTIVE (handoff 2026-09-13)** — turnos advisor + advisor, 27 pruebas tocadas (12 advisor + 13 backtest + 12 advisor_fallback se ejecutaron todos en verde), ruff limpio.

## Propósito
El advisor OAR propone ajustes de parámetros de trading con **Human Gate**:
1. `TradingAdvisor.propose(metrics, config)` → si hay OAR disponible (`cores/ai/runtime` → `_propose_via_oar`) genera propuestas con confianza; si no → fallback rule-based.
2. Las propuestas se persisten en `cores/trading` store como `AdvisorProposal` sin aplicar.
3. El humano aprueba/rechaza vía API; el advisor nunca aplica sin gate.

## Contrato JSON de OAR
```json
[
  {"param":"position_sol","current_value":0.1,"proposed_value":0.05,
   "reason":"drawdown 33% > daily loss limit","confidence":0.5},
  ...
]
```
Parser con tolerancia: markdown code fences, llaves incompletas, hasta 3 propuestas por respuesta (cap defensivo).

## Fallbacks
| Escenario | Path |
|-----------|------|
| OAR apagado `_oar_available` | rule-based en backlog (win_rate < 50% y sl > 0.10 → tighten stop; PF < 1.5 & win_rate < 55 → reduce; negativo expectancy → neutral) |
| Parsing falla en runtime | advisor.expand() retorna [] y el scheduler continua |
| `TradingAdvisor` sin OAR en runtime | advisor.py `_oar_sync_proposals` → propuestas vacías cierra honestamente |

## Backtest
`run_backtest(snapshots, config)` replays la serie con cooldowns + filtros + staged exits;
`parameter_sweep` rankea por expectancy; `BacktestConfig` pinta stop/trailing/tiers.
Estado: paper-only, jamás toca capital real. Los tests usan fixtures sin red.

## Gate humano
- Endpoint `POST /api/trading/paywall/*`? No: el gate vive en `api/routers/trading_advisor.py` approve/reject vía token de aprobación single-use (HMAC), recojo de `cores/automation/safety.py`.
- **Regla**: el advisor jamás ejecuta en live sin aprobación humana y sin capital real.

## Verificación (2026-09-13)
`tests/test_trading_advisor.py` 12 passed + `tests/test_trading_backtest.py` 13 passed + advisor test fallback suite → ruff advisor dir 0 errores · ruff clean.
