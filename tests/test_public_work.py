"""PUBLIC WORK ladder — classifier + observed claims + API contract."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.direct_work import router
from cores.direct_work_engine.competition_intel import CompetitionIntelEngine
from cores.direct_work_engine.models import Opportunity, OpportunityCategory, WorkPlatform
from cores.direct_work_engine.public_work import (
    RUNG_LABEL_ES,
    PublicWorkRung,
    classify_rung,
    validation_block,
)

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def op_dict(**overrides) -> dict:
    data = {
        "id": "op-1",
        "title": "Fix a bug",
        "platform": "opire",
        "category": "dev_bounty",
        "specialization": None,
        "remote": True,
        "payment": 150.0,
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
        "skills": ["python"],
    }
    data.update(overrides)
    return data


def make_opp(**overrides) -> Opportunity:
    base = {
        "id": "t",
        "title": "t",
        "platform": WorkPlatform.OPIRE,
        "category": OpportunityCategory.DEV_BOUNTY,
        "payment": 150.0,
    }
    base.update(overrides)
    return Opportunity(**base)


class TestClassifyRung:
    def test_zero_payment_is_etapa_0(self) -> None:
        rung, difficulty, unknown = classify_rung(0)
        assert rung == PublicWorkRung.OSS_VALIDATION
        assert difficulty == 0.0

    def test_none_payment_is_etapa_0(self) -> None:
        rung, _, _ = classify_rung(None)
        assert rung == PublicWorkRung.OSS_VALIDATION

    def test_easy_small_bounty_is_beginner(self) -> None:
        rung, _, unknown = classify_rung(50.0, barrier_total=80.0, acceptance=0.85, competition=0.2)
        assert rung == PublicWorkRung.BEGINNER
        assert unknown is False

    def test_hard_big_bounty_is_expert(self) -> None:
        rung, _, _ = classify_rung(5000.0, barrier_total=20.0, acceptance=0.3, competition=0.9)
        assert rung == PublicWorkRung.EXPERT

    def test_100_harder_than_500_possible(self) -> None:
        # Ranges are NOT rules: difficulty decides, not the headline.
        easy_500, _, _ = classify_rung(500.0, barrier_total=90.0, acceptance=0.9, competition=0.1)
        hard_100, _, _ = classify_rung(100.0, barrier_total=10.0, acceptance=0.2, competition=0.95)
        order = list(PublicWorkRung)
        assert order.index(hard_100) > order.index(easy_500)

    def test_unknown_inputs_flagged(self) -> None:
        _, _, unknown = classify_rung(150.0, None, None, None)
        assert unknown is True

    def test_es_labels_cover_all_rungs(self) -> None:
        assert set(RUNG_LABEL_ES) == set(PublicWorkRung)
        assert RUNG_LABEL_ES[PublicWorkRung.OSS_VALIDATION].startswith("Etapa 0")
        assert RUNG_LABEL_ES[PublicWorkRung.BEGINNER] == "Principiante"
        assert RUNG_LABEL_ES[PublicWorkRung.EXPERT] == "Experto"

    def test_validation_block_proof(self) -> None:
        assert validation_block(PublicWorkRung.OSS_VALIDATION)["proof"] == "PR MERGED"
        paid = validation_block(PublicWorkRung.BEGINNER)
        assert paid["proof"] == "PR ACEPTADO + PAGO"
        assert len(paid["checks"]) == 4


class TestActiveClaims:
    def test_default_is_unknown_never_zero(self) -> None:
        a = CompetitionIntelEngine().assess(make_opp())
        assert a.active_claims is None
        assert a.claims_source == "unavailable"
        assert a.claims_observed_at is None

    def test_observed_claims_surface_with_source(self) -> None:
        opp = make_opp(observed_claims={"active_claims": 7, "source": "algora", "observed_at": "2026-09-11"})
        a = CompetitionIntelEngine().assess(opp)
        assert a.active_claims == 7
        assert a.claims_source == "algora"
        assert a.claims_observed_at == "2026-09-11"
        assert any(s.source == "observed_claims" and s.confidence == 0.9 for s in a.signals)

    def test_observed_zero_is_valid_when_reported(self) -> None:
        opp = make_opp(observed_claims={"active_claims": 0, "source": "algora"})
        a = CompetitionIntelEngine().assess(opp)
        assert a.active_claims == 0
        assert a.claims_source == "algora"

    def test_sourceless_count_stays_unknown(self) -> None:
        opp = make_opp(observed_claims={"active_claims": 7})
        a = CompetitionIntelEngine().assess(opp)
        assert a.active_claims is None
        assert a.claims_source == "unavailable"


class TestContract:
    def test_recommend_includes_public_work(self) -> None:
        payload = {
            "profile": profile_dict(),
            "opportunities": [op_dict(id="pw-1")],
            "mode": "secure_plus_upside",
        }
        resp = client.post("/direct-work/recommend", json=payload)
        assert resp.status_code == 200
        item = resp.json()["ranked"][0]
        pw = item["public_work"]
        assert pw["rung"] in ("oss_validation", "beginner", "intermediate", "advanced", "expert")
        assert pw["rung_label_es"]
        assert pw["proof"] in ("PR MERGED", "PR ACEPTADO + PAGO")
        assert isinstance(pw["checks"], list) and pw["checks"]

    def test_zero_payment_item_is_etapa_0(self) -> None:
        payload = {
            "profile": profile_dict(),
            "opportunities": [op_dict(id="pw-0", payment=0.0)],
            "mode": "secure_plus_upside",
        }
        resp = client.post("/direct-work/recommend", json=payload)
        assert resp.status_code == 200
        ranked = resp.json()["ranked"]
        assert ranked
        assert ranked[0]["public_work"]["rung"] == "oss_validation"

    def test_enrich_never_raises(self) -> None:
        from cores.direct_work_engine.public_work import enrich_ranked as enrich

        assert enrich(object())["rung"] == "beginner"
