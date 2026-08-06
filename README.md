<p align="center">
  <img src="https://raw.githubusercontent.com/AdriDob/rastrohunteralpha/main/assets/logos/ownex-logo.svg" alt="OWNEX" width="140"/>
</p>

<h1 align="center">OWNEX</h1>

<p align="center">
  <strong>Personalized Autonomous Operating System</strong>
</p>

<p align="center">
  Autonomous Intelligence for Technical Work
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-7.0.0-e82127?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIj48cGF0aCBkPSJNMTIgMmw1IDUgNyA3LTcgNy01IDUtNS01TDQgMTQgOSA5eiIvPjwvc3ZnPg=="/>
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/vue-3.5-4FC08D?style=flat-square&logo=vue.js&logoColor=white"/>
  <img src="https://img.shields.io/badge/fastapi-0.104+-009688?style=flat-square&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/tests-1400+-00C853?style=flat-square"/>
</p>

---

<p align="center">
  <img src="https://raw.githubusercontent.com/AdriDob/rastrohunteralpha/main/docs/screenshots/01_mission-control.svg" alt="OWNEX Mission Control" width="900"/>
</p>

---

## Mission

OWNEX transforms technical workflows through autonomous operation, persistent memory, and continuous self-improvement. It is a **Personalized Autonomous Operating System** that discovers opportunities, executes technical work, learns from outcomes, and evolves its own operation — from a desktop command center to your phone and wrist.

The human stays at the decision gate. The system handles the rest.

## Why OWNEX

Technical professionals face a fragmented landscape: disconnected automation tools, lost knowledge between sessions, manual security research, and no persistent learning from past operations.

OWNEX solves this through a **closed-loop architecture**:

<p align="center">
  <strong>OBSERVE → DECIDE → EXECUTE → LEARN → EVOLVE</strong>
</p>

Every operation feeds back into the system. Every outcome improves future performance.

## Core Philosophy

| Principle | Meaning |
|-----------|---------|
| **Freedom First** | Technology serves the user, not the other way around |
| **Zero Barrier Entry** | Demonstrable capability over bureaucracy |
| **Maximum Value Generation** | Results, not activity metrics |
| **Intelligence Before Action** | Understand → Analyze → Evaluate → Propose → Execute → Learn |
| **Continuous Evolution** | Complexity only when it increases freedom, value, or capacity |
| **Human Control** | The user is always the final authority |

---

## What It Does

### Autonomous Pipeline

A 7-stage bug bounty pipeline that runs every 30 minutes:

<p align="center">
  <img src="https://raw.githubusercontent.com/AdriDob/rastrohunteralpha/main/docs/screenshots/02_pipeline.svg" alt="Pipeline" width="900"/>
</p>

| Stage | Function |
|-------|----------|
| **1. Recon** | Subdomain enumeration, target discovery |
| **2. Attack Surface** | Endpoint discovery and cataloging |
| **3. Hypothesis** | Vulnerability prediction via pattern recognition |
| **4. Validation** | Proof-of-concept verification |
| **5. Evidence** | Screenshots, HTTP replay, auto-captured |
| **6. Report** | Auto-generated markdown with full reproduction steps |
| **7. Submit** | Auto-submission to HackerOne, Bugcrowd, Intigriti |

Only elite findings (score > 85) pass the quality gate to auto-submit.

### Intelligence & Memory

<p align="center">
  <img src="https://raw.githubusercontent.com/AdriDob/rastrohunteralpha/main/docs/screenshots/03_intelligence.svg" alt="Intelligence" width="900"/>
</p>

- **UnifiedMemoryStore** — Persistent memory that survives restarts
- **KnowledgeCapture** — Patterns recognized across operations
- **DecisionJournal** — Every system decision logged with reasoning
- **AdaptiveSuccessRate** — Acceptance rate learning per platform

### Financial Intelligence

<p align="center">
  <img src="https://raw.githubusercontent.com/AdriDob/rastrohunteralpha/main/docs/screenshots/05_financial.svg" alt="Financial Intelligence" width="900"/>
</p>

**Progressive Scaling** — A 4-phase revenue system:

| Phase | Focus | Target |
|-------|-------|--------|
| **0** | Survival (data annotation, quick gigs) | Immediate cash flow |
| **1** | Bug bounty (HackerOne, Bugcrowd, Intigriti) | $500+/month |
| **2** | Multi-platform (freelance, dev bounties, auto-apply) | $2k+/month |
| **3** | Investment + scale (crypto, smart allocation) | $10k+/month |

**Risk Guardian** — Max drawdown protection (15% warning, 25% critical). Kelly criterion position sizing. Auto-rebalance on correlation spikes.

**Smart Allocator** — Auto-assigns payouts to highest-yield strategy based on real performance data.

### Work Cycles

<p align="center">
  <img src="https://raw.githubusercontent.com/AdriDob/rastrohunteralpha/main/docs/screenshots/06_work-cycles.svg" alt="Work Cycles" width="900"/>
</p>

Six autonomous work cycles, each a complete workflow:

- **SECURITY** — Bug bounty to auto-submit
- **FORGE** — Dev bounties to PR to merge
- **PULSE** — AI work and data tasks
- **WEALTH** — Investment management
- **ATLAS** — System monitoring and self-healing
- **DIRECT WORK** — Freelance platform integration

A 26-job scheduler orchestrates all cycles with self-healing capabilities.

---

## Architecture

<p align="center">
  <img src="https://raw.githubusercontent.com/AdriDob/rastrohunteralpha/main/docs/screenshots/04_desktop-arch.svg" alt="Architecture" width="900"/>
</p>

### Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy |
| **Frontend** | Vue 3 + TypeScript, Tailwind CSS v4, Vite |
| **Desktop** | Tauri v2 (Rust shell + WebView2) |
| **Mobile** | Capacitor v6 (Android) |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **AI** | Multi-provider router (Ollama → FCC Proxy → OpenRouter → OpenAI) |
| **Build** | PyInstaller (Python), Cargo (Rust), npm (Frontend) |

### Repository Structure

```
OWNEX/
├── api/                    # FastAPI REST + WebSocket endpoints
│   └── routers/            # 15+ API modules
├── core/                   # Shared platform services
│   ├── scheduler/          # 26-job async scheduler
│   ├── events/             # EventBus for inter-module comms
│   ├── investment/         # Trading adapters (9 platforms)
│   └── ai_worker/          # Autonomous AI agent system
├── cores/                  # Intelligence & automation modules
│   ├── financial_intelligence/  # Progressive scaling, risk, allocation
│   ├── auto_submit/        # Auto-submission pipeline
│   ├── evidence/           # Evidence capture & composition
│   ├── opportunity/        # Opportunity engine
│   └── merlin/             # AI personality & reasoning
├── frontend/               # Vue 3 + TypeScript web UI
│   └── src/
│       ├── pages/          # 60+ views
│       └── components/     # 80+ components
├── android/                # Capacitor Android app
├── docs/                   # Comprehensive documentation
└── .ai/                    # Strategic planning & decisions
```

---

## Desktop Command Center

<p align="center">
  <img src="https://raw.githubusercontent.com/AdriDob/rastrohunteralpha/main/docs/screenshots/07_mobile-companion.svg" alt="Mobile Companion" width="900"/>
</p>

OWNEX Desktop is a **Tauri v2** application that bundles the Python backend with a native Rust shell and the full Vue 3 frontend:

- Frameless window with Mica/Acrylic effects
- System tray integration
- WebSocket real-time updates
- Single binary distribution (~120MB)
- Security: CSP, IPC allowlist, token auth, no node integration

---

## Mobile Companion

ORION Companion brings OWNEX to Android:

- Same codebase as desktop (Capacitor wrapper)
- Real-time WebSocket sync
- Push notifications for approvals and critical findings
- One-tap approve/skip for auto-submissions
- Biometric authentication
- Revenue tracking and agent fleet status

---

## Getting Started

### Quick Start

```bash
# Clone the repository
git clone https://github.com/AdriDob/rastrohunteralpha.git
cd rastrohunteralpha

# Setup Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the autonomous system
python run.py
```

### Frontend Development

```bash
cd frontend
npm install
npm run run
```

### Key Commands

```bash
# Health check
python run.py --health

# Add target for research
python run.py --add-target "example.com" --domain "example.com"

# Run tests
make test

# Quality checks (lint + typecheck + fast tests)
make check

# Backup system state
python run.py --backup
```

---

## Testing & Quality

| Metric | Value |
|--------|-------|
| **Tests** | 1,400+ (pytest + Vitest) |
| **Python Linting** | Ruff |
| **Frontend Linting** | Biome |
| **Type Checking** | Mypy (strict mode) |
| **Test Coverage** | All modules |

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture/) | System design and ADRs |
| [API Reference](docs/API_REFERENCE.md) | REST API documentation |
| [Development Guide](docs/development/) | Setup, workflow, deployment |
| [Operations](docs/operations/) | Running and monitoring |
| [Security Model](docs/SECURITY_MODEL.md) | Security architecture |
| [Changelog](CHANGELOG.md) | Release history |

---

## Status

OWNEX v7.0.0 is in **active development**. Core systems are operational:

- [x] Autonomous pipeline (7 stages)
- [x] Progressive scaling (4 phases)
- [x] Risk guardian + smart allocator
- [x] 6 work cycles
- [x] Desktop command center (Tauri)
- [x] Mobile companion (Android)
- [x] AI Worker foundation
- [x] Alert system + notifications
- [x] Infinite sources + auto-apply
- [ ] Tauri production build
- ] Android crash fix
- [ ] Real trading integration (dry-run mode active)

---

## License

Proprietary. All rights reserved.

---

<p align="center">
  <strong>Built for autonomous technical work.</strong>
</p>

<p align="center">
  <sub>OWNEX is a private competitive advantage asset. It does not sell services. It works for its operator.</sub>
</p>
