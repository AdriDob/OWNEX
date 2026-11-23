# OWNEX Task Board — Multi-Agent Coordination (v1.0)

Prioritized queue. Single write-owner per task. Check `.ai/TASK_QUEUE.md` for the strategic backlog — this board tracks *agent assignments*.

> **Progress ledger**: `.ai/PROGRESS.md` is the canonical per-module advancement tracker (%, state, evidence, blocker, next action). Run `python3 scripts/progress.py` at session start and `--update` at session end — the delta vs `.ai/progress_snapshot.json` is the real progress. Update your module's row when closing work; UNKNOWN beats invented numbers.

## Priority order (from governance §19)

1. Security & data integrity
2. Critical errors
3. Architecture stability
4. Broken core functionality
5. Frontend↔backend integration
6. Persistence & contracts
7. Real connections
8. New features
9. Optimizations
10. Experiments

## Board

| # | Task | Owner | Depends on | Files | State | Notes |
|---|------|-------|-----------|-------|-------|-------|
| 1 | Live-validate IOL/PPI/Binance sync | user+agent | user credentials | `cores/brokers/` | BLOCKED | needs real creds |
| 2 | FX policy decision → capital engines wiring | user decision | #1 optional | `cores/capital/`, `core/investment/` | BLOCKED | currency mixing forbidden until decided |
| 3 | Remote jobs: AR/ES-specific feeds | Work Intelligence | — | `cores/opportunity/job_feeds.py` | IN_PROGRESS | feeds expandidos y verificados live: +getonbrd (LatAm/AR, JSON:API), +workingnomads, +himalayas (locationRestrictions→argentina_ok); InfoJobs/Tecnoempleo/Manfred descartados (404/403/WAF); pendiente: resolved company names (GoB expone solo company_id); yield medido 2026-11-20 (~296 listings, 71 argentina_ok; jobicy 39 + getonbrd 21 + workingnomads 10 lideran) |
| 4 | Perch E2E verification of OWNEX MCP | Connections | Perch install | `core/mcp_ownex_server.py` | TODO | consent flow ready |
| 5 | Consolidate `core/` vs `cores/` twin trees | Coordinator | ADR-0002 v2 accepted | both trees | IN_PROGRESS | phase-1 merged; event bus unified `bacaab8d`; adjudication session: 31 dead twins deleted (`99053839`,`35eac594`,`fb7b5e98`), 18 live-importer files restored after agent sweep `72a58b69`+`828db5e1`; key lesson: path-equal ≠ twin (validation/confidence false positive); remaining: 59 ties + per-domain decisions |
| 6 | npm audit fix (devDeps) | Frontend | — | `frontend/package*.json`, `package-lock.json` | DONE | vitest/^4.1.12 + ownex-contracts ^1→^4.1.12 (critical cleared); audit 9→6 moderate, all dev-only chains needing breaking bumps (vue-tsc 3.x dependabot branch exists) |
| 7 | Crypto/quant: real strategies | Finance | capital data flow | `core/quant/` (empty dirs) | DEFERRED | dirs exist but empty — don't build until income flows |
| 8 | Investment Hub: permisos por conexión (escalera de autonomía §H) | Connections | — | `cores/connections/permissions.py`, `api/routers/connection_manager.py`, `api/routers/investment.py` | DONE | deny-by-default, escalado contiguo, ack humano para LIVE, kill switch, audit JSONL; gate `LIVE_ORDER` en órdenes reales; UI en `PermissionModePanel.vue` |
| 9 | Conectores Coinbase/Kraken/Bybit (read-only + verificación pública) | Connections | — | `cores/brokers/cex_client.py`, `cores/connections/catalog.py`, `api/routers/connection_manager.py` | DONE | verificado live sin keys: coinbase 1154 markets / BTC-USD 58051.2, kraken 1436 / 58056.8, bybit 3681 / BTC-USDT 58149.4; pendiente sync con keys reales |
| 10 | OWNEX Desktop Finalization — App Shell + QA visual | devin-frontend-finalization | — | `frontend/src/components/layout/`, `frontend/qa/`, `frontend/FRONTEND_RUNBOOK.md` | DONE | `eed542a4`: AppLayout con router-view real, tokens.css `:root` fix, sidebar 8 secciones, harness QA (`capture.cjs` sin/con auth), runbook; build Vite OK (2026-11-23) |
| 11 | Investment Hub: strategy attribution + patas sin fill | Investment | — | `core/investment/`, `api/routers/investment.py`, `scripts/paper_trade.py` | DONE | `0c4162137`: `TradeGroupMetrics`, `LEG_UNHEDGED`, `net_pnl_completeness`+currency, `strategy_attribution` en `/metrics`, `GlobalArbitrageAdapter`, CLI paper-trade; 208 tests focalizados verdes |
| 12 | Discovery: cuarentena de fuentes placeholder | Discovery | — | `core/opportunity/source_discovery.py`, `api/routers/discovery.py` | DONE | `04efdff36`: hosts RFC 2606/6761 y base URLs placeholder no se registran como live, se reportan `quarantined`; 187 tests del módulo verdes |
| 13 | Security isolation: sandbox + credential broker canónicos | Security | — | `core/security/` | DONE | `d7188cc24`: consolidado en `core/security/` y borrado el duplicado `cores/security/`; fix del `RLIMIT_AS` del padre (SIGSEGV en cada fork), broker ya no arma `python -c` roto; 17 tests (`tests/test_security_isolation.py`). Broker cableado a los workers de Factory (resolve_credential → BaseExecutor.credential) — exp/fail-closed/evidencia asegurada |
| 14 | Open Source Factory slice: repair autopilot→CoderAgent→sandbox→delivery (audit B1–B7, PR #72) | devin-factory-slice | PR #72 audit | `core/autonomy/`, `core/cycles/`, `core/execution_queue/`, `core/security/` | DONE | `find_path()` BFS en la máquina de estados; autopiloto idempotente con transiciones legales y repo_url solo desde URL GitHub issue/PR (si no → BLOCKED); CoderAgent canónico `core.autonomy` (callers `cores.autonomy.*` rotos corregidos — `cores/autonomy/` es dir muerto sombreado por `cores/autonomy.py`, pendiente borrado en consolidación #5); clone path único por tarea; patch aplicado ANTES de tests con guard anti-traversal + `patch.diff`/`changed_files.json`; tests+install SOLO en Sandbox docker (writable efímero, red solo en install, fail-closed sin daemon, imagen por lenguaje); PR eliminado del flujo autónomo → delivery package local + `publish_delivery()` como única vía de publicación aprobada; verdicts: ready_for_owner_review/blocked/tests_failed/low_confidence; 18 tests nuevos (`test_factory_slice.py`) + security_isolation actualizado, todo verde. Follow-up: `POST /execution-queue/{id}/approve` → `approve_and_execute` → `_execute_coder_action` publica `delivery_package` vía `publish_delivery()` (submitted solo si PR real; pr_url a payload); 21 tests verdes |

## Rules

- Before starting: record commit base, declare files, check registry for conflicts.
- Before finishing: run relevant tests + ruff/biome, file completion report, update this board.
| 15 | Weekly-review P0/P1 hardening: withdrawal evidence, truth-layer downgrade, queue transition gate, computer-use dry_run | devin-factory-slice | weekly review 2026-11-23 | `cores/financial/`, `api/routers/financial_truth.py`, `api/routers/execution_queue.py`, `api/routers/copilot.py`, `tests/test_financial_evidence.py` | DONE | `complete_withdrawal` exige evidencia (tx_hash o proof; UNCONFIRMED nunca completa); endpoint `/withdrawals/{id}/complete` → 400 sin evidencia; `TruthLayer.get_state` degrada `WITHDRAWAL_COMPLETED` sin evidencia a PENDING (nunca VERIFIED_REAL); `/execution-queue/{id}/transition` bloquea targets executing/submitted/verification/paid (solo executor/approve/payment-evidence); `ComputerUseRequest.dry_run` default True (plan-only salvo opt-in explícito); review items descartados como ya-resueltos: sandbox fail-closed (`43cf3f68b`), `is_paused` es property usada sin `()` en `_order_gate`; 13 tests nuevos verdes, 111 focalizados OK |
| 16 | P1 hardening: credential broker deny-by-default + investment integrity | devin-factory-slice | weekly review follow-up | `core/opportunity/executors/`, `core/investment/`, `tests/test_investment_integrity.py` | DONE | `BaseExecutor.credential()`: fallback config/env no-scoped ahora opt-in (`allow_unscoped_credentials`, default deny) — asignación de broker ausente ⇒ None; `TaskmarketExecutor` resuelve `taskmarket_identity`/`taskmarket_api_key` por broker en cada acción (nada cacheado, READ_ONLY para list_pitches, EXECUTION para mutantes), eliminado `load_credentials`+env del `__init__`; `InvestmentMetrics._compute_metrics` excluye trades con net declarado INCOMPLETE/PARTIAL/UNKNOWN (legacy "" conserva comportamiento) → nuevo `RiskMetrics.incomplete_trades` + `consolidated_metrics`; atribución: duplicados ahora EXCLUIDOS de agregados (antes solo flaggeados) → `excluded_reasons["duplicate"]`; 4 tests nuevos + 2 actualizados; 169 tests investment + 52 credential verdes. NOTA: lane paralelo ya modificó `cores/opportunity/executors/__init__.py` eliminando el fallback por completo (sin opt-in) — divergencia core/ vs cores/ queda para consolidación #5 |
