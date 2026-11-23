from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

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


def test_execute_routes_to_fallback_without_docker(monkeypatch, tmp_path: Path):
    sandbox = Sandbox(SandboxConfig())
    monkeypatch.setattr(sandbox, "_docker_available", False)
    called = {}

    async def fake_fallback(command, input_data=None, timeout=None):
        called["command"] = command
        from core.security.sandbox import SandboxResult

        return SandboxResult(success=True, output="fallback")

    monkeypatch.setattr(sandbox, "_fallback_execute", fake_fallback)
    result = asyncio.run(sandbox.execute(tmp_path, ["echo", "hi"]))
    assert called["command"] == ["echo", "hi"]
    assert result.output == "fallback"


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


def test_broker_drops_expired_credentials():
    broker = CredentialBroker()
    broker.assign_project_credentials("alpha", ["github"], {"github": "ghp_alphatoken12"}, expires_in_hours=-1)
    assert asyncio.run(broker.get_credential("alpha", "github")) is None
    assert broker.get_stats()["expired_credentials"] == 1
    assert broker.get_project_credentials_summary("alpha")["count"] == 0


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
