"""Daily Brief Store — Persistence for daily briefs."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from database.db import SessionLocal, engine

logger = logging.getLogger("ownex.daily.brief_store")


def _create_table() -> None:
    """Create table if not exists."""
    with engine.connect() as conn:
        conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS daily_briefs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brief_id TEXT UNIQUE NOT NULL,
                generated_at TEXT NOT NULL,
                brief_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def save_brief(brief: dict) -> str:
    """Save a daily brief to persistent storage."""
    from core.daily.brief_store import _create_table

    _create_table()  # Ensure table exists

    brief_id = (
        brief.get("generated_at", datetime.now(UTC).isoformat())
        .replace(":", "")
        .replace("-", "")
        .replace("T", "")
        .replace(".", "")
    )
    if not brief_id.startswith("brief_"):
        brief_id = f"brief_{brief_id}"

    session = SessionLocal()
    try:
        conn = session.connection().connection
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO daily_briefs (brief_id, generated_at, brief_json) VALUES (?, ?, ?)",
            (brief_id, brief.get("generated_at"), json.dumps(brief)),
        )
        conn.commit()
        logging.getLogger("ownex.daily.brief_store").info(f"[BRIEF_STORE] Saved brief {brief_id}")
        return brief_id
    except Exception as e:
        logging.getLogger("ownex.daily.brief_store").error(f"[BRIEF_STORE] Failed to save brief: {e}")
        raise
    finally:
        session.close()


def get_brief_history(limit: int = 30) -> list[dict]:
    """Get recent briefs."""
    session = SessionLocal()
    try:
        conn = session.connection().connection
        cursor = conn.cursor()
        cursor.execute("SELECT brief_json FROM daily_briefs ORDER BY generated_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [json.loads(row[0]) for row in rows]
    finally:
        session.close()


def get_latest_brief() -> dict | None:
    """Get the most recent brief."""
    history = get_brief_history(limit=1)
    return history[0] if history else None
