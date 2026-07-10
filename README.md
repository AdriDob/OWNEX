# CATEYE v3.0.0 — Bug Bounty Intelligence System

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://github.com/AdriDob/Rastro/releases)
[![Python](https://img.shields.io/badge/python-3.10+-purple.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.95+-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/vue-3.5-4FC08D.svg)](https://vuejs.org/)
[![Status](https://img.shields.io/badge/status-stable-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)]()

---

## What is CATEYE?

CATEYE is a **private operational intelligence system** for bug bounty hunters. It automates the complete vulnerability hunting lifecycle — from program discovery and reconnaissance to hypothesis generation, validation, reporting, and financial tracking.

It is **not** a scanner. It is **not** a framework. It is a **daily companion** that augments your hunting workflow with automation, prioritization, and learning — while keeping you in control of every decision.

---

## Who is it for?

- **Bug bounty hunters** who manage multiple programs and need automation
- **Security researchers** who want AI-assisted validation and reporting
- **Anyone** who spends more time on repetitive tasks than on actual hunting

## Who is it NOT for?

- Teams or enterprises (CATEYE is single-user, local-first)
- Pentesters needing a traditional scanner
- Anyone looking for a cloud/SaaS solution
- Beginners who haven't done manual bug bounty hunting

---

## Philosophy

1. **Eliminate repetitive human work** — Every feature must answer: "Does this remove human work or just add complexity?"
2. **ORION decides, modules execute** — ORION is read-only (with one documented exception). It recommends, you decide.
3. **One official pipeline** — The scheduler is the only runtime flow. No parallel state machines.
4. **Persistence first** — Critical state survives restarts (SQLite WAL, persistent EventBus, SystemState in DB).
5. **Security over features** — No secrets in code, CSRF on all mutating routes, AES-256-GCM encryption, JSONL audit logging.

---

## What CATEYE can do

### 🎯 Economic Intelligence
- **ORION Score** (0.0-1.0) — 6-factor program ranking algorithm
- **EVH** (Expected Value per Hour) — monetary ROI per program
- **Pattern Learning** — automatically learns from earnings patterns
- **Auto-prioritization** — scheduler consults ORION to pick next target

### 🧠 Multi-Agent System
- 8 specialized agents (Coordinator, Research, Validator, Exploit, Documentation, Strategy, Memory, Financial)
- Internal event bus communication (pub/sub)
- Multi-AI support: Gemini, Ollama, OpenAI, OpenRouter

### 🔍 Autonomous Reconnaissance
- Orchestrates 15+ tools: Subfinder, Amass, httpx, Katana, nuclei, ffuf, gau, waybackurls, dnsx, naabu
- OWASP ZAP integration (spider + passive scan)
- 16 OSINT clients: Shodan, Censys, VirusTotal, SecurityTrails, and more
- 3 scan modes: FAST (~2-5 min), DEEP (~15-30 min), API (no external tools)

### 🔎 Hypothesis Generation & Validation
- 8 rule-based generators (IDOR, auth bypass, SSRF, privesc, data exposure, GraphQL, business logic, file operation)
- RequestReplayer (baseline vs probe comparison)
- LLM semantic analysis
- Confidence scoring and pattern memory

### 📊 Professional Reporting
- AI-assisted report generation
- Export: Markdown, PDF, HTML, TXT
- Direct submission to platforms via API keys
- Auto-report: confirmed finding → automatic draft

### 💰 Financial Truth Layer
- Single source of truth for all earnings
- 5 value categories: VERIFIED_REAL, PENDING, ESTIMATED, MANUAL, UNKNOWN
- 4 blockchain connectors (BTC, ETH, SOL, TRX)
- Withdrawal tracking with reorg-safe confirmations
- Bank payout detection (Plaid API + CSV import)
- Exchange integrations (Binance, Coinbase, Kraken, Bybit)

### 🔐 Security & Privacy
- 100% local and privacy-first
- AES-256-GCM encrypted credential vault
- Never auto-exploits or auto-submits without human approval
- CSRF double-submit cookie middleware
- JSONL audit trail with rotation
- Rate limiting by identity + IP fallback

### 🔌 Platform Integrations
- **Bug Bounty:** HackerOne, Bugcrowd, Intigriti, YesWeHack (scraping + earnings sync)
- **AuthHub:** Gmail OAuth2, WhatsApp, Telegram — token storage in Identity Vault
- **Recon Tools:** 15+ external (must be installed separately)

---

## What CATEYE does NOT do

- ❌ Submit reports automatically without approval
- ❌ Exploit vulnerabilities outside the validation pipeline
- ❌ Modify program scopes
- ❌ Accept platform Terms of Service
- ❌ Spend money (crypto/fiat) without explicit user command
- ❌ Replace human judgment on findings and reports
- ❌ Be multi-user or SaaS
- ❌ Be a C2 or malware
- ❌ Invent findings without evidence
- ❌ Delete evidence automatically

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- Git
- External recon tools (optional): subfinder, httpx, katana, nuclei, amass, etc.

### Installation

```bash
# Clone
git clone https://github.com/AdriDob/Rastro.git
cd Rastro

# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Initialize database
python run.py --setup

# Seed demo data (optional but recommended)
python scripts/seed_real.py
```

### Start

```bash
# Development mode (browser)
python run.py --browser

# Or manual: backend + frontend separately
source .venv/bin/activate
python run.py --dev

# In another terminal
cd frontend && npm run dev
```

Open `http://127.0.0.1:8000` in your browser.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     DESKTOP LAYER                             │
│  run.py (State Machine) → PyWebView + Uvicorn + System Tray   │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                     API LAYER (FastAPI)                        │
│  60+ routers · CORS · Auth · Rate Limiting · Scheduler       │
└──────┬───────────────────────────────────────────┬────────────┘
       │                                           │
┌──────▼──────────────────┐     ┌──────────────────▼────────────┐
│    CORE ENGINES (cores/) │     │       UI (Vue 3 SPA)          │
│                          │     │                              │
│  ├─ orion/     (AI)      │     │  46+ pages                   │
│  ├─ agents/    (8 agents)│     │  9 Pinia stores              │
│  ├─ recon/     (15 tools)│     │  Cyber theme glassmorphism   │
│  ├─ engine/    (hypoth.) │     │  Tailwind CSS + Radix UI     │
│  ├─ validation/          │     │  WebSocket bridge            │
│  ├─ events/    (pub/sub) │     │                              │
│  ├─ financial/ (truth)   │     │                              │
│  ├─ crypto/    (wallets) │     │                              │
│  └─ 30+ more modules     │     │                              │
└──────┬──────────────────┘     └──────────────────────────────┘
       │
┌──────▼───────────────────────────────────────────────────────┐
│                     DATABASE (SQLite)                          │
│  36+ tables · SQLAlchemy · WAL mode · FK constraints          │
└──────────────────────────────────────────────────────────────┘
```

---

## Documentation

| Document | Description |
|---|---|
| [`SYSTEM.md`](SYSTEM.md) | Full system architecture and technical reference |
| [`FUNCTIONAL_SPEC.md`](FUNCTIONAL_SPEC.md) | Verified capabilities — what CATEYE can and cannot do |
| [`USER_GUIDE.md`](USER_GUIDE.md) | Practical manual for daily use (Spanish) |
| [`DAILY_WORKFLOW.md`](DAILY_WORKFLOW.md) | Daily, weekly, and monthly routines |
| [`RELEASE_NOTES_v3.0.0.md`](RELEASE_NOTES_v3.0.0.md) | v3.0.0 release notes |
| [`SETUP_GUIDE.md`](SETUP_GUIDE.md) | Optimal configuration guide |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | Python + FastAPI | 3.10+ / 0.95+ |
| ASGI | Uvicorn | 0.22+ |
| ORM | SQLAlchemy + Pydantic v2 | 2.0+ |
| Database | SQLite (WAL) | — |
| Frontend | Vue 3 + TypeScript + Vite | 3.5+ / 5.8+ / 6.4+ |
| CSS | Tailwind CSS | 4.1+ |
| State | Pinia | 3.0+ |
| UI | Radix Vue / Reka UI + Lucide Vue | — |
| AI | Gemini · OpenRouter · Ollama · OpenAI | — |
| Desktop | PyInstaller + PyWebView + Pystray | — |
| Security | Cryptography (AES-256-GCM) | — |
| Testing | pytest + pytest-timeout + pytest-cov | — |

---

## Status

- **Version:** 3.0.0 STABLE
- **Tests:** 393 pass, 2 xfailed, 0 failures
- **Lint:** 0 errors (ruff)
- **Pipeline:** 5-stage E2E functional
- **License:** Proprietary (Ed25519 validation)

---

## License

Proprietary. See [SECURITY_POLICY.md](.ai/SECURITY_POLICY.md) for security details.

---

<div align="center">
  <sub>Built by bug bounty hunters, for bug bounty hunters. Hecho en 🇦🇷.</sub>
</div>
