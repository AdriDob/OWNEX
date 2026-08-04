# Backup and Recovery

> Version 4.6.0 — Julio 2026

## 1. What to Backup

All critical data is stored under `~/.orion/`. The backup system (`cores/backup.py`) backs up the following paths:

| Path | Description | Criticality |
|---|---|---|
| `~/.orion/catseye.db` | Main SQLite database — targets, findings, reports, users, events, settings | Critical |
| `~/.orion/config.json` | User configuration | High |
| `~/.orion/audit.jsonl` | Security audit log | High |
| `~/.orion/identity_vault.key` | AES-256-GCM encryption key (32 bytes, random) | Critical |
| `~/.orion/evidence/` | Uploaded evidence files (screenshots, proofs) | Medium |

### App Databases

ORION Platform apps maintain their own SQLite databases:

| App | Path |
|---|---|
| ATLAS | `~/.orion/data/atlas.db` |
| ODYSSEY | `~/.orion/data/odyssey.db` |
| Recovery Engine | `~/.orion/data/recovery_history.db` |

These are NOT currently included in the automatic backup command. For a complete backup, include the entire `~/.orion/` directory.

### What is NOT Backed Up

- `node_modules/` and `.venv/` — can be recreated via `npm install` / `pip install`
- Compiled frontend assets — can be rebuilt via `npm run build`
- Desktop builds in `dist/` — can be rebuilt via PyInstaller
- Log files in `logs/` — non-critical, regenerated on restart

## 2. Backup Command

### Interactive Backup

```bash
python run.py --backup
```

This creates a timestamped tar.gz archive at `~/.orion/cateye_backup_YYYYMMDD_HHMMSS.tar.gz` containing all critical paths listed above.

### Custom Output Directory

```bash
python run.py --backup /path/to/backup/dir
```

### Manual Backup

```bash
# Full backup of all ORION data
tar czf ~/cateye_full_backup_$(date +%Y%m%d).tar.gz ~/.orion/
```

### Backup Code (`cores/backup.py`)

```python
BACKUP_PATHS = [
    "catseye.db",
    "config.json",
    "audit.jsonl",
    "identity_vault.key",
    "evidence/",
]


def create_backup(output_dir: str | None = None) -> Path | None:
    dest = Path(output_dir) if output_dir else ORION_DIR
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    archive = dest / f"cateye_backup_{timestamp}.tar.gz"

    with tarfile.open(archive, "w:gz") as tar:
        for rel_path in BACKUP_PATHS:
            full = ORION_DIR / rel_path
            if full.exists():
                tar.add(full, arcname=rel_path)
    return archive
```

## 3. Restore Procedure

### From Backup Command

```bash
python run.py --restore /path/to/backup/cateye_backup_20260710_120000.tar.gz
```

### Manual Restore

```bash
# Stop the backend first
# Extract backup to ~/.orion/
tar xzf /path/to/backup/cateye_backup_20260710_120000.tar.gz -C ~/.orion/
# Restart the backend
```

### Important Notes

1. **Stop the backend** before restoring to prevent database corruption
2. **Check disk space** — the restore extracts files in-place
3. **Verify file permissions** — `identity_vault.key` must be `chmod 600`
4. **Database migrations**: If the backup was created with an older version, run `python run.py` after restore to apply any pending migrations
5. **Restart required**: Always restart the backend after restore to reload cached state

## 4. WAL Checkpoint

SQLite uses Write-Ahead Logging (WAL) for concurrent reads. The WAL file (`catseye.db-wal`) can grow unboundedly on 24/7 systems.

### Automatic Checkpoint

The scheduler (`api/scheduler.py`) runs a WAL checkpoint at the end of every pipeline cycle:

```python
# api/scheduler.py:109-113
with db.SessionLocal() as sess:
    sess.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
```

### Manual Checkpoint

```python
from sqlalchemy import text
from database.db import SessionLocal

session = SessionLocal()
session.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
session.commit()
session.close()
```

### WAL Configuration

Set at database initialization (`database/db.py`):

```python
PRAGMA journal_mode=WAL
PRAGMA busy_timeout=5000
PRAGMA synchronous=NORMAL
```

## 5. Audit Log Rotation

The audit log (`~/.orion/audit.jsonl`) rotates automatically at 10MB:

```python
# cores/audit_log.py:43-50
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 3

if os.path.exists(path) and os.path.getsize(path) > _MAX_BYTES:
    # Rotate: .1 -> .2, .2 -> .3, current -> .1
    for i in range(_BACKUP_COUNT - 1, 0, -1):
        src = f"{path}.{i}"
        dst = f"{path}.{i + 1}"
        if os.path.exists(src):
            shutil.move(src, dst)
    shutil.move(path, f"{path}.1")
```

After rotation, the active log continues at `audit.jsonl` with the oldest backups at `.3`.

## 6. Recovery Engine

The Recovery Engine (`cores/recovery/engine.py`) provides automated failure detection, diagnosis, and recovery.

### Architecture

```
+------------------+     +------------------+
|   HealthMonitor  | --> |  RecoveryEngine  |
| (periodic checks)|     | (failure handler)|
+------------------+     +------------------+
         |                       |
         v                       v
+------------------+     +------------------+
|  Health Checks   |     |  Healing Rules   |
| - eventbus alive |     | - eventbus_stuck |
| - agent bus      |     | - agent_crashed  |
| - agents running |     | - db_lock        |
| - database OK    |     | - memory_leak    |
| - memory usage   |     | - pipeline_stall |
+------------------+     +------------------+
         |                       |
         v                       v
+------------------+     +------------------+
| CircuitBreaker   |     | RecoveryStore    |
| - max 3 failures |     | (SQLite persist) |
| - 60s cooldown   |     | - recovery_events|
| - half-open retry|     | - health_snapshots|
+------------------+     +------------------+
```

### Circuit Breaker (`cores/recovery/circuit_breaker.py`)

- **States**: `CLOSED` (normal), `OPEN` (failing), `HALF_OPEN` (cooldown expired, testing)
- **Threshold**: Max 3 failures before opening
- **Cooldown**: 60 seconds before transitioning to half-open
- **Persistence**: State persisted to `RecoveryStore` SQLite, restored on startup

### Healing Rules (`cores/recovery/healing_rules.py`)

13 predefined failure types each mapped to a recovery action:

| Failure Type | Recovery Action | Priority |
|---|---|---|
| `eventbus_stuck` | `reset_event_bus` | 1 |
| `eventbus_dead` | `restart_agent_bus` | 1 |
| `agent_crashed` | `restart_agent` | 1 |
| `agent_unresponsive` | `restart_agent` | 2 |
| `scheduler_dead` | `restart_scheduler` | 1 |
| `pipeline_corrupt` | `restore_last_valid_state` | 1 |
| `pipeline_stalled` | `retry_pipeline` | 2 |
| `db_lock` | `reopen_db_connection` | 1 |
| `db_connection_lost` | `reopen_db_connection` | 1 |
| `memory_leak` | `trim_memory_history` | 2 |
| `memory_corrupt` | `reset_memory_store` | 2 |
| `watchdog_stalled` | `restart_watchdog` | 1 |
| `api_unresponsive` | `restart_api_server` | 1 |

### RecoveryStore (`cores/recovery/persistence.py`)

SQLite-backed persistence for recovery history:

- **Tables**: `recovery_events`, `circuit_breaker_state`, `learning_state`, `health_snapshots`
- **Health snapshots**: Persisted for historical analysis, queryable via `get_health_snapshots()`
- **Path**: `~/.orion/data/recovery_history.db`

### HealthMonitor (`cores/recovery/health_monitor.py`)

Periodic background thread that checks:

- EventBus alive (publishes a test event)
- Agent bus initialized
- All agents running
- Database connectivity (`SELECT 1`)
- Memory usage (psutil, threshold 80%)

Failed checks are reported to the RecoveryEngine, which applies the appropriate healing rule.

## 7. Persistence Verification

The following subsystems persist state to SQLite and survive restarts:

### EventBus History

`cores/events/event_bus.py` writes every published event to the `event_bus_entries` table. On restart, `get_history()` reads from the database.

```python
# Verified: events published before restart are available after restart
history = bus.get_history(limit=10)
assert len(history) > 0  # contains events from previous sessions
```

### SystemState

`cores/system_state.py` persists the latest state snapshot to the `system_state_records` table. On restart, the last-known state is restored:

```python
saved = _load_state()  # reads from SystemStateRecord table
if saved:
    self._system_state = saved["state"]  # BOOTING / READY / DEGRADED / FAILED
```

### Ledger

`cores/ledger/` (via `LedgerEntry` model) persists all financial ledger entries. The dashboard reads from the database on every request.

### Notification Dedup

`cores/notifications/hub.py` rehydrates the dedup cache from recent DB notifications on restart (`DEDUP_WINDOW=30s`).

### Financial TruthLayer

`cores/financial/truth_layer.py` persists verified/pending/withdrawn balances via `LedgerEntry`. Survives restart with full history.

## 8. Disaster Recovery Checklist

1. **Stop backend**: Kill the Python process running the API
2. **Verify backup exists**: Check `ls -la ~/.orion/cateye_backup_*.tar.gz`
3. **Check disk**: Ensure enough space for restore (`du -sh ~/.orion/`)
4. **Restore**: `python run.py --restore <backup_file>`
5. **Verify key permissions**: `ls -la ~/.orion/identity_vault.key` (must be `-rw-------`)
6. **Verify database integrity**: `sqlite3 ~/.orion/catseye.db "PRAGMA integrity_check;"`
7. **Start backend**: `python run.py --browser`
8. **Check health**: `curl http://localhost:8000/api/health`
9. **Verify data**: Check that findings, targets, and settings are intact
