# OWNEX — Autonomous Work Operating System

<p align="center">
  <strong>Autonomous Work Operating System</strong> 📡
</p>

<p align="center">
  <sub>Version: <code>9.0.0</code> · Python 3.11+ · FastAPI · Vue 3 · Tauri v2</sub>
</p>

<p align="center">
  <strong>👁️ Mission Control</strong> &bull; <strong>🛡️ Security Cycle</strong> &bull; <strong>💰 Revenue Engine</strong> &bull; <strong>🤖 MERLIN</strong> &bull; <strong>⚙️ Automation</strong> &bull; <strong>🧠 Intelligence</strong>
</p>

---

## Table of Contents

<details>
<summary>Click to expand 📖</summary>

1. [Overview](#overview)
2. [Product](#product)
3. [Architecture](#architecture)
4. [How a Day Runs](#how-a-day-runs)
5. [FAQ](#faq)
6. [Quick Start](#quick-start)
7. [Development](#development)
8. [Security](#security)
9. [Project Status](#project-status)
10. [Roadmap](#roadmap)
11. [Branding](#branding)
12. [Documentation](#documentation)
13. [License](#license)

</details>

---

## Overview 🚀

> **OWNEX** (pronounced *OH-neks*) — *Personal Autonomous Work Operating System*.

OWNEX is an autonomous work operating system that continuously discovers, understands, evaluates, organizes and prepares digital work opportunities while coordinating tools, agents, models and information.

### The concept 💡

OWNEX is **not** a chatbot, a dashboard, or a collection of scripts. It is an **intelligent operating system** that navigates the universe of work opportunities, orchestrates multiple AI providers, and executes complex workflows with minimal human intervention.

### The approach 📊

Every opportunity is scored against a **[zero-barrier spectrum](.ai/CURRENT_STATE.md)** (0–100): how far is it from *finding* to *getting paid*, with no interview, no portfolio gate, no unpaid trial. The engine rank-orders thousands of candidates and surfaces the ones most likely to turn into revenue **this week**.

### The human role 👤

The human sits at the **decision gate**. The system does everything before and after.

<details>
<summary><strong>🔮 The Revenue Rule</strong></summary>
<p>no feature enters the roadmap unless it increases vulnerability detection, evidence quality, acceptance probability, or system learning. No exceptions.</p>
</details>

---

## Product 🎯

> Central surfaces: Mission Control, Intelligence, Targets, Capital, MERLIN, Agents, Reports, Settings. All backed by real endpoints — nothing is a mock.

### Mission Control 🎛️

> Central operational surface for monitoring opportunities, agents and active work.

**Endpoints:** [`GET /api/mission/status`](.ai/CURRENT_STATE.md), [`GET /api/activity`](docs/diagrams/architecture.mmd), [`POST /api/hunt/start`](.ai/ROADMAP.md)

### Intelligence 🧠

> Information processing and opportunity analysis surfaces — findings, hypotheses, evidence, confidence.

### Targets 📍

> Target intelligence and opportunity prioritization — scan queues, attack surface, prioritization.

### Capital 💰

> Revenue tracking and financial intelligence dashboard — USD/hour per platform, payout timelines, ROI.

### MERLIN 🤖

> AI assistant with persistent memory, intent analysis, Office Retro personality (`calm_operator`, local-first Piper TTS, native mic).

**API:** [`POST /api/voice/assistant`](.ai/CURRENT_STATE.md), `POST /direct-work/daily-companion`

### Agents 👥

> Twelve departmental specialists — Security, Coding, QA, Debug, Documentation, Research, Product, Revenue, Automation, Infrastructure, Evolution, Orchestrator.

### Reports 📊

> Report generation, submission tracking, finder queues.

### Settings ⚙️

> System configuration, AI providers, credentials, scheduler, integrations.

### Mobile (OMEGA) 📱

> Native companion (Capacitor Android): home, agents, opportunities, MERLIN chat, notifications, watch sync.

---

## Architecture 🏗️

A **modular monolith**: one FastAPI process, EventBus-driven, single database. No microservices, no external message queue, no lock-in.

```mermaid
flowchart TB
    subgraph SURFACE["📡 Presentation"]
        MC["Mission Control - Vue 3 SPA"]
        DESK["💻 OWNEX Desktop - Tauri v2"]
        MOB["📱 Mobile Companion - Capacitor"]
        MERLIN["🤖 MERLIN - Copilot"]
    end

    subgraph CORE["🧩 Core Platform - FastAPI"]
        EB["🔌 EventBus"]
        SCH["⏰ Scheduler - 28 cron jobs"]
        UM["🧠 Unified Memory - SQLite"]
        DJ["📓 Decision Journal"]
        VAULT["🔐 Identity Vault"]
        HC["🩺 Health Center"]
    end

    subgraph CYCLES["🔄 Work Cycles"]
        SEC["🛡️ Security"]
        FORGE["🔨 Forge"]
        PULSE["📈 Pulse"]
        VAULT_C["💰 Vault"]
        ATLAS["🗺️ Atlas"]
        QA["🧪 QA Cycle"]
        DW["💼 Direct Work"]
    end

    subgraph ENGINES["⚙️ Engines"]
        DWE["Direct Work Engine"]
        REV["💵 Revenue Intelligence"]
        OPP["🔍 Opportunity Discovery"]
        VAL["✅ Validation & Evidence"]
        EVO["📈 Evolution Learning"]
        OAR["🤖 OAR AI Runtime"]
        CAR["🎓 Career Engine"]
    end

    subgraph AI["🤖 Multi-Provider AI"]
        RT["🧠 OAR Smart Router"]
        P1["🦙 Ollama (local)"]
        P2["🔗 FCC Proxy"]
        P3["🔑 OpenRouter (optional)"]
    end

    SURFACE --> CORE
    CORE --> CYCLES
    CYCLES --> ENGINES
    ENGINES --> AI
```

### Stack (real, no smoke) 🛠️

| Layer | Technology | Notes |
|---|---|---|
| **Backend** 🐍 | Python 3.11+ · FastAPI · SQLAlchemy 2.0 | 3,228+ tests, Ruff clean, mypy strict |
| **Frontend** 🌐 | Vue 3 + TypeScript · Tailwind CSS v4 · Vite | 92 routed pages, Mission Control SPA |
| **Desktop** 💻 | Tauri v2 (Rust+WebView2) + PyInstaller sidecar | Native desktop, `OWNEX Alpha` binary |
| **Mobile** 📱 | Capacitor (Android) + Expo/React Native (OMEGA) | Native mic, native voice, APK ~5 MB |
| **AI Stack** 🤖 | Free-first con fallback y modo degradado: local → free cloud → reglas | OAR runtime: routing, circuit breakers, quota tracking, observability, 13 adapters |
| **Database** 📦 | SQLite (dev/desktop) · PostgreSQL (prod) | Single DB, no external queue |
| **Security** 🔐 | Ed25519 licenses · AES-256-GCM vault · CSRF double-submit | IdentityVault, chmod 600 keys |
| **Testing** ✅ | pytest · pytest-cov · pytest-timeout | `make test`, `make test-fast` |

### 7 Work Cycles 🔄

OWNEX runs as 7 autonomous work cycles, coordinated by the scheduler:

| Cycle | Focus | Key APIs | Schedule |
|---|---|---|---|
| **🛡️ Security** | Bug bounty pipeline | [`/api/cycles/security/*`](.ai/CURRENT_STATE.md) | 30-min cron |
| **🔨 Forge** | Dev bounty opportunities | [`/api/cycles/forge/*`](.ai/ROADMAP.md) | 2-hour cron |
| **📈 Pulse** | AI work / market signals | [`/api/cycles/pulse/*`](docs/audit/INTERNAL_AUDIT.md) | 1-hour cron |
| **💰 Vault** | Wealth management | [`/api/cycles/vault/*`](.ai/CURRENT_STATE.md) | 4-hour cron |
| **🗺️ Atlas** | Intelligence | [`/api/cycles/atlas/*`](docs/audit/INTERNAL_AUDIT.md) | 4-hour cron |
| **🧪 QA Cycle** | Test execution + regression | [`/api/cycles/qa/*`](.ai/ROADMAP.md) | daily 08:30 |
| **💼 Direct Work** | Zero-barrier opportunities | [`/direct-work/*`](.ai/STRATEGIC_AUDIT.md) | daily 06:15 |

---

## How a Day Runs ⏰

| Time | Cycle | What happens | Key APIs |
|---|---|---|---|
| **06:15** | 💼 Direct Work | Work Bank: discover → filter zero-barrier → rank by EV → prepare packages | [`POST /direct-work/workbank/cycle`](.ai/CURRENT_STATE.md) |
| **06:30** | 🤖 MERLIN | `daily-companion` → consolidated briefing (system + personal + market + focus) | [`POST /direct-work/daily-companion`](.ai/CURRENT_STATE.md) |
| **07:00** | 👁️ Mission Control | Top pick of the day + skill gap + learning plan | [`GET /api/activity`](docs/diagrams/architecture.mmd) |
| **08:00** | 📈 Market | Platform report: friction tiers, retired sources, emerging categories | [`POST /api/direct-work/market-report`](.ai/ROADMAP.md) |
| **09:00** | 💰 Capital | Revenue dashboard: earned/pending/ROI per platform, projection | [`POST /direct-work/income-dashboard`](.ai/CURRENT_STATE.md) |
| **14:00** | 🛡️ Security | Findings → evidence → report → auto-submit | [`POST /api/cycles/security/run_pipe`](.ai/CURRENT_STATE.md) |
| **18:00** | 👨‍💼 Executive | "Did we make money this week?" USD/hour per platform | [`GET /api/cycles/security/dashboard`](docs/audit/GITHUB_PRESENTATION_REPORT.md) |
| **22:00** | 🛡️ Backup | Version backup + health snapshot persisted | [`/api/version-backup/*`](.ai/CURRENT_STATE.md) |

---

## FAQ ❓

<details>
<summary><strong>What is OWNEX exactly?</strong></summary>

**OWNEX** is a personal autonomous work operating system — a private platform that discovers income opportunities (bug bounty, dev bounty, AI work, freelance), analyzes them with economic scoring, prepares deliverables autonomously, and tracks results. It is **not a SaaS product**: it runs on your machine and works for you.

</details>

<details>
<summary><strong>Is OWNEX open source? Can I contribute?</strong></summary>

No — the code is **proprietary** and private. OWNEX is a personal competitive-advantage asset, not a community project. The repository is public for presentation, but the license is Proprietary and contributions are not accepted.

</details>

<details>
<summary><strong>What can it actually do today?</strong></summary>

Verified working features (not roadmap): discovery from **135 curated sources** (HackerOne, Bugcrowd, Intigriti, YesWeHack, Opire, IssueHunt, Freelancer, OpenCollective…), zero-barrier scoring, Work Bank that prepares jobs to 100% ready-to-deliver, EV ranking, Daily Brief/Companion, market evolution engine (OVOS + friction tiers), career/skill gap engine, revenue tracking + projections, security pipeline (recon → hypothesis → validation → evidence → report), scheduler with 28 cron jobs, 7 work cycles, mobile Android companion (APK), desktop (Tauri + PyInstaller), voice assistant, MERLIN chat, CSRF/rate-limit/auth security layers.

</details>

<details>
<summary><strong>Does OWNEX submit reports and work by itself?</strong></summary>

No — by design (**Human Control layer**). OWNEX prepares everything: packages, reports, submissions, and negotiation analysis. The human is the final authority for actions that send data out (submissions, deliveries, payouts). Automations run only for internal preparation, discovery and analysis.

</details>

<details>
<summary><strong>Do I need to be a bug bounty expert?</strong></summary>

No. The Direct Work Engine scores opportunities by **entry barrier** and prioritizes zero-barrier public tasks; the career engine detects skill gaps and builds a daily training plan; the guided onboarding covers the fundamentals. You can start from zero and progress by category.

</details>

<details>
<summary><strong>Does it require an internet connection or cloud services?</strong></summary>

No. Everything runs **100% local**: FastAPI backend, SQLite, local model via Ollama. Optional integrations (SMTP for email verification, platform APIs, cloud backup) are opt-in and never required. There is no telemetry, no account cloud.

</details>

<details>
<summary><strong>Which AI models does it use? Do I need API keys?</strong></summary>

No keys required to start. OWNEX prioritizes local (Ollama) and free providers (OpenCode, OmniRoute) with automatic fallback. When a provider fails or hits quotas, the circuit breaker routes to the next in the chain — and if all LLMs are unavailable, deterministic engines keep the system running in degraded mode. Paid providers exist but are disabled by default (`daily_budget = $0`).

</details>

<details>
<summary><strong>Does it really make money?</strong></summary>

The system optimizes **probability × reward × speed** and tracks real outcomes (earnings, acceptance rates, USD/hour per platform) — it never fabricates rates. Revenue figures in the UI come from actual tracked payouts. Results depend on the market and on delivery; OWNEX maximizes the odds and removes the busywork.

</details>

<details>
<summary><strong>What platforms does it integrate with?</strong></summary>

Bug bounty: HackerOne, Bugcrowd, Intigriti, YesWeHack. Dev bounty: Opire, IssueHunt, OpenCollective, Algora. Freelance: Fiverr engine (11 gigs), Freelancer. Plus 135 curated discovery sources across 36 categories. Connectors for crypto/wealth (CoinGecko, Polymarket) and data annotation categories.

</details>

<details>
<summary><strong>How do I install it?</strong></summary>

```bash
git clone https://github.com/AdriDob/OWNEX.git && cd OWNEX
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:8000 — the guided personalization wizard takes you through setup. See [Quick Start](#quick-start).

</details>

<details>
<summary><strong>What platforms does it run on?</strong></summary>

- **Desktop:** Linux, Windows, macOS (Python 3.11+; Tauri bundle + PyInstaller sidecar)
- **Mobile companion:** Android (Capacitor APK, ~5 MB, native mic/voice)
- The mobile app connects to your local backend; it does not require a cloud server.

</details>

<details>
<summary><strong>Is my data safe?</strong></summary>

Security is layered: AES-256-GCM IdentityVault (random key, `chmod 600`), Ed25519 licenses, double-submit CSRF, identity-based rate limiting, session tokens with device binding, audit log (append-only JSONL, rotated), 100% local storage. Details in [.ai/SECURITY_POLICY.md](.ai/SECURITY_POLICY.md).

</details>

<details>
<summary><strong>Is there a mobile/desktop app?</strong></summary>

Yes — an Android APK (OMEGA companion: dashboard, agents, opportunities, MERLIN chat, notifications, watch sync) and a Tauri desktop bundle (`OWNEX OMEGA`). Both are build-verified; see [Project Status](#project-status).

</details>

<details>
<summary><strong>What is the "Work Bank"?</strong></summary>

The Work Bank is an autonomous production engine: it discovers public zero-barrier jobs, filters and ranks them by EV, **prepares each one to 100% ready-to-deliver** (README, proposal, work package) and accumulates them (target: 10/day, 1000/month). You only review and deliver the best ones.

</details>

<details>
<summary><strong>How is OWNEX different from a SaaS bounty tool?</strong></summary>

SaaS tools are multi-tenant dashboards; OWNEX is a **private autonomous operator**. It doesn't just display findings — it discovers opportunities, prepares deliverables, projects income, learns from outcomes and runs a full daily cycle with zero external infrastructure. And your data never leaves your machine.

</details>

---

## Quick Start 🚀

### Multi-Platform Installation

Choose your platform:

#### 🪟 Windows 11 (with WSL) — Desktop Installer (Recommended)

**Auto-contained bundle — no Python/Node required**

1. Build or download the installer:
   - **Canonical (Tauri)**: run `.github/workflows/ownex-tauri-windows.yml` → artifact `OWNEX-Tauri-Windows` (`OWNEX Alpha_7.0.0_x64-setup.exe` / `.msi`)
   - **Legacy (PySide6 NSIS)**: dispatch `ownex-alpha-windows.yml` (manual) → artifact `OWNEX-Alpha-Windows-Installer`; last deployed build: `ownexinstalador/windows/OWNEX-Desktop-Alpha-Setup.exe`
   - GitHub Releases (when published)
2. Run the installer (accept SmartScreen warning — debug build)
3. Launch OWNEX Desktop from Start menu
4. Backend starts automatically at `http://127.0.0.1:8000`
5. Data persists in `%APPDATA%\OWNEX` (survives reinstalls)

**Detailed guide:** [README-INSTALACION.md](README-INSTALACION.md)

#### 🐧 Linux — Development Setup

```bash
# 1️⃣ Clone
git clone https://github.com/AdriDob/OWNEX.git
cd OWNEX

# 2️⃣ Virtual environment + deps
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # backend
cd frontend && npm install               # frontend

# 3️⃣ Start everything
python run.py                              # → FastAPI on http://localhost:8000
# in another terminal:
cd frontend && npm run dev                # → Mission Control on http://localhost:5173
```

#### 📱 Android — Mobile Companion

```bash
cd android
./gradlew assembleDebug                  # → android/app/build/outputs/apk/debug/app-debug.apk
# Install via ADB or transfer to device
```

**Detailed guide:** [android/BUILD_RELEASE_APK.md](android/BUILD_RELEASE_APK.md)

#### ⌚ WearOS — Smartwatch Companion

```bash
cd android
./gradlew :wear:assembleDebug           # → android/wear/build/outputs/apk/debug/wear-debug.apk
# Install via ADB to WearOS device
```

**Detailed guide:** [.ai/WEAROS_DECISION.md](.ai/WEAROS_DECISION.md)

### Guided install (Linux/Dev)

The universal installer (`install.py`) configures everything interactively:

```bash
python install.py
# → Wizard: use case → modules → experience level → platforms → integrations
# → sets up .venv, DB, credentials, desktop, notifications
```

### Next steps

| Action | Command / Route | Docs |
|---|---|---|
| Health check | `curl localhost:8000/api/health` | [.ai/CURRENT_STATE.md](.ai/CURRENT_STATE.md) |
| Add a bug bounty target | `python run.py --add-target "demo" --domain example.com` | [Agent Charter](.ai/AGENT_CHARTER.md) |
| Run the QA cycle | `POST /api/cycles/qa/run` | [.ai/ROADMAP.md](.ai/ROADMAP.md) |
| Daily briefing | `POST /direct-work/daily-companion` | [.ai/CURRENT_STATE.md](.ai/CURRENT_STATE.md) |
| Create version backup | `python scripts/version_backup.py backup` | [DECISIONS.md](.ai/DECISIONS.md) |
| Quality gate | `make check` | [.ai/TESTING_POLICY.md](.ai/TESTING_POLICY.md) |
| Fast smoke tests | `python scripts/dev test-fast` | [.ai/TESTING_POLICY.md](.ai/TESTING_POLICY.md) |
| Generate docs diagrams | `scripts/brand/regenerate.sh` | [docs/README.md](docs/README.md) |

> **Tip:** `make` is your friend. Other targets: `make test`, `make fmt`, `make backup`, `make typecheck-fast`.

### Environment variables

API keys go to `IdentityVault` (AES-256-GCM, random key, `chmod 600`) or `.env` (never committed):

```bash
# AI providers (at least one)
OLLAMA_URL=http://localhost:11434                  # local (default)
OPENROUTER_API_KEY=                                 # optional premium
FCC_PROXY_URL=http://localhost:8082                 # free Claude proxy

# Platforms (bug bounty etc.)
HACKERONE_API_KEY=
BUGCROWD_API_KEY=
SYNACK_API_KEY=

# Email verification (optional)
OWNNEX_MAIL_SMTP_HOST=                              # set to enable email verification
```

See **[.ai/SECURITY_POLICY.md](.ai/SECURITY_POLICY.md)** for the full security model.

---

## Development 🛠️

OWNEX is developed as a **single source of truth** system. Everything operational lives in [.ai/](.ai/):

```
.ai/                          ← Sistema de verdad única
├── AGENT_CHARTER.md          # 🏛️ Constitución, Agent Loop, Regla de Oro
├── PRODUCTION_RULES.md       # 📋 Reglas de producción (extend, never break)
├── CURRENT_STATE.md          # 📊 Estado verificado feature por feature
├── TASK_QUEUE.md             # 📋 Cola priorizada con criterios de cierre
├── ROADMAP.md                # 🗺️ Roadmap general
├── DECISIONS.md              # 📓 Decisiones arquitectónicas con evidencia
├── KNOWN_DEBT.md             # ⚠️ Deuda técnica conocida
├── DO_NOT_TOUCH.md           # 🚫 Componentes estables (licencia, vault, auth)
├── STRATEGIC_AUDIT.md        # 🔍 Marco de auditoría permanente
├── CODE_QUALITY.md           # 🧹 Standards de calidad
├── TESTING_POLICY.md         # ✅ Política de testing
├── SECURITY_POLICY.md        # 🔐 Principios de seguridad
├── PROJECT_CONTEXT.md        # 📐 Contexto del proyecto
├── LESSONS.md                # 📚 Lecciones aprendidas
├── MEMORY.md                 # 🧠 Unified Memory subsystem
└── OWNEX_OMEGA_ARCHITECTURE.md  # 🏢 Arquitectura OMEGA
```

**Golden rule:** when code, docs, or agent memory conflict — `.ai/` wins.

### Commands

```bash
# Testing
python scripts/dev test              # full suite (excluye test_security.py)
python scripts/dev test-fast         # smoke: scoring + scheduler + DWE
make test                            # alias

# Lint + typecheck (CI-equivalent)
make check                            # ruff + mypy scoped + fast tests
make fmt                             # write fixes

# Backend
python run.py                        # full system
python run.py --add-target <name> --domain <domain>
python run.py --backup
python scripts/version_backup.py backup --notes "pre-update"

# Frontend (from frontend/)
npm run dev                          # dev server
npm run build                        # production build
npx vite preview                     # serve dist
npx vue-tsc --noEmit                  # typecheck

# Branding pipeline
scripts/brand/regenerate.sh          # logo + banners + README badge sync
scripts/brand/regenerate.sh --shots  # + screenshots (dark + light)
```

### Stack

| Concern | Tool | Config |
|---|---|---|
| Python lint | Ruff | `pyproject.toml[tool.ruff]` |
| Python types | mypy | strict on `core/` |
| Frontend lint | Biome | `frontend/biome.json` |
| Python tests | pytest | `tests/test_*.py`, `--timeout=60` |
| Frontend build | Vite | `frontend/vite.config.ts` |

---

## Security 🔐

| Measure | Implementation | Docs |
|---|---|---|
| Local-first | 100% local by default — nothing leaves the machine | [.ai/SECURITY_POLICY.md](.ai/SECURITY_POLICY.md) |
| Credential vault | IdentityVault AES-256-GCM, random key, `chmod 600` | [core/identity_vault.py](core/identity_vault.py) |
| License validation | Ed25519 asymmetric, 25-char format | [cores/license/](cores/license/) |
| CSRF protection | Double-submit cookie on all mutantes | [api/middleware/csrf_middleware.py](api/middleware/csrf_middleware.py) |
| Rate limiting | Per-identity with IP fallback | [api/middleware/rate_limit_middleware.py](api/middleware/rate_limit_middleware.py) |
| Audit log | Append-only JSONL, 10 MB rotation | [cores/audit_log.py](cores/audit_log.py) |
| Session security | AES-256-GCM, device binding, 30-min expiry | [cores/auth/session.py](cores/auth/session.py) |

See **[.ai/SECURITY_POLICY.md](.ai/SECURITY_POLICY.md)** for the complete security model.

---

## Project Status 🩺

Honest state of the system — nothing here is a mock:

| Layer | State | EVIDENCE |
|---|---|---|
| 🛡️ Security pipeline (7 stages, auto-submit) | ✅ production-hardened | `tests/test_e2e_security_pipeline.py` — 8 passed |
| 💼 Direct Work Engine + Work Bank + Daily Companion + Evolution | ✅ production | `cores/direct_work_engine/` (engine + filters + feedback) |
| 🔄 7 Work Cycles · 28 scheduled jobs · Mission Control · Executive Dashboard | ✅ production | `tests/test_scheduler_jobs.py` — 40 passed |
| 🤖 OAR AI Runtime (routing + resilience + observability) + Career Engine | ✅ production | `tests/test_oar.py` · `test_ai_resilience.py` 46 ✓ · [AI Runtime →](docs/AI_RUNTIME.md) |
| 💰 Income Target Engine + Economic Engine + Payment Pipeline canónico | ✅ production | `tests/test_income_target.py` · `test_payment_pipeline.py` · `test_economics_ssot.py` |
| 💻 Desktop (Tauri v2) · Mobile (Capacitor) · MERLIN | ✅ build-verified | APKs 5.1 MB · Tauri cargo check OK |
| 📱 OMEGA mobile (Expo/React Native) | 🟡 experimental skeleton | functional shell |
| ⌚ Wear OS native | ✅ COMPLETED | [.ai/WEAROS_DECISION.md](.ai/WEAROS_DECISION.md) — fully implemented |
| ⚙️ core/ → cores/ migration | ✅ completed | 7 files migrated from empty `core/` in GitHub to `cores/` with 278 real modules |

Single-user, local-first. New surfaces ship as **experimental** until they pass the end-to-end gate (persistence, restart survival, real output — no mocks).

<details>
<summary><sub>🐝 Bee Monitor active: every <code>/api/health</code>, <code>/api/system/health</code> and <code>/api/system/status</code> is live. Check <code>.ai/CURRENT_STATE.md</code> for the latest honey — findings, reports, payouts.</sub></summary>
</details>

---

## Roadmap 🗺️

See [`.ai/ROADMAP.md`](.ai/ROADMAP.md) for the full roadmap.

| Status | Item | Docs |
|---|---|---|
| ✅ **DONE** | Security pipeline (7 stages) — auto-submit to finder queues | [Security Cycle](.ai/CURRENT_STATE.md) |
| ✅ **DONE** | Direct Work Engine + Work Bank + Daily Companion + Evolution | [DWE](.ai/CURRENT_STATE.md) |
| ✅ **DONE** | 7 Work Cycles, 28 scheduled jobs, Mission Control, Executive Dashboard | [Auditoría](docs/audit/INTERNAL_AUDIT.md) |
| ✅ **DONE** | Desktop (Tauri v2 + PyInstaller sidecar), mobile companion, MERLIN | [PRESENTATION](docs/audit/GITHUB_PRESENTATION_REPORT.md) |
| ✅ **DONE** | OAR AI Runtime — engine + tests + API mounted (`/oar/*`, `/career/*`) | [DECISIONS](.ai/DECISIONS.md) |
| 🟡 **IN PROGRESS** | OMEGA mobile (Expo/React Native) — functional skeleton | [.ai/ROADMAP.md](.ai/ROADMAP.md) |
| 🔲 **PLANNED** | OAR smart-routing wired into API decisions · more discovery adapters (Algora, OpenCollective, Superteam) | [.ai/TASK_QUEUE.md](.ai/TASK_QUEUE.md) |
| ✅ **INCLUDED** | Wear OS native — fully implemented with API integration and themes | [.ai/WEAROS_DECISION.md](.ai/WEAROS_DECISION.md) |

---

## Branding 🎨

OWNEX mark — **The Aperture Nexus**: octagonal ring + X of rays + central node that breaks the ring. Generated by a **deterministic, GPU-free pipeline** (`scripts/brand/`), zero generative AI, 100% reproducible.

```bash
scripts/brand/regenerate.sh          # logo system + banners + PNG renders + README badge sync
scripts/brand/regenerate.sh --shots  # + real product screenshots (dark + light, Playwright)
```

Design language: **Tesla dark** — pure black surfaces, white primary accent, deep blue `#1E40FF` as the only saturated accent, no noise, no glow.

> 📦 **Assets live at:** [`docs/assets/branding/`](docs/assets/branding/) and [`docs/assets/screenshots/`](docs/assets/screenshots/). See the [Asset Registry](docs/design/ASSET_REGISTRY.md).

### Branded deliverables 🖼️

<p align="center">
  [LOGO_OSCURO]  —  [LOGO_CLARO]
</p>

<p align="center">
  [MARCA_ALFA]  —  [MARCA_OMEGA]
</p>

### Capturas de Escritorio — Modo Oscuro 💻

<p align="center">
  [CAPTURA_MISSION_CONTROL_DARK]  —  [CAPTURA_MISSION_CONTROL_DARK_REF]
</p>

*pantalla principal de Mission Control con visión general de oportunidades activas, filtros y estadísticas en tiempo real*

<p align="center">
  [CAPTURA_INTELLIGENCE_DARK]  —  [CAPTURA_INTELLIGENCE_DARK_REF]
</p>

*vista de análisis de inteligencia con hallazgos, hipótesis y puntuación EV*

<p align="center">
  [CAPTURA_MERLIN_DARK]  —  [CAPTURA_MERLIN_DARK_REF]
</p>

*interfaz del asistente MERLIN con chat activo y memoria persistente*

<p align="center">
  [CAPTURA_CAPITAL_DARK]  —  [CAPTURA_CAPITAL_DARK_REF]
</p>

*panel de control financiero con seguimiento de ingresos, proyecciones ROI y estado de pagos*

<p align="center">
  [CAPTURA_REPORTS_DARK]  —  [CAPTURA_REPORTS_DARK_REF]
</p>

*gestión de reports y finder queues con seguimiento de estados SUBMITTED→PENDING→PAID*

<p align="center">
  [CAPTURA_SETTINGS_DARK]  —  [CAPTURA_SETTINGS_DARK_REF]
</p>

*configuración del sistema: AI providers, credentials, scheduler, integraciones*

<p align="center">
  [CAPTURA_TARGETS_DARK]  —  [CAPTURA_TARGETS_DARK_REF]
</p>

*Target intelligence y attack surface prioritization*

<p align="center">
  [CAPTURA_OPERATIONS_DARK]  —  [CAPTURA_OPERATIONS_DARK_REF]
</p>

*vista de operaciones activas y flujo de trabajo del día*

### Capturas de Escritorio — Modo Claro 💻

<p align="center">
  [CAPTURA_MISSION_CONTROL_LIGHT]  —  [CAPTURA_MISSION_CONTROL_LIGHT_REF]
</p>

*pantalla principal de Mission Control en modo claro*

<p align="center">
  [CAPTURA_INTELLIGENCE_LIGHT]  —  [CAPTURA_INTELLIGENCE_LIGHT_REF]
</p>

*vista de inteligencia modo claro*

<p align="center">
  [CAPTURA_MERLIN_LIGHT]  —  [CAPTURA_MERLIN_LIGHT_REF]
</p>

*asistente MERLIN modo claro*

<p align="center">
  [CAPTURA_CAPITAL_LIGHT]  —  [CAPTURA_CAPITAL_LIGHT_REF]
</p>

*panel financiero modo claro*

<p align="center">
  [CAPTURA_REPORTS_LIGHT]  —  [CAPTURA_REPORTS_LIGHT_REF]
</p>

*gestión de reports modo claro*

<p align="center">
  [CAPTURA_SETTINGS_LIGHT]  —  [CAPTURA_SETTINGS_LIGHT_REF]
</p>

*configuración modo claro*

<p align="center">
  [CAPTURA_TARGETS_LIGHT]  —  [CAPTURA_TARGETS_LIGHT_REF]
</p>

*Target intelligence modo claro*

<p align="center">
  [CAPTURA_OPERATIONS_LIGHT]  —  [CAPTURA_OPERATIONS_LIGHT_REF]
</p>

*Operaciones modo claro*

### Capturas Mobile — Modo Oscuro 📱

<p align="center">
  [CAPTURA_HOME_DARK]  —  [CAPTURA_HOME_DARK_REF]
</p>

*pantalla principal OMEGA companion — dashboard de oportunidades*

<p align="center">
  [CAPTURA_AGENTS_DARK]  —  [CAPTURA_AGENTS_DARK_REF]
</p>

*vista de agentes asignados y especialistas*

<p align="center">
  [CAPTURA_OPPORTUNITIES_DARK]  —  [CAPTURA_OPPORTUNITIES_DARK_REF]
</p>

*lista de oportunidades descubiertas y clasificadas*

<p align="center">
  [CAPTURA_MERLIN_CHAT_DARK]  —  [CAPTURA_MERLIN_CHAT_DARK_REF]
</p>

*chat con MERLIN dentro de la app móvil*

<p align="center">
  [CAPTURA_NOTIFICATIONS_DARK]  —  [CAPTURA_NOTIFICATIONS_DARK_REF]
</p>

*panel de notificaciones y alertas del sistema*

<p align="center">
  [CAPTURA_WATCH_SYNC_DARK]  —  [CAPTURA_WATCH_SYNC_DARK_REF]
</p>

*sincronización con Wear OS / smartwatch*

### Capturas Mobile — Modo Claro 📱

<p align="center">
  [CAPTURA_HOME_LIGHT]  —  [CAPTURA_HOME_LIGHT_REF]
</p>

*dashboard oscuro-claro toggle*

<p align="center">
  [CAPTURA_AGENTS_LIGHT]  —  [CAPTURA_AGENTS_LIGHT_REF]
</p>

*Agents list modo claro*

<p align="center">
  [CAPTURA_OPPORTUNITIES_LIGHT]  —  [CAPTURA_OPPORTUNITIES_LIGHT_REF]
</p>

*Oportunidades modo claro*

<p align="center">
  [CAPTURA_MERLIN_CHAT_LIGHT]  —  [CAPTURA_MERLIN_CHAT_LIGHT_REF]
</p>

*Chat MERLIN modo claro*

<p align="center">
  [CAPTURA_NOTIFICATIONS_LIGHT]  —  [CAPTURA_NOTIFICATIONS_LIGHT_REF]
</p>

*Notificaciones modo claro*

<p align="center">
  [CAPTURA_WATCH_SYNC_LIGHT]  —  [CAPTURA_WATCH_SYNC_LIGHT_REF]
</p>

*Sincronización Wear OS modo claro*

### Capturas Wear OS ⌚

<p align="center">
  [CAPTURA_WEAROS_DARK]  —  [CAPTURA_WEAROS_DARK_REF]
</p>

*interfaz nativa Wear OS — modo oscuro. Estado: ✅ COMPLETADO (.ai/WEAROS_DECISION.md)*

<p align="center">
  [CAPTURA_WEAROS_LIGHT]  —  [CAPTURA_WEAROS_LIGHT_REF]
</p>

*interfaz nativa Wear OS — modo claro*

### Logotipos y Elementos de Marca

<p align="center">
  [MARCA_ALFA]  —  Marca OWNEX ALPHA (blanca/sobre fondo oscuro)
</p>

<p align="center">
  [MARCA_OMEGA]  —  Marca OWNEX OMEGA (blanca/sobre fondo oscuro)
</p>

<p align="center">
  [LOGO_OSCURO]  —  Logo oscuro principal (PNG transparente, versión completa)
</p>

<p align="center">
  [LOGO_CLARO]  —  Logo claro principal (PNG transparente, versión completa)
</p>

<p align="center">
  [ICONO_FAVICON]  —  Favicon SVG/PNG (16x16, 32x32)
</p>

<p align="center">
  [MARCA_SOLO]  —  Marca/símbolo aislado (para favicons y pequeños renders)
</p>

### Banners y Activos de Presentación

<p align="center">
  [BANNER_HERO_OSCURO]  —  [BANNER_HERO_OSCURO_REF]
</p>

*hero-banner 2400×900 — dark mode. Usado en GitHub README principal*

<p align="center">
  [BANNER_HERO_CLARO]  —  [BANNER_HERO_CLARO_REF]
</p>

*hero-banner 2400×900 — light mode*

<p align="center">
  [BANNER_FOOTER_OSCURO]  —  [BANNER_FOOTER_OSCURO_REF]
</p>

*footer-banner para presentaciones y docs*

<p align="center">
  [BANNER_FOOTER_CLARO]  —  [BANNER_FOOTER_CLARO_REF]
</p>

*footer-banner modo claro*

### Redes Sociales y Previsualización

<p align="center">
  [SOCIAL_PREVIEW_OSCURO]  —  [SOCIAL_PREVIEW_OSCURO_REF]
</p>

*open-graph preview 1200×630 — dark mode para compartir en redes*

<p align="center">
  [SOCIAL_PREVIEW_CLARO]  —  [SOCIAL_PREVIEW_CLARO_REF]
</p>

*open-graph preview 1200×630 — light mode*

<p align="center">
  [LOGO_HORIZONTAL_ALFA]  —  [LOGO_HORIZONTAL_ALFA_REF]
</p>

*logotype horizontal ALPHA — versión para redes y escritorio*

<p align="center">
  [LOGO_HORIZONTAL_OMEGA]  —  [LOGO_HORIZONTAL_OMEGA_REF]
</p>

*logotype horizontal OMEGA — versión para redes y escritorio*

<p align="center">
  [LOGO_MONOCROMO]  —  [LOGO_MONOCROMO_REF]
</p>

*marca monocromática — solo el símbolo O+X, para favicons y favicons pequeños*

| Role | Color | Usage |
|---|---|---|
| `--ownex-bg` | `#05060A` | Page/surface backgrounds |
| `--ownex-blue` | `#1E40FF` | Primary action, links |
| `--ownex-accent` | `#e82127` | Tesla red — the only saturated accent |
| `--ownex-white` | `#F6F8FB` | Text and icons |

---

## Documentation 📚

> The project runs on a **single source of truth**: everything operational lives in [.ai/](.ai/).

### Core (.ai/)

| Document | Purpose |
|---|---|
| [AGENT_CHARTER.md](.ai/AGENT_CHARTER.md) | 🏛️ Constitution, Agent Loop, Golden Rule |
| [PRODUCTION_RULES.md](.ai/PRODUCTION_RULES.md) | 📋 Reglas de producción (never break stable) |
| [CURRENT_STATE.md](.ai/CURRENT_STATE.md) | 📊 Estado verificado feature por feature |
| [TASK_QUEUE.md](.ai/TASK_QUEUE.md) | 📋 Cola de tareas priorizada |
| [ROADMAP.md](.ai/ROADMAP.md) | 🗺️ Roadmap general |
| [DECISIONS.md](.ai/DECISIONS.md) | 📓 Decisiones arquitectónicas con evidencia |
| [KNOWN_DEBT.md](.ai/KNOWN_DEBT.md) | ⚠️ Deuda técnica conocida |
| [DO_NOT_TOUCH.md](.ai/DO_NOT_TOUCH.md) | 🚫 Componentes estables |
| [STRATEGIC_AUDIT.md](.ai/STRATEGIC_AUDIT.md) | 🔍 Marco de auditoría permanente (10 questions, 18 dimensions) |
| [SECURITY_POLICY.md](.ai/SECURITY_POLICY.md) | 🔐 Principios de seguridad |
| [TESTING_POLICY.md](.ai/TESTING_POLICY.md) | ✅ Política de testing |
| [CODE_QUALITY.md](.ai/CODE_QUALITY.md) | 🧹 Standards de calidad |
| [PROJECT_CONTEXT.md](.ai/PROJECT_CONTEXT.md) | 📐 Contexto completo del proyecto |
| [LESSONS.md](.ai/LESSONS.md) | 📚 Lecciones aprendidas |
| [MEMORY.md](.ai/MEMORY.md) | 🧠 Unified Memory subsystem |

### Design & Audit (/docs)

| Document | Purpose |
|---|---|
| [docs/README.md](docs/README.md) | 📚 Documentation hub |
| [docs/audit/INTERNAL_AUDIT.md](docs/audit/INTERNAL_AUDIT.md) | 🔍 Auditoría completa del sistema |
| [docs/audit/GITHUB_PRESENTATION_REPORT.md](docs/audit/GITHUB_PRESENTATION_REPORT.md) | 🐝 Branding + presentation report |
| [docs/design/ASSET_REGISTRY.md](docs/design/ASSET_REGISTRY.md) | 🎨 Asset registry |
| [docs/diagrams/architecture.mmd](docs/diagrams/architecture.mmd) | 🏗️ Architecture diagram (Mermaid) |

### Quick references

- **API:** `curl http://localhost:8000/docs` → FastAPI interactive docs (Swagger + ReDoc)
- **CLI:** `python run.py --help` → all commands (backup, add-target, dev tools)
- **Makefile:** `make help` → all targets

---

## License 📄

**Proprietary.** All rights reserved.

OWNEX is a private competitive-advantage asset. It does **not** sell a service to a customer. **OWNEX works for me.**

### Estado de Validación (FASE G)

```text
Build: ✅ 11.2s | Tests: ✅ 119 passing | Version: ✅ 9.0.0 (sincronizada)
Negocios: ✅ 3 integrados en ExtraWork | IA: ✅ AUTO_BEST_FREE activado
Monitor: ✅ 3 paneles de salud | Temas: ✅ dark/light configurables
Open Source: ✅ 100% free, sin herramientas de pago
```

### Funcionalidades Completadas (FASE A-F)

| Área | Logrado |
|------|---------|
| **3 Negocios Extra Work** | ✅ DroppingLabel (ML sin stock), YTS Auto Free, Adriel Webs |
| **Investment/Capital** | ✅ InvestmentHub con RevenueLedger integrado |
| **Monitorización** | ✅ HealthCenter, OperationsDashboard, Capital panel |
| **4 Secciones principales** | ✅ TRABAJANDO, DINERO, INTELIGENCIA, AUTÓNOMO |
| **Temas y personalización** | ✅ Settings.vue con themeEngine dark/light |
| **Panel comandos IA/voz** | ✅ VoiceCommandPanel con AUTO_BEST_FREE |
| **Investigación +100 fuentes** | ✅ Discovery, OpportunityPlanner, OpportunityRadar |
| **Múltiples funcionalidades** | ✅ 86 páginas + 37 componentes + 3 libs compartidas |
| **Open source / free** | ✅ 0 herramientas de pago, modelos Ollama locales |

### Arquitectura Compartida (clave del éxito)

- **RevenueLedger** — Finanzas compartidas por todos los negocios
- **TaskOrchestration** — Cola priorizada y ejecución de tareas
- **AIModelService** — Política AUTO_BEST_FREE, mejores modelos gratuitos

### Siguiente Paso: FASE G+ — Validación Windows

- Build y tests verificados exitosamente en Linux/WSL
- Instalación nativa Windows: **pendiente** (requiere entorno Windows real para validación)
- Health: YELLOW 9/10 (scheduler sin arrancar = falla visible y controlable, no oculto)

<p align="center">
  <sub>🐝 Bee Monitor: <code>curl localhost:8000/api/health</code> · built with <code>make check</code></sub>
</p>

---