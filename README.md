# ORION Platform — Private Intelligence Operating System

## Quick Start

```bash
# 1. Clone
https://github.com/AdriDob/Rastro.git
cd Rastro

# 2. Environment Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Application Run
python run.py

# 4. Access Web Interface
http://127.0.0.1:8000
```

## 📊 System Status Dashboard

| Indicator | Status | Details |
|-----------|--------|---------|
| **Version** | `v4.6.0` | Julio 2026 STABLE |
| **Tests** | 2290 collected | ✅ All pass (Ruff clean) |
| **Lint** | ✅ Ruff clean | 0 errors |
| **Pipeline** | ✅ E2E functional | 13 stages |
| **HTTP Probes** | ✅ 5 types | 56 tests |
| **Commands** | ✅ 107 registered | 14 categories |
| **Widgets** | ✅ 10 types | drag-and-drop |
| **Health Center** | ✅ 3 systems | score 0-100 |
| **Attack Pipeline** | ✅ 6 reasoners | IDOR, SSRF, XSS, SQLi, Auth, Web3 |
| **Financial Hub** | ✅ 61 tests | KYC, Routes, Taxes, Documents |

---

## 📋 Documentation Structure

### Core Documentation
| **[AGENTS.md](AGENTS.md)** — CATEYE/OpenCode workflow rules
|- **[docs/ATTACK_PIPELINE.md](docs/ATTACK_PIPELINE.md)** — Pipeline de hipótesis a evidencia
|- **[docs/ORION_OPERATION_MANUAL.md](docs/ORION_OPERATION_MANUAL.md)** — Manual de operación diaria
|- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** — Referencia completa de API REST
|- **[PROJECT_CONTEXT.md](.ai/PROJECT_CONTEXT.md)** — Project context
|- **[ROADMAP.md](.ai/ROADMAP.md)** — Platform roadmap

### Supporting Documentation
|- **[STRATEGIC_AUDIT.md](.ai/STRATEGIC_AUDIT.md)** — Strategic audit framework
|- **[CODE_QUALITY.md](.ai/CODE_QUALITY.md)** — Development standards
|- **[SECURITY_POLICY.md](.ai/SECURITY_POLICY.md)** — Security policy
|- **[TESTING_POLICY.md](.ai/TESTING_POLICY.md)** — Testing guidelines
|- **[ARCHITECTURE_FINAL.md](.ai/ARCHITECTURE_FINAL.md)** — Arquitectura del sistema

---

## 🎯 Engineering Principles

1. **Evidence Rule** — Never assume, always inspect
2. **Minimum Intervention** — 30 lines > 500
3. **80% Rule** — Can existing component do 80%?
4. **Simplicity** — Simple → Stable → Fast → Elegant
5. **No Regressions** — Ruff + Tests + TypeCheck always
6. **Revenue Priority** — Detection → Acceptance → Revenue

---

## 🏗️ Technology Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI · Uvicorn
- **ORM**: SQLAlchemy 2.0+ · Pydantic v2
- **Database**: SQLite WAL · PostgreSQL
- **Security**: Cryptography · AES-256-GCM · Ed25519

### Frontend
- **Framework**: Vue 3.5+ · TypeScript
- **Build**: Vite 6.4+ · Tailwind CSS 4.1+
- **State**: Pinia 3.0+ · Composables

### AI & Intelligence
- **Models**: Gemini · OpenRouter · Ollama · OpenAI
- **Testing**: pytest (2,290 tests) · Ruff (strict)

---

## 📱 System Architecture

### Core Components
- **EventBus** — Pub/sub persistent over SQLite
- **Decision Journal** — Append-only log of every decision
- **Knowledge Graph** — Nodes & edges for findings, reports, decisions
- **Unified Memory** — 10 namespaces
- **Senior Copilot** — 5 authority levels, AI agent

### Key Apps
| App | Logo | Purpose | Status |
|:---|:---|:---|:---|
| **AEGIS** | 🛡️ | Active pentesting | ✅ Production |
| **CATEYE** | 👁️ | Bug bounty operations | ✅ Production |
| **ATLAS** | 📈 | Financial intelligence | ✅ Production |
| **ODYSSEY** | 🎲 | Predictive markets | ✅ Stable |
| **MERLIN** | 🤖 | Automation & Operations | ✅ Production |

---

## 🔐 Security Model

```
+------------------------------------------------------------------+
|                    SECURITY MODEL                                 |
+------------------------------------------------------------------+
| 100% local .............. Nothing leaves your machine. No telemetry.|
| AES-256-GCM ............ Credential vault encrypted. Random key.    |
| CSRF ..................... Double-submit cookie on all mutantes routes. |
| Rate limiting .......... By identity with IP fallback.             |
| Audit log .............. JSONL append-only. 10MB rotation.        |
| Ed25519 ................. Asymmetric license validation.         |
| No secrets in repo ..... API keys in IdentityVault or env vars.    |
+------------------------------------------------------------------+
```

---

## 🎯 Mission

**ORION** is not an application. It is an **operating system for work** — a private intelligence platform that runs specialized apps for bug bounty hunting, financial intelligence, security operations, and autonomous decision-making.

> **You don't operate. You decide.** That is the goal.

---

<div align="center">
<sub>
  <strong>ORION</strong> · Private Intelligence OS · v4.6.0 STABLE<br/>
  100% local · No cloud · Autonomous<br/>
  <a href="https://github.com/AdriDob/Rastro">GitHub</a> ·
  <a href=".ai/ROADMAP.md">Roadmap</a> ·
  <a href=".ai/PROJECT_CONTEXT.md">Project Context</a> ·
  <a href=".ai/CURRENT_STATE.md">Current State</a>
</sub>
</div>


| Command | Purpose |
|---------|---------|
| `python run.py --backup` | Create database backup |
| `python run.py --add-target <name> --domain <domain>` | Add new target |
| `.venv/bin/python -m pytest --timeout=60` | Run tests |
| `.venv/bin/python -m ruff check .` | Lint Python |
| `curl http://127.0.0.1:8000/api/health` | Health check |

---

## 📧 Contact

For questions or support, please refer to the project documentation or repository issues.

---

<sub>Generated as part of systematic documentation improvement initiative</sub>
```