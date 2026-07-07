import contextlib
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database/catseye.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

_engine_args: dict = {}
if IS_SQLITE:
    _engine_args["connect_args"] = {"check_same_thread": False, "timeout": 5}

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

# Register knowledge models with SQLAlchemy metadata before init_db() runs.
import cores.knowledge.store  # noqa: F401


def _ensure_db_dir() -> None:
    if not IS_SQLITE:
        return
    match = re.match(r"sqlite:///(.+)", DATABASE_URL)
    if match:
        db_path = Path(match.group(1))
        db_path.parent.mkdir(parents=True, exist_ok=True)


logger = __import__('logging').getLogger('cateye.db')


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


def init_db():

    _ensure_db_dir()
    Base.metadata.create_all(bind=engine)

    # Auto-migration for tables that may have been created before model updates
    if IS_SQLITE:
        session = None
        try:
            session = SessionLocal()

            _migrate_columns(session, "targets_intel", [
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
            ])

            _migrate_columns(session, "reports", [
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
            ])

            _migrate_columns(session, "notifications", [
                ("title", "VARCHAR"),
                ("severity", "VARCHAR DEFAULT 'info'"),
                ("priority", "VARCHAR DEFAULT 'medium'"),
                ("dedup_key", "VARCHAR"),
                ("delivered_via", "VARCHAR"),
            ])

            session.commit()
        except Exception as exc:
            logger.warning("Migration block failed: %s", exc)
        finally:
            if session is not None:
                session.close()
