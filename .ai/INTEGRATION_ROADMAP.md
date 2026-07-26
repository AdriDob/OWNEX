# Integration Roadmap

> Sequencing of all external integrations by ROI.
> Every integration must pass the 20% improvement test.

---

## P0 — Already done

| Integration | Status |
|---|---|
| Nuclei | ✅ Active |
| Subfinder | ✅ Active |
| Katana | ✅ Active |
| Amass | ✅ Active |
| Naabu | ✅ Active |
| Shodan | ✅ Active |
| Uncover | ✅ Active |
| Ollama | ✅ Active |
| OpenRouter | ✅ Active |
| CoinGecko | ✅ Active |
| Takenos | ✅ Active |
| Discord webhook | ✅ Active |
| ARCA | ✅ Active |
| Outlook | ✅ Active |

---

## P1 — Revenue Ready (Next 3 weeks)

| # | Integration | Impact | Effort | Done |
|---|---|---|---|---|
| 1 | **httpx** — HTTP probe module | ⭐⭐⭐⭐⭐ | 3d | |
| 2 | **Playwright** — Screenshots + HAR for evidence | ⭐⭐⭐⭐ | 2d | |
| 3 | **Immunefi API** — Submission + payout sync | ⭐⭐⭐⭐⭐ | 2d | |
| 4 | **Code4rena API** — Contest submission + payout | ⭐⭐⭐⭐ | 2d | |

---

## P2 — Platform Hardening (Month 2)

| # | Integration | Impact | Effort |
|---|---|---|---|
| 5 | **CCXT** — Universal exchange tracking | ⭐⭐⭐ | 2-3d |
| 6 | **sqlmap** — SQLi validation | ⭐⭐⭐ | 2d |
| 7 | **FFUF** — Parameter/endpoint discovery | ⭐⭐⭐ | 1d |
| 8 | **DolarAPI** — Real-time ARS rates | ⭐⭐ | 1d |
| 9 | **Slack webhook** — Notifications | ⭐⭐ | 1d |

---

## P3 — AI & Learning (Month 2-3)

| # | Integration | Impact | Effort |
|---|---|---|---|
| 10 | **sentence-transformers** — Semantic memory | ⭐⭐⭐⭐ | 2-3d |
| 11 | **HuggingFace models** — Specialized vuln detection | ⭐⭐⭐ | 1-2d |

---

## P4 — Desktop Intelligence (Month 3)

| # | Integration | Impact | Effort |
|---|---|---|---|
| 12 | **Open Interpreter** — Code execution for Hermes | ⭐⭐ | 2-3d |
| 13 | **PyAutoGUI** — GUI automation for Hermes | ⭐⭐ | 1-2d |

---

## P5 — Expansion (Ongoing)

| # | Integration | Impact | Effort |
|---|---|---|---|
| 14 | Huntr API | ⭐⭐ | 1-2d |
| 15 | BugBase API | ⭐⭐ | 1-2d |
| 16 | YesWeHack API | ⭐⭐ | 1-2d |
| 17 | Synack API | ⭐⭐ | 1-2d |
| 18 | huntr.com API | ⭐⭐ | 1-2d |

---

## Timeline

```
Week 1-2:  httpx probe + Playwright evidence
Week 2-3:  Immunefi + Code4rena connectors
Week 3-4:  CCXT + sqlmap + FFUF
Week 4-6:  sentence-transformers
Week 6-8:  Hermes integrations
Week 8+:   Platform expansion
```
