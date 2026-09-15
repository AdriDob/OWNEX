# Plan 0-100: Trading (memecoins + acciones)

## Visión General
**CAPITAL ONLY, jamás renta base. PAPER por defecto, armado humano explícito.** Workspace `trading` (CAPITAL_ONLY). El trading financia con capital ya ganado, nunca con expectativa.

**Modelo**: paper → métricas paper ≥2 semanas → live solo con orden explícita + IdentityVault + Human Gate + capital declarado.
**Regla de oro**: sin paper-metrics (win-rate/profit-factor/drawdown ≥2 sem) no se habla de live.

---

## 0. Requisitos ($0)
| Qué | Herramienta |
|---|---|
| Paper memecoins | DexScreener keyless + RugCheck + Jupiter canónico (adapter real, DRY_RUN default) |
| Acciones/paper | Adapter paper existente |
| Kill switch | STRATEGY kill requiere humano para desactivar |
| Capital | Solo declarado por owner; jamás auto-detectado/inferido |

## 1. Fases 0-100
### FASE 0 — Descubrimiento
- Memecoins: filtros duros fail-closed (liquidez/volumen/holders/top10/autoridades/LP/edad).
- Acciones: universo + criterios de entrada/salida por escrito antes de operar.

### FASE 1 — Preparación (paper)
- [ ] Adapter en DRY_RUN verificado (fills simulados desde quotes reales).
- [ ] Filtros + exits configurados (SL > TP escalonado > trailing > tiempo).
- [ ] Kill switch STRATEGY armado y probado.

### FASE 2 — Paper loop (≥2 semanas, automático cada 15m vía scheduler)
- `run_paper_cycle_once()` + job `trading_memecoin_paper` (`*/15`).
- Ledger PnL + métricas: win-rate, profit-factor, expectancy, drawdown.
- Veredicto EDGE_CANDIDATE solo con n≥20 y PF>1.2.

### FASE 3 — Evaluación (Human Gate)
- Revisar métricas paper con owner. Solo con tu orden explícita se habla de live.
- Live exige: IdentityVault + Human Gate + capital declarado + sizing fraccionado fijo + haircut 1%.

### FASE 4+ — Live supervisado / Mantenimiento
- Kill STRATEGY activo siempre. Daily loss limit. Métricas diarias.
- Ante drawdown: volver a paper automáticamente, revisar, re-autorizar.

## 2. Métricas (paper y live)
`win_rate · profit_factor · expectancy · drawdown · n_trades · daily_pnl`

## 3. Reglas no negociables
1. **PAPER default.** Live = tu orden + IdentityVault + Human Gate + capital.
2. **El job jamás mueve fondos** (adapter DRY_RUN default).
3. **Kill STRATEGY requiere humano** para desactivar.
4. **Trading jamás renta base** (política CAPITAL_ONLY, fuera del mix).

## 4. Superficie OWNEX
- `cores/trading/` (adapter, strategies, paper, store) + job `trading_memecoin_paper`
- `GET /api/trading/*` (dashboard, status, kill)
- Workspace `trading` + Project OS si se abre proyecto
