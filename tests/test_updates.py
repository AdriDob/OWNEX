"""Tests for ORION Update Manager."""

from __future__ import annotations

from datetime import datetime, timezone

from core.update.engine import UpdateManager, _parse_semver


class TestParseSemver:
    def test_parses_standard(self) -> None:
        assert _parse_semver("4.3.2") == (4, 3, 2)

    def test_parses_with_v_prefix(self) -> None:
        assert _parse_semver("v4.3.2") == (4, 3, 2)

    def test_parses_dev_suffix(self) -> None:
        assert _parse_semver("4.0.0-dev") == (4, 0, 0)

    def test_returns_zero_on_invalid(self) -> None:
        assert _parse_semver("invalid") == (0, 0, 0)


class TestUpdateManager:
    def test_init_has_current_version(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("core.update.engine.UPDATE_LOG", tmp_path / "history.jsonl")
        mgr = UpdateManager()
        status = mgr.status()
        assert "current_version" in status
        assert status["current_version"] != ""

    def test_remote_check_falls_back_gracefully(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("core.update.engine.UPDATE_LOG", tmp_path / "history.jsonl")
        mgr = UpdateManager()
        result = mgr.check_remote()
        # Without network, falls back to current version
        assert "current_version" in result
        assert "update_available" in result

    def test_status_shape(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("core.update.engine.UPDATE_LOG", tmp_path / "history.jsonl")
        mgr = UpdateManager()
        status = mgr.status()
        assert "current_version" in status
        assert "remote_version" in status
        assert "update_available" in status
        assert "last_checked" in status

    def test_history_starts_empty(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("core.update.engine.UPDATE_LOG", tmp_path / "history.jsonl")
        mgr = UpdateManager()
        assert mgr.get_history() == []

    def test_prepare_update_creates_backup(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("core.update.engine.UPDATE_LOG", tmp_path / "history.jsonl")
        mgr = UpdateManager()
        result = mgr.prepare_update()
        # Should work (backup ~/.orion/) or fail gracefully
        if result.get("status") == "error":
            assert "reason" in result
        else:
            assert result["status"] == "ready"
            assert "backup_path" in result

    def test_rollback_returns_error_without_backup(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("core.update.engine.UPDATE_LOG", tmp_path / "history.jsonl")
        mgr = UpdateManager()
        result = mgr.rollback()
        assert result["status"] == "error"
        assert "reason" in result

    def test_persistence_survives_reinit(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("core.update.engine.UPDATE_LOG", tmp_path / "history.jsonl")

        mgr1 = UpdateManager()
        mgr1._persist({"action": "test", "timestamp": datetime.now(timezone.utc).isoformat()})

        mgr2 = UpdateManager()
        assert len(mgr2.get_history()) == 1
        assert mgr2._history[0]["action"] == "test"
