"""ContradictionTestRunner — executes the contradiction tests designed by the HypothesisChallenger.

The Challenger only *designs* tests (test_type, expected outcomes, info_gain).
This runner executes them against the RequestReplayer and interprets the observed
outcome as SUPPORT / CONTRADICT / INCONCLUSIVE for the vulnerability hypothesis,
so the ValidationLoopEngine can refute false positives instead of just listing doubts.
"""

from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass
from typing import Any

from cores.validation.challenger import ContradictionTest
from cores.validation.replayer import AuthContext, RequestReplayer, RequestSpec

logger = logging.getLogger("ownex.validation.contradiction")

MIN_INFO_GAIN = "alta"
INFO_GAIN_ORDER = {"baja": 0, "media": 1, "alta": 2, "muy alta": 3}

_STATUS_CODE_RE = re.compile(r"\b(\d{3})\b")

NONEXISTENT_ID = "00000000-0000-0000-0000-000000000000"

# test_type → (mutation strategy, does a CHANGED response support the vulnerability?)
#   None strategy = requires alternate auth context (skipped when not provided).
_TEST_STRATEGY: dict[str, tuple[str | None, bool | None]] = {
    "anonymous_access": ("anonymous", None),
    "cache_buster": ("cache_buster", True),
    "nonexistent_resource": ("nonexistent_id", None),
    "cross_user": (None, None),
    "lower_role": (None, None),
    "invalid_url": ("invalid_url", None),
    "header_override": ("header_override", False),
    "pagination_depth": ("pagination_depth", None),
    "baseline_confirmation": ("baseline_confirmation", False),
}


@dataclass
class ContradictionResult:
    """Outcome of executing one contradiction test."""

    test_type: str
    info_gain: str
    executed: bool
    supports_vulnerability: bool | None
    observed_status: int
    baseline_status: int
    reasoning: str
    skip_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_type": self.test_type,
            "info_gain": self.info_gain,
            "executed": self.executed,
            "supports_vulnerability": self.supports_vulnerability,
            "observed_status": self.observed_status,
            "baseline_status": self.baseline_status,
            "reasoning": self.reasoning,
            "skip_reason": self.skip_reason,
        }


class ContradictionTestRunner:
    """Executes contradiction tests and interprets outcomes deterministically."""

    def __init__(self, replayer: RequestReplayer | None = None) -> None:
        self._replayer = replayer or RequestReplayer(timeout=10, pacing=0.0)

    def run(
        self,
        test: ContradictionTest,
        request_spec: RequestSpec,
        auth_probe: AuthContext,
        alt_auths: dict[str, AuthContext] | None = None,
    ) -> ContradictionResult:
        strategy, change_supports = _TEST_STRATEGY.get(test.test_type, (None, None))
        if strategy is None:
            if test.test_type in {"cross_user", "lower_role"}:
                return self._skipped(test, "requires_alternate_auth")
            return self._skipped(test, "no_strategy")

        try:
            baseline = self._replayer.execute(request_spec, auth_probe)
            probe = self._execute_strategy(strategy, request_spec, auth_probe)
        except Exception as exc:  # never break the validation pipeline
            logger.warning("[CONTRADICTION] %s failed: %s", test.test_type, exc)
            return ContradictionResult(
                test_type=test.test_type,
                info_gain=test.info_gain,
                executed=False,
                supports_vulnerability=None,
                observed_status=0,
                baseline_status=0,
                reasoning=f"execution_error: {str(exc)[:120]}",
                skip_reason="execution_error",
            )

        supports = self._interpret(test, baseline, probe, change_supports)
        return ContradictionResult(
            test_type=test.test_type,
            info_gain=test.info_gain,
            executed=True,
            supports_vulnerability=supports,
            observed_status=probe.status_code,
            baseline_status=baseline.status_code,
            reasoning=self._reasoning(test, baseline, probe, supports),
        )

    def _execute_strategy(
        self,
        strategy: str,
        request_spec: RequestSpec,
        auth: AuthContext,
    ) -> Any:
        if strategy == "anonymous":
            return self._replayer.execute(request_spec, AuthContext(label="anonymous"))
        if strategy == "cache_buster":
            mutated = RequestSpec(
                url=request_spec.url,
                method=request_spec.method,
                headers=dict(request_spec.headers),
                params=dict(request_spec.params),
                body=request_spec.body,
            )
            mutated.headers["Cache-Control"] = "no-cache"
            mutated.params["_cb"] = f"{random.getrandbits(64):x}"
            return self._replayer.execute(mutated, auth)
        if strategy == "nonexistent_id":
            mutated = RequestSpec(
                url=self._mutate_path_id(request_spec.url),
                method=request_spec.method,
                headers=dict(request_spec.headers),
                params=dict(request_spec.params),
                body=request_spec.body,
            )
            return self._replayer.execute(mutated, auth)
        if strategy == "invalid_url":
            mutated = RequestSpec(
                url=request_spec.url,
                method=request_spec.method,
                headers=dict(request_spec.headers),
                params=self._mutate_url_param(request_spec.params),
                body=request_spec.body,
            )
            return self._replayer.execute(mutated, auth)
        if strategy == "header_override":
            mutated = RequestSpec(
                url=request_spec.url,
                method=request_spec.method,
                headers=dict(request_spec.headers),
                params=dict(request_spec.params),
                body=request_spec.body,
            )
            mutated.headers["X-Forwarded-Role"] = "admin"
            mutated.headers["X-Admin"] = "true"
            return self._replayer.execute(mutated, auth)
        if strategy == "pagination_depth":
            mutated = RequestSpec(
                url=request_spec.url,
                method=request_spec.method,
                headers=dict(request_spec.headers),
                params=dict(request_spec.params),
                body=request_spec.body,
            )
            mutated.params["page"] = "100"
            return self._replayer.execute(mutated, auth)
        # baseline_confirmation: same request twice (consistency check)
        return self._replayer.execute(request_spec, auth)

    @staticmethod
    def _mutate_path_id(url: str) -> str:
        head, sep, _ = url.rpartition("/")
        if sep:
            return head + sep + NONEXISTENT_ID
        return url + "/" + NONEXISTENT_ID

    @staticmethod
    def _mutate_url_param(params: dict[str, str]) -> dict[str, str]:
        mutated = dict(params)
        for key, value in mutated.items():
            if "http://" in value or "https://" in value or "." in value:
                mutated[key] = "http://nonexistent.invalid"
                return mutated
        mutated["url"] = "http://nonexistent.invalid"
        return mutated

    def _interpret(
        self,
        test: ContradictionTest,
        baseline: Any,
        probe: Any,
        change_supports: bool | None,
    ) -> bool | None:
        vuln_codes = _expected_codes(test.expected_if_vulnerable)
        not_codes = _expected_codes(test.expected_if_not)
        if vuln_codes or not_codes:
            if probe.status_code in vuln_codes:
                return True
            if probe.status_code in not_codes:
                return False
            return None  # status outside both expectations → inconclusive

        if change_supports is not None:
            changed = probe.status_code != baseline.status_code or probe.body_hash != baseline.body_hash
            return changed == change_supports
        return None

    @staticmethod
    def _reasoning(test: ContradictionTest, baseline: Any, probe: Any, supports: bool | None) -> str:
        if supports is True:
            return f"observed {probe.status_code} matches expected_if_vulnerable"
        if supports is False:
            return f"observed {probe.status_code} matches expected_if_not"
        return f"observed {probe.status_code} matches neither expectation (inconclusive)"

    @staticmethod
    def _skipped(test: ContradictionTest, reason: str) -> ContradictionResult:
        return ContradictionResult(
            test_type=test.test_type,
            info_gain=test.info_gain,
            executed=False,
            supports_vulnerability=None,
            observed_status=0,
            baseline_status=0,
            reasoning=f"skipped: {reason}",
            skip_reason=reason,
        )


def _expected_codes(expectation: str) -> set[int]:
    return {int(m) for m in _STATUS_CODE_RE.findall(expectation)}
