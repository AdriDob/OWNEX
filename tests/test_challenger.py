"""Tests for ORION Hypothesis Challenger."""

from cores.validation.challenger import (
    AlternativeExplanation,
    ContradictionTest,
    EnrichedVerdictData,
    HypothesisChallenger,
)


class TestAlternativeExplanation:
    def test_to_dict(self):
        alt = AlternativeExplanation(
            label="Recurso público",
            description="El endpoint es público",
            test_description="Hacer request sin auth",
            confidence_reduction=0.3,
        )
        d = alt.to_dict()
        assert d["label"] == "Recurso público"
        assert d["confidence_reduction"] == 0.3


class TestContradictionTest:
    def test_to_dict(self):
        t = ContradictionTest(
            test_type="anonymous_access",
            description="Request sin auth",
            expected_if_vulnerable="403",
            expected_if_not="200",
            info_gain="muy alta",
        )
        d = t.to_dict()
        assert d["test_type"] == "anonymous_access"
        assert d["info_gain"] == "muy alta"


class TestEnrichedVerdictData:
    def test_uncertainty_penalty_mapping(self):
        assert EnrichedVerdictData(uncertainty_level="baja").uncertainty_penalty == 0.0
        assert EnrichedVerdictData(uncertainty_level="media").uncertainty_penalty == 0.05
        assert EnrichedVerdictData(uncertainty_level="alta").uncertainty_penalty == 0.12
        assert EnrichedVerdictData(uncertainty_level="unknown").uncertainty_penalty == 0.03

    def test_to_dict(self):
        data = EnrichedVerdictData(
            alternative_explanations=[
                AlternativeExplanation("a", "d", "t", 0.2)
            ],
            contradiction_tests=[
                ContradictionTest("t1", "d1", "vuln", "not", "alta")
            ],
            missing_verifications=["Falta ownership"],
            next_best_test=ContradictionTest("t2", "d2", "vuln", "not", "muy alta"),
            uncertainty_level="media",
        )
        d = data.to_dict()
        assert len(d["alternative_explanations"]) == 1
        assert len(d["contradiction_tests"]) == 1
        assert len(d["missing_verifications"]) == 1
        assert d["next_best_test"]["test_type"] == "t2"
        assert d["uncertainty_level"] == "media"
        assert d["uncertainty_penalty"] == 0.05

    def test_empty_defaults(self):
        data = EnrichedVerdictData()
        assert data.alternative_explanations == []
        assert data.contradiction_tests == []
        assert data.missing_verifications == []
        assert data.next_best_test is None
        assert data.uncertainty_level == "unknown"


class TestHypothesisChallenger:
    def test_challenge_returns_enriched_data(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("idor")
        assert isinstance(result, EnrichedVerdictData)

    def test_idor_alternatives(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("idor")
        assert len(result.alternative_explanations) == 4
        labels = [a.label for a in result.alternative_explanations]
        assert "Recurso público" in labels
        assert "Mismo usuario" in labels
        assert "Permiso delegado" in labels
        assert "Respuesta genérica" in labels

    def test_idor_contradiction_tests(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("idor")
        assert len(result.contradiction_tests) == 3
        types = [t.test_type for t in result.contradiction_tests]
        assert "anonymous_access" in types
        assert "nonexistent_resource" in types
        assert "cross_user" in types

    def test_idor_missing_verifications(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("idor")
        assert len(result.missing_verifications) == 4
        assert any("Ownership" in m for m in result.missing_verifications)
        assert any("Recurso público" in m for m in result.missing_verifications)
        assert any("RBAC" in m for m in result.missing_verifications)
        assert any("Recurso inexistente" in m for m in result.missing_verifications)

    def test_auth_bypass_alternatives(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("auth_bypass")
        assert len(result.alternative_explanations) == 4
        labels = [a.label for a in result.alternative_explanations]
        assert "Endpoint público" in labels
        assert "Cache" in labels
        assert "Mock / stub" in labels

    def test_unknown_type_gives_fallback(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("nonexistent_vuln_type")
        assert len(result.alternative_explanations) == 2
        assert "Falso positivo" in result.alternative_explanations[0].label

    def test_next_best_test_is_highest_info_gain(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("idor")
        assert result.next_best_test is not None
        assert result.next_best_test.info_gain in ("muy alta", "alta")

    def test_missing_filtered_by_ownership_signal(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("idor", signals={"ownership_boundary": True})
        missing = result.missing_verifications
        assert not any(m.startswith("Ownership") for m in missing)

    def test_missing_filtered_by_public_signal(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("idor", signals={"public_endpoint": True})
        missing = result.missing_verifications
        assert not any(m.startswith("Recurso público") for m in missing)

    def test_missing_filtered_multiple_signals(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge(
            "idor",
            signals={"ownership_boundary": True, "uuid": True},
        )
        missing = result.missing_verifications
        assert not any(m.startswith("Ownership") for m in missing)
        assert not any(m.startswith("Recurso inexistente") for m in missing)

    def test_uncertainty_level_not_none(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("idor")
        assert result.uncertainty_level in ("baja", "media", "alta")

    def test_ssrf_alternatives(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("ssrf")
        assert len(result.alternative_explanations) == 3
        assert any("URL validation" in a.label for a in result.alternative_explanations)
        assert any("Restricción" in a.label for a in result.alternative_explanations)

    def test_privilege_escalation_alternatives(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("privilege_escalation")
        assert len(result.alternative_explanations) == 2

    def test_data_exposure_alternatives(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("data_exposure")
        assert len(result.alternative_explanations) == 2

    def test_business_logic_alternatives(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("business_logic")
        assert len(result.alternative_explanations) == 2

    def test_graphql_missing_verifications(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("graphql_introspection")
        assert len(result.missing_verifications) == 2

    def test_file_operation_missing_verifications(self):
        challenger = HypothesisChallenger()
        result = challenger.challenge("file_operation")
        assert len(result.missing_verifications) == 2

    def test_one_challenger_reused_multiple_types(self):
        challenger = HypothesisChallenger()
        r1 = challenger.challenge("idor")
        r2 = challenger.challenge("ssrf")
        r3 = challenger.challenge("auth_bypass")
        assert r1.alternative_explanations[0].label != r2.alternative_explanations[0].label
        assert r2.alternative_explanations[0].label != r3.alternative_explanations[0].label
