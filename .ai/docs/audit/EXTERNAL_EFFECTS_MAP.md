# EXTERNAL EFFECTS MAP — OWNEX (2026-09-30)

## All External Side Effects

Every point where OWNEX touches the outside world.

---

## 1. HTTP/REST Calls (Outbound)

| Target | Protocol | Auth | Purpose | File |
|--------|----------|------|---------|------|
| HackerOne | GraphQL + REST | Bearer | Bounty discovery, submission | `adapters/security/hackerone.py` |
| Bugcrowd | REST | API key | Bounty discovery, submission | `adapters/security/bugcrowd.py` |
| Intigriti | REST | API key | Bounty discovery | `adapters/security/intigriti.py` |
| YesWeHack | REST | API key | Bounty discovery | `adapters/security/yeswehack.py` |
| Synack | REST | API key | Bounty discovery | `adapters/security/synack.py` |
| Immunefi | REST | Bearer | Bounty discovery | `adapters/security/immunefi.py` |
| GitHub | GraphQL + REST | PAT | Issues, PRs, bounties | `adapters/direct_work_github.py`, `github_executor.py` |
| GitLab | REST | Token | Issues, MRs | `adapters/gitlab.py` |
| BugBountyHQ | REST | API key | Bounty discovery | `direct_work_bugbounty.py` |
| Algora | REST | Bearer | Bounty discovery | `direct_work_algora.py` |
| Opire | REST | Bearer | Bounty discovery | `direct_work_opire.py` |
| Polar | REST | Bearer | Payments | `direct_work_polar.py` |
| OpenAI | REST | Bearer | LLM inference | `cores/ai/` |
| Anthropic | REST | Bearer | LLM inference | `cores/ai/` |
| FCC Proxy | HTTP | Local | Local LLM proxy | `cores/ai/providers/` |
| MPT (Money Printer) | HTTP | Local | Local LLM | `services/moneyprinter.ts` |
| GitHub API | GraphQL | PAT | Issues, bounties | `cores/opportunity/executors/github_executor.py` |
| FCC Proxy | HTTP | Local | LLM gateway | `cores/ai/providers/` |
| MPT (Money Printer) | HTTP | Local | Local LLM | `services/moneyprinter.ts` |

---

## 2. WebSocket Connections (Outbound)

| Target | Protocol | Auth | Purpose | File |
|--------|----------|------|---------|------|
| Local Backend | WS | Token (query) | Real-time notifications | `stores/notifications.ts:80` |
| Local Backend | WS | Token (query) | Terminal | `TerminalView.vue:71` |
| Local Backend | WS | Token (query) | Bounty stream | `useBountyStream.ts:20` |

---

## 3. Browser Automation (Playwright)

| Target | Purpose | File |
|--------|---------|------|
| GitHub | PR creation, issue interaction | `cores/opportunity/executors/github_executor.py` |
| Bug bounty platforms | Submission, claim | Various executors |
| General web | Reconnaissance | `cores/opportunity/executors/*` |

**CRITICAL**: Browser automation is **not** the product foundation. It's an isolated adapter capability.

---

## 3. Git Operations

| Operation | Target | Auth | File |
|-----------|--------|------|------|
| `git clone` | GitHub repos | PAT | `cores/opportunity/executors/github_executor.py` |
| `git push` | PR creation | PAT | `github_executor.py` |
| `git status` | Repo status | None (local) | `api/routers/merlin.py:267` |
| `git push` | Remote sync | PAT | Various executors |

---

## 4. File System Operations

| Operation | Path | Trigger |
|-----------|------|---------|
| Read/Write JSON | `~/.ownex/` | State persistence |
| Read/Write JSON | `~/.orion/` | Credentials, config |
| Read/Write JSON | `<repo>/data/` | Dev state |
| Read/Write SQLite | `database/catseye.db` | ORM |
| Read/Write SQLite | `~/.ownex/database/*.db` | Knowledge, recovery |
| Write logs | `logs/` | App logs |
| Write screenshots | `/tmp/` | QA (stub) |
| Execute shell | `subprocess` | Various tools |

---

## 5. Credential Storage & Access

| Credential Type | Storage | Encryption | Access |
|-----------------|---------|------------|--------|
| Platform API keys | `~/.orion/identity_vault.json` | AES-256-GCM | `IdentityVault` |
| Vault key | `~/.orion/identity_vault.key` | Raw 32 bytes, chmod 600 | `VaultCrypto` |
| Device ID | `localStorage` (browser) | None | `main.ts` |
| Auth token | `localStorage` (browser) | None | `lib/api.ts` |
| Session cookie | httpOnly cookie | HttpOnly, SameSite=lax | Backend |
| GitHub PAT | `identity_vault.json` | AES-256-GCM | `IdentityVault` |
| Platform API keys | `identity_vault.json` | AES-256-GCM | `IdentityVault` |
| FCC Proxy | Local env | None | Env var |

**CRITICAL**: `~/.orion/identity_vault.key` (32 bytes, chmod 600) is the **single most critical file** — loss = permanent credential loss.

---

## 5. External Process Execution

| Command | Purpose | Trigger |
|---------|---------|---------|
| `subprocess.run()` | Git, shell tools | Various executors |
| `pyinstaller` | Sidecar build | CI/Release |
| `cargo build` | Tauri build | CI/Release |
| `npm run build` | Frontend build | CI/Release |
| `pyinstaller` | Sidecar build | Release |

---

## 6. Database Operations

| Operation | Target | Frequency |
|-----------|---------|-----------|
| SELECT/INSERT/UPDATE/DELETE | `database/catseye.db` (SQLite) | High |
| SELECT/INSERT/UPDATE/DELETE | `~/.ownex/database/*.db` | Medium |
| Read/Write JSON | `~/.ownex/*.json` | High |
| Read/Write JSON | `<repo>/data/` | Dev only |
| Read/Write JSONL | `~/.ownex/learning/*.jsonl` | Low |

---

## 7. Notifications & Alerts

| Channel | Trigger | Implementation |
|---------|---------|----------------|
| WebSocket | Real-time updates | `stores/notifications.ts` |
| Browser notification | Approval requests | `Notification` API |
| System tray | Background alerts | Tauri tray |
| Email | None implemented | — |
| Telegram | Optional | `cores/notifications/telegram/` |

---

## 8. Scheduled/Background Operations

| Operation | Interval | Trigger |
|-----------|----------|---------|
| Discovery sweep | 1h / config | Scheduler |
| Recon sweep | Config | Scheduler |
| Hypothesis generation | Config | Scheduler |
| Validation sweep | Config | Scheduler |
| Auto-submit sweep | Config | Scheduler |
| Review digest | Daily | Scheduler |
| Autopilot | Config | Scheduler |
| Calibration | Config | Scheduler |
| Financial sync | Config | FinancialSyncScheduler |
| Health checks | 5s | Scheduler |

---

## 9. External Effects by Component

### Opportunity Engine
- **Outbound**: HTTP to sources (GitHub, platforms), WS to backend
- **Inbound**: Webhook callbacks (GitHub, platforms)
- **Side effects**: Creates opportunities, updates state files

### Work Execution
- **Outbound**: HTTP to platforms (submit PR, claim bounty), Git operations
- **Inbound**: Platform webhooks (PR reviews, status changes)
- **Side effects**: Git commits, PRs, bounty claims, file writes

### Security (Validation)
- **Outbound**: HTTP to targets (scans, probes), Nuclei, Nmap
- **Inbound**: Target responses
- **Side effects**: Network traffic to targets, evidence files

### Scheduler
- **Internal**: Spawns jobs, manages lifecycle
- **External**: Triggers adapters, validation, sync
- **Side effects**: All of the above

### Scheduler (Sidecar)
- **Internal**: Manages backend process
- **External**: Spawns Python process, port discovery
- **Side effects**: Process management, port binding

---

## 9. Credential Flows

```
User Input
    ↓
IdentityVault (AES-256-GCM)
    ↓
Memory (decrypted)
    ↓
Adapter/Executor (injected)
    ↓
External API (Bearer/Key)
    ↓
Response
    ↓
Evidence/Result
    ↓
Storage (encrypted)
```

**Never in logs**: Tokens, keys, passwords, private keys — guarded by `tests/test_no_secrets_committed.py`.

---

## 10. Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                        DESKTOP (Tauri)                        │
│  ┌─────────────┐    ┌──────────────────┐    ┌────────────┐  │
│  │   Frontend  │    │   Backend Sidecar  │  │  System    │  │
│  │  (WebView)  │◄───│  (Python/PyInstaller)  │  │  Tray      │  │
│  └──────┬──────┘    └────────┬─────────┘    └────────────┘  │
│         │                    │                              │
│         │ HTTP/WS            │ IPC (stdio)                  │
│         ▼                    ▼                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              BACKEND (Python/FastAPI)                   │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐  │  │
│  │  │ Auth    │ │ API     │ │ Sched   │ │ Adapters/   │  │  │
│  │  │ Middle  │ │ Routers │ │ uler    │ │ Executors   │  │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └──────┬──────┘  │  │
│  │       │           │           │              │          │  │
│  │       ▼           ▼           ▼              ▼          │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │              SQLAlchemy → SQLite (catseye.db)        │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
│         │                                                    │
│         │ HTTP/WS                                            │
│         ▼                                                    │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              EXTERNAL SERVICES                           │  │
│  │  GitHub │ Bugcrowd │ HackerOne │ GitHub │ OpenAI │ ...  │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. External Effects Summary Matrix

| Category | Count | Auth Required | Human Gate |
|----------|-------|---------------|------------|
| HTTP/REST (outbound) | 20+ services | Yes (Bearer/Key) | No (discovery), Yes (submit) |
| WebSocket (outbound) | 3 endpoints | Token (query) | No |
| Browser automation | 10+ targets | Session/Cookie | Yes (submit) |
| Git operations | GitHub/GitLab | PAT | Yes (PR create) |
| File system | Local | — | No |
| Database | SQLite + JSON | — | No |
| Notifications | WebSocket, Browser, Tray | — | No |
| Scheduled jobs | 10+ cycles | Internal | Configurable |
| Notifications | 4 channels | Optional | No |
| Credentials | Vault (AES-256) | — | No |

---

## Critical External Dependencies

| Dependency | Type | Risk if Down | Mitigation |
|------------|------|--------------|------------|
| GitHub API | Core source | High | Cache, fallback |
| HackerOne/Bugcrowd | Bounty sources | High | Multi-source |
| OpenAI/Anthropic | AI features | Medium | Local fallback (FCC) |
| FCC Proxy | Local LLM | Low | Optional |
| GitHub PAT | Auth | Critical | Vault rotation |
| Platform API keys | Auth | Critical | Vault rotation |
| Sidecar binary | Runtime | Critical | Rebuild on change |
| SQLite DB | Storage | Critical | Backup/WAL |
| `~/.orion/identity_vault.key` | Credentials | **Critical** | **Backup mandatory** |

---

## Network Ports

| Port | Service | Direction | Binding |
|--------|---------|-----------|---------|
| 8000-8099 | Backend API | Inbound | 127.0.0.1 (default) |
| 8082 | FCC Proxy | Inbound | 127.0.0.1 |
| 8081 | MPT | Inbound | 127.0.0.1 |
| 11434 | Ollama | Inbound | 127.0.0.1 |
| 5173 | Vite Dev | Inbound | localhost |
| 8094 | Static Server | Inbound | 127.0.0.1 |
| 8095+ | Ephemeral | Outbound | Dynamic |

**Default bind**: `127.0.0.1` (loopback only). **Do not bind `0.0.0.0`** without fixing auth bypass (C-1).