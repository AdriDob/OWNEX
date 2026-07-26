# ORION Platform — Project Context

## 🎯 **Descripción General**

Rastro (anteriormente CATEYE) es un sistema de inteligencia operativa privada que ejecuta descubrimiento → reconocimiento → hipótesis → validación → reporte de vulnerabilidades. Incluye Revenue Intelligence, Offensive Intelligence, Knowledge Graph, COPILOT Senior Agent, y automatización vía Scheduler.

## 🏗️ **Technology Stack**

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI · Uvicorn
- **ORM**: SQLAlchemy 2.0+ · Alembic
- **Database**: SQLite (dev/desktop) · PostgreSQL (prod)
- **Security**: cryptography (AES-256-GCM, Ed25519)

### Frontend
- **Framework**: Vue 3 + TypeScript
- **Build**: Vite · Tailwind CSS 4 + ShadCN Vue
- **Desktop**: Tauri (Rust + WebView) · PyInstaller

### AI & Intelligence
- **Models**: Ollama (qwen2.5-coder:1.5b) · FCC Proxy · OpenRouter
- **Testing**: pytest (1400+ tests) · pytest-timeout · pytest-cov
- **Linting**: Ruff
- **Type Checking**: MyPy (strict mode)

### Environment
- **CI/CD**: GitHub Actions
- **Pre-commit**: Ruff + pytest hooks

---

## 🏗️ **System Architecture**

### Core Components
- **Unified Memory** — 10 namespaces including "economic", "offensive", "knowledge"
- **Decision Journal** — Append-only log of all decisions
- **Knowledge Graph** — Graph database for findings, reports, decisions
- **Senior Copilot** — 5 authority levels, 4 confidence bands, 6 policy rules
- **Evidence Graph** — Evidence for/against/neutral per hypothesis
- **Integration Center** — 23 integration definitions in 7 categories
- **Secrets Manager** — IdentityVault with AES-256-GCM
- **Health Center** — Unified monitoring across 3 systems

### Key Apps
| App | Logo | Purpose | Status |
|:---|:---|:---|:---|
| **AEGIS** | 🛡️ | Active pentesting | ✅ Production |
| **CATEYE** | 👁️ | Bug bounty operations | ✅ Production |
| **ATLAS** | 📈 | Financial intelligence | ✅ Production |
| **ODYSSEY** | 🎲 | Predictive markets | ✅ Stable |
| **MERLIN** | 🤖 | Automation & Operations | ✅ Production |

### Event Architecture
- **EventBus** — Event-driven communication
- **Scheduler** — Job execution and timing
- **Normalizer** — Registry + types

### Events Network
- **CATEYE Core (Legacy)** - publishes: platform:balance:updated, payout:received, etc.
- **Core EventBus (ORION)** - receives events, publishes to legacy
- **Apps (ATLAS, ODYSSEY)** - consume events via Core EventBus
- **Mobile (Companion)** - receives events via EventBus

---

## 📱 **System Components**

### 1. Revenue Intelligence
- EconomicMemory – program-level tracking and ranking
- Time-Waste Detector – idle time monitoring and suggestions
- Report Scoring – acceptance probability prediction
- TargetPrioritizer – EV-based target ranking with economic signals
- RevenuePipeline – finding → evidence → report → platform → payout

### 2. Offensive Intelligence
- HTTP Probes – 5 reasoners (IDOR, SSRF, XSS, SQLi, Auth Bypass)
- Contradiction Engine – cross-vulnerability analysis
- Evidence Composer – standardized PoC and metadata

### 3. Knowledge Intelligence
- Evidence Graph – structured relationships between findings
- Knowledge Graph – SQL storage of evidence and decisions

### 4. Automation & Operations
- Scheduler – workflow execution and timing
- Senior Copilot – autonomous decision-making and assistance
- Extension SDK – module integration framework

---

## 🔧 **Configuration & Setup**

### Environment Variables
- **CATEYE_DESKTOP** – flag to enable desktop mode
- **ORION_ENVIRONMENT** – development/production
- **DATABASE_PATH** – SQLite/DB connection string
- **API_KEY** – authentication for platform connectors

### Quick Start Commands
```bash
# Environment setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Application run
python run.py

# Access web interface
http://127.0.0.1:8000

# Database backup
python run.py --backup

# Add new target
python run.py --add-target <name> --domain <domain>

# Health check
curl http://127.0.0.1:8000/api/health
```

---

## 📊 **System Status**

| Metric | Status | Details |
|--------|--------|---------|
| **Version** | `v4.6.0 STABLE` | July 2026 |
| **Tests** | 1419+ pass | 8 xfailed, 0 new failures |
| **Lint** | ✅ Ruff clean | 0 errors |
| **Pipeline** | ✅ E2E functional | 13 stages |
| **HTTP Probes** | ✅ 5 types | 56 tests |
| **Commands** | ✅ 107 registered | 14 categories |
| **Widgets** | ✅ 10 types | drag-and-drop |
| **Health Center** | ✅ 3 systems | score 0-100 |

---

## 🎯 **Engineering Principles**

1. **Evidence Rule** — Never assume, always inspect
2. **Minimum Intervention** — 30 lines > 500
3. **80% Rule** — Can existing component do 80%?
4. **Simplicity** — Simple → Stable → Fast → Elegant
5. **No Regressions** — Ruff + Tests + TypeCheck always
6. **Revenue Priority** — Detection → Acceptance → Revenue

---

## 🚀 **Key Features**

### Revenue Intelligence
- Dynamic USD/hour metrics from payout history
- Platform speed estimation from real data
- Economic ranking by acceptance rate, payout, uniqueness
- Rewards → detection probability → speed optimization

### Offensive Intelligence
- 5 vulnerability types: IDOR, SSRF, XSS, SQLi, Auth Bypass
- Evidence bundles with PoC, CVSS, CWE, CAPEC, MITRE
- Evidence verification and contradiction analysis

### Automation
- 13-stage pipeline execution
- Event-driven workflow coordination
- Continuous learning from outcomes

---

## 🔐 **Security Model**

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

## 📞 **Contact & Support**

For questions, please refer to the project documentation or repository issues.

---

<div align="center">
<sub>
  <strong>ORION Platform</strong> · Private Intelligence OS · v4.6.0 STABLE<br/>
  100% local · No cloud · Autonomous<br/>
  <a href="https://github.com/AdriDob/Rastro">GitHub</a> · 
  <a href=".ai/ROADMAP.md">Roadmap</a> · 
  <a href=".ai/CURRENT_STATE.md">Current State</a> · 
  <a href=".ai/STRATEGIC_VISION.md">Strategic Vision</a>
</sub>
</div>
```
