# CATEYE Integration Guide

> Complete configuration reference for all external integrations.
> v4.1.0 STABLE — July 2026.

Every integration reads credentials from environment variables or the IdentityVault (AES-256-GCM encrypted store at `~/.orion/`). The Secrets Manager (`core/secrets/manager.py`) provides a REST API bridge with env var fallback.

---

## 1. AI Providers

### 1.1 OpenAI

**Purpose**: LLM-powered analysis, hypothesis generation, report drafting.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `OPENAI_API_KEY` | Yes | "" |
| `OPENAI_BASE_URL` | No | https://api.openai.com/v1 |

**Verification**:
```bash
curl http://localhost:8000/api/settings/all
# Look for openai_available in settings
```

**Implementation**: `cores/ai/provider.py:OpenAIProvider` — configurable base URL for proxy/compatible APIs.

**Common issues**: Missing API key causes fallback to Ollama or OpenRouter. Check logs for "OpenAI disabled — no API key".

### 1.2 OpenRouter

**Purpose**: Free tier LLM access (multiple models), fallback when OpenAI is unavailable.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | "" |

**Verification**: The ORION agent (`cores/ai/orion_agent.py`) tries OpenRouter free models when Gemini and Ollama are unavailable.

**Implementation**: Uses `https://openrouter.ai/api/v1/chat/completions` with Bearer token auth. Free models include: deepseek/deepseek-chat, google/gemini-flash-1.5, mistralai/mistral-7b-instruct, among others.

### 1.3 Gemini (Google)

**Purpose**: Alternative LLM provider for ORION agent reasoning.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `GEMINI_API_KEY` | Yes | "" |

**Verification**: ORION agent checks `GEMINI_API_KEY` at startup. If set, Gemini is preferred over OpenRouter.

**Implementation**: `cores/ai/provider.py:GeminiProvider` and direct HTTP calls in `cores/ai/orion_agent.py` using `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-001:generateContent`.

### 1.4 Anthropic (Claude)

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `ANTHROPIC_KEY` | Yes | "" |

Not directly implemented in current AI provider layer. Expected via OpenRouter free tier or future provider expansion.

### 1.5 Ollama (Local)

**Purpose**: Local LLM inference (privacy, offline operation).

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `OLLAMA_HOST` | No | http://localhost:11434 |
| `OLLAMA_MODEL` | No | freehuntx/qwen3-coder:8b |

**Verification**:
```bash
curl http://localhost:11434/api/tags
```

**Implementation**: `cores/ai/provider.py:OllamaProvider`. Used as fallback when cloud LLMs are unavailable. The ORION agent prioritizes Gemini > OpenRouter > Ollama.

---

## 2. Bug Bounty Platforms

Credentials for all platforms are configured via the IdentityVault or `CATEYEConfig` settings:

### 2.1 HackerOne

**Purpose**: Sync program scope, submitted reports, and payout data. HackerOne is the largest bug bounty platform and a primary source of validated findings and revenue for most hunters.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `HACKERONE_API_TOKEN` | Yes | "" |
| `HACKERONE_USERNAME` | Yes | "" |

The API token is generated from your HackerOne profile Settings > API Tokens. Ensure it has read access for programs, reports, and payouts.

**Verification**:
```bash
curl http://localhost:8000/api/system/definitions
# Returns "hackerone" in platforms list with color #00d46a

# Check if findings from HackerOne are appearing in the pipeline
curl http://localhost:8000/api/findings/stats
```

**Implementation**: Platform configuration in `cores/settings/service.py:DEFAULT_PLATFORM_CONFIG`. API auth via HTTP Basic using username + token. Payouts are reconciled via the financial truth layer.

**Common issues**: Token rotation — if the token was regenerated on HackerOne, update it in the vault. Ups tracking via `core/financial/bank_payout.py` which parses bank statement lines for "HACKERONE" or "HackerOne Inc" patterns.

### 2.2 Bugcrowd

**Purpose**: Sync program scope, submissions, and payout data. Bugcrowd is typically the second largest source of bounty revenue after HackerOne.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `BUGCROWD_API_TOKEN` | Yes | "" |

API tokens are generated from Bugcrowd Settings > API Keys. Need read and write scopes for full functionality.

**Verification**: Check the integrations status endpoint for a "green" or "yellow" status indicator.

**Implementation**: Configured in settings service, authenticated via API token in Authorization header. Sync via the financial scheduler (`cores/financial/scheduler.py`). Partial syncs (yellow status) typically indicate rate limiting or temporary API degradation.

**Common issues**: Bugcrowd enforces stricter rate limits than HackerOne. If consecutive failures increase, check that your token has not expired and that you are within rate limits.

### 2.2 Bugcrowd

**Purpose**: Sync program scope and submissions.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `BUGCROWD_API_TOKEN` | Yes | "" |

**Implementation**: Configured in settings service, authenticated via API token in Authorization header.

### 2.3 Intigriti

**Purpose**: European bounty platform with EUR payouts. Intigriti covers programs from European companies and offers competitive bounties.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| Intigriti API key (vault) | Yes | — |

**Implementation**: Settings service includes Intigriti in default platform configs. Uses OAuth2 client credentials flow. To configure, store your Intigriti API key in IdentityVault.

**Verification**: Intigriti payouts are detected by the bank payout reconciliation engine (`cores/financial/bank_payout.py`) via the regex pattern `INTIGRITI` in bank statement lines. Check integration status after configuring.

**Common issues**: Intigriti uses OAuth2 tokens that expire. Ensure your refresh flow is working. EUR payouts may appear as different amounts due to currency conversion in bank statements.

### 2.4 YesWeHack

**Purpose**: European bounty platform (EUR payouts). YesWeHack covers programs primarily from European companies with a focus on responsible disclosure.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| YesWeHack API key (vault) | Yes | — |

**Implementation**: Platform configured in settings service. API key stored in IdentityVault. The bank payout reconciliation engine (`cores/financial/bank_payout.py`) detects YesWeHack payouts via the `YESWEHACK` regex pattern.

**Verification**: After configuring, check the financial sync status and integration health. YesWeHack uses a REST API with token-based authentication.

**Common issues**: EUR-denominated payouts require manual currency tracking. The financial truth layer handles multiple currency conversions. Ensure your API key has read access for program scope and submission status.

### 2.5 Synack

**Purpose**: Invite-only bounty platform.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| Synack API key (vault) | Yes | — |

**Implementation**: Platform configured in settings service. Note: Synack has additional NDA/approval requirements.

---

## 3. Reconnaissance Tools

All OSINT clients are defined in `cores/recon/osint_api.py`. Each reads its API key from the named environment variable.

### 3.1 Shodan

**Purpose**: Service banners, open ports, vulnerability data.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `SHODAN_API_KEY` | Yes | "" |

**Verify**:
```bash
# Via OSINT API (requires API client)
curl http://localhost:8000/api/system/state
# Check if shodan is in available tools
```

**Implementation**: `ShodanClient` — queries `/shodan/host/{ip}`, `/shodan/host/search`, `/dns/resolve`.

### 3.2 Censys

**Purpose**: Internet asset discovery, certificate transparency.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `CENSYS_API_KEY` | Yes | "" |
| `CENSYS_API_SECRET` | Yes | "" |

**Implementation**: `CensysClient` — HTTP Basic auth with API ID + Secret. Searches hosts, certificates.

### 3.3 VirusTotal

**Purpose**: File/URL/IP threat intelligence.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `VIRUSTOTAL_API_KEY` | Yes | "" |

**Implementation**: `VirusTotalClient` — `x-apikey` header auth. Queries IP, domain, URL, file reports.

### 3.4 SecurityTrails

**Purpose**: DNS, subdomain, WHOIS intelligence.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `SECURITYTRAILS_API_KEY` | Yes | "" |

**Implementation**: `SecurityTrailsClient` — `APIKEY` header. Domain info, subdomain enumeration, DNS history, WHOIS.

### 3.5 AlienVault OTX

**Purpose**: Threat intelligence, IoCs.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `ALIENVAULT_OTX_KEY` | Yes | "" |

**Implementation**: `AlienVaultClient` — `X-OTX-API-KEY` header. IP/domain/URL reputation, pulse subscriptions.

### 3.6 GreyNoise

**Purpose**: Internet noise / threat context for IPs.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `GREYNOISE_API_KEY` | Yes | "" |

**Implementation**: `GreyNoiseClient` — `key` header. IP context and quick classification.

### 3.7 Intelligence X (IntelX)

**Purpose**: Dark web, leaked data, document search.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `INTELX_API_KEY` | Yes | "" |

**Implementation**: `IntelXClient` — `x-key` header. Search terms and fetch results.

### 3.8 Hunter.io

**Purpose**: Email pattern discovery, domain email search.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `HUNTER_API_KEY` | Yes | "" |

**Implementation**: `HunterClient` — API key as query param. Domain search, email finder, verifier.

### 3.9 IPInfo

**Purpose**: IP geolocation, ASN, carrier data.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `IPINFO_API_KEY` | Yes | "" |

**Implementation**: `IPInfoClient` — token as query param. Single and bulk IP lookup. Free tier allows 50K requests/month.

### 3.10 BuiltWith

**Purpose**: Website technology profiling.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `BUILTWITH_API_KEY` | Yes | "" |

**Implementation**: `BuiltWithClient` — API key as query param. Technology lookup for any domain.

### 3.11 URLScan.io

**Purpose**: Website screenshot, DOM, requests analysis.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `URLSCAN_API_KEY` | Yes | "" |

**Implementation**: `URLScanClient` — `API-Key` header. Submit URLs for scan, retrieve results.

### 3.12 Have I Been Pwned (HIBP)

**Purpose**: Breach and paste account monitoring.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `HIBP_API_KEY` | Yes | "" |

**Implementation**: `HIBPClient` — `hibp-api-key` header. Check breached accounts, list all breaches, paste monitoring.

### 3.13 Additional OSINT Tools

| Service | Env Var | Class |
|---|---|---|
| Pulsedive | `PULSEDIVE_API_KEY` | `PulsediveClient` |
| ThreatFox | (none, free) | `ThreatFoxClient` |
| SpoofCheck | (none, free) | `SpoofCheckClient` |

---

## 4. Crypto / Financial

### 4.1 Binance

**Purpose**: Exchange balance sync, portfolio tracking.

**Configuration** (stored in IdentityVault):
| Vault Key | Description |
|---|---|
| `exchange_binance.api_key` | Binance API key |
| `exchange_binance.api_secret` | Binance API secret |

**Verify**:
```bash
curl http://localhost:8000/api/financial/integrations/status
# Look for "Binance" entry with green/yellow/red status
```

**Implementation**: `ExchangeConnector` in `cores/crypto/exchange.py`. Uses `api.binance.com` with signed requests (HMAC-SHA256). Reads balances from `/api/v3/account`.

### 4.2 Coinbase

**Purpose**: Exchange balance sync, portfolio tracking.

**Configuration** (stored in IdentityVault):
| Vault Key | Description |
|---|---|
| `exchange_coinbase.api_key` | Coinbase API key |
| `exchange_coinbase.api_secret` | Coinbase API secret (HMAC-SHA256 signing) |

**Implementation**: `ExchangeConnector`. Uses `api.coinbase.com`. HMAC-SHA256 signed requests with CB-ACCESS-SIGN header. The ATLAS connector at `apps/atlas/connectors/coinbase/connector.py` was specifically fixed to implement correct HMAC signing.

### 4.3 Kraken

**Purpose**: Exchange balance sync, ticker data.

**Configuration** (stored in IdentityVault):
| Vault Key | Description |
|---|---|
| `exchange_kraken.api_key` | Kraken API key |
| `exchange_kraken.api_secret` | Kraken private key (HMAC-SHA512) |

**Implementation**: `ExchangeConnector`. Uses `api.kraken.com`. HMAC-SHA512 signed requests. Fixed in v4.1.0 for correct portfolio balance + ticker via private API.

### 4.4 Takenos (Virtual Wallet)

**Purpose**: Virtual USD wallet for LATAM freelancers. No public REST API available.

**Configuration**: No env vars required. Configured via connector methods:

```python
from cores.financial.takenos.connector import get_takenos_connector
conn = get_takenos_connector()

# Manual balance entry
conn.set_balance_manual(usd=1500.00, ars=1350000.00)

# Link Solana wallet for auto-tracking
conn.link_solana_wallet("8x...your-solana-address")

# Import CSV extract
conn.import_csv_file("/path/to/takenos_export.csv")
```

**Verify**:
```bash
curl http://localhost:8000/api/financial/integrations/status
# Look for "Takenos" entry
```

**Implementation**: `TakenosConnector` in `cores/financial/takenos/connector.py`. Supports manual balance, CSV import with columns (date, description, amount, currency, type, status, reference), and on-chain Solana USDC sync.

### 4.5 CoinGecko

**Purpose**: Crypto price oracle (no API key needed for free tier).

**Configuration**: None required for demo/free tier (100 calls/min, 10k/month).

**Verify**:
```bash
# Check health
curl http://localhost:8000/api/financial/integrations/status
# "coingecko" entry should show green

# Check prices in dashboard
curl http://localhost:8000/api/financial/dashboard
# Look for "precios" field
```

**Implementation**: `CoinGeckoFeed` in `cores/crypto/coingecko.py`. Tracks 30+ crypto prices (BTC, ETH, SOL, USDC, USDT, DAI, BNB, ADA, DOT, AVAX, LINK, UNI, ATOM, XRP, DOGE, TRX, ARB, OP, APT, SUI, NEAR, FET, RENDER, INJ, TIA, SEI, PEPE, WIF, BONK). 60-second cache, 1.5s rate limiting between calls. The CoinGecko feed is automatically used by the financial dashboard (`cores/financial/dashboard.py`) to populate `precios` in the dashboard response. Prices include 24-hour change data for trend visualization.

**Supported endpoints**: `/simple/price` with `include_24hr_change=true`, `/ping` for health.

### 4.6 Yahoo Finance

Not currently implemented as a standalone connector. Price data for traditional assets is expected via extension or CoinGecko fallback.

### 4.7 Alpaca

Not currently implemented. Could be added as an extension using the Extension SDK.

### 4.8 Finnhub

Not currently implemented. Could be added as an extension.

### 4.9 Polygon

Not currently implemented. Could be added as an extension.

---

## 5. Communications

### 5.1 SMTP Email

**Purpose**: Send email notifications (findings, reports, system alerts).

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `CATEYE_SMTP_HOST` | Yes | "" |
| `CATEYE_SMTP_PORT` | No | 587 |
| `CATEYE_SMTP_USER` | No | "" |
| `CATEYE_SMTP_PASSWORD` | No | "" |
| `CATEYE_SMTP_FROM` | No | "" |
| `CATEYE_NOTIFICATION_EMAIL` | Yes | "" |

**Implementation**: `EmailAdapter` in `cores/notifications/email.py`. STARTTLS, HTML emails with CATEYE branding. Sends to configured notification email address.

**Verify**: Set env vars, restart backend, check logs for "Email sent".

### 5.2 Twilio (WhatsApp)

**Purpose**: WhatsApp notifications for critical findings and system alerts.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `CATEYE_TWILIO_ACCOUNT_SID` | Yes | "" |
| `CATEYE_TWILIO_AUTH_TOKEN` | Yes | "" |
| `CATEYE_TWILIO_WHATSAPP_FROM` | No | 14155238886 |
| `CATEYE_NOTIFICATION_WHATSAPP_TO` | Yes | "" |

**Implementation**: WhatsApp adapter in `cores/notifications/whatsapp.py`. Uses Twilio Messages API.

**Verify**: Set env vars, trigger a notification, check WhatsApp for message.

### 5.3 Google OAuth (Gmail)

**Purpose**: Send email notifications via Gmail API (OAuth2). Also powers AuthHub Gmail integration.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `CATEYE_GMAIL_CLIENT_ID` | Yes | "" |
| `CATEYE_GMAIL_CLIENT_SECRET` | Yes | "" |
| `CATEYE_GMAIL_REFRESH_TOKEN` | Yes | "" |
| `CATEYE_GMAIL_FROM` | Yes | "" |

OAuth2 flow:
1. Set CLIENT_ID and CLIENT_SECRET
2. Generate authorize URL: `POST /api/authhub/gmail/authorize`
3. Visit URL, grant consent, get authorization code
4. Exchange code: `POST /api/authhub/gmail/callback`
5. Tokens saved automatically to IdentityVault

**Implementation**: `GmailOAuth2` in `cores/authhub/gmail.py` (OAuth2 flow) and `GmailAdapter` in `cores/notifications/gmail.py` (sending). Uses `https://gmail.googleapis.com/gmail/v1/users/me/messages/send`.

**Verify**: Check `GET /api/authhub/gmail/status` for authentication state.

### 5.4 Firebase Cloud Messaging (FCM)

**Purpose**: Push notifications for the desktop/web app.

**Configuration**:
| Variable | Required | Default |
|---|---|---|
| `CATEYE_FCM_SERVER_KEY` | Yes | "" |
| `CATEYE_FCM_PROJECT_ID` | Yes | "" |

**Verify**: Registered in notification bridges on startup (see `api/main.py:236`).

---

## 6. Other Integrations

### 6.1 GitHub

**Purpose**: Code scanning, repository intelligence, leak detection. Monitor GitHub for leaked credentials, exposed API keys, or sensitive configuration in public repositories.

**Configuration**: Via IdentityVault or extension. Access tokens can be configured via the IdentityVault and are consumed by the OSINT pipeline. GitHub API base URL is `https://api.github.com`.

### 6.2 GitLab

**Purpose**: Self-hosted code scanning, CI/CD pipeline intelligence. Monitor GitLab instances for exposed repositories, CI/CD misconfigurations, and leaked secrets.

**Configuration**: Via IdentityVault or extension. API tokens can be stored in the IdentityVault under the `gitlab` provider. Supports both cloud (gitlab.com) and self-hosted instances.

---

## 7. Checking Integration Status (Unified)

The single endpoint for all integration health:

```bash
curl http://localhost:8000/api/financial/integrations/status
```

Returns:
```json
{
  "overall": "green",
  "total_integraciones": 8,
  "integradas": 6,
  "parciales": 1,
  "fallidas": 1,
  "integraciones": {
    "hackerone": {
      "nombre": "Hackerone",
      "tipo": "plataforma_bounty",
      "balance_usd": 4500.00,
      "estado": "green",
      "ultima_sincronizacion": "2026-07-10T12:00:00+00:00",
      "fallos_consecutivos": 0,
      "error": ""
    },
    "coingecko": {
      "nombre": "CoinGecko",
      "tipo": "oraculo_precios",
      "balance_usd": 0.0,
      "estado": "green",
      "error": ""
    },
    "takenos": {
      "nombre": "Takenos",
      "tipo": "billetera_virtual",
      "balance_usd": 1500.00,
      "estado": "yellow",
      "error": "Sin datos cargados — usá CSV o vinculá wallet Solana"
    }
  }
}
```

Status calculation:
- **green**: 0 consecutive failures, last success recent
- **yellow**: 1-4 consecutive failures or no success yet
- **red**: 5+ consecutive failures

The status logic is in `api/routers/financial_truth.py:_calc_integration_status()`.

---

## 8. IdentityVault Credential Storage

All exchange and platform credentials are stored in the IdentityVault (`cores/identity_vault.py`). The vault uses AES-256-GCM encryption with a random key stored at `~/.orion/identity_vault.key` (chmod 600). On first access, the vault auto-migrates from legacy `/etc/machine-id` derived keys to random keys, ensuring forward secrecy. Each credential is stored with a provider name, associated email, token, and arbitrary metadata dict.

```python
from cores.identity_vault import get_identity_vault

vault = get_identity_vault()

# Store exchange credentials
vault.store_credentials(
    provider="exchange_binance",
    email="",
    token="",
    metadata={
        "api_key": "your-binance-api-key",
        "api_secret": "your-binance-api-secret",
    }
)

# Retrieve
creds = vault.get_credentials("exchange_binance")
api_key = creds.get("api_key")
api_secret = creds.get("api_secret")
```

Vault data is encrypted with AES-256-GCM at `~/.orion/`. For quick configuration, environment variables also work and are preferred for most setups. Use the IdentityVault REST API (`/api/core/secrets/*`) for runtime secret management without restarting the backend. The Secrets Manager also caches secrets in-memory for fast access and falls back to environment variables if a key is not found in the vault.

---

## Appendix: Complete Env Var Reference

| Category | Variable | Default |
|---|---|---|
| Server | `CATEYE_PORT` | 8000 |
| Server | `CATEYE_HOST` | 127.0.0.1 |
| Mode | `CATEYE_DESKTOP` | 0 |
| Mode | `CATEYE_DEBUG` | 0 |
| Mode | `CATEYE_SAFE_MODE` | 0 |
| Mode | `CATEYE_DEMO` | 0 |
| Auth | `CATEYE_AUTH_SECRET` | "" |
| AI | `OPENAI_API_KEY` | "" |
| AI | `OPENAI_BASE_URL` | https://api.openai.com/v1 |
| AI | `OPENROUTER_API_KEY` | "" |
| AI | `GEMINI_API_KEY` | "" |
| AI | `OLLAMA_HOST` | http://localhost:11434 |
| AI | `OLLAMA_MODEL` | freehuntx/qwen3-coder:8b |
| OSINT | `SHODAN_API_KEY` | "" |
| OSINT | `CENSYS_API_KEY` | "" |
| OSINT | `CENSYS_API_SECRET` | "" |
| OSINT | `VIRUSTOTAL_API_KEY` | "" |
| OSINT | `SECURITYTRAILS_API_KEY` | "" |
| OSINT | `ALIENVAULT_OTX_KEY` | "" |
| OSINT | `URLSCAN_API_KEY` | "" |
| OSINT | `HUNTER_API_KEY` | "" |
| OSINT | `BUILTWITH_API_KEY` | "" |
| OSINT | `HIBP_API_KEY` | "" |
| OSINT | `GREYNOISE_API_KEY` | "" |
| OSINT | `INTELX_API_KEY` | "" |
| OSINT | `PULSEDIVE_API_KEY` | "" |
| OSINT | `IPINFO_API_KEY` | "" |
| SMTP | `CATEYE_SMTP_HOST` | "" |
| SMTP | `CATEYE_SMTP_PORT` | 587 |
| SMTP | `CATEYE_SMTP_USER` | "" |
| SMTP | `CATEYE_SMTP_PASSWORD` | "" |
| SMTP | `CATEYE_SMTP_FROM` | "" |
| Notification | `CATEYE_NOTIFICATION_EMAIL` | "" |
| Twilio | `CATEYE_TWILIO_ACCOUNT_SID` | "" |
| Twilio | `CATEYE_TWILIO_AUTH_TOKEN` | "" |
| Twilio | `CATEYE_TWILIO_WHATSAPP_FROM` | 14155238886 |
| Twilio | `CATEYE_NOTIFICATION_WHATSAPP_TO` | "" |
| Gmail | `CATEYE_GMAIL_CLIENT_ID` | "" |
| Gmail | `CATEYE_GMAIL_CLIENT_SECRET` | "" |
| Gmail | `CATEYE_GMAIL_REFRESH_TOKEN` | "" |
| Gmail | `CATEYE_GMAIL_FROM` | "" |
| FCM | `CATEYE_FCM_SERVER_KEY` | "" |
| FCM | `CATEYE_FCM_PROJECT_ID` | "" |
| Scan | `CATEYE_SCAN_INTERVAL` | 30 |
| Scan | `CATEYE_SCAN_MODE` | DEEP |
| Sync | `CATEYE_SYNC_INTERVAL` | 30 |
| License | `CATEYE_LICENSE_SECRET` | "" |
| DB | `DATABASE_URL` | sqlite:///~/.orion/database/cateye.db |
| Crypto | `BINANCE_API_KEY` | vault |
| Crypto | `BINANCE_API_SECRET` | vault |
| Crypto | `COINBASE_API_KEY` | vault |
| Crypto | `COINBASE_API_SECRET` | vault |
| Crypto | `KRAKEN_API_KEY` | vault |
| Crypto | `KRAKEN_PRIVATE_KEY` | vault |
