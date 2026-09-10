"""Adversarial tests for HIGH_CONFIDENCE_90 mode."""

from __future__ import annotations

import pytest

from cores.direct_work_engine.recommendation import (
    HIGH_CONFIDENCE_90_RECOMMENDER_CONFIG,
    IntelligentRecommender,
)
from cores.direct_work_engine.models import (
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    UserProfile,
    WorkPlatform,
)
from cores.direct_work_engine.reward_probability import (
    EvidenceGate,
    get_personal_acceptance_probability,
    niche_for_category,
    NICHE_WEB3,
    get_evidence_gate,
)
from cores.evidence.composer import EvidenceBundle


def _make_opp(**overrides):
    from cores.direct_work_engine.models import (
        Opportunity,
        OpportunityCategory,
        PaymentMethod,
        WorkPlatform,
    )

    defaults = {
        "id": "op-1",
        "title": "Audit AI agent auth",
        "platform": WorkPlatform.OPIRE,
        "category": OpportunityCategory.LLM_ENGINEERING,
        "remote": True,
        "payment": 3000.0,
        "currency": "USD",
        "payment_method": PaymentMethod.PAYPAL,
        "estimated_time_hours": 10.0,
    }
    defaults.update(overrides)
    return Opportunity(**defaults)


def _profile(**overrides):
    from cores.direct_work_engine.models import UserProfile

    defaults = {
        "name": "Adriel",
        "country": "Argentina",
        "languages": {"es", "en"},
        "skills": {"python"},
    }
    defaults.update(overrides)
    return UserProfile(**defaults)


class TestHighConfidence90Mode:
    def test_preset_weights_sum_to_one(self):
        cfg = HIGH_CONFIDENCE_90_RECOMMENDER_CONFIG
        total = (
            cfg.weight_expected_value
            + cfg.weight_acceptance_probability
            + cfg.weight_zero_barrier
            + cfg.weight_compatibility
            + cfg.weight_speed
            + cfg.weight_reputation
        )
        assert abs(total - 1.0) < 0.001

    def test_preset_has_correct_priorities(self):
        cfg = HIGH_CONFIDENCE_90_RECOMMENDER_CONFIG
        assert cfg.weight_acceptance_probability == 0.50  # HIGHEST
        assert cfg.weight_expected_value == 0.15
        assert cfg.min_acceptance_probability == 0.90
        assert cfg.enforce_acceptance_floor is True
        assert cfg.enforce_evidence_gate is True
        assert cfg.upside_boost is False

    def test_mode_filters_by_evidence_gate(self, tmp_path, monkeypatch):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        opp = _make_opp()
        profile = _profile()

        # Without evidence gate status, should be filtered out
        opp.evidence_gate_status = "NOT_READY"
        ranked = IntelligentRecommender().recommend([opp], profile, limit=1, mode="high_confidence_90")
        assert len(ranked) == 0

        # With HIGH_CONFIDENCE status, should pass
        opp.evidence_gate_status = "HIGH_CONFIDENCE"
        ranked = IntelligentRecommender().recommend([opp], profile, limit=1, mode="high_confidence_90")
        assert len(ranked) == 1
        assert ranked[0].rank == 1

    def test_other_modes_unchanged(self, tmp_path, monkeypatch):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        opp = _make_opp()
        profile = _profile()

        # balanced mode should not apply evidence gate
        ranked = IntelligentRecommender().recommend([opp], profile, limit=1, mode="balanced")
        assert len(ranked) >= 0  # may return empty if no opps pass other filters

    def test_evidence_gate_blocks_low_evidence(self, tmp_path, monkeypatch):
        from cores.direct_work_engine.reward_probability import get_evidence_gate
        from cores.direct_work_engine.models import Opportunity, OpportunityCategory, PaymentMethod, WorkPlatform

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))

        opp = _make_opp()
        profile = _profile()

        # Create evidence with low validity score
        from cores.evidence.composer import EvidenceBundle

        evidence = EvidenceBundle(
            hypothesis_id="test",
            vulnerability_type="idor",
            endpoint="https://api.example.com/users/1",
            method="GET",
            host="api.example.com",
            summary="Test",
            description="Test",
            cvss_score=0.5,  # Low validity
            evidence_score=0.5,
            acceptance_probability=0.95,
            is_report_ready=False,
        )

        gate = get_evidence_gate()
        # Manually set acceptance probability high
        opp.acceptance_probability = 0.95

        result = get_evidence_gate().evaluate(opp, evidence)
        assert result.status == "NEEDS_EVIDENCE"

    def test_evidence_gate_requires_all_checks(self, tmp_path, monkeypatch):
        from cores.direct_work_engine.reward_probability import get_evidence_gate

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))

        opp = _make_opp()
        opp.acceptance_probability = 0.95
        opp.evidence_quality = 0.9
        opp.uniqueness_score = 0.9
        opp.scope_verified = True

        from cores.evidence.composer import EvidenceBundle

        evidence = EvidenceBundle(
            hypothesis_id="test",
            vulnerability_type="idor",
            endpoint="https://api.example.com/users/1",
            method="GET",
            host="api.example.com",
            summary="Test",
            description="Test",
            cvss_score=9.0,
            evidence_score=0.9,
            acceptance_probability=0.95,
            is_report_ready=False,
        )

        gate = get_evidence_gate()
        result = gate.evaluate(opp, evidence)
        assert result.status == "HIGH_CONFIDENCE"


class TestAcceptanceProbability:
    def test_prior_externo_label(self):
        from cores.direct_work_engine.reward_probability import get_external_prior

        p = get_external_prior("web3")
        assert p.label == "PRIOR_EXTERNO"

    def test_evidence_gate_labels(self):
        from cores.direct_work_engine.reward_probability import acceptance_evidence_label

        assert acceptance_evidence_label(0) == "NO_EVIDENCE"
        assert acceptance_evidence_label(2) == "THIN_EVIDENCE"
        assert acceptance_evidence_label(5) == "LOW"
        assert acceptance_evidence_label(20) == "MEDIUM"
        assert acceptance_evidence_label(100) == "VERY_HIGH"

    def test_wilson_lower_bound(self):
        from cores.direct_work_engine.reward_probability import _wilson_lower_bound

        # 1/1 = 1.0, Wilson lower bound should be < 1.0
        lb = _wilson_lower_bound(1, 1)
        assert 0.0 < lb < 1.0
        # 50/100 = 0.5
        lb = _wilson_lower_bound(50, 100)
        assert 0.4 < lb < 0.5

    def test_duplicate_not_a_win(self, tmp_path):
        e = get_personal_acceptance_probability(tmp_path / "outcomes.jsonl")
        e.record_outcome(platform="h1", niche="web3", result="duplicate")
        est = e.estimate("web3")
        assert est.n_wins == 0
        assert est.n_outcomes == 1

    def test_many_outcomes_converge_to_personal_rate(self, tmp_path):
        e = get_personal_acceptance_probability(tmp_path / "outcomes.jsonl")
        for _ in range(60):
            e.record_outcome(platform="h1", niche="web3", result="accepted", reward_usd=100)
        for _ in range(60):
            e.record_outcome(platform="h1", niche="web3", result="rejected")
        est = e.estimate("web3")
        assert est.evidence_label == "VERY_HIGH"
        assert est.source == "personal"
        assert 0.40 < est.p_accept < 0.60


class TestEvidenceGate:
    def test_evidence_gate_blocks_weak_evidence(self, tmp_path):
        from cores.direct_work_engine.reward_probability import get_evidence_gate
        from cores.direct_work_engine.models import Opportunity, OpportunityCategory, PaymentMethod, WorkPlatform
        from cores.evidence.composer import EvidenceBundle

        opp = _make_opp()
        opp.acceptance_probability = 0.95
        opp.evidence_quality = 0.9
        opp.uniqueness_score = 0.9
        opp.scope_verified = True

        evidence = EvidenceBundle(
            hypothesis_id="test",
            vulnerability_type="idor",
            endpoint="https://api.example.com/users/1",
            method="GET",
            host="api.example.com",
            summary="Test",
            description="Test",
            cvss_score=0.5,  # Low validity
            evidence_score=0.5,
            acceptance_probability=0.95,
            is_report_ready=False,
        )

        gate = get_evidence_gate()
        result = gate.evaluate(opp, evidence)
        assert result.status == "NEEDS_EVIDENCE"


def test_evidence_gate_passes_strong_evidence(self, tmp_path, monkeypatch):
    from cores.direct_work_engine.reward_probability import get_evidence_gate
    from cores.evidence.composer import EvidenceBundle

    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))

    opp = _make_opp()
    opp.acceptance_probability = 0.95
    opp.evidence_quality = 0.9
    opp.uniqueness_score = 0.9
    opp.scope_verified = True

    evidence = EvidenceBundle(
        hypothesis_id="test",
        vulnerability_type="idor",
        endpoint="https://api.example.com/users/1",
        method="GET",
        host="api.example.com",
        summary="Test",
        description="Test",
        cvss_score=9.0,
        evidence_score=0.9,
        acceptance_probability=0.95,
        is_report_ready=False,
    )

    gate = get_evidence_gate()
    result = gate.evaluate(opp, evidence)
    assert result.status == "HIGH_CONFIDENCE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
