"""Tests for credentials vault and health check."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.credentials.health import PLATFORMS, check_secrets_health
from core.credentials.vault import (
    backup_vault,
    get_credentials,
    get_platform_credentials,
    validate_credentials,
)


@pytest.fixture(autouse=True)
def _clear_credentials_singleton(monkeypatch):
    from core.credentials import vault as _vault

    _vault._credentials = None
    # Clear env vars that may be set in dev environment
    monkeypatch.delenv("FCC_API_KEY", raising=False)
    monkeypatch.delenv("FCC_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OMNIROUTE_API_KEY", raising=False)
    yield
    _vault._credentials = None


@pytest.fixture
def with_env(monkeypatch):
    monkeypatch.setenv("ALGORA_API_KEY", "test-algora-key")
    monkeypatch.setenv("GITHUB_TOKEN", "test-github-token")
    monkeypatch.setenv("OPIRE_API_KEY", "test-opire-key")
    monkeypatch.setenv("FREELANCER_API_KEY", "test-freelancer-key")
    monkeypatch.setenv("ISSUEHUNT_API_KEY", "test-issuehunt-key")
    return monkeypatch


class TestGetCredentials:
    def test_returns_singleton(self):
        c1 = get_credentials()
        c2 = get_credentials()
        assert c1 is c2

    def test_empty_by_default(self):
        c = get_credentials()
        for field_name in c.model_fields:
            assert getattr(c, field_name) == "" or getattr(c, field_name) == c.model_fields[field_name].default

    def test_reads_from_env(self, with_env):
        c = get_credentials()
        assert c.algora_api_key == "test-algora-key"
        assert c.github_token == "test-github-token"

    def test_reads_all_env_vars(self, with_env):
        c = get_credentials()
        assert c.opire_api_key == "test-opire-key"
        assert c.freelancer_api_key == "test-freelancer-key"
        assert c.issuehunt_api_key == "test-issuehunt-key"


class TestGetPlatformCredentials:
    def test_returns_empty_for_unknown_platform(self):
        assert get_platform_credentials("unknown") == {}

    def test_returns_algora_creds(self, with_env):
        creds = get_platform_credentials("algora")
        assert creds.get("api_key") == "test-algora-key"

    def test_returns_github_creds(self, with_env):
        creds = get_platform_credentials("github")
        assert creds.get("token") == "test-github-token"

    def test_returns_url_defaults_when_no_key(self):
        creds = get_platform_credentials("algora")
        # URL defaults have values even when no API key is set
        assert creds.get("api_key") is None or creds.get("api_key") == ""
        assert creds.get("api_url") == "https://api.algora.io"

    def test_handles_case_insensitive(self, with_env):
        creds = get_platform_credentials("ALGORA")
        assert creds.get("api_key") == "test-algora-key"


class TestValidateCredentials:
    def test_valid_platform_returns_true(self, with_env):
        valid, missing = validate_credentials("algora")
        assert valid is True
        assert missing == []

    def test_missing_token(self):
        valid, missing = validate_credentials("algora")
        assert valid is False
        assert "api_key" in missing

    def test_linkedin_requires_two_fields(self):
        valid, missing = validate_credentials("linkedin")
        assert valid is False
        assert "client_id" in missing
        assert "client_secret" in missing

    def test_unknown_platform(self, with_env):
        valid, missing = validate_credentials("nonexistent")
        assert valid is True


class TestBackupVault:
    def test_backup_creates_file(self, with_env, tmp_path):
        from core.credentials import vault as _vault

        original = _vault.Path
        _vault.Path = lambda *a, **kw: tmp_path

        import asyncio

        result = asyncio.run(backup_vault())

        assert result["success"] is True
        assert "path" in result
        assert result["fields"] > 0

        _vault.Path = original

    def test_backup_redacts_secrets(self, with_env, tmp_path):
        from core.credentials import vault as _vault

        original = _vault.Path
        _vault.Path = lambda *a, **kw: tmp_path

        import asyncio

        result = asyncio.run(backup_vault())

        backup_content = json.loads(Path(result["path"]).read_text())
        for _key, value in backup_content.items():
            assert "test" not in value.lower() or "redacted" in value

        _vault.Path = original


class TestCheckSecretsHealth:
    def test_returns_success_structure(self):
        import asyncio

        result = asyncio.run(check_secrets_health())

        assert result["success"] is True
        assert "total_fields" in result
        assert "populated_fields" in result
        assert "total_platforms" in result
        assert "populated_platforms" in result
        assert "coverage_pct" in result
        assert "platforms" in result
        assert "timestamp" in result

    def test_lists_all_platforms(self):
        import asyncio

        result = asyncio.run(check_secrets_health())
        for platform in PLATFORMS:
            assert platform in result["platforms"]

    def test_coverage_starts_low(self):
        import asyncio

        result = asyncio.run(check_secrets_health())
        assert result["coverage_pct"] < 50

    def test_reports_platform_health(self):
        import asyncio

        result = asyncio.run(check_secrets_health())
        for platform in PLATFORMS:
            entry = result["platforms"][platform]
            assert "valid" in entry
            assert "missing" in entry
