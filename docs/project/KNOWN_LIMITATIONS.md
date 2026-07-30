# KNOWN LIMITATIONS — OWNEX OMEGA v7.0

**Honest assessment of what the system CANNOT do today. Updated per session from code evidence.**

---

## Product Limitations (Revenue-Impacting)

| Limitation | Impact | Workaround | Fix ETA |
|------------|--------|------------|---------|
| **Security Cycle not auto-bootstrapped** | No autonomous offensive cycles on startup | Manual API call to `/api/security/cycle/start` | Sprint 1 |
| **GamingConsole shows fake activity** | Dashboard credibility zero | None — hardcoded array | Sprint 1 |
| **AgentFleet shows static agents** | No real agent health visibility | Fallback to Hermes/OpenCode/Cline/Ollama/FCC | Sprint 1 |
| **Desktop installer never built** | Cannot distribute to Windows | Run in WSL only | Sprint 2 |
| **No `/api/activity` endpoint** | GamingConsole & real-time feeds broken | Poll `/api/system/state/events` (exists?) | Sprint 1 |
| **Forge Cycle (Dev Bounties) does not exist** | Missing dev bounty revenue stream | None — not built | Sprint 4 |
| **Pulse Cycle (AI Work) does not exist** | Missing AI work revenue stream | None — not built | Sprint 5 |
| **Multi-Cycle Orchestrator does not exist** | Cycles can't share resources intelligently | None — not built | Sprint 6 |
| **12 OMEGA Agents not created** | No continuous observation/learning | 7 core agents only | Sprint 6 |
| **Continuous Sensors not implemented** | No 24/7 domain monitoring | Scheduler only (interval-based) | Sprint 6 |
| **Self-Repair System not implemented** | Manual intervention for infra failures | Human monitoring | Sprint 7 |
| **Post-Cycle Learning not implemented** | No automatic improvement from results | Manual analysis | Sprint 7 |
| **Mobile Companion not built** | Cannot monitor from phone/watch | Web dashboard only | Sprint 7 |

---

## Infrastructure Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **Single-process EventBus** | No horizontal scaling, no HA | Run single instance; Redis pub/sub not implemented |
| **In-process Scheduler** | If API restarts, pipeline stops | Systemd restart; no distributed lock |
| **SQLite only (dev)** | No concurrent writers, no production scale | PostgreSQL config exists, not tested |
| **No distributed tracing** | Cross-service debugging hard | Structured logs + EventBus events |
| **No secrets rotation** | Long-lived credentials risk | AES-256-GCM vault, but no auto-rotation |
| **Python 3.14.4 in dev** | Pre-release, unstable | Pin 3.11/3.12 for production |

---

## Frontend Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **Tailwind v4 scoped styles** | `@apply` with opacity fails | Use plain CSS instead |
| **Vue SFC single `<script setup>`** | Second script must be `<script>` | Known, documented |
| **No E2E tests** | Regression risk on UI | Manual verification only |
| **WebSocket CSRF bypass needed** | Terminal sidecar blocked | Middleware early return for WS |

---

## Agent/Automation Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **7 agents, no coordination protocol** | Potential conflicts on same target | Per-target cooldown (1hr) |
| **COPILOT recommendations not auto-executed** | Human-in-the-loop for all decisions | By design — safety |
| **No agent failure recovery** | Stuck agent = stuck pipeline | Watchdog not implemented |
| **Hypothesis generator: 7 types only** | Misses novel vuln classes | Path-based fallback catches some |
| **OMEGA 12 agents not created** | No continuous observation/learning | Not yet built |

---

## Data/Intelligence Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **RewardLearner: needs 50+ payouts for signal** | Early programs have weak adjustments | Bootstrap with public HackerOne data |
| **No CVE database integration** | Can't match findings to known CVEs | Manual CVE lookup |
| **No exploit development framework** | PoC generation limited to templates | EvidenceComposer templates only |
| **Target discovery: 5 platforms only** | Misses private/regional programs | BountyScraper extensible |

---

## Extension/Evolution Limitations (Deferred)

| Limitation | Why Not Fixed | When It Matters |
|------------|---------------|-----------------|
| **13 extensions not in cycles** | Revenue Rule gate | Specific capability needed |
| **Evolution engine 9 stubs** | Infrastructure only | Production self-healing need |
| **No plugin marketplace** | Not a platform product | Never — private asset |

---

## Security Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| **No auth on API endpoints** | Local network exposure | Run on trusted network only |
| **No rate limiting** | DoS possible | Reverse proxy (nginx) |
| **Audit log: file only** | No tamper-proofing | Rotation + backup |
| **Secrets: env fallback** | Leaks in .env | Vault primary, env dev only |

---

## What We Explicitly DON'T Do (By Design)

| Not Done | Reason |
|----------|--------|
| Multi-tenant SaaS | Private asset — "OWNEX trabaja para mí" |
| Public bug bounty platform | Competes with H1/BC/Intigriti |
| Mobile app (yet) | ORION Companion separate vision |
| Crypto trading bot | Separate revenue stream |
| Investment bot | Separate revenue stream |
| Sports betting bot | Separate revenue stream |
| Dropshipping store | Not software/automation |
| General-purpose AI assistant | Focused on bug bounty automation |

---

## Limitation → Fix Mapping (For Planning)

| Limitation | Fix Task | Sprint |
|------------|----------|--------|
| Security Cycle not auto | Scheduler bootstrap job | 1 |
| GamingConsole fake | `/api/activity` endpoint + Vue fix | 1 |
| AgentFleet static | Real agent status in `/api/system/state` | 1 |
| Desktop not built | `npm run tauri build` + PyInstaller | 2 |
| No HA | Redis EventBus + distributed scheduler | Post-v7.0 |
| No PostgreSQL | Test prod config + migrate | Post-v7.0 |
| No E2E tests | Playwright + Vitest coverage | 3 |
| No auth | JWT + role-based API | When exposed externally |
| Forge Cycle missing | Algora/Opire/Superteam adapters + CoderAgent | 4 |
| Pulse Cycle missing | Outlier/Mindrift/DataAnnotation adapters + BrowserAgent | 5 |
| Multi-Cycle Orchestrator | Cross-cycle resource allocation | 6 |
| OMEGA 12 Agents | Observer, Researcher, Planner, Architect, Developer, Reviewer, Validator, Documentation, Repair, Infrastructure, Learning, Evolution | 6 |
| Continuous Sensors | Per-domain sensor framework | 6 |
| Self-Repair System | Auto-diagnose, repair, validate, log | 7 |
| Post-Cycle Learning | Results vs objectives, update knowledge | 7 |
| Mobile Companion | Android app + Wear OS | 7 |