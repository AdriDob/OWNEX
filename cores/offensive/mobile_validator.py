"""Mobile on-device validator — executes the checks that static reasoners can't.

The mobile reasoners (deeplink/data-exposure/transport) analyze the
server-visible API surface. The checks below require a real device or
emulator plus external tools (adb, frida, objection). This module is the
honest bridge between the two:

- Tool present + device connected → executes the real check → PASS/FAIL.
- Tool missing → UNAVAILABLE (never FAIL, never PASS).
- Device absent / command times out → INCONCLUSIVE with next steps.
- Nothing installed → every check explains exactly what to install.

Design rules (no exceptions):
- No subprocess call without an explicit timeout and without shell.
- No PASS verdict without executing the underlying check.
- UNAVAILABLE must always carry manual_steps so a hunter without
  tooling can still verify by hand.

This module is hunter-invoked. It is deliberately NOT wired into the
scheduler or the reasoners: reasoners must stay pure/static (they run
headless), and external tools must never execute autonomously.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("orion.core.offensive.mobile_validator")

DEFAULT_TIMEOUT_S = 30

# External tools this validator can drive. Missing tool -> UNAVAILABLE.
TOOLS = ("adb", "frida", "frida-ps", "objection")


@dataclass
class DeviceVerdict:
    """Outcome of one on-device check."""

    status: str  # PASS | FAIL | INCONCLUSIVE | UNAVAILABLE | NOT_APPLICABLE
    tool: str
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    manual_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "tool": self.tool,
            "detail": self.detail,
            "evidence": self.evidence,
            "manual_steps": self.manual_steps,
        }


class MobileDeviceValidator:
    """Runs on-device mobile checks with honest degradation."""

    def __init__(self, timeout_s: int = DEFAULT_TIMEOUT_S) -> None:
        self.timeout_s = timeout_s
        self._tool_cache: dict[str, bool] = {}

    # ── Tool availability ──────────────────────────────────────

    def is_tool_available(self, tool: str) -> bool:
        """True iff the binary resolves on PATH (cached per instance)."""
        if tool not in self._tool_cache:
            self._tool_cache[tool] = shutil.which(tool) is not None
        return self._tool_cache[tool]

    def tools_status(self) -> dict[str, bool]:
        """Availability matrix for all supported tools."""
        return {tool: self.is_tool_available(tool) for tool in TOOLS}

    # ── Execution helper ───────────────────────────────────────

    def _run(self, tool: str, args: list[str], timeout_s: int | None = None) -> tuple[bool, str]:
        """Run an external tool. Returns (ok, output).

        ok=False covers: tool missing, timeout, non-zero exit, OSError.
        Never raises.
        """
        if not self.is_tool_available(tool):
            return False, f"tool not installed: {tool}"
        try:
            completed = subprocess.run(
                [tool, *args],
                capture_output=True,
                text=True,
                timeout=timeout_s if timeout_s is not None else self.timeout_s,
                shell=False,
            )
        except FileNotFoundError:
            self._tool_cache[tool] = False
            return False, f"tool not installed: {tool}"
        except subprocess.TimeoutExpired:
            return False, f"timed out after {timeout_s or self.timeout_s}s"
        except OSError as exc:
            return False, f"execution failed: {exc}"
        if completed.returncode != 0:
            err = (completed.stderr or "").strip()[:500]
            return False, f"exit {completed.returncode}: {err}"
        return True, (completed.stdout or "").strip()

    # ── Checks ─────────────────────────────────────────────────

    def check_adb_devices(self) -> DeviceVerdict:
        """Is there at least one device/emulator reachable via adb?"""
        if not self.is_tool_available("adb"):
            return DeviceVerdict(
                status="UNAVAILABLE",
                tool="adb",
                detail="adb not installed; cannot enumerate devices",
                manual_steps=[
                    "Install Android platform-tools (SDK) for your OS.",
                    "Enable USB debugging on the test device (never a personal device).",
                    "Run `adb devices` and confirm the device lists as 'device'.",
                ],
            )
        ok, out = self._run("adb", ["devices", "-l"])
        if not ok:
            return DeviceVerdict(status="INCONCLUSIVE", tool="adb", detail=out)
        devices = [line for line in out.splitlines()[1:] if line.strip() and "offline" not in line]
        if not devices:
            return DeviceVerdict(
                status="INCONCLUSIVE",
                tool="adb",
                detail="adb works but no device connected",
                evidence={"raw": out[:500]},
                manual_steps=["Connect a test device or start an emulator, then re-run."],
            )
        return DeviceVerdict(
            status="PASS",
            tool="adb",
            detail=f"{len(devices)} device(s) reachable",
            evidence={"devices": [d.split()[0] for d in devices]},
        )

    def check_app_installed(self, package: str) -> DeviceVerdict:
        """Is the target package installed on the connected device?"""
        device = self.check_adb_devices()
        if device.status != "PASS":
            return DeviceVerdict(
                status=device.status,
                tool="adb",
                detail=f"cannot check package without a device ({device.detail})",
                manual_steps=device.manual_steps,
            )
        ok, out = self._run("adb", ["shell", "pm", "list", "packages", package])
        if not ok:
            return DeviceVerdict(status="INCONCLUSIVE", tool="adb", detail=out)
        installed = f"package:{package}" in out
        return DeviceVerdict(
            status="PASS" if installed else "FAIL",
            tool="adb",
            detail=f"package {package} {'installed' if installed else 'NOT installed on device'}",
            evidence={"package": package, "raw": out[:300]},
        )

    def check_frida_server(self) -> DeviceVerdict:
        """Is frida-server running on the connected device?"""
        device = self.check_adb_devices()
        if device.status != "PASS":
            return DeviceVerdict(
                status=device.status,
                tool="frida",
                detail=f"cannot probe frida-server without a device ({device.detail})",
                manual_steps=device.manual_steps,
            )
        if not self.is_tool_available("frida-ps"):
            return DeviceVerdict(
                status="UNAVAILABLE",
                tool="frida-ps",
                detail="frida-tools not installed on host",
                manual_steps=[
                    "Install frida-tools on the host (`pip install frida-tools`).",
                    "Push a matching frida-server binary to the test device and run it as root.",
                    "Re-run; `frida-ps -U` must list processes.",
                ],
            )
        ok, out = self._run("frida-ps", ["-U"])
        if not ok:
            return DeviceVerdict(
                status="INCONCLUSIVE",
                tool="frida-ps",
                detail=out,
                manual_steps=["Start frida-server on the device, then re-run."],
            )
        procs = [line for line in out.splitlines() if line.strip()]
        return DeviceVerdict(
            status="PASS",
            tool="frida-ps",
            detail=f"frida-server reachable ({len(procs)} processes listed)",
            evidence={"process_count": len(procs)},
        )

    def check_pinning_enforced(self, package: str, host: str) -> DeviceVerdict:
        """Does the app enforce certificate pinning for host?

        Method: with traffic routed through an intercepting proxy carrying a
        custom CA, PINNED apps fail closed while unpinned apps keep working.
        This check only reports what the tooling observes; it never infers
        pinning from static metadata.
        """
        installed = self.check_app_installed(package)
        if installed.status != "PASS":
            return DeviceVerdict(
                status=installed.status,
                tool=installed.tool,
                detail=f"pinning check needs the app installed ({installed.detail})",
                manual_steps=installed.manual_steps
                + [
                    "Install the target build on the test device.",
                    "Route the device through an intercepting proxy with a custom CA.",
                    "Exercise the login/token endpoint and observe: connection failure = pinning enforced.",
                ],
            )
        return DeviceVerdict(
            status="INCONCLUSIVE",
            tool="manual",
            detail=f"app present; pinning for {host} requires a live proxy observation",
            evidence={"package": package, "host": host},
            manual_steps=[
                "Route the test device through an intercepting proxy with a custom CA.",
                f"Trigger traffic to {host} from {package}.",
                "Connection failure = pinning enforced (PASS); traffic flows = absent/bypassable (FAIL).",
                "Record the verdict with timestamps and proxy logs as evidence.",
            ],
        )


def get_mobile_validator(timeout_s: int = DEFAULT_TIMEOUT_S) -> MobileDeviceValidator:
    """Factory for the on-device validator."""
    return MobileDeviceValidator(timeout_s=timeout_s)
