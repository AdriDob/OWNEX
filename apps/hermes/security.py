"""Hermes Security — PowerShell sanitization, command validation, destructive action protection."""

from __future__ import annotations

import re
from typing import Any

# ── PowerShell injection patterns ──────────────────────────────────

_PS_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"[;|&`$(){}\[\]]"),  # command chaining / expansion
    re.compile(r"-EncodedCommand", re.I),  # encoded command execution
    re.compile(r"Invoke-Expression|iex", re.I),
    re.compile(r"Start-Process", re.I),
    re.compile(r"New-Object", re.I),
    re.compile(r"Add-Type", re.I),
    re.compile(r"\[System\.", re.I),  # .NET reflection
    re.compile(r"Set-ExecutionPolicy", re.I),
    re.compile(r"Remove-Item\s+-Recurse", re.I),
    re.compile(r"Format-Volume|Clear-Disk", re.I),
    re.compile(r"Restart-Computer|Stop-Computer", re.I),
    re.compile(r"Disable-BitLocker", re.I),
    re.compile(r"Set-MpPreference", re.I),  # disable defender
]

# ── Destructive system operations (block in safe mode) ────────────

_BLOCKED_PATHS: list[re.Pattern[str]] = [
    re.compile(r"/boot/?"),
    re.compile(r"/etc/?"),
    re.compile(r"/sys/?"),
    re.compile(r"/proc/?"),
    re.compile(r"C:\\Windows\\System32", re.I),
    re.compile(r"/dev/?"),
]

_BLOCKED_COMMANDS: list[str] = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=",
    "format",
    "fdisk",
    "mkswap",
    "shutdown",
    "reboot",
    "init 0",
    "init 6",
]


def sanitize_powershell(command: str) -> tuple[bool, str]:
    """Check a PowerShell command for injection patterns.

    Returns:
        (safe, reason) — safe=True if no injection detected.
    """
    for pat in _PS_INJECTION_PATTERNS:
        m = pat.search(command)
        if m:
            return False, "Blocked by PowerShell security policy: matched pattern"
    return True, ""


def validate_file_path(path: str) -> tuple[bool, str]:
    """Check if a file path targets a blocked system location."""
    for pat in _BLOCKED_PATHS:
        if pat.search(path):
            return False, f"Path targets protected system area: {pat.pattern}"
    return True, ""


def validate_shell_command(command: str) -> tuple[bool, str]:
    """Check if a shell command is blocked for destructive operations."""
    cmd_lower = command.strip().lower()
    for blocked in _BLOCKED_COMMANDS:
        if cmd_lower.startswith(blocked) or blocked in cmd_lower:
            return False, f"Blocked destructive command: {blocked}"
    return True, ""


def validate_action(command: str, **kwargs: Any) -> list[str]:
    """Run all security validations for a Hermes action.

    Returns:
        List of violation messages. Empty list = action is safe.
    """
    violations: list[str] = []

    if command == "kill":
        pid = kwargs.get("pid", 0)
        if isinstance(pid, int) and pid <= 0:
            violations.append("Invalid PID — must be a positive integer")
        if isinstance(pid, int) and pid == 1:
            violations.append("Blocked: cannot kill PID 1 (init/systemd)")
        if isinstance(pid, int) and 0 < pid < 100:
            violations.append("Warning: targeting a system PID (< 100)")

    ps_command = kwargs.get("powershell_command", "")
    if ps_command:
        safe, reason = sanitize_powershell(ps_command)
        if not safe:
            violations.append(reason)

    file_path = kwargs.get("file_path", "")
    if file_path:
        safe, reason = validate_file_path(file_path)
        if not safe:
            violations.append(reason)

    shell_cmd = kwargs.get("shell_command", "")
    if shell_cmd:
        safe, reason = validate_shell_command(shell_cmd)
        if not safe:
            violations.append(reason)

    return violations
