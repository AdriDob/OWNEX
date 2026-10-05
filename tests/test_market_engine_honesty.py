"""Honestidad del motor de mercado: nada de 0.0 hardcodeado como si fuera real.

Contexto (audit 2026-09-28):
- /api/daily-brief leía `opp.expected_value_usd_per_hour`, campo que NUNCA existió
  en direct_work_engine.models.Opportunity → `expected_value_per_hour` salía 0.0
  en cada item. Ahora usa el SSOT: `ranked.htroi.usd_per_hour` (compute_htroi).
- /api/unified-income/dashboard devolvía 0.0 en los tres agregados y listas
  vacías; se calculaba capital/risk y se descartaba. Ahora expone data real y
  None (UNKNOWN) donde no hay medición.
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.daily_brief import router as brief_router
from api.routers.unified_income import router as income_router

app = FastAPI()
app.include_router(brief_router)
app.include_router(income_router)
client = TestClient(app)


class TestUnifiedIncomeHonesty:
    def test_dashboard_unknown_not_zero(self) -> None:
        r = client.get("/api/unified-income/dashboard")
        assert r.status_code == 200
        body = r.json()
        # UNKNOWN ≠ 0.0
        assert body["total_ev_hour"] is None
        assert body["total_expected_value"] is None
        assert body["total_probability"] is None

    def test_dashboard_exposes_real_engines(self) -> None:
        r = client.get("/api/unified-income/dashboard")
        body = r.json()
        assert "capital" in body["by_engine"]
        assert "risk" in body["by_engine"]
        assert "total_capital" in body["by_engine"]["capital"]

    def test_ev_ranking_empty_but_valid(self) -> None:
        r = client.get("/api/unified-income/ev-ranking")
        assert r.status_code == 200
        body = r.json()
        assert body["all_ranked"] == []
        assert body["best_overall"] is None


class TestDailyBriefPerHour:
    def test_uses_htroi_and_never_zero_fake(self) -> None:
        """El $/h sale del htroi del recommender; sin htroi → None (no 0.0 falso)."""
        import asyncio

        from api.routers import daily_brief as db
        from cores.direct_work_engine.models import Opportunity, OpportunityCategory, WorkPlatform

        opp = Opportunity(
            id="o1",
            title="T",
            platform=WorkPlatform.ALGORA,
            category=OpportunityCategory.DEV_BOUNTY,
            payment=100.0,
            estimated_time_hours=2.0,
        )

        class FakeEngine:
            class discovery:  # noqa: N801
                @staticmethod
                async def discover_all():
                    return [opp]

        class FakeRanked:
            def __init__(self, htroi):
                self.final_score = 1.0
                self.htroi = htroi
                self.opportunity = opp

        class FakeRec:
            def __init__(self, htroi):
                self._h = htroi

            def recommend(self, *a, **kw):
                return [FakeRanked(self._h)]

        import cores.direct_work_engine as dwe_mod

        with (
            patch.object(dwe_mod, "get_direct_work_engine", lambda: FakeEngine()),
            patch.object(db, "_get_recommender", lambda: FakeRec({"usd_per_hour": 25.0})),
        ):
            out = asyncio.run(db.daily_brief())
            assert [a for a in out["actions"] if a["id"] == "o1"][0]["expected_value_per_hour"] == 25.0

            # Sin htroi medido: None, jamás 0.0 (UNKNOWN no es cero)
            with patch.object(db, "_get_recommender", lambda: FakeRec(None)):
                out2 = asyncio.run(db.daily_brief())
        row = [a for a in out2["actions"] if a["id"] == "o1"][0]
        assert row["expected_value_per_hour"] is None
