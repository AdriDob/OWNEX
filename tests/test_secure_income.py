"""SECURE_INCOME / SECURE_PLUS_UPSIDE + P(CASH) — base segura + upside medido."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.direct_work import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def op_dict(**overrides) -> dict:
    data = {
        "id": "op-1",
        "title": "Annotation task",
        "platform": "workana",
        "category": "data_annotation",
        "specialization": None,
        "remote": True,
        "payment": 200.0,
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
        "skills": ["python", "data"],
    }
    data.update(overrides)
    return data


class TestPCash:
    def test_chain_product(self) -> None:
        from cores.direct_work_engine.economics import compute_p_cash

        out = compute_p_cash({"p_complete": 0.95, "p_accept": 0.97, "p_pay": 0.99})
        assert out.p_cash is not None
        assert abs(out.p_cash - round(0.95 * 0.97 * 0.99, 4)) < 1e-9
        assert out.band == "HIGH"
        assert out.formula_version == "PCASH-V1"

    def test_unknown_when_stage_missing(self) -> None:
        from cores.direct_work_engine.economics import compute_p_cash

        out = compute_p_cash({"p_complete": 0.95, "p_accept": None, "p_pay": 0.99})
        assert out.p_cash is None
        assert out.band == "UNKNOWN"
        assert any("p_accept" in w for w in out.warnings)

    def test_unknown_when_empty_or_out_of_range(self) -> None:
        from cores.direct_work_engine.economics import compute_p_cash

        assert compute_p_cash({}).band == "UNKNOWN"
        assert compute_p_cash({"p_accept": 1.5}).band == "UNKNOWN"
        assert compute_p_cash({"p_accept": -0.1}).band == "UNKNOWN"

    def test_bands(self) -> None:
        from cores.direct_work_engine.economics import compute_p_cash

        assert compute_p_cash({"a": 0.9, "b": 0.9}).band == "HIGH"  # 0.81
        assert compute_p_cash({"a": 0.8, "b": 0.8}).band == "MEDIUM"  # 0.64
        assert compute_p_cash({"a": 0.2, "b": 0.8}).band == "LOW"  # 0.16


class TestSecurePresets:
    def test_presets_validate_and_sum_to_one(self) -> None:
        from cores.direct_work_engine.recommendation import (
            SECURE_INCOME_RECOMMENDER_CONFIG,
            SECURE_PLUS_UPSIDE_RECOMMENDER_CONFIG,
        )

        assert SECURE_INCOME_RECOMMENDER_CONFIG.validate()
        assert SECURE_PLUS_UPSIDE_RECOMMENDER_CONFIG.validate()
        assert SECURE_INCOME_RECOMMENDER_CONFIG.enforce_acceptance_floor is True
        assert SECURE_INCOME_RECOMMENDER_CONFIG.min_acceptance_probability == 0.5
        assert SECURE_INCOME_RECOMMENDER_CONFIG.max_per_platform == 2
        assert SECURE_PLUS_UPSIDE_RECOMMENDER_CONFIG.enforce_acceptance_floor is False
        assert SECURE_PLUS_UPSIDE_RECOMMENDER_CONFIG.min_acceptance_probability == 0.3

    def test_secure_income_filters_low_acceptance(self) -> None:
        profile = profile_dict(
            skills=["data", "python"],
            experience_level="junior",
            platform_success_rates={"workana": 0.95},
            category_success_rates={"data_annotation": 0.95},
        )
        payload = {
            "profile": profile,
            "opportunities": [
                op_dict(id="secure-high", payment=200.0, platform="workana", category="data_annotation"),
                op_dict(
                    id="risky-low",
                    payment=5000.0,
                    platform="opire",
                    category="dev_bounty",
                    experience_required="senior",
                    portfolio_required=True,
                    interview_required=True,
                    technical_test_required=True,
                    registration_required=True,
                ),
            ],
            "mode": "secure_income",
        }
        resp = client.post("/direct-work/recommend", json=payload)
        assert resp.status_code == 200
        ranked = resp.json()["ranked"]
        assert len(ranked) == 1
        assert ranked[0]["opportunity"]["id"] == "secure-high"

    def test_secure_income_ranks_acceptance_over_reward(self) -> None:
        profile = profile_dict(
            skills=["data", "python"],
            experience_level="junior",
            platform_success_rates={"workana": 0.95, "opire": 0.95},
            category_success_rates={"data_annotation": 0.95, "dev_bounty": 0.95},
        )
        payload = {
            "profile": profile,
            "opportunities": [
                op_dict(
                    id="high-reward",
                    payment=5000.0,
                    platform="opire",
                    category="dev_bounty",
                    technology_tags=["python"],
                    experience_required="senior",
                ),
                op_dict(
                    id="high-accept",
                    payment=200.0,
                    platform="workana",
                    category="data_annotation",
                    technology_tags=["data"],
                    experience_required="junior",
                ),
            ],
            "mode": "secure_income",
        }
        resp = client.post("/direct-work/recommend", json=payload)
        assert resp.status_code == 200
        ranked = resp.json()["ranked"]
        assert len(ranked) == 2
        # secure base: aceptación manda sobre recompensa nominal
        assert ranked[0]["opportunity"]["id"] == "high-accept"

    def test_p_cash_exposed_in_api(self) -> None:
        payload = {
            "profile": profile_dict(),
            "opportunities": [op_dict(id="cash-1")],
            "mode": "secure_plus_upside",
        }
        resp = client.post("/direct-work/recommend", json=payload)
        assert resp.status_code == 200
        ranked = resp.json()["ranked"]
        assert len(ranked) == 1
        item = ranked[0]
        assert "p_cash" in item
        assert "p_cash_band" in item
        assert item["p_cash_band"] in ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
        if item["p_cash"] is not None:
            assert 0.0 <= item["p_cash"] <= 1.0
        assert any("P(CASH)" in r for r in item["recommendation_reasoning"])

    def test_plus_upside_allows_lower_floor_than_secure(self) -> None:
        profile = profile_dict(
            skills=["data", "python"],
            experience_level="junior",
            platform_success_rates={"workana": 0.95},
            category_success_rates={"data_annotation": 0.95},
        )
        opps = [
            op_dict(id="secure-high", payment=200.0, platform="workana", category="data_annotation"),
            op_dict(
                id="risky-low",
                payment=5000.0,
                platform="opire",
                category="dev_bounty",
                experience_required="senior",
                portfolio_required=True,
                interview_required=True,
                technical_test_required=True,
                registration_required=True,
            ),
        ]
        secure = client.post(
            "/direct-work/recommend",
            json={"profile": profile, "opportunities": opps, "mode": "secure_income"},
        ).json()["ranked"]
        plus = client.post(
            "/direct-work/recommend",
            json={"profile": profile, "opportunities": opps, "mode": "secure_plus_upside"},
        ).json()["ranked"]
        assert len(secure) == 1
        assert len(plus) >= len(secure)

    def test_balanced_still_default(self) -> None:
        payload = {"profile": profile_dict(), "opportunities": [op_dict(id="b-1")]}
        resp = client.post("/direct-work/recommend", json=payload)
        assert resp.status_code == 200
        assert resp.json()["ranked"][0]["opportunity"]["id"] == "b-1"
