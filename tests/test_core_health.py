"""Tests for core/health/ — Health Center."""

from __future__ import annotations

from core.health.engine import HealthCenter, HealthCheck, HealthSnapshot


class TestHealthCenter:
    def test_register_and_run(self):
        center = HealthCenter()
        center.register("always_ok", lambda: True, "system")
        center.register("always_fail", lambda: False, "system")
        snapshot = center.run_all()
        assert snapshot.checks["always_ok"] is True
        assert snapshot.checks["always_fail"] is False

    def test_green_status(self):
        center = HealthCenter()
        center.register("ok1", lambda: True, "system")
        center.register("ok2", lambda: True, "background")
        snapshot = center.run_all()
        assert snapshot.status == "green"

    def test_yellow_status(self):
        center = HealthCenter()
        center.register("ok", lambda: True, "system")
        center.register("fail", lambda: False, "background")
        snapshot = center.run_all()
        assert snapshot.status == "yellow"

    def test_red_status(self):
        center = HealthCenter()
        center.register("fail_critical", lambda: False, "system")
        snapshot = center.run_all()
        assert snapshot.status == "red"

    def test_run_category(self):
        center = HealthCenter()
        center.register("sys1", lambda: True, "system")
        center.register("bg1", lambda: True, "background")
        center.register("bg2", lambda: False, "background")
        snapshot = center.run_category("background")
        assert "bg1" in snapshot.checks
        assert "bg2" in snapshot.checks
        assert "sys1" not in snapshot.checks
        assert snapshot.details.get("category") == "background"

    def test_latest(self):
        center = HealthCenter()
        assert center.latest() is None
        center.register("ok", lambda: True, "system")
        center.run_all()
        assert center.latest() is not None
        assert isinstance(center.latest(), HealthSnapshot)

    def test_status_before_run(self):
        center = HealthCenter()
        assert center.status() == "unknown"

    def test_summary(self):
        center = HealthCenter()
        center.register("ok", lambda: True, "system")
        s = center.summary()
        assert s["status"] == "unknown"  # before any run
        center.run_all()
        s = center.summary()
        assert s["status"] == "green"
        assert s["checks_total"] == 1
        assert s["checks_passed"] == 1

    def test_list_checks(self):
        center = HealthCenter()
        center.register("ok", lambda: True, "system")
        checks = center.list_checks()
        assert len(checks) == 1
        assert checks[0]["name"] == "ok"

    def test_unregister(self):
        center = HealthCenter()
        center.register("temp", lambda: True, "system")
        center.unregister("temp")
        assert len(center.list_checks()) == 0

    def test_check_exception(self):
        center = HealthCenter()

        def failing():
            raise RuntimeError("boom")

        center.register("explode", failing, "background")
        snapshot = center.run_all()
        assert snapshot.checks["explode"] is False
        # should be yellow (non-critical failure)
        assert snapshot.status == "yellow"

    def test_snapshot_limit(self):
        center = HealthCenter()
        center.register("ok", lambda: True, "system")
        for _ in range(200):
            center.run_all()
        assert len(center._snapshots) <= 100

    def test_check_timeout_set(self):
        center = HealthCenter()
        center.register("slow", lambda: True, "system")
        check = center._checks["slow"]
        assert check.timeout == 10

    def test_all_statuses(self):
        center = HealthCenter()
        # unknown
        assert center.status() == "unknown"
        # green
        center.register("ok", lambda: True, "system")
        center.run_all()
        assert center.status() == "green"
        # yellow
        center.register("bg_fail", lambda: False, "background")
        center.run_all()
        assert center.status() == "yellow"
        # red
        center.register("sys_fail", lambda: False, "system")
        center.run_all()
        assert center.status() == "red"


class TestHealthCheck:
    def test_defaults(self):
        hc = HealthCheck(name="test", check_fn=lambda: True)
        assert hc.name == "test"
        assert hc.last_ok is True
        assert hc.last_error == ""
        assert hc.category == "system"

    def test_custom_category(self):
        hc = HealthCheck(name="test", check_fn=lambda: True, category="custom")
        assert hc.category == "custom"


class TestHealthSnapshot:
    def test_snapshot_creation(self):
        snap = HealthSnapshot(
            status="green",
            checks={"ok": True},
        )
        assert snap.status == "green"
        assert snap.checks == {"ok": True}
        assert snap.extensions_loaded == 0
        assert snap.extensions_failed == 0

    def test_full_snapshot(self):
        snap = HealthSnapshot(
            status="yellow",
            checks={"a": True, "b": False},
            extensions_loaded=3,
            extensions_failed=1,
            secrets_available=True,
            details={"note": "testing"},
        )
        assert snap.extensions_loaded == 3
        assert snap.extensions_failed == 1
        assert snap.secrets_available is True
