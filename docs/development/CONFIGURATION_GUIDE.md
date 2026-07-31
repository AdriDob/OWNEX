# Configuration Guide

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `CATEYE_DESKTOP` | `false` | Enable desktop mode (CORS, CSRF relaxed) |
| `CATEYE_API_KEY` | — | API key for programmatic access |
| `CATEYE_SYNC_INTERVAL` | `30` | Financial sync interval (minutes) |
| `ORION_EXTENSIONS_DIR` | `extensions/` | Custom extension directory |
| `ORION_CONFIG_PROFILE` | `minimal` | Active config profile |
| `LOG_LEVEL` | `INFO` | Logging level |
| `COPILOT_AUTHORITY` | `observer` | Senior Copilot authority level (`observer`, `assistant`, `operator`, `senior_hunter`, `admin`) |
| `COPILOT_MIN_CONFIDENCE_AUTO` | `0.70` | Min confidence for autonomous execution |
| `COPILOT_MIN_CONFIDENCE_REPORT` | `0.92` | Min confidence for auto-reporting |
| `COPILOT_MAX_DECISIONS` | `1000` | Max in-memory decisions in journal |
| `COPILOT_ENABLE_AUTO_AUDIT` | `true` | Enable periodic system auditing |
| `COPILOT_AUDIT_INTERVAL` | `24` | Audit interval in hours |
| `COPILOT_ENABLE_AUTO_REVIEW` | `true` | Enable pre-report Copilot Review |
| `COPILOT_MEMORY_ENABLED` | `true` | Enable Unified Memory integration |
| `COPILOT_HUNTER_MODE` | `standard` | Hunter mode (`beginner`, `standard`, `senior`, `elite`, `research`, `autonomous`) |

## Config Profiles

Located in `config/profiles/`. Built-in profiles:

- **minimal** — Core only, no extensions, no background agents
- **hunter** — Full pipeline (DISCOVER → RECON → HYPOTHESIS → VALIDATE → REPORT)
- **trading** — ATLAS + ODYSSEY enabled, financial sync active
- **developer** — Hot reload, verbose logging, mock providers
- **offline** — No external calls, cached data only
- **production** — All extensions, strict validation, full security

### Switching profiles

```bash
# Via CLI
python run.py --profile hunter

# Via API
curl -X PUT http://localhost:8000/api/core/profile -H "Content-Type: application/json" -d '{"profile": "hunter"}'
```

## Secrets Management

All API keys and credentials are managed through the Secrets Manager
backed by IdentityVault (AES-256-GCM encrypted on disk).

```bash
# Via API
curl -X PUT http://localhost:8000/api/core/secrets/BINANCE_API_KEY \
  -H "Content-Type: application/json" \
  -d '{"value": "your-key-here"}'

curl http://localhost:8000/api/core/secrets/BINANCE_API_KEY
```

Environment variables serve as fallback when the vault is unavailable.

## Health Checks

Run all health checks: `POST /api/core/health/run`

Status meanings:
- **green** — All systems operational
- **yellow** — Non-critical subsystems degraded
- **red** — Critical systems unavailable
