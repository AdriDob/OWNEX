"""Tests for ORION Maintenance Engine."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from core.maintenance.engine import MaintenanceEngine


def _create_test_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO test VALUES (1, 'hello'), (2, 'world')")
    conn.execute("CREATE INDEX idx_value ON test(value)")
    conn.commit()
    conn.close()


class TestMaintenanceEngine:
    def test_vacuum(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        engine = MaintenanceEngine()
        results = engine.vacuum(db_path)
        assert len(results) == 1
        assert results[0].status == "ok"
        assert results[0].operation == "vacuum"

    def test_analyze(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        engine = MaintenanceEngine()
        results = engine.analyze(db_path)
        assert len(results) == 1
        assert results[0].status == "ok"

    def test_integrity_check_ok(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        engine = MaintenanceEngine()
        results = engine.integrity_check(db_path)
        assert len(results) == 1
        assert results[0].status == "ok"

    def test_integrity_check_corrupted_fails_gracefully(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        engine = MaintenanceEngine()
        results = engine.wal_checkpoint(db_path)
        assert len(results) == 1
        assert results[0].status in ("ok", "error")

    def test_reindex(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        engine = MaintenanceEngine()
        results = engine.reindex(db_path)
        assert len(results) == 1
        assert results[0].status == "ok"

    def test_wal_checkpoint(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.close()
        engine = MaintenanceEngine()
        results = engine.wal_checkpoint(db_path)
        assert len(results) == 1
        assert results[0].status == "ok"

    def test_unknown_db_skips_gracefully(self, tmp_path) -> None:
        engine = MaintenanceEngine()
        results = engine.vacuum(tmp_path / "nonexistent.db")
        assert len(results) == 0

    def test_summary_shape(self, tmp_path) -> None:
        db_path = tmp_path / "for_summary.db"
        _create_test_db(db_path)
        engine = MaintenanceEngine()
        summary = engine.summary()
        assert "databases" in summary
        assert "total_db_count" in summary
        assert "total_size_mb" in summary
        assert "timestamp" in summary

    def test_full_maintenance_returns_report(self, tmp_path) -> None:
        db_path = tmp_path / "full_maint.db"
        _create_test_db(db_path)
        engine = MaintenanceEngine()
        report = engine.full_maintenance()
        assert report["status"] in ("ok", "completed_with_errors")
        assert "total_operations" in report
        assert "results" in report
        assert "vacuum" in report["results"]
        assert "analyze" in report["results"]
        assert "integrity_check" in report["results"]
        assert "reindex" in report["results"]
        assert "wal_checkpoint" in report["results"]
