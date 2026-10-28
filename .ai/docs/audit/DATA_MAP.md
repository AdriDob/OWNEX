# DATA MAP — OWNEX (2026-09-30)

## Database (SQLite + SQLAlchemy + Alembic)

### Tables (21) — NO FINANCIAL TABLES

| Table | Purpose | Owner |
|-------|---------|-------|
| `users` | User accounts | `database/models.py` |
| `sessions` | Auth sessions | `cores/auth/` |
| `targets` | Bug bounty targets | `api/routers/targets.py` |
| `endpoints` | Target endpoints | `api/routers/targets.py` |
| `scan_runs` | Scan executions | `api/routers/scans.py` |
| `findings` | Vulnerability findings | `api/routers/findings.py` |
| `reports` | Generated reports | `api/routers/reports.py` |
| `verdicts` | Finding verdicts | `api/routers/verdicts.py` |
| `programs` | Bug bounty programs | `api/routers/programs.py` |
| `scan_configs` | Scan configurations | `api/routers/scans.py` |
| `endpoint_configs` | Endpoint configs | `api/routers/targets.py` |
| `endpoint_parameters` | Endpoint params | `api/routers/targets.py` |
| `endpoint_auth` | Endpoint auth | `api/routers/targets.py` |
| `scan_findings` | Scan-finding links | `api/routers/scans.py` |
| `program_scopes` | Program scopes | `api/routers/programs.py` |
| `program_rewards` | Program rewards | `api/routers/programs.py` |
| `program_domains` | Program domains | `api/routers/programs.py` |
| `scheduled_scans` | Scheduled scans | `api/routers/scans.py` |
| `audit_log` | Security audit trail | `cores/audit_log.py` |
| `device_identities` | Device auth | `cores/identity/` |
| `api_keys` | Stored API keys | `api/routers/api_keys.py` |

**CRITICAL: NO financial tables** — no `revenue`, `payouts`, `payments`, `ledger`, `transactions`, `capital`, `investments` tables.

---

## File-Based Stores (JSON/JSONL)

### Primary Data Root: `~/.ownex/` (11,437 files)

| File/Dir | Owner | Format | Contents |
|----------|-------|--------|----------|
| `workbank.json` | `cores/direct_work_engine/workbank.py` | JSON | Deliverable work items |
| `payment_pipeline.json` | `cores/direct_work_engine/payment_pipeline.py` | JSON | Payment tracking |
| `projects.json` | `cores/projects/` | JSON | Project metadata |
| `execution_queue.json` | `cores/execution_queue/` | JSON | Task queue |
| `capabilities_registry.json` | `cores/capabilities/` | JSON | Tool capabilities |
| `capability_approvals.json` | `cores/capabilities/` | JSON | Approvals |
| `curated_sources.json` | `cores/direct_work_engine/source_registry.py` | JSON | Source list |
| `alerts_state.json` | `api/routers/alerts.py` | JSON | Alert state |
| `infinite_sources_state.json` | `cores/infinite_sources` | JSON | Source state |
| `tool_usage.json` | `cores/tools/ecosystem.py` | JSON | Tool usage stats |
| `trading/trading_state.json` | `cores/trading/store.py` | JSON | Trading state |
| `voice_profile.json` | `cores/voice/voice_engine.py` | JSON | Voice settings |
| `ultra_fast_state.json` | `cores/ultra_fast_income` | JSON | State |
| `desktop_device.json` | `desktop/native/services/api_client.py` | JSON | Device info |
| `discovery_cache/engine_state.json` | `cores/discovery_engine/` | JSON | Cache |
| `opportunity_discovery/discovery_*.json` | 40 snapshots | Timestamped |
| `knowledge/config.json` | `cores/knowledge/` | JSON | Config |
| `knowledge/qa_evidence/*` | `cores/knowledge/` | JSONL | QA evidence |
| `license.json` | Licensing | JSON | License state |
| `hhd_state.json` | | JSON | HHD state |
| `economic_feedback/` | 2 files | JSON | Feedback snapshots |
| `learning/` | 2 files | JSONL | Acceptance outcomes, reward funnel |
| `first_money/progress.json` | `cores/first_money/` | JSON | First money progress |
| `personal_infrastructure/` | 5 files | JSON | Infrastructure |
| `wear_os/` | 2 files | JSON | Wear OS state |
| `training/training_plans.json` | | JSON | Training plans |
| `hunter/state.json` | | JSON | Hunter state |
| `identity/identity.json` | | JSON | Identity |

### Subdir: `economic_feedback/`
| File | Content |
|------|---------|
| `snapshot.json` | Economic snapshot |
| `history.jsonl` | History log |

### Subdir: `learning/`
| File | Content |
|------|---------|
| `acceptance_outcomes.jsonl` | Acceptance outcomes |
| `reward_funnel.jsonl` | Reward funnel |

### Subdir: `economic_feedback/`
| File | Content |
|------|---------|
| `snapshot.json` | Economic snapshot |
| `history.jsonl` | History log |

### Subdir: `learning/`
| File | Content |
|------|---------|
| `acceptance_outcomes.jsonl` | Acceptance outcomes |
| `reward_funnel.jsonl` | Reward funnel |

---

## Subdir: `economic_feedback/`
| File | Content |
|------|---------|
| `snapshot.json` | Economic snapshot |
| `history.jsonl` | History log |

### Subdir: `learning/`
| File | Content |
|------|---------|
| `acceptance_outcomes.jsonl` | Acceptance outcomes |
| `reward_funnel.jsonl` | Reward funnel |

---

## Subdir: `economic_feedback/`
| File | Content |
|------|---------|
| `snapshot.json` | Economic snapshot |
| `history.jsonl` | History log |

### Subdir: `learning/`
| File | Content |
|------|---------|
| `acceptance_outcomes.jsonl` | Acceptance outcomes |
| `reward_funnel.jsonl` | Reward funnel |

---

## Secondary Data Root: `~/.orion/` (Legacy)

| File/Dir | Content |
|----------|---------|
| `identity_vault.json` | Encrypted credentials (AES-256-GCM) |
| `identity_vault.key` | **32-byte raw key, chmod 600 — SINGLE MOST CRITICAL FILE** |
| `config.sh` | Config |
| `identity_vault.json.backup` | Backup |
| `database/orion.db` | Legacy SQLite |
| `config.sh.backup` | Backup |

---

## Subdir: `~/.config/ownex/`
| File | Content |
|------|---------|
| `trading.json` | Trading config |

---

## Dev-Only Stores (`<repo>/data/`)

| File | Owner |
|------|-------|
| `workbank.json` | `cores/direct_work_engine/workbank.py` |
| `affiliate.json` | `cores/affiliate.py` |
| `ecommerce_outreach.json` | `cores/ecommerce/outreach.py` |
| `ecommerce_publish_queue.json` | `cores/ecommerce/publish_queue.py` |
| `ecommerce_suppliers.json` | `cores/ecommerce/engine.py` |
| `execution_queue.json` | `cores/execution_queue/` |
| `capabilities_registry.json` | `cores/capabilities/` |
| `capability_approvals.json` | `cores/capabilities/` |
| `curated_sources.json` | `cores/direct_work_engine/source_registry.py` |
| `alerts_state.json` | `api/routers/alerts.py` |
| `infinite_sources_state.json` | `cores/infinite_sources` |
| `tool_usage.json` | `cores/tools/ecosystem.py` |
| `trading/trading_state.json` | `cores/trading/store.py` |
| `voice_profile.json` | `cores/voice/voice_engine.py` |
| `ultra_fast_state.json` | `cores/ultra_fast_income` |
| `desktop_device.json` | `desktop/native/services/api_client.py` |
| `discovery_cache/engine_state.json` | `cores/discovery_engine/` |
| `opportunity_discovery/discovery_*.json` | 40 snapshots |
| `knowledge/config.json` | `cores/knowledge/` |
| `knowledge/qa_evidence/*` | JSONL |
| `trading/trading_state.json` | `cores/trading/store.py` |
| `voice_profile.json` | `cores/voice/voice_engine.py` |
| `ultra_fast_state.json` | `cores/ultra_fast_income` |
| `desktop_device.json` | `desktop/native/services/api_client.py` |

---

## SQLite Databases

| Path | Purpose | Owner |
|------|---------|-------|
| `database/catseye.db` | Dev DB (default) | SQLAlchemy |
| `~/.ownex/database/knowledge.db` | Knowledge graph | `cores/knowledge/` |
| `~/.ownex/database/recovery_history.db` | Recovery log | `cores/recovery/` |
| `~/.ownex/database/{memory,orion,orion_core,odyssey}.db` | App-specific | Various |
| `~/.ownex/database/knowledge_graph_kg_test_*.db` | **11,057 test files** | **TEST POLLUTION** |

---

## Database Models (SQLAlchemy)

| Model | Table | Module |
|-------|-------|--------|
| `User` | `users` | `database/models.py` |
| `Session` | `sessions` | `database/models.py` |
| `Target` | `targets` | `database/models.py` |
| `Endpoint` | `endpoints` | `database/models.py` |
| `ScanRun` | `scan_runs` | `database/models.py` |
| `Finding` | `findings` | `database/models.py` |
| `Report` | `reports` | `database/models.py` |
| `Verdict` | `verdicts` | `database/models.py` |
| `Program` | `programs` | `database/models.py` |
| `ScanConfig` | `scan_configs` | `database/models.py` |
| `EndpointConfig` | `endpoint_configs` | `database/models.py` |
| `EndpointParameter` | `endpoint_parameters` | `database/models.py` |
| `EndpointAuth` | `endpoint_auth` | `database/models.py` |
| `ScanFinding` | `scan_findings` | `database/models.py` |
| `ProgramScope` | `program_scopes` | `database/models.py` |
| `ProgramReward` | `program_rewards` | `database/models.py` |
| `ProgramDomain` | `program_domains` | `database/models.py` |
| `ScheduledScan` | `scheduled_scans` | `database/models.py` |
| `AuditLog` | `audit_log` | `cores/audit_log.py` |
| `DeviceIdentity` | `device_identities` | `cores/identity/` |
| `ApiKey` | `api_keys` | `api/routers/api_keys.py` |

---

## Financial Data (CRITICAL: NO SQL TABLES)

| Concept | Location | Persistence |
|---------|----------|-------------|
| Revenue | `cores/revenue_tracker/` (memory) + `workbank.json` + `submission_queue.json` | JSON files only |
| Payouts | `payment_pipeline.json` | JSON |
| Ledger | `cores/revenue/` + `cores/revenue_tracker/` | Memory + JSON |
| Capital | `cores/financial/` | JSON |
| Investments | `workbank.json` + `investment.json` | JSON |
| Trajectory | `cores/economic_trajectory/` | Memory + JSON |

**CRITICAL**: `RevenueTracker` (`cores/revenue_tracker/revenue_tracker.py:355`) is **memory-only** — no DB, no file persistence. Recovery only from `workbank.json` + `submission_queue.json`.

---

## Data Ownership Matrix

| Domain | Owner Module | Store | Single Owner? |
|--------|-------------|-------|---------------|
| Opportunities | `cores/opportunity/` | SQLite + JSON | ⚠️ Shared with `direct_work_engine` |
| Work Items | `cores/direct_work_engine/` | `workbank.json` | ✅ |
| Revenue | `cores/revenue/` + `revenue_tracker/` | Memory + JSON | ❌ 2 owners |
| Capital | `cores/financial/` | JSON | ✅ |
| Findings | `cores/findings/` | SQLite | ✅ |
| Reports | `cores/reports/` | SQLite | ✅ |
| Targets | `api/routers/targets.py` | SQLite | ✅ |
| Credentials | `cores/identity_vault.py` | `~/.orion/identity_vault.json` (encrypted) | ✅ |
| Settings | `stores/settings.ts` | localStorage + JSON | ✅ |
| Identity | `cores/identity/` | `~/.orion/identity_vault.json` | ✅ |
| Targets (live) | `cores/direct_work_engine/` | `curated_sources.json` | ✅ |

---

## Data Flow (Critical Paths)

```
Source → Adapter → Normalizer → Deduplicator → Opportunity
                                        ↓
                    Eligibility → Technical Score + Economic Score
                                        ↓
                            Human Gate → Work Item → Execution
                                                          ↓
                                              Evidence → Verdict → Finding/Result
                                                              ↓
                                                      Payment → Revenue → Capital
```

---

## Data Quality Issues

| Issue | Location | Severity |
|-------|----------|----------|
| 11,057 test DBs in `~/.ownex/database/` | `~/.ownex/database/knowledge_graph_kg_test_*.db` | HIGH (pollution) |
| 190 distinct store filename literals | `cores/` + `api/` | HIGH (no registry) |
| 5 distinct store roots | `~/.ownex/`, `~/.orion/`, `~/.config/ownex/`, `<repo>/data/`, `database/` | HIGH |
| `RevenueTracker` memory-only | `cores/revenue_tracker/revenue_tracker.py:355` | CRITICAL |
| No financial SQL tables | `database/models.py` | CRITICAL |
| Test DB pollution in prod data dir | `~/.ownex/database/knowledge_graph_kg_test_*.db` | HIGH |
| `aiohttp` missing for sidecar | `cores/direct_work_engine/autonomous_discovery.py` | HIGH |
| Test DB pollution in `~/.ownex/database/` | 11,057 files | HIGH |