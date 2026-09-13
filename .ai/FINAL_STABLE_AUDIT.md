# FINAL STABLE AUDIT — Matriz de estado del cierre 7.1.x

> Audit interno del megaprompt FINAL DEFINITIVE RELEASE (2026-09-13).
> Fuente de verdad: runtime (`api/`, `cores/`), tests, `.ai/` verificado por lectura de código.
> Veredictos: ACTIVE / PARTIAL / BROKEN / DUPLICATED / DEPRECATED / DEAD / MISSING / UNVERIFIED.

## Reglas de cierre vinculantes (del owner)
- `core/` solo se borra con prueba: `rg "from core\." cores/` == 0 + `api/main.py` sin imports `core.` + MSI validado en Windows 11 (W1-W12 ejecutado por el owner en PC real). Hasta entonces: **CONGELADO**.
- Versión freeze: **7.1.x** (hoy 7.1.0, 11 superficies vía `scripts/sync_version.py`). No v7.2.0.
- Windows físico W1-W12: lo ejecuta el owner. CI entrega MSI + smoke.

## Matriz de estado

| # | Sistema | Veredicto | Evidencia |
|---|---------|-----------|-----------|
| 1 | Contrato `IntelligenceItem` + ABC `IntelligenceFeed` | ACTIVE | `cores/intelligence/__init__.py:84,126`; 7 feeds conforman; `tests/test_threat_intel_feeds.py:44` |
| 2 | Feeds OSV/NVD/EPSS/GHSA/ThreatFox/arXiv/OpenAlex | ACTIVE | 7 feeds `feeds/*.py` keyless+timeout+graceful `[]`; 7/7 registrados |
| 3 | Registry `IntelligenceRegistry` | ACTIVE | `build_default_intelligence_registry()` 7 feeds; `lifespan._init_intelligence_registry` + `health_check_all()`; `tasks.run_intelligence_refresh` |
| 4 | Cache/TTL/provenance feeds | ACTIVE | `IntelligenceCache` JSONL `OWNEX_DATA_DIR/intelligence/items.jsonl`; `is_fresh()` TTL; `_default_cache_dir()`; `ContentHasher` en `provenance.py` |
| 5 | Hypothesis pipeline CISA KEV | ACTIVE | `threat_intel.py:62` + `_stage_threat_intel` |
| 6 | ThreatFox/OSV/NVD/EPSS/GHSA → hypothesis | ACTIVE | `threat_intel.generate_from_feed_items()` + cache `iter_source` → bridge en `engine._stage_threat_intel` (cache-only) |
| 7 | Economics SSOT (EV/HTROI/P_CASH/CONF) | ACTIVE | `economics.py:67,139,250,327,393` + 5 tests |
| 8 | Lifecycle POTENTIAL→PAID→NET | ACTIVE (dual) | `state_machine.py:27` + `ledger.py:22`; `paid_only_increments_real` |
| 9 | P(CASH) / UNKNOWN labelling | ACTIVE | `reward_probability.py:317`; `recommendation.py:952` |
| 10 | Human Gate (HMAC single-use) | ACTIVE | `safety.py:77` 600s single-process |
| 11 | OAR fallback | ACTIVE | Orden canónico `Ollama→OpenCode→Groq→FCC→OpenRouter` pineado `test_oar.py:local_first` |
| 12 | Frontend Mission / UnifiedChat / router | ACTIVE | `Mission.vue:22`; `UnifiedChat.vue:49`; `chat.py:90` `/api/chat`; `/merlin→/ai` `router/index.ts:48` |
| 13 | CommandPalette `/hunt/scan` | BROKEN → FIXED | Era 404 (no existe en `hunt.py`, solo status/start/pause/resume/stop/restart). Mapeado a `/hunt/restart` (2026-09-13) |
| 14 | Mobile daily-brief contract | BROKEN → FIXED | Android leía `top_actions`/`ev`/`next_step`; backend emite `actions`/`expected_value_usd`/`next_action`. Fix tolerante a ambos (2026-09-13) |
| 15 | Target model (`active` + property `status`) | ACTIVE | `database/models.py:44,52`; fix 500 `/mobile/status` (09-08) |
| 16 | Endpoint `last_scanned`/`scan_count` | ACTIVE | `database/models.py:99-108` presentes; sin drift verificado |
| 17 | Hunt contract | ACTIVE | `api/routers/hunt.py:10,28,89`; `test_hunt_router.py` |
| 18 | Packaging Tauri + sidecar | ACTIVE | `tauri.conf.json:3-5` 7.1.0; `externalBin` triple suffix guard `test_tauri_packaging.py:87`; `OWNEX-Backend.spec:111` embe| VERSION; `lib.rs:188` |
| 19 | core/ vs cores/ | DUPLICATED (congelado) | `core/` 652py vs `cores/` 1447py; `api/` 100% `cores.` (0/983); 322 `from core.` self-imports inertes; borrado gateado |
| 20 | datetime.utcnow producción | ACTIVE (0 naked) | Solo `_naive_utcnow` intencional (`content_factory/models.py:17`) + `utcnow_iso` aware helper |
| 21 | Pydantic V2 `model_fields` | PARTIAL | `cores/credentials/vault.py:163,227` OK (`type(creds).model_fields`); `core/credentials/vault.py:161,224` deprecated (congelado) |
| 22 | Dead code `omega/moondownloader/tauri-windows-build` | DEAD → ausentes | Ya no existen en checkout; `graft/` 150M gitignored correcto |
| 23 | Versión | ACTIVE | 11 superficies 7.1.0; `sync_version.py` idempotente (exit 0) |
| 24 | `MoneyState.TRANSITIONS` duplicados | BROKEN → FIXED | `IN_REVIEW` ×2 + 7 terminales duplicados; dedup (2026-09-13), grafo sin cambio semántico |

## Siguiente (FASE 2 completada 2026-09-13)
- `GET /api/intelligence/feeds/health` vivo (14 passed `test_threat_intel_feeds`).
- `/feeds` y `/intelligence` health agregados a la matriz anterior (items 2-4,6,11).
- Pendiente productivo menor: `TaskAvailability` con productores reales; mapper dual state (cuando alguien lo pida).

## Qué NO tocar
`cores/events/*`, `cores/opportunity/engine.py`, `cores/validation/*`, `cognee`, `core/` (gate), workspaces business logic, providers OAR extra, nueva arch frontend.