# Integration Research — Micro Integraciones para Rastro

> Investigación realizada el 22-Jul-2026. Cada integración evaluada contra la Revenue Rule:
> ¿aumenta detección de vulns, calidad de evidencia, probabilidad de aceptación, o aprendizaje?

## Evaluación

| Impacto | Score | Significa |
|---------|-------|----------|
| 🔴 Detección | 1-10 | Encuentra más vulnerabilidades |
| 📊 Evidencia | 1-10 | Mejora calidad del reporte |
| ✅ Aceptación | 1-10 | Mayor chance de bounty |
| 🧠 Aprendizaje | 1-10 | El sistema mejora con uso |

---

## 1. Bug Bounty Platforms

### HackerOne API
- **Tier**: Gratis (hacker)
- **Auth**: Basic Auth (API token)
- **Rate Limit**: 50 req/min
- **Docs**: api.hackerone.com
- **Endpoints clave**: reports, programs, bounties, hacktivity, structured_scopes
- **Evaluación**:
  - 🔴 Detección: 8 — structured_scopes te da el scope exacto, hacktivity muestra qué están aceptando
  - 📊 Evidencia: 0
  - ✅ Aceptación: 9 — ver reportes aceptados/rechazados → entrenar AcceptanceLearner
  - 🧠 Aprendizaje: 9 — historial de bounty amounts + severities + vulnerabilidades aceptadas
- ** esfuerzo**: Bajo (~150 líneas, connector REST)
- **Prioridad**: ⭐⭐⭐⭐⭐

### Bugcrowd API
- **Tier**: Gratis
- **Auth**: Token-based
- **Rate Limit**: 60 req/min
- **Docs**: docs.bugcrowd.com/api
- **Endpoints clave**: programs, submissions, targets
- **Evaluación**:
  - 🔴 Detección: 7 — targets con scope, reward ranges
  - 📊 Evidencia: 0
  - ✅ Aceptación: 8 — ver submissions aceptados/rechazados
  - 🧠 Aprendizaje: 8
- **Esfuerzo**: Bajo
- **Prioridad**: ⭐⭐⭐⭐☆

### Intigriti API v2.0
- **Tier**: Clientes (OAuth 2.0)
- **Auth**: OAuth 2.0 con refresh tokens
- **Rate Limit**: 600 req/min read, 200 write
- **Docs**: kb.intigriti.com
- **Nota**: API v2.0 con 8 nuevos read endpoints + 11 write (severidad, bounty, GDPR)
- **Evaluación**: Similar a H1 pero requiere ser cliente. Prioridad media mientras no tengamos programa activo.
- **Prioridad**: ⭐⭐☆☆☆

### YesWeHack API
- **Tier**: Clientes
- **Nota**: No hay API pública documented para hackers. Baja prioridad.

---

## 2. OSINT / Recon APIs

### SecurityTrails API
- **Tier**: Paga (sin free tier significativo)
- **Endpoints**: DNS History, Subdomains, WHOIS, ASN, Associated Domains, SQL API
- **Evaluación**:
  - 🔴 Detección: 9 — DNS history + subdomains + WHOIS history = encontrar superficie oculta
  - 📊 Evidencia: 7 — WHOIS history como evidencia de propiedad
  - ✅ Aceptación: 0
  - 🧠 Aprendizaje: 2
- **esfuerzo**: Bajo
- **Prioridad**: ⭐⭐⭐⭐☆ (solo si tenemos presupuesto)

### Censys Platform API (v3)
- **Tier**: Free (host lookup, certs, web properties) / Starter paga
- **Auth**: Personal Access Token
- **Rate Limit**: 1 concurrent (free)
- **Endpoints**: hosts, certificates, web properties, search, collections
- **Evaluación**:
  - 🔴 Detección: 8 — host search + certificate transparency + service discovery
  - 📊 Evidencia: 6 — certificates como evidencia de servicio
  - ✅ Aceptación: 0
  - 🧠 Aprendizaje: 1
- **esfuerzo**: Bajo
- **Prioridad**: ⭐⭐⭐⭐☆

### Hunter.io API v2
- **Tier**: Free (25 req/mes) / Paga
- **Endpoints**: Domain Search, Email Finder, Email Verifier, Company Enrichment
- **Evaluación**:
  - 🔴 Detección: 6 — emails de empleados = phishing surface
  - 📊 Evidencia: 4
  - ✅ Aceptación: 0
  - 🧠 Aprendizaje: 1
- **Nota**: El rate limit free es muy bajo. Solo si actualizamos a plan pago.
- **Prioridad**: ⭐⭐⭐☆☆

### VirusTotal API
- **Tier**: Free (4 req/min) / Premium
- **Endpoints**: domain reputation, subdomains, IP reputation, URL scan
- **Evaluación**:
  - 🔴 Detección: 7 — subdomain enumeration + reputation + malware detección
  - 📊 Evidencia: 7 — domain/IP reputation para confirmar malicious
  - ✅ Aceptación: 4 — evidencia de que el dominio es malicioso
  - 🧠 Aprendizaje: 2
- **esfuerzo**: Bajo (wrapper simple REST)
- **Prioridad**: ⭐⭐⭐⭐☆

### DNSlytics API
- **Tier**: Free (2,500 req/día) / Premium paga
- **Endpoints**: Reverse IP, Reverse NS, Reverse MX, AS info, Hosting History, Reverse Adsense/GA
- **Evaluación**:
  - 🔴 Detección: 8 — Reverse Adsense/GA para encontrar dominios del mismo dueño
  - 📊 Evidencia: 6
  - ✅ Aceptación: 0
  - 🧠 Aprendizaje: 2
- **esfuerzo**: Bajo
- **Prioridad**: ⭐⭐⭐☆☆ (casos de uso específicos)

### WhoisXML API
- **Tier**: Free (500 queries)
- **Endpoints**: DNS Lookup (50 tipos), Reverse DNS, WHOIS, DNS History
- **Evaluación**: Similar a SecurityTrails pero con free tier más bajo.
- **Prioridad**: ⭐⭐☆☆☆

### osint-mcp-server
- **Tier**: Open source, 21 tools gratuitas sin API key
- **URL**: github.com/badchars/osint-mcp-server
- **Qué hace**: 37 tools across 12 sources en paralelo. DNS, WHOIS, crt.sh, GeoIP, BGP, Wayback, HackerTarget, M365
- **Evaluación**:
  - 🔴 Detección: 9 — 8 fuentes en paralelo en un solo comando
  - 📊 Evidencia: 7 — correlación entre fuentes
  - ✅ Aceptación: 0
  - 🧠 Aprendizaje: 2
- **esfuerzo**: Muy bajo — es un MCP server, solo configurar
- **Prioridad**: ⭐⭐⭐⭐⭐ — **implementar YA**

### theHarvester (API wrapper)
- **Tier**: Open source, 54+ fuentes
- **Nota**: Ya existe theHarvester como tool CLI. Podemos wrappear su output.
- **Prioridad**: ⭐⭐⭐☆☆ (duplicado funcional con osint-mcp-server)

---

## 3. AI Inference Providers

### OpenRouter (free tier)
- **Free**: 20+ modelos, 50 req/día (1,000 con $10 top-up)
- **OpenAI-compatible**: Sí
- **Evaluación**: Ya integrado vía FCC Proxy. Prioridad baja duplicar.
- **Prioridad**: ⭐⭐☆☆☆

### Groq API
- **Free**: Llama 3.3 70B, Mixtral, 1,000 req/día, ~320 t/s
- **OpenAI-compatible**: Sí
- **Evaluación**:
  - 🔴 Detección: 2 — no directamente
  - 🧠 Aprendizaje: 8 — inferencia ultrarrápida para análisis de endpoints
- **Prioridad**: ⭐⭐⭐☆☆ (alternativa a FCC Proxy cuando está caído)

### Google AI Studio (Gemini)
- **Free**: 1M context, multimodal, 20-1,500 req/día
- **OpenAI-compatible**: Parcial
- **Evaluación**: Útil para análisis de documentos largos (PDFs de bug bounty programs, terms)
- **Prioridad**: ⭐⭐☆☆☆

### RelayFreeLLM / FreeRideV3
- **Tier**: Open source — gateway multi-provider con failover automático
- **URLs**: github.com/msmarkgu/RelayFreeLLM, github.com/Shaivpidadi/FreeRideV3
- **Qué hace**: Unifica Gemini + Groq + Mistral + DeepSeek + NVIDIA + Cerebras + Ollama en un solo endpoint
- **Evaluación**:
  - 🔴 Detección: 0
  - 🧠 Aprendizaje: 9 — failover automático = nunca quedarse sin inferencia
- **Prioridad**: ⭐⭐⭐⭐☆ — complemento del AI Router

### Ollama (local)
- **Tier**: Gratis, infinito
- **Evaluación**: Ya integrado. Prioridad mantener actualizado.
- **Prioridad**: ⭐⭐☆☆☆

---

## 4. Vulnerability Databases

### OSV.dev API
- **Tier**: Gratis, sin API key
- **Rate Limit**: Sin límite documentado
- **Endpoints**: `/v1/query` (por package+version), `/v1/querybatch` (hasta 1,000), `/v1/vulns/{id}`
- **Ecosistemas**: npm, PyPI, Go, Rust, Maven, etc.
- **Evaluación**:
  - 🔴 Detección: 6 — conocer vulns en dependencias de targets
  - 📊 Evidencia: 3
  - ✅ Aceptación: 8 — citar CVE en reportes = más credibilidad
  - 🧠 Aprendizaje: 3
- **esfuerzo**: Muy bajo (~80 líneas)
- **Prioridad**: ⭐⭐⭐⭐☆

### NVD API v2.0
- **Tier**: Gratis (10 req/min sin key, 50 con key)
- **Endpoints**: CVEs, CVE History, CPE search
- **Evaluación**:
  - 🔴 Detección: 6
  - ✅ Aceptación: 9 — CVSS score oficial + CWE mapping
- **esfuerzo**: Bajo
- **Prioridad**: ⭐⭐⭐☆☆ (OSV cubre la mayoría de casos)

### CISA KEV
- **Tier**: Gratis
- **Formato**: JSON feed
- **Evaluación**: Saber qué vulns están siendo explotadas activamente
- **Prioridad**: ⭐⭐⭐☆☆

### Exploit-DB
- **Tier**: Gratis
- **Formato**: API pública (search)
- **Evaluación**: Buscar PoCs existentes para una vuln
- **Prioridad**: ⭐⭐☆☆☆

---

## 5. Notifications

### Telegram Bot API
- **Tier**: Gratis, sin límite de mensajes
- **Auth**: Bot token
- **Evaluación**: Canal de notificaciones ideal — mobile push, grupos, canales
- **esfuerzo**: Muy bajo (~100 líneas)
- **Prioridad**: ⭐⭐⭐⭐⭐ — **implementar YA**

### Ntfy.sh
- **Tier**: Gratis, sin signup, open source
- **Formato**: PUT/POST a `ntfy.sh/{topic}`
- **Evaluación**: Cero configuración, push a mobile/desktop
- **esfuerzo**: Mínimo (~30 líneas)
- **Prioridad**: ⭐⭐⭐⭐☆

### Pushover
- **Tier**: Gratis (10,000 msgs/mes)
- **Auth**: App token + user key
- **Evaluación**: Push a mobile con prioridades, sonidos, adjuntos
- **Prioridad**: ⭐⭐⭐☆☆

### Discord Webhook
- **Tier**: Gratis
- **Evaluación**: Ya existe integración. Prioridad baja.
- **Prioridad**: ⭐⭐☆☆☆

---

## 6. Crypto / Financial Data

### DefiLlama API
- **Tier**: Gratis, sin key, 31 endpoints
- **URL**: api.llama.fi
- **Endpoints**: protocols, TVL, chains, yields
- **Evaluación**: Útil para dashboard financiero de ORION
- **Prioridad**: ⭐⭐☆☆☆

### DexScreener API
- **Tier**: Gratis, sin key, 300 req/min
- **Evaluación**: Pair data en tiempo real para bots de trading
- **Prioridad**: ⭐⭐☆☆☆

### Mobula API
- **Tier**: Gratis con límites generosos
- **Evaluación**: Wallet portfolio, on-chain data, 90+ chains
- **Prioridad**: ⭐⭐⭐☆☆ (para el módulo financiero)

---

## 7. DNS / Infrastructure Tools

### osint-mcp-server (ya cubierto)
**Prioridad máxima.** Unifica 37 tools de OSINT en un MCP server. 21 tools funcionan sin API key. Correlación multi-fuente.

---

## Ranking Final de Prioridad

| # | Integración | Esfuerzo | Revenue Impact | Por qué |
|---|-------------|----------|----------------|---------|
| 1 | **osint-mcp-server** | Muy bajo | 🔴 9 / ✅ 7 | 37 tools, 12 fuentes, 21 sin key. Detección masiva |
| 2 | **Telegram Bot API** | Muy bajo | ✅ 6 / 🧠 4 | Notificaciones en tiempo real a mobile |
| 3 | **HackerOne API** | Bajo | 🔴 8 / ✅ 9 / 🧠 9 | Scope exacto, hacktivity, entrenar AcceptanceLearner |
| 4 | **Bugcrowd API** | Bajo | 🔴 7 / ✅ 8 / 🧠 8 | Targets + submissions para aprendizaje |
| 5 | **OSV.dev API** | Muy bajo | ✅ 8 | CVE references en reportes |
| 6 | **Censys API** | Bajo | 🔴 8 / 📊 6 | Host search + cert transparency |
| 7 | **VirusTotal API** | Bajo | 🔴 7 / 📊 7 | Reputation + subdomain enum |
| 8 | **RelayFreeLLM** | Medio | 🧠 9 | Failover multi-provider AI |
| 9 | **Ntfy.sh** | Mínimo | ✅ 4 | Notificaciones zero-config |
| 10 | **SecurityTrails API** | Bajo | 🔴 9 | Solo si hay presupuesto |

## Conclusión

**Top 3 a implementar inmediatamente:**
1. `osint-mcp-server` — MCP server, 37 tools, correlación multi-fuente. Detección massiva.
2. `Telegram Bot API` — Notificaciones en tiempo real a mobile/desktop.
3. `HackerOne API` — Hacktivity + structured_scopes para AcceptanceLearner.

**Próximo sprint:**
- OSV.dev API (CVE references)
- Censys API (certificate transparency + host search)
