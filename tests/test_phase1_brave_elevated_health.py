"""Phase 1: Brave detection/context/state + elevated mode + PC health.

No browser launch, no network, no real elevation: detection is monkeypatched,
open_in_brave's webbrowser calls are faked, health never raises by contract.
"""

from __future__ import annotations


class TestDetectBrave:
    def test_not_detected_when_absent(self, monkeypatch):
        import cores.browsing.brave as brave

        monkeypatch.setattr(brave.Path, "exists", lambda self: False)
        monkeypatch.setattr(brave.shutil, "which", lambda name: None)
        out = brave.detect_brave()
        assert out["installed"] is False
        assert out["path"] is None

    def test_detected_via_which(self, monkeypatch):
        import cores.browsing.brave as brave

        monkeypatch.setattr(brave.Path, "exists", lambda self: False)
        monkeypatch.setattr(brave.shutil, "which", lambda name: "/usr/bin/brave" if "brave" in name else None)
        out = brave.detect_brave()
        assert out["installed"] is True
        assert out["path"] == "/usr/bin/brave"

    def test_open_uses_brave_controller_when_registered(self, monkeypatch):
        import cores.browsing.brave as brave

        monkeypatch.setattr(brave, "detect_brave", lambda: {"installed": True, "path": "/b/brave", "is_default": True})
        calls = []

        class _FakeController:
            def open(self, url, new=2, autoraise=True):
                calls.append(url)

        monkeypatch.setattr(brave.webbrowser, "get", lambda name=None: _FakeController())
        out = brave.open_in_brave("https://example.com/work")
        assert out["opened"] is True
        assert out["browser"] == "brave"
        assert calls == ["https://example.com/work"]

    def test_open_falls_back_without_brave(self, monkeypatch):
        import cores.browsing.brave as brave

        monkeypatch.setattr(brave, "detect_brave", lambda: {"installed": False, "path": None, "is_default": False})
        monkeypatch.setattr(brave.webbrowser, "open", lambda url, new=2, autoraise=True: True)
        out = brave.open_in_brave("https://example.com")
        assert out["opened"] is True
        assert out["browser"] == "default"

    def test_context_never_contains_secrets(self, monkeypatch):
        import cores.browsing.brave as brave

        monkeypatch.setattr(brave, "detect_brave", lambda: {"installed": True, "path": "/b", "is_default": False})
        ctx = brave.browser_context()
        blob = repr(ctx).lower()
        for needle in ("password", "cookie", "token", "secret", "seed phrase"):
            assert needle not in blob or "never extracts" in blob


class TestBrowserState:
    def test_not_detected_state(self, monkeypatch):
        import cores.browsing.brave as brave

        monkeypatch.setattr(brave, "detect_brave", lambda: {"installed": False, "path": None, "is_default": False})
        st = brave.browser_state()
        assert st["state"] == "NOT_DETECTED"
        assert "Brave" in st["cause"]
        assert st["next_action"]

    def test_detected_without_session(self, monkeypatch):
        import cores.browsing.brave as brave

        monkeypatch.setattr(brave, "detect_brave", lambda: {"installed": True, "path": "/b", "is_default": False})
        st = brave.browser_state()
        assert st["state"] == "DETECTED"

    def test_ready_requires_evidence_never_invented(self, monkeypatch):
        import cores.browsing.brave as brave

        monkeypatch.setattr(brave, "detect_brave", lambda: {"installed": True, "path": "/b", "is_default": False})
        assert brave.browser_state()["state"] != "READY"
        assert brave.browser_state({"session_ready": True})["state"] == "READY"

    def test_human_flows(self):
        import cores.browsing.brave as brave

        assert brave.browser_state({"login_required": True})["state"] == "LOGIN_REQUIRED"
        assert brave.browser_state({"verification_required": True})["state"] == "VERIFICATION_REQUIRED"
        assert brave.browser_state({"human_action_required": True})["state"] == "HUMAN_ACTION_REQUIRED"
        blocked = brave.browser_state({"blocked_reason": "CAPTCHA en login"})
        assert blocked["state"] == "BLOCKED"
        assert "CAPTCHA" in blocked["cause"]
        assert "nunca bypass" in blocked["next_action"]
        assert brave.browser_state({"error": "boom"})["state"] == "ERROR"

    def test_automating_only_with_evidence(self):
        import cores.browsing.brave as brave

        assert brave.browser_state({"automation_active": True})["state"] == "AUTOMATING"


class TestElevatedMode:
    def test_is_admin_returns_bool(self):
        from cores.platform.elevated import is_admin

        assert isinstance(is_admin(), bool)

    def test_needs_elevation_matrix(self):
        from cores.platform.elevated import needs_elevation

        for action in ("install", "update", "service", "repair", "driver", "windows_config"):
            need, why = needs_elevation(action)
            assert need is True and why
        for action in ("scan", "read", "classify", "prepare", "unknown_xyz"):
            need, _ = needs_elevation(action)
            assert need is False

    def test_request_records_audit_trail(self, monkeypatch, tmp_path):
        import json

        import cores.platform.elevated as elevated

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        out = elevated.request_elevation("instalar servicio", "ownex-agent", workspace="OWNEX")
        assert "how" in out and "reason" in out
        lines = (tmp_path / "elevation_audit.jsonl").read_text(encoding="utf-8").strip().split("\n")
        rec = json.loads(lines[-1])
        assert rec["reason"] == "instalar servicio"
        assert rec["workspace"] == "OWNEX"
        assert rec["result"] in ("requested", "already_elevated")

    def test_elevation_status_shape(self):
        from cores.platform.elevated import elevation_status

        st = elevation_status()
        assert st["mode"] in ("NORMAL USER", "ELEVATED")
        assert isinstance(st["is_admin"], bool)


class TestPcHealth:
    def test_collect_never_raises_and_has_level(self):
        from cores.health.system_health import collect_pc_health

        out = collect_pc_health()
        assert out["level"] in ("HEALTHY", "WARNING", "DEGRADED", "BLOCKED", "CRITICAL")
        assert "summary" in out and "collected_at" in out

    def test_collect_contains_no_secrets(self):
        import json
        import re

        from cores.health.system_health import collect_pc_health

        blob = json.dumps(collect_pc_health(), default=str)
        # Secret VALUES (not English words like "password" in the security note).
        for pattern in (
            r"sk-(live|test)-[A-Za-z0-9]{8,}",
            r"ghp_[A-Za-z0-9]{8,}",
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        ):
            assert not re.search(pattern, blob)
        assert "api_key=" not in blob.lower()

    def test_level_text_mapping(self):
        from cores.health.system_health import health_level_text

        assert health_level_text("HEALTHY") != "HEALTHY"
        assert health_level_text("CRITICAL") != "CRITICAL"
        assert health_level_text("NOPE") == "NOPE"


class TestSystemEndpoints:
    def test_pc_health_endpoint_never_500s(self):
        from api.routers.system import pc_health

        out = pc_health()
        assert out["level"] in ("HEALTHY", "WARNING", "DEGRADED", "BLOCKED", "CRITICAL")

    def test_brave_status_endpoint_shape(self):
        from api.routers.system import brave_status

        out = brave_status()
        assert "brave" in out and "installed" in out["brave"]

    def test_brave_open_rejects_non_http(self):
        import pytest
        from fastapi import HTTPException

        from api.routers.system import brave_open

        with pytest.raises(HTTPException):
            brave_open({"url": "file:///etc/passwd"})
        with pytest.raises(HTTPException):
            brave_open({})
