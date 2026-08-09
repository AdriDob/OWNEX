"""Tests for Command System — registry, dispatcher, API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.commands import (
    CommandDefinition,
    PermissionLevel,
    get_command_dispatcher,
    get_command_registry,
)
from core.commands.dispatcher import reset_command_dispatcher
from core.commands.registry import reset_command_registry

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset():
    reset_command_registry()
    reset_command_dispatcher()
    yield


# ── Tests: CommandRegistry ───────────────────────────────────────


class TestCommandRegistry:
    def test_register_and_get(self):
        reg = get_command_registry()
        cmd = reg.get("status")
        assert cmd is not None
        assert cmd.name == "status"
        assert cmd.permission == PermissionLevel.PUBLIC

    def test_get_by_alias(self):
        reg = get_command_registry()
        cmd = reg.get("/st")
        assert cmd is not None
        assert cmd.name == "status"

    def test_get_with_leading_slash(self):
        reg = get_command_registry()
        cmd = reg.get("/health")
        assert cmd is not None
        assert cmd.name == "health"

    def test_get_unknown(self):
        reg = get_command_registry()
        assert reg.get("nonexistent_command_xyz") is None

    def test_list_all(self):
        reg = get_command_registry()
        cmds = reg.list()
        assert len(cmds) == 107

    def test_list_by_category(self):
        reg = get_command_registry()
        cmds = reg.list(category="bugbounty")
        assert len(cmds) == 12
        for c in cmds:
            assert c.category == "bugbounty"

    def test_list_by_permission(self):
        reg = get_command_registry()
        cmds = reg.list(permission="PUBLIC")
        for c in cmds:
            assert c.permission == PermissionLevel.PUBLIC

    def test_categories(self):
        reg = get_command_registry()
        cats = reg.categories()
        assert "bugbounty" in cats
        assert "architecture" in cats
        assert "copilot" in cats
        assert "smart" in cats

    def test_count(self):
        reg = get_command_registry()
        assert reg.count() == 107

    def test_to_capability_registry(self):
        reg = get_command_registry()
        entries = reg.to_capability_registry()
        assert len(entries) == 107
        names = [e[0] for e in entries]
        assert "command:status" in names
        assert "command:health" in names
        assert "command:rollback" in names

    def test_smart_commands_have_correct_permissions(self):
        reg = get_command_registry()
        assert reg.get("ship").permission == PermissionLevel.ADMIN
        assert reg.get("money").permission == PermissionLevel.OPERATOR
        assert reg.get("morning").permission == PermissionLevel.PUBLIC
        assert reg.get("rollback").permission == PermissionLevel.DANGEROUS

    def test_all_commands_have_names(self):
        reg = get_command_registry()
        for cmd in reg.list():
            assert cmd.name, "Command with empty name found"
            assert cmd.category, f"Command '{cmd.name}' has no category"

    def test_aliases_are_indexed(self):
        reg = get_command_registry()
        cmds = reg.list()
        for cmd in cmds:
            for alias in cmd.aliases:
                resolved = reg.get(alias)
                assert resolved is not None, f"Alias '{alias}' for '{cmd.name}' not found"
                assert resolved.name == cmd.name


# ── Tests: CommandDispatcher ─────────────────────────────────────


class TestCommandDispatcher:
    def test_dispatch_public_command(self):
        disp = get_command_dispatcher()
        result = disp.dispatch("status", authority="observer")
        assert result.status == "executed"
        assert result.permission == "PUBLIC"

    def test_dispatch_operator_command_as_admin(self):
        disp = get_command_dispatcher()
        result = disp.dispatch("recon", authority="administrator")
        assert result.status == "executed"
        assert result.permission == "OPERATOR"

    def test_dispatch_operator_command_as_observer(self):
        disp = get_command_dispatcher()
        result = disp.dispatch("recon", authority="observer")
        assert result.status == "rejected"
        assert "Insufficient permission" in (result.error or "")

    def test_dispatch_admin_command_as_operator(self):
        disp = get_command_dispatcher()
        result = disp.dispatch("audit", authority="operator")
        assert result.status == "rejected"

    def test_dispatch_dangerous_requires_admin(self):
        disp = get_command_dispatcher()
        result = disp.dispatch("rollback", authority="operator")
        assert result.status == "rejected"

    def test_dispatch_dangerous_as_admin(self):
        disp = get_command_dispatcher()
        result = disp.dispatch("rollback", authority="administrator")
        assert result.status == "executed"

    def test_dispatch_unknown_command(self):
        disp = get_command_dispatcher()
        result = disp.dispatch("does_not_exist", authority="observer")
        assert result.status == "failed"
        assert result.error is not None

    def test_dispatch_dry_run(self):
        disp = get_command_dispatcher()
        result = disp.dispatch("health", authority="observer", dry_run=True)
        assert result.status == "simulated"
        assert "output" in result.__dict__

    def test_dispatch_without_authority_only_public(self):
        disp = get_command_dispatcher()
        result = disp.dispatch("status")
        assert result.status == "executed"

        result2 = disp.dispatch("recon")
        assert result2.status == "rejected"

    def test_history_records_executions(self):
        disp = get_command_dispatcher()
        disp.dispatch("status", authority="observer")
        disp.dispatch("health", authority="observer")
        h = disp.history()
        assert len(h) == 2

    def test_history_filter_by_status(self):
        disp = get_command_dispatcher()
        disp.dispatch("status", authority="observer")
        disp.dispatch("recon", authority="observer")
        rejected = disp.history(status="rejected")
        assert len(rejected) == 1
        executed = disp.history(status="executed")
        assert len(executed) == 1

    def test_history_by_command(self):
        disp = get_command_dispatcher()
        disp.dispatch("status", authority="observer")
        disp.dispatch("status", authority="observer")
        disp.dispatch("health", authority="observer")
        h = disp.history_by_command("status")
        assert len(h) == 2

    def test_event_bus_integration(self):
        events = []

        class FakeBus:
            def publish(self, event_type, **kwargs):
                events.append((event_type, kwargs))

        disp = get_command_dispatcher()
        disp.bind_event_bus(FakeBus())
        disp.dispatch("status", authority="observer")
        assert len(events) == 1
        assert events[0][0] == "command:executed"

        disp.dispatch("recon", authority="observer")
        assert len(events) == 2
        assert events[1][0] == "command:rejected"

    def test_capability_registry_integration(self):
        caps = []

        class FakeCapReg:
            def register(self, cap, module, meta):
                caps.append((cap, module, meta))

        disp = get_command_dispatcher()
        disp.bind_capability_registry(FakeCapReg())
        assert len(caps) == 107
        assert ("command:audit", "command_system") == (caps[0][0], caps[0][1])

    def test_dispatch_result_has_timestamp(self):
        disp = get_command_dispatcher()
        result = disp.dispatch("status", authority="observer")
        assert result.timestamp is not None
        assert result.duration_ms >= 0


# ── Tests: CommandDefinition model ───────────────────────────────


class TestCommandDefinition:
    def test_dict_output(self):
        cmd = CommandDefinition(
            name="test_cmd",
            aliases=["/tc"],
            category="testing",
            description="A test command",
            permission=PermissionLevel.OPERATOR,
        )
        d = cmd.dict()
        assert d["name"] == "test_cmd"
        assert d["permission"] == "OPERATOR"
        assert d["category"] == "testing"
        assert d["aliases"] == ["/tc"]

    def test_default_permission_is_public(self):
        cmd = CommandDefinition(name="test")
        assert cmd.permission == PermissionLevel.PUBLIC

    def test_cost_defaults(self):
        cmd = CommandDefinition(name="test")
        assert cmd.cost.time == ""
        assert cmd.cost.tokens == 0


# ── Tests: API endpoints ─────────────────────────────────────────


@pytest.fixture
def client():
    reset_command_registry()
    reset_command_dispatcher()
    import uuid

    from api.main import app
    from cores.license.validator import generate_license

    c = TestClient(app)
    lic = generate_license(expiry_days=365)
    c.post("/api/license/activate", json={"key": lic})
    resp = c.post(
        "/api/auth/login",
        json={"device_id": f"pytest-device-{uuid.uuid4().hex[:12]}"},
    )
    assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text[:300]}"
    token = resp.json()["data"]["token"]
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


class TestCommandAPI:
    def test_list_commands(self, client):
        r = client.get("/api/commands")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 107
        assert "categories" in data

    def test_list_by_category(self, client):
        r = client.get("/api/commands?category=bugbounty")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 12

    def test_list_categories(self, client):
        r = client.get("/api/commands/categories")
        assert r.status_code == 200
        data = r.json()
        assert "bugbounty" in data["categories"]

    def test_get_command(self, client):
        r = client.get("/api/commands/status")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "status"
        assert data["permission"] == "PUBLIC"

    def test_get_command_not_found(self, client):
        r = client.get("/api/commands/nonexistent")
        assert r.status_code == 404

    def test_execute_command(self, client):
        r = client.post("/api/commands/health/execute", json={"authority": "observer"})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "executed"

    def test_execute_command_not_found(self, client):
        r = client.post("/api/commands/nonexistent/execute", json={"authority": "observer"})
        assert r.status_code == 404

    def test_execute_permission_denied(self, client):
        r = client.post("/api/commands/audit/execute", json={"authority": "observer"})
        assert r.status_code == 403

    def test_execute_dry_run(self, client):
        r = client.post("/api/commands/status/execute?dry_run=true", json={"authority": "observer"})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "simulated"

    def test_history(self, client):
        client.post("/api/commands/status/execute", json={"authority": "observer"})
        client.post("/api/commands/health/execute", json={"authority": "observer"})
        r = client.get("/api/commands/history/all")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 2

    def test_history_with_status_filter(self, client):
        client.post("/api/commands/recon/execute", json={"authority": "observer"})
        client.post("/api/commands/status/execute", json={"authority": "observer"})
        r = client.get("/api/commands/history/all?status=rejected")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        for rec in data["records"]:
            assert rec["status"] == "rejected"


# ── Tests: Permission mapping ────────────────────────────────────


class TestPermissionMapping:
    def test_observer_can_only_do_public(self):
        reg = get_command_registry()
        for cmd in reg.list():
            if cmd.permission == PermissionLevel.PUBLIC:
                dispatcher = get_command_dispatcher()
                result = dispatcher.dispatch(cmd.name, authority="observer")
                assert result.status == "executed", f"Observer should be able to run '/{cmd.name}'"

    def test_operator_can_do_public_and_operator(self):
        reg = get_command_registry()
        for cmd in reg.list():
            if cmd.permission in (PermissionLevel.PUBLIC, PermissionLevel.OPERATOR):
                dispatcher = get_command_dispatcher()
                result = dispatcher.dispatch(cmd.name, authority="operator")
                assert result.status == "executed", f"Operator should be able to run '/{cmd.name}', got {result.status}"
            else:
                dispatcher = get_command_dispatcher()
                result = dispatcher.dispatch(cmd.name, authority="operator")
                assert result.status == "rejected", f"Operator should NOT be able to run '/{cmd.name}'"

    def test_senior_hunter_can_do_up_to_admin(self):
        """senior_hunter maps to ADMIN, so they can do PUBLIC + OPERATOR + ADMIN but not SYSTEM or DANGEROUS."""
        disp = get_command_dispatcher()
        # Can do ADMIN commands
        assert disp.dispatch("audit", authority="senior_hunter").status == "executed"
        # Cannot do SYSTEM commands
        assert disp.dispatch("copilot learn", authority="senior_hunter").status == "rejected"
        # Cannot do DANGEROUS commands
        assert disp.dispatch("rollback", authority="senior_hunter").status == "rejected"
