"""Tests for the Direct Work Engine API router (score / recommend / learn / status)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.direct_work import router
from cores.direct_work_engine.models import Opportunity

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def op_dict(**overrides) -> dict:
    data = {
        "id": "op-1",
        "title": "Fix a bug in an open-source game backend",
        "platform": "algora",
        "category": "game_development",
        "specialization": "game_backend",
        "remote": True,
        "payment": 500.0,
        "currency": "USD",
        "payment_method": "paypal",
        "payment_proven": True,
        "time_to_payout_days": 5,
    }
    data.update(overrides)
    return data


def profile_dict(**overrides) -> dict:
    data = {
        "name": "Adriel",
        "country": "Argentina",
        "languages": ["es", "en"],
        "skills": ["python", "unity"],
    }
    data.update(overrides)
    return data


class TestDirectWorkApi:
    def test_status_endpoint(self) -> None:
        response = client.get("/direct-work/status")
        assert response.status_code == 200
        body = response.json()
        assert "stats" in body
        assert "platforms" in body
        assert "sources" in body

    def test_score_sorts_by_barrier_desc(self) -> None:
        payload = {
            "opportunities": [
                op_dict(
                    id="op-easy",
                    experience_required="none",
                ),
                op_dict(
                    id="op-hard",
                    experience_required="senior",
                    portfolio_required=True,
                    interview_required=True,
                    technical_test_required=True,
                    registration_required=True,
                    remote=False,
                    time_to_payout_days=90,
                ),
            ]
        }
        response = client.post("/direct-work/score", json=payload)
        assert response.status_code == 200
        scored = response.json()["scored"]
        assert scored[0]["id"] == "op-easy"
        assert scored[0]["zero_barrier_score"]["total"] > scored[1]["zero_barrier_score"]["total"]

    def test_recommend_returns_ranked(self) -> None:
        payload = {
            "profile": profile_dict(),
            "opportunities": [
                op_dict(id="op-a", payment=1000.0),
                op_dict(id="op-b", payment=200.0, category="dev_bounty", specialization=None),
                op_dict(id="op-c", payment=50.0, category="data_annotation", specialization=None),
            ],
            "limit": 3,
        }
        response = client.post("/direct-work/recommend", json=payload)
        assert response.status_code == 200
        ranked = response.json()["ranked"]
        assert len(ranked) == 3
        assert ranked[0]["rank"] == 1
        assert ranked[0]["opportunity"]["id"] == "op-a"
        assert ranked[0]["overall_recommendation_score"] >= ranked[1]["overall_recommendation_score"]
        assert "strategy" in ranked[0]

    def test_learn_folds_outcomes_into_profile(self) -> None:
        payload = {
            "profile": profile_dict(),
            "records": [
                {"platform": "algora", "category": "dev_bounty", "accepted": True, "amount": 500.0},
                {"platform": "algora", "category": "dev_bounty", "accepted": False, "amount": 0.0},
            ],
        }
        response = client.post("/direct-work/learn", json=payload)
        assert response.status_code == 200
        profile = response.json()["profile"]
        assert profile["applications_submitted"] == 2
        assert profile["applications_accepted"] == 1
        assert profile["total_earnings"] == 500.0
        assert profile["platform_success_rates"] == {"algora": 0.5}

    def test_recommend_handles_empty_opportunities(self) -> None:
        from api.routers import direct_work as dw

        engine = dw.get_engine()
        with patch.object(engine.discovery, "discover_all", new=AsyncMock(return_value=[])):
            response = client.post("/direct-work/recommend", json={"profile": profile_dict(), "opportunities": []})
        assert response.status_code == 200
        assert response.json()["ranked"] == []

    def test_recommend_auto_discovers_when_empty(self) -> None:
        from api.routers import direct_work as dw
        from cores.direct_work_engine.models import Opportunity, OpportunityCategory, WorkPlatform

        op = Opportunity(
            id="op-1",
            title="Fix bug",
            platform=WorkPlatform.OPIRE,
            category=OpportunityCategory.DEV_BOUNTY,
            payment=300.0,
        )
        engine = dw.get_engine()
        with patch.object(engine.discovery, "discover_all", new=AsyncMock(return_value=[op])):
            response = client.post("/direct-work/recommend", json={"profile": profile_dict(), "opportunities": []})
        assert response.status_code == 200
        ranked = response.json()["ranked"]
        assert len(ranked) == 1
        assert ranked[0]["opportunity"]["id"] == "op-1"

    def test_discover_runs_live_scan_and_scores(self) -> None:
        from api.routers import direct_work as dw
        from cores.direct_work_engine.models import Opportunity, OpportunityCategory, WorkPlatform

        op = Opportunity(
            id="op-1",
            title="Migrate REST to GraphQL",
            platform=WorkPlatform.OPIRE,
            category=OpportunityCategory.DEV_BOUNTY,
            payment=1500.0,
        )
        engine = dw.get_engine()
        with patch.object(engine.discovery, "discover_all", new=AsyncMock(return_value=[op])):
            response = client.post("/direct-work/discover", json={"limit": 10})
        assert response.status_code == 200
        body = response.json()
        assert body["discovered"] == 1
        assert body["opportunities"][0]["id"] == "op-1"
        assert body["opportunities"][0]["zero_barrier_score"]["total"] > 0

    def test_daily_brief_returns_top_opportunity_and_learning(self) -> None:
        from api.routers import direct_work as dw
        from cores.direct_work_engine.models import Opportunity, OpportunityCategory, WorkPlatform

        op = Opportunity(
            id="op-1",
            title="Migrate REST to GraphQL",
            platform=WorkPlatform.OPIRE,
            category=OpportunityCategory.DEV_BOUNTY,
            payment=1500.0,
            technology_tags=["graphql"],
        )
        engine = dw.get_engine()
        with patch.object(engine.discovery, "discover_all", new=AsyncMock(return_value=[op])):
            response = client.post(
                "/direct-work/daily-brief",
                json={"profile": profile_dict(skills=["python"])},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["scanned"] == 1
        assert body["top_opportunity"]["opportunity"]["id"] == "op-1"
        assert body["summary"]
        assert "graphql" in [s.lower() for s in body["learning"]["missing_skills"]]


class TestOpireDweAdapter:
    def test_converts_raw_opportunity_to_dwe(self) -> None:
        from core.opportunity.adapters import RawOpportunity
        from cores.direct_work_engine.discovery import UniversalDiscovery
        from cores.direct_work_engine.models import EmploymentType, OpportunityCategory

        raw = RawOpportunity(
            id="b1",
            name="Add OAuth to API",
            description="Implement OAuth2 flow",
            platform="opire",
            url="https://opire.com/b1",
            reward=800.0,
            effort_hours=6,
            tags=["auth", "python"],
        )

        with patch("core.opportunity.adapters.opire.OpireAdapter") as mock_cls:
            mock_cls.return_value.fetch_opportunities = AsyncMock(return_value=[raw])

            from api.adapters.direct_work_opire import OpireDweAdapter

            adapter = OpireDweAdapter()
            discovery = UniversalDiscovery()
            discovery.register_adapter(adapter)
            opportunities = asyncio.run(discovery.discover_all())

        assert len(opportunities) == 1
        opp = opportunities[0]
        assert opp.title == "Add OAuth to API"
        assert opp.category == OpportunityCategory.DEV_BOUNTY
        assert opp.employment_type == EmploymentType.BOUNTY
        assert opp.payment == 800.0
        assert opp.estimated_time_hours == 6
        assert opp.experience_required.value == "none"

    def test_engine_registers_opire_adapter(self) -> None:
        from api.routers.direct_work import get_engine
        from cores.direct_work_engine.models import WorkPlatform

        assert WorkPlatform.OPIRE in get_engine().discovery.adapters

    def test_validate_connection_is_cheap_and_true(self) -> None:
        from api.adapters.direct_work_opire import OpireDweAdapter

        with patch("core.opportunity.adapters.opire.OpireAdapter"):
            instance = OpireDweAdapter()
        assert asyncio.run(instance.validate_connection()) is True


class TestLegacyDweAdapter:
    def test_classifies_freelance_model_as_selection_world(self) -> None:
        from api.adapters.legacy import LegacyOpportunityDweAdapter
        from core.opportunity.adapters import RawOpportunity
        from cores.direct_work_engine.models import EmploymentType, OpportunityCategory, WorkPlatform

        raw = RawOpportunity(
            id="f1", name="Build a landing page", description="", platform="freelancer", reward=1500.0, effort_hours=20
        )
        with patch("core.opportunity.adapters.freelancer.FreelancerAdapter") as mock_cls:
            mock_cls.return_value.fetch_opportunities = AsyncMock(return_value=[raw])
            adapter = LegacyOpportunityDweAdapter(
                mock_cls.return_value,
                name="freelancer",
                platform=WorkPlatform.FREELANCER,
                category=OpportunityCategory.SOFTWARE_ENGINEERING,
                employment_type=EmploymentType.FREELANCE,
            )
            opp = asyncio.run(adapter.fetch_opportunities())[0]

        assert opp.category == OpportunityCategory.SOFTWARE_ENGINEERING
        assert opp.employment_type == EmploymentType.FREELANCE
        assert opp.difficulty.value == "advanced"

    def test_build_default_adapters_includes_real_sources(self) -> None:
        from api.adapters.legacy import build_default_adapters

        adapters = build_default_adapters()
        names = {a.source.name for a in adapters}
        assert {"opire", "issuehunt", "freelancer"} <= names


class TestNegotiationApi:
    def test_negotiate_recommends_decline_for_poor_terms(self) -> None:
        payload = {
            "opportunity": op_dict(
                id="op-terms",
                payment=40.0,
                estimated_time_hours=20,
                payment_method="gift_card",
                time_to_payout_days=60,
                interview_required=True,
            )
        }
        response = client.post("/direct-work/negotiate", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["verdict"] == "decline"
        assert body["terms_issues"]
        assert body["effective_rate_usd_per_hour"] == 2.0

    def test_negotiate_accepts_fair_terms(self) -> None:
        payload = {"opportunity": op_dict(id="op-fair", payment=1000.0, estimated_time_hours=10)}
        response = client.post("/direct-work/negotiate", json=payload)
        assert response.status_code == 200
        assert response.json()["verdict"] == "accept"

    def test_skill_gap_returns_missing_skills_and_plan(self) -> None:
        payload = {
            "opportunity": op_dict(id="op-gap", technology_tags=["react", "docker", "aws"]),
            "profile": profile_dict(skills=["python", "docker"]),
        }
        response = client.post("/direct-work/skill-gap", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert set(body["missing_skills"]) == {"react", "aws"}
        assert body["readiness"] < 1.0
        assert any("react" in step for step in body["learning_plan"])


def make_opp(**overrides) -> Opportunity:
    from cores.direct_work_engine.models import (
        EmploymentType,
        Opportunity,
        OpportunityCategory,
        PaymentMethod,
        WorkPlatform,
    )

    data = {
        "id": "op-1",
        "title": "Fix a public OSS issue",
        "platform": WorkPlatform.OPIRE,
        "category": OpportunityCategory.DEV_BOUNTY,
        "payment": 500.0,
        "payment_method": PaymentMethod.PAYPAL,
        "employment_type": EmploymentType.BOUNTY,
    }
    data.update(overrides)
    return Opportunity(**data)


class TestDeliveryFlow:
    def test_prepare_approve_flow(self, tmp_path, monkeypatch) -> None:
        from cores.direct_work_engine.workbank import WorkBank

        bank = WorkBank(tmp_path / "workbank.json")
        monkeypatch.setattr("api.routers.direct_work.get_workbank", lambda: bank)

        bank.daily_cycle(
            [
                make_opp(
                    id="deliv-1",
                    payment=120.0,
                    description="Fix the login rate-limit bypass",
                    url="https://opire.dev/task/deliv-1",
                )
            ],
            target=1,
        )

        prep = client.post("/direct-work/workbank/deliv-1/deliver/prepare")
        assert prep.status_code == 200
        body = prep.json()
        assert body["item_id"] == "deliv-1"
        assert body["package_path"]
        assert "work.md" in body["files"]
        assert body["submission_url"] == "https://opire.dev/task/deliv-1"

        done = client.post("/direct-work/workbank/deliv-1/deliver/approve")
        assert done.status_code == 200
        assert done.json()["status"] == "delivered"
        assert done.json()["reward"] == 120.0

        item = bank.get_item("deliv-1")
        assert item is not None
        assert item.status == "delivered"
        assert item.ready_to_deliver is False

    def test_prepare_missing_item_404(self) -> None:
        resp = client.post("/direct-work/workbank/does-not-exist/deliver/prepare")
        assert resp.status_code == 404

    def test_deliver_pending_lists_ready_items(self, tmp_path, monkeypatch) -> None:
        from cores.direct_work_engine.workbank import WorkBank

        bank = WorkBank(tmp_path / "wb.json")
        monkeypatch.setattr("api.routers.direct_work.get_workbank", lambda: bank)
        bank.daily_cycle([make_opp(id="pend-1", payment=60.0)], target=1)

        resp = client.get("/direct-work/deliver/pending")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] >= 1
        assert any(i["id"] == "pend-1" for i in body["items"])


class TestSourceTiers:
    def test_default_adapters_assign_tiers(self) -> None:
        from api.adapters.legacy import build_default_adapters

        adapters = build_default_adapters()
        by_name = {a.source.name: a.source for a in adapters}
        assert by_name["opire"].tier == 1
        assert by_name["issuehunt"].tier == 1
        assert by_name["freelancer"].tier == 3
        assert by_name["opencollective"].tier == 3

    def test_source_status_exposes_tier_and_cadence(self) -> None:
        from api.routers.direct_work import get_engine

        status = get_engine().discovery.get_source_status()
        assert status
        row = next(iter(status.values()))
        assert "tier" in row
        assert "analysis_cadence_hours" in row

    def test_platform_tier_maps_access_status(self) -> None:
        from cores.direct_work_engine.workbank import platform_tier

        assert platform_tier("public") == 1
        assert platform_tier("needs_api_key") == 2
        assert platform_tier("needs_manual_setup") == 3
        assert platform_tier("unknown") == 3


class TestAnalysisCardApi:
    def test_analysis_card_unifies_all_analysis(self) -> None:
        payload = {
            "opportunity": op_dict(id="card-1", payment=900.0, technology_tags=["python", "aws"]),
            "profile": profile_dict(skills=["python"]),
        }
        resp = client.post("/direct-work/analysis-card", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["card_id"] == "algora:card-1"
        assert body["opportunity"]["id"] == "card-1"
        assert 0 <= body["zero_barrier_score"]["total"] <= 100
        assert body["recommendation"]["opportunity"]["id"] == "card-1"
        assert "verdict" in body["negotiation"]
        assert "missing_skills" in body["skill_gap"]
        assert body["access"]["platform"] == "algora"
        assert body["access"]["tier"] >= 1
        assert body["access"]["status"]

    def test_analysis_card_includes_access_requirement(self) -> None:
        payload = {
            "opportunity": op_dict(id="card-2", platform="freelancer"),
            "profile": profile_dict(),
        }
        resp = client.post("/direct-work/analysis-card", json=payload)
        assert resp.status_code == 200
        access = resp.json()["access"]
        assert access["tier"] == 2 or access["tier"] == 3


class TestAccessExplainApi:
    def test_access_explain_lists_platforms_with_reasons(self) -> None:
        resp = client.get("/direct-work/access/explain")
        assert resp.status_code == 200
        body = resp.json()
        assert "tiers" in body
        assert body["platforms"]
        platforms = {p["platform"] for p in body["platforms"]}
        assert {"opire", "freelancer", "opencollective"} <= platforms
        for p in body["platforms"]:
            assert p["access_status"] in {"public", "needs_api_key", "needs_manual_setup"}
            assert p["explanation"]
            assert "registered" in p

    def test_access_explain_public_platforms_are_tier_one(self) -> None:
        resp = client.get("/direct-work/access/explain")
        body = resp.json()
        opire = next(p for p in body["platforms"] if p["platform"] == "opire")
        assert opire["tier"] == 1
        assert opire["access_status"] == "public"


class TestStrictFilterApi:
    def test_filter_rejects_garbage_and_reports_reasons(self) -> None:
        payload = {
            "opportunities": [
                op_dict(id="good-1"),
                op_dict(id="no-pay", payment=0.0),
                op_dict(id="onsite", remote=False),
                op_dict(id="funnel", interview_required=True, portfolio_required=True, registration_required=True),
            ]
        }
        resp = client.post("/direct-work/filter", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["analyzed"] == 4
        assert body["passed"] == 1
        assert body["passed_ids"] == ["good-1"]
        assert body["rejected_reasons"]["no-pay"][0].startswith("unclear_payment")
        assert body["rejected_reasons"]["onsite"][0] == "not_remote: country/location restriction blocks delivery"
        assert body["rejected_reasons"]["funnel"][0].startswith("excessive_application_process")

    def test_filter_rejects_gift_card_payout(self) -> None:
        payload = {"opportunities": [op_dict(id="gift", payment_method="gift_card")]}
        resp = client.post("/direct-work/filter", json=payload)
        assert resp.status_code == 200
        assert resp.json()["rejected_reasons"]["gift"][0].startswith("suspicious_platform")


class TestEvolutionApi:
    def test_evolution_report_lost_to_learning(self) -> None:
        payload = {
            "profile": profile_dict(skills=["python"]),
            "records": [
                {"platform": "algora", "category": "devops", "accepted": False, "amount": 0.0},
                {"platform": "opire", "category": "bug_bounty", "accepted": True, "amount": 400.0},
            ],
            "opportunities": [
                op_dict(id="ev-1", technology_tags=["docker", "kubernetes", "docker", "terraform", "docker"]),
            ],
            "time_invested_hours": 8.0,
        }
        resp = client.post("/direct-work/evolution", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["lessons"][0]["category"] == "devops"
        assert body["lessons"][0]["learning_path"]
        assert any("Docker" in p["name"] for p in body["capabilities"])
        assert body["performance"]["total"] == 2
        assert body["performance"]["revenue"] == 400.0
        assert body["performance"]["roi_usd_per_hour"] == 50.0
        assert body["performance"]["top_platform_by_revenue"] == "opire"

    def test_evolution_empty_history_is_noop(self) -> None:
        payload = {"profile": profile_dict(), "records": [], "opportunities": []}
        resp = client.post("/direct-work/evolution", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["lessons"] == []
        assert body["capabilities"] == []
        assert body["performance"]["total"] == 0


class TestFastIncomeMode:
    def test_fast_income_preset_weights_sum_to_one(self) -> None:
        from cores.direct_work_engine.recommendation import FAST_INCOME_RECOMMENDER_CONFIG

        assert FAST_INCOME_RECOMMENDER_CONFIG.validate()

    def test_recommend_accepts_fast_income_mode(self) -> None:
        payload = {
            "profile": profile_dict(),
            "opportunities": [
                op_dict(id="fi-1", payment=50.0, time_to_payout_days=2),
                op_dict(id="fi-2", payment=5000.0, time_to_payout_days=120, experience_required="senior"),
            ],
            "mode": "fast_income",
        }
        resp = client.post("/direct-work/recommend", json=payload)
        assert resp.status_code == 200
        assert len(resp.json()["ranked"]) >= 1

    def test_balanced_mode_is_default(self) -> None:
        payload = {
            "profile": profile_dict(),
            "opportunities": [op_dict(id="b-1")],
        }
        resp = client.post("/direct-work/recommend", json=payload)
        assert resp.status_code == 200
        assert resp.json()["ranked"][0]["opportunity"]["id"] == "b-1"


class TestMaxSuccessMode:
    def test_max_success_preset_weights_and_floor(self) -> None:
        import dataclasses

        from cores.direct_work_engine.recommendation import MAX_SUCCESS_RECOMMENDER_CONFIG

        cfg = MAX_SUCCESS_RECOMMENDER_CONFIG
        assert cfg.validate()
        assert cfg.weight_acceptance_probability == 0.40
        assert cfg.enforce_acceptance_floor is True
        assert cfg.min_acceptance_probability == 0.5

        relaxed = dataclasses.replace(cfg, enforce_acceptance_floor=False)
        assert relaxed.enforce_acceptance_floor is False

    def _success_max_profile(self, full_history: bool = True) -> dict:
        rates = {
            "platform_success_rates": {"freelancer": 0.95, "opire": 0.95},
            "category_success_rates": {"data_annotation": 0.95, "dev_bounty": 0.95},
        }
        if not full_history:
            rates = {
                "platform_success_rates": {"freelancer": 0.95},
                "category_success_rates": {"data_annotation": 0.95},
            }
        return profile_dict(skills=["data", "python"], experience_level="junior", **rates)

    def test_max_success_drops_low_acceptance_work(self) -> None:
        payload = {
            "profile": self._success_max_profile(full_history=False),
            "opportunities": [
                op_dict(
                    id="ms-high",
                    payment=500.0,
                    platform="freelancer",
                    category="data_annotation",
                    specialization=None,
                    technology_tags=["data"],
                    experience_required="junior",
                ),
                op_dict(
                    id="ms-low",
                    payment=5000.0,
                    platform="opire",
                    category="dev_bounty",
                    specialization=None,
                    technology_tags=["python"],
                    experience_required="senior",
                    portfolio_required=True,
                    interview_required=True,
                    technical_test_required=True,
                    registration_required=True,
                ),
            ],
            "mode": "max_success",
        }
        resp = client.post("/direct-work/recommend", json=payload)
        assert resp.status_code == 200
        ranked = resp.json()["ranked"]
        assert len(ranked) == 1
        assert ranked[0]["opportunity"]["id"] == "ms-high"

        payload["mode"] = "balanced"
        resp = client.post("/direct-work/recommend", json=payload)
        ranked_balanced = resp.json()["ranked"]
        assert len(ranked_balanced) == 2

    def test_max_success_ranks_by_acceptance_over_reward(self) -> None:
        payload = {
            "profile": self._success_max_profile(),
            "opportunities": [
                op_dict(
                    id="high-reward",
                    payment=5000.0,
                    platform="opire",
                    category="dev_bounty",
                    specialization=None,
                    technology_tags=["python"],
                    experience_required="senior",
                ),
                op_dict(
                    id="high-accept",
                    payment=200.0,
                    platform="freelancer",
                    category="data_annotation",
                    specialization=None,
                    technology_tags=["data"],
                    experience_required="junior",
                ),
            ],
            "mode": "max_success",
        }
        resp = client.post("/direct-work/recommend", json=payload)
        assert resp.status_code == 200
        ranked = resp.json()["ranked"]
        assert len(ranked) == 2
        assert ranked[0]["opportunity"]["id"] == "high-accept"


class TestSourceIntelApi:
    def test_radar_reports_curated_database(self) -> None:
        resp = client.post("/direct-work/source-intel", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert body["analyzed"] >= 100
        assert body["total_curated_sources"] == body["analyzed"]
        assert body["stats"]["by_category"]["bug_bounty"] >= 30
        assert any(s["recommendation"] == "DISCOVER" for s in body["sources"])

    def test_radar_card_shape_and_argentina_flags(self) -> None:
        resp = client.post("/direct-work/source-intel", json={"categories": ["dev_bounty"], "query": "opire"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["analyzed"] == 1
        card = body["sources"][0]
        assert card["name"].lower() == "opire"
        assert card["trust_score"] >= 70
        assert card["argentina_compatibility"] == "YES"
        assert card["entry_barrier"] == "LOW"
        assert card["task_transparency"] >= 0.6
        assert card["earning_potential"] in ("MEDIUM", "HIGH", "VERY_HIGH")
        assert card["recommendation"] in ("DISCOVER", "CONSIDER")

    def test_radar_filters_and_uncovered_categories(self) -> None:
        resp = client.post("/direct-work/source-intel", json={"min_trust": 90.0})
        assert resp.status_code == 200
        body = resp.json()
        assert all(s["trust_score"] >= 90 for s in body["sources"])
        assert isinstance(body["uncovered_categories"], list)


class TestBugBountyDweAdapter:
    """Public-grade bug bounty discovery: works with zero keys, honors payout."""

    def test_fetches_public_programs_across_sources(self) -> None:
        from api.adapters.direct_work_bugbounty import _BOUNTY_DATA_URLS, BugBountyDweAdapter

        sample = [
            {"name": "OpenSea", "url": "https://bugcrowd.com/opensea", "max_payout": 3000000},
            {"handle": "tesla", "url": "https://bugcrowd.com/tesla", "offers_bounties": True, "max_payout": 100000},
        ]

        adapter = BugBountyDweAdapter()
        with (
            patch.object(adapter, "_load_json", new=AsyncMock(return_value=sample)),
            patch.object(adapter, "_credentials_for", return_value={}),
        ):
            opps = asyncio.run(adapter.fetch_opportunities())

        assert len(opps) == len(sample) * len(_BOUNTY_DATA_URLS)
        top = max(opps, key=lambda o: o.payment)
        assert top.payment == 3000000.0
        assert top.category.value == "bug_bounty"
        assert top.employment_type.value == "bounty"
        assert top.portfolio_required is False
        assert top.interview_required is False
        assert top.experience_required.value == "none"

    def test_public_grade_requires_registration_when_no_key(self) -> None:
        from api.adapters.direct_work_bugbounty import BugBountyDweAdapter

        adapter = BugBountyDweAdapter()
        with patch.object(adapter, "_load_json", new=AsyncMock(return_value=[])):
            opps = asyncio.run(adapter.fetch_opportunities())
        assert opps == []

    def test_registered_in_default_adapters(self) -> None:
        from api.adapters.legacy import build_default_adapters

        names = [a.source.name for a in build_default_adapters()]
        assert "bugbounty" in names


class TestCashflowRadarApi:
    """Cashflow Radar endpoint: classify by horizon, digest + weekly plan."""

    def test_radar_with_explicit_opportunities(self) -> None:
        payload = {
            "opportunities": [
                op_dict(id="radar-1", payment=40.0, estimated_hours=2),
                op_dict(id="radar-2", payment=200.0, estimated_hours=30),
            ]
        }
        response = client.post("/direct-work/cashflow-radar", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["buckets"]["today"][0]["id"] == "radar-1"
        assert body["buckets"]["week"][0]["id"] == "radar-2"
        assert body["top_pick"]["id"] == "radar-1"
        assert "daily_digest" in body
        assert "weekly_plan" in body

    def test_radar_empty_request_uses_workbank(self) -> None:
        response = client.post("/direct-work/cashflow-radar", json={})
        assert response.status_code == 200
        body = response.json()
        assert set(body["buckets"]) == {"today", "week", "growth"}
        assert set(body["recommended_mix"]) == {"today", "week", "growth"}
