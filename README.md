<p align="center">
  <img src="assets/banners/hero-banner.png" alt="OWNEX — The Personalized Autonomous Operating System" width="100%"/>
</p>

<p align="center">
  <a href="https://github.com/AdriDob/rastrohunteralpha/releases"><img src="https://img.shields.io/badge/version-7.0.0-00D5FF?style=flat-square" alt="Version"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square" alt="Python"/></a>
  <a href="https://vuejs.org/"><img src="https://img.shields.io/badge/vue-3-42B883?style=flat-square" alt="Vue"/></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/typescript-5-3178C6?style=flat-square" alt="TypeScript"/></a>
  <a href="https://www.kotlinlang.org/"><img src="https://img.shields.io/badge/kotlin-android-7F52FF?style=flat-square" alt="Kotlin"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-F6F8FB?style=flat-square" alt="License"/></a>
</p>

---

# OWNEX

## The Personalized Autonomous Operating System

An intelligent system that learns your goals, adapts to your workflow and helps you build, automate and evolve.

---

## What is OWNEX?

OWNEX is a personalized autonomous operating system designed to help individuals learn, create, automate and execute tasks with intelligent AI agents.

It is not a collection of tools. It is a system that observes how you work, understands your objectives, and evolves alongside you — from a desktop command center to your phone and wrist.

OWNEX runs a continuous **Evolution Loop**:

```
Observe → Understand → Recommend → Improve → Learn
```

Every interaction teaches the system. Every decision refines its model of you. The result: a personal operating environment that becomes more valuable the longer you use it.

---

## Brand Architecture

OWNEX is organized into four interconnected layers:

| Layer | Identity | Role |
|-------|----------|------|
| **OWNEX ALPHA** | Desktop Core | Mission Control, development environment, agent orchestration, automation, engineering |
| **OWNEX OMEGA** | Mobile Companion | Personal connection, notifications, approvals, daily intelligence, anywhere access |
| **MERLIN** | Personal AI Agent | Teacher, assistant, guide, explanation layer, memory |
| **ORION** | System Intelligence Layer | Health monitoring, evolution, optimization, self-improvement |

```
OWNEX ALPHA
    ↓
MERLIN
    ↓
Agent Departments
    ↓
Execution Layer
    ↓
Memory
    ↓
Evolution Engine (ORION)
    ↓
OWNEX OMEGA
```

---

## One System, Two Editions

OWNEX ships as two connected identities sharing a single core.

| ALPHA — Desktop Operating System | OMEGA — Android & Wear OS Companion |
|---|---|
| <img src="assets/logos/ownex-alpha.png" alt="ALPHA" width="280"/> | <img src="assets/logos/ownex-omega.png" alt="OMEGA" width="280"/> |
| Command center: agents, workflows, terminal, memory, evolution engine, mission-control dashboard. | Permanent connection: approvals, notifications, MERLIN chat, system health — on your phone and wrist. |

---

## Core Capabilities

| Capability | Status |
|---|---|
| Bug bounty pipeline (discover → recon → hypothesis → validate → report) | Production |
| Opportunity engine with EV scoring and platform executors | Production |
| Autonomous workflows and agent fleet | Production |
| MERLIN assistant with unified memory | Production |
| Security cycle with 7 stage executors | Production |
| Executive dashboard (revenue verdict, USD/hour, platform speed) | Production |
| Self-update, version backup, recovery engine | Production |
| 6-language interface (EN, ES, FR, DE, JA, ZH) | Production |

---

## Architecture

Control plane, departments, agents, execution, learning, feedback — designed for autonomy, with the human at every decision gate.

<p align="center">
  <img src="assets/concepts/architecture.png" alt="Architecture" width="80%"/>
</p>

| Layer | Responsibility |
|---|---|
| **OWNEX Core** | Event bus, scheduler, unified memory, security layer |
| **Departments** | Orchestrator · Engineering · Quality · Security · Revenue |
| **Agents** | Autonomous specialists coordinated per department |
| **Execution** | Workflows, executors, platform connectors |
| **Learning** | Feedback loops, knowledge capture, reward models |
| **Evolution (ORION)** | Self-improvement, version rollback, recovery |

---

## Quick Start

```bash
git clone https://github.com/AdriDob/rastrohunteralpha.git
cd rastrohunteralpha

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your platform credentials

python api/main.py            # backend → http://127.0.0.1:8000

cd frontend && npm install
npm run dev                   # frontend → http://localhost:5173
```

```bash
curl http://127.0.0.1:8000/api/health   # system health
python run.py --backup                   # snapshot before changes
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 · FastAPI · SQLAlchemy · Pydantic |
| Data | SQLite (dev) · PostgreSQL (prod) · Unified Memory (SQLite) |
| Frontend | Vue 3 · TypeScript · Tailwind v4 · Vite · ShadCN Vue |
| Mobile | Kotlin · Jetpack Compose · Wear OS 3+ |
| AI | Local models (Ollama) · OpenRouter · free providers · MERLIN |
| Automation | Scheduler (cron-aware) · EventBus · AgentBus · RecoveryEngine |
| Quality | pytest (1,400+ tests) · Ruff · mypy · Biome · Vitest |

---

## Documentation

- [Documentation Index](DOCUMENTATION_INDEX.md) — Complete documentation index
- [Troubleshooting Guide](TROUBLESHOOTING.md) — Common issues and solutions
- [API Reference](API_REFERENCE.md) — Complete API documentation
- [Brand Usage Guide](BRAND_USAGE_GUIDE.md) — Brand asset usage guidelines
- [Screenshot Guide](SCREENSHOT_GUIDE.md) — Screenshot standards and process
- [Brand Identity](assets/branding/OWNEX_BRAND_IDENTITY.md) — Complete brand identity
- [Design Tokens](assets/branding/design-tokens.json) — Machine-readable brand tokens
- [Trailer Storyboard](assets/video/trailer-storyboard.md) — 90s product trailer structure
- [Agent Charter](.ai/AGENT_CHARTER.md) — Constitution and operating rules
- [Architecture](.ai/ARCHITECTURE_FINAL.md) — Full architectural decisions

---

## Philosophy

**Consolidation over expansion.** OWNEX does not grow by adding modules; it grows by closing loops. Every component must produce observable results, survive restarts, and connect to at least one real consumer. If it cannot be verified, it does not exist.

**The system adapts to the person, not the person to the software.**

---

## License

MIT — see [LICENSE](LICENSE). Brand fonts: SIL OFL 1.1 (Google Fonts).

---

<p align="center">
  <img src="assets/logos/ownex-mark.png" alt="OWNEX" width="140"/>
</p>

<p align="center"><sub>OWNEX — The Personalized Autonomous Operating System · ALPHA + OMEGA</sub></p>