# OWNEX V13 — Weather Module Blockers and Open Questions

## Current Blockers — Must Resolve Before V13 Release

### B1: Argentina Access Restrictions — INVESTIGATE PENDING

| Aspect | Status | Action Required |
|--------|--------|----------------|
| Residency requirements for Polymarket | ❓ Unknown | Investigate: can non-residents create accounts? |
| KYC requirements for Kalshi | ❓ Unknown | Investigate: identity verification needed? |
| Payment methods from Argentina | ❓ Unknown | Investigate: deposit/withdrawal possible? |
| Geoblocking on both platforms | ❓ Unknown | Investigate: IP restrictions? |
| Market availability for AR users | ❓ Unknown | Investigate: weather markets open? |
| Commission rates for AR users | ❓ Unknown | Investigate: do they differ? |
| Tax obligations for AR users | ❓ Unknown | Investigate: any tax requirements? |

**⚠️ Decision**: Do NOT assume API-accessible = legally financable. Document all findings. Work within restrictions.

### B2: Real Trading Enablement — DECISION PENDING

| Question | Options | Decision Required |
|----------|---------|-------------------|
| When to enable real trading? | • After P0 baseline complete<br>• After V13 full validation<br>• Never (paper trading only)<br>• Separate module | Define clear criteria and timeline |
| Human approval mechanism | • Per-trade approval<br>• Batch approval<br>• Monthly review<br>• Never | Define approval workflow |
| Risk controls before enablement | • Must have all calibrated<br>• Minimum trade count<br>• Minimum Brier score<br>• Minimum liquidity | Set pre-conditions |

**⚠️ Decision**: Real trading out of V13 scope. Define P2/P3 criteria separately. First version: paper trading only.

### B3: PolyWeather AGPL-3.0 Legal Review — PENDING

| Question | Status | Action Required |
|----------|--------|----------------|
| License compatibility analysis | ❓ Not done | Legal review: can we consume API externally? |
| API access terms | ❓ Not verified | Check PolyWeather API ToS/licensing |
| External service integration pattern | ❓ Not documented | Define API consumption pattern |
| Mitigation if legal denied | ❓ Not planned | Backup plan if API integration blocked |

**⚠️ Decision**: ✅ Already decided: consume API externally, NO code reuse. Legal review to confirm API terms allow this.

### B4: ML Weather Model Credentials.txt — SECURITY PENDING

| Question | Status | Action Required |
|----------|--------|----------------|
| credentials.txt content | ⚠️ Warning only | Verify: what secrets might be present? |
| Safe to reference repo | ⚠️ Experimental only | Treat as reference only, no integration |
| Lessons learned extraction | ⚠️ Possible | Extract methodology concepts, not code or datasets |
| Dataset quality verification | ❓ Not done | If integrating data, verify quality first |

**⚠️ Decision**: ✅ Already decided: experimental only, reference quality datasets, avoid credentials.txt. Never open/use possible secrets.

### B5: Probability Calibration Thresholds — DEFINE PENDING

| Question | Options | Decision Required |
|----------|---------|-------------------|
| Brier score threshold | • 0.20 (stricter)<br>• 0.25 (standard)<br>• 0.30 (lenient) | Set calibration quality requirement |
| σ estimation minimum data points | • 30 (standard)<br>• 50 (conservative)<br>• 100 (strict) | Define per-group minimum |
| Calibration curve tolerance | • MAE < 1.0°C<br>• MAE < 2.0°C<br>• MAE < 3.0°C | Set acceptable error |
| risk_score maximum | • 0.5 (strict)<br>• 0.7 (moderate)<br>• 0.9 (lenient) | Set trade skip threshold |

**⚠️ Decision**: Define based on P0 baseline data after 4-week measurement. Start moderate, adjust.

### B5: Edge Detection Thresholds — DEFINE PENDING

| Question | Options | Decision Required |
|----------|---------|-------------------|
| raw_edge threshold (strong) | • 0.05<br>• 0.10<br>• 0.15 | Set strong opportunity threshold |
| raw_edge threshold (moderate) | • 0.02<br>• 0.05<br>• 0.08 | Set moderate opportunity threshold |
| adjusted_edge minimum | • 0 (break-even)<br>• 0.01 (small edge)<br>• 0.05 (meaningful) | Set minimum for trade |
| cost coverage requirement | • Edge must cover 100% costs<br>• Edge must cover 150% costs<br>• Edge must cover 200% costs | Define cost coverage rule |

**⚠️ Decision**: Base on Polymarket/Kalshi commission/slippage data after investigation. Start conservative.

### B6: Paper Trading Realism — DEFINE PENDING

| Question | Options | Decision Required |
|----------|---------|-------------------|
| Slippage estimation method | • Fixed per market<br>• Historical observation<br>• ML model<br>• Conservative fixed | Choose method |
| Cost inclusion level | • Commissions only<br>• Commissions + fees<br>• Commissions + slippage<br>• Full realistic model | Choose granularity |
| Resolution simulation acceleration | • Real-time (wait actual)<br>• Accelerated (N× speed)<br>• End-of-day resolution | Choose timeline |
| Capital allocation model | • Fixed per strategy<br>• Fractional Kelly<br>• Fixed fraction (% capital)<br>• Per-edge-size | Choose sizing method |

**⚠️ Decision**: Start conservative (historical slippage, commissions + slippage, real-time-ish resolution, fractional Kelly 0.25).

### B7: Human Gate Approval Workflow — DEFINE PENDING

| Question | Options | Decision Required |
|----------|---------|-------------------|
| Who approves strategy activation | • Lead engineer<br>• Product owner<br>• Security team<br>• Multi-sig | Define role |
| What's approved | • All new strategies<br>• Only high-edge strategies<br>• Only after validation<br>• Only after re-validation | Define scope |
| Approval timeline | • Immediate<br>• Same day<br>• 24h<br>• 5 business days | Set expectation |
| Denial process | • Automatic re-review<br>• Requires revision<br>• Requires completely new version | Define process |

**⚠️ Decision**: Human gate required for all strategy activation. Lead engineer approves after validation passed. 24h timeline for standard approvals.

### B8: Polymarket/Kalshi Commission/Slippage Data — GATHER PENDING

| Data Point | Status | Action Required |
|------------|--------|----------------|
| Polymarket commission rate | ❓ Unknown | Query API/documentation |
| Kalshi commission rate | ❓ Unknown | Query API/documentation |
| Polymarket typical spread | ❓ Unknown | Historical data analysis |
| Kalshi typical spread | ❓ Unknown | Historical data analysis |
| Slippage estimates per market condition | ❓ Unknown | Paper trading simulation data |
| Liquidity variations by hour/day | ❓ Unknown | Monitor and document |

**⚠️ Decision**: Gather before setting edge thresholds (B5). Query APIs, analyze historical data.

### B9: Polymarket/Kalshi Access from Argentina — GATHER PENDING

| Data Point | Status | Action Required |
|------------|--------|----------------|
| Can Argentine create Polymarket account | ❓ Unknown | Try registration (no real funding) |
| Can Argentine create Kalshi account | ❓ Unknown | Try registration (no real funding) |
| Geographic IP restrictions | ❓ Unknown | Test with/without VPN (theory only) |
| Commission differences for AR | ❓ Unknown | Compare standard vs potential AR rates |
| Payment methods supported from AR | ❓ Unknown | Check supported methods |

**⚠️ Decision**: ✅ Already decided: investigate before any integration. Never bypass geoblocking.

### B10: Frontend Integration Pattern — DEFINE PENDING

| Question | Options | Decision Required |
|----------|---------|-------------------|
| Weather section in existing frontend | ✅ Already decided | Integrate into OWNEX Investment Dashboard, NOT separate app |
| Weather module React components | ❓ Need design | Design: WeatherOverview, CityForecast, etc. |
| Navigation integration | ❓ Menu item needed | Add "Weather Intelligence" to main nav |
| State management | ❓ Global or local | Choose: Redux, Context, or simple props |
| API integration pattern | ❓ Backend endpoints | Define: /api/weather/* endpoints |

**⚠️ Decision**: ✅ Already decided: integrate into canonical frontend, not separate app. Design to begin after core module validated.

## Priority Order — What to Resolve First

| Priority | Blocker | Why First |
|----------|---------|-------------|
| **1** | Argentina access restrictions | Must know before any market integration; legal/compliance |
| **2** | Real trading enablement criteria | Defines V13 scope; paper trading only is default |
| **3** | PolyWeather AGPL legal review | Confirms API consumption pattern is allowed |
| **4** | ML Weather Model credentials.txt | Security: verify no secrets should be used |
| **5** | Calibration thresholds | Affects signal quality and strategy activation |
| **6** | Edge detection thresholds | Affects which opportunities are traded |
| **7** | Paper trading realism | Affects simulation quality and learning validity |
| **8** | Human gate workflow | Defines approval process for all activations |
| **9** | Commission/slippage data | Needed for edge threshold calculations |
| **10** | Frontend integration pattern | Needed for UI, but core module independent |

## Resolution Timeline

| Phase | Timeframe | Deliverables |
|-------|-----------|--------------|
| **P0 Week 1-4** | Current week | Continue revenue baseline; gather commission/slippage data; investigate Argentina access |
| **P0 Week 4 (end)** | Baseline complete | Decision: V13 scope confirmed (paper trading only) |
| **P1 (Week 5-8)** | After P0 | Resolve B1-B5: Argentina access, trading criteria, calibration thresholds, edge thresholds |
| **P1 (Week 9-10)** | Mid-P1 | Resolve B6-B8: Paper trading realism, human gate, commission data |
| **P1 (Week 11-12)** | Late P1 | Resolve B9-B10: Argentina access confirmation, frontend integration |
| **P2** | After P1 | Evaluate real trading enablement based on all criteria met |
| **Post-P2** | After real trading | Full module with real trading if approved |

## Immediate Actions (This Session)

- [ ] **B1**: Start Argentina access investigation — check Polymarket/Kalshi ToS, document restrictions
- [ ] **B2**: Confirm V13 real trading = disabled, paper trading only
- [ ] **B4**: Review credentials.txt warning — verify no secrets should be used; treat repo as experimental reference only
- [ ] **B8**: Gather Polymarket/Kalshi commission/slippage data from API docs or community knowledge
- [ ] **B9**: Test account creation from Argentina (no real funding) on both platforms; document
- [ ] **Update** `.ai/CURRENT_STATE.md` with blocker status and decisions
- [ ] **Continue** P0 Week 1 baseline data collection (revenue metrics)

## Blockers Impact on V13 Timeline

```
If Argentina access BLOCKED for both platforms:
  → V13 cannot integrate real markets
  → Paper trading with synthetic data only
  → Document as "no real market access from AR"
  → Re-evaluate value proposition

If REAL TRADING enabled prematurely:
  → Violates revenue rule
  → Violates safety constraints
  → Must roll back to paper trading
  → Delay V13 release

If AGPL LEGAL REVIEW BLOCKS API consumption:
  → Loss of one data source (PolyWeather)
  → Use GFS + ECMWF + Open-Meteo + METAR + NOAA
  → Still robust module without PolyWeather

If CALIBRATION THRESHOLDS too lenient:
  → Low-quality signals, poor paper trading results
  → Adjust stricter after data review

If CALIBRATION THRESHOLDS too strict:
  → Fewer signals, slower learning
  → Adjust lenient after sufficient data
```

## Deliverables Already Generated

- outputs/OWNEX_V13_WEATHER_DATA_SOURCES.md (created)
- outputs/OWNEX_V13_WEATHER_MODELS.md (created)
- outputs/OWNEX_V13_POLYMARKET_MARKET_ANALYSIS.md (created)
- outputs/OWNEX_V13_WEATHER_STRATEGIES.md (created)
- outputs/OWNEX_V13_WEATHER_RISK.md (created)
- outputs/OWNEX_V13_WEATHER_BACKTEST.md (created)
- outputs/OWNEX_V13_WEATHER_SECURITY.md (created)
- outputs/OWNEX_V13_WEATHER_TESTS.md (created)
- outputs/OWNEX_V13_WEATHER_BLOCKERS.md — created above