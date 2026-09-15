"""Economic Operating System — ladder + workspaces + loops (no network, DB-isolated)."""

from __future__ import annotations

from cores.automation.ladder import (
    AutomationRung,
    LadderTask,
    advance,
    automation_ratio,
    fail,
    label_es,
    mark_unsupported,
    next_rung,
)
from cores.workspaces.allocation import allocate_daily_hours
from cores.workspaces.economics import economics_for, rank_workspaces


class TestLadder:
    def test_happy_path_order(self) -> None:
        assert next_rung(AutomationRung.A0_INFORMATION) == AutomationRung.A1_PREPARE
        assert next_rung(AutomationRung.A2_AUTO_RUN) == AutomationRung.A3_HUMAN_APPROVAL
        assert next_rung(AutomationRung.A11_OPTIMIZE) == AutomationRung.A11_OPTIMIZE

    def test_advance_records_evidence(self) -> None:
        t = LadderTask(id="t1", title="x")
        advance(t, evidence="e1")
        assert t.rung == AutomationRung.A1_PREPARE
        assert t.evidence == ["e1"]

    def test_gated_rungs_need_human(self) -> None:
        assert LadderTask(id="a", title="a", rung=AutomationRung.A3_HUMAN_APPROVAL).needs_human is True
        assert LadderTask(id="b", title="b", rung=AutomationRung.A2_AUTO_RUN).needs_human is False

    def test_fail_parks_honestly(self) -> None:
        t = LadderTask(id="f", title="f")
        fail(t, stage="deliver", cause="no token")
        assert t.rung == AutomationRung.A5_EXTERNAL_BLOCK
        assert t.failure and t.failure["cause"] == "no token"

    def test_unsupported_is_explicit(self) -> None:
        t = LadderTask(id="u", title="u")
        mark_unsupported(t, reason="captcha")
        assert t.rung == AutomationRung.A6_UNSUPPORTED
        assert t.is_terminal is True

    def test_labels_cover_all(self) -> None:
        assert label_es(AutomationRung.A0_INFORMATION).startswith("A0")
        assert label_es("A11_optimize").startswith("A11")

    def test_ratio(self) -> None:
        ts = [LadderTask(id="1", title="a", automated_minutes=90, human_minutes=30)]
        r = automation_ratio(ts)
        assert r["automation_ratio"] == 0.75
        assert automation_ratio([])["automation_ratio"] == 0.0


class TestWorkspaceEconomics:
    def test_rank_returns_eligible_first(self) -> None:
        ranked = rank_workspaces()
        assert ranked
        assert all(e.eligible for e in ranked)

    def test_cold_start_unknown(self) -> None:
        e = economics_for("bug_bounty")
        assert e.eligible is True
        # Honest either way: outcomes>0 measured, else UNKNOWN fields
        assert (e.outcomes == 0 and e.ev_per_hour is None) or e.outcomes > 0

    def test_trading_never_base(self) -> None:
        e = economics_for("trading")
        assert e.eligible is False

    def test_to_dict_shape(self) -> None:
        e = economics_for("dev_bounty")
        d = e.to_dict()
        assert {"workspace", "role", "eligible", "ev_per_hour", "outcomes"} <= set(d)


class TestAllocation:
    def test_cold_start_splits_primary(self) -> None:
        alloc = allocate_daily_hours(240)
        assert alloc.total_minutes == 240
        assert sum(s.minutes for s in alloc.slices) == 240
        assert alloc.mode in ("cold_start", "measured")

    def test_admin_reserve(self) -> None:
        alloc = allocate_daily_hours(200)
        admin = [s for s in alloc.slices if s.workspace == "admin"]
        assert admin and admin[0].minutes == 10

    def test_to_dict(self) -> None:
        assert "slices" in allocate_daily_hours(120).to_dict()


class TestLoops:
    def test_daily_loop_never_raises(self) -> None:
        from cores.automation.daily_loop import run_daily_loop

        res = run_daily_loop(60)
        d = res.to_dict()
        assert {"selected", "parked_gated", "payment_check", "learning"} <= set(d)

    def test_economic_loop_phase(self) -> None:
        from cores.automation.economic_loop import PHASES, current_phase

        st = current_phase()
        assert st.phase in PHASES
        assert st.next_transition
        assert "escalable" in st.scale_question

    def test_mission_endpoints(self) -> None:
        from fastapi.testclient import TestClient

        from api.main import app

        c = TestClient(app)
        r = c.post("/api/auth/login", json={"device_id": "econ-test"})
        tok = r.json()["data"]["token"]
        c.headers.update({"Authorization": f"Bearer {tok}"})
        g = c.get("/api/system/pc-health")
        csrf = g.cookies.get("csrf-token")
        if csrf:
            c.headers.update({"X-CSRF-Token": csrf})
        assert c.get("/mission-hub/economics").status_code == 200
        assert c.get("/mission-hub/allocation/daily?total_minutes=120").status_code == 200
        assert c.get("/mission-hub/economic-loop").status_code == 200
        assert c.post("/mission-hub/daily-loop/run?total_minutes=60").status_code == 200
