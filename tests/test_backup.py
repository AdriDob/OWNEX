"""Tests for OWNEX Backup System."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def _backup_env(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temp OWNEX_DIR with some test files and point backup at it."""
    tmp = Path(tempfile.mkdtemp())
    monkeypatch.setattr("cores.backup.engine.OWNEX_DIR", tmp)
    monkeypatch.setattr("cores.backup.engine.BACKUP_DIR", tmp / "backups")

    # Create some test files
    (tmp / "database").mkdir(parents=True)
    (tmp / "database" / "ownex.db").write_text("fake db content")
    (tmp / "database" / "memory.db").write_text("fake memory content")
    (tmp / "config.json").write_text('{"key": "value"}')
    (tmp / "identity_vault.key").write_text("fake-key-content-32bytes!!")
    (tmp / "targets").mkdir()
    (tmp / "targets" / "test-target").mkdir(parents=True)
    (tmp / "targets" / "test-target" / "recon.json").write_text('{"data": "test"}')

    return tmp


class TestCreateBackup:
    def test_backup_creates_archive(self, _backup_env: Path) -> None:
        from cores.backup import create_backup

        result = create_backup()
        assert result["status"] == "ok"
        assert "backup_path" in result
        assert result["total_files"] >= 4
        assert result["size"] > 0

        path = Path(result["backup_path"])
        assert path.exists()
        assert path.name.startswith("OWNEX_BACKUP_")
        assert path.suffix == ".zip"

    def test_backup_contains_manifest(self, _backup_env: Path) -> None:
        from cores.backup import create_backup

        result = create_backup()
        assert result["status"] == "ok"

        import zipfile

        from cores.version import OWNEX_VERSION

        with zipfile.ZipFile(result["backup_path"]) as zf:
            assert "manifest.json" in zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["version"] == OWNEX_VERSION
            assert "created_at" in manifest
            assert manifest["total_files"] >= 4
            assert "files" in manifest
            assert any(f["path"] == "database/ownex.db" for f in manifest["files"])

    def test_backup_manifest_checksum(self, _backup_env: Path) -> None:
        from cores.backup import create_backup

        result = create_backup()

        import zipfile

        with zipfile.ZipFile(result["backup_path"]) as zf:
            manifest = json.loads(zf.read("manifest.json"))

        # Verify each file's checksum in manifest matches actual content
        import hashlib

        for entry in manifest["files"]:
            content = (_backup_env / entry["path"]).read_bytes()
            expected = hashlib.sha256(content).hexdigest()
            assert entry["checksum"] == expected, f"Checksum mismatch for {entry['path']}"


class TestListBackups:
    def test_list_empty(self, _backup_env: Path) -> None:
        from cores.backup import list_backups

        assert list_backups() == []

    def test_list_after_create(self, _backup_env: Path) -> None:
        from cores.backup import create_backup, list_backups

        create_backup()
        backups = list_backups()
        assert len(backups) == 1
        assert backups[0]["filename"].startswith("OWNEX_BACKUP_")
        assert backups[0]["size"] > 0

    def test_list_multiple_backups(self, _backup_env: Path) -> None:
        from cores.backup import create_backup, list_backups

        create_backup()
        create_backup()
        backups = list_backups()
        assert len(backups) == 2


class TestVerifyBackup:
    def test_verify_valid_backup(self, _backup_env: Path) -> None:
        from cores.backup import create_backup, verify_backup

        result = create_backup()
        v = verify_backup(result["backup_path"])
        assert v["status"] == "ok"
        assert v["total_files_expected"] == v["total_files_actual"]
        assert v["missing_files"] == []
        assert v["checksum_errors"] == []

    def test_verify_nonexistent_backup(self, _backup_env: Path) -> None:
        from cores.backup import verify_backup

        v = verify_backup("/nonexistent/path.zip")
        assert v["status"] == "error"
        assert "not found" in v["reason"]


class TestPruneBackups:
    def test_prune_keeps_n_most_recent(self, _backup_env: Path) -> None:
        from cores.backup import create_backup, list_backups, prune_backups

        for _ in range(5):
            create_backup()
        assert len(list_backups()) == 5
        result = prune_backups(keep=2)
        assert result["deleted"] == 3
        assert result["kept"] == 2
        assert len(list_backups()) == 2

    def test_prune_with_fewer_than_keep(self, _backup_env: Path) -> None:
        from cores.backup import create_backup, prune_backups

        create_backup()
        result = prune_backups(keep=10)
        assert result["deleted"] == 0


class TestBackupStatus:
    def test_status_shape(self, _backup_env: Path) -> None:
        from cores.backup import backup_status

        status = backup_status()
        assert "total_backups" in status
        assert "backup_dir" in status
        assert "ownex_dir" in status
        assert status["total_backups"] == 0

        from cores.backup import create_backup

        create_backup()
        status2 = backup_status()
        assert status2["total_backups"] == 1
        assert status2["latest_backup"] is not None


class TestRestoreBackup:
    def test_restore_to_target_dir(self, _backup_env: Path) -> None:
        from cores.backup import create_backup, restore_backup

        result = create_backup()

        restore_dir = Path(tempfile.mkdtemp())
        r = restore_backup(result["backup_path"], target_dir=str(restore_dir))
        assert r["status"] == "ok"
        assert r["restored_files"] >= 4
        assert (restore_dir / "database" / "ownex.db").exists()
        assert (restore_dir / "config.json").exists()


class TestSecurityHardening:
    def test_backup_never_contains_raw_secrets(self, _backup_env: Path) -> None:
        """SECURITY: vault key / private keys must never land in a plaintext zip."""
        import zipfile

        from cores.backup import create_backup

        (_backup_env / "id_ed25519").write_text("fake-private-key")
        (_backup_env / "cert.pem").write_text("fake-pem")
        (_backup_env / "wallet_key.p12").write_text("fake-p12")
        (_backup_env / "identity_vault.json").write_text('{"encrypted": true}')

        result = create_backup()
        assert result["status"] == "ok"
        with zipfile.ZipFile(result["backup_path"]) as zf:
            names = zf.namelist()
            assert "identity_vault.key" not in names
            assert "identity_vault.key.bak" not in names
            assert "id_ed25519" not in names
            assert "cert.pem" not in names
            assert "wallet_key.p12" not in names

        # Encrypted vault + DBs still backed up (recovery works).
        with zipfile.ZipFile(result["backup_path"]) as zf:
            manifest = json.loads(zf.read("manifest.json"))
            assert "identity_vault.json" in {f["path"] for f in manifest["files"]}
            assert any("database/ownex.db" == f["path"] for f in manifest["files"])

    def test_restore_preserves_existing_vault_key(self, _backup_env: Path) -> None:
        """Restoring with an existing vault key never clobbers it (preserves .key.bak)."""
        from cores.backup import create_backup, restore_backup

        # Put a fake identity_vault.json in the tree so restore has something.
        (_backup_env / "identity_vault.json").write_text('{"x": 1}')
        result = create_backup()

        restore_dir = Path(tempfile.mkdtemp())
        (restore_dir / "identity_vault.key").write_text("precious-existing-key")
        r = restore_backup(result["backup_path"], target_dir=str(restore_dir))
        assert r["status"] == "ok"
        # The archive contains no key, so the existing one is untouched.
        assert (restore_dir / "identity_vault.key").read_text() == "precious-existing-key"
        # Restored data landed.
        assert (restore_dir / "identity_vault.json").exists()


class TestAPIEndpoints:
    def test_backup_create_endpoint(self, _backup_env: Path) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from cores.api.routers import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.post("/api/core/backup/create")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "backup_path" in data

    def test_backup_list_endpoint(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from cores.api.routers import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.get("/api/core/backup/list")
        assert resp.status_code == 200
        data = resp.json()
        assert "backups" in data

    def test_backup_status_endpoint(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from cores.api.routers import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.get("/api/core/backup/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_backups" in data
        assert "backup_dir" in data
