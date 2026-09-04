"""SQLite-backed repository for OpportunityGenome.

Lightweight adapter using the stdlib `sqlite3` and JSON storage of the
genome `to_dict()` payload. Intended for local dev and tests.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Iterable, Optional

from cores.opportunity_genome.models import OpportunityGenome


class SQLiteOpportunityGenomeRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS genomes (
                    id TEXT PRIMARY KEY,
                    external_id TEXT UNIQUE,
                    data TEXT NOT NULL,
                    discovered_at TEXT,
                    updated_at TEXT
                )
                """
            )

    def save(self, genome: OpportunityGenome) -> OpportunityGenome:
        payload = genome.to_dict()
        data = json.dumps(payload, ensure_ascii=False)
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO genomes (id, external_id, data, discovered_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (genome.id, genome.external_id, data, payload.get("discovered_at"), payload.get("updated_at")),
            )
        return genome

    def get_by_id(self, id: str) -> Optional[OpportunityGenome]:
        with self._conn() as conn:
            row = conn.execute("SELECT data FROM genomes WHERE id = ?", (id,)).fetchone()
            if not row:
                return None
            payload = json.loads(row["data"])
            return OpportunityGenome.from_dict(payload)

    def get_by_external_id(self, external_id: str) -> Optional[OpportunityGenome]:
        with self._conn() as conn:
            row = conn.execute("SELECT data FROM genomes WHERE external_id = ?", (external_id,)).fetchone()
            if not row:
                return None
            payload = json.loads(row["data"])
            return OpportunityGenome.from_dict(payload)

    def list_all(self) -> Iterable[OpportunityGenome]:
        with self._conn() as conn:
            rows = conn.execute("SELECT data FROM genomes").fetchall()
            for r in rows:
                yield OpportunityGenome.from_dict(json.loads(r["data"]))

    def delete(self, id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM genomes WHERE id = ?", (id,))
            return cur.rowcount > 0
