"""Tests for the mobile on-device validator.

All execution paths are faked (monkeypatched shutil.which / subprocess):
no device, no tools, no side effects. Pins honest degradation:
UNAVAILABLE (tool missing) is never FAIL, nothing passes without running.
"""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from cores.offensive.mobile_validator import (
    DEFAULT_TIMEOUT_S,
    DeviceVerdict,
    MobileDeviceValidator,
    get_mobile_validator,
)


def _validator(present: set[str]) -> MobileDeviceValidator:
    v = MobileDeviceValidator()
    v._tool_cache = {t: (t in present) for t in ("adb", "frida", "frida-ps", "objection")}
    return v


class TestAvailabilityMatrix:
    def test_tools_status_shape(self):
        v = _validator({"adb"})
        status = v.tools_status()
        assert set(status) == {"adb", "frida", "frida-ps", "objection"}
        assert status["adb"] is True
        assert status["frida"] is False

    def test_caches_lookups(self):
        v = MobileDeviceValidator()
        with patch("cores.offensive.mobile_validator.shutil.which", return_value=None) as which:
            assert v.is_tool_available("adb") is False
            assert v.is_tool_available("adb") is False
            which.assert_called_once_with("adb")

    def test_default_timeout(self):
        assert MobileDeviceValidator().timeout_s == DEFAULT_TIMEOUT_S
        assert get_mobile_validator(timeout_s=5).timeout_s == 5


class TestAdbDevices:
    def test_no_adb_is_unavailable_not_fail(self):
        v = _validator(set())
        verdict = v.check_adb_devices()
        assert verdict.status == "UNAVAILABLE"
        assert verdict.tool == "adb"
        assert len(verdict.manual_steps) >= 2

    def test_no_device_is_inconclusive(self):
        v = _validator({"adb"})

        class Done:
            returncode = 0
            stdout = "List of devices attached\n\n"
            stderr = ""

        with patch("cores.offensive.mobile_validator.subprocess.run", return_value=Done()):
            verdict = v.check_adb_devices()
        assert verdict.status == "INCONCLUSIVE"

    def test_device_present_passes(self):
        v = _validator({"adb"})

        class Done:
            returncode = 0
            stdout = "List of devices attached\nemulator-5554\tdevice product:sdk\n"
            stderr = ""

        with patch("cores.offensive.mobile_validator.subprocess.run", return_value=Done()):
            verdict = v.check_adb_devices()
        assert verdict.status == "PASS"
        assert verdict.evidence["devices"] == ["emulator-5554"]

    def test_offline_device_ignored(self):
        v = _validator({"adb"})

        class Done:
            returncode = 0
            stdout = "List of devices attached\nemulator-5554\toffline\n"
            stderr = ""

        with patch("cores.offensive.mobile_validator.subprocess.run", return_value=Done()):
            verdict = v.check_adb_devices()
        assert verdict.status == "INCONCLUSIVE"


class TestRunHelper:
    def test_missing_tool_never_raises(self):
        v = _validator(set())
        ok, out = v._run("adb", ["devices"])
        assert ok is False
        assert "not installed" in out

    def test_timeout_never_raises(self):
        v = _validator({"adb"})
        with patch(
            "cores.offensive.mobile_validator.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="adb", timeout=1),
        ):
            ok, out = v._run("adb", ["devices"], timeout_s=1)
        assert ok is False
        assert "timed out" in out

    def test_nonzero_exit_is_not_pass(self):
        v = _validator({"adb"})

        class Done:
            returncode = 1
            stdout = ""
            stderr = "error: no devices"

        with patch("cores.offensive.mobile_validator.subprocess.run", return_value=Done()):
            ok, out = v._run("adb", ["devices"])
        assert ok is False
        assert "exit 1" in out

    def test_no_shell_used(self):
        v = _validator({"adb"})
        with patch("cores.offensive.mobile_validator.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "List of devices attached\n"
            run.return_value.stderr = ""
            v.check_adb_devices()
        _, kwargs = run.call_args
        assert kwargs.get("shell", False) is False


class TestAppAndFrida:
    def test_app_check_needs_device_first(self):
        v = _validator({"adb"})

        class Done:
            returncode = 0
            stdout = "List of devices attached\n\n"
            stderr = ""

        with patch("cores.offensive.mobile_validator.subprocess.run", return_value=Done()):
            verdict = v.check_app_installed("com.example.app")
        assert verdict.status == "INCONCLUSIVE"

    def test_app_installed_pass_fail(self):
        v = _validator({"adb"})
        calls = {"n": 0}

        class Done:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_run(*args, **kwargs):
            calls["n"] += 1
            d = Done()
            if calls["n"] == 1:
                d.stdout = "List of devices attached\nemulator-5554\tdevice\n"
            else:
                d.stdout = "package:com.example.app\n"
            return d

        with patch("cores.offensive.mobile_validator.subprocess.run", side_effect=fake_run):
            verdict = v.check_app_installed("com.example.app")
        assert verdict.status == "PASS"

    def test_frida_without_tools_is_unavailable(self):
        v = _validator({"adb"})

        class Done:
            returncode = 0
            stdout = "List of devices attached\nemulator-5554\tdevice\n"
            stderr = ""

        with patch("cores.offensive.mobile_validator.subprocess.run", return_value=Done()):
            verdict = v.check_frida_server()
        assert verdict.status == "UNAVAILABLE"
        assert verdict.tool == "frida-ps"


class TestPinningCheck:
    def test_pinning_without_app_is_not_pass(self):
        v = _validator({"adb"})

        class Done:
            returncode = 0
            stdout = "List of devices attached\n\n"
            stderr = ""

        with patch("cores.offensive.mobile_validator.subprocess.run", return_value=Done()):
            verdict = v.check_pinning_enforced("com.example.app", "https://api.example.com")
        assert verdict.status in ("INCONCLUSIVE", "UNAVAILABLE")
        assert verdict.status != "PASS"

    def test_pinning_with_app_is_inconclusive_with_steps(self):
        v = _validator({"adb"})
        calls = {"n": 0}

        class Done:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_run(*args, **kwargs):
            calls["n"] += 1
            d = Done()
            if calls["n"] == 1:
                d.stdout = "List of devices attached\nemulator-5554\tdevice\n"
            else:
                d.stdout = "package:com.example.app\n"
            return d

        with patch("cores.offensive.mobile_validator.subprocess.run", side_effect=fake_run):
            verdict = v.check_pinning_enforced("com.example.app", "https://api.example.com")
        # Static tooling cannot observe the handshake: honest INCONCLUSIVE.
        assert verdict.status == "INCONCLUSIVE"
        assert len(verdict.manual_steps) >= 3

    def test_verdict_serializes(self):
        v = DeviceVerdict(status="PASS", tool="adb", detail="ok")
        d = v.to_dict()
        assert d == {"status": "PASS", "tool": "adb", "detail": "ok", "evidence": {}, "manual_steps": []}
