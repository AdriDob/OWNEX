# OWNEX Troubleshooting Guide

> **Generated from actual codebase** — This document reflects the real implementation.

## Organization

Organized by **symptom** → **likely cause** → **check** → **fix** → **verification**.

---

## Backend Issues

### Backend Won't Start

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| `Address already in use` | Port 8000 occupied | `lsof -i :8000` or `netstat -an \| findstr 8000` | Kill process: `kill -9 <PID>` or `taskkill /f /pid <PID>` | `curl http://localhost:8000/api/health` → 200 |
| `ModuleNotFoundError` | Venv not activated | `which python` | `source .venv/bin/activate` | `python -c "import api.main"` |
| `Database locked` | Multiple backends | `ps aux \| grep api.main` | Kill all, restart one | `curl /api/health` → 200 |
| `SystemExit(2)` on import | pytest argv consumed | Check `api/main.py:207` uses `parse_known_args()` | Already fixed in 7.0.0 | `import api.main` works in pytest |

### Health Endpoint Fails

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| 500 on `/api/health` | DB migration needed | Logs show `OperationalError` | Run `python -m api.main` (auto-migrates) | 200 with `{"status":"ok"}` |
| 503 Service Unavailable | Sidecar not ready | Desktop: wait 60-90s | Wait or Tray → Restart Backend | 200 |
| Timeout | `discover_all` hanging | Logs show "Starting discover" | Increase timeout in `api/main.py:258` | 200 within timeout |

### Database Issues

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| `OperationalError: no such table` | Schema not initialized | `sqlite3 db.sqlite .schema \| head` | Run `python -c "from database.db import init_db; init_db()"` | Tables exist |
| `OperationalError: database is locked` | WAL files stale | `ls -la database/*.db*` | Delete `-wal`, `-shm` files | Backend starts |
| `IntegrityError: UNIQUE constraint` | Duplicate insert | Check deduplication logic | Use `ON CONFLICT` or check before insert | Insert succeeds |

---

## Frontend Issues

### Build Failures

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| `vue-tsc` errors | Type mismatches | `npx vue-tsc --noEmit` | Fix types, add `@ts-expect-error` if needed | 0 errors |
| `vite build` fails | Missing dependency | Error shows missing import | `npm install <pkg>` | Build succeeds |
| `Single file component can contain only one <script setup>` | Duplicate script blocks | Open `.vue` file | Merge into one `<script setup>` | Build succeeds |
| `export 'X' not found` | Wrong import path | Check `src/services/ownexData.ts` exports | Add missing export | Import resolves |

### Runtime Errors

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| White screen | JS error in mount | Browser Console | Fix error, refresh | App loads |
| "Backend not responding" | Sidecar not healthy | Network tab: `/api/health` fails | Tray → Restart Backend | Health → 200 |
| WebSocket fails | CSP blocks `ws://` | Network tab: WS 403/404 | Add `ws://localhost:*` to CSP in `tauri.conf.json` | WS connects |
| 401 on API calls | Token expired | `localStorage.getItem('CATEYE-token')` | Re-login or check cookie | Auth works |
| CORS error | Wrong origin | Network tab: CORS error | Check `configure_cors()` in `api/main.py` | Request succeeds |

---

## Desktop (Tauri) Issues

### App Won't Launch

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| Splash shows, then closes | Sidecar crash | `%LOCALAPPDATA%\OWNEX\logs\ownex-api.log` | Fix backend error, restart | Window stays open |
| "Backend not responding" indefinitely | Sidecar health check failing | Logs: "Health check failed" | Fix backend, Tray → Restart Backend | Mission Control shows data |
| White window | Frontend not loaded | DevTools: blank page | Rebuild frontend: `npm run build` | UI renders |
| App won't close | Sidecar orphan | Task Manager: `ownex-backend.exe` running | Kill process, restart app | Clean restart |

### Database Issues

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| "Ops: error" on Dashboard | `no such table: targets` | Logs show SQLite error | Fixed in 7.0.0: `_ensure_db_dir()` at module level | Dashboard loads |
| Data lost on reinstall | DB in app folder | Check `%LOCALAPPDATA%\OWNEX\database\` | Fixed: DB now in `%LOCALAPPDATA%\OWNEX\database\` | Data persists |

### Sidecar Issues

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| Sidecar won't start | `ownex-backend.exe` missing | Check bundle resources | Rebuild with `pyinstaller OWNEX-Backend.spec` | Sidecar starts |
| Port conflict | Dev backend on 8000 | `netstat -an \| findstr 8000` | Sidecar reuses existing (dev mode) | No conflict |
| High memory | Memory leak | Task Manager > 500MB | Restart backend, check for leaks | Stable < 300MB |

---

## Mobile Issues

### Connection

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| "Cannot connect to desktop" | Wrong IP | Phone IP vs Desktop IP | Use `ipconfig` (Win) / `ifconfig` (Linux) | Mobile loads dashboard |
| "Network error" | Firewall blocks 8000 | `ufw status` / Windows Firewall | Allow port 8000 | Mobile connects |
| WebSocket fails | Cleartext HTTP | `capacitor.config.json: cleartext: false` | Use HTTPS or set `cleartext: true` for dev | WS connects |

### Push Notifications

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| Notifications not received | FCM token not registered | Logcat: "FCM token" | Check `google-services.json` in `android/app/` | Token sent to backend |
| Notifications delayed | Battery optimization | Android Settings > Battery | Whitelist app | Instant delivery |
| Duplicate notifications | Multiple registrations | Backend logs | Deduplicate FCM token on register | Single notification |

### Biometric Auth

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| "Biometric not available" | No fingerprint/face enrolled | Android Settings > Security | Enroll biometric | Auth works |
| Fallback to PIN not shown | `cancelTitle` missing | `BiometricAuth.authenticate()` options | Add `cancelTitle: 'Use PIN'` | PIN fallback works |

---

## Watch (Wear OS) Issues

### Sync

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| Watch not receiving notifications | Data Layer permission | Phone: Settings > Apps > OWNEX > Permissions | Enable "Nearby devices" | Notifications appear |
| Approvals not syncing | Data Layer cache stale | Phone app: "Sync Watch" button | Clear Data Layer cache, re-pair | Approvals sync |
| Complications not updating | `ComplicationDataSourceService` not running | Watch: Settings > Apps > OWNEX | Reinstall watch app | Complications update |

### Battery

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| High battery drain | Complications updating too often | Watch battery stats | Reduce complication update frequency | < 5%/day |
| Wake lock held | `WAKE_LOCK` permission | `dumpsys batterystats` | Only acquire during interaction | Normal drain |

---

## AI / OAR Issues

### Provider Errors

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| "Provider returned empty stream" | OmniRoute SSE issue | `curl http://localhost:20128/v1/models` | Use FCC fallback, check OmniRoute logs | Response received |
| 404 on FCC models | NIM model deprecated | `curl http://localhost:8082/v1/models` | Use working model: `claude-sonnet-4-20250514` | Model responds |
| Ollama not found | Service not running | `systemctl status ollama` | `systemctl start ollama` | `ollama list` shows models |
| Circuit breaker open | 3+ failures | OAR logs: "Circuit open" | Wait 60s or restart backend | Provider available |

### Cost/Budget

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| "Budget exceeded" | `daily_budget_usd` too low | `curl /api/oar/status \| jq .cost_tracker` | Increase budget or use free providers | Requests allowed |
| High costs | Using paid models | OAR logs show provider | Set `prefer_free: true`, `daily_budget_usd: 0` | Costs near $0 |

---

## Scheduler / Pipeline Issues

### Jobs Not Running

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| Jobs not executing | Scheduler not started | Logs: "CoreScheduler started" | Check `api/main.py` lifespan | `curl /api/system/status \| jq .scheduler` |
| Handler not found | Wrong dotted path | `core/scheduler/jobs.py` handler strings | Use `module:attr` or `module.Class.method` | Job runs |
| Stale scans | `recover_stale_scans` not running | Logs at boot | Fixed: runs in lifespan + scheduler tick | Scans marked failed |

### Pipeline Stuck

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| Stage never completes | Stage executor error | `core/cycles/stages/` logs | Fix executor, restart pipeline | Stage advances |
| Findings not promoting | Validation threshold | `cores/validation/gate.py` threshold | Adjust or check evidence | Promotion works |

---

## Security / Auth Issues

### CSRF

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| 403 on POST | Missing CSRF token | Network tab: `X-CSRF-Token` header | Ensure cookie + header sent | Request succeeds |
| 403 on WebSocket | CSRF middleware blocks | `api/middleware/csrf_middleware.py` exempt | WebSocket scope bypasses CSRF | WS connects |

### Rate Limiting

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| 429 Too Many Requests | Burst exceeded | `X-RateLimit-Remaining: 0` | Wait or increase burst | Request succeeds after wait |
| Legitimate requests blocked | `NO_LIMIT_PREFIXES` missing | Check `rate_limit_middleware.py` | Add path to `NO_LIMIT_PREFIXES` | Request allowed |

### Authentication

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| 401 Unauthorized | Token expired | JWT `exp` claim | Re-login or refresh token | New token works |
| Cookie not sent | `SameSite=Lax` + cross-origin | Dev: localhost vs tauri.localhost | Set `OWNEX_DESKTOP=1` for dev | Cookie sent |

---

## Data / Sync Issues

### Mobile/Watch Sync

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| Data stale | Background sync not running | Mobile: last sync time | Enable background runner, check FCM | Sync completes |
| Conflict on sync | Same record edited both sides | Server timestamps | Server wins (LWW) | Data consistent |
| Offline actions lost | Outbox not flushed | IndexedDB `outbox` table | Reconnect network, wait | Actions synced |

### Backup/Restore

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| Restore fails | Destination not empty | `python run.py --migrate backup.zip` | Use `--force` flag | Restore succeeds |
| Key mismatch | IdentityVault key changed | `identity_vault.key` vs backup | Backup preserves key as `.bak` | Vault decrypts |

---

## Performance Issues

### Slow Backend

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| High latency | N+1 queries | `/api/metrics` shows slow queries | Add eager loading, indexes | Latency < 200ms |
| High memory | Memory leak | `ps aux \| grep python` | Restart, profile with `objgraph` | Stable < 300MB |
| CPU spike | Scheduler busy loop | `top -p <pid>` | Check `CoreScheduler` loop interval | CPU < 10% idle |

### Slow Frontend

| Symptom | Likely Cause | Check | Fix | Verification |
|---------|--------------|-------|-----|--------------|
| Slow initial load | Large bundle | `vite build --mode=analyze` | Code split, lazy routes | < 3s FCP |
| Janky animations | Layout thrashing | DevTools Performance | Use `transform` not `top/left` | 60fps |

---

## Emergency Procedures

### Complete Reset (Nuclear Option)

```bash
# 1. Stop all
pkill -f "api.main"
pkill -f "ownex-backend"
pkill -f "tauri"

# 2. Backup data
cp -r %LOCALAPPDATA%\OWNEX %LOCALAPPDATA%\OWNEX_BAK_$(date +%Y%m%d)

# 3. Clean install
rm -rf %LOCALAPPDATA%\OWNEX
# Reinstall from MSI

# 4. Restore data if needed
cp %LOCALAPPDATA%\OWNEX_BAK_\database\cateye.db %LOCALAPPDATA%\OWNEX\database\
```

### Data Recovery

```bash
# Corrupted SQLite
sqlite3 cateye.db ".recover" > recovered.sql
sqlite3 new.db < recovered.sql

# WAL recovery
sqlite3 cateye.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

---

*Document generated from codebase. Last verified: 2026-08-27*