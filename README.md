# OWNEX — Semi-Autonomous Work Operating System

**Version:** 9.0.0  
**Python:** 3.11+  
**Built with:** FastAPI · Vue 3 · Tauri v2

---

## Quick overview

OWNEX is a personal autonomous work operating system. It discovers opportunities (bug bounty, dev bounty, AI work, freelance), evaluates them, prepares deliverables, and tracks results — running mostly on your machine, not in the cloud.

It's not a chatbot. It's not a dashboard. It's software that runs locally and works for you.

**Core principles:** Freedom first · Zero barrier entry · Maximum value generation · Intelligence before action · Human control (you're the authority final) · Universal solutions before specialized ones

---

## What it actually does (verified, not roadmap)

- Discovers opportunities from 135+ curated sources across 36 categories
- Scores each opportunity on a 0–100 barrier/economic spectrum (no interviews, no portfolio, no payment gates needed)
- Prepares deliverables (READMEs, proposals, work packages) ready to submit
- Runs 7 autonomous work cycles with 28 scheduled jobs
- Generates daily briefings (system + personal + market + focus)
- Tracks income, projections, ROI per platform
- Security pipeline with 7 stages, auto-submit to finder queues
- Desktop (Tauri v2 + PyInstaller), mobile companion (Android APK ~5 MB), Wear OS
- **100% local by default** — nothing leaves your machine unless you explicitly send it

> **The Revenue Rule:** No feature enters the roadmap unless it increases vulnerability detection quality, evidence quality, acceptance probability, or system learning. No exceptions.

---

## Architecture (the essentials)

OWNEX is a **modular monolith**. One FastAPI process, EventBus-driven, single database. No microservices, no external message queue, no lock-in.

Diagram: `docs/diagrams/architecture.mmd` (Mermaid)

---

## Daily flow (approximately)

| Time | What happens |
|------|-------------|
| 06:15 | Work Bank: discover → filter → rank by EV → prepare packages |
| 07:00 | Mission Control: top pick of the day + skill gap + learning plan |
| 08:00 | Market: platform report, friction tiers, emerging categories |
| 09:00 | Capital: revenue dashboard, earned/pending/ROI per platform |
| 14:00 | Security: findings → evidence → report → auto-submit |
| 18:00 | Executive: "Did we make money this week?" USD/hour per platform |
| 22:00 | Backup: version backup + health snapshot persisted |

---

## Installation (choose your platform)

### Linux (development)

```bash
git clone https://github.com/AdriDob/OWNEX.git
cd OWNEX

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install

python run.py          # FastAPI on http://localhost:8000
# another terminal: cd frontend && npm run dev  # Mission Control on http://localhost:5173
```

### Windows

Download the Tauri installer from Releases (or build from source). Runs natively, no Python/Node required.

### Android

```bash
cd android
./gradlew assembleDebug
# Install the APK via ADB or transfer to device
# ~5 MB, native mic/voice, connects to your local backend
```

### The universal installer

```bash
python install.py
# Guided wizard: use case → modules → experience level → platforms → integrations
# Sets up .venv, DB, credentials, desktop, notifications
```

---

## v12 — Real Integrations & Income OS

External connections, financial data, and remote-job pipeline — all read-only by default, human approval for anything that moves money or submits work.

**V12.1 — Upwork Removed + Remote Job Matcher Integrated**

| Module | Status |
|--------|--------|
| Connection Manager (`/integrations/connections`) | ✅ catalog, setup, sync, import |
| IOL Inversiones (REST OAuth2 + refresh token cifrado + quotes + WebSocket market data) | ✅ implemented — requiere credenciales reales para validar |
| PPI Portfolio Personal (REST oficial v1.0) | ✅ implemented — sandbox disponible |
| Binance (ccxt, solo lectura) | ✅ implemented — sin trading/withdrawals por diseño |
| Importación manual CSV/JSON/XLSX (Cocos, Balanz, etc.) | ✅ con dedup + provenance |
| Cartera consolidada normalizada (sin mezclar monedas, sin FX inventado) | ✅ |
| Income → Ledger bridge (ingresos de inversión al ledger canónico) | ✅ acción explícita del usuario |
| OWNEX MCP Server (`python -m core.mcp_ownex_server`) | ✅ 9 tools read-only + consent scopes + audit log |
| **Remote Job Matcher (`/operations/remote-jobs`)** | ✅ **feeds reales (Remotive/Arbeitnow/RemoteOK) + score explicable + perfil persistente + tracker con aprobación humana** |
| Application drafter (borradores solo con datos reales del perfil) | ✅ drafts, nunca auto-envío |
| **Upwork** | ❌ **Excluido del catálogo activo** — removido V12.1 |

**Honestidad:** ninguna integración externa fue validada con credenciales reales todavía — están implementadas según documentación oficial y testeadas con mocks. Upwork está excluido del catálogo activo.

---\n\n## Actually working (vs roadmap)

| Area | Status |
|------|--------|
| 135+ discovery sources (HackerOne, Bugcrowd, Intigriti, YesWeHack, Opire, IssueHunt, Freelancer, OpenCollective…) | ✅ |
| Zero-barrier scoring spectrum (0–100) | ✅ |
| Work Bank + daily companion + preparation | ✅ |
| 7 work cycles, 28 scheduled jobs | ✅ |
| Desktop (Tauri + PyInstaller), mobile companion (Android) | ✅ build-verified |
| Wear OS native | ✅ Completed |
| Income tracking + projections | ✅ |
| Security pipeline (recon → hypothesis → validation → evidence → report) | ✅ |
| OAR AI Runtime (routing + resilience + observability) | ✅ |
| AI providers: local-first (Ollama), free cloud fallback, deterministic degradation | ✅ |
| No telemetry, no cloud account required | ✅ |
| Revenue tracking with real payout data | ✅ |

---

## Security (because it matters)

Everything is local-first by default. Security layers:

- **IdentityVault:** AES-256-GCM, random key, `chmod 600`
- **Ed25519 licenses:** 25-character format
- **CSRF protection:** Double-submit cookie on all mutating endpoints
- **Rate limiting:** Per-identity with IP fallback
- **Audit log:** Append-only JSONL, 10 MB rotation
- **Session security:** AES-256-GCM, device binding, 30-min expiry

No telemetry. No cloud account. Your data stays on your machine.

---

## License

**Proprietary.** All rights reserved.

OWNEX is a private competitive-advantage asset. It does **not** sell a service to a customer. **OWNEX works for me.**

---

## Built with

- **Backend:** Python 3.11+ · FastAPI · SQLAlchemy 2.0 · 3,228+ tests, Ruff clean, mypy strict
- **Frontend:** Vue 3 + TypeScript · Tailwind CSS v4 · Vite · 92 routed pages
- **Desktop:** Tauri v2 (Rust + WebView2) + PyInstaller sidecar
- **Mobile:** Capacitor (Android) · native mic/voice, APK ~5 MB
- **AI Stack:** Free-first con fallback y modo degradado: local → free cloud → reglas
- **Database:** SQLite (dev/desktop) · PostgreSQL (prod) · Single DB, no external queue
- **Testing:** pytest · pytest-cov · pytest-timeout · `make test` · `make test-fast`

---

## Commands you'll actually use

```bash
# Testing
python scripts/dev test          # full suite (excluye test_security.py)
python scripts/dev test-fast     # smoke: scoring + scheduler + DWE

# Lint + typecheck
make check                       # ruff + mypy scoped + fast tests
make fmt                         # write fixes

# Backend
python run.py                    # full system
python run.py --add-target <name> --domain <domain>
python run.py --backup

# Frontend (from frontend/)
npm run dev                      # dev server
npm run build                    # production build

# Branding pipeline
scripts/brand/regenerate.sh      # logo + banners + README badge sync
```

---

## Tesla dark style

Pure black surfaces, white primary accent, `#e82127` (Tesla red) as the only saturated accent, no noise, no gradients, no glows, no colors beyond the palette.

---

**© 2026 OWNEX — Autonomous Work Operating System · The Aperture Nexus**

*Built with discipline, not hype. Works for one person, on one machine, with maximum autonomy.*
