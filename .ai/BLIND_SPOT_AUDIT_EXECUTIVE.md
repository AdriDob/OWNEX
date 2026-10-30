# OWNEX — BLIND SPOT ELIMINATION: EXECUTIVE DIAGNOSIS

**Audit Phase**: A (Diagnóstico) — completed
**Audit Date**: 2026-10-13
**Status**: Findings catalogued, priorities assigned, implementation planned

## 1. EXECUTIVE SUMMARY

OWNEX has **3 HIGH**, **5 MEDIUM**, and **0 CRITICAL** severity blind spots in the resiliency/observability audit, plus **4 additional HIGH-severity findings** across finance, shutdown, and API layers. The system is functional but has several modes of failure that could cause data loss, silent error swallowing, or uncontrolled behavior under stress.

**Critical pattern**: 4302 of 4554 `except` clauses across the codebase are `bare except:` (no exception type specified), which means any unexpected error is silently swallowed and execution continues as if nothing happened.

---

## 2. SEVERITY DISTRIBUTION

| Severity | Count | Primary Areas |
|----------|-------|--------------|
| **CRITICAL** | 0 | — |
| **HIGH** | 7 | Bare except (4302 patterns), Finisher boot recovery, Trading connectors without retry, Shutdown sys.exit(0), DB integrity, API shutdown, Opportunity adapters without retry |
| **MEDIUM** | 5 | Drain bug, No worker heartbeat, Disk full handling, Connection pool exhaustion, No circuit breaker in adapters |
| **LOW** | 10+ | Well-managed (PID reuse, WAL checkpoint, Graceful shutdown, etc.) |

---

## 3. KEY FINDINGS BY DOMAIN

### 3.1 Data Integrity & Idempotency

| ID | Finding | Evidence | Severity |
|----|---------|----------|----------|
| D1 | **4302 bare `except:` patterns** across cores/, api/, scripts/ | `python3 count_audit.py` found 4554 lines with `except`; 4302 are bare `except:` (no exception type). Any unexpected error silently swallows and continues. Example: `cores/finance/store.py:88`, `cores/self_healing/system.py:49`, `api/main.py:396` | **HIGH** |
| D2 | **No idempotency keys** for financial operations | Transaction creation in `cores/finance/store.py:98` (`add_transaction`) overwrites existing entries by ID without check. No deduplication of external operation results. | **MEDIUM** |
| D3 | **No reconciliation** after external API calls | Opportunity adapters (`cores/opportunity/adapters/`) fetch data and store it without verifying against source. No reconcilation loop. | **MEDIUM** |

### 3.2 Resilience & Recovery

| ID | Finding | Evidence | Severity |
|----|---------|----------|----------|
| R1 | **Finisher has no state recovery on boot** | `scripts/finisher/main.py:109-148` — `_load()` reads JSON but has no logic to detect workers in RUNNING/STARTING state and mark them CRASHED. Tasks left RUNNING never complete. | **HIGH** |
| R2 | **Trading connectors have no retry with backoff** | `cores/trading/connectors/binance.py:50-83`, `coingecko.py:49-101` — use `requests.get(timeout=10)` but return `[]` on any error without retry. Pattern already exists in `jupiter.py` with retry. | **HIGH** |
| R3 | **Opportunity adapters have no retry** | `cores/opportunity/adapters/forge_legacy.py:75-125`, `security_bounty.py:29-71` — same pattern. No `base_retry_delay`, `max_retry_delay`. | **HIGH** |
| R4 | **Shutdown endpoint uses sys.exit(0)** | `api/main.py:950-965` — `/api/shutdown` calls `asyncio.create_task(_delayed_exit())` then `sys.exit(0)` after 0.5s. Does not wait for lifespan to cleanly shut down scheduler, agents, DB connections. | **HIGH** |
| R5 | **No database integrity check on boot** | `database/db.py:130-137` — PRAGMAs set but no `PRAGMA integrity_check`. If WAL corrupts, app fails on first query with OperationalError. | **HIGH** |
| R6 | **No disk full / connection pool exhaustion handling** | `database/db.py:91-93` — default SQLAlchemy QueuePool with no explicit pool_size. No try/except around commits for `sqlite3.OperationalError: database or disk is full`. | **MEDIUM** |
| R7 | **No periodic worker heartbeat** | `scripts/finisher/worker.py:95-101` — heartbeat only on `update_worker()`, not during task execution. Worker hangs undetected until timeout (1800s default). | **MEDIUM** |

### 3.3 Security & Privacy

| ID | Finding | Evidence | Severity |
|----|---------|----------|----------|
| S1 | **4302 bare `except:` patterns** | Same as D1 — silent error swallowing is a security risk. Exceptions that should propagate (auth errors, validation errors) are consumed and hidden. | **HIGH** |
| S2 | **No circuit breaker in external adapters** | `cores/opportunity/adapters/` and `cores/trading/connectors/` have no circuit breaker. Failed API keeps being called at full rate. `cores/recovery/circuit_breaker.py` exists but not wired. | **MEDIUM** |

### 3.4 FINISHER Deep Dive

| ID | Finding | Evidence | Severity |
|----|---------|----------|----------|
| F1 | **Drain loop bug with VERIFYING tasks** | `scripts/finisher/main.py:313-360` — when deadline passes, `running_still` only checks RUNNING and VERIFYING tasks, but `running` variable includes both. If only VERIFYING tasks remain, drain exits prematurely and tasks stay VERIFYING forever. | **MEDIUM** |
| F2 | **No checkpoint recovery after crash** | Checkpoints are saved (checkpoint.py) but no automatic recovery on restart. State is loaded from JSON, not reconstructed from checkpoints. | **MEDIUM** |
| F3 | **Graceful shutdown implemented** | `scripts/finisher/main.py:670-685` — `shutdown()` terminates workers, frees locks, writes final report. Well-designed compared to API shutdown. | — (positive) |

### 3.5 Financial Tracking

| ID | Finding | Evidence | Severity |
|----|---------|----------|----------|
| FC1 | **No distinction pending/confirmed/available revenue** | `api/routers/finance.py` and `cores/finance/engine.py` track income/expenses but cannot clearly separate expected vs confirmed vs available. Revenue can be double-counted across sources. | **MEDIUM** |
| FC2 | **No budget enforcement** | `OvernightConfig` has `max_tasks` and `max_duration` but no code enforces them during execution — only checked at loop start of each `_tick()`. | **LOW** |

---

## 4. PRIORITIZED IMPLEMENTATION ROADMAP

### Phase A: Immediate Fixes (This Sprint)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| A1 | **Add exception types to bare `except:` clauses** — minimal change: add `except Exception as e:` where bare except was, or remove try/except entirely if the error should propagate. Target: 100 highest-impact locations first (finance store, health checks, API endpoints). | 1-2 days | Prevents silent error swallowing — highest ROI |
| A2 | **Add `PRAGMA integrity_check` on DB boot** — `database/db.py:130-137`, add `conn.execute(text("PRAGMA integrity_check"))` and fail startup if not OK. | 0.5 day | Catches DB corruption early |
| A3 | **Add retry with backoff to trading connectors** — replicate pattern from `cores/trading/dex/jupiter.py:155-195`. Add `base_retry_delay`, `max_retry_delay`, `max_retries`. | 1 day | Prevents cascading failures on external API blips |
| A4 | **Fix shutdown endpoint** — replace `sys.exit(0)` with proper signal handling that waits for lifespan cleanup task completion. Use `asyncio.Event()` or similar. | 0.5 day | Ensures clean shutdown, no resource leaks |

### Phase B: This Week

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| B1 | **Add Finisher state recovery on boot** — detect RUNNING/STARTING workers, mark them CRASHED, reset their tasks to READY with failure_reason. | 2 days | Prevents stuck tasks after restart |
| B2 | **Add retry with backoff to opportunity adapters** — same pattern as trading connectors. Add circuit breaker integration. | 2 days | Improves reliability of opportunity ingestion |
| B3 | **Add disk full handling** — wrap DB commit attempts in try/except for `sqlite3.OperationalError`, log and degrade gracefully. | 1 day | Prevents crashes from full disk |
| B4 | **Add connection pool sizing** — configure `pool_size` and `max_overflow` in `database.db` based on expected concurrency. | 0.5 day | Prevents connection exhaustion under load |

### Phase C: Next Sprint

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| C1 | **Add periodic worker heartbeat** — send heartbeat every 30s during task execution, detect hangs before timeout. | 2 days | Faster detection of stuck workers |
| C2 | **Add circuit breaker to external adapters** — wire `cores/recovery/circuit_breaker.py` into opportunity and trading adapters. | 3 days | Prevents failed API from hammering system |
| C3 | **Fix drain loop VERIFYING bug** — adjust condition to properly detect all non-terminal task states. | 0.5 day | Prevents tasks stuck in VERIFYING state |
| C4 | **Add budget enforcement** — ensure `task_budget_exhausted()` and `past_deadline()` are checked at appropriate points in `_tick()`, not just once per loop. | 1 day | Prevents unbounded runs |

### Phase D: Future (Optional)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| D1 | **Full idempotency key system** — dedup keys for all financial operations, external task results. | 5+ days | Eliminates duplicate operations entirely |
| D2 | **Complete financial reconciliation** — automated matching of local transactions vs provider statements. | 5+ days | Accurate financial tracking |
| D3 | **Comprehensive observability** — structured logging with correlation IDs, metrics for all critical paths, alerting on degradation. | 5+ days | Better operational visibility |

---

## 5. CHANGES ALREADY MADE DURING THIS AUDIT

| Change | File | Impact |
|--------|------|--------|
| Identified 4302 bare `except:` patterns | Across codebase | Diagnosis complete — next: fix |
| Identified Finisher boot recovery gap | `scripts/finisher/main.py:109-148` | Documented for Phase B |
| Identified trading/opportunity adapter retry gaps | `cores/trading/connectors/`, `cores/opportunity/adapters/` | Documented for Phase B |
| Identified shutdown sys.exit(0) issue | `api/main.py:950-965` | Documented for Phase A |
| Identified DB integrity check gap | `database/db.py:130-137` | Documented for Phase A |
| Verified PID reuse already handled (create_time+PID) | `scripts/finisher/worker.py:34-59` | No action needed |
| Verified path locks already implemented | `scripts/finisher/locks.py` | No action needed |
| Verified WAL checkpoint on boot exists | `database/db.py:342` | No action needed |
| Verified graceful Finisher shutdown exists | `scripts/finisher/main.py:670-685` | No action needed |
| Verified stale scan recovery exists | `cores/orchestrator/scan_service.py:209-243` | No action needed |

---

## 6. RISKS IF NOT ADDRESSED

| Risk | Probability | Impact |
|------|-------------|--------|
| **Silent error swallowing** — critical operations fail without any log, user sees success | High | Very High — data corruption, financial loss, stuck workflows |
| **Stuck tasks after restart** — Finisher reboot leaves RUNNING tasks forever | Medium | High — automation reliability degrades over time |
| **Cascading API failures** — no retry/backoff means one bad API takes down whole pipeline | Medium | High — loss of opportunity detection, stale data |
| **Unclean shutdown** — sys.exit(0) before lifespan finishes | Medium | Medium — resource leaks, inconsistent state |
| **DB corruption undetected** — no integrity check means corruption silently spreads | Low | High — data recovery difficult or impossible |
| **Unbounded resource consumption** — no disk full/pool exhaustion handling | Medium | Medium — sudden crashes, downtime |

---

## 7. MEASURES OF SUCCESS (Post-Implementation)

- [ ] 0 bare `except:` patterns remain in production code (all have `except Exception as e:` or specific exception types)
- [ ] DB boot includes `PRAGMA integrity_check` that passes
- [ ] Trading and opportunity adapters have retry with exponential backoff
- [ ] Shutdown endpoint waits for graceful cleanup before exiting
- [ ] Finisher boot recovery marks stale RUNNING tasks as CRASHED and resets them
- [ ] Worker heartbeat detected within 60s of a hang (vs current 1800s timeout)
- [ ] System handles disk full gracefully without crashing

---

## 8. NEXT STEPS

1. **Owner approval**: Review and prioritize the Phase A fixes (A1-A4 above)
2. **Implement Phase A** (this sprint: 3-4 days)
3. **Review and implement Phase B** (this week: 6-8 days)
4. **Continue through phases** as capacity allows
5. **Re-audit** after each phase to verify no regressions
6. **Update documentation** for any new patterns introduced

**Core principle**: Fix the highest-impact, lowest-effort items first. The 4302 bare `except:` patterns are the single highest-ROI fix — each one is a potential silent failure waiting to happen.

---
*Diagnosis generated by blind spot elimination audit per OWNEX Megaprompt 03. Based on analysis of 2653 files, 33682 symbols, 71024 edges. No production data modified. All findings verified via code review only.*