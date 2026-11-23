from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from core.opportunity.executors import BaseExecutor
from core.security import (
    AccessLevel,
    CredentialBroker,
    ProjectScopedCredential,
    Sandbox,
    SandboxConfig,
    get_credential_broker,
)

# === Sandbox ===


def test_sandbox_config_defaults_deny_network_and_capabilities():
    config = SandboxConfig()
    assert config.ENABLE_NETWORK is False
    assert config.ALLOWED_PORTS == ()
    assert config.DROP_CAPABILITIES == ("ALL",)
    assert config.DISABLE_PRIVILEGED is True
    assert config.READ_ONLY_ROOTFILESYSTEM is True
    assert config.PROHIBIT_DOCKER_SOCKET is True


def test_docker_args_enforce_isolation_policy(tmp_path: Path):
    sandbox = Sandbox(SandboxConfig())
    args = sandbox._build_docker_args(tmp_path, ["python", "-V"])

    assert args[:2] == ["run", "--rm"]
    assert "--network=none" in args
    assert "--read-only" in args
    assert "--cap-drop" in args and "ALL" in args
    assert "--cap-add" not in args
    assert "--privileged" not in args
    assert not any("docker.sock" in arg for arg in args)
    assert f"{tmp_path.resolve()}:/work:ro" in args
    assert args[-2:] == ["python", "-V"]


def test_docker_args_use_configured_image_and_ports():
    config = SandboxConfig()
    config.ENABLE_NETWORK = True
    config.ALLOWED_PORTS = (8443,)
    config.DOCKER_IMAGE = "custom/image:1"
    args = Sandbox(config)._build_docker_args(Path("/tmp"), ["true"])

    assert "--network=bridge" in args
    assert "8443:8443" in args
    assert "custom/image:1" in args


def test_fallback_execute_captures_output():
    sandbox = Sandbox(SandboxConfig())
    result = asyncio.run(
        sandbox._fallback_execute(["/bin/sh", "-c", "echo honey"]),
    )
    assert result.success is True
    assert result.output.strip() == "honey"
    assert result.exit_code == 0


def test_fallback_execute_reports_failure_exit_code():
    sandbox = Sandbox(SandboxConfig())
    result = asyncio.run(sandbox._fallback_execute(["/bin/sh", "-c", "exit 7"]))
    assert result.success is False
    assert result.exit_code == 7


def test_fallback_execute_enforces_timeout():
    sandbox = Sandbox(SandboxConfig())
    result = asyncio.run(sandbox._fallback_execute(["/bin/sh", "-c", "sleep 5"], timeout=1))
    assert result.success is False
    assert result.exit_code == 124
    assert "timed out" in result.error


def test_execute_fails_closed_without_docker(monkeypatch, tmp_path: Path):
    """Untrusted-code path must never fall back to a host subprocess."""
    sandbox = Sandbox(SandboxConfig())
    monkeypatch.setattr(sandbox, "_docker_available", False)
    result = asyncio.run(sandbox.execute(tmp_path, ["echo", "hi"]))
    assert result.success is False
    assert result.exit_code == -1
    assert "fail-closed" in result.error


def test_execute_fails_closed_when_daemon_down(monkeypatch, tmp_path: Path):
    sandbox = Sandbox(SandboxConfig())
    monkeypatch.setattr(sandbox, "_docker_available", True)
    monkeypatch.setattr(sandbox, "_daemon_ok", False)
    result = asyncio.run(sandbox.execute(tmp_path, ["echo", "hi"]))
    assert result.success is False
    assert "fail-closed" in result.error


def test_build_docker_args_writable_and_network_overrides(tmp_path: Path):
    sandbox = Sandbox(SandboxConfig())
    args = sandbox._build_docker_args(tmp_path, ["true"], writable=True, network=True)
    assert f"{tmp_path.resolve()}:/work:rw" in args
    assert "--network=bridge" in args
    # read-only default preserved
    args_ro = sandbox._build_docker_args(tmp_path, ["true"])
    assert f"{tmp_path.resolve()}:/work:ro" in args_ro
    assert "--network=none" in args_ro


# === Credential broker ===


def test_project_credential_mask_never_leaks_value():
    cred = ProjectScopedCredential(project_id="p1", provider="github", credential_type="token", value="ghp_secretvalue1234")
    masked = cred.mask()
    assert masked.startswith("ghp_")
    assert masked.endswith("1234")
    assert "secretvalue" not in masked


def test_project_credential_short_values_fully_masked():
    cred = ProjectScopedCredential(project_id="p1", provider="npm", credential_type="password", value="abc")
    assert cred.mask() == "***"


def test_project_credential_expiration():
    expired = ProjectScopedCredential(
        project_id="p1",
        provider="github",
        credential_type="token",
        value="x" * 12,
        expires_at=time.time() - 1,
    )
    assert expired.is_expired() is True
    assert expired.can_use(AccessLevel.READ_ONLY) is False


def test_broker_isolates_credentials_between_projects():
    broker = CredentialBroker()
    broker.assign_project_credentials("alpha", ["github"], {"github": "ghp_alphatoken12"})

    granted = asyncio.run(broker.get_credential("alpha", "github"))
    denied = asyncio.run(broker.get_credential("beta", "github"))

    assert granted is not None
    assert granted.value == "ghp_alphatoken12"
    assert denied is None
    stats = broker.get_stats()
    assert stats["granted_requests"] == 1
    assert stats["denied_requests"] == 1


def test_broker_denies_insufficient_access_level():
    broker = CredentialBroker()
    broker.assign_project_credentials("alpha", ["github"], {"github": "ghp_alphatoken12"}, access_level=AccessLevel.READ_ONLY)
    assert asyncio.run(broker.get_credential("alpha", "github", AccessLevel.EXECUTION)) is None
    assert broker.get_stats()["denied_requests"] == 1


def test_broker_refuses_expired_credentials_but_keeps_the_assignment():
    broker = CredentialBroker()
    broker.assign_project_credentials("alpha", ["github"], {"github": "ghp_alphatoken12"}, expires_in_hours=-1)
    assert asyncio.run(broker.get_credential("alpha", "github")) is None
    assert broker.get_stats()["expired_credentials"] == 1
    # The expired assignment stays visible so callers fail closed.
    summary = broker.get_project_credentials_summary("alpha")
    assert summary["count"] == 1
    assert summary["providers"]["github"]["expired"] is True
    assert broker.has_credential("alpha", "github") is True


def test_broker_summary_is_masked():
    broker = CredentialBroker()
    broker.assign_project_credentials(
        "alpha",
        ["github", "aws"],
        {"github": "ghp_alphatoken12", "aws": "AKIAsecretvalue99"},
        access_level=AccessLevel.EXECUTION,
    )
    summary = broker.get_project_credentials_summary("alpha")
    assert summary["count"] == 2
    dumped = repr(summary)
    assert "ghp_alphatoken12" not in dumped
    assert "AKIAsecretvalue99" not in dumped
    assert summary["providers"]["github"]["access_level"] == "execution"


def test_execute_with_credentials_passes_secret_to_callback_only():
    broker = CredentialBroker()
    broker.assign_project_credentials("alpha", ["github"], {"github": "ghp_alphatoken12"}, access_level=AccessLevel.EXECUTION)
    seen: list[str] = []

    def callback(secret: str) -> str:
        seen.append(secret)
        return "done"

    result = asyncio.run(broker.execute_with_credentials("alpha", "github", callback, timeout=5))
    assert result == "done"
    assert seen == ["ghp_alphatoken12"]


def test_execute_with_credentials_raises_when_missing():
    broker = CredentialBroker()
    with pytest.raises(ValueError, match="Cannot get credential"):
        asyncio.run(broker.execute_with_credentials("ghost", "github", lambda secret: secret))


def test_get_credential_broker_is_singleton():
    assert get_credential_broker() is get_credential_broker()


# === Executor <-> broker wiring ===


class _GithubExecutor(BaseExecutor):
    """BaseExecutor subclass with a github credential source, for wiring tests."""

    platform = "wiring-test"
    credential_sources = {"github": "github_token"}


def test_executor_denies_unscoped_fallback_by_default():
    executor = _GithubExecutor({"project_id": "wiring-deny", "github_token": "cfg-token"})
    assert executor.credential("github") is None


def test_executor_falls_back_to_config_when_project_has_no_assignment():
    executor = _GithubExecutor({"project_id": "wiring-fallback", "github_token": "cfg-token", "allow_unscoped_credentials": True})
    assert executor.credential("github") == "cfg-token"


def test_executor_falls_back_to_env_when_config_is_empty(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    executor = _GithubExecutor({"project_id": "wiring-env", "allow_unscoped_credentials": True})
    assert executor.credential("github") == "env-token"


def test_executor_returns_none_without_any_credential(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    executor = _GithubExecutor({"project_id": "wiring-none"})
    assert executor.credential("github") is None


def test_broker_assignment_wins_over_config_secret():
    executor = _GithubExecutor({"project_id": "wiring-scoped", "github_token": "cfg-token"})
    get_credential_broker().assign_project_credentials("wiring-scoped", ["github"], {"github": "broker-token"}, access_level=AccessLevel.EXECUTION)
    assert executor.credential("github") == "broker-token"


def test_expired_assignment_fails_closed_instead_of_using_global_secret():
    executor = _GithubExecutor({"project_id": "wiring-expired", "github_token": "cfg-token"})
    get_credential_broker().assign_project_credentials(
        "wiring-expired",
        ["github"],
        {"github": "broker-token"},
        expires_in_hours=-1,
        access_level=AccessLevel.EXECUTION,
    )
    assert executor.credential("github") is None


def test_under_privileged_assignment_fails_closed():
    executor = _GithubExecutor({"project_id": "wiring-level", "github_token": "cfg-token"})
    get_credential_broker().assign_project_credentials("wiring-level", ["github"], {"github": "broker-token"}, access_level=AccessLevel.READ_ONLY)
    assert executor.credential("github") is None
    assert executor.credential("github", AccessLevel.READ_ONLY) == "broker-token"


def test_executor_does_not_cache_the_secret():
    executor = _GithubExecutor({"project_id": "wiring-nocache", "github_token": "cfg-token", "allow_unscoped_credentials": True})
    assert executor.credential("github") == "cfg-token"
    get_credential_broker().assign_project_credentials("wiring-nocache", ["github"], {"github": "scoped-token"}, access_level=AccessLevel.EXECUTION)
    assert executor.credential("github") == "scoped-token"
