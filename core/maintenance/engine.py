"""OWNEX Maintenance Engine — DB longevity, VACUUM, ANALYZE, integrity checks."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import OWNEX_DIR

logger = logging.getLogger("ownex.core.maintenance")

KNOWN_DATABASES: list[Path] = [
    OWNEX_DIR / "ownex.db",
    OWNEX_DIR / "database" / "ownex.db",
    OWNEX_DIR / "database" / "ownex_core.db",
    OWNEX_DIR / "database" / "memory.db",
    OWNEX_DIR / "database" / "evidence_graph.db",
    OWNEX_DIR / "database" / "atlas.db",
    OWNEX_DIR / "database" / "odyssey.db",
]


@dataclass
class MaintenanceResult:
    operation: str
    db_name: str
    status: str
    message: str
    duration_ms: float


def _connect(db_path: Path) -> sqlite3.Connection | None:
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA busy_timeout=5000")
        return conn
    except Exception as exc:
        logger.warning("Cannot connect to %s: %s", db_path.name, exc)
        return None


def _run_vacuum(conn: sqlite3.Connection) -> dict[str, Any]:
    before = conn.execute("PRAGMA page_count").fetchone()[0]
    before_size = before * conn.execute("PRAGMA page_size").fetchone()[0]
    conn.execute("VACUUM")
    after = conn.execute("PRAGMA page_count").fetchone()[0]
    after_size = after * conn.execute("PRAGMA page_size").fetchone()[0]
    freed = before_size - after_size
    return {"pages_before": before, "pages_after": after, "freed_bytes": max(0, freed)}


def _run_analyze(conn: sqlite3.Connection) -> None:
    conn.execute("ANALYZE")


def _run_integrity_check(conn: sqlite3.Connection) -> list[str]:
    cursor = conn.execute("PRAGMA integrity_check")
    results = [row[0] for row in cursor.fetchall()]
    return results


def _run_reindex(conn: sqlite3.Connection) -> None:
    conn.execute("REINDEX")


def _run_wal_checkpoint(conn: sqlite3.Connection) -> dict[str, Any]:
    cursor = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    row = cursor.fetchone()
    return {"wal_frames": row[0] if row else 0, "wal_bytes": row[1] if row else 0}


class MaintenanceEngine:
    """Centralized DB maintenance — vacuum, analyze, integrity, reindex, WAL."""

    def vacuum(self, db_path: Path | None = None) -> list[MaintenanceResult]:
        """Run VACUUM on all (or specific) known databases to reclaim disk space."""
        return self._run_on_all(_run_vacuum, "vacuum", db_path)

    def analyze(self, db_path: Path | None = None) -> list[MaintenanceResult]:
        """Run ANALYZE to update query planner statistics."""
        return self._run_on_all(_run_analyze, "analyze", db_path)

    def integrity_check(self, db_path: Path | None = None) -> list[MaintenanceResult]:
        """Run integrity_check on all (or specific) known databases."""
        return self._run_on_all(_run_integrity_check, "integrity_check", db_path)

    def reindex(self, db_path: Path | None = None) -> list[MaintenanceResult]:
        """Rebuild all indexes."""
        return self._run_on_all(_run_reindex, "reindex", db_path)

    def wal_checkpoint(self, db_path: Path | None = None) -> list[MaintenanceResult]:
        """WAL checkpoint (TRUNCATE) on all known databases."""
        return self._run_on_all(_run_wal_checkpoint, "wal_checkpoint", db_path)

    def full_maintenance(self) -> dict[str, Any]:
        """Run all maintenance operations on all databases. Returns full report."""
        results: dict[str, list[MaintenanceResult]] = {
            "vacuum": self.vacuum(),
            "analyze": self.analyze(),
            "integrity_check": self.integrity_check(),
            "reindex": self.reindex(),
            "wal_checkpoint": self.wal_checkpoint(),
        }
        total_ops = sum(len(r) for r in results.values())
        errors = sum(1 for r in results.values() for mr in r if mr.status == "error")
        return {
            "status": "ok" if errors == 0 else "completed_with_errors",
            "total_operations": total_ops,
            "errors": errors,
            "results": {k: [self._result_to_dict(mr) for mr in v] for k, v in results.items()},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def summary(self) -> dict[str, Any]:
        """Return DB file sizes and status summary."""
        dbs: list[dict[str, Any]] = []
        for db_path in KNOWN_DATABASES:
            if not db_path.exists():
                continue
            try:
                conn = _connect(db_path)
                if conn is None:
                    continue
                page_count = conn.execute("PRAGMA page_count").fetchone()[0]
                page_size = conn.execute("PRAGMA page_size").fetchone()[0]
                wal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
                conn.close()
                dbs.append(
                    {
                        "name": db_path.name,
                        "size_bytes": page_count * page_size,
                        "size_mb": round(page_count * page_size / (1024 * 1024), 2),
                        "pages": page_count,
                        "journal_mode": wal_mode,
                    }
                )
            except Exception as exc:
                dbs.append({"name": db_path.name, "error": str(exc)})
        return {
            "databases": dbs,
            "total_db_count": len(dbs),
            "total_size_mb": round(sum(d.get("size_mb", 0) for d in dbs if "size_mb" in d), 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Internal helpers ──────────────────────────────────────────

    def _run_on_all(
        self,
        op_fn: Any,
        op_name: str,
        specific_path: Path | None = None,
    ) -> list[MaintenanceResult]:
        targets = [specific_path] if specific_path else KNOWN_DATABASES
        results: list[MaintenanceResult] = []
        for db_path in targets:
            if not db_path.exists():
                continue
            conn = _connect(db_path)
            if conn is None:
                results.append(
                    MaintenanceResult(
                        operation=op_name,
                        db_name=db_path.name,
                        status="error",
                        message="Cannot connect",
                        duration_ms=0,
                    )
                )
                continue
            start = datetime.now()
            try:
                result = op_fn(conn)
                conn.commit()
                elapsed = (datetime.now() - start).total_seconds() * 1000
                msg = str(result) if isinstance(result, dict) else "ok"
                results.append(
                    MaintenanceResult(
                        operation=op_name,
                        db_name=db_path.name,
                        status="ok",
                        message=msg,
                        duration_ms=round(elapsed, 2),
                    )
                )
                logger.info("[MAINT] %s on %s: %s (%.0f ms)", op_name, db_path.name, msg, elapsed)
            except Exception as exc:
                elapsed = (datetime.now() - start).total_seconds() * 1000
                results.append(
                    MaintenanceResult(
                        operation=op_name,
                        db_name=db_path.name,
                        status="error",
                        message=str(exc),
                        duration_ms=round(elapsed, 2),
                    )
                )
                logger.warning("[MAINT] %s on %s failed: %s", op_name, db_path.name, exc)
            finally:
                conn.close()
        return results

    @staticmethod
    def _result_to_dict(mr: MaintenanceResult) -> dict[str, Any]:
        return {
            "operation": mr.operation,
            "db_name": mr.db_name,
            "status": mr.status,
            "message": mr.message,
            "duration_ms": mr.duration_ms,
        }


# ── Convenience ────────────────────────────────────────────────────


def run_maintenance() -> dict[str, Any]:
    """Run full maintenance on all databases. Convenience wrapper."""
    return MaintenanceEngine().full_maintenance()
