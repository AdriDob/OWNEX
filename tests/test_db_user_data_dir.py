"""Tests for database.db user data directory resolution + legacy migration."""

import sys
from pathlib import Path

import pytest

from database import db as db_mod


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("OWNEX_DATA_DIR", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)


def test_env_var_wins_over_everything(monkeypatch, tmp_path):
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path / "custom"))
    assert db_mod.user_data_dir() == tmp_path / "custom"


def test_frozen_windows_uses_localappdata(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(db_mod.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    result = db_mod.user_data_dir()
    assert result == tmp_path / "OWNEX"


def test_frozen_windows_falls_back_to_home(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(db_mod.sys, "platform", "win32")
    result = db_mod.user_data_dir()
    assert result == Path.home() / "AppData" / "Local" / "OWNEX"


def test_frozen_posix_uses_xdg_data_home(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(db_mod.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert db_mod.user_data_dir() == tmp_path / "OWNEX"


def test_migration_copies_legacy_roaming_db(monkeypatch, tmp_path):
    legacy = tmp_path / "roaming" / "OWNEX" / "database"
    legacy.mkdir(parents=True)
    (legacy / "catseye.db").write_bytes(b"legacy-data")
    target = tmp_path / "local" / "OWNEX"
    monkeypatch.setattr(db_mod.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))

    db_mod._migrate_legacy_roaming_data(target)

    assert (target / "database" / "catseye.db").read_bytes() == b"legacy-data"
    assert (target / ".migrated_from_roaming").exists()


def test_migration_skips_when_target_has_db(monkeypatch, tmp_path):
    legacy = tmp_path / "roaming" / "OWNEX" / "database"
    legacy.mkdir(parents=True)
    (legacy / "catseye.db").write_bytes(b"legacy-data")
    target_db = tmp_path / "local" / "OWNEX" / "database"
    target_db.mkdir(parents=True)
    (target_db / "catseye.db").write_bytes(b"existing-data")
    monkeypatch.setattr(db_mod.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))

    db_mod._migrate_legacy_roaming_data(target_db.parent)

    assert (target_db / "catseye.db").read_bytes() == b"existing-data"


def test_migration_noop_on_posix(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod.sys, "platform", "linux")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    target = tmp_path / "target"
    db_mod._migrate_legacy_roaming_data(target)
    assert not target.exists()
