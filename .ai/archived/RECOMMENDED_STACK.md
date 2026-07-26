# Recommended Stack — ORION Technology Choices

> Authoritative list of what technologies ORION uses, plans to use, and explicitly excludes.

---

## Core

| Layer | Choice | Why | Alternative Rejected |
|---|---|---|---|
| Backend | Python 3.11+ | Ecosystem, AI/ML libraries, async support | Node.js, Go, Rust |
| API | FastAPI | Fast, async, auto-docs, Pydantic validation | Flask, Django REST |
| ORM | SQLAlchemy | Mature, async, migration support | SQLite raw, Tortoise |
| Database | SQLite (dev) / PostgreSQL (prod) | Correct for single-user desktop use | MySQL, MariaDB |
| Events | Custom EventBus (SQLite-backed) | Purpose-built for ORION's architecture | Redis pub/sub, RabbitMQ |
| Frontend | Vue 3 + TypeScript | Fast dev, good ecosystem | React, Svelte |
| CSS | Tailwind CSS v4 | Utility-first, small bundle | Bootstrap, SCSS |
| Charts | Chart.js | Lightweight, sufficient for dashboards | D3 (for KG only), ApexCharts |
| Desktop | Tauri (Rust + WebView) | Small binary, secure | Electron |

---

## Security Tooling (Keep)

| Tool | Purpose | Priority |
|---|---|---|
| Nuclei | Template-based vulnerability scanning | Active |
| Subfinder | Subdomain discovery | Active |
| Katana | Web crawling | Active |
| Amass | External attack surface mapping | Active |
| Naabu | Port scanning | Active |
| Shodan | Exposure intelligence | Active |
| Uncover | Infrastructure discovery | Active |
| httpx | HTTP probing | **Integrate P1** |
| Playwright | Browser automation (screenshots, HAR) | **Integrate P1** |
| sqlmap | SQLi validation | **Integrate P2** |
| FFUF | Web fuzzing | **Integrate P2** |

---

## AI/LLM

| Tool | Purpose | Status |
|---|---|---|
| Ollama | Local LLM inference (primary) | Active |
| OpenRouter | Premium LLM fallback | Active |
| sentence-transformers | Semantic memory search | **Integrate P3** |
| No agent framework | ORION EventBus > LangChain/CrewAI | Explicit decision |

---

## Financial (Read-Only)

| Tool | Purpose | Status |
|---|---|---|
| CoinGecko | Crypto prices | Active |
| CCXT | Exchange data | **Integrate P2** |
| Takenos | ARS payouts | Active |
| No auto-trading | ORION recommends, user approves | Hard rule |

---

## Excluded (with reason)

| Technology | Reason |
|---|---|
| LangChain, LangGraph, CrewAI, AutoGen | Overengineered. EventBus is simpler and more robust. |
| Neo4j, ArangoDB | Premature. SQLite handles <10K KG nodes. |
| Grafana, Redash, Metabase | Transactional UI ≠ dashboards. ORION needs operational UI. |
| Redis | No need. SQLite with WAL is fast enough for single-user. |
| Electron | Tauri is lighter, more secure, smaller binary. |
| React | Vue 3 is already chosen and working well. |
| Polymarket, sports betting | Gambling. Not aligned with revenue mission. |
| Auto-trading bots | ORION recommends, user executes. Hard safety boundary. |
| OWASP ZAP, Caido | Better tools exist (Nuclei, httpx, custom reasoners). |
| Metasploit | Exploitation is out of scope for bug bounty. |
