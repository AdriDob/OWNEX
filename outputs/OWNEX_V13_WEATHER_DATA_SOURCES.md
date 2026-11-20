# OWNEX V13 — Weather Data Engine

## Overview

Extensible system for collecting weather data from multiple sources to feed the Probability Engine. **NOT** copying code from audited repos — implementing own verified implementation.

## Data Providers

| Provider | Type | Access | Priority | Notes |
|----------|------|--------|----------|-------|
| **GFS** | Ensemble model (31 members) | NOAA/NWS APIs | 🔴 HIGH | Primary source; 31-member ensemble; from Repo 1 analysis |
| **ECMWF** | Ensemble model | API access | 🔴 HIGH | From Repo 2; Gaussian Bucket Model integration |
| **Open-Meteo** | Open API | Free, no auth | 🟡 MEDIUM | Alternative to NOAA; validate quality |
| **METAR** | Airport weather stations | NOAA/TAF | 🟡 MEDIUM | Station reports; from Repo 2 (HRRR/METAR) |
| **NOAA/NWS** | US national weather | Government API | 🟡 MEDIUM | Official source; cross-validate GFS |
| **PolyWeather API** | External API | Consume as service | 🟡 MEDIUM | ⚠️ AGPL-3.0: consume API only, NO code reuse (Repo 3) |

## Data Model — Weather Record

Every record must include all of these fields:

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | Provider name (gfs, ec_met, open_meteo, metar, noaa, deb) |
| `model` | string | Model name/version |
| `city` | string | City name |
| `coordinates` | object | {lat: float, lon: float} |
| `weather_station` | string | Station ID (for METAR/NOAA) |
| `variable` | string | Temperature, precipitation, wind, etc. |
| `unit` | string | celsius, fahrenheit, mm, m/s, etc. |
| `timestamp_utc` | datetime | UTC timestamp of observation |
| `local_time` | string | Human-readable local time |
| `forecast_issuance` | datetime | When the forecast was issued |
| `horizon` | string | Immediate, 6h, 24h, 72h, 7d, etc. |
| `version` | string | Model version (e.g., "GFS 12z") |
| `retrieval_timestamp` | datetime | When this data was fetched |
| `quality` | enum | validated, unvalidated, error |
| `validation_status` | enum | pending, validated, invalid |

## Source Discrimination

| Type | Description | Example |
|------|-------------|---------|
| **Forecast** | Predicted value | "Temp will be 25°C at 14:00" |
| **Observation** | Measured value | "Temp was 24°C at 14:00" |
| **Reanalysis** | Historical reconstruction | "ERA5 data for 2020-01-15" |
| **Estimation** | Derived from other data | "Gaussian bucket probability" |

## Comparison Capability

System must support comparing forecasts from different sources:

```
Comparison: GFS ensemble vs ECMWF ensemble vs Open-Meteo
         for: Buenos Aires, temperature max, horizon 24h
```

Each comparison includes:
- Source model
- City/coordinates
- Variable and unit
- Forecast horizon
- Emission timestamp
- Retrieval timestamp
- Quality status

## API Design — Weather Data Endpoints

| Endpoint | Description | Auth |
|----------|-------------|------|
| `GET /api/weather/sources` | List available data sources | None |
| `GET /api/weather/forecast` | Get forecast from a source | API key (optional) |
| `GET /api/weather/compare` | Compare multiple forecasts | None |
| `GET /api/weather/buckets` | Get probability buckets | None |
| `GET /api/weather/quality` | Check data quality status | None |

## Implementation Notes

1. **No code copied from audited repos** — own implementation from scratch
2. **All sources validated** with Brier score and error metrics
3. **Quality flags** on every record (validated/unvalidated/error)
4. **No arbitrary probabilities** — all probabilities must be calibrated
5. **Standard deviation estimated and validated per**: city, station, model, horizon, variable, season
6. **No look-ahead bias** — historical data only, no future data used for past forecasts
7. **Intervals of uncertainty** must be presented; avoid artificial precision
8. **Argentina access**: Investigate current access restrictions, residency, KYC, payments and operations. **Do NOT assume** API-accessible = legally financable from Argentina. **Do NOT bypass geoblocking** nor account restrictions. Document any incompatibility.

## Data Ingestion Pipeline

```
┌─────────────┐
│  Scheduler  │  (runs every 1h, 6h, 24h)
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Source Connectors  │  GFS, ECMWF, Open-Meteo, METAR, NOAA
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Normalization Layer│  All → unified Weather Record format
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Quality Filter     │  validated/unvalidated/error
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Probability Engine │  Gaussian Bucket + calibration
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Market Discovery   │  Polymarket/Kalshi edge detection
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Edge Detection     │  Estimated vs market probability
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Strategy Engine    │  Modular strategies (read-only)
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Paper Trading      │  Simulation only, real disabled
└─────────────────────┘
```

## Quality Control

- **Brier score** calculated per city, station, model, horizon, variable, season
- **Calibration curves** maintained per data source
- **MAE and RMSE** tracked over time
- **Out-of-sample validation** required before model substitution
- **Walk-forward validation** recommended for strategy evaluation

## Security & Compliance

- ❌ **No credentials stored** in code or config
- ❌ **No private keys** requested or stored
- ❌ **No real transaction signing**
- ❌ **No trade execution** in this module
- ✅ **All data public** or consumed via authorized APIs
- ✅ **Argentina access restrictions** documented and respected
- ✅ **License compliance** — AGPL-3.0 code never copied, API consumed externally only
- ✅ **Audit trail** of all data retrieval and quality checks