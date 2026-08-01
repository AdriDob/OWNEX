<p align="center">
  <img src="assets/banners/hero-banner-unified.png" alt="OWNEX" width="100%"/>
</p>

<p align="center">
  <a href="https://github.com/AdriDob/rastrohunteralpha/releases"><img src="https://img.shields.io/badge/version-7.0.0-5E6AD2?style=flat-square" alt="Version"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square" alt="Python"/></a>
  <a href="https://vuejs.org/"><img src="https://img.shields.io/badge/vue-3-42B883?style=flat-square" alt="Vue"/></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/typescript-5-3178C6?style=flat-square" alt="TypeScript"/></a>
  <a href="https://www.kotlinlang.org/"><img src="https://img.shields.io/badge/kotlin-android-7F52FF?style=flat-square" alt="Kotlin"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-08090A?style=flat-square" alt="License"/></a>
</p>

---

## OWNEX

**The Personalized Autonomous Operating System**

OWNEX is an autonomous personal operating system: a single platform that discovers opportunities, executes technical work, learns from outcomes, and evolves its own operation — from a desktop command center to your phone and wrist.

It is built around a closed loop: **observe → decide → execute → learn → evolve**. The human stays at the decision gate; the system handles the rest.

---

## Two Editions

OWNEX ships as two connected identities sharing a single core.

<table>
  <tr>
    <td width="50%" align="center">
      <img src="assets/logos/ownex-alpha.png" alt="OWNEX ALPHA" width="320"/>
      <br/><br/>
      <b>ALPHA — Desktop Operating System</b>
      <br/>
      The command center: agents, workflows, terminal, memory,
      evolution engine, and the full mission-control dashboard.
    </td>
    <td width="50%" align="center">
      <img src="assets/logos/ownex-omega.png" alt="OWNEX OMEGA" width="320"/>
      <br/><br/>
      <b>OMEGA — Android & Wear OS Companion</b>
      <br/>
      Permanent connection: approvals, notifications, MERLIN chat,
      system health — on your phone and on your wrist.
    </td>
  </tr>
</table>

---

## Mission Control

Every operation is visible in one place: system health, the agent fleet,
opportunities scored by expected value, revenue, and the next best action.

<p align="center">
  <img src="assets/concepts/desktop-showcase.png" alt="Mission Control" width="100%"/>
</p>

---

## Architecture

Control plane, departments, agents, execution, learning, feedback — designed for
autonomy, with the human at every decision gate.

```mermaid
graph TB
    subgraph "Human Layer"
        H[Human Operator]
    end

    subgraph "OWNEX Core"
        EC[Event Bus]
        SC[Scheduler]
        UM[Unified Memory]
        SL[Security Layer]
    end

    subgraph "Intelligence Layer"
        ME[MERLIN]
        IE[Evolution Engine]
        RL[Recovery Engine]
    end

    subgraph "Agent Departments"
        ORCH[Orchestrator]
        ENG[Engineering]
        QUA[Quality]
        SEC[Security]
        REV[Revenue]
    end

    subgraph "Execution Layer"
        WF[Workflows]
        EX[Executors]
        PC[Platform Connectors]
    end

    subgraph "Memory Layer"
        KM[Knowledge Capture]
        FM[Feedback Loops]
        RM[Reward Models]
    end

    H -->|Strategic Direction| EC
    H -->|Approval Gates| ORCH

    EC --> SC
    EC --> UM
    EC --> SL

    SC --> ORCH
    SC --> ENG
    SC --> QUA
    SC --> SEC
    SC --> REV

    ME --> EC
    ME --> UM

    IE --> EC
    IE --> UM
    IE --> RL

    ORCH --> WF
    ENG --> WF
    QUA --> WF
    SEC --> WF
    REV --> WF

    WF --> EX
    EX --> PC

    EX --> KM
    KM --> FM
    FM --> RM
    RM --> IE

    UM --> ME
    UM --> IE
```

| Layer | Responsibility |
|---|---|
| **OWNEX Core** | Event bus, scheduler, unified memory, security layer |
| **Departments** | Orchestrator · Engineering · Quality · Security · Revenue |
| **Agents** | Autonomous specialists coordinated per department |
| **Execution** | Workflows, executors, platform connectors |
| **Learning** | Feedback loops, knowledge capture, reward models |
| **Evolution** | Self-improvement, version rollback, recovery |

---

## Ecosystem

<p align="center">
  <img src="assets/concepts/mobile-showcase.png" alt="OMEGA mobile experience" width="400"/>
</p>

| Component | Role |
|---|---|
| **ALPHA Desktop** | Command center — core operations |
| **OMEGA Mobile** | Android companion — approvals, chat, sync |
| **Wear OS** | Wrist alerts — critical decisions on the move |
| **MERLIN** | Intelligent assistant with persistent memory |
| **Agents** | Autonomous departments working in parallel |
| **Memory** | Persistent knowledge store (SQLite, namespaced) |
| **Evolution Engine** | Continuous self-improvement with recovery |

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
| ALPHA + OMEGA + Wear OS companions | Production |
| Self-update, version backup, recovery engine | Production |
| 6-language interface (EN, ES, FR, DE, JA, ZH) | Production |

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

## Repository Structure

```
api/              FastAPI application and routers
core/ cores/      Domain engines (cycles, opportunities, execution, learning)
apps/             ORION applications (aegis, atlas, odyssey, hermes)
frontend/         Vue 3 single-page application
android/ wearos/  OMEGA companions
scripts/brand/    Deterministic brand pipeline (SVG → PNG)
assets/           Brand system, banners, concept art, video storyboard
```

---

## Documentation

- [Brand identity](assets/branding/OWNEX_BRAND_IDENTITY.md) — marks, colors, type, usage rules
- [Brand usage guide](BRAND_USAGE_GUIDE.md) — comprehensive brand guidelines
- [Design tokens](assets/branding/design-tokens.json) — machine-readable brand tokens
- [Architecture diagram](assets/concepts/architecture.md) — system architecture with Mermaid
- [Agent Charter](.ai/AGENT_CHARTER.md) — constitution and operating rules
- [Architecture decisions](.ai/ARCHITECTURE_FINAL.md) — full architectural decisions

---

## Philosophy

**Consolidation over expansion.** OWNEX does not grow by adding modules; it grows by
closing loops. Every component must produce observable results, survive restarts, and
connect to at least one real consumer. If it cannot be verified, it does not exist.

---

## License

MIT — see [LICENSE](LICENSE). Brand fonts: SIL OFL 1.1 (Google Fonts).

---

<p align="center">
  <img src="assets/logos/ownex-mark.png" alt="OWNEX" width="100"/>
</p>

<p align="center"><sub>OWNEX — The Personalized Autonomous Operating System</sub></p>
