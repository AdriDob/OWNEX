# CATEYE Operation Manual

> v4.1.0 STABLE — ORION Financial Layer. CoinGecko, Takenos, Dashboard, Integrations.
> July 2026.

---

## 1. Quick Start

### Starting the Backend

```bash
# Development mode (hot reload)
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# Production mode via launcher
python run.py --start

# Or directly with Python
python run.py
```

### Health Check

```bash
curl http://localhost:8000/api/health
# {"status":"ok","app":"CATEYE API","version":"4.1.0"}
```

### Add a Target

```bash
python run.py --add-target "Acme Corp" --domain acme.com
# Target 'Acme Corp' created (id=1)
```

### Run Tests

```bash
# Full test suite (516 tests)
.venv/bin/python -m pytest --timeout=60

# Specific module
.venv/bin/python -m pytest tests/test_financial_truth.py -v

# Lint
.venv/bin/python -m ruff check .
```

### Backup

```bash
python run.py --backup
# Backup created: /home/user/.orion/backups/cateye_20260710_120000.zip
```

---

## 2. Daily Workflow

### 2.1 Check System Health

Start every day by verifying the system is operational:

```bash
# Quick health check
curl http://localhost:8000/api/health

# Full system status
curl http://localhost:8000/api/system/status

# System state with service health
curl http://localhost:8000/api/system/state

# ORION Platform health
curl http://localhost:8000/api/core/health
```

Expected: all endpoints return 200, status is "ok", services are "healthy".

### 2.2 Review New Findings

```bash
# List all findings (paginated, default sort by severity desc)
curl http://localhost:8000/api/findings

# Filter by open status
curl http://localhost:8000/api/findings?search=open

# Get finding statistics
curl http://localhost:8000/api/findings/stats
```

The findings stats endpoint returns total count, severity breakdown, and new findings in the last 24 hours.

### 2.3 Validate Pending Findings

The scheduler automatically runs VALIDATE stage every 2 hours, processing open findings with high/critical severity. To manually validate:

```bash
# Trigger scan on a target
curl -X POST http://localhost:8000/api/targets/1/scan \
  -H "Content-Type: application/json" \
  -d '{"mode": "quick"}'
```

Update finding status after review:

```bash
curl -X PUT http://localhost:8000/api/findings/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}'
```

Valid statuses: `open`, `confirmed`, `rejected`, `in_progress`.

### 2.4 Generate Reports

When findings are confirmed, generate reports:

```bash
# List reports
curl http://localhost:8000/api/reports

# Create a new report from confirmed findings
curl -X POST http://localhost:8000/api/reports \
  -H "Content-Type: application/json" \
  -d '{"finding_ids": [1, 2, 3]}'
```

The auto-report feature (registered in `api/main.py:266`) automatically generates a draft report when any finding's status changes to "confirmed".

### 2.5 Check Financial Dashboard

```bash
# Unified financial dashboard
curl http://localhost:8000/api/financial/dashboard

# Integration status (green/yellow/red)
curl http://localhost:8000/api/financial/integrations/status
```

The dashboard returns: patrimonio_total, objetivo_libertad (30K goal with progress %), liquidity breakdown, crypto prices, monthly income, and alerts.

### 2.6 Review Integration Status

```bash
# All financial integrations
curl http://localhost:8000/api/financial/integrations/status

# Sync status
curl http://localhost:8000/api/financial/sync/status

# Force sync all
curl -X POST http://localhost:8000/api/financial/sync/all
```

---

## 3. System Management

### 3.1 Backup and Restore

```bash
# Create backup (archives DB + config + vault)
python run.py --backup

# Restore from backup
python run.py --restore /path/to/backup.zip
```

Backups include: SQLite database, IdentityVault key, audit log, evidence files, and configuration.

### 3.2 Scheduler Pipeline

The autonomous scheduler runs continuously with these stages:

| Stage | Interval | Function |
|---|---|---|
| DISCOVER | 60 min | Scrape public bug bounty platforms for new programs |
| RECON | 30 min | Passive recon (subfinder, amass, httpx, etc.) |
| HYPOTHESIS | 15 min | Generate vulnerability hypotheses from recon data |
| SCOPE_CHECK | 60 min | Verify validation is authorized before proceeding |
| VALIDATE | 120 min | Run controlled active tests on in-scope targets |
| REPORT | 60 min | Generate reports for confirmed findings |

Configuration via environment:
```bash
export CATEYE_SCAN_INTERVAL=30    # Pipeline cycle interval (minutes)
export CATEYE_SCAN_MODE=DEEP      # Scan mode: FAST, DEEP, or SCHEDULED
```

The scheduler is defined in `api/scheduler.py`. ORION auto-prioritization via `get_next_action()` provides a 1.5x priority boost to recommended targets.

### 3.3 ORION Auto-Prioritization

ORION computes target priority using:
1. RewardLearner adjustments (vuln type payout history)
2. Program.orion_score multiplier (0.5x to 2.0x)
3. ORION next_action 1.5x boost for recommended targets
4. Recency weighting (targets active within last 10 days)

Logged as: `[ORION] Auto-prioritized <target> (priority=<score>)`

The auto-prioritization logic is in `api/scheduler.py:_compute_target_priorities()`.

### 3.4 Financial Auto-Sync

The financial scheduler syncs platform balances and crypto wallets:
```bash
export CATEYE_SYNC_INTERVAL=30    # Sync interval (minutes)
```

Manual triggers:
```bash
# Sync all platforms
curl -X POST http://localhost:8000/api/financial/sync/platforms

# Sync all crypto wallets
curl -X POST http://localhost:8000/api/financial/sync/crypto

# Sync everything
curl -X POST http://localhost:8000/api/financial/sync/all

# Check sync status
curl http://localhost:8000/api/financial/sync/history?limit=5
```

---

## 4. Configuration

### 4.1 Environment Variables

All configuration uses `CATEYE_*` prefixed env vars (with legacy `RASTRO_*` fallbacks). See `cores/env/config.py` for the complete list.

| Variable | Default | Description |
|---|---|---|
| CATEYE_PORT | 8000 | API server port |
| CATEYE_HOST | 127.0.0.1 | API bind address |
| CATEYE_DEBUG | 0 | Enable debug mode |
| CATEYE_LOG_LEVEL | INFO | Logging level |
| CATEYE_DESKTOP | 0 | Desktop mode (disables CORS wildcard) |
| CATEYE_SCAN_INTERVAL | 30 | Pipeline cycle minutes |
| CATEYE_SCAN_MODE | DEEP | Scan mode (FAST/DEEP/SCHEDULED) |
| CATEYE_SYNC_INTERVAL | 30 | Financial sync interval |
| CATEYE_AUTH_SECRET | "" | Auth token signing secret |
| CATEYE_DATA_DIR | ~/.orion | Data directory |
| DATABASE_URL | sqlite:///~/.orion/database/cateye.db | Database connection string |

### 4.2 IdentityVault

Sensitive credentials are stored in the IdentityVault (`cores/identity_vault.py`), encrypted with AES-256-GCM. The vault key is at `~/.orion/identity_vault.key`.

```bash
# Reset vault (regenerates key)
rm ~/.orion/identity_vault.key
```

After reset, all stored credentials must be re-configured. The vault auto-migrates from legacy `machine-id` derived keys on first access.

### 4.3 Extension Configuration

ORION Platform extensions live in `extensions/*/manifest.py`. Each extension declares:
- `id`, `name`, `version`
- `capabilities` (what APIs/hooks it provides)
- `settings` (declarative schema with defaults)
- `hooks` (before/after handlers)

Example minimal extension manifest:
```python
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="hello_world",
    name="Hello World",
    version="1.0.0",
    description="Minimal example extension",
    capabilities=["greeting"],
    settings={"greeting": {"type": "string", "default": "Hello"}},
)
```

Extensions are auto-discovered on startup. Status available at:
```bash
curl http://localhost:8000/api/core/extensions
```

### 4.4 Secrets Management

API keys and tokens can be managed via the Secrets Manager (`core/secrets/manager.py`), which bridges IdentityVault with env var fallback:

```bash
# List secret keys
curl http://localhost:8000/api/core/secrets

# Get a secret
curl http://localhost:8000/api/core/secrets/OPENAI_API_KEY

# Set a secret
curl -X PUT http://localhost:8000/api/core/secrets/SHODAN_API_KEY \
  -H "Content-Type: application/json" \
  -d '{"value": "your-key-here"}'

# Delete a secret
curl -X DELETE http://localhost:8000/api/core/secrets/SHODAN_API_KEY
```

---

## 5. Troubleshooting

### 5.1 Check Logs

```bash
# Audit log (JSONL, rotated at 10MB, 3 backups)
tail -f ~/.orion/audit.jsonl

# Scheduler logs (via application logging)
# Set CATEYE_LOG_LEVEL=DEBUG for verbose output

# System events
curl http://localhost:8000/api/system/state/events?limit=50
```

### 5.2 Common Issues

**Backend won't start**
- Check port availability: `lsof -i :8000`
- Verify database path: `echo $DATABASE_URL`
- Check Python version: 3.10+ required
- Run in safe mode: `python run.py --safe-mode`

**Scheduler not running**
- Verify it started: check logs for "Scan scheduler started"
- Check cooldowns: targets skip recon for 1 hour after scan
- Verify ORION scoring: look for "[ORION]" log entries

**Financial sync failing**
- Check integration status: `curl http://localhost:8000/api/financial/integrations/status`
- Verify API keys in IdentityVault or env vars
- Check crypto sync manager connectors

**Auth issues**
- Clear session store: `rm ~/.orion/sessions.json`
- Reset IdentityVault: `rm ~/.orion/identity_vault.key`
- Verify CATEYE_AUTH_SECRET is set

**Database errors**
- WAL checkpoint: the scheduler runs `PRAGMA wal_checkpoint(TRUNCATE)` after each cycle
- Backup and restore: `python run.py --backup && python run.py --restore <file>`
- DB size check: `curl http://localhost:8000/api/system/status`

### 5.3 Desktop App Issues

```bash
# Build desktop app
pyinstaller CATEYE.spec

# Run in browser mode (no tray)
python run.py --browser

# Run with tray
python run.py --tray

# Diagnostics
python run.py --check
```

The Watchdog (`desktop/watchdog.py`) monitors the backend process and EventBus health. It checks bus connectivity every 10 seconds.

### 5.4 Reset Procedures

| Issue | Command |
|---|---|
| Reset vault | `rm ~/.orion/identity_vault.key` |
| Clear sessions | `rm ~/.orion/sessions.json`* |
| Clear evidence | `rm -rf ~/.orion/evidence/*` |
| Reset DB | `rm ~/.orion/database/cateye.db` |
| Factory reset | `rm -rf ~/.orion` |

*\* File is encrypted with AES-256-GCM.*

---

## 5.5 Understanding the Pipeline Logs

The scheduler logs are the primary diagnostic tool. Each log entry has a consistent format:

```
[CATEYE] === Autonomous Pipeline Cycle ===
[CATEYE][DISCOVER] Scraping public bug bounty platforms...
[CATEYE][RECON] Scanning acme.com (mode=DEEP)
[CATEYE][ORION] Auto-prioritized Acme Corp (priority=2.35) — selected by reward learning + ORION scoring
[CATEYE][HYPOTHESIS] Generating vulnerability hypotheses...
[CATEYE][VALIDATE] Running scope-aware validation...
[CATEYE][REPORT] Generating reports...
[CATEYE] === Pipeline Cycle Complete ===
```

Key indicators:
- `[ORION] Auto-prioritized` — shows which target ORION chose and why
- `cooldown filtered` — shows how many targets were skipped due to 1-hour cooldown
- `DISCOVER ... X new targets created` — shows discovery output
- Each stage runs on its own interval (DISCOVER=60min, RECON=30min, HYPOTHESIS=15min, VALIDATE=120min, REPORT=60min)

## 5.6 WebSocket Event Stream

The system provides a WebSocket endpoint for real-time event streaming:

```
ws://localhost:8000/ws
```

Events from the EventBus are forwarded to connected WebSocket clients, including:
- `finding:created` — new findings
- `finding:status_changed` — status updates
- `report:generated` — auto-generated reports
- `opportunity:found` — new opportunities
- `system:*` — system health events
- `agent:*` — multi-agent events
- `financial:*` — financial sync events

## 6. Desktop App

### 6.1 PyInstaller Build

```bash
# Build distributable
python run.py --build

# Or directly
pyinstaller CATEYE.spec -y
```

The build uses `CATEYE.spec` in the project root. Output goes to `dist/CATEYE/`.

### 6.2 Watchdog

The desktop watchdog (`desktop/watchdog.py`) provides:
- Process health monitoring (checks backend PID every 10s)
- EventBus connectivity verification
- Automatic notification on failure

Configure via:
```bash
export CATEYE_HEALTH_CHECK_INTERVAL=10
export CATEYE_MAX_RESTART_RETRIES=3
```

### 6.3 Tray Icon

System tray icon provides:
- Quick status indicator (green/red)
- Start/stop backend
- Open dashboard in browser
- View recent findings
- Check integration status

### 6.4 Service Mode

Windows service installation:
```bash
python run.py --install-service
python run.py --remove-service
```

On Linux, use the provided init scripts or run as a systemd service.

### 6.5 Running in Headless Mode

For server deployments without a display:

```bash
# Run without tray or desktop UI
python run.py --browser

# Or set environment
export CATEYE_DESKTOP=0
python run.py
```

The system detects headless environments via `boot_guard.py` and automatically falls back to browser-only mode. The Watchdog adapts its health checks to not require tray icon connectivity.

### 6.6 Performance Tuning

For production deployments, consider these optimizations:

**Database**: The SQLite backend can handle moderate workloads. For heavy use (100+ targets), consider tuning WAL settings:
```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-64000;  -- 64MB cache
```

The scheduler automatically runs `PRAGMA wal_checkpoint(TRUNCATE)` after each pipeline cycle to prevent WAL unbounded growth.

**Cache**: The CoinGecko price cache TTL is 60 seconds by default. For dashboard-heavy usage, increase via:
```python
# In cores/crypto/coingecko.py
self._cache_ttl = 120  # Increase from 60 to 120 seconds
```

**Cooldowns**: Target cooldown is 1 hour. For aggressive testing, decrease via `TARGET_COOLDOWN` in `api/scheduler.py`.

**Max pool connections**: SQLAlchemy default pool is fine for single-user desktop use. For multi-agent setups, configure pool_size and max_overflow via the DATABASE_URL query params.

### 6.7 Multi-Agent System

Starting in v4.0.0, CATEYE includes a multi-agent system (`cores/agents/`) that runs alongside the scheduler. Agents are started automatically on boot and include:
- Research agents (analyze targets, gather intelligence)
- Validation agents (run controlled tests)
- Report agents (draft and format reports)

Agent activity is logged with `[AGENT]` prefix. All agent events are bridged to the EventBus via AgentBus bridge (`cores/agents/bus.py`).

---

## 7. Security Best Practices

1. **Environment isolation**: Never run CATEYE as root. Use a dedicated user account with limited permissions.
2. **Vault backups**: Back up `~/.orion/identity_vault.key` separately from the database. Without this key, stored credentials are permanently lost.
3. **Audit monitoring**: Review `~/.orion/audit.jsonl` regularly for unauthorized access attempts. The audit log records login, logout, and token_stored events.
4. **CSRF protection**: CSRF middleware is always active. To disable (development only), set `CATEYE_CSRF_DISABLED=1`.
5. **Network exposure**: Bind to `127.0.0.1` by default. Only expose the API to external networks if you have proper firewall rules.
6. **Token rotation**: Rotate API keys for all integrations periodically. Use the Secrets Manager REST API for key updates without restart.
7. **File permissions**: The vault key and audit log have `chmod 600`. Verify this after installation:
   ```bash
   ls -la ~/.orion/identity_vault.key ~/.orion/audit.jsonl
   ```

## Appendix: Key Files

| Component | Path |
|---|---|
| API entry point | `api/main.py` |
| Router index | `api/routers/` (66 routers) |
| Scheduler | `api/scheduler.py` |
| Auth manager | `cores/auth/auth_manager.py` |
| IdentityVault | `cores/identity_vault.py` |
| Event bus | `cores/events/event_bus.py` |
| Financial dashboard | `cores/financial/dashboard.py` |
| CoinGecko feed | `cores/crypto/coingecko.py` |
| Takenos connector | `cores/financial/takenos/connector.py` |
| OSINT clients | `cores/recon/osint_api.py` |
| AI providers | `cores/ai/provider.py` |
| ORION agent | `cores/ai/orion_agent.py` |
| Extension SDK | `core/extension/` |
| Secrets manager | `core/secrets/manager.py` |
| Health center | `core/health/engine.py` |
| Env config | `cores/env/config.py` |
| Launcher | `run.py` |
| Desktop watchdog | `desktop/watchdog.py` |
| Database models | `database/models.py` |
