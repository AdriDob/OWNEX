"""Tests for the ContradictionTestRunner (SELF-5).

Coverage:
  - strategy mapping + execution per test_type (anonymous, cache_buster,
    nonexistent_id, invalid_url, header_override, pagination_depth,
    baseline_confirmation)
  - interpretation: status-code expectations, change-based expectations,
    inconclusive when neither expectation matches
  - alt-auth tests (cross_user, lower_role) skip when no alternate auth
  - unknown test_type skips; runner never raises on replayer errors
  - loop engine integration: refutation downgrades confirmed -> inconclusive
  - learning record persists contradiction outcomes (separate JSONL)
"""

from __future__ import annotations

from cores.validation.challenger import ContradictionTest, EnrichedVerdictData, HypothesisChallenger
from cores.validation.contradiction_runner import ContradictionResult, ContradictionTestRunner
from cores.validation.replayer import AuthContext, ComparisonResult, RequestSpec, ResponseRecord


class FakeReplayer:
    """Deterministic replayer: canned baseline/probe responses."""

    def __init__(self, baseline_status=200, probe_status=200, probe_body="ok", baseline_body="ok"):
        self._baseline_status = baseline_status
        self._probe_status = probe_status
        self._baseline_body = baseline_body
        self._probe_body = probe_body
        self.calls: list[tuple[RequestSpec, AuthContext]] = []

    def execute(self, request_spec, auth):
        self.calls.append((request_spec, auth))
        if len(self.calls) == 1:
            return ResponseRecord(
                status_code=self._baseline_status,
                headers={},
                body=self._baseline_body,
                body_hash=f"h{self._baseline_body}",
                elapsed_ms=1,
            )
        return ResponseRecord(
            status_code=self._probe_status,
            headers={},
            body=self._probe_body,
            body_hash=f"h{self._probe_body}",
            elapsed_ms=1,
        )


def _spec(url="https://api.example.com/users/1", method="GET", params=None, headers=None) -> RequestSpec:
    return RequestSpec(url=url, method=method, params=params or {}, headers=headers or {})


def _auth(label="probe") -> AuthContext:
    return AuthContext(token="tok", label=label)


def _test(test_type, info_gain="muy alta", if_vuln="401/403", if_not="200") -> ContradictionTest:
    return ContradictionTest(
        test_type=test_type,
        description="d",
        expected_if_vulnerable=if_vuln,
        expected_if_not=if_not,
        info_gain=info_gain,
    )


class TestStrategyMapping:
    def test_anonymous_access_uses_anonymous_auth(self) -> None:
        replayer = FakeReplayer()
        runner = ContradictionTestRunner(replayer=replayer)  # type: ignore[arg-type]
        runner.run(_test("anonymous_access"), _spec(), _auth())
        assert replayer.calls[0][1].label == "probe"
        assert replayer.calls[1][1].label == "anonymous"

    def test_cache_buster_adds_header_and_param(self) -> None:
        replayer = FakeReplayer()
        runner = ContradictionTestRunner(replayer=replayer)  # type: ignore[arg-type]
        runner.run(_test("cache_buster", if_vuln="respuesta diferente", if_not="misma"), _spec(), _auth())
        probe_spec = replayer.calls[1][0]
        assert probe_spec.headers.get("Cache-Control") == "no-cache"
        assert any(k.startswith("_cb") for k in probe_spec.params)

    def test_nonexistent_resource_replaces_path_id(self) -> None:
        replayer = FakeReplayer()
        runner = ContradictionTestRunner(replayer=replayer)  # type: ignore[arg-type]
        runner.run(_test("nonexistent_resource", if_vuln="404", if_not="200"), _spec(), _auth())
        assert replayer.calls[1][0].url == "https://api.example.com/users/00000000-0000-0000-0000-000000000000"

    def test_invalid_url_mutates_url_param(self) -> None:
        replayer = FakeReplayer()
        runner = ContradictionTestRunner(replayer=replayer)  # type: ignore[arg-type]
        runner.run(
            _test("invalid_url", if_vuln="400", if_not="200"),
            _spec(params={"callback": "https://x.example"}),
            _auth(),
        )
        assert replayer.calls[1][0].params["callback"] == "http://nonexistent.invalid"

    def test_header_override_adds_privilege_headers(self) -> None:
        replayer = FakeReplayer()
        runner = ContradictionTestRunner(replayer=replayer)  # type: ignore[arg-type]
        runner.run(_test("header_override", if_vuln="sin efecto", if_not="200"), _spec(), _auth())
        probe_headers = replayer.calls[1][0].headers
        assert probe_headers.get("X-Forwarded-Role") == "admin"
        assert probe_headers.get("X-Admin") == "true"

    def test_pagination_depth_sets_page_param(self) -> None:
        replayer = FakeReplayer()
        runner = ContradictionTestRunner(replayer=replayer)  # type: ignore[arg-type]
        runner.run(_test("pagination_depth", if_vuln="error", if_not="200"), _spec(), _auth())
        assert replayer.calls[1][0].params.get("page") == "100"

    def test_baseline_confirmation_repeats_same_request(self) -> None:
        replayer = FakeReplayer()
        runner = ContradictionTestRunner(replayer=replayer)  # type: ignore[arg-type]
        runner.run(_test("baseline_confirmation", if_vuln="misma respuesta", if_not="diferente"), _spec(), _auth())
        assert replayer.calls[0][0] == replayer.calls[1][0]


class TestInterpretation:
    def test_status_matches_vulnerable_expectation_supports(self) -> None:
        replayer = FakeReplayer(probe_status=401)
        runner = ContradictionTestRunner(replayer=replayer)  # type: ignore[arg-type]
        result = runner.run(_test("anonymous_access"), _spec(), _auth())
        assert result.executed is True
        assert result.supports_vulnerability is True
        assert result.observed_status == 401
        assert result.baseline_status == 200

    def test_status_matches_not_vulnerable_expectation_contradicts(self) -> None:
        replayer = FakeReplayer(probe_status=200)
        runner = ContradictionTestRunner(replayer=replayer)  # type: ignore[arg-type]
        result = runner.run(_test("anonymous_access"), _spec(), _auth())
        assert result.supports_vulnerability is False

    def test_status_matches_neither_is_inconclusive(self) -> None:
        replayer = FakeReplayer(probe_status=500)
        runner = ContradictionTestRunner(replayer=replayer)  # type: ignore[arg-type]
        result = runner.run(_test("anonymous_access"), _spec(), _auth())
        assert result.supports_vulnerability is None

    def test_change_based_expectation_cache_buster_same_response_refutes(self) -> None:
        replayer = FakeReplayer(probe_status=200, probe_body="ok", baseline_body="ok")
        runner = ContradictionTestRunner(replayer=replayer)  # type: ignore[arg-type]
        result = runner.run(_test("cache_buster", if_vuln="respuesta diferente", if_not="misma"), _spec(), _auth())
        assert result.supports_vulnerability is False

    def test_change_based_expectation_cache_buster_differs_supports(self) -> None:
        replayer = FakeReplayer(probe_status=200, probe_body="different", baseline_body="ok")
        runner = ContradictionTestRunner(replayer=replayer)  # type: ignore[arg-type]
        result = runner.run(_test("cache_buster", if_vuln="respuesta diferente", if_not="misma"), _spec(), _auth())
        assert result.supports_vulnerability is True

    def test_change_based_expectation_baseline_confirmation_same_supports(self) -> None:
        replayer = FakeReplayer(probe_status=200, probe_body="ok", baseline_body="ok")
        runner = ContradictionTestRunner(replayer=replayer)  # type: ignore[arg-type]
        result = runner.run(
            _test("baseline_confirmation", if_vuln="misma respuesta", if_not="diferente"), _spec(), _auth()
        )
        assert result.supports_vulnerability is True

    def test_to_dict_shape(self) -> None:
        result = ContradictionResult(
            test_type="anonymous_access",
            info_gain="muy alta",
            executed=True,
            supports_vulnerability=True,
            observed_status=401,
            baseline_status=200,
            reasoning="observed 401 matches expected_if_vulnerable",
        )
        d = result.to_dict()
        assert d["test_type"] == "anonymous_access"
        assert d["supports_vulnerability"] is True
        assert d["executed"] is True


class TestSkipAndSafety:
    def test_cross_user_skips_without_alt_auth(self) -> None:
        runner = ContradictionTestRunner(replayer=FakeReplayer())  # type: ignore[arg-type]
        result = runner.run(_test("cross_user"), _spec(), _auth())
        assert result.executed is False
        assert result.skip_reason == "requires_alternate_auth"

    def test_lower_role_skips_without_alt_auth(self) -> None:
        runner = ContradictionTestRunner(replayer=FakeReplayer())  # type: ignore[arg-type]
        result = runner.run(_test("lower_role"), _spec(), _auth())
        assert result.executed is False
        assert result.skip_reason == "requires_alternate_auth"

    def test_unknown_test_type_skips(self) -> None:
        runner = ContradictionTestRunner(replayer=FakeReplayer())  # type: ignore[arg-type]
        result = runner.run(_test("mystery"), _spec(), _auth())
        assert result.executed is False
        assert result.skip_reason == "no_strategy"

    def test_runner_never_raises_on_replayer_error(self) -> None:
        class ExplodingReplayer:
            def execute(self, request_spec, auth):  # noqa: ARG002
                raise RuntimeError("boom")

        runner = ContradictionTestRunner(replayer=ExplodingReplayer())  # type: ignore[arg-type]
        result = runner.run(_test("anonymous_access"), _spec(), _auth())
        assert result.executed is False
        assert result.skip_reason == "execution_error"


class TestLoopEngineIntegration:
    """The loop executes the next_best_test on confirmation and downgrades on refutation."""

    def _engine(self, supports_result: bool | None, tmp_path, monkeypatch):
        from cores.validation.confidence import ConfidenceScore, ConfidenceScorer
        from cores.validation.gate import ReportGate
        from cores.validation.loop_engine import ValidationLoopEngine
        from cores.validation.rules import ValidationRuleSet

        monkeypatch.setattr("cores.validation.gate.STATE_FILE", tmp_path / "gate_state.json")
        monkeypatch.setattr("cores.validation.learning.CONTRADICTION_FILE", tmp_path / "contradictions.jsonl")
        monkeypatch.setattr("cores.validation.learning.LEARNING_DIR", tmp_path)

        class HighScorer(ConfidenceScorer):
            def calculate(self, results, validation, endpoint_signals, llm_boost=0.0, uncertainty_penalty=0.0):
                return ConfidenceScore(score=0.95, breakdown={}, level="high")

        class FakeReplayer:
            def revalidate(self, request_spec, auth_baseline, auth_probe, mutations=None, min_attempts=3):
                rec = ResponseRecord(status_code=200, headers={}, body="same", body_hash="h", elapsed_ms=1)
                return [
                    ComparisonResult(
                        attempt=1,
                        baseline=rec,
                        probe=rec,
                        status_match=True,
                        body_diff_ratio=0.0,
                        headers_diff={},
                        sensitive_fields_detected=[],
                        has_rate_limit=False,
                        has_timeout=False,
                        consistent=True,
                        timestamp="t",
                    )
                ]

        class FakeChallenger(HypothesisChallenger):
            def challenge(self, vulnerability_type, vulnerability_vector="", signals=None):
                return EnrichedVerdictData(
                    alternative_explanations=[],
                    contradiction_tests=[_test("anonymous_access")],
                    missing_verifications=[],
                    next_best_test=_test("anonymous_access"),
                    uncertainty_level="baja",
                )

        class FakeRunner(ContradictionTestRunner):
            def run(self, test, request_spec, auth_probe, alt_auths=None):
                return ContradictionResult(
                    test_type=test.test_type,
                    info_gain=test.info_gain,
                    executed=True,
                    supports_vulnerability=supports_result,
                    observed_status=401,
                    baseline_status=200,
                    reasoning="observed 401 matches expected_if_vulnerable",
                )

        gate = ReportGate()
        gate._thresholds = {"idor": 0.5}
        return ValidationLoopEngine(
            replayer=FakeReplayer(),  # type: ignore[arg-type]
            rules=ValidationRuleSet(),
            scorer=HighScorer(),
            gate=gate,
            challenger=FakeChallenger(),
            contradiction_runner=FakeRunner(),
        )

    def _evaluate(self, engine):
        return engine.evaluate(
            hot_path_id="hp:n1",
            endpoint_details={"url": "https://api.example.com/users/1", "method": "GET"},
            endpoint_signals={"risk_score": 50},
            auth_baseline=AuthContext(token="a", label="identity_1"),
            auth_probe=AuthContext(token="b", label="identity_2"),
            mutations={},
            min_attempts=3,
            vulnerability_type="idor",
        )

    def test_refutation_downgrades_confirmed_to_inconclusive(self, tmp_path, monkeypatch) -> None:
        verdict = self._evaluate(self._engine(False, tmp_path, monkeypatch))
        assert verdict.status == "inconclusive"
        assert "Refuted by contradiction test" in verdict.reason
        assert len(verdict.contradiction_results) == 1
        assert verdict.contradiction_results[0]["supports_vulnerability"] is False

    def test_support_keeps_confirmed(self, tmp_path, monkeypatch) -> None:
        verdict = self._evaluate(self._engine(True, tmp_path, monkeypatch))
        assert verdict.status == "confirmed"
        assert len(verdict.contradiction_results) == 1
        assert verdict.contradiction_results[0]["supports_vulnerability"] is True

    def test_learning_record_persisted_on_refutation(self, tmp_path, monkeypatch) -> None:
        from cores.validation.learning import get_contradiction_stats

        self._evaluate(self._engine(False, tmp_path, monkeypatch))
        stats = get_contradiction_stats()
        assert stats["total"] == 1
        assert stats["refuted"] == 1
        assert stats["by_test_type"]["anonymous_access"]["total"] == 1

    def test_low_info_gain_test_not_executed(self, tmp_path, monkeypatch) -> None:
        from cores.validation.challenger import ContradictionTest

        class LowGainChallenger(HypothesisChallenger):
            def challenge(self, vulnerability_type, vulnerability_vector="", signals=None):
                return EnrichedVerdictData(
                    alternative_explanations=[],
                    contradiction_tests=[],
                    missing_verifications=[],
                    next_best_test=ContradictionTest(
                        test_type="pagination_depth",
                        description="d",
                        expected_if_vulnerable="error",
                        expected_if_not="200",
                        info_gain="media",
                    ),
                    uncertainty_level="baja",
                )

        engine = self._engine(False, tmp_path, monkeypatch)
        engine._challenger = LowGainChallenger()
        verdict = self._evaluate(engine)
        assert verdict.status == "confirmed"  # not challenged -> stays confirmed
        assert verdict.contradiction_results == []
