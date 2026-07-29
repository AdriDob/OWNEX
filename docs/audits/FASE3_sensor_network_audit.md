# FASE 3 — Universal Sensor Network: Audit Report

**Date:** 2026-07-29  
**Auditor:** Hermes Agent  
**Target:** Sensor layer and opportunity intelligence in Rastro/OWNEX v6

---

## Files Audited

| # | Path | Status | Lines |
|---|------|--------|-------|
| 1 | `core/sensors/base.py` | ✅ Found | 114 |
| 2 | `core/sensors/observation.py` | ✅ Found | 69 |
| 3 | `core/sensors/observation_engine.py` | ✅ Found | 134 |
| 4 | `cores/intelligence/bounty_intel.py` | ✅ Found | 161 |
| 5 | `cores/opportunity/engine.py` | ✅ Found | 320 |
| 6 | `core/sensors/adapters/__init__.py` | ✅ Found (stub) | 5 |
| 7 | `core/sensors/adapters/generic_adapter.py` | ✅ Found | 72 |
| 8 | `core/sensors/adapters/hackerone.py` | ✅ Found | 68 |
| 9 | `extensions/playwright/__init__.py` | ✅ Found | 41 |
| 10 | `core/engine/base.py` | ✅ Found | 68 |
| 11 | `cores/observability.py` | ✅ Found | 50 |
| 12 | `cores/observability_core.py` | ✅ Found | 687 |
| 13 | `cores/events/event_bus.py` | ✅ Found | 293 |
| 14 | `core/events/event_bus.py` | ✅ Found | 177 |
| 15 | `cores/opportunity/providers.py` | ✅ Found | 594 |
| 16 | `cores/opportunity/history.py` | ✅ Found | 115 |
| 17 | `cores/opportunity/models.py` | ✅ Found | 142 |
| 18 | `cores/dedup.py` | ✅ Found | 100 |
| 19 | `cores/bounty_scraper/scraper.py` | ✅ Found | 995 |
| 20 | `cores/bounty_scraper/changes.py` | ✅ Found | 184 |
| 21 | `cores/bounty_scraper/monitor.py` | ✅ Found | 73 |
| 22 | `cores/intelligence/event_system.py` | ✅ Found | 110 |
| 23 | `core/financial_intelligence/opportunity_engine.py` | ✅ Found | 97 |

All requested files exist. The path `cores/opportunity/engine.py` uses plural `cores/` — confirmed present.

---

## Dimensional Analysis

### 1. DEDUPLICACIÓN ✅ (with gaps)

| Component | Mechanism | Score |
|-----------|-----------|-------|
| `ObservationCache` (base.py) | LRU dict keyed `(sensor_id, external_id)`. TTL=24h, max=10K. | ✅ |
| `Observation.dedup_key()` | `f"{sensor_id}:{external_id}"` | ✅ |
| `Observation.checksum` | Explicit field for fingerprint identity resolution | ✅ |
| `ObservationEngine.collect()` | Runs `is_duplicate()` per observation before adding | ✅ |
| `DedupTracker` (cores/dedup.py) | URL/path/program fingerprint w/ optional TTL | ✅ |
| `BountyScraper` | Local `seen: set[str]` on program URLs | ✅ |
| `ProgramChangeTracker` | JSON-persisted diff tracking by program key | ✅ |

**Gap:** No cross-sensor dedup. Two sensors monitoring the same external source produce different `sensor_id:external_id` keys by design, but no mechanism to collapse them. Fine for v1 — intentional separation of concerns.

---

### 2. PERSISTENCIA ❌ (partial)

| Component | Storage | Score |
|-----------|---------|-------|
| `ObservationCache` | In-memory only | ❌ |
| `DedupTracker` | In-memory only | ❌ |
| `ProgramChangeTracker` | JSON file `~/.orion/known_programs.json` | ✅ |
| `EventBus` (CATEYE) | SQLite via `EventBusEntry` model | ✅ |
| `CoreEventBus` | SQLite via `_EventRecord` model | ✅ |
| `ObservabilityCore` | SQLite at `~/.ownex/observability.db` | ✅ |
| `OpportunityEngine._opportunities` | In-memory dict | ❌ |
| `HistoryManager._snapshots` | In-memory list | ❌ |
| `Observation` objects | Never persisted to DB | ❌ |

**Critical gap:** Observations flow through the pipeline but are never persisted. On restart, everything is re-fetched. Opportunity state also lives entirely in memory.

---

### 3. TIMEOUTS ⚠️ (inconsistent)

| Component | Timeout | Score |
|-----------|---------|-------|
| `BountyScraper._fetch_json()` | 20s | ✅ |
| `BountyScraper._fetch_text()` | 20s | ✅ |
| `BountyScraper.scrape_hackerone()` | 15s per page (45s total) | ✅ |
| `BountyScraper.scrape_bugcrowd()` | 15s per page | ✅ |
| `BountyScraper.scrape_intigriti()` | 15s per page | ✅ |
| `BountyScraper.scan_domain()` | 10s per path | ✅ |
| `GenericAdapterSensor.fetch()` | **No timeout** | ❌ |
| `ObservationEngine.collect()` | **No timeout on sensor.fetch()** | ❌ |
| `HackerOneSensor.fetch()` | Inherits from scraper (15s) | ✅ |
| `OpportunityEngine.discover_all()` | No timeout per provider | ⚠️ |

**Critical gap:** `ObservationEngine.collect()` iterates all sensors and awaits each `fetch()` with no timeout. A single hanging sensor blocks the entire sensor network indefinitely.

---

### 4. RETRY ❌

| Component | Retry | Score |
|-----------|-------|-------|
| `BountyScraper` methods | Catch + `continue` only. No backoff. | ❌ |
| `ObservationEngine.collect()` | Catch Exception, log, skip sensor | ⚠️ |
| `GenericAdapterSensor.fetch()` | Catch Exception, return `[]` | ❌ |
| `OpportunityEngine.discover_all()` | Catch Exception, mark provider "down" | ❌ |
| `OpportunityEngine.refresh()` | Catch Exception, mark "degraded" | ❌ |
| `tenacity` / `backoff` / `retry` decorators | **Not used anywhere** | ❌ |

**Critical gap:** Zero retry/backoff logic anywhere in the sensor layer. Any transient failure is silently discarded.

---

### 5. RATE LIMITING ⚠️ (minimal)

| Component | Mechanism | Score |
|-----------|-----------|-------|
| `BountyScraper._rate_limit(min, max)` | `time.sleep(random.uniform(...))` | ✅ |
| `BountyScraper.scrape_bounty_targets_data()` | Uses `_rate_limit(0.5, 1.0)` between platforms | ✅ |
| `BountyScraper.scan_domain()` | Uses `_rate_limit(0.3, 0.8)` between paths | ✅ |
| Token bucket / sliding window | **Not implemented** | ❌ |
| `ObservationEngine.collect()` | No rate limiting on sensors | ❌ |
| `OpportunityEngine` | No rate limiting on providers | ❌ |

**Gap:** Rate limiting is ad-hoc and only present in the legacy `BountyScraper`. The sensor network has no rate limiting at all.

---

### 6. LOGS ✅

| Component | Logger | Score |
|-----------|--------|-------|
| `base.py` | `ownex.sensors` | ✅ |
| `observation_engine.py` | `ownex.sensors.observation_engine` | ✅ |
| `generic_adapter.py` | `ownex.sensors.generic` | ✅ |
| `hackerone.py` | `ownex.sensors.hackerone` | ✅ |
| `ObservationEngine.initialize()` | `logger.info` on sensor count | ✅ |
| `ObservationEngine.collect()` | `logger.error` on fetch fail, `logger.debug` on dedup | ✅ |
| `GenericAdapterSensor.fetch()` | `logger.error` on failure, `logger.info` on count | ✅ |
| `BountyScraper` | Extensive `logger.warning` + `logger.info` | ✅ |
| `OpportunityEngine` | `logger.info`/`logger.warning` throughout | ✅ |

**Gap:** No structured logging (JSON). No correlation IDs for traceability.

---

### 7. EVENTOS ✅ (with weakness)

| Component | Events Published | Score |
|-----------|-----------------|-------|
| `ObservationEngine.collect()` | `sensors:observations:new` (count, sensor_ids) | ✅ |
| `OpportunityEngine.discover_all()` | `opportunity:found` (top 5) | ✅ |
| `OpportunityEngine.refresh()` | `opportunity:updated` (per update) | ✅ |
| `CoreEventBus` | Namespaced app events + legacy bridge | ✅ |
| `CATEYE EventBus` | Priority-classified, SQLite-persisted | ✅ |
| `EventSystem` (intelligence) | `intel:*` typed events | ✅ |

**Gap:** All event publishes are wrapped in `try/except`/`contextlib.suppress` — failures are invisible. No event schema validation.

---

### 8. OBSERVABILIDAD ✅ (with gaps)

| Component | Capability | Score |
|-----------|-----------|-------|
| `Sensor.health()` | Returns running, fetch_count, last_fetch, last_error, cadence | ✅ |
| `Engine.health()` | Abstract — required by every engine | ✅ |
| `ObservationEngine.health()` | Per-sensor health + cache size | ✅ |
| `cores/observability.py` | `timer` context manager, `record()` for metrics | ✅ |
| `cores/observability_core.py` | SQLite-backed metrics, executions, alerts, health snapshots | ✅ |
| `OpportunityEngine.get_metrics()` | Comprehensive metrics + per-provider health | ✅ |
| `DiscoveryMonitor.get_status()` | Running state, interval, last check | ✅ |

**Gap:** No sensor heartbeat/watchdog. No Prometheus/OpenTelemetry export. No dashboard.

---

## Activos vs. Deficiencias

### ✅ Activos (fortalezas de la capa)
1. **Arquitectura sólida**: `Sensor` ABC, `Engine` ABC, `ObservationCache` LRU, `DedupTracker` — bien diseñados.
2. **Observación desacoplada**: Observaciones vs. clasificación separadas por diseño.
3. **EventBus dual**: `CoreEventBus` (namespaced) + `CATEYE EventBus` (prioritized, persistent).
4. **Logging jerárquico**: Nombres de logger consistentes (`ownex.*`, `cateye.*`).
5. **Observabilidad**: Dos capas (ligera `cores/observability.py` + pesada `cores/observability_core.py` con SQLite).
6. **Sensores concretos**: `HackerOneSensor` y `GenericAdapterSensor` implementan correctamente el ABC.

### ❌ Deficiencias críticas (deben resolverse)
1. **TIME-OUT AUSENTE**: `ObservationEngine.collect()` no tiene timeout por sensor. Un sensor colgado congela toda la red.
2. **RETRY AUSENTE**: Cero lógica de reintento. Fallos transitorios se pierden silenciosamente.
3. **SIN PERSISTENCIA**: `ObservationCache` y observaciones son volátiles. Al reiniciar se pierde todo.
4. **SIN RATE LIMITING**: La red de sensores no tiene control de flujo. Solo el `BountyScraper` legacy tiene `time.sleep()`.

### ⚠️ Deficiencias menores
5. **PlaywrightSensor no hereda de Sensor**: Es una clase standalone, no integrada en la Universal Sensor Network.
6. **Sin heartbeat/watchdog**: No hay monitor que verifique que los sensores están vivos.
7. **Eventos best-effort**: Todos los `publish()` están envueltos en `try/except` — fallos silenciosos.
8. **Sin structured logging**: Los logs no tienen formato JSON ni correlation IDs.
9. **Sin schema validation en eventos**: Cualquiera puede publicar cualquier payload.

---

## Mapa de Archivos de Sensor

```
core/sensors/
├── __init__.py                    # Docstring only (5 lines)
├── base.py                        # Sensor(ABC) + ObservationCache(LRU)
├── observation.py                 # Observation dataclass
├── observation_engine.py          # ObservationEngine(Engine) + collect()
└── adapters/
    ├── __init__.py                # Docstring only (5 lines)
    ├── generic_adapter.py         # GenericAdapterSensor(Sensor)
    └── hackerone.py               # HackerOneSensor(Sensor)

extensions/
└── playwright/
    └── __init__.py                # PlaywrightSensor (standalone, no Sensor)

cores/
├── dedup.py                       # DedupTracker + fingerprint functions
├── observability.py               # timer/record/get_metrics (lightweight)
├── observability_core.py          # MetricsCollector (SQLite-backed)
├── events/
│   └── event_bus.py               # CATEYE EventBus (persistent, priority)
├── intelligence/
│   ├── bounty_intel.py            # BountyIntelligence (report generator)
│   └── event_system.py            # Typed EventSystem wrapper
├── opportunity/
│   ├── engine.py                  # OpportunityEngine (discovery + scoring)
│   ├── providers.py               # BaseProvider + concrete providers
│   ├── history.py                 # HistoryManager (snapshots)
│   ├── models.py                  # Data models (Opportunity, etc.)
│   ├── scoring2.py                # Layered scoring engine
│   └── recommendations.py         # Recommendation generator
├── bounty_scraper/
│   ├── scraper.py                 # BountyScraper (multi-platform)
│   ├── changes.py                 # ProgramChangeTracker (persistent diff)
│   └── monitor.py                 # DiscoveryMonitor (background loop)
└── orion/
    └── opportunity_analyzer.py    # Orion opportunity analyzer
```

---

## Recomendaciones Prioritarias

1. **Añadir timeout a `ObservationEngine.collect()`**: `asyncio.wait_for(sensor.fetch(), timeout=30)`
2. **Añadir retry a sensores**: Decorador `@retry(max_attempts=3, backoff=exponential)` en `fetch()`
3. **Persistir ObservationCache**: Usar SQLite o Redis como backend en lugar de memoria
4. **Añadir rate limiter a ObservationEngine**: Token bucket antes de invocar `sensor.fetch()`
5. **Integrar PlaywrightSensor**: Que herede de `Sensor` y se registre en `ObservationEngine`
6. **Añadir heartbeat**: Sensor debe reportar liveness periódicamente; `ObservationEngine` debe detectar sensores caídos
7. **Structured logging**: Reemplazar `logging` directo con `structlog` o `python-json-logger`

---

*End of FASE 3 Audit*
