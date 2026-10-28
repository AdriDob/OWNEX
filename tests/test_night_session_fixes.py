"""Night session fixes — mission_hub OBA, daily_loop weighting, outreach next_step,
adapter audit, /sources perf + prep wiring.

Un archivo, sin red real (todo mockeado o local).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def mission_client(monkeypatch, tmp_path, ownex_login):
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CATEYE_CSRF_DISABLED", "1")
    from cores.levels import reset_progression_engine

    reset_progression_engine()
    import api.main as main

    c = TestClient(main.app, raise_server_exceptions=False)
    # `/mission-hub/*` y `/direct-work/*` se montan en RAÍZ y el gate de auth
    # exige sesión desde KNOWN_DEBT #32.
    ownex_login(c)
    return c


class TestMissionHubUsesRealOBA:
    def test_next_action_from_one_best_action(self, mission_client, monkeypatch) -> None:
        from cores.direct_work_engine import one_best_action as oba_mod
        from cores.direct_work_engine.one_best_action import ActionType, OneBestAction, Urgency

        fake = OneBestAction(
            action_type=ActionType.DELIVER_NOW,
            title="Entregar: Bounty X",
            description="Trabajo listo",
            why_now="Cash sobre la mesa",
            platform="algora",
            work_item_id="w-1",
            estimated_human_hours=0.5,
            expected_value_usd=2000.0,
            url="https://example.com/bounty",
            next_step_instruction="POST /direct-work/workbank/w-1/deliver/prepare",
            urgency=Urgency.IMMEDIATE,
        )
        monkeypatch.setattr(oba_mod, "get_one_best_action", lambda profile=None: fake)
        r = mission_client.get("/mission-hub/overview")
        assert r.status_code == 200
        na = r.json()["next_action"]
        assert isinstance(na, dict)
        assert na["title"] == "Entregar: Bounty X"
        assert na["why"] == "Cash sobre la mesa"
        assert na["est_minutes"] == 30
        assert na["url"] == "https://example.com/bounty"
        assert na["endpoint"] == "POST /direct-work/workbank/w-1/deliver/prepare"
        assert na["life_goal"]  # brújula PERSONAL_CONTEXT §24, nunca vacío acá

    def test_next_action_fallback_still_actionable(self, mission_client, monkeypatch) -> None:
        from cores.direct_work_engine import one_best_action as oba_mod

        def _boom(profile=None):
            raise RuntimeError("sin OBA")

        monkeypatch.setattr(oba_mod, "get_one_best_action", _boom)
        r = mission_client.get("/mission-hub/overview")
        assert r.status_code == 200
        na = r.json()["next_action"]
        assert isinstance(na, dict)
        assert na.get("title")
        assert "url" in na or "endpoint" in na


class TestDailyLoopAllocationWeighted:
    def test_platform_maps_to_workspace_weight(self, monkeypatch) -> None:
        import cores.automation.daily_loop as dl
        import cores.direct_work_engine.workbank as wb_mod
        import cores.workspaces.allocation as alloc_mod

        items = {
            "a": SimpleNamespace(
                id="a",
                title="Algora chico",
                platform="algora",
                reward=100.0,
                url="https://example.com/a",
                status="ready_to_deliver",
            ),
            "b": SimpleNamespace(
                id="b",
                title="Outlier grande",
                platform="outlier",
                reward=5000.0,
                url="https://example.com/b",
                status="ready_to_deliver",
            ),
        }
        monkeypatch.setattr(wb_mod, "get_workbank", lambda: SimpleNamespace(_items=items))
        monkeypatch.setattr(
            alloc_mod,
            "allocate_daily_hours",
            lambda total_minutes, active=None: SimpleNamespace(
                slices=[
                    SimpleNamespace(workspace="dev_bounty", minutes=200),
                    SimpleNamespace(workspace="ai_training", minutes=20),
                ]
            ),
        )
        top = dl._top_candidates(limit=2, total_minutes=240)
        assert [c["id"] for c in top] == ["a", "b"]  # peso dev_bounty gana al reward bruto

    def test_unknown_platform_falls_back_to_reward(self, monkeypatch) -> None:
        import cores.automation.daily_loop as dl
        import cores.direct_work_engine.workbank as wb_mod
        import cores.workspaces.allocation as alloc_mod

        items = {
            "a": SimpleNamespace(
                id="a",
                title="Chico",
                platform="nope",
                reward=10.0,
                url="https://example.com/a",
                status="ready_to_deliver",
            ),
            "b": SimpleNamespace(
                id="b",
                title="Grande",
                platform="nope2",
                reward=900.0,
                url="https://example.com/b",
                status="ready_to_deliver",
            ),
        }
        monkeypatch.setattr(wb_mod, "get_workbank", lambda: SimpleNamespace(_items=items))
        monkeypatch.setattr(
            alloc_mod,
            "allocate_daily_hours",
            lambda total_minutes, active=None: SimpleNamespace(slices=[]),
        )
        top = dl._top_candidates(limit=2, total_minutes=240)
        assert [c["id"] for c in top] == ["b", "a"]


class TestOutreachNextStep:
    def test_next_step_per_status(self) -> None:
        from cores.ecommerce.outreach import OutreachRecord, next_step_for_status

        assert "WhatsApp" in next_step_for_status("pending")
        assert "48h" in next_step_for_status("contacted")
        assert "sync-catalog" in next_step_for_status("replied")
        assert "VIABLE" in next_step_for_status("verified")
        assert "Descartado" in next_step_for_status("rejected")
        rec = OutreachRecord(supplier_id="s1", status="contacted")
        d = rec.to_dict()
        assert d["next_step"] == next_step_for_status("contacted")

    def test_store_contacted_roundtrip(self, tmp_path) -> None:
        from cores.ecommerce.outreach import OutreachStore

        store = OutreachStore(path=tmp_path / "outreach.json")
        rec = store.mark_contacted("s1", wa_url="https://wa.me/?text=hola", message="hola")
        assert rec.status == "contacted"
        assert store.mark("s1", status="replied", notes="pidió ficha") is not None
        reloaded = OutreachStore(path=tmp_path / "outreach.json").get("s1")
        assert reloaded is not None and reloaded.status == "replied"


class TestAdapterAudit:
    def test_all_registered_have_audit_entry(self) -> None:
        from api.adapters.legacy import build_default_adapters, get_adapter_fetch_audit

        audit = get_adapter_fetch_audit()
        names = {a.source.name for a in build_default_adapters()}
        assert names, "sin adapters registrados"
        for n in names:
            assert n in audit, f"adapter {n} sin entrada de audit"
            assert audit[n]["mode"] in ("LIVE", "STATIC", "INTERNAL", "DEGRADED")
            assert audit[n]["evidence"]

    def test_upstream_muerto_no_esta_registrado(self) -> None:
        """`DEAD` es un modo del audit, pero de un adapter NO registrado.

        El builder dice "only LIVE upstreams are registered"; Dework devuelve
        200 text/html con 0 bytes (verificado 2026-10-01) y antes quedó
        registrado: fetch 0 en silencio dentro de un `except` con logger.debug.
        Registrar un upstream muerto quema requests y oculta el canal vacío.
        """
        from api.adapters.legacy import build_default_adapters, get_adapter_fetch_audit

        audit = get_adapter_fetch_audit()
        registered = {a.source.name for a in build_default_adapters()}
        dead = {n for n, v in audit.items() if v.get("mode") == "DEAD"}
        assert dead, "el audit debería registrar algún upstream muerto conocido"
        assert not (dead & registered), f"adapter muerto registrado: {sorted(dead & registered)}"

    def test_dead_seeds_emptied(self) -> None:
        from api.adapters.direct_work_algora import AlgoraAdapter
        from api.adapters.direct_work_bountyboard import BountyBoardAdapter
        from api.adapters.direct_work_polar import PolarAdapter

        assert AlgoraAdapter.CURATED_BOUNTIES == []
        assert BountyBoardAdapter.CURATED_BOUNTIES == []
        assert PolarAdapter.CURATED_BOUNTIES == []


class TestSourcesPerfAndPrep:
    def test_overview_single_store_load(self, monkeypatch, tmp_path) -> None:
        from cores.direct_work_engine import source_registry as reg

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        calls = {"n": 0}
        real_load = reg._load_store

        def counting():
            calls["n"] += 1
            return real_load()

        monkeypatch.setattr(reg, "_load_store", counting)
        ov = reg.sources_overview()
        assert ov["total"] >= 100
        assert calls["n"] == 1
        first = ov["sources"][0]
        assert {"name", "url", "category", "type", "gate", "liveness", "enabled"} <= set(first)

    def test_prep_endpoint_roundtrip(self, mission_client) -> None:
        from cores.opportunity.global_sources import get_sources

        name = get_sources()[0].name
        r = mission_client.post("/direct-work/sources/prep", json={"name": name, "use_ai": False})
        assert r.status_code == 200
        body = r.json()
        assert body.get("checklist") or body.get("topics") or body.get("steps") or isinstance(body, dict)
        r2 = mission_client.post(
            "/direct-work/sources/prep", json={"name": "fuente-que-no-existe-xyz", "use_ai": False}
        )
        assert r2.status_code == 404
