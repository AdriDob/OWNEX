# OWNEX Operations

> **Generated from actual codebase** — This document reflects the real implementation.

## Overview

This document covers operational procedures for running, monitoring, and maintaining OWNEX in production.

## Startup

### Development Mode

```bash
# Terminal 1: Backend
cd /home/adriel/projects/Rastro
source .venv/bin/activate
python -m api.main --port 8000 --log-level INFO

# Terminal 2: Frontend
cd /home/adriel/projects/Rastro/frontend
npm run dev

# Terminal 3: Tauri (Desktop)
cd /home/adriel/projects/Rastro/src-tauri
cargo tauri dev
```

### Production Mode (Desktop)

```bash
# 1. Build frontend
cd /home/adriel/projects/Rastro/frontend
npm run build

# 2. Build Python sidecar (ONEFILE)
cd /home/adriel/projects/Rastro
.venv/bin/pyinstaller OWNEX-Backend.spec --clean --noconfirm

# 3. Build Tauri bundle
cd /home/adriel/projects/Rastro/src-tauri
cargo tauri build --target x86_64-pc-windows-msvc

# 4. Installer artifacts in src-tauri/target/release/bundle/
```

### Production Mode (Server)

```bash
# Using systemd (Linux)
sudo systemctl start ownex-backend
sudo systemctl start ownex-frontend  # nginx + systemd

# Or Docker
docker-compose up -d
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite:///./database/cateye.db` | DB connection |
| `CATEYE_DATA_DIR` | No | Platform-specific | Data directory |
| `OWNEX_DESKTOP` | Desktop only | `1` | Enables desktop CORS |
| `ANTHROPIC_API_KEY` | For FCC | `orion-dev-local` | FCC proxy key |
| `OPENROUTER_API_KEY` | For OmniRoute | - | OmniRoute API key |
| `CATEYE_CSRF_DISABLED` | No | `0` | Disable CSRF (dev only) |

### Config Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python deps, tools config |
| `package.json` / `package-lock.json` | Frontend deps (workspace root) |
| `src-tauri/Cargo.toml` | Rust deps |
| `src-tauri/tauri.conf.json` | Tauri bundle config |
| `~/.hermes/config.yaml` | Hermes CLI |
| `~/.config/opencode/config.json` | OpenCode |

## Service Management

### Backend (FastAPI)

```bash
# Direct
python -m api.main --port 8000 --host 127.0.0.1

# With systemd (Linux)
# /etc/systemd/system/ownex-backend.service
[Unit]
Description=OWNEX Backend
After=network.target

[Service]
Type=simple
User=ownex
WorkingDirectory=/opt/ownex
Environment=DATABASE_URL=sqlite:////opt/ownex/data/database/cateye.db
ExecStart=/opt/ownex/.venv/bin/python -m api.main --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target

# Enable
sudo systemctl enable --now ownex-backend
```

### Frontend (Vite dev / nginx prod)

```bash
# Dev
cd frontend && npm run dev

# Prod (nginx)
# /etc/nginx/sites-available/ownex
server {
    listen 80;
    server_name ownex.local;
    root /opt/ownex/frontend/dist;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### Desktop Sidecar (Tauri)

Managed automatically by Tauri:
- Spawns on app start
- Health checks every 5s
- Auto-restart on failure
- Stops on app quit

### Ollama

```bash
# Install (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Start service
systemctl enable --now ollama

# Pull model
ollama pull qwen2.5:3b-instruct

# Verify
curl http://localhost:11434/api/tags
```

### FCC Proxy

```bash
# From free-claude-code repo
cd ~/free-claude-code
source .venv/bin/activate
python -m free_claude_code --port 8082

# Or via orion command
orion proxy start
```

### OmniRoute

```bash
# Configured via ~/.config/omniroute/config.yaml
# Runs on port 20128
```

## Monitoring

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Basic liveness |
| `GET /api/system/status` | Detailed: memory, CPU, DB, agents, pipeline |
| `GET /api/version` | Version info |
| `GET /api/metrics` | Prometheus metrics |

### Key Metrics (Prometheus)

```
ownex_http_requests_total{method, path, status}
ownex_http_request_duration_seconds{method, path}
ownex_db_size_mb
ownex_memory_rss_mb
ownex_cpu_percent
ownex_active_scans
ownex_findings_total
ownex_revenue_usd_per_hour
ownex_ai_daily_spend_usd
ownex_sync_latency_seconds
ownex_watch_sync_failures_total
```

### Log Locations

| Component | Location |
|-----------|----------|
| Backend | `$CATEYE_DATA_DIR/logs/ownex-api.log` |
| Desktop | `%LOCALAPPDATA%/OWNEX/logs/ownex-api.log` |
| Frontend | Browser DevTools Console |
| Tauri | `%LOCALAPPDATA%/OWNEX/logs/tauri.log` |
| Hermes | `~/.hermes/logs/` |
| Ollama | `journalctl -u ollama` |

### Structured Logging

```json
{
  "timestamp": "2026-08-27T10:30:00.123Z",
  "level": "INFO",
  "logger": "ownex.api",
  "message": "Finding validated",
  "finding_id": "fnd_abc123",
  "target_id": "tgt_xyz789",
  "severity": "high",
  "platform": "hackerone"
}
```

## Database Operations

### Backup

```bash
# Automatic (run.py)
python run.py --backup

# Manual
cp $CATEYE_DATA_DIR/database/cateye.db $CATEYE_DATA_DIR/backups/cateye_$(date +%Y%m%d_%H%M%S).db

# With WAL checkpoint
sqlite3 $CATEYE_DATA_DIR/database/cateye.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

### Restore

```bash
# Stop backend first!
cp $CATEYE_DATA_DIR/backups/cateye_20260827_103000.db $CATEYE_DATA_DIR/database/cateye.db
# Restart backend
```

### Migration (PC to PC)

```bash
# Export
python run.py --migrate-export [output.zip]
# --no-targets excludes ~/.orion/targets (4GB+)

# Import
python run.py --migrate backup.zip --force
# Verifies checksums, preserves IdentityVault key
```

### Vacuum/Analyze

```bash
sqlite3 $CATEYE_DATA_DIR/database/cateye.db "VACUUM; ANALYZE;"
```

## Scheduler Operations

### Job Management

```bash
# List all jobs
python -c "from core.scheduler.jobs import get_all_jobs; import json; print(json.dumps(get_all_jobs(), indent=2))"

# Run specific job manually
python -c "from core.scheduler.tasks import run_qa_cycle; import asyncio; asyncio.run(run_qa_cycle())"

# Check scheduler status
curl http://localhost:8000/api/system/status | jq .scheduler
```

### Key Jobs

| Job | Cron | Purpose |
|-----|------|---------|
| `advance_security_pipeline` | `*/30 * * * *` | Runs security pipeline |
| `work_bank_daily_cycle` | `15 6 * * *` | Daily work discovery |
| `financial_sync` | `*/30 * * * *` | Syncs platform payouts |
| `knowledge_sync_daily` | `30 6 * * *` | Obsidian vault sync |
| `trading_risk_check` | `*/5 * * * *` | Copy trading risk |
| `delivery_preparation` | `0 8 * * *` | Prepares deliveries |

## AI Operations

### Provider Health

```bash
# Check all providers
curl http://localhost:20128/v1/models  # OmniRoute
curl http://localhost:8082/v1/models   # FCC Proxy
curl http://localhost:11434/api/tags   # Ollama

# OAR status
curl http://localhost:8000/api/oar/status
```

### Cost Monitoring

```bash
# Daily spend
curl http://localhost:8000/api/oar/status | jq .cost_tracker.daily_spend_usd

# Budget config
curl http://localhost:8000/api/oar/status | jq .config.daily_budget_usd
```

### Model Management

```bash
# Ollama
ollama list
ollama pull qwen2.5:3b-instruct
ollama rm unused-model

# FCC Proxy (via OmniRoute)
# Models auto-discovered from OpenRouter
```

## Security Operations

### Certificate Management

```bash
# TLS for mobile (self-signed, pinned)
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes

# Rotate IdentityVault key (emergency only)
# 1. Backup current key
cp ~/.ownex/identity_vault.key ~/.ownex/identity_vault.key.bak
# 2. Generate new
python -c "from cores.identity_vault import rotate_key; rotate_key()"
# 3. Re-encrypt all vaults (automatic on next access)
```

### Credential Rotation

```bash
# API keys (manual via UI or API)
curl -X POST http://localhost:8000/api/credentials/rotate \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"platform": "hackerone", "new_key": "..."}'

# Scheduled: credentials_rotation job runs daily
```

### Audit Logs

```bash
# View recent security events
tail -100 $CATEYE_DATA_DIR/logs/audit.log | jq .

# Filter by event
grep '"event":"login"' $CATEYE_DATA_DIR/logs/audit.log | tail -20
```

## Performance Tuning

### Database

```bash
# Indexes (check query plans)
sqlite3 $CATEYE_DATA_DIR/database/cateye.db ".schema" | grep INDEX

# Vacuum (monthly)
sqlite3 $CATEYE_DATA_DIR/database/cateye.db "VACUUM;"

# Analyze stats
sqlite3 $CATEYE_DATA_DIR/database/cateye.db "ANALYZE;"
```

### Memory

```bash
# Backend memory limit (systemd)
MemoryLimit=2G

# Python GC tuning
export PYTHONGC=1
export PYTHONMALLOC=debug
```

### Frontend Bundle

```bash
# Analyze bundle
cd frontend && npm run build -- --mode=analyze

# Target: < 500KB initial JS, < 2MB total
```

## Troubleshooting Quick Reference

| Symptom | Check | Fix |
|---------|-------|-----|
| Backend won't start | Port 8000 in use? | `lsof -i :8000` |
| Frontend 404 on refresh | nginx try_files? | `try_files $uri $uri/ /index.html;` |
| Desktop "Backend not responding" | Sidecar health? | Tray → Restart Backend |
| Mobile can't connect | Firewall port 8000? | `ufw allow 8000` |
| Ollama not found | Service running? | `systemctl status ollama` |
| FCC 404 on models | Provider keys? | Check OmniRoute/OpenRouter keys |
| Database locked | Multiple backends? | `pkill -f api.main` |
| FCM not working | google-services.json? | Check `android/app/google-services.json` |

## Maintenance Schedule

| Frequency | Task |
|-----------|------|
| Daily | Check `/api/health`, review audit logs |
| Weekly | Vacuum DB, review AI costs, rotate logs |
| Monthly | Vacuum DB, update dependencies, security scan |
| Quarterly | Rotate API keys, review access, disaster recovery test |

## Disaster Recovery

### RTO/RPO Targets
- **RTO**: 15 minutes (restart services)
- **RPO**: 1 hour (DB backup frequency)

### Recovery Procedure
1. Provision new server
2. Restore DB from latest backup
3. Restore config files
4. Start services
5. Verify health endpoints
6. Update DNS/load balancer

---

*Document generated from codebase. Last verified: 2026-08-27*