"""Tests for Hermes security layer."""

from __future__ import annotations

from apps.hermes.security import (
    sanitize_powershell,
    validate_action,
    validate_file_path,
    validate_shell_command,
)

# ── PowerShell sanitization ──────────────────────────────────────


def test_sanitize_powershell_clean() -> None:
    safe, reason = sanitize_powershell("Get-Service -Name 'Spooler'")
    assert safe is True
    assert reason == ""


def test_sanitize_powershell_injection_chaining() -> None:
    safe, reason = sanitize_powershell("Get-Service | Stop-Service")
    assert safe is False
    assert "security policy" in reason


def test_sanitize_powershell_encoded_command() -> None:
    safe, reason = sanitize_powershell("powershell -EncodedCommand SGVsbG8=")
    assert safe is False


def test_sanitize_powershell_invoke_expression() -> None:
    safe, reason = sanitize_powershell("Invoke-Expression 'malicious'")
    assert safe is False


def test_sanitize_powershell_remove_item_recurse() -> None:
    safe, reason = sanitize_powershell("Remove-Item -Recurse C:\\Windows")
    assert safe is False


def test_sanitize_powershell_start_process() -> None:
    safe, reason = sanitize_powershell("Start-Process cmd.exe")
    assert safe is False


def test_sanitize_powershell_add_type() -> None:
    safe, reason = sanitize_powershell("Add-Type -Path 'evil.dll'")
    assert safe is False


def test_sanitize_powershell_dotnet_reflection() -> None:
    safe, reason = sanitize_powershell("[System.Runtime.InteropServices]")
    assert safe is False


# ── File path validation ─────────────────────────────────────────


def test_validate_file_path_safe() -> None:
    safe, reason = validate_file_path("/home/user/projects")
    assert safe is True


def test_validate_file_path_blocked_boot() -> None:
    safe, reason = validate_file_path("/boot/grub/grub.cfg")
    assert safe is False


def test_validate_file_path_blocked_etc() -> None:
    safe, reason = validate_file_path("/etc/passwd")
    assert safe is False


def test_validate_file_path_blocked_sys() -> None:
    safe, reason = validate_file_path("/sys/class/whatever")
    assert safe is False


def test_validate_file_path_blocked_windows_system32() -> None:
    safe, reason = validate_file_path("C:\\Windows\\System32\\config")
    assert safe is False


# ── Shell command validation ─────────────────────────────────────


def test_validate_shell_command_safe() -> None:
    safe, reason = validate_shell_command("ls -la /home")
    assert safe is True


def test_validate_shell_command_rm_root() -> None:
    safe, reason = validate_shell_command("rm -rf /")
    assert safe is False


def test_validate_shell_command_mkfs() -> None:
    safe, reason = validate_shell_command("mkfs.ext4 /dev/sda1")
    assert safe is False


def test_validate_shell_command_dd() -> None:
    safe, reason = validate_shell_command("dd if=/dev/zero of=/dev/sda")
    assert safe is False


def test_validate_shell_command_shutdown() -> None:
    safe, reason = validate_shell_command("shutdown -h now")
    assert safe is False


def test_validate_shell_command_reboot() -> None:
    safe, reason = validate_shell_command("reboot")
    assert safe is False


# ── Full action validation ───────────────────────────────────────


def test_validate_action_kill_valid_pid() -> None:
    violations = validate_action("kill", pid=1234)
    assert len(violations) == 0


def test_validate_action_kill_invalid_pid() -> None:
    violations = validate_action("kill", pid=-1)
    assert len(violations) >= 1
    assert any("positive integer" in v for v in violations)


def test_validate_action_kill_pid_1() -> None:
    violations = validate_action("kill", pid=1)
    assert any("PID 1" in v for v in violations)


def test_validate_action_kill_pid_under_100() -> None:
    violations = validate_action("kill", pid=50)
    assert any("system PID" in v for v in violations)


def test_validate_action_with_powershell_injection() -> None:
    violations = validate_action("custom", powershell_command="Invoke-Expression 'bad'")
    assert len(violations) == 1


def test_validate_action_with_blocked_path() -> None:
    violations = validate_action("write", file_path="/etc/hosts")
    assert len(violations) == 1


def test_validate_action_with_destructive_command() -> None:
    violations = validate_action("run", shell_command="rm -rf /home")
    assert len(violations) == 1


def test_validate_action_safe_command() -> None:
    violations = validate_action("status")
    assert len(violations) == 0


def test_validate_action_multiple_violations() -> None:
    violations = validate_action("run", powershell_command="iex 'drop'", shell_command="rm -rf /")
    assert len(violations) == 2
