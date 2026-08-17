import contextlib
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


def user_data_dir() -> Path:
    """User-writable data directory (per-user, survives app upgrades).

    Frozen desktop bundles write to %APPDATA%/OWNEX (Windows) or
    ~/.config/OWNEX (POSIX) so that user data survives reinstalls of the
    executable. Dev mode keeps the historical repo-relative ``data`` dir.
    """
    if getattr(sys, "frozen", False):
        base = os.getenv("APPDATA") or os.getenv("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        return Path(base) / "OWNEX"
    return Path("data")


def _default_db_url() -> str:
    if getattr(sys, "frozen", False):
        return "sqlite:///" + str((user_data_dir() / "database" / "catseye.db").resolve())
    return "sqlite:///./database/catseye.db"


DATABASE_URL = os.getenv("DATABASE_URL", _default_db_url())
IS_SQLITE = DATABASE_URL.startswith("sqlite")

_engine_args: dict = {}
if IS_SQLITE:
    _engine_args["connect_args"] = {"check_same_thread": False, "timeout": 5}


def _ensure_db_dir() -> None:
    """Create the SQLite parent directory before the engine opens the file.

    Required for frozen desktop bundles, where a fresh install has no
    ``database/`` directory next to the executable. Without this, any
    import-time ``SessionLocal()`` fails with "unable to open database file".
    """
    if not IS_SQLITE:
        return
    match = re.match(r"sqlite:///(.+)", DATABASE_URL)
    if match:
        db_path = Path(match.group(1))
        db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_db_dir()

logger = __import__("logging").getLogger("ownex.db")

engine = create_engine(DATABASE_URL, **_engine_args)

if IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    with engine.connect() as conn:
        for pragma in ("PRAGMA journal_mode=WAL", "PRAGMA synchronous=NORMAL", "PRAGMA busy_timeout=5000"):
            with contextlib.suppress(Exception):
                conn.execute(text(pragma))
        conn.commit()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# Register model modules so SQLAlchemy metadata includes all tables
# before init_db()/create_all() runs. These are imported at the bottom
# to avoid circular imports (each module imports Base/SessionLocal above).
import cores.knowledge.store  # noqa: F401
from database import models as _db_models  # noqa: F401 — registers User, MemoryRecord, etc.


def _get_existing_columns(session, table_name: str) -> set[str]:
    """Get column names for a table using PRAGMA (SQLite) or information_schema."""
    if IS_SQLITE:
        rows = session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        return {row[1] for row in rows}  # row[1] = column name
    return set()


# NOTE: Schema migrations are now managed via Alembic (alembic/ directory).
# The _migrate_columns() function below is legacy and will be removed once
# all deployments have run `alembic upgrade head`.


def _migrate_columns(session, table: str, columns: list[tuple[str, str]]) -> None:
    """Add columns to a table only if they don't already exist."""
    existing = _get_existing_columns(session, table)
    if not existing:
        logger.info("Table %s does not exist yet — skipping migration", table)
        return
    for col_name, col_type in columns:
        if col_name in existing:
            continue
        try:
            session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type};"))
            logger.info("Migrated %s.%s", table, col_name)
        except Exception as exc:
            logger.warning("Migration failed (%s.%s): %s", table, col_name, exc)


def _migrate_indexes(session) -> None:
    """Create indexes that exist in ORM but may not exist in the DB yet.

    SQLAlchemy's create_all() only creates indexes for NEW tables.
    Existing tables keep their original schema even when index=True is added later.
    """
    indexes = [
        "CREATE INDEX IF NOT EXISTS ix_targets_name ON targets (name);",
        "CREATE INDEX IF NOT EXISTS ix_endpoints_target_id ON endpoints (target_id);",
        "CREATE INDEX IF NOT EXISTS ix_findings_target_id ON findings (target_id);",
        "CREATE INDEX IF NOT EXISTS ix_findings_endpoint_id ON findings (endpoint_id);",
        "CREATE INDEX IF NOT EXISTS ix_memory_records_category ON memory_records (category);",
        "CREATE INDEX IF NOT EXISTS ix_memory_records_key ON memory_records (key);",
        "CREATE INDEX IF NOT EXISTS ix_evidence_endpoint_id ON evidence (endpoint_id);",
        "CREATE INDEX IF NOT EXISTS ix_scan_runs_target_id ON scan_runs (target_id);",
        "CREATE INDEX IF NOT EXISTS ix_validation_runs_identity_baseline_id ON validation_runs (identity_baseline_id);",
        "CREATE INDEX IF NOT EXISTS ix_validation_runs_identity_probe_id ON validation_runs (identity_probe_id);",
        "CREATE INDEX IF NOT EXISTS ix_validation_runs_verdict_id ON validation_runs (verdict_id);",
        "CREATE INDEX IF NOT EXISTS ix_reports_program ON reports (program);",
        "CREATE INDEX IF NOT EXISTS ix_reports_target ON reports (target);",
        "CREATE INDEX IF NOT EXISTS ix_reports_status ON reports (status);",
    ]
    for sql in indexes:
        try:
            session.execute(text(sql))
        except Exception as exc:
            logger.warning("Index migration failed (%s): %s", sql, exc)
    logger.info("[DB] Index migration complete")


def init_db():

    _ensure_db_dir()
    Base.metadata.create_all(bind=engine)

    # Auto-migration for tables that may have been created before model updates
    if IS_SQLITE:
        session = None
        try:
            session = SessionLocal()

            _migrate_columns(
                session,
                "targets_intel",
                [
                    ("target_id", "INTEGER REFERENCES targets(id) ON DELETE SET NULL"),
                    ("freshness_score", "FLOAT DEFAULT 0.0"),
                    ("competition_score", "FLOAT DEFAULT 0.0"),
                    ("opportunity_score", "FLOAT DEFAULT 0.0"),
                    ("reward_score", "FLOAT DEFAULT 0.0"),
                    ("reward_confidence", "FLOAT DEFAULT 0.0"),
                    ("attack_surface_score", "FLOAT DEFAULT 0.0"),
                    ("evidence_potential_score", "FLOAT DEFAULT 0.0"),
                    ("technology_tags", "VARCHAR DEFAULT ''"),
                    ("cms_detected", "VARCHAR"),
                    ("framework_detected", "VARCHAR"),
                    ("wordpress_plugins_detected", "VARCHAR"),
                ],
            )

            _migrate_columns(
                session,
                "reports",
                [
                    ("program", "VARCHAR DEFAULT ''"),
                    ("target", "VARCHAR DEFAULT ''"),
                    ("vulnerability", "VARCHAR DEFAULT ''"),
                    ("severity", "VARCHAR DEFAULT 'medium'"),
                    ("status", "VARCHAR DEFAULT 'draft'"),
                    ("estimated_reward", "FLOAT DEFAULT 0.0"),
                    ("confirmed_reward", "FLOAT DEFAULT 0.0"),
                    ("currency", "VARCHAR DEFAULT 'USD'"),
                    ("evidence_count", "INTEGER DEFAULT 0"),
                    ("notes", "TEXT DEFAULT ''"),
                    ("timeline", "TEXT DEFAULT '[]'"),
                    ("attachments", "TEXT DEFAULT '[]'"),
                    ("updated_at", "DATETIME"),
                ],
            )

            _migrate_columns(
                session,
                "findings",
                [
                    ("status", "VARCHAR DEFAULT 'open'"),
                ],
            )

            _migrate_columns(
                session,
                "endpoints",
                [
                    ("hypothesis_id", "VARCHAR"),
                ],
            )

            _migrate_columns(
                session,
                "notifications",
                [
                    ("title", "VARCHAR"),
                    ("severity", "VARCHAR DEFAULT 'info'"),
                    ("priority", "VARCHAR DEFAULT 'medium'"),
                    ("dedup_key", "VARCHAR"),
                    ("delivered_via", "VARCHAR"),
                ],
            )

            _migrate_columns(
                session,
                "verdicts",
                [
                    ("uncertainty_level", "VARCHAR DEFAULT 'unknown'"),
                    ("missing_verifications", "TEXT"),
                    ("alternative_explanations", "TEXT"),
                    ("next_best_test", "TEXT"),
                    ("vulnerability_type", "VARCHAR DEFAULT 'unknown'"),
                ],
            )

            _migrate_columns(
                session,
                "findings",
                [
                    ("vulnerability_type", "VARCHAR DEFAULT 'unknown'"),
                ],
            )

            _migrate_columns(
                session,
                "findings",
                [
                    ("notes", "TEXT DEFAULT ''"),
                ],
            )

            _migrate_columns(
                session,
                "users",
                [
                    ("email_verified", "BOOLEAN DEFAULT 0"),
                    ("verification_token", "VARCHAR"),
                    ("verification_expires", "DATETIME"),
                ],
            )

            _migrate_columns(
                session,
                "tasks",
                [
                    ("due_date", "DATETIME"),
                    ("calendar_event_id", "VARCHAR"),
                    ("synced_to_calendar", "VARCHAR DEFAULT 'false'"),
                    ("todo_task_id", "VARCHAR"),
                    ("synced_to_todo", "VARCHAR DEFAULT 'false'"),
                    ("last_synced_at", "DATETIME"),
                ],
            )

            _migrate_indexes(session)
            session.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
            session.commit()
        except Exception as exc:
            logger.warning("Migration block failed: %s", exc)
        finally:
            if session is not None:
                session.close()
