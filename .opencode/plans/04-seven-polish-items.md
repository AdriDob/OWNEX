# 7 Detalles de Lujo — Plan Completo

## Orden de implementación

Dependencias: backup (run.py) y dashboard (api router) necesitan registrarse. Todo lo demás es independiente.

---

## 1. Finding Notes (~30 min)

**Archivos**: `database/models.py` → `database/db.py` → `api/routers/findings.py`

Agregar columna `notes` al modelo Finding:
```python
# models.py — después de vulnerability_type
notes = Column(Text, nullable=True, default="")
```

Migración en `db.py`:
```python
_migrate_columns(session, "findings", [
    ("notes", "TEXT DEFAULT ''"),
])
```

Endpoint `PATCH /api/findings/{finding_id}` en `findings.py`:
```python
@router.patch("/{finding_id}")
async def update_finding(finding_id: int, body: FindingUpdate, db: Session = Depends(get_db)):
    finding = db.query(models.Finding).filter(models.Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(404)
    if body.notes is not None:
        finding.notes = body.notes
    if body.status is not None:
        finding.status = body.status
    db.commit()
    return finding_to_dict(finding)
```

Pydantic model `FindingUpdate` con `notes: str | None = None` y `status: str | None = None`.

Incluir `notes` en `_finding_to_dict()`.

---

## 2. FP Feedback Loop (~20 min)

**Archivos**: `api/main.py` (nuevo subscriber)

Cuando un finding cambia a `"rejected"`, alimentar FeedbackLearner.

En `api/main.py` startup, agregar:
```python
from cores.validation.llm_analyzer import FeedbackLearner

def _on_finding_status_changed(event_data: dict):
    new_status = event_data.get("new_status", "")
    if new_status == "rejected":
        finding_id = event_data.get("finding_id")
        try:
            learner = FeedbackLearner()
            # Gather feedback events related to this finding
            learner.analyze_verdict_patterns()
        except Exception as e:
            logger.warning("FeedbackLearner error: %s", e)

get_event_bus().subscribe("finding:status_changed", _on_finding_status_changed)
```

La función `handle_finding_status_change` en `api/routers/findings.py` ya publica el evento. Solo falta el subscriber.

---

## 3. One-command Backup (~45 min)

**Archivos nuevos**: `cores/backup.py`
**Archivos modificados**: `run.py`

### cores/backup.py

```python
"""Backup and restore for CATEYE data."""
import json
import logging
import shutil
import tarfile
import tempfile
import time
from pathlib import Path

logger = logging.getLogger("cateye.backup")

ORION_DIR = Path.home() / ".orion"

BACKUP_PATHS = [
    "catseye.db",
    "config.json",
    "audit.jsonl",
    "identity_vault.key",
    "evidence/",
]

def create_backup(output_dir: str | None = None) -> Path | None:
    dest = Path(output_dir or ORION_DIR)
    dest.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    archive = dest / f"cateye_backup_{timestamp}.tar.gz"

    with tarfile.open(archive, "w:gz") as tar:
        for rel_path in BACKUP_PATHS:
            full = ORION_DIR / rel_path
            if full.exists():
                tar.add(full, arcname=rel_path)
                logger.info("Backup: added %s", rel_path)
    logger.info("Backup created: %s (%d bytes)", archive, archive.stat().st_size)
    return archive


def restore_backup(archive_path: str) -> bool:
    archive = Path(archive_path)
    if not archive.exists():
        logger.error("Backup not found: %s", archive_path)
        return False
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(path=ORION_DIR, filter="data")
    logger.info("Restored from %s", archive_path)
    return True
```

### run.py

Agregar flags:
```python
parser.add_argument("--backup", nargs="?", const="auto", help="Create backup (optional output dir)")
parser.add_argument("--restore", type=str, help="Restore from backup file")
```

En `main()`:
```python
if args.backup:
    from cores.backup import create_backup
    out = None if args.backup == "auto" else args.backup
    path = create_backup(out)
    if path:
        print(f"✅ Backup created: {path}")
    return

if args.restore:
    from cores.backup import restore_backup
    if restore_backup(args.restore):
        print("✅ Restored successfully")
    else:
        print("❌ Restore failed")
    return
```

---

## 4. Hunter Dashboard (~1 hr)

**Archivo nuevo**: `api/routers/hunter.py`

```python
"""Hunter dashboard — single endpoint for daily bug bounty overview."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import db, models
from cores.intelligence.reward_learning import RewardLearner

router = APIRouter(prefix="/api/hunter", tags=["hunter"])

@router.get("/summary")
def hunter_summary(session: Session = Depends(db.get_db)):
    # Active targets
    target_count = session.query(models.Target).count()
    
    # Pending findings (open, not rejected)
    pending = session.query(models.Finding).filter(
        models.Finding.status == "open"
    ).count()
    confirmed = session.query(models.Finding).filter(
        models.Finding.status == "confirmed"
    ).count()
    
    # Recent reports (last 30 days)
    from datetime import datetime, timedelta
    from database.models import Report
    month_ago = datetime.utcnow() - timedelta(days=30)
    monthly_reports = session.query(Report).filter(
        Report.created_at >= month_ago
    ).count()
    
    # Payouts
    learner = RewardLearner()
    reward_report = learner.analyze()
    total_confirmed = reward_report.total_confirmed_value if reward_report else 0.0
    total_estimated = sum(
        r.estimated_reward or 0.0 for r in session.query(Report).all()
    )
    
    return {
        "active_targets": target_count,
        "pending_findings": pending,
        "confirmed_findings": confirmed,
        "reports_this_month": monthly_reports,
        "total_confirmed_payout": round(total_confirmed, 2),
        "total_estimated_payout": round(total_estimated, 2),
        "currency": "USD",
    }
```

Registrar en `api/main.py`:
```python
from api.routers.hunter import router as hunter_router
app.include_router(hunter_router)
```

---

## 5. CLI Quick-Add Target (~30 min)

**Archivo**: `run.py`

```python
parser.add_argument("--add-target", type=str, help="Quick-add a target by name")
parser.add_argument("--domain", type=str, help="Target domain (for --add-target)")
```

En `main()`:
```python
if args.add_target:
    from database import db, models
    db.init_db()
    session = db.SessionLocal()
    try:
        target = models.Target(name=args.add_target, domain=args.domain or "")
        session.add(target)
        session.commit()
        print(f"✅ Target '{args.add_target}' created (id={target.id})")
    finally:
        session.close()
    return
```

---

## 6. Report Templates (~45 min)

**Archivos**: `cores/reporting/export_formats.py`

Modificar `ExportFormats.__init__()` para buscar templates primero en `~/.orion/templates/`, fallback a los built-in:

```python
import shutil
from pathlib import Path

USER_TEMPLATES_DIR = Path.home() / ".orion" / "templates"

def ensure_default_templates():
    """Copy built-in templates to user dir on first run."""
    if not USER_TEMPLATES_DIR.exists():
        USER_TEMPLATES_DIR.mkdir(parents=True)
        built_in = Path(__file__).parent / "templates"
        if built_in.exists():
            shutil.copytree(built_in, USER_TEMPLATES_DIR, dirs_exist_ok=True)
            logger.info("Copied default templates to %s", USER_TEMPLATES_DIR)

class ExportFormats:
    def __init__(self):
        ensure_default_templates()
        env = Environment(
            loader=FileSystemLoader(str(USER_TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        ...
```

---

## 7. Session Retry Mid-Validation (~30 min)

**Archivo**: `cores/validation/replayer.py`

Modificar `execute()`:
```python
def execute(self, request_spec, auth: AuthContext):
    # Normal execution
    try:
        resp = requests.request(...)
        if resp.status_code in (401, 403) and auth.token:
            # Session may have expired — try to refresh
            refreshed = self._try_refresh_auth(auth)
            if refreshed:
                auth = refreshed
                resp = requests.request(...)
        ...
```

Agregar `_try_refresh_auth()`:
```python
def _try_refresh_auth(self, auth: AuthContext) -> AuthContext | None:
    """If auth failed with 401/403, try to refresh the session."""
    try:
        from cores.target_auth.session_resolver import get_session_resolver
        resolver = get_session_resolver()
        # We need the identity_id — stored in auth.label
        if auth.label and auth.label.startswith("identity_"):
            identity_id = int(auth.label.split("_")[1])
            ctx = resolver.resolve(identity_id)
            if ctx:
                logger.info("Auth refreshed for %s", auth.label)
                return AuthContext(
                    token=ctx.get("token"),
                    cookies=ctx.get("cookies", {}),
                    headers=ctx.get("headers", {}),
                    label=auth.label,
                )
    except Exception as e:
        logger.warning("Auth refresh failed: %s", e)
    return None
```

---

## Resumen

| # | Feature | Archivos | Líneas estimadas | Dependencia |
|---|---|---|---|---|
| 1 | Finding Notes | models.py, db.py, findings.py | ~30 | Ninguna |
| 2 | FP Feedback Loop | main.py | ~20 | #1 (finding status) |
| 3 | Backup CLI | cores/backup.py (nuevo), run.py | ~80 | Ninguna |
| 4 | Hunter Dashboard | api/routers/hunter.py (nuevo), main.py | ~50 | Ninguna |
| 5 | CLI Quick-Add | run.py | ~20 | Ninguna |
| 6 | Report Templates | export_formats.py | ~25 | Ninguna |
| 7 | Session Retry | replayer.py | ~25 | Ninguna |
| | **Total** | **10 archivos** | **~250** | |

## Verificación

1. `pytest --timeout=60 -q` — todos verdes
2. `ruff check .` — clean
3. `python run.py --backup` → `cateye_backup_20260709_120000.tar.gz`
4. `python run.py --add-target "Test" --domain test.com` → target creado
5. `curl localhost:8000/api/hunter/summary` → JSON con métricas
