# ROADMAP — OWNEX OMEGA v7.0+

**Source of Truth:** This file. Updated per session from code evidence.

---

## Legend

| Status | Meaning |
|--------|---------|
| ✅ **COMPLETED** | Production-ready, tests pass, integrated |
| 🟡 **IN PROGRESS** | Core works, integration/fixes pending |
| 🟢 **PREPARED** | Code exists, needs wiring/activation |
| 🔴 **PENDING** | Not started or stubbed |
| 💡 **FUTURE IDEAS** | Post-v7.0, Revenue Rule evaluated |

---

## ✅ COMPLETED (Production Ready)

| ID | Feature | Phase | Tests | Revenue Rule |
|----|---------|-------|-------|--------------|
| P01 | Autonomous 10-Stage Pipeline | FASE_3 | — | ✅ Detection/Learning |
| P02 | EventBus Unification | FASE_2 | — | ✅ Learning |
| P03 | Opportunity Score Engine | FASE_29 | 23 | ✅ Acceptance/Detection |
| P04 | Revenue Engine Multi-Platform | FASE_8 | — | ✅ Revenue |
| P05 | Health Center Unified | FASE_7 | 25 | ✅ Stability→Revenue |
| P06 | Offensive Engine (5 reasoners) | FASE_18 | 101 | ✅ Detection |
| P07 | Evidence Composer | FASE_18 | 37 | ✅ Evidence/Acceptance |
| P08 | Report Quality Gate + Acceptance | FASE_22 | 18 | ✅ Acceptance |
| P09 | RewardLearner Feedback Loop | FASE_4 | — | ✅ Learning/Detection |
| P10 | VerdictLearner Auto-Outcome | FASE_25 S-10 | 14 | ✅ Learning |
| P11 | Recon Enhancement (Naabu, dedup) | FASE_25 S-9 | 23 | ✅ Detection |
| P12 | Auto-Submission Pipeline | FASE_25 S-6 | 12 | ✅ Acceptance |
| P13 | AI Bounty Auto-Hunter | FASE_25 S-4 | 29 | ✅ Detection |
| P14 | Target Discovery Automator | FASE_25 S-7 | 25 | ✅ Detection |
| P15 | Command System (107 cmds) | FASE_20 | 45 | ✅ Autonomy |
| P16 | Hermes v2 (Events, Permissions, Security) | FASE_19 | 48 | ✅ Autonomy |
| P17 | Secrets Manager (AES-256-GCM) | FASE_7 | 11 | ✅ Stability |
| P18 | Extension SDK (Manifest, Hooks, Caps) | FASE_7 | — | 🟡 Infrastructure |
| P19 | Mission Control API + Frontend | FASE_18 | — | ✅ Observability |
| P20 | Copilot API Router | FASE_18 | — | ✅ Autonomy |
| P21 | Workflows Engine | FASE_18 | — | ✅ Autonomy |
| P22 | Aegis Security App | FASE_18 | — | ✅ Detection |
| P23 | Finance Core | FASE_18 | — | ✅ Revenue |
| P24 | Reports Core | FASE_18 | — | ✅ Acceptance |
| P25 | Documentation Platform (Auto) | FASE_18 | — | ✅ Learning |
| P26 | Tools: Amass, Naabu, Shodan, Uncover, Censys | Various | — | ✅ Detection |
| P27 | Discord Notifications (12 events) | FASE_18 | — | ✅ Observability |
| P28 | ARCA / Outlook Integrations | FASE_18 | — | ✅ Revenue |
| P29 | Linux Setup + Windows Installer (33 tools) | FASE_18 | — | ✅ Deployment |

---

## 🟡 IN PROGRESS (Core Works, Integration Pending)

| ID | Feature | Blockers | Effort | Target |
|----|---------|----------|--------|--------|
| IP01 | **Security Cycle E2E** | Executive Dashboard, Knowledge Capture, scheduler bootstrap, GamingConsole fake data | 3-4 hrs | **NEXT** |
| IP02 | **Desktop Release (Tauri)** | Never built, PyInstaller sidecar untested, credentials vault seed | 1-2 hrs | AFTER IP01 |

---

## 🟢 PREPARED (Code Exists, Needs Activation)

| ID | Feature | What's Ready | What's Missing |
|----|---------|--------------|----------------|
| PR01 | Extension Registry Integration | 13 extensions with manifest+connector, `verify_extensions.py` loads them | Scheduler hooks, cycle integration, capability wiring |
| PR02 | Evolution Engine | 9 modules in `core/evolution/` | EventBus hooks, scheduler jobs, API endpoints, tests |
| PR03 | GamingConsole Real Data | Frontend component exists, `ownexData.ts` service exists | `/api/activity` or `/api/system/state/events` endpoint |
| PR04 | AgentFleet Real Health | Component calls `/api/system/state` | Backend endpoint returns real agent status |

---

## 🔴 PENDING — OMEGA MULTI-CYCLE ARCHITECTURE (Revenue Rule Compliant)

| ID | Feature | Revenue Rule | Effort |
|----|---------|--------------|--------|
| OM01 | **Forge Cycle (Dev Bounties)** | ✅ Detection + Acceptance + Learning | 4-6 hrs |
| OM02 | **Pulse Cycle (AI Work / Microtasks)** | ✅ Detection + Acceptance + Learning | 4-6 hrs |
| OM03 | **Multi-Cycle Orchestrator** | ✅ Autonomy + Learning | 3-4 hrs |
| OM04 | **Autonomous Agents System (12 agents)** | ✅ Autonomy + Learning | 6-8 hrs |
| OM05 | **Continuous Sensors per Domain** | ✅ Detection | 4-6 hrs |
| OM06 | **Self-Repair System** | ✅ Stability → Revenue continuity | 3-4 hrs |
| OM07 | **Learning System (Post-cycle)** | ✅ Learning | 3-4 hrs |
| OM08 | **Mobile Companion (Android + Wear OS)** | ✅ Autonomy + Observability | 4-6 hrs |

---

## 🔴 PENDING (Deferred — Fails Revenue Rule)

| ID | Feature | Reason |
|----|---------|--------|
| PD01 | CI/CD Pipeline (GitHub Actions) | Deferred — no release blocker yet |
| PD02 | Repo Hygiene (216 modified, 50 untracked) | Deferred — commit after IP01+IP02 |
| PD03 | Extension Cycle Integration | **Fails Revenue Rule** — no direct detection/evidence/acceptance/learning |
| PD04 | Evolution Engine Wiring | **Fails Revenue Rule** — infrastructure only |
| PD05 | Smart Notifications Bridge | FASE_28 partial — needs frontend |

---

## 💡 FUTURE IDEAS (Post-v7.0, Revenue Rule Gate)

| Idea | Potential Revenue Rule | Status |
|------|------------------------|--------|
| LightRAG / Cognee / Graphiti for knowledge graph | Learning + Detection | Extensions ready |
| Skyvern / BrowserUse for visual recon | Detection | Extensions ready |
| Composio for tool orchestration | Autonomy | Extension ready |
| n8n / Kestra for workflow automation | Autonomy | Extensions ready |
| Langfuse for LLM observability | Learning | Extension ready |
| ORION Companion (Android + Wear OS) | Autonomy + Observability | Vision doc exists |
| Crypto Arbitrage / On-Chain Analysis | Revenue (new stream) | Separate project |
| Investment / Trading Bot | Revenue | Separate project |
| Sports Betting Bot | Revenue | Separate project |

---

## Dependency Graph (Critical Path)

```
IP01 Security Cycle E2E
    ├─ Executive Dashboard (CEO view)
    ├─ Knowledge Capture (learning metadata)
    ├─ Scheduler bootstrap job for Security Cycle
    └─ GamingConsole fake activityLog → real /api/activity
        │
        ▼
IP02 Desktop Release
    ├─ npm run tauri build
    ├─ PyInstaller sidecar
    ├─ Credentials vault seed
    └─ CSP WebSocket verify
        │
        ▼
OMEGA Multi-Cycle Architecture (Parallel, Revenue Rule Compliant)
    ├─ OM01 Forge Cycle (Dev Bounties)
    ├─ OM02 Pulse Cycle (AI Work)
    ├─ OM03 Multi-Cycle Orchestrator
    ├─ OM04 Autonomous Agents System
    ├─ OM05 Continuous Sensors
    ├─ OM06 Self-Repair System
    ├─ OM07 Learning System
    └─ OM08 Mobile Companion
```

---

## Sprint Definitions

| Sprint | Focus | Duration | Exit Criteria |
|--------|-------|----------|---------------|
| **Sprint 1** | Security Cycle E2E | 1 session | All 44 tests pass, SecurityCycle real data, Executive Dashboard, Knowledge Capture, GamingConsole real data |
| **Sprint 2** | Desktop Release | 1 session | `OWNEX.exe` builds, installs, runs on Windows |
| **Sprint 3** | Hardening + Hygiene | 1 session | 216 files committed/clean, CI/CD basic, verify scripts pass |
| **Sprint 4** | Forge Cycle (Dev Bounties) | 1-2 sessions | Forge cycle operational, Algora/Opire/Superteam integrated, CoderAgent wired |
| **Sprint 5** | Pulse Cycle (AI Work) | 1-2 sessions | Pulse cycle operational, Outlier/Mindrift/DataAnnotation integrated, BrowserAgent workers |
| **Sprint 6** | Multi-Cycle Orchestrator + Agents | 1-2 sessions | Cross-cycle resource allocation, 12 agents observing/learning 24/7 |
| **Sprint 7** | Self-Repair + Learning + Mobile | 1-2 sessions | Auto-repair active, post-cycle learning, Android/Wear OS companion |

---

## Version Milestones

| Version | Target | Features |
|---------|--------|----------|
| **7.0.1** | Sprint 1 done | Security Cycle E2E complete |
| **7.1.0** | Sprint 2 done | Desktop installer released |
| **7.2.0** | Sprint 3 done | Clean repo, CI/CD, production hardened |
| **8.0.0** | Sprint 4-6 done | Forge + Pulse + Orchestrator + Agents operational |
| **8.1.0** | Sprint 7 done | Self-Repair + Learning + Mobile Companion |
| **9.0.0** | Post-v8 | Extension/Evolution integration (if Revenue Rule passes) |