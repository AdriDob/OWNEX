"""Tests for Whop Content Rewards clipping (Fase A+B).

Evaluator: pure brief math (VIABLE/SKIP + UNKNOWN-honest net hint).
ClipPackStore: guarded human pipeline, tmp_path isolated.
Source + checklist + API: wiring without inventing data.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.content_factory import router
from cores.content_factory.whop import (
    ClipPackStore,
    auto_build_packs,
    evaluate_campaign,
)

app = FastAPI()
app.include_router(router)


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
    return ClipPackStore()


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
    return TestClient(app)


class TestEvaluateCampaign:
    def test_viable_full_brief(self) -> None:
        out = evaluate_campaign(2.0, 250.0, minimum_usd=5.0, budget_remaining_usd=5000.0)
        assert out["verdict"] == "VIABLE"
        assert out["reasons"] == []
        assert out["net_hint_usd"] is None  # sin expected_views no se inventa

    def test_net_hint_math_with_fee_and_cap(self) -> None:
        out = evaluate_campaign(2.0, 100.0, expected_views=100_000)
        assert out["verdict"] == "VIABLE"
        assert out["net_hint_usd"] == 90.0  # min(200, cap 100) * 0.9

    def test_boundary_rate_and_cap_pass(self) -> None:
        assert evaluate_campaign(1.0, 100.0)["verdict"] == "VIABLE"

    def test_low_rate_skip(self) -> None:
        out = evaluate_campaign(0.5, 500.0)
        assert out["verdict"] == "SKIP"
        assert any("rate" in r for r in out["reasons"])

    def test_low_cap_skip(self) -> None:
        out = evaluate_campaign(3.0, 25.0)
        assert out["verdict"] == "SKIP"
        assert any("cap" in r for r in out["reasons"])

    def test_entry_fee_skip(self) -> None:
        out = evaluate_campaign(5.0, 500.0, entry_fee_usd=20.0)
        assert out["verdict"] == "SKIP"
        assert any("entry fee" in r for r in out["reasons"])

    def test_dead_budget_skip(self) -> None:
        assert evaluate_campaign(3.0, 300.0, budget_remaining_usd=0.0)["verdict"] == "SKIP"

    def test_minimum_above_cap_incoherent(self) -> None:
        out = evaluate_campaign(2.0, 50.0, minimum_usd=60.0)
        assert out["verdict"] == "SKIP"
        assert any("incoherente" in r for r in out["reasons"])

    def test_unknown_rate_skip(self) -> None:
        assert evaluate_campaign(None, 200.0)["verdict"] == "SKIP"


class TestClipPackStore:
    def test_create_and_get_roundtrip(self, store: ClipPackStore) -> None:
        pack = store.create("Roobet Clips", "clipping", 1.0, 250.0, "https://whop.com/")
        assert pack.status == "building"
        fetched = store.get(pack.id)
        assert fetched is not None and fetched.campaign_name == "Roobet Clips"

    def test_create_rejects_bad_type(self, store: ClipPackStore) -> None:
        with pytest.raises(ValueError):
            store.create("X", "viral")

    def test_guards_block_skips(self, store: ClipPackStore) -> None:
        pack = store.create("Y", "ugc", 1.5, 150.0)
        assert store.mark_posted(pack.id, "https://tiktok.com/@x/1") == (False, "requiere video listo (status ready)")
        assert store.mark_submitted(pack.id)[0] is False
        assert store.record_paid(pack.id, 10.0)[0] is True  # paid directo admitido con monto
        assert store.attach_video(pack.id, "/tmp/a.mp4") == (False, "pack terminal (paid)")

    def test_full_lifecycle(self, store: ClipPackStore) -> None:
        pack = store.create("Z", "ugc", 2.0, 200.0)
        assert store.attach_video(pack.id, "/tmp/z.mp4") == (True, "ok")
        assert store.mark_posted(pack.id, "https://youtu.be/z")[0] is True
        assert store.mark_submitted(pack.id)[0] is True
        assert store.record_paid(pack.id, 0.0) == (False, "PAID exige monto acreditado > 0")
        assert store.record_paid(pack.id, 45.5) == (True, "ok")
        fetched = store.get(pack.id)
        assert fetched is not None and fetched.status == "paid"

    def test_reject_needs_reason_and_is_terminal(self, store: ClipPackStore) -> None:
        pack = store.create("W", "ugc", 2.0, 200.0)
        assert store.mark_rejected(pack.id, "")[0] is False
        assert store.mark_rejected(pack.id, "faltó tag del brief")[0] is True
        assert store.record_paid(pack.id, 5.0) == (False, "pack rechazado (terminal)")

    def test_summary_counts_only_accredited_paid(self, store: ClipPackStore) -> None:
        a = store.create("A", "ugc", 1.0, 100.0)
        b = store.create("B", "ugc", 1.0, 100.0)
        store.attach_video(a.id, "/tmp/a.mp4")
        store.mark_posted(a.id, "https://tiktok.com/@a/1")
        store.mark_submitted(a.id)
        store.record_paid(a.id, 12.0)
        store.mark_rejected(b.id, "duplicado")
        summary = store.summary()
        assert summary["total"] == 2
        assert summary["paid_usd"] == 12.0
        assert summary["by_status"]["paid"] == 1

    def test_reload_survives_restart(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        first = ClipPackStore()
        pack = first.create("R", "ugc", 1.0, 100.0)
        second = ClipPackStore()
        fetched = second.get(pack.id)
        assert fetched is not None and fetched.campaign_name == "R"


class TestWiring:
    def test_whop_source_registered_and_gated(self) -> None:
        from cores.direct_work_engine.source_registry import source_gate
        from cores.opportunity.global_sources import OpportunityCategory, get_sources

        srcs = get_sources(OpportunityCategory.open_call)
        assert any(s.name == "Whop Content Rewards" for s in srcs)
        whop = next(s for s in srcs if s.name == "Whop Content Rewards")
        assert source_gate(whop)[0] is True
        assert whop.requires_interview is False
        assert whop.typical_hourly_rate_usd is None  # UNKNOWN honesto, no inventado

    def test_checklist_whop_item_manual(self) -> None:
        import cores.setup.checklist as cl

        item = next(i for i in cl._catalog() if i["id"] == "whop_account")
        assert item["auto"] is False
        assert item["phase"] == cl.PHASE_PLATFORMS
        assert item["priority"] == 14


class TestWhopApi:
    def test_full_flow(self, api_client: TestClient) -> None:
        created = api_client.post(
            "/api/content-factory/whop/packs",
            json={"campaign_name": "COD Clips", "campaign_type": "clipping", "rate_per_1k_usd": 1.5, "cap_usd": 120.0},
        )
        assert created.status_code == 201
        pid = created.json()["id"]
        assert (
            api_client.post(
                f"/api/content-factory/whop/packs/{pid}/video", json={"video_path": "/tmp/c.mp4"}
            ).status_code
            == 200
        )
        assert (
            api_client.post(
                f"/api/content-factory/whop/packs/{pid}/posted", json={"post_url": "https://tiktok.com/@c/1"}
            ).status_code
            == 200
        )
        assert api_client.post(f"/api/content-factory/whop/packs/{pid}/submitted").status_code == 200
        paid = api_client.post(f"/api/content-factory/whop/packs/{pid}/paid", json={"amount_usd": 33.0})
        assert paid.status_code == 200
        assert paid.json()["status"] == "paid"
        body = api_client.get("/api/content-factory/whop/packs").json()
        assert body["paid_usd"] == 33.0

    def test_bad_type_422_and_unknown_404(self, api_client: TestClient) -> None:
        assert (
            api_client.post(
                "/api/content-factory/whop/packs", json={"campaign_name": "X", "campaign_type": "x"}
            ).status_code
            == 422
        )
        assert (
            api_client.post("/api/content-factory/whop/packs/nope/video", json={"video_path": "/tmp/a.mp4"}).status_code
            == 404
        )
        assert (
            api_client.post(
                "/api/content-factory/whop/evaluate", json={"rate_per_1k_usd": 0.3, "cap_usd": 50.0}
            ).json()["verdict"]
            == "SKIP"
        )


class TestCampaignRank:
    def _brief(self, store: ClipPackStore, name: str, **kw) -> str:
        base = {"campaign_type": "ugc", "rate_per_1k_usd": 2.0, "cap_usd": 200.0, "language": "en", "verified": True}
        base.update(kw)
        brief, verdict = store.register_campaign(name, **base)
        assert brief is not None
        return brief.id

    def test_rank_orders_by_rate_then_cap(self, store: ClipPackStore) -> None:
        self._brief(store, "Low", rate_per_1k_usd=1.0, cap_usd=500.0)
        self._brief(store, "High", rate_per_1k_usd=3.0, cap_usd=100.0)
        ranked = store.rank_campaigns()
        assert [r["brief"]["name"] for r in ranked] == ["High", "Low"]

    def test_rank_excludes_unverified_paid_entry_wrong_lang_nonviable(self, store: ClipPackStore) -> None:
        self._brief(store, "OK", language="es")
        self._brief(store, "Unver", verified=False)
        self._brief(store, "Paid", entry_fee_usd=10.0)
        self._brief(store, "Other", language="other")
        self._brief(store, "Cheap", rate_per_1k_usd=0.2)
        assert [r["brief"]["name"] for r in store.rank_campaigns()] == ["OK"]

    def test_register_rejects_bad_type_and_lang(self, store: ClipPackStore) -> None:
        brief, verdict = store.register_campaign("X", campaign_type="viral")
        assert brief is None and verdict["verdict"] == "SKIP"
        brief, verdict = store.register_campaign("X", language="pt")
        assert brief is None and verdict["verdict"] == "SKIP"

    def test_campaigns_survive_reload(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        first = ClipPackStore()
        self._brief(first, "Persist")
        assert any(c.name == "Persist" for c in ClipPackStore().list_campaigns())


class FakeMPT:
    def __init__(self, healthy: bool = True, video: str | None = "/tmp/fake.mp4") -> None:
        self.healthy = healthy
        self.video = video
        self.subjects: list[str] = []

    async def wait_for_healthy(self, timeout: float = 30.0, interval: float = 2.0) -> bool:
        return self.healthy

    async def generate_video(self, request):  # type: ignore[no-untyped-def]
        self.subjects.append(request.video_subject)
        return type("Resp", (), {"task_id": "t1"})()

    async def wait_for_completion(self, task_id: str, timeout: float = 600.0):  # type: ignore[no-untyped-def]
        return type("St", (), {"videos": [self.video] if self.video else []})()


class TestAutoBuild:
    def _seed(self, store: ClipPackStore) -> None:
        store.register_campaign("Top ES", "ugc", 3.0, 300.0, language="es", verified=True)
        store.register_campaign("Mid EN", "ugc", 1.5, 150.0, language="en", verified=True)

    async def _run(self, store, mpt, **kw):
        import asyncio

        return asyncio.get_event_loop().run_until_complete(auto_build_packs(store, mpt_client=mpt, **kw))

    def test_builds_top_and_generates_video(self, store: ClipPackStore) -> None:
        import asyncio

        self._seed(store)
        out = asyncio.new_event_loop().run_until_complete(auto_build_packs(store, mpt_client=FakeMPT()))
        assert out["created"] == 2 and out["videos_ready"] == 2
        names = {p.campaign_name for p in store.list()}
        assert names == {"Top ES", "Mid EN"}
        assert all(p.status == "ready" for p in store.list())

    def test_no_duplicate_active_pack(self, store: ClipPackStore) -> None:
        import asyncio

        self._seed(store)
        fake = FakeMPT()
        asyncio.new_event_loop().run_until_complete(auto_build_packs(store, mpt_client=fake, max_new=1))
        out = asyncio.new_event_loop().run_until_complete(auto_build_packs(store, mpt_client=fake, max_new=5))
        assert out["created"] == 1  # solo Mid EN (Top ES ya tiene pack activo)
        assert any("ya existe" in s for s in out["skipped"])

    def test_mpt_down_skips_without_creating(self, store: ClipPackStore) -> None:
        import asyncio

        self._seed(store)
        out = asyncio.new_event_loop().run_until_complete(auto_build_packs(store, mpt_client=FakeMPT(healthy=False)))
        assert out["created"] == 0 and any("mpt_unhealthy" in s for s in out["skipped"])

    def test_no_viable_briefs(self, store: ClipPackStore) -> None:
        import asyncio

        out = asyncio.new_event_loop().run_until_complete(auto_build_packs(store, mpt_client=FakeMPT()))
        assert out["created"] == 0 and any("viables" in s for s in out["skipped"])


class TestWhopCampaignApi:
    def test_register_rank_autobuild(self, api_client: TestClient, monkeypatch) -> None:
        import cores.content_factory.whop as whop_mod

        async def _fake_build(store, **kw):  # type: ignore[no-untyped-def]
            return {"created": 0, "videos_ready": 0, "skipped": ["mpt_unhealthy (mock)"]}

        monkeypatch.setattr(whop_mod, "auto_build_packs", _fake_build)
        reg = api_client.post(
            "/api/content-factory/whop/campaigns",
            json={
                "name": "Roobet",
                "campaign_type": "clipping",
                "rate_per_1k_usd": 1.0,
                "cap_usd": 250.0,
                "language": "en",
                "verified": True,
            },
        )
        assert reg.status_code == 201
        assert reg.json()["verdict"]["verdict"] == "VIABLE"
        ranked = api_client.get("/api/content-factory/whop/campaigns").json()
        assert ranked["total"] == 1
        # MPT caído en este entorno → auto-build degradado honesto, sin crear
        auto = api_client.post("/api/content-factory/whop/auto-build").json()
        assert auto["created"] == 0
        assert any("mpt" in s for s in auto["skipped"])
        bad = api_client.post("/api/content-factory/whop/campaigns", json={"name": "X", "language": "pt"})
        assert bad.status_code == 422
