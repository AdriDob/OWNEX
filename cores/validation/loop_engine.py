import logging
from datetime import UTC, datetime
from typing import Any

from cores.validation.challenger import HypothesisChallenger
from cores.validation.confidence import ConfidenceScorer
from cores.validation.contradiction_runner import (
    INFO_GAIN_ORDER,
    MIN_INFO_GAIN,
    ContradictionResult,
    ContradictionTestRunner,
)
from cores.validation.gate import ReportGate, Verdict
from cores.validation.llm_analyzer import LLMResponseAnalyzer
from cores.validation.replayer import AuthContext, RequestReplayer, RequestSpec
from cores.validation.rules import ValidationRuleSet

logger = logging.getLogger("ownex.validation.loop")

DEFAULT_CONCURRENCY = 5


class ValidationLoopEngine:
    def __init__(
        self,
        replayer: RequestReplayer | None = None,
        rules: ValidationRuleSet | None = None,
        scorer: ConfidenceScorer | None = None,
        gate: ReportGate | None = None,
        llm_analyzer: LLMResponseAnalyzer | None = None,
        challenger: HypothesisChallenger | None = None,
        contradiction_runner: ContradictionTestRunner | None = None,
    ):
        self._replayer = replayer or RequestReplayer()
        self._rules = rules or ValidationRuleSet()
        # Use shared singleton by default so FeedbackTuner weight adjustments propagate
        from cores.validation.confidence import get_confidence_scorer

        self._scorer = scorer or get_confidence_scorer()
        self._gate = gate or ReportGate()
        self._llm = llm_analyzer or LLMResponseAnalyzer()
        self._challenger = challenger or HypothesisChallenger()
        self._contradiction_runner = contradiction_runner or ContradictionTestRunner(self._replayer)

    def evaluate(
        self,
        hot_path_id: str,
        endpoint_details: dict[str, Any],
        endpoint_signals: dict[str, Any],
        auth_baseline: AuthContext,
        auth_probe: AuthContext,
        mutations: dict[str, str] | None = None,
        min_attempts: int = 3,
        vulnerability_type: str = "unknown",
        vulnerability_vector: str = "",
    ) -> Verdict:
        request_spec = RequestSpec(
            url=endpoint_details.get("url", ""),
            method=endpoint_details.get("method", "GET"),
            headers=endpoint_details.get("headers", {}),
            params=endpoint_details.get("params", {}),
            body=endpoint_details.get("body"),
        )

        enriched = self._challenger.challenge(
            vulnerability_type=vulnerability_type,
            vulnerability_vector=vulnerability_vector,
            signals=endpoint_signals,
        )

        comparison_results = self._replayer.revalidate(
            request_spec=request_spec,
            auth_baseline=auth_baseline,
            auth_probe=auth_probe,
            mutations=mutations or {},
            min_attempts=min_attempts,
        )

        validation_report = self._rules.evaluate(comparison_results)

        # ── LLM semantic analysis ────────────────────────────────────
        # The LLM understands SEMANTICS, not just length diffs.
        # It can detect: permission changes, data leaks, different objects,
        # context shifts, and semantic differences the rules miss.
        llm_insight = None
        if comparison_results and self._llm._provider.is_available():
            try:
                last = comparison_results[-1]
                sem = self._llm.semantic_compare(
                    baseline_body=last.baseline.body,
                    probe_body=last.probe.body,
                    endpoint_path=request_spec.url,
                    http_method=request_spec.method,
                    baseline_status=last.baseline.status_code,
                    probe_status=last.probe.status_code,
                )
                if sem.vulnerability_hints:
                    logger.info(
                        "LLM semantic analysis for %s: %s (confidence=%.2f)",
                        request_spec.url,
                        sem.explanation[:100],
                        sem.confidence,
                    )
                llm_insight = sem
            except Exception as e:
                logger.warning("LLM semantic analysis failed: %s", e)

        # Boost confidence when LLM confirms vulnerability pattern
        llm_boost = 0.0
        if llm_insight and not llm_insight.semantically_identical and not llm_insight.same_resource:
            llm_boost = 0.15 if llm_insight.confidence > 0.7 else 0.08

        confidence = self._scorer.calculate(
            results=comparison_results,
            validation=validation_report,
            endpoint_signals=endpoint_signals,
            llm_boost=llm_boost,
            uncertainty_penalty=enriched.uncertainty_penalty,
        )

        consistent_count = sum(1 for r in comparison_results if r.consistent)
        reproducibility_score = consistent_count / max(len(comparison_results), 1)

        if self._gate.admit(
            Verdict(
                hot_path_id=hot_path_id,
                status="confirmed",
                confidence=confidence.score,
                reproducibility_score=reproducibility_score,
                validation=validation_report,
                confidence_details=confidence,
                evidence_links=[],
                reason="",
                retry_count=len(comparison_results),
                timestamp="",
            )
        ):
            passed = validation_report.passed_rules
            status = "confirmed"
            reason = (
                f"Confirmed: {len(passed)} rule(s) passed ({', '.join(passed)}), "
                f"confidence={confidence.score:.2f} ({confidence.level}), "
                f"reproducibility={reproducibility_score:.2f}"
            )
        elif confidence.score >= 0.3:
            status = "inconclusive"
            reason = (
                f"Inconclusive: confidence={confidence.score:.2f} below 0.6 threshold, "
                f"reproducibility={reproducibility_score:.2f}, "
                f"rules passed={validation_report.passed_rules}"
            )
        else:
            status = "rejected"
            reason = (
                f"Rejected: confidence={confidence.score:.2f}, "
                f"reproducibility={reproducibility_score:.2f}, "
                f"rules passed={validation_report.passed_rules}"
            )

        evidence_links = [f"attempt_{r.attempt}" for r in comparison_results if r.consistent]

        contradiction_results: list[dict[str, Any]] = []
        if status == "confirmed":
            contradiction_results = self._run_contradiction_tests(
                vulnerability_type=vulnerability_type,
                request_spec=request_spec,
                auth_probe=auth_probe,
                next_best_test=enriched.next_best_test,
            )
            if any(r["executed"] and r["supports_vulnerability"] is False for r in contradiction_results):
                status = "inconclusive"
                refuted = next(
                    r for r in contradiction_results if r["executed"] and r["supports_vulnerability"] is False
                )
                reason = (
                    f"Refuted by contradiction test '{refuted['test_type']}': {refuted['reasoning']}; "
                    f"confidence={confidence.score:.2f} below 0.6 threshold"
                )

        return Verdict(
            hot_path_id=hot_path_id,
            status=status,
            confidence=confidence.score,
            reproducibility_score=reproducibility_score,
            validation=validation_report,
            confidence_details=confidence,
            evidence_links=evidence_links,
            reason=reason,
            retry_count=len(comparison_results),
            timestamp=datetime.now(UTC).isoformat(),
            alternative_explanations=[a.to_dict() for a in enriched.alternative_explanations],
            missing_verifications=enriched.missing_verifications,
            next_best_test=enriched.next_best_test.to_dict() if enriched.next_best_test else None,
            vulnerability_type=vulnerability_type,
            uncertainty_level=enriched.uncertainty_level,
            contradiction_results=contradiction_results,
        )

    def _run_contradiction_tests(
        self,
        vulnerability_type: str,
        request_spec: RequestSpec,
        auth_probe: AuthContext,
        next_best_test: Any,
    ) -> list[dict[str, Any]]:
        """Execute the highest-info-gain contradiction test (always-on for confirmed findings).

        Runs on EVERY confirmed finding (always-on). Only the highest-info-gain
        test is executed to avoid false refutations from lower-quality tests.
        Outcomes are recorded into the learning loop.
        """
        if not next_best_test:
            return []
        if INFO_GAIN_ORDER.get(next_best_test.info_gain, 0) < INFO_GAIN_ORDER[MIN_INFO_GAIN]:
            return []
        try:
            result: ContradictionResult = self._contradiction_runner.run(
                test=next_best_test,
                request_spec=request_spec,
                auth_probe=auth_probe,
            )
        except Exception as exc:  # never break the validation pipeline
            logger.warning("Contradiction test execution failed: %s", exc)
            return []

        self._record_contradiction(vulnerability_type, request_spec.url, result)
        logger.info(
            "[CONTRADICTION] %s: executed=%s supports=%s observed=%d",
            result.test_type,
            result.executed,
            result.supports_vulnerability,
            result.observed_status,
        )
        return [result.to_dict()]

    @staticmethod
    def _record_contradiction(
        vulnerability_type: str,
        endpoint_url: str,
        result: ContradictionResult,
    ) -> None:
        try:
            from cores.validation.learning import record_contradiction_outcome

            record_contradiction_outcome(
                vulnerability_type=vulnerability_type,
                test_type=result.test_type,
                info_gain=result.info_gain,
                supports_vulnerability=result.supports_vulnerability,
                endpoint_path=endpoint_url,
            )
        except Exception as exc:
            logger.warning("Contradiction learning record failed: %s", exc)

    def evaluate_all(
        self,
        hot_paths: list[dict[str, Any]],
        endpoint_details_map: dict[str, dict[str, Any]],
        endpoint_signals_map: dict[str, dict[str, Any]],
        auth_baseline: AuthContext,
        auth_probe: AuthContext,
        mutations_map: dict[str, dict[str, str]] | None = None,
        min_attempts: int = 3,
    ) -> dict[str, Verdict]:
        verdicts: dict[str, Verdict] = {}
        for hp in hot_paths:
            hp_id = hp.get("id") or hp.get("hot_path_id") or str(id(hp))
            for node_id in hp.get("nodes", []):
                details = endpoint_details_map.get(node_id, {})
                signals = endpoint_signals_map.get(node_id, {})
                mutations = (mutations_map or {}).get(node_id, {})
                verdict = self.evaluate(
                    hot_path_id=f"{hp_id}:{node_id}",
                    endpoint_details=details,
                    endpoint_signals=signals,
                    auth_baseline=auth_baseline,
                    auth_probe=auth_probe,
                    mutations=mutations,
                    min_attempts=min_attempts,
                )
                verdicts[verdict.hot_path_id] = verdict
        return verdicts
