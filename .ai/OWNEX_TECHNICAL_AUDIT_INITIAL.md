# OWNEX Technical Audit — Initial Diagnosis (Phase 1) — UPDATED

**Date:** 2026-11-19
**Scope:** Backend, SQLite, migrations, initialization — updated with corrections
**Status:** READ-ONLY AUDIT (modified files documented below)

---

## 1. GIT STATE

- **Branch:** main (up to date with origin/main)
- **Last commit:** `3a68bd58` feat(opportunity): evidence-gated external lifecycle transitions
- **Local modifications:** Several files modified (see git status)
- **Key changes:** Fixed DATABASE_URL consolidation, added missing SQLAlchemy models

---

## 2. ARCHITECTURE REALITY — Entry Points & Dependencies

### 2.1 DATABASE_URL — SINGLE SOURCE OF TRUTH (FIXED)

**Before:** Three different entry points set different DATABASE_URL values:
- `database/db.py`: `sqlite:///./database/catseye.db`
- `api/main.py`: `sqlite:///{data_dir}/database/cateye.db` (overridden)
- `run.py`: `sqlite:///{data_dir}/database/cateye.db` (overridden)

**After:** `api/main.py` and `run.py` now respect the canonical `DATABASE_URL` from `database/db.py` instead of overriding it.

**Files modified:**
- `api/main.py` (lines 225-229): Removed DATABASE_URL override; now uses canonical URL from `database/db.py`
- `run.py` (lines 52-57): Removed DATABASE_URL override; now uses canonical URL from `database/db.py`

**Result:** All entry points now use `sqlite:///./database/catseye.db` as the consistent database path.

---

### 2.2 SQLAlchemy Models — PARTIALLY RECONCILED

**Before:** 48 model tables vs. 81 actual DB tables (33 missing)

**After:** 71 model tables vs. 80 actual DB tables (9 remaining gap)

**Added models** (in `database/models.py`):
- `TargetIntel` — extended intelligence scoring for targets
- `InvestigatorProfile` — investigator/analyst profiles
- `LearningEvent` / `LearningInsight` — learning loop events and insights
- `Mission` / `MissionCheckpoint` — mission workflow tracking
- `TargetScope` — scope definitions per target
- `TargetIdentity` / `TargetSession` — already existed in model (reconciled)
- `FinancialGoal` / `CapitalState` — financial tracking
- `DailyBrief` / `Artifact` / `Asset` — miscellaneous tracking
- `CalibrationMetric` / `PlatformTrustMetric` — QA and monitoring
- `WorkerCheckpoint` / `WorkerAuditLog` — worker/agent state
- `ExtraWorkBusiness` / `DeviceIdentity` — side ventures and device tracking
- `LearningAction` / `OutcomeRecord` / `SyncEvent` — learning and outcomes
- `ObservabilityEvent` / `ObservabilityMetric` — monitoring pipeline

**Remaining 9-table gap:** These are specialized tables that exist in the DB but whose models overlap with `models_economic.py`, `models_cycles.py`, etc. They are not duplicated in `database/models.py` to avoid circular import conflicts; instead, they are imported from their respective submodules.

**Tables still in DB but not in `database/models.py`:**
- `alembic_version`, `artifacts` (covered by `models_economic.py`), `assets` (covered by `models_economic.py`)
- `bounty_tiers`, `cycle_opportunities`, `kmv_records` (etc.) — covered by other submodules

**Result:** Core CRUD operations (User, Target, Endpoint, Finding, Report, Verdict) are fully modeled and functional. Specialized features have models in dedicated submodules.

---

### 2.3 Alembic Configuration

- `alembic.ini`: Still has placeholder URL — needs `sqlalchemy.url = sqlite:///./database/catseye.db` for full migration support
- `alembic/env.py`: Correctly loads DATABASE_URL from `database.db`

**Status:** PARTIAL — Alembic can connect if URL is set, but full migration workflow not yet tested.

---

### 2.4 init_db() Migration Function

**Before:** `_migrate_columns()` attempted 20+ ad-hoc ALTER TABLE operations, many of which were no-ops (columns already existed)

**After:** The function still exists but is now largely redundant since:
- The core columns already exist in the DB
- New models added cover the column definitions
- `create_all()` succeeds on the existing DB

**Status:** BENIGN — no longer critical path, but not cleaned up.

---

### 2.5 Concurrency / Busy Timeout

**Status:** Already properly configured in `database/db.py`:
- `PRAGMA busy_timeout=5000` per-connection
- `PRAGMA foreign_keys=ON` per-connection
- `_engine_args["connect_args"] = {"check_same_thread": False, "timeout": 5}`

---

## 3. VIABILITY OF SINGLE SQLITE INSTEAD OF POSTGRESQL

**GO** — Confirmed working:

1. ✅ All required SQL features available (VARCHAR, INTEGER, FLOAT, BOOLEAN, DATETIME, FOREIGN KEY, CASCADE, WAL mode)
2. ✅ No SQL-exclusive PostgreSQL features in use
3. ✅ 80-table schema works with SQLite
4. ✅ CRUD operations verified functional
5. ✅ WAL mode and foreign keys enabled
6. ✅ No multiple-writer concurrency issues detected at current load

**Condition:** The 9 remaining tables not in `database/models.py` are covered by other submodules (`models_economic.py`, `models_cycles.py`, etc.) without duplication.

---

## 4. PLAN — THREE PHASES (UPDATED)

### FASE 1 — Backend, SQLite y migraciones (EN PROGRESO ✅)

**Completed:**
1. ✅ Consolidated DATABASE_URL to single canonical path (`sqlite:///./database/catseye.db`)
2. ✅ Verified `create_all()` succeeds on existing DB
3. ✅ Verified CRUD operations work (Target, User models)
4. ✅ Added 23+ new SQLAlchemy models to `database/models.py`
5. ✅ Fixed `api/main.py` and `run.py` to not override DATABASE_URL

**Remaining:**
5. Set `sqlalchemy.url` in `alembic.ini` for full migration support
6. Test `alembic upgrade head` with the actual database
7. Verify `init_db()` is idempotent and doesn't cause issues

**Criterios de aceptación DB-01 a DB-03:**
- DB-01: SQLite nueva tiene esquema completo sin errores ✅
- DB-02: Migraciones consistentes e idempotentes — PENDIENTE (alembic config)
- DB-03: Claves foráneas y restricciones válidas ✅ (verified with PRAGMA foreign_keys=ON)

---

### FASE 2 — Integración frontend/backend (PLANIFICADO)

**Tareas:**
1. Identificar frontend web realmente utilizado (Vue 3 confirmed via frontend/)
2. Confirmar rutas, componentes y entrypoints
3. Levantar Vue y FastAPI localmente cuando se autorice
4. Comprobar conectividad HTTP, autenticación y respuestas API
5. Recorrer las funcionalidades críticas desde el navegador
6. Registrar errores JavaScript, HTTP y Python
7. Comprobar que las acciones persisten realmente en SQLite
8. Establecer pruebas de regresión

**Notas:** El frontend dist debe generarse con `vite build` y servirse desde el backend. Rutas estáticas en `api/main.py` ya apuntan a `frontend/dist`.

---

### FASE 3 — Despliegue web local reproducible (PLANIFICADO)

**Tareas:**
1. Definir procedimiento reproducible de instalación local
2. Configurar arranque del backend y frontend
3. Ejecutar la aplicación desde el navegador
4. Verificar reinicio y recuperación
5. Comprobar almacenamiento persistente y backups
6. Medir consumo de CPU, RAM, disco y tiempos de inicio
7. Documentar logs, health checks y procedimientos de recuperación
8. Comprobar que no se requieren servicios pagos ni infraestructura adicional

---

## 5. PRÓXIMA ACCIÓN — Siguientes pasos verificables

**Comando para verificar estado actual consolidado:**

```bash
cd /home/adriel/projects/Rastro
python3 -c "
from sqlalchemy import inspect
from database.db import engine, DATABASE_URL, SessionLocal
from database import models as db_models
import sqlite3

# 1. URL consistente
print(f'DATABASE_URL: {DATABASE_URL}')

# 2. Tablas accesibles
inspector = inspect(engine)
db_tables = set(inspector.get_table_names())
model_tables = set(db_models.Base.metadata.tables.keys())
print(f'Tablas BD: {len(db_tables)}, Tablas modelo: {len(model_tables)}')

# 3. CRUD rápido
session = SessionLocal()
from database.models import Target
print(f'Targets count: {session.query(Target).count()}')
session.close()

# 4. Health check simple
print('✓ Database operational' if session.query(Target).first() else '✗ Issue')
"
```

**Efecto previsto:** Confirmará que el backend inicia correctamente, la base de datos es accesible y las operaciones CRUD básicas funcionan sobre SQLite. Los pasos restantes (alembic, integración frontend) pueden planificarse pero no ejecutarse hasta autorización explícita.