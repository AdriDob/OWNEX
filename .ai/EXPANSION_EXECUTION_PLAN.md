# Expansion Execution Plan — Ecosistema ORION 360

> **Objetivo**: Convertir ORION en un ecosistema completo de inteligencia operativa que cubra bug bounty, trading, prediction markets, on-chain analysis, Argentina finance, sports betting, AI bounty y revenue intelligence — con UX de lujo, priorizando revenue directo y autonomía.

---

## 1. REVENUE PROJECTIONS — Bug Bounty

### 1.1 Estimación conservadora (50% del potencial)

| Mes | Acumulado | Monthly | Fuente principal | Confianza |
|-----|-----------|---------|------------------|-----------|
| Mes 1-2 | $0 | $0 | Setup, onboarding, primeros scans | Setup |
| Mes 2-3 | $250 | $250 | AI Bounty programs (primer cobro público) | Baja |
| Mes 3-4 | $750 | $500 | First valid IDOR/XSS en web targets | Media |
| Mes 4-6 | $2,750 | $1,000 | Pipeline estable, findings consistentes | Media-Alta |
| Mes 6-9 | $8,750 | $2,000 | SSRF/SQLi/AuthBypass + automatización | Alta |
| Mes 9-12 | $23,750 | $5,000 | Full pipeline, acceptance optimization | Alta |
| Mes 12-18 | $65,000 | $7,000 | Reputación + programas privados | Muy Alta |

### 1.2 Estimación realista (80% del potencial)

| Mes | Acumulado | Monthly | Driver |
|-----|-----------|---------|--------|
| Mes 1-2 | $0 | $0 | Setup |
| Mes 2-3 | $500 | $500 | AI bounty triage + primeros reports |
| Mes 3-4 | $1,500 | $1,000 | Valid findings en targets mediano porte |
| Mes 4-6 | $7,500 | $3,000 | Pipeline E2E + auto-report |
| Mes 6-9 | $25,000 | $6,000 | Acceptance optimizer + quality gate |
| Mes 9-12 | $70,000 | $15,000 | Reputación + programas privados + bounties altos |
| Mes 12-18 | $200,000+ | $20,000+ | Full stack operational + hunting continuo |

### 1.3 Primer payout: timeline crítico

| Hito | Timeline | Dependencias | Riesgo |
|------|----------|-------------|--------|
| Setup + programas targets | Día 1-5 | Nada | Bajo |
| Primer scan real | Día 3-7 | Targets cargados | Bajo |
| Primer finding válido | Día 7-21 | Recon + Probe + Hypothesis | Medio |
| Primer report enviado | Día 21-45 | Validation + Quality Gate | Medio |
| Primer payout recibido | Día 45-90 | Tiempo de respuesta plataforma | Alto (depende de triage) |

### 1.4 Revenue Rule aplicada

Cada sprint se evalúa contra: ¿aumenta directamente mi probabilidad de cobrar o el monto del cobro?

| Clasificación | Definición |
|--------------|-----------|
| 🪙 **Direct Revenue** | Feature que, por sí sola, puede generar un bounty validable |
| ⚡ **Revenue Accelerator** | Feature que duplica o triplica velocidad de encontrar/cobrar |
| 📈 **Revenue Multiplier** | Feature que aumenta probabilidad de aceptación |
| 🔧 **Revenue Enabler** | Feature que hace posible lo que antes no era |
| 🧠 **Revenue Intelligence** | Feature que mejora decisiones de qué/vale la pena atacar |
| 🎯 **Indirect** | Feature que mejora calidad de vida pero no impacta revenue directamente |

---

## 2. SPRINT ORDERING — Fastest to Most Complex

Priorización por velocidad de implementación + revenue impact. Tiempos estimados para un desarrollador senior.

### 2.1 Sprints Inmediatos (Día 1-7) — Revenue Accelerators

| Sprint | Herramientas | Tiempo | Revenue Impact | Complexity |
|--------|-------------|--------|---------------|---------|
| **S-1** | Dalfox, ffuf, sqlmap (✅ ya existen) | Ya integradas | ⚡ Accel | 0 |
| **S-2** | Gitleaks (✅ ya implementado) | Ya integrado | 🪙 Direct | 1 |
| **S-3** | Browser Use + Garak (✅ ya implementados) | Ya integrados | 🪙 Direct | 2 |
| **S-4** | 🤖 **AI Bounty Auto-Hunter**: Script que monitorea plataformas AI Bounty (Imbue, Anthropic, OpenAI, etc.), descarga retos, ejecuta scans, envía reports automatizados | 4-6 horas | 🪙 Direct (pago rápido) | 2 |
| **S-5** | 📊 **Revenue Dashboard V2**: Vista en frontend que muestra targets rankeados por EV(USD/hora), probabilidad de aceptación, findings activos, reports enviados/pendientes/accepted | 3-4 horas | 📈 Multiplier | 2 |
| **S-6** | 🔄 **Auto-Submission Pipeline**: Cuando un finding pasa Quality Gate (>0.75), genera report, lo envía a plataforma, trackea estado | 4-6 horas | ⚡ Accel | 3 |

### 2.2 Sprints Cortos (Día 3-14) — Revenue Multipliers

| Sprint | Herramientas | Tiempo | Revenue Impact | Complexity |
|--------|-------------|--------|---------------|---------|
| **S-7** | 🔍 **Target Discovery Automator**: scraping de programas públicos + ranking por payout promedio + detección de programas nuevos | 3-5 horas | ⚡ Accel | 2 |
| **S-8** | 📝 **Report Optimizer V2**: template engine con variables dinámicas, auto-CVSS, auto-CWE, auto-remediation | 4-6 horas | 📈 Multiplier | 3 |
| **S-9** | 🧪 **Auto-Recon Enhancement**: Naabu→HTTPx→Katana→Nuclei pipeline completo con auto-dedup | 3-5 horas | ⚡ Accel | 2 |
| **S-10** | ✅ **Verdict Auto-Learner**: FeedbackTuner conectado a AcceptanceLearner para ajustar pesos automáticamente | 4-6 horas | 🧠 Intel | 3 |
| **S-11** | ⚔️ **Auto-Bypass Engine**: Baipaseo automático de WAF, rate limits, autenticación | 5-8 horas | 🪙 Direct | 4 |

### 2.3 Sprints Medios (Día 7-21) — Direct Revenue

| Sprint | Herramientas | Tiempo | Revenue Impact | Complexity |
|--------|-------------|--------|---------------|---------|
| **S-12** | 🏛️ **On-Chain Intelligence Sprint**: Etherscan + Dune + Nansen data → leads de exploits → targets priorizados | 8-12 horas | 🪙 Direct | 5 |
| **S-13** | 🤖 **Prediction Markets AI Sprint**: Polymarket adapter (✅ existe) + auto-trader basado en LLM analysis | 6-10 horas | 🪙 Direct | 4 |
| **S-14** | 📈 **Crypto Trading Signals Sprint**: CoinGecko → technical indicators → buy/sell signals → auto-orders | 8-12 horas | 🪙 Direct | 5 |
| **S-15** | 💵 **Argentina Finance Sprint**: DolarAPI + BCRA + MEP/CCL arbitrage + UVA alerts + crypto P2P | 6-10 horas | 🪙 Direct | 4 |
| **S-16** | 🏈 **Sports Betting AI Sprint**: TheOddsAPI + ML predictions + Kelly Criterion + auto-bets | 10-15 horas | 🪙 Direct | 6 |

### 2.4 Sprints Largos (Día 14-30) — High Complexity

| Sprint | Herramientas | Tiempo | Revenue Impact | Complexity |
|--------|-------------|--------|---------------|---------|
| **S-17** | 🕵️ **DeFi Protocol Inspector**: Scanner automático de smart contracts (Mythril/Slither) + economic exploit detection | 12-18 horas | 🪙 Direct | 7 |
| **S-18** | 🤝 **Cross-Chain Arbitrage Engine**: Bridge monitoring + price diffs + auto-swap execution | 15-20 horas | 🪙 Direct | 8 |
| **S-19** | 🎰 **Multi-Exchange Arbitrage Bot**: Triangular + cross-exchange + funding rate arb ejecutable | 15-25 horas | 🪙 Direct | 9 |
| **S-20** | 💰 **Prediction Market Market Making**: Automated liquidity provision + hedging en Polymarket | 12-18 horas | 🪙 Direct | 7 |
| **S-21** | 🧠 **Full AI Bounty Pipeline**: End-to-end: monitor → classify → solve → submit → track → learn | 12-16 horas | 🪙 Direct | 7 |

### 2.5 Sprints de Infraestructura UX (Paralelo)

Estos sprints corren en paralelo con los demás y no bloquean revenue.

| Sprint | Herramientas | Tiempo | Complexity |
|--------|-------------|--------|---------|
| **UX-1** | 🧒 **Baby Mode**: Dashboard simplificado con 3 botones grandes: "¿Qué hago ahora?", "Ver mi dinero", "Probar suerte" | 3-4 horas | 1 |
| **UX-2** | 📊 **Analyst Mode**: Tablas, gráficos, filtros, export CSV, comparativas, heatmaps | 4-6 horas | 2 |
| **UX-3** | 🔔 **Smart Notifications**: Alertas contextuales con probabilidad de éxito + botón "Ejecutar" | 3-5 horas | 3 |
| **UX-4** | 📱 **Mobile Companion V2**: Refactor de UI existente con modo streaming de resultados | 5-8 horas | 4 |
| **UX-5** | 🎯 **"Just F*cking Do It" Button**: Un botón que ejecuta el flujo completo desde target hasta payout | 8-12 horas | 6 |

### 2.6 Dependencies Map

```
S-4 (AI Bounty Auto-Hunter) → S-21 (Full AI Bounty Pipeline)
S-6 (Auto-Submission) → S-8 (Report Optimizer V2) → S-10 (Verdict Auto-Learner)
S-9 (Auto-Recon) → S-11 (Auto-Bypass Engine)
S-12 (On-Chain) → S-17 (DeFi Protocol) → S-18 (Cross-Chain)
S-13 (Prediction Markets AI) → S-20 (Prediction Market MM)
S-14 (Crypto Trading) → S-19 (Multi-Exchange Arb)
S-16 (Sports Betting) → standalone

UX sprints: independientes, cualquier orden
```

---

## 3. FIRST PAYOUT — Timeline + Estrategia

### 3.1 Ruta más rápida al primer cobro: AI Bounty

Los AI Bounty programs son los más rápidos para cobrar:
- **Imbue**: $10k-50k por vulnerabilidades en agentes autónomos
- **Anthropic**: Red teaming de safety measures
- **OpenAI**: Bug bounty tradicional + red team
- **Google AI**: Vulnerabilities en productos AI

**¿Por qué son más rápidos?**
- Menos competencia (pocos hunters especializados en AI security)
- Triage más rápido (equipos dedicados)
- Scope más definido (jailbreaks, prompt injection, data leakage, model manipulation)
- Pagos más rápidos (semanas vs meses)

**Estrategia**: Sprint 4 (AI Bounty Auto-Hunter) es la prioridad #1 después de los tools ya implementados.

### 3.2 Ruta segura: Web tradicional

- HackerOne + Bugcrowd + Intigriti
- Targets medianos con programas públicos
- Vulnerabilidades clásicas: IDOR, XSS, SSRF, SQLi, Auth Bypass
- Timeline: 45-90 días para primer cobro

### 3.3 Estrategia híbrida recomendada

| Semana | Acción | Revenue esperado |
|--------|--------|------------------|
| 1-2 | Setup + Recon en 50 targets + AI Bounty triage | $0 |
| 2-3 | Reportes en AI programs + primeros findings web | $0-$500 |
| 3-4 | 5-10 reports enviados (mix AI + web) | $500-$1,000 |
| 4-8 | Escalar a 200+ targets, auto-submission, optimizar acceptance | $1k-$3k |
| 8-12 | Revenue pipeline maduro, 3+ payouts/mes | $3k-$6k |
| 12+ | Invitación a programas privados por reputación | $6k-$20k |

---

## 4. FIFTEEN ADDITIONAL ECOSYSTEM TOOLS

Investigación de herramientas que complementan el ecosistema ORION fuera del scope original (no duplican existentes).

### 4.1 Portfolio & Wealth Tracking

| Tool | Descripción | ¿Por qué ahora? | Tipo |
|------|-------------|-----------------|------|
| **Rotki** | Open-source portfolio tracker con blockchain data, tax reporting, DeFi positions | ORION tiene Financial Dashboard pero sin soporte multi-chain completo ni tax reporting | 🧠 Intel |
| **Ghostfolio** | Self-hosted portfolio management con analytics, benchmarks, alerts | Dashboard financiero web con API REST, fácil integración con ORION backend | 🧠 Intel |
| **Tiller** | Google Sheets connected financial tracker, auto-categorización | Complementa revenue tracking con categorización granular de ingresos/gastos | 🎯 Indirect |

### 4.2 Exchange & Market Monitoring

| Tool | Descripción | ¿Por qué ahora? | Tipo |
|------|-------------|-----------------|------|
| **Cryptomon** | Multi-exchange monitoring dashboard, real-time prices, P&L tracking | ORION tiene CCXT pero no dashboard visual de monitoreo multi-exchange en tiempo real | 🧠 Intel |
| **CoinTracker** | Portfolio + tax tracking, 300+ exchanges, auto-sync | Tax reporting + portfolio visibility para Argentina compliance | 🧠 Intel |
| **3Commas** | Smart trading bots, DCA, Grid trading, auto-rebalancing | Trading automation lista para usar, complementa estrategias propias ORION | 🪙 Direct |

### 4.3 Security Infrastructure

| Tool | Descripción | ¿Por qué ahora? | Tipo |
|------|-------------|-----------------|------|
| **Wazuh** | Open-source SIEM, file integrity monitoring, vulnerability detection | Seguridad del propio ORION + capacidad de ofrecer SIEM como servicio | 🔧 Enabler |
| **SecurityTrails** | DNS history, WHOIS, subdomain discovery API | Enriquecimiento de recon para bug bounty con datos históricos | ⚡ Accel |
| **Dehashed** | Breached credentials search, dark web intel | OSINT para correlates vulnerabilidades con credenciales filtradas | 🪙 Direct |

### 4.4 AI & Automation

| Tool | Descripción | ¿Por qué ahora? | Tipo |
|------|-------------|-----------------|------|
| **AutoGPT** / **LangChain Agents** | Autonomous agent framework for multi-step task execution | Potencial para orquestar flujos completos ORION con LLM autónomo | 🔧 Enabler |
| **CrewAI** | Multi-agent orchestration framework | ORION ya tiene COPILOT, pero CrewAI permite equipos de agentes colaborando | 🧠 Intel |
| **Hugging Face Model Hub** | 50k+ modelos open-source, datasets, spaces | Fine-tuning de modelos para detección de vulnerabilidades específicas | 🔧 Enabler |

### 4.5 Intelligence & Analytics

| Tool | Descripción | ¿Por qué ahora? | Tipo |
|------|-------------|-----------------|------|
| **Maltego** | Link analysis, entity graphing, OSINT transforms | ORION tiene Knowledge Graph, Maltego agrega visualización link analysis profesional | 🧠 Intel |
| **Shodan** (✅ ya integrado) | Internet device search, service enumeration | ✅ Ya existe en `cores/tools/shodan.py` | ⚡ Accel |
| **Censys** | Internet asset discovery, certificate transparency | Complementa Shodan con datos de certificados, SSL, servicios cloud | ⚡ Accel |

### 4.6 Not Prioritized (Rechazadas con evidencia)

| Tool | Razón |
|------|-------|
| **Ledger Live** | Desktop-only, no tiene API para integración programática |
| **Koinly** | Solo crypto tax, no aporta nada que CoinTracker no tenga + es pago |
| **CoinMarketCap** | API ya disponible vía CoinGecko (redundante) |
| **TradingView** | Widgets embebibles pero no reemplazan análisis propio |
| **Dune Analytics** | Excelente pero requiere SQL + análisis manual, ORION necesita automation |

---

## 5. LUXURY UX VISION — ORION 360

### 5.1 Filosofía de diseño

```
                        ORION 360
              ┌─────────────────────────┐
              │   🧒   👨‍💻   🎯         │
              │ Baby   Analyst   DO IT  │
              │ Mode    Mode    Button  │
              └─────────────────────────┘
```

Tres modos, un solo sistema. Sin config, sin learning curve. Abrís ORION y elegís cómo querés operar hoy.

### 5.2 Baby Mode — "¿Qué hago ahora?"

```python
# UX: Pantalla única, 3 botones grandes

┌─────────────────────────────────────────┐
│  🔭 ORION — Baby Mode                    │
│  "¿Qué hago ahora para ganar plata?"     │
├─────────────────────────────────────────┤
│                                           │
│  ┌─────────────────────┐  ┌──────────────┐│
│  │  🎯                  │  │  💰           ││
│  │  LO MEJOR PARA HOY   │  │  MI DINERO    ││
│  │  Target rankeado por  │  │  Portfolio +  ││
│  │  USD/hora esperado    │  │  Revenue YTD  ││
│  └─────────────────────┘  └──────────────┘│
│                                           │
│  ┌─────────────────────────────────────┐ │
│  │  🤖                                  │ │
│  │  PROBAR SUERTE (Auto-Pilot)          │ │
│  │  ORION decide, ejecuta, reporta      │ │
│  └─────────────────────────────────────┘ │
│                                           │
│  Última acción: Scan en hackerone.com    │
│  → 14 endpoints → 3 vulnerabilidades     │
│  → 1 lista para reporte. ¿Enviar? [Sí]  │
├─────────────────────────────────────────┤
│  Switch to: [Analyst Mode] [DO IT Mode]  │
└─────────────────────────────────────────┘
```

- **Target rankeado por USD/hora**: no por severity, no por CVSS. Por dinero real esperado.
- **Auto-Pilot**: ORION decide target, ejecuta scan, valida findings, genera report, pide aprobación, envía.
- **Última acción**: contexto inmediato. ORION nunca te deja preguntándote "¿qué pasó?".

### 5.3 Analyst Mode — "Muéstrame todos los datos"

```python
# UX: Tablero de control completo con secciones colapsables

┌──────────────────────────────────────────────┐
│ 📊 ORION — Analyst Mode                       │
├──────────────────────────────────────────────┤
│                                               │
│ 📈 REVENUE                                   │
│ ┌─────────────────────────────────────────┐  │
│ │ $4,250 This Month    ↑23% vs last month │  │
│ │ Targets: 142  Active: 38  Findings: 312  │  │
│ │ Acceptance Rate: 67%  Avg Payout: $850   │  │
│ └─────────────────────────────────────────┘  │
│                                               │
│ 🎯 TARGETS RANKED BY EV (USD/hora)           │
│ ┌──────┬──────────────┬──────┬──────┬──────┐ │
│ │ Rank │ Target       │ EV   │ Prob │ Est.$│ │
│ ├──────┼──────────────┼──────┼──────┼──────┤ │
│ │ #1   │ reddit.com   │$142/h│ 78%  │ $3,500│ │
│ │ #2   │ shopify.com  │ $98/h│ 65%  │ $2,100│ │
│ │ #3   │ hackerone.com│ $87/h│ 71%  │ $1,800│ │
│ └──────┴──────────────┴──────┴──────┴──────┘ │
│                                               │
│ 🔬 FINDINGS PIPELINE                          │
│ ┌──────────┬──────┬──────┬──────┬─────────┐ │
│ │ Status   │ IDOR │ XSS  │ SSRF │ Total   │ │
│ ├──────────┼──────┼──────┼──────┼─────────┤ │
│ │ Discover │ 12   │ 8    │ 3    │ 23      │ │
│ │ Validate │ 5    │ 3    │ 1    │ 9       │ │
│ │ Report   │ 2    │ 0    │ 0    │ 2       │ │
│ │ Accepted │ 1    │ 0    │ 0    │ 1       │ │
│ ├──────────┼──────┼──────┼──────┼─────────┤ │
│ │ Revenue  │$2,500│ $0   │ $0   │ $2,500  │ │
│ └──────────┴──────┴──────┴──────┴─────────┘ │
│                                               │
│ 🧠 ORION INTELLIGENCE                         │
│ ┌─────────────────────────────────────────┐  │
│ │ "IDOR tiene mejor ROI histórico en      │  │
│ │  tu stack (68% acceptance, $1.2k avg).  │  │
│ │  Reddit.com tiene 12 endpoints IDOR     │  │
│ │  sin validar. ¿Empiezo?" [Sí]           │  │
│ └─────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

- **Revenue primero**: todo tablero empieza con cuánta plata se generó y cómo va el mes.
- **Pipelines de findings**: números fríos. Cuántos discoveries, cuántos validados, cuántos reportados, cuántos aceptados.
- **ORION Intelligence**: la IA te dice qué hacer con datos concretos. No "tenés 12 findings", sino "IDOR paga más, reddit tiene 12 sin validar, ¿empiezo?".

### 5.4 DO IT Mode — "Just F*cking Do It"

```python
# UX: Un botón. Nada más.

┌──────────────────────────────────────────────┐
│ 🎯 ORION — DO IT Mode                        │
├──────────────────────────────────────────────┤
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │                                         │  │
│  │          ▶  DO IT  ◀                    │  │
│  │                                         │  │
│  │  "ORION decides target, executes full   │  │
│  │   pipeline, validates, reports, submits,│  │
│  │   and tracks until payout."             │  │
│  │                                         │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  Status: ⚡ Running                           │
│  Target: reddit.com (EV: $142/h)              │
│  Phase: RECON → 342 endpoints found           │
│  Last: 3 IDOR potential.                      │
│  Next: Validating...                          │
│                                               │
│  [Cancel] [Pause] [View Details]             │
│                                               │
└──────────────────────────────────────────────┘
```

- **Un solo botón**: ORION decide qué target tiene mejor EV, ejecuta pipeline completo, valida, genera report, pide aprobación, envía, trackea hasta payout.
- **Live status**: siempre sabés en qué fase está sin tener que abrir 3 pantallas distintas.
- **Cancel/Pause**: control humano siempre presente.

### 5.5 Shared UX Components (Todos los modos)

| Componente | Descripción |
|-----------|-------------|
| **Smart Notification Bar** | Alertas contextuales con probabilidad de éxito + botón ejecutar |
| **Revenue Counter** | Siempre visible: $"Este mes: $4,250 ↑23%" |
| **Quick Action FAB** | Botón flotante: "¿Qué hago ahora?" desde cualquier pantalla |
| **Dark Mode Premium** | Tema oscuro profesional, gráficos con glow, animaciones suaves |
| **Voice Commands** | "ORION, scan reddit.com", "ORION, show my revenue" |
| **Streaming Results** | Resultados aparecen en vivo mientras se ejecutan, no después |

### 5.6 MVP UX: Prioridad de implementación

| Feature | Tiempo | Impacto | Sprint |
|---------|--------|---------|--------|
| Revenue Dashboard V2 (Analyst Mode core) | 3-4h | 📈 Alto | S-5 |
| Baby Mode — 3 botones + "¿Qué hago hoy?" | 2-3h | 🧒 Alto | UX-1 |
| Smart Notification Bar | 2-3h | 🔔 Medio | UX-3 |
| "DO IT" Button MVP | 3-4h | 🎯 Alto | UX-5 |
| Analyst Mode completo (gráficos, filtros) | 4-6h | 📊 Alto | UX-2 |

---

## 6. CONSOLIDATED ROADMAP

### Sprint 0 — Ya implementado (Día 0)
- ✅ Dalfox, ffuf, sqlmap (existían)
- ✅ Gitleaks, Garak, Browser Use (24 tests, 0 fallos)
- ✅ CensysTool — REST tool en TOOL_REGISTRY (2026-07-24)
- ✅ Crypto Technical Analysis — RSI/SMA/MACD desde CoinGecko (2026-07-24)
- ✅ Smart Notifications — bridge 14 eventos EventBus + 3 endpoints (2026-07-24)
- ✅ Revenue Intelligence — USD/h dinámico + platform speed (2026-07-24)
- ✅ FCC Proxy + Hermes provider stable
- ✅ 200+ herramientas evaluadas (TECHNOLOGY_SCOUT_REPORT.md)
- ✅ 50 herramientas evaluadas (EXPANSION_INTELLIGENCE_REPORT.md)
- ✅ Revenue projections, timeline, sprint ordering, 15 tools, UX vision (este documento)

### Week 1 — Revenue First ✅ (Completado)
| Sprint | Feature | Hours | Estado |
|--------|---------|-------|--------|
| S-4 | AI Bounty Auto-Hunter | 5h | ✅ |
| S-5 | Revenue Dashboard V2 | 4h | ✅ |
| UX-1 | Baby Mode | 3h | ✅ |
| S-7 | Target Discovery Automator | 4h | ✅ |

### Week 2 — Pipeline Optimization ✅ (Completado)
| Sprint | Feature | Hours | Estado |
|--------|---------|-------|--------|
| S-6 | Auto-Submission Pipeline | 5h | ✅ |
| S-8 | Report Optimizer V2 | 5h | ✅ |
| S-9 | Auto-Recon Enhancement | 4h | ✅ |
| UX-2 | Analyst Mode | 5h | ✅ |

### Week 3 — Intelligence Layer (En progreso)
| Sprint | Feature | Hours | Estado |
|--------|---------|-------|--------|
| S-10 | Verdict Auto-Learner | 5h | ✅ |
| UX-3 | Smart Notifications | 4h | ✅ (2026-07-24) |
| S-13 | Prediction Markets AI | 8h | ⏸ Pendiente |
| S-15 | Argentina Finance | 8h | ⏸ Pendiente |

### Week 4 — Direct Revenue (Pendiente)
| Sprint | Feature | Hours | Estado |
|--------|---------|-------|--------|
| S-11 | Auto-Bypass Engine | 7h | ⏸ Pendiente |
| S-14 | Crypto Trading Signals (TA) | 10h | ✅ TA done, auto-ordenes pendiente |
| S-16 | Sports Betting AI | 12h | ⏸ Pendiente |

### Week 5+ — Advanced (Pendiente)
| Sprint | Feature | Hours | Estado |
|--------|---------|-------|--------|
| S-12 | On-Chain Intelligence | 10h | ⏸ Pendiente |
| S-17 | DeFi Protocol Inspector | 15h | ⏸ Pendiente |
| S-18 | Cross-Chain Arbitrage | 18h | ⏸ Pendiente |
| S-19 | Multi-Exchange Arb Bot | 20h | ⏸ Pendiente |
| S-20 | Prediction Market MM | 15h | ⏸ Pendiente |
| S-21 | Full AI Bounty Pipeline | 14h | ⏸ Pendiente |
| UX-5 | "DO IT" Button | 10h | ⏸ Pendiente |

---

## 7. REVENUE RULE — MÉTRICAS DE ÉXITO

Cada sprint se evaluará contra:

| Métrica | Cómo se mide | Target |
|---------|-------------|--------|
| **First Payout** | Días desde Sprint 0 hasta primer bounty cobrado | < 60 días |
| **Monthly Revenue** | USD/mes de bounties aceptados | $500/mes (mes 3), $2k/mes (mes 6) |
| **Acceptance Rate** | % de reports enviados que son aceptados | > 50% |
| **Findings-to-Payout** | Promedio de findings por payout | < 20 findings/payout |
| **Time-to-Report** | Desde finding hasta report enviado | < 1 hora (auto) |
| **Time-to-Payout** | Desde report enviado hasta dinero en cuenta | < 45 días |

---

## 8. EXECUTION RULES

1. **Baby Mode first**: toda feature nueva debe tener su versión Baby Mode antes de ser considerada "completa".
2. **Revenue Rule**: no implementar nada que no aumente dinero, tiempo libre, reduzca trabajo o mejore decisiones.
3. **One sprint at a time**: no empezar Sprint N+1 hasta que Sprint N esté 100% operativo (tests, docs, UX).
4. **UX parallels**: UX sprints corren en paralelo, no bloquean revenue sprints.
5. **First payout is priority zero**: si algo no acerca el primer payout, baja prioridad.
6. **Test coverage**: cada sprint debe tener tests que prueben el flujo real, no solo la función aislada.
