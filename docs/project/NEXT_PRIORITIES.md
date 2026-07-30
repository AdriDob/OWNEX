# NEXT PRIORITIES — OWNEX OMEGA

**Auto-ordered by architectural value + Revenue Rule. Updated per session.**

---

## Priority Scoring Formula

```
Priority = (Revenue_Impact × 10) + (Unblock_Value × 5) + (Effort_Inverse × 2) + (Risk_Reduction × 3)

Revenue_Impact: 0-10 (direct detection/evidence/acceptance/learning increase)
Unblock_Value: 0-10 (enables other work)
Effort_Inverse: 10=trivial, 1=major (lower effort = higher score)
Risk_Reduction: 0-10 (reduces failure surface)
```

---

## Current Sprint: **SPRINT 1 — Security Cycle E2E**

| # | Task | Score | Revenue Rule | Effort | Dependencies | Status |
|---|------|-------|--------------|--------|--------------|--------|
| **1** | ~~Fix `test_ensure_cycle` category mismatch~~ | ~~98~~ | ✅ All 4 | 10 min | None | ✅ **DONE** |
| **2** | Add Security Cycle bootstrap to scheduler | 95 | ✅ Detection+Learning | 30 min | #1 | 🔴 READY |
| **3** | Connect SecurityCycle.vue → real cycle data | 92 | ✅ Detection+Evidence | 30 min | #2 | 🔴 READY |
| **4** | Replace GamingConsole fake activityLog | 88 | ✅ Evidence+Learning | 20 min | None | 🔴 READY |
| **5** | Verify AgentFleet shows real agent health | 85 | ✅ Learning | 20 min | Backend endpoint | 🟡 PARTIAL |

**Sprint 1 Target:** All 44 tests pass, SecurityCycle real data, GamingConsole real data, AgentFleet real data.

---

## Next Sprint: **SPRINT 2 — Desktop Release**

| # | Task | Score | Revenue Rule | Effort | Dependencies | Status |
|---|------|-------|--------------|--------|--------------|--------|
| **1** | Run `npm run tauri build` | 90 | ✅ Autonomy (distribution) | 30-60 min | Sprint 1 done | 🔴 READY |
| **2** | PyInstaller sidecar (`start_backend.py` → `.exe`) | 85 | ✅ Autonomy | 20 min | #1 | 🔴 READY |
| **3** | Credentials vault seed (`opportunity.env`) | 80 | ✅ Stability→Revenue | 10 min | #1 | 🔴 READY |
| **4** | Verify CSP allows WebSocket (`ws://`) | 78 | ✅ Autonomy | 10 min | #1 | 🔴 READY |
| **5** | Smoke test installer on Windows | 75 | ✅ Autonomy | 30 min | #1-4 | 🔴 READY |

**Sprint 2 Target:** `OWNEX.exe` builds, installs, runs on Windows with terminal + API.

---

## Sprint 3: **Hardening + Hygiene** (Post-Release)

| # | Task | Score | Revenue Rule | Effort | Dependencies |
|---|------|-------|--------------|--------|--------------|
| **1** | Commit/clean 216 modified files | 70 | ❌ (hygiene) | 2 hrs | Sprint 2 |
| **2** | Basic CI/CD (GitHub Actions: lint + test) | 68 | ❌ (stability) | 1 hr | Sprint 2 |
| **3** | Run `verify_extensions.py` + `verify_system.py` | 65 | ❌ (validation) | 15 min | Sprint 2 |
| **4** | PostgreSQL dev config test | 60 | ❌ (prod parity) | 4 hrs | Sprint 2 |
| **5** | Structured logging (JSON) | 55 | ❌ (observability) | 1 day | Sprint 2 |

---

## **OMEGA MULTI-CYCLE ARCHITECTURE** (Revenue Rule Compliant — Ready to Build)

| Sprint | Cycle | Platforms | Agents | Revenue Rule | Effort |
|--------|-------|-----------|--------|--------------|--------|
| **4** | **Forge** (Dev Bounties) | Algora, Opire, Superteam, IssueHunt, Gitcoin, Bounties.network | CoderAgent, SpecAgent, TestAgent | ✅ Detection + Acceptance + Learning | 4-6 hrs |
| **5** | **Pulse** (AI Work / Microtasks) | Outlier, DataAnnotation, Mindrift, Remotasks, Clickworker, Appen | BrowserAgent, DataAgent, QualityAgent | ✅ Detection + Acceptance + Learning | 4-6 hrs |
| **6** | **Orchestrator + Agents** | Cross-cycle | 12 OMEGA Agents (Observer, Researcher, Planner, Architect, Developer, Reviewer, Validator, Documentation, Repair, Infrastructure, Learning, Evolution) | ✅ Autonomy + Learning | 6-8 hrs |
| **7** | **Self-Repair + Learning + Mobile** | All | Self-Repair, Post-Cycle Learning, Android + Wear OS Companion | ✅ Stability + Learning + Observability | 8-10 hrs |

### OMEGA Agent Roster (12 Autonomous Agents)

| Agent | Role | Domain | Continuous? |
|-------|------|--------|-------------|
| **Observer** | Continuous monitoring, anomaly detection | All | ✅ 24/7 |
| **Researcher** | Deep dive, threat intel, tech research | All | ✅ On-demand |
| **Planner** | Task decomposition, dependency resolution, scheduling | All | ✅ Per-cycle |
| **Architect** | Solution design, API contracts, data models | All | ✅ Per-task |
| **Developer** | Code generation, PoC, exploit, automation | All | ✅ Per-task |
| **Reviewer** | Code review, security review, quality gate | All | ✅ Per-task |
| **Validator** | Hypothesis validation, evidence verification, reproduction | All | ✅ Per-cycle |
| **Documentation** | Auto-docs, report generation, knowledge capture | All | ✅ Continuous |
| **Repair** | Auto-fix, self-heal, dependency resolution, config repair | Infra | ✅ 24/7 |
| **Infrastructure** | Provisioning, scaling, monitoring, deployment | Infra | ✅ 24/7 |
| **Learning** | Post-cycle evaluation, pattern extraction, weight updates | All | ✅ Post-cycle |
| **Evolution** | Propose improvements, run DESIGN→PREPARE→VALIDATE→PROPOSE | All | ✅ Weekly |

---

## Deferred (Revenue Rule Gate)

| Feature | Why Deferred | Activation Condition |
|---------|--------------|---------------------|
| Extension cycle integration (13) | No direct detection/evidence/acceptance/learning | Specific use case: e.g., LightRAG for evidence retrieval |
| Evolution engine wiring (9 modules) | Infrastructure only | Self-healing detects real production issue |
| Mobile Companion (Android/Wear) | ORION vision, not OWNEX core | Operator needs mobile approval |
| CI/CD advanced | No release blocker yet | Sprint 3 basic CI done |
| Crypto/Trading bots | Separate revenue streams | Validated paper trading strategy |

---

## Architectural Value Priorities (If Time)

| Priority | Initiative | Value | Effort |
|----------|------------|-------|--------|
| **A1** | EventBus → Redis (persistence, replay, multi-process) | High | 2 days |
| **A2** | Scheduler stages pluggable (not hardcoded) | Medium | 1 day |
| **A3** | Config consolidation (single source) | Medium | 4 hrs |
| **A4** | Feature flags system | Low | 2 days |
| **A5** | API versioning (/api/v1/) | Low | 1 day |

---

## Decision: What to Do RIGHT NOW

**Start Sprint 1, Task 2:** Add Security Cycle bootstrap in `api/scheduler.py` `ScanScheduler.start()`:

```python
async def start(self):
    # ... existing ...
    # Bootstrap Security Cycle if none exists
    await self._bootstrap_security_cycle()
```

**Then Task 3:** Frontend wiring (30 min).
**Then Task 4:** Fix GamingConsole (20 min).

**Total Sprint 1: ~2 hours → 100% Security Cycle E2E.**

---

## Why This Order?

1. **Revenue Rule compliance** — Every Sprint 1 task directly increases detection, evidence, acceptance, or learning
2. **Minimum intervention** — Fix test (10 min ✅) unblocks entire test suite; scheduler bootstrap (30 min) activates core product
3. **Unblocks desktop** — Sprint 2 needs clean test baseline
4. **Defers correctly** — Extensions/Evolution fail Revenue Rule today; no guilt, no waste
5. **OMEGA ready** — Multi-cycle architecture defined, Revenue Rule compliant, ready for Sprint 4+

---

## Quick Commands Reference

```bash
# Sprint 1
cd /home/adrie/projects/Rastro
# Task 2: Add bootstrap to scheduler
vim api/scheduler.py

# Verify scheduler bootstrap works
curl -X POST http://localhost:8000/api/security/cycle/start

# Verify SecurityCycle.vue data
curl http://localhost:8000/api/cycles/security/status

# Task 4: Fix GamingConsole
# Edit frontend/src/pages/GamingConsole.vue:39-48 → fetch from /api/system/state/events

# Sprint 2
npm run tauri build
# Fix any Rust/PyInstaller issues
```