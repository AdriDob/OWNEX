"""Tests for credential rotation system."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from core.credentials.vault import (
    _AUTO_REFRESH_PLATFORMS,
    _DEFAULT_FAILED_AUTH_THRESHOLD,
    _DEFAULT_MAX_AGE_DAYS,
    _DEFAULT_WARNING_DAYS,
    _MANUAL_ROTATION_PLATFORMS,
    _get_platform_rotation_state,
    _load_rotation_config,
    _save_rotation_config,
    _update_platform_rotation_state,
    auto_rotate_all,
    check_rotation_needs,
    get_expiring_credentials,
    record_failed_auth,
    rotate_credential_with_backup,
    set_credential_expiration,
)


@pytest.fixture
def clean_rotation_config(tmp_path: Path):
    """Provide a clean rotation config file for each test."""
    config_path = tmp_path / "credential_rotation.json"
    with patch("core.credentials.vault._ROTATION_CONFIG_PATH", config_path):
        yield config_path


class TestLoadRotationConfig:
    def test_returns_default_when_file_missing(self, clean_rotation_config):
        """Should return default config when file doesn't exist."""
        config = _load_rotation_config()
        assert config["max_age_days"] == _DEFAULT_MAX_AGE_DAYS
        assert config["warning_days"] == _DEFAULT_WARNING_DAYS
        assert config["failed_auth_threshold"] == _DEFAULT_FAILED_AUTH_THRESHOLD
        assert config["platforms"] == {}

    def test_returns_existing_config(self, clean_rotation_config):
        """Should return existing config when file exists."""
        clean_rotation_config.write_text(
            json.dumps(
                {
                    "max_age_days": 60,
                    "warning_days": 5,
                    "failed_auth_threshold": 5,
                    "platforms": {"github": {"last_rotated": "2026-01-01T00:00:00Z"}},
                }
            )
        )
        config = _load_rotation_config()
        assert config["max_age_days"] == 60
        assert config["warning_days"] == 5
        assert config["failed_auth_threshold"] == 5
        assert "github" in config["platforms"]

    def test_handles_corrupt_file(self, clean_rotation_config):
        """Should return default config when file is corrupt."""
        clean_rotation_config.write_text("invalid json")
        config = _load_rotation_config()
        assert config["max_age_days"] == _DEFAULT_MAX_AGE_DAYS


class TestSaveRotationConfig:
    def test_saves_config_to_file(self, clean_rotation_config):
        """Should save config to file."""
        config = {"max_age_days": 45, "platforms": {}}
        _save_rotation_config(config)
        assert clean_rotation_config.exists()
        loaded = json.loads(clean_rotation_config.read_text())
        assert loaded["max_age_days"] == 45


class TestGetPlatformRotationState:
    def test_returns_default_state_for_new_platform(self, clean_rotation_config):
        """Should return default state for platform with no history."""
        state = _get_platform_rotation_state("github")
        assert state["last_rotated"] is None
        assert state["failed_auth_count"] == 0
        assert state["expiration_date"] is None

    def test_returns_existing_state(self, clean_rotation_config):
        """Should return existing state for platform with history."""
        clean_rotation_config.write_text(
            json.dumps(
                {
                    "max_age_days": 90,
                    "platforms": {
                        "github": {
                            "last_rotated": "2026-01-01T00:00:00Z",
                            "failed_auth_count": 2,
                        }
                    },
                }
            )
        )
        state = _get_platform_rotation_state("github")
        assert state["last_rotated"] == "2026-01-01T00:00:00Z"
        assert state["failed_auth_count"] == 2


class TestUpdatePlatformRotationState:
    def test_updates_platform_state(self, clean_rotation_config):
        """Should update platform state in config."""
        new_state = {
            "last_rotated": "2026-08-04T12:00:00Z",
            "failed_auth_count": 0,
            "expiration_date": None,
        }
        _update_platform_rotation_state("github", new_state)
        state = _get_platform_rotation_state("github")
        assert state["last_rotated"] == "2026-08-04T12:00:00Z"


class TestCheckRotationNeeds:
    def test_no_rotation_needed_for_new_credential(self, clean_rotation_config):
        """Should not require rotation for new credential."""
        result = check_rotation_needs("github")
        assert result["needs_rotation"] is False
        assert result["reason"] is None

    def test_rotation_needed_on_failed_auth_threshold(self, clean_rotation_config):
        """Should require rotation when failed auth count exceeds threshold."""
        _update_platform_rotation_state(
            "github",
            {
                "last_rotated": None,
                "failed_auth_count": 3,
                "expiration_date": None,
            },
        )
        result = check_rotation_needs("github")
        assert result["needs_rotation"] is True
        assert "Failed auth count" in result["reason"]

    def test_rotation_needed_on_age_exceeded(self, clean_rotation_config):
        """Should require rotation when credential age exceeds max."""
        old_date = (datetime.now(UTC) - timedelta(days=91)).isoformat()
        _update_platform_rotation_state(
            "github",
            {
                "last_rotated": old_date,
                "failed_auth_count": 0,
                "expiration_date": None,
            },
        )
        result = check_rotation_needs("github")
        assert result["needs_rotation"] is True
        assert "age" in result["reason"].lower()

    def test_warning_on_approaching_expiration(self, clean_rotation_config):
        """Should warn when approaching expiration threshold."""
        old_date = (datetime.now(UTC) - timedelta(days=85)).isoformat()
        _update_platform_rotation_state(
            "github",
            {
                "last_rotated": old_date,
                "failed_auth_count": 0,
                "expiration_date": None,
            },
        )
        result = check_rotation_needs("github")
        assert result["needs_rotation"] is False
        assert result["days_until_expiration"] == 5

    def test_rotation_needed_on_explicit_expiration(self, clean_rotation_config):
        """Should require rotation when explicit expiration date passed."""
        past_date = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        _update_platform_rotation_state(
            "github",
            {
                "last_rotated": None,
                "failed_auth_count": 0,
                "expiration_date": past_date,
            },
        )
        result = check_rotation_needs("github")
        assert result["needs_rotation"] is True
        assert "expired" in result["reason"].lower()


class TestRecordFailedAuth:
    def test_increments_failed_auth_count(self, clean_rotation_config):
        """Should increment failed auth counter."""
        result = record_failed_auth("github")
        assert result["success"] is True
        assert result["failed_auth_count"] == 1

    def test_signals_rotation_required_on_threshold(self, clean_rotation_config):
        """Should signal rotation required when threshold reached."""
        # Set count to threshold - 1
        _update_platform_rotation_state(
            "github",
            {
                "last_rotated": None,
                "failed_auth_count": 2,
                "expiration_date": None,
            },
        )
        result = record_failed_auth("github")
        assert result["rotation_required"] is True
        assert result["failed_auth_count"] == 3


class TestSetCredentialExpiration:
    def test_sets_expiration_date(self, clean_rotation_config):
        """Should set expiration date for platform."""
        future_date = "2026-12-31T23:59:59Z"
        result = set_credential_expiration("github", future_date)
        assert result["success"] is True
        state = _get_platform_rotation_state("github")
        assert state["expiration_date"] == future_date

    def test_rejects_invalid_date_format(self, clean_rotation_config):
        """Should reject invalid date format."""
        result = set_credential_expiration("github", "invalid-date")
        assert result["success"] is False
        assert "Invalid" in result["error"]


class TestGetExpiringCredentials:
    def test_returns_empty_when_none_expiring(self, clean_rotation_config):
        """Should return empty list when no credentials expiring."""
        result = get_expiring_credentials(7)
        assert result["expiring_count"] == 0
        assert result["credentials"] == []

    def test_includes_expiring_credentials(self, clean_rotation_config):
        """Should include credentials expiring within threshold."""
        # Set expiration to 5 days from now
        future_date = (datetime.now(UTC) + timedelta(days=5)).isoformat()
        _update_platform_rotation_state(
            "github",
            {
                "last_rotated": None,
                "failed_auth_count": 0,
                "expiration_date": future_date,
            },
        )
        result = get_expiring_credentials(7)
        assert result["expiring_count"] == 1
        assert result["credentials"][0]["platform"] == "github"

    def test_excludes_credentials_beyond_threshold(self, clean_rotation_config):
        """Should exclude credentials beyond threshold."""
        # Set expiration to 10 days from now
        future_date = (datetime.now(UTC) + timedelta(days=10)).isoformat()
        _update_platform_rotation_state(
            "github",
            {
                "last_rotated": None,
                "failed_auth_count": 0,
                "expiration_date": future_date,
            },
        )
        result = get_expiring_credentials(7)
        assert result["expiring_count"] == 0


class TestRotateCredentialWithBackup:
    @pytest.mark.asyncio
    @patch("core.credentials.vault.backup_vault")
    @patch("core.credentials.vault._auto_refresh_credential")
    @patch("core.credentials.vault._publish_rotation_event")
    async def test_auto_refresh_success(self, mock_publish, mock_refresh, mock_backup, clean_rotation_config):
        """Should successfully auto-refresh for supported platforms."""
        mock_backup.return_value = {"success": True, "path": "/backup/path"}
        mock_refresh.return_value = {"success": True}

        result = await rotate_credential_with_backup("github")
        assert result["success"] is True
        assert result["method"] == "auto_refresh"
        assert result["backup_path"] == "/backup/path"

    @pytest.mark.asyncio
    @patch("core.credentials.vault.backup_vault")
    @patch("core.credentials.vault._publish_rotation_event")
    async def test_manual_platform_generates_alert(self, mock_publish, mock_backup, clean_rotation_config):
        """Should generate alert for manual rotation platforms."""
        mock_backup.return_value = {"success": True, "path": "/backup/path"}

        result = await rotate_credential_with_backup("hackerone")
        assert result["success"] is True
        assert result["method"] == "manual_alert"
        assert "Manual rotation required" in result["message"]

    @pytest.mark.asyncio
    @patch("core.credentials.vault.backup_vault")
    async def test_fails_on_backup_error(self, mock_backup, clean_rotation_config):
        """Should fail when backup fails."""
        mock_backup.return_value = {"success": False, "error": "Backup failed"}

        result = await rotate_credential_with_backup("github")
        assert result["success"] is False
        assert "Backup failed" in result["error"]


class TestAutoRotateAll:
    @pytest.mark.asyncio
    @patch("core.credentials.vault.rotate_credential_with_backup")
    @patch("core.credentials.vault.check_rotation_needs")
    async def test_rotates_platforms_needing_rotation(self, mock_check, mock_rotate, clean_rotation_config):
        """Should rotate only platforms that need it."""
        mock_check.side_effect = lambda p: {"needs_rotation": p == "github"}
        mock_rotate.return_value = {"success": True, "action": "rotated"}

        result = await auto_rotate_all()
        assert result["success"] is True
        assert result["rotated"] == 1
        mock_rotate.assert_called_once_with("github")

    @pytest.mark.asyncio
    @patch("core.credentials.vault.check_rotation_needs")
    async def test_skips_platforms_not_needing_rotation(self, mock_check, clean_rotation_config):
        """Should skip platforms that don't need rotation."""
        mock_check.return_value = {"needs_rotation": False}

        result = await auto_rotate_all()
        assert result["success"] is True
        assert result["rotated"] == 0


class TestPlatformConstants:
    def test_auto_refresh_platforms_defined(self):
        """Should have auto-refresh platforms defined."""
        assert "github" in _AUTO_REFRESH_PLATFORMS

    def test_manual_rotation_platforms_defined(self):
        """Should have manual rotation platforms defined."""
        assert "hackerone" in _MANUAL_ROTATION_PLATFORMS
        assert "bugcrowd" in _MANUAL_ROTATION_PLATFORMS
        assert "intigriti" in _MANUAL_ROTATION_PLATFORMS
