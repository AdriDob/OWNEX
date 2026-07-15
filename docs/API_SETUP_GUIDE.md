# API Setup Guide — Configure ORION for Real-World Operation

> **Purpose**: One-stop reference for configuring every integration ORION supports.
> Use the Integration Center (`Settings > Integraciones`) to verify each one after setup.

---

## Quick Start

1. Set environment variables OR use the Secrets Manager (Settings > API Keys)
2. Run `python run.py --setup` or visit the Setup Wizard at first run
3. Check status at `Settings > Integraciones`

---

## Bug Bounty Platforms

### HackerOne
| Field | Value |
|---|---|
| Env var | `HACKERONE_API_KEY` |
| Obtené tu key | `https://hackerone.com/settings/api` |
| Permisos necesarios | `Read` |

### Bugcrowd
| Field | Value |
|---|---|
| Env var | `BUGCROWD_TOKEN` |
| Obtené tu token | `https://bugcrowd.com/user/edit` |
| Permisos necesarios | `Read` |

### Intigriti
| Field | Value |
|---|---|
| API Key | Settings > API Keys > `intigriti` |
| Obtené tu key | `https://app.intigriti.com/profile` |

### YesWeHack
| Field | Value |
|---|---|
| API Key | Settings > API Keys > `yeswehack` |
| Obtené tu key | `https://yeswehack.com/profile` |

### Synack
| Field | Value |
|---|---|
| API Key | Settings > API Keys > `synack` |
| Obtené tu key | `https://synack.com/account` |

---

## Reconnaissance (OSINT)

### Shodan
| Field | Value |
|---|---|
| Env var | `SHODAN_API_KEY` |
| Obtené tu key | `https://account.shodan.io` |
| Uso | IP lookup, port scanning, service fingerprinting |

### Censys
| Field | Value |
|---|---|
| Env var | `CENSYS_API_ID`, `CENSYS_SECRET` |
| Obtené tu key | `https://search.censys.io/account/api` |
| Uso | Certificate transparency, host enumeration |

### VirusTotal
| Field | Value |
|---|---|
| Env var | `VIRUSTOTAL_API_KEY` |
| Obtené tu key | `https://virustotal.com/gui/my-apikey` |
| Uso | Domain/IP reputation, sample analysis |

### SecurityTrails
| Field | Value |
|---|---|
| Env var | `SECURITYTRAILS_API_KEY` |
| Obtené tu key | `https://securitytrails.com/app/account/credentials` |
| Uso | DNS history, subdomain enumeration |

### URLScan
| Field | Value |
|---|---|
| Env var | `URLSCAN_API_KEY` |
| Obtené tu key | `https://urlscan.io/user/api/` |
| Uso | Screenshot capture, domain analysis |

---

## AI Providers

### Ollama (local, recommended)
```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull qwen3:8b
ollama pull llama3:8b

# Verify
ollama list
```

| Setting | Value |
|---|---|
| Host | `http://localhost:11434` (default) |
| Model | `qwen3:8b` or `llama3:8b` |
| Env var | `OLLAMA_HOST` |

### OpenAI
| Field | Value |
|---|---|
| Env var | `OPENAI_API_KEY` |
| Obtené tu key | `https://platform.openai.com/api-keys` |
| Modelos | `gpt-4o`, `gpt-4o-mini` |

### Gemini
| Field | Value |
|---|---|
| Env var | `GEMINI_API_KEY` |
| Obtené tu key | `https://aistudio.google.com/apikey` |
| Modelos | `gemini-2.0-flash`, `gemini-2.0-pro` |

### OpenRouter
| Field | Value |
|---|---|
| Env var | `OPENROUTER_API_KEY` |
| Obtené tu key | `https://openrouter.ai/keys` |
| Beneficio | Un solo API key para múltiples modelos |

---

## Notifications

### Discord (recommended for real-time alerts)
```bash
# 1. Go to your Discord server
# 2. Server Settings > Integrations > Webhooks
# 3. Create a webhook, copy the URL
# 4. Set the env var:
export CATEYE_DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

| Field | Value |
|---|---|
| Env var | `CATEYE_DISCORD_WEBHOOK_URL` |
| Eventos que recibe | finding.confirmed, backup.failed, health.warning, system.error, report.ready |

### Gmail
Requiere OAuth2. Configuración más compleja:
1. Crear proyecto en `https://console.cloud.google.com`
2. Habilitar Gmail API
3. Crear credenciales OAuth2 (Desktop)
4. Obtener refresh token

| Field | Env var |
|---|---|
| Client ID | `CATEYE_GMAIL_CLIENT_ID` |
| Client Secret | `CATEYE_GMAIL_CLIENT_SECRET` |
| Refresh Token | `CATEYE_GMAIL_REFRESH_TOKEN` |
| From email | `CATEYE_GMAIL_FROM` |

### Email (SMTP)
```bash
export CATEYE_SMTP_HOST="smtp.gmail.com"
export CATEYE_SMTP_PORT=587
export CATEYE_SMTP_USER="tu@email.com"
export CATEYE_SMTP_PASSWORD="tu-contraseña"
export CATEYE_SMTP_FROM="tu@email.com"
export CATEYE_NOTIFICATION_EMAIL="tu@email.com"
```

### WhatsApp (Twilio)
```bash
export CATEYE_TWILIO_ACCOUNT_SID="..."
export CATEYE_TWILIO_AUTH_TOKEN="..."
export CATEYE_TWILIO_WHATSAPP_FROM="+14155238886"
export CATEYE_NOTIFICATION_WHATSAPP_TO="+5411..."
```

---

## Financial

### CoinGecko
No necesita API key (free tier). Se usa automáticamente para precios de crypto.

| Env var | Default |
|---|---|
| `COINGECKO_API_KEY` | (opcional, para rate limits más altos) |

### Binance
| Field | Value |
|---|---|
| Env vars | `BINANCE_API_KEY`, `BINANCE_SECRET_KEY` |
| Crear API key | `https://binance.com/en/settings/api-management` |

### Coinbase
| Field | Value |
|---|---|
| Env vars | `COINBASE_API_KEY`, `COINBASE_SECRET` |
| Nota | Usa HMAC-SHA256 para firmar requests |

### Kraken
| Field | Value |
|---|---|
| Env vars | `KRAKEN_API_KEY`, `KRAKEN_SECRET` |
| Crear API key | `https://kraken.com/settings/api` |

### Takenos
| Field | Value |
|---|---|
| Config | Via Secrets Manager > `takenos` |

---

## Infrastructure

### Identity Vault
Se crea automáticamente en `~/.orion/identity_vault.key`.
Almacena todas las API keys cifradas con AES-256-GCM.

```bash
# Verificar estado
curl http://localhost:8000/api/core/secrets/health

# Listar keys almacenadas
curl http://localhost:8000/api/core/secrets
```

---

## Verifying Integrations

### From the UI
1. Go to `Settings > Integraciones`
2. Click "Actualizar" to refresh status
3. Click "Test" on any integration to verify

### From the API
```bash
# List all integrations
curl http://localhost:8000/api/core/integrations | jq

# Test a specific one
curl -X POST http://localhost:8000/api/core/integrations/discord/test | jq
```

### From the terminal
```bash
# Run the setup wizard
python run.py --setup
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Integration shows 🔴 error | Expired API key, wrong env var name | Regenerate key in provider dashboard |
| Integration shows 🟡 disconnected | Key not configured yet | Set env var or add via Secrets Manager |
| Integration shows ⚪ unknown | Never checked | Click "Test" or "Actualizar" |
| Ollama not found | Not installed or not in PATH | `curl -fsSL https://ollama.com/install.sh | sh` |
| Discord not sending | Wrong webhook URL | Test with `curl -X POST $URL -H "Content-Type: application/json" -d '{"content":"hello"}'` |
| Gmail auth fails | Expired refresh token | Regenerate OAuth2 credentials |

---

## Complete Environment Reference

```bash
# === REQUIRED ===
CATEYE_AUTH_SECRET=your-secret-key

# === AI ===
OLLAMA_HOST=http://localhost:11434
# or
OPENAI_API_KEY=sk-...
# or
GEMINI_API_KEY=...
# or
OPENROUTER_API_KEY=...

# === OSINT ===
SHODAN_API_KEY=...
CENSYS_API_ID=...
CENSYS_SECRET=...
VIRUSTOTAL_API_KEY=...
SECURITYTRAILS_API_KEY=...

# === NOTIFICATIONS ===
CATEYE_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
CATEYE_GMAIL_CLIENT_ID=...
CATEYE_GMAIL_CLIENT_SECRET=...
CATEYE_GMAIL_REFRESH_TOKEN=...
CATEYE_GMAIL_FROM=tu@email.com
CATEYE_SMTP_HOST=smtp.gmail.com
CATEYE_SMTP_PORT=587
CATEYE_SMTP_USER=tu@email.com
CATEYE_SMTP_PASSWORD=...
CATEYE_NOTIFICATION_EMAIL=tu@email.com
CATEYE_TWILIO_ACCOUNT_SID=...
CATEYE_TWILIO_AUTH_TOKEN=...
CATEYE_TWILIO_WHATSAPP_FROM=+14155238886

# === EXCHANGES ===
BINANCE_API_KEY=...
BINANCE_SECRET_KEY=...
COINBASE_API_KEY=...
COINBASE_SECRET=...
KRAKEN_API_KEY=...
KRAKEN_SECRET=...
```
