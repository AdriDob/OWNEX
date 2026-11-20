# OWNEX V13 — Polymarket Market Analysis

## Overview

Analysis of Polymarket weather markets to detect edges between estimated probabilities and market prices. **NOT** cloning the GFS Weather Bot — own implementation.

## Active Market Detection

### What to Detect per Market

| Field | Description | Example |
|-------|-------------|---------|
| `event_active` | Is the market currently active? | true/false |
| `max_temp` | Maximum temperature event | 35°C |
| `min_temp` | Minimum temperature event | 15°C |
| `temp_range` | Temperature range | 20-35°C |
| `city` | Reference city | Buenos Aires |
| `date` | Event date | 2026-12-25 |
| `reference_station` | Weather station ID | SAME/AAAA |
| `unit` | Temperature unit | celsius/fahrenheit |
| `resolution_rules` | How the market resolves | "MAX temp at city airport" |
| `official_resolution_source` | Authoritative source | NOAA/Weather Service |
| `liquidity` | Market depth | USD volume |
| `volume` | Trading volume | 24h USD volume |
| `bid` | Best bid price | 0.45 |
| `ask` | Best ask price | 0.55 |
| `spread` | Ask - Bid | 0.10 |
| `price` | Last traded price | 0.50 |
| `last_update` | When last updated | 2026-11-09T14:30:00Z |

### API Sources (Official Only)

| Platform | Endpoint Pattern | Authentication |
|----------|-----------------|----------------|
| **Polymarket** | API access via approved partners | ⚠️ Verify access from Argentina |
| **Kalshi** | API access via broker | ⚠️ Verify access from Argentina |

### ⚠️ Critical: Do NOT Assume

1. **API-accessible ≠ legally financable** from Argentina
2. **City and station are equivalent** — they are NOT
3. **Resolution rules are standard** — each market has its own
4. **Both platforms support same markets/cities/users** — they differ
5. **Liquidity is sufficient** — verify per market

### Required Action: Read Resolution Rules

**Before calculating any opportunity, read the resolution rules of each market.** If the market resolution cannot be verified, mark it `UNKNOWN` and exclude it from simulated operations requiring defined resolution.

## Edge Detection — Comparing Estimated vs Market

### Core Formula

```
raw_edge = model_probability - market_implied_probability
```

### Market Implied Probability Calculation

```
market_implied_probability = f(price, commission, liquidity, resolution_rules)
```

Where:
- `price` = last traded price (0.0 - 1.0)
- `commission` = platform commission rate (varies by market)
- `liquidity` = order book depth, volume
- `resolution_rules` = how the event is verified

### Adjusted Edge (Critical)

```
adjusted_edge = raw_edge - costs
```

Where `costs` includes:
- **Commissions** — platform fee per side
- **Slippage** — estimated execution slippage
- **Spread** — bid-ask spread
- **Liquidity costs** — inability to execute full size

### Edge Classifications

| Classification | Edge Range | Action |
|----------------|------------|--------|
| **Strong opportunity** | edge > threshold_high | Paper trade only |
| **Moderate opportunity** | 0 < edge ≤ threshold_high | Paper trade only |
| **Fair/neutral** | -threshold_low ≤ edge ≤ 0 | No action |
| **Poor opportunity** | edge < -threshold_low | No action |

### Threshold Determination

Thresholds must be data-driven, not arbitrary:

1. **Historical calibration** — calculate edge distribution from past forecasts
2. **Cost coverage** — threshold must cover all costs + provide positive expected value
3. **Risk-adjusted** — factor in liquidity and uncertainty
4. **Per-market** — different markets have different commission/spread structures

### Expected Value Calculation

```
EV = adjusted_edge × position_size × payout − costs
```

Where:
- `adjusted_edge` = model_probability - market_implied_probability - costs
- `position_size` = fractional Kelly or fixed fraction
- `payout` = what you win/lose per unit (market-dependent)
- `costs` = commissions + slippage + spread

**If costs/data unavailable → mark as INCOMPLETE, not wrong.**

## Market Resolution Rules — Must Know

Each market has specific resolution rules. Must read and document:

| Component | What to Document |
|-----------|-----------------|
| **Temperature source** | Which weather service determines the value |
| **Measurement location** | Specific station/airport |
| **Measurement time** | When max/min is observed |
| **Time zone** | Local time of measurement |
| **Resolution date** | By when result must be known |
| **Dispute resolution** | What if sources disagree |
| **Official source** | Primary authority |

### Example Resolution Rules

```
Market: "Buenos Aires Max Temp > 35°C on 2026-12-25"
Resolution: NOAA National Weather Service data for EZE airport
            Max temperature on 2026-12-25, local time
Source: https://www.ncdc.noaa.gov/
```

```
Market: "Buenos Aires Min Temp < 10°C on 2026-12-25"
Resolution: SMN (Servicio Meteorológico Nacional) Argentina
            Min temperature on 2026-12-25, 00:00-23:59 local time
Source: https://www.smn.gob.ar/
```

## Argentina Access — Investigate Restrictions

### Must Investigate (DO NOT ASSUME)

| Aspect | Action | Document |
|--------|--------|----------|
| **Residency requirements** | Can non-residents create accounts? | ✅/❌ |
| **KYC requirements** | Identity verification needed? | ✅/❌ |
| **Payment methods** | Can you deposit/withdraw from AR? | ✅/❌ |
| **Geoblocking** | Does platform restrict AR IP? | ✅/❌ |
| **Market availability** | Are weather markets open for AR users? | ✅/❌ |
| **Commission rates** | Do they differ for AR users? | ✅/❌ |
| **Tax implications** | Any tax obligations for AR users? | ✅/❌ |

### Non-Negotiable Rules

- 🛡️ **Never bypass geoblocking** nor account restrictions
- 🛡️ **Never assume** API-accessible = legally financable from Argentina
- 🛡️ **Document any incompatibility** found
- 🛡️ **Work within existing restrictions** — if platform doesn't accept AR users, document and move on

## Market Data Schema

Every market record must include:

| Field | Type | Description |
|-------|------|-------------|
| `platform` | string | "polymarket" or "kalshi" |
| `market_id` | string | Unique market identifier |
| `event_name` | string | Human-readable event description |
| `temperature_variable` | string | "max_temp", "min_temp", "range" |
| `value_threshold` | number | The threshold (e.g., 35 for >35°C) |
| `resolution` | string | How the value is determined |
| `official_source` | string | Weather service authority |
| `city` | string | Reference city |
| `country` | string | Country code |
| `date` | date | Event date |
| `unit` | string | celsius/fahrenheit |
| `status` | enum | active, inactive, resolved, unknown |
| `liquidity_usd` | number | Current liquidity in USD |
| `volume_24h_usd` | number | 24h trading volume |
| `bid` | number | Best bid (0-1) |
| `ask` | number | Best ask (0-1) |
| `spread` | number | ask - bid |
| `last_price` | number | Last traded price (0-1) |
| `last_update` | datetime | When data was last updated |
| `resolution_rules` | text | Full resolution rule description |
| `access_from_ar` | bool | Can Argentina access this market? |
| `kyc_required` | bool | KYC required to trade? |
| `residency_required` | bool | Residency required? |

## Edge Detection Workflow

```
1. Fetch weather forecast from Data Engine (GFS, ECMWF, etc.)
2. Calculate model probability (Gaussian Bucket)
3. Fetch market data from Polymarket/Kalshi
4. Parse resolution rules for the market
5. Calculate market_implied_probability from price
6. Compute raw_edge = model_prob - market_implied
7. Subtract costs (commissions + slippage + spread)
8. Compute adjusted_edge
9. Classify edge (strong/moderate/fair/poor)
10. If adjusted_edge > threshold → paper trade signal
11. Record: signal, price, model, edge, costs, EV, strategy
12. Paper trade simulation only
13. Compare result vs observation at resolution
14. Update model calibration (historical learning)
```

## Liquidity and Slippage Considerations

### Liquidity Requirements

Minimum thresholds before considering a market:

| Metric | Minimum Threshold | Rationale |
|--------|------------------|-----------|
| `liquidity_usd` | ≥ 1000 | Enough depth for reasonable position |
| `volume_24h_usd` | ≥ 500 | Recent trading activity |
| `bid-ask spread` | ≤ 0.05 | Tight enough for entry/exit |
| `market_age` | ≥ 24h | Not brand new, some price discovery |

### Slippage Estimates

| Market Condition | Estimated Slippage |
|-----------------|-------------------|
| High liquidity, tight spread | 0.001 - 0.005 |
| Medium liquidity, moderate spread | 0.005 - 0.01 |
| Low liquidity, wide spread | 0.01 - 0.05 |
| Very low liquidity | 0.05+ (avoid) |

**Always include slippage in adjusted_edge calculation.**

## No Automatic Profit Assumption

**Fundamental rule**: A more precise meteorological prediction does NOT guarantee a profitable operation.

Factors that matter:

1. Exact market rules
2. Location and measurement time horizon
3. Event resolution
4. Commissions
5. Liquidity
6. Slippage
7. Market depth
8. Order execution quality

**Edge detection must incorporate ALL of the above.** Never present probability difference as automatically profitable.

## Polymarket vs Kalshi — Differences

| Aspect | Polymarket | Kalshi |
|--------|------------|--------|
| **Platform type** | Decentralized prediction market | Regulated exchange |
| **Trading hours** | 24/7 (crypto-style) | Market hours (9:30-16:00 ET) |
| **Settlement** | oracle-mediated | Exchange-defined |
| **Commission structure** | Maker/taker fees | Fixed per-contract |
| **Liquidity model** | AMM-like | Order book |
| **Available markets** | Wide variety | More focused |
| **Geographic restrictions** | Varies by jurisdiction | US-centric (more regulated) |
| **Price range** | 0.01 - 0.99 | 0.00 - 1.00 |

**Do NOT assume one platform's behavior applies to the other.** Each must be analyzed separately.

## Deliverables Already Generated

- outputs/OWNEX_V13_WEATHER_DATA_SOURCES.md (created)
- outputs/OWNEX_V13_WEATHER_MODELS.md (created)
- outputs/OWNEX_V13_POLYMARKET_MARKET_ANALYSIS.md — created above
- outputs/OWNEX_V13_WEATHER_STRATEGIES.md — next
- outputs/OWNEX_V13_WEATHER_RISK.md — next
- outputs/OWNEX_V13_WEATHER_BACKEND.md — next
- outputs/OWNEX_V13_WEATHER_TESTS.md — next
- outputs/OWNEX_V13_WEATHER_BLOCKERS.md — next