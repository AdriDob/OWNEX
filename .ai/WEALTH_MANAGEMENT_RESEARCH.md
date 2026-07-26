# OWNEX Wealth Management & Financial Opportunities — Research Report

> Investigación completa de plataformas, APIs y oportunidades para integrar en OWNEX como ciclo de optimización de dinero. Research only — no code.

---

## 1. PORTFOLIO TRACKING & AGGREGATION

### 1.1 Plaid

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ REST API completa. `/investments/holdings/get`, `/investments/transactions/get`, webhooks |
| **Coverage** | 12,000+ instituciones US/CA/EU |
| **Crypto?** | Sí — exchanges y self-custody wallets |
| **Automation** | Total — polling diario automático, webhooks on-change |
| **Risk** | Bajo |
| **Returns** | N/A (tracking, no genera) |
| **Pricing** | Sales-led producción. Sandbox gratis. ~$0.50–2.00/usuari/mes (est.) |
| **Regulation** | Plaid es agregador regulado. Términos restrictivos para reventa de datos |
| **ROI** | 5 |
| **Automation** | 9 |
| **Risk (score)** | 9 (bajo riesgo) |
| **Integration** | 7 (SDK Python/JS, doc extensa. Sales-led para prod) |
| **Stability** | 10 |
| **Verification** | `core/events/`, `cores/` — no hay integración existente |

### 1.2 Yodlee (Envestnet)

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ REST. 17,000+ fuentes globales. Clean & enrich ML |
| **Coverage** | Global — mejor para PFM/wealth que Plaid fuera de US |
| **Automation** | Total |
| **Risk** | Bajo |
| **Pricing** | Enterprise, sales-led. Coste no público |
| **ROI** | 4 |
| **Automation** | 9 |
| **Risk** | 9 |
| **Integration** | 5 (enterprise-only, sin self-service real) |
| **Stability** | 9 |

### 1.3 Teller.io ⚠️ DISCONTINUED (julio 2026)

| Dimensi | Valor |
|---------|-------|
| **Status** | Cerrado. Migrar a Plaid |
| **Nota** | Era la mejor opci indie para US. Ya no operativa |

### 1.4 Kubera

| Dimensi | Valor |
|---------|-------|
| **API** | Plaid + crypto wallets. Sin API pública programática |
| **Pricing** | $15/mes individual |
| **Model** | SaaS. No integrable como backend |
| **Veredict** | ❌ No para OWNEX. Es producto final, no API |

### 1.5 Zapper (crypto portfolio)

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ GraphQL (`portfolioV2`). Tokens, apps (DeFi), NFTs, claimables |
| **Status** | **Shuts down August 3, 2026** |
| **Veredict** | ❌ Moribundo. Migrar a Zerion |

### 1.6 Zerion (crypto portfolio) ✅ RECOMMENDED

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ REST + GraphQL. 40+ chains (EVM + Solana). Portfolio, transactions, DeFi, PnL |
| **Coverage** | 40+ chains, unifica EVM + Solana en un schema |
| **Migration** | Guías 1:1 desde Zapper, DeBank, Dune SIM, Allium |
| **Automation** | Total |
| **Risk** | Bajo |
| **Pricing** | Contactar. Tiene free tier para dev |
| **ROI** | 7 |
| **Automation** | 9 |
| **Risk** | 9 |
| **Integration** | 8 (SDK, CLI, doc clara, REST + GraphQL) |
| **Stability** | 9 |
| **Verification** | `cores/analysis/` — CoinGecko existe, Zerion no |

### 1.7 DeBank (crypto portfolio)

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ Cloud API. Net worth, DeFi, history, NFTs |
| **Status** | Activo. Zerion ofrece migración desde DeBank |
| **Veredict** | Alternativa viable. Zerion tiene mejor DX |

### 1.8 CoinGecko (crypto prices)

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ Ya integrado en CATEYE. 17,000+ coins, precios, market data, onchain |
| **Portfolio** | ✅ Endpoint portfolio tracking real-time, cost basis, PnL |
| **Status** | ✅ Ya existe en `cores/` |
| **ROI** | 8 (ya implementado, solo conectar) |
| **Automation** | 10 |
| **Risk** | 10 |
| **Integration** | 10 (ya existe) |
| **Stability** | 10 |

---

## 2. CRYPTO OPPORTUNITIES

### 2.1 DeFi Yield Farming (Aave, Compound, Curve)

| Plataforma | API | Notas |
|------------|-----|-------|
| **DeFiLlama Yields** | ✅ API pro (key). 15,000+ pools. APY base/reward, 30d mean, IL risk, TVL | **Mejor fuente única** |
| **Oanor DeFi Yield** | ✅ API keyless. 15,000+ pools, filtros por chain/project, APY base+reward | Free tier: 100 calls/mes. Desde €10.90/mes |
| **YieldXyz** | ✅ SOC 2. 40+ protocols (Aave, Compound, Morpho, Yearn, Ethena). TXs ready-to-sign | Enterprise, SOC 2 |
| **Apify DeFi Yields** | ✅ Pay-per-result ($0.10/pool). Sin subscripcin. Datos DeFiLlama | Ideal para snapshots peridicos |

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ Múltiples opciones. DeFiLlama Pro = mejor calidad/precio |
| **Automation** | Parcial — tracking automático, ejecucin requiere wallet+firmar TX |
| **Risk** | Medio-alto (IL, smart contract risk, MEV, rug pulls) |
| **Returns** | 2-15% estable, 20-200% reward-driven (volátil) |
| **Fees** | Gas fees (ETH: $1-20/tx) + protocol fees |
| **Regulation** | No regulado. Riesgo regulatorio US/EU creciente |
| **ROI** | 7 |
| **Automation** | 6 (tracking 10, ejecucin 2) |
| **Risk** | 4 (riesgo medio-alto) |
| **Integration** | 7 (DeFiLlama API simple, Oanor más simple) |
| **Stability** | 5 (APYs volátiles, protocols cambian) |

### 2.2 Arbitrage CEX/DEX

| Plataforma | API | Notas |
|------------|-----|-------|
| **Oanor Arbitrage** | ✅ Spot price 5 CEX (Binance, OKX, Bybit, KuCoin, Coinbase). Spread + best buy/sell | Free: 100 calls/mes. €12/mes |
| **ArbitrageScanner** | ✅ 80+ CEX, 200+ DEX, 40+ blockchains. Spot+futures. Funding rates. On-chain | Pricing no público. Cada 4s actualizacin |
| **DataMaxi+** | ✅ 20+ venues. REST + WebSocket. Kimchi premium, funding skews. Sub-100ms | Free tier. Ideal para bots |
| **ArbiPulse** | ✅ x402 micropagos. CEX spot, DEX, funding rates, sports surebets | Pago por call |
| **Odds-API** | ✅ 250+ bookmakers. Arbitraje deportivo + EV | Desde free. MCP server incluido |

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ Múltiples. DataMaxi+ mejor para bots; Oanor mejor para research |
| **Automation** | Alto — tracking automático. Ejecucin requiere exchange API keys + capital |
| **Risk** | Medio (execution risk, slippage, rate limits, account bans) |
| **Returns** | 0.1-3% por arbitraje. Escalable con capital |
| **Fees** | Trading fees (0.1% spot), withdrawal fees, gas |
| **Regulation** | No regulado (crypto). Exchange TOS puede prohibir bots |
| **ROI** | 8 |
| **Automation** | 8 |
| **Risk** | 5 (riesgo medio) |
| **Integration** | 7 |
| **Stability** | 6 (oportunidades fugaces, exchanges cambian APIs) |

### 2.3 Staking

| Protocolo | API | APR |
|-----------|-----|-----|
| **Lido** | ✅ API pública. APR, wstETH rate, TVL | ~2.5-3.5% ETH |
| **Rocket Pool** | ✅ API pública (vía Oanor). rETH APR, node operators | ~2-3% ETH |
| **LST Compare (Oanor)** | ✅ wstETH, rETH, cbETH, wBETH, sfrxETH side-by-side | Cross-provider |
| **ETH Staking Tracker (Apify)** | ✅ Lido + RocketPool + Beacon Chain. $0.008/snapshot | Tracking consolidado |

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ Múltiples fuentes libres/públicas |
| **Automation** | Total para tracking. Parcial para staking (requires TX) |
| **Risk** | Bajo (Lido/RP son protocolos maduros. Slashing risk mínimo) |
| **Returns** | 2-4% APR ETH. Estable |
| **Fees** | Lido: 10% de rewards. RP: 15% |
| **Regulation** | Bajo riesgo (staking es core de ETH) |
| **ROI** | 6 |
| **Automation** | 7 |
| **Risk** | 8 (bajo-medio) |
| **Integration** | 9 |
| **Stability** | 8 |

### 2.4 Airdrop Farming

| Plataforma | API | Notas |
|------------|-----|-------|
| **airdrop5** | ✅ REST. Drops, hype score, EV, eligibility check. Webhooks | 99.95% SLA. 10k+ req/min |
| **Drops Bot** | ✅ REST. 8 networks. Wallet eligibility, claim status | Usado por Solscan, Blockscout, Etherscan |
| **x402 Airdrop Checker** | ✅ $0.012/check. Sin API key. MCP server | Pago por call en USDC |

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ airdrop5 es la mejor opcin |
| **Automation** | Medio — tracking automático, farming requiere acciones manuales |
| **Risk** | Medio (token price risk, scams, rug pulls) |
| **Returns** | $0-10k+ por airdrop. Muy variable |
| **Fees** | Gas fees para TXs |
| **Regulation** | No regulado. Riesgo fiscal |
| **ROI** | 7 |
| **Automation** | 4 (tracking 8, ejecucin 1) |
| **Risk** | 4 (alto riesgo) |
| **Integration** | 8 |
| **Stability** | 4 (airdrops son eventos nicos) |

---

## 3. CASHBACK & PROMOS

### 3.1 Cashback (Rakuten, TopCashback)

| Dimensi | Valor |
|---------|-------|
| **API** | ⚠️ Rakuten: API de afiliados (requiere aprobacin). No API pública directa. TopCashback: vía FlexOffers |
| **Automation** | Bajo — requiere extensin browser o portal. Afiliados API existente pero con aprobacin |
| **Risk** | Bajo |
| **Returns** | 1-15% cashback. Media 3-5% |
| **Fees** | 0% para el usuario |
| **Regulation** | Afiliados marketing — estandar |
| **ROI** | 4 |
| **Automation** | 3 |
| **Risk** | 10 |
| **Integration** | 3 (sin API pública simple) |
| **Stability** | 8 |

### 3.2 Credit Card Rewards Optimization

| Dimensi | Valor |
|---------|-------|
| **API** | ❌ Sin API unificada. Cada banco/emisor tiene su sistema |
| **Automation** | Bajo |
| **Risk** | Bajo |
| **Returns** | 2-5% efectivo con estrategia |
| **Veredict** | ❌ No integrable como API. Productos tipo MaxRewards existen pero sin API |

### 3.3 Bank Bonus Churning

| Plataforma | API | Notas |
|------------|-----|-------|
| **Bank Bonus App** | ❌ Sin API. App iOS. iCloud sync. Smart Add desde URLs | $0-59/año Pro |
| **Churning Hub** | ❌ Web app gratis. Sin API. Manual tracking | 100% gratis |
| **BonusBreaker** | ⚠️ Plaid opcional para auto-tracking. Chex/EWS scoring | $59/año. Modelo interesante |

| Dimensi | Valor |
|---------|-------|
| **API** | ❌ Ninguna plataforma expone API. BonusBreaker usa Plaid internamente |
| **Automation** | Bajo — manual por naturaleza (aplicaciones requieren accin humana) |
| **Risk** | Bajo-medio (credit score impact, Chex/EWS flags) |
| **Returns** | $200-1000 por bonus. $2k-10k/año posible |
| **Fees** | 0% |
| **Regulation** | Legal pero bank TOS puede limitar |
| **ROI** | 5 |
| **Automation** | 2 |
| **Risk** | 7 |
| **Integration** | 1 (sin APIs) |
| **Stability** | 7 |

---

## 4. BUDGETING & TRACKING

### 4.1 Actual Budget (self-hosted)

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ NPM package `@actual-app/api`. Programmatic access completo |
| **Deploy** | Docker. ~60MB RAM. SQLite. 15 min setup |
| **Bank Sync** | GoCardless (EU, free tier) / SimpleFIN ($15/año US) |
| **Model** | Zero-based budgeting (YNAB-like) |
| **Automation** | Total — API programática para import/export |
| **Risk** | Bajo (self-hosted, datos locales) |
| **Cost** | $0 software + $1.5/mes SimpleFIN |
| **ROI** | 7 |
| **Automation** | 9 |
| **Risk** | 10 |
| **Integration** | 8 (NPM package, Python wrapper posible) |
| **Stability** | 9 |

### 4.2 Firefly III (self-hosted)

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ REST API completa con personal access tokens. Webhooks |
| **Deploy** | Docker + PostgreSQL. ~150MB RAM |
| **Bank Sync** | GoCardless vía Data Importer. 80+ currencies |
| **Model** | Double-entry accounting + budgets + piggy banks |
| **Automation** | Total — API REST, webhooks, transaction rules |
| **Risk** | Bajo (self-hosted) |
| **Cost** | $0 |
| **ROI** | 8 |
| **Automation** | 9 |
| **Risk** | 10 |
| **Integration** | 9 (REST API documentation excelente, Python friendly) |
| **Stability** | 9 |

### 4.3 SimpleFIN Bridge

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ $15/año. 24 requests/día. 7,000+ institutions US |
| **Pricing** | $15/año. Read-only |
| **Veredict** | Útil como bridge si no se quiere Plaid. Limitado para PROD |

---

## 5. GAMBLING WITH LIMITS

### 5.1 Sports Betting Arbitrage

| Plataforma | API | Notas |
|------------|-----|-------|
| **SharpAPI** | ✅ 45+ sportsbooks. Arb detection + SSE streaming. +EV + middles | $79-399/mes. Sub-second latency |
| **SportsGameOdds** | ✅ 85+ books + exchanges + prediction markets. WebSocket | Free tier amateur. Pro ~$50-200/mes |
| **Breaking-Bet** | ✅ 270+ bookmakers. Cada 1-3s. Surebets + middles + valuebets | Pricing por bookmaker selection |
| **Odds-API** | ✅ 250+ bookmakers. Arbitrage endpoints. OpenAPI + MCP | Free tier disponible |

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ Múltiples opciones robustas |
| **Automation** | Alto — deteccin automática. Ejecucin requiere cuentas en books |
| **Risk** | Medio (account limits, line moves, voided bets, gct) |
| **Returns** | 0.5-5% por arbitraje. 5-15%/mes con bankroll |
| **Fees** | 0% (profit de spreads) |
| **Regulation** | Legal en UK/EU/Colombia. Prohibido en algunos estados US |
| **ROI** | 8 |
| **Automation** | 8 |
| **Risk** | 4 (riesgo de account bans, gct es real) |
| **Integration** | 8 (SharpAPI SSE, Odds-API MCP) |
| **Stability** | 5 (books limitan cuentas consistentemente arberas) |

### 5.2 Matched Betting

| Dimensi | Valor |
|---------|-------|
| **API** | Mismas APIs que arbitraje deportivo (SharpAPI, Odds-API, etc.) |
| **Risk** | Bajo-medio (riesgo es error humano, no riesgo de mercado) |
| **Returns** | £500-1500/mes UK. Menos en otros mercados |
| **Veredict** | Técnicamente integrable con mismas APIs de odds |

### 5.3 Low-Risk Casino Bonuses

| Dimensi | Valor |
|---------|-------|
| **API** | ❌ Sin API. Cada casino requiere scraping |
| **Risk** | Bajo si ejecutado correctamente (wager math) |
| **Returns** | $50-500 por bonus. No escalable |
| **Veredict** | ❌ No integrable vía API. Producto manual |

---

## 6. INVESTMENT ANALYSIS

### 6.1 Stock Screening

| Plataforma | API | Filtros |
|------------|-----|---------|
| **BusinessQuant** | ✅ REST. Gratis. 1,000+ metrics. P/E, revenue, margins, dividend yield | SQL-like conditions. 10,000 records/page |
| **Macroaxis** | ✅ REST + MCP. Market cap, P/E, P/B, dividend yield, ROE, beta | 100 results max |
| **FundamentalsAPI** | ✅ REST. Dividends, growth, ROE, debt/equity, stock screener | Free tier disponible |
| **SecuritiesDB** | ✅ REST. Dividend history, splits. Free | Consecutive increase streak |

| Dimensi | Valor |
|---------|-------|
| **API** | ✅ BusinessQuant = mejor gratuita. Macroaxis = mejor MCP |
| **Automation** | Total — screener polling automático, alertas |
| **Risk** | Bajo (solo data) |
| **Returns** | Indirecto (mejores decisiones de inversin) |
| **Cost** | BusinessQuant: FREE. Macroaxis: gratuito/limitado |
| **ROI** | 6 |
| **Automation** | 9 |
| **Risk** | 10 |
| **Integration** | 8 (REST simple, MCP para agentes) |
| **Stability** | 8 |

### 6.2 Dividend Tracking

| Plataforma | API | Notas |
|------------|-----|-------|
| **BusinessQuant** | ✅ Dividend yield, payout ratio en screener | Gratuito |
| **SecuritiesDB** | ✅ Dividend history, splits, consecutive streaks | Gratuito |
| **FundamentalsAPI** | ✅ Dividend growth, payout ratio, years growth | Free tier |
| **Halal Terminal** | ✅ Dividend history + purification calculator. Shariah screening | API completa |

### 6.3 Rebalancing Automation

| Dimensi | Valor |
|---------|-------|
| **API** | ❌ Sin API unificada. Requiere conectar brokers (Alpaca, Interactive Brokers API) |
| **Automation** | Total si se conecta broker API |
| **Risk** | Bajo-moderado |
| **Veredict** | Posible pero fuera de scope immediate. Alpaca API + CCXT para crypto |

---

## SUMMARY RANKING

### Top 10 Opportunities for OWNEX Integration

| # | Opportunity | ROI | Automation | Risk (score) | Integration | Stability | **Total** | Nota |
|---|------------|-----|-----------|-------------|-------------|----------|-----------|------|
| 1 | **CoinGecko Portfolio** (ya existe) | 8 | 10 | 10 | 10 | 10 | **9.6** | Ya en CATEYE. Solo conectar |
| 2 | **Firefly III Budgeting** | 8 | 9 | 10 | 9 | 9 | **9.0** | Self-hosted, REST API, full financial picture |
| 3 | **DeFiLlama / Oanor Yields** | 7 | 6 | 4 | 7 | 5 | **5.8** | Mejor tracking DeFi yields |
| 4 | **Zerion Portfolio** | 7 | 9 | 9 | 8 | 9 | **8.4** | Crypto portfolio completo, post-Zapper |
| 5 | **BusinessQuant Screener** | 6 | 9 | 10 | 8 | 8 | **8.2** | Stock screening gratuita |
| 6 | **SharpAPI/Odds-API Arbitrage** | 8 | 8 | 4 | 8 | 5 | **6.6** | Sports arbitrage, alto ROI, riesgo medio |
| 7 | **Plaid Investments** | 5 | 9 | 9 | 7 | 10 | **8.0** | Tracking tradicional, sales-led |
| 8 | **airdrop5** | 7 | 4 | 4 | 8 | 4 | **5.4** | Airdrop tracking, farming manual |
| 9 | **Staking (Lido/RP/Oanor)** | 6 | 7 | 8 | 9 | 8 | **7.6** | Tracking yields, bajo riesgo |
| 10 | **DataMaxi+ Arbitrage** | 8 | 8 | 5 | 7 | 6 | **6.8** | Crypto arbitrage en tiempo real |

### Quick Wins (bajo esfuerzo, alto impacto)

1. **CoinGecko → Dashboard de wealth** — ya tenemos la API. Solo mostrar portfolio + PnL
2. **DeFiLlama Yields → Oportunidades** — añadir tabla de mejores yields por chain
3. **Firefly III o Actual Budget** — deploy Docker, conectar con OWNEX API
4. **BusinessQuant Screener** — screener de acciones gratuito, REST simple

### Long-term (alto esfuerzo, alto ROI)

1. **SharpAPI → Sports arbitrage automation** — requiere bankroll + cuentas en books
2. **Plaid → Full aggregation** — sales-led, requiere acuerdo comercial
3. **DataMaxi+ → Crypto arbitrage bot** — requiere exchange APIs + capital management
4. **Churning automation** — tracking manual, difcil de automatizar

### No Recommended (now)

- **Rakuten/TopCashback API** — no hay API pública directa
- **Credit card optimization** — sin API unificada
- **Casino bonuses** — sin API, scraping frágil
- **Teller.io** — discontinuado
- **Zapper** — shutting down August 2026

---

## Architecture Notes for OWNEX

### Potential Integration Points

```yaml
# Suggested OWNEX Wealth Module Structure
wealth_cycle:
  aggregators:
    - plaid:         # Traditional banking/brokerage (sales-led)
    - zerion:        # Crypto multi-chain portfolio
    - coingecko:     # Prices + basic portfolio (ya existe)
  
  yield_sources:
    - defillama:     # DeFi yields tracking
    - staking:       # Lido/Rocket Pool APR
    - screener:      # Stock screening
  
  opportunities:
    - arbitrage:     # Sports (SharpAPI) / Crypto (DataMaxi+)
    - airdrops:      # airdrop5 tracking
    - bank_bonuses:  # Manual tracking UI
  
  budgeting:
    - firefly_iii:   # Self-hosted accounting
    - actual:        # Self-hosted budgeting (simpler)
```

### Recommended First Implementation

1. **Week 1**: CoinGecko wealth dashboard (ya tenemos API)
2. **Week 2**: DeFiLlama yield opportunities table
3. **Week 3**: Deploy Firefly III + conectar bank sync
4. **Week 4**: BusinessQuant stock screener integration
5. **Future**: Plaid (si se consigue acceso) → full aggregation

---

> Research conducted 2026-07-26. Market conditions change. Re-verify pricing and availability before implementation.
