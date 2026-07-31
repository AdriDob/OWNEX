"""Tests for Version Backup System."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cores.recovery.persistence import reset_recovery_store
from cores.version_backup import (
    BackupResult,
    BackupStatus,
    VersionBackupSystem,
    VersionSnapshot,
    VersionState,
    get_version_backup_system,
    reset_version_backup_system,
)


@pytest.fixture
def temp_ownex_dir():
    """Create a temporary OWNEX directory with test files."""
    tmp = Path(tempfile.mkdtemp())

    # Create essential files
    (tmp / "database").mkdir(parents=True)
    (tmp / "database" / "ownex.db").write_text("fake db content")
    (tmp / "database" / "memory.db").write_text("fake memory content")
    (tmp / "config.json").write_text('{"key": "value"}')
    (tmp / ".env").write_text("API_KEY=test")
    (tmp / "identity_vault.key").write_text("fake-key-content-32bytes!!")
    (tmp / "targets").mkdir()
    (tmp / "targets" / "test-target").mkdir(parents=True)
    (tmp / "targets" / "test-target" / "recon.json").write_text('{"data": "test"}')
    (tmp / ".ai").mkdir()
    (tmp / ".ai" / "CURRENT_STATE.md").write_text("# Current State")
    (tmp / "cores").mkdir()
    (tmp / "cores" / "test.py").write_text("# test module")
    (tmp / "api").mkdir()
    (tmp / "api" / "main.py").write_text("# api main")
    (tmp / "frontend").mkdir()
    (tmp / "frontend" / "package.json").write_text('{"name": "test"}')
    (tmp / "scripts").mkdir()
    (tmp / "scripts" / "test.py").write_text("# test script")
    (tmp / "requirements.txt").write_text("requests==2.28.0")
    (tmp / "pyproject.toml").write_text("[project]")

    return tmp


@pytest.fixture
def backup_system(temp_ownex_dir):
    """Create a VersionBackupSystem instance with temp directory."""
    # Reset singletons before each test
    reset_version_backup_system()
    reset_recovery_store()

    system = VersionBackupSystem(ownex_dir=temp_ownex_dir)
    yield system

    # Cleanup after test
    reset_version_backup_system()
    reset_recovery_store()


class TestVersionBackupSystem:
    """Test VersionBackupSystem functionality."""

    def test_initialization(self, temp_ownex_dir):
        """Test system initialization."""
        reset_version_backup_system()
        reset_recovery_store()

        system = VersionBackupSystem(ownex_dir=temp_ownex_dir)

        assert system.ownex_dir == temp_ownex_dir
        assert system.backup_dir == temp_ownex_dir / ".ownex_backups"
        assert system.max_backups == 10
        assert system._recovery_store is not None

    def test_get_current_version(self, backup_system, temp_ownex_dir):
        """Test getting current version."""
        # Create a VERSION file
        (temp_ownex_dir / "VERSION").write_text("1.0.0")

        version = backup_system.get_current_version()
        assert version == "1.0.0"

    def test_get_current_version_fallback(self, backup_system):
        """Test getting current version fallback."""
        version = backup_system.get_current_version()
        assert version == "unknown"

    def test_create_backup(self, backup_system):
        """Test creating a backup."""
        result = backup_system.create_backup(notes="Test backup")

        assert result.status == BackupStatus.SUCCESS
        assert result.version == "unknown"
        assert result.backup_path != ""
        assert result.message == "Backup created successfully"
        assert "manifest" in result.__dict__
        assert result.manifest.get("total_files", 0) > 0

    def test_create_backup_with_notes(self, backup_system):
        """Test creating a backup with notes."""
        notes = "Pre-update backup before v2.0.0"
        result = backup_system.create_backup(notes=notes)

        assert result.status == BackupStatus.SUCCESS
        assert result.manifest.get("notes") == notes

    def test_create_backup_creates_directory(self, backup_system):
        """Test that backup creates directory structure."""
        result = backup_system.create_backup()

        backup_path = Path(result.backup_path)
        assert backup_path.exists()
        assert backup_path.is_dir()

        # Check for essential files
        assert (backup_path / "manifest.json").exists()
        assert (backup_path / "database").exists()
        assert (backup_path / "config.json").exists()

    def test_create_backup_manifest(self, backup_system):
        """Test that backup creates manifest."""
        result = backup_system.create_backup()

        manifest_path = Path(result.backup_path) / "manifest.json"
        assert manifest_path.exists()

        with open(manifest_path) as f:
            manifest = json.load(f)

        assert "version" in manifest
        assert "git_commit" in manifest
        assert "created_at" in manifest
        assert "backup_name" in manifest
        assert "files" in manifest
        assert "checksum" in manifest
        assert "size" in manifest

    def test_create_backup_checksum(self, backup_system):
        """Test that backup calculates checksum."""
        result = backup_system.create_backup()

        checksum = result.manifest.get("checksum")
        assert checksum != ""
        assert len(checksum) == 64  # SHA256 hex string

    def test_list_backups_empty(self, backup_system):
        """Test listing backups when none exist."""
        # Reset recovery store to ensure empty state
        reset_recovery_store()
        reset_version_backup_system()

        system = VersionBackupSystem(ownex_dir=backup_system.ownex_dir)
        backups = system.list_backups()
        assert backups == []

    def test_list_backups_after_create(self, backup_system):
        """Test listing backups after creating one."""
        backup_system.create_backup(notes="First backup")

        backups = backup_system.list_backups()
        assert len(backups) == 1
        assert backups[0]["version"] == "unknown"
        assert backups[0]["state"] == "backup"
        assert backups[0]["notes"] == "First backup"

    def test_list_backups_multiple(self, backup_system):
        """Test listing multiple backups."""
        backup_system.create_backup(notes="First backup")
        backup_system.create_backup(notes="Second backup")
        backup_system.create_backup(notes="Third backup")

        backups = backup_system.list_backups()
        assert len(backups) == 3

    def test_verify_backup_valid(self, backup_system):
        """Test verifying a valid backup."""
        result = backup_system.create_backup()

        verification = backup_system.verify_backup(result.backup_path)
        assert verification["valid"] == True
        assert verification["version"] == "unknown"
        assert "git_commit" in verification
        assert "created_at" in verification
        assert "size" in verification

    def test_verify_backup_invalid_path(self, backup_system):
        """Test verifying a backup with invalid path."""
        verification = backup_system.verify_backup("/nonexistent/path")
        assert verification["valid"] == False
        assert "error" in verification

    def test_verify_backup_missing_manifest(self, backup_system, temp_ownex_dir):
        """Test verifying a backup with missing manifest."""
        # Create a backup directory without manifest
        backup_path = temp_ownex_dir / ".ownex_backups" / "test_backup"
        backup_path.mkdir(parents=True)

        verification = backup_system.verify_backup(str(backup_path))
        assert verification["valid"] == False
        assert "Manifest not found" in verification["error"]

    def test_rollback_to_version(self, backup_system):
        """Test rollback to a specific version."""
        # Create initial backup
        backup_system.create_backup(notes="Initial state")

        # Modify a file
        (backup_system.ownex_dir / "config.json").write_text('{"modified": true}')

        # Get the backup to rollback to
        backups = backup_system.list_backups()
        assert len(backups) == 1

        # Rollback
        result = backup_system.rollback_to_version(version=backups[0]["version"])

        assert result["success"] == True
        assert result["version"] == "unknown"
        assert "Rollback completed successfully" in result["message"]

    def test_rollback_to_version_not_found(self, backup_system):
        """Test rollback to non-existent version."""
        result = backup_system.rollback_to_version(version="nonexistent")

        assert result["success"] == False
        assert "not found" in result["error"].lower()

    def test_restore_latest(self, backup_system):
        """Test restoring from latest backup."""
        backup_system.create_backup(notes="First backup")
        backup_system.create_backup(notes="Second backup")

        result = backup_system.restore_latest()

        assert result["success"] == True
        assert result["version"] == "unknown"

    def test_restore_latest_no_backups(self, backup_system):
        """Test restoring when no backups exist."""
        # Reset to ensure no backups
        reset_recovery_store()
        reset_version_backup_system()

        system = VersionBackupSystem(ownex_dir=backup_system.ownex_dir)
        result = system.restore_latest()

        assert result["success"] == False
        assert "No backups available" in result["error"]

    def test_cleanup_old_backups(self, backup_system):
        """Test automatic cleanup of old backups."""
        # Create more than max_backups
        for i in range(15):
            backup_system.create_backup(notes=f"Backup {i}")

        backups = backup_system.list_backups()
        assert len(backups) <= 10  # Should keep max 10

    def test_singleton_instance(self, temp_ownex_dir):
        """Test that get_version_backup_system returns singleton."""
        reset_version_backup_system()
        reset_recovery_store()

        system1 = get_version_backup_system()
        system2 = get_version_backup_system()

        assert system1 is system2

    def test_reset_singleton(self, temp_ownex_dir):
        """Test resetting singleton instance."""
        reset_version_backup_system()
        reset_recovery_store()

        system1 = get_version_backup_system()
        reset_version_backup_system()
        reset_recovery_store()
        system2 = get_version_backup_system()

        assert system1 is not system2


class TestVersionSnapshot:
    """Test VersionSnapshot dataclass."""

    def test_version_snapshot_creation(self):
        """Test creating a VersionSnapshot."""
        snapshot = VersionSnapshot(
            version="1.0.0",
            git_commit="abc123",
            created_at="2024-01-01T00:00:00",
            state=VersionState.BACKUP,
            backup_path="/path/to/backup",
            checksum="sha256sum",
            size=1024,
            notes="Test backup",
        )

        assert snapshot.version == "1.0.0"
        assert snapshot.git_commit == "abc123"
        assert snapshot.state == VersionState.BACKUP
        assert snapshot.backup_path == "/path/to/backup"
        assert snapshot.checksum == "sha256sum"
        assert snapshot.size == 1024
        assert snapshot.notes == "Test backup"


class TestBackupResult:
    """Test BackupResult dataclass."""

    def test_backup_result_success(self):
        """Test creating a successful BackupResult."""
        result = BackupResult(
            status=BackupStatus.SUCCESS,
            version="1.0.0",
            backup_path="/path/to/backup",
            message="Backup created successfully",
            manifest={"version": "1.0.0"},
        )

        assert result.status == BackupStatus.SUCCESS
        assert result.version == "1.0.0"
        assert result.backup_path == "/path/to/backup"
        assert result.message == "Backup created successfully"

    def test_backup_result_failure(self):
        """Test creating a failed BackupResult."""
        result = BackupResult(
            status=BackupStatus.FAILED,
            version="1.0.0",
            error="Insufficient disk space",
        )

        assert result.status == BackupStatus.FAILED
        assert result.error == "Insufficient disk space"
