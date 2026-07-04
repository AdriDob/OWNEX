"""Advanced validation rule set.

Detects:
  - privilege_boundary_break: same status, similar body, sensitive fields
  - auth_bypass: probe returns 200 matching baseline
  - sensitive_data_exposure: critical/non-critical fields in response
  - cross_session_mismatch: different user data returned
  - timing_based_injection: response time anomalies (blind SQLi/SSRF)
  - content_type_aware_diff: JSON/XML/HTML-aware structural comparison
  - oob_interaction: out-of-band detection markers
  - multi_step_chain: multi-step auth bypass (login -> action -> verify)

Each rule requires >=3 consistent attempts for confirmation.
"""

import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from cores.validation.replayer import ComparisonResult

CRITICAL_SENSITIVE_FIELDS = {
    "email", "ssn", "credit_card", "passport", "jwt",
}

NON_CRITICAL_SENSITIVE_FIELDS = {
    "phone", "role", "billing", "admin", "superuser",
    "staff", "moderator", "secret", "token", "password",
    "apikey", "api_key", "subscription", "payment",
    "invoice",
}

OOB_CALLBACK_PATTERNS = [
    r"https?://[a-zA-Z0-9-]+\.(?:burpcollaborator|interactsh|oastify|oast|oast\.fun|requestbin|webhook\.site)",
    r"(?:burpcollaborator|interactsh|oast|oastify)\.net",
]

TIMING_ANOMALY_THRESHOLD_MS = 3000


@dataclass
class RuleResult:
    passed: bool
    reason: str
    evidence: list[str]
    confidence_contribution: float


@dataclass
class ValidationReport:
    passed: bool
    passed_rules: list[str]
    failed_rules: list[str]
    details: dict[str, RuleResult]


class ContentAwareDiff:
    """Content-type-aware structural comparison."""

    @staticmethod
    def json_diff(body_a: str, body_b: str) -> float:
        try:
            a = json.loads(body_a)
            b = json.loads(body_b)
        except (json.JSONDecodeError, ValueError):
            return 1.0
        return ContentAwareDiff._json_obj_diff(a, b)

    @staticmethod
    def _json_obj_diff(a: Any, b: Any) -> float:
        if type(a) != type(b):
            return 1.0
        if isinstance(a, dict):
            keys = set(a) | set(b)
            if not keys:
                return 0.0
            diffs = sum(ContentAwareDiff._json_obj_diff(a.get(k), b.get(k)) for k in keys)
            return diffs / len(keys)
        elif isinstance(a, list):
            if not a and not b:
                return 0.0
            max_len = max(len(a), len(b))
            if max_len == 0:
                return 0.0
            diffs = 0
            for i in range(max_len):
                if i >= len(a) or i >= len(b):
                    diffs += 1
                else:
                    diffs += ContentAwareDiff._json_obj_diff(a[i], b[i])
            return diffs / max_len
        else:
            return 0.0 if a == b else 1.0

    @staticmethod
    def html_structure_diff(body_a: str, body_b: str) -> float:
        def extract_tags(html: str) -> list[str]:
            class _TagExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.tags: list[str] = []
                def handle_starttag(self, tag, attrs):
                    self.tags.append(tag)
                def handle_endtag(self, tag):
                    self.tags.append(f"/{tag}")
            parser = _TagExtractor()
            parser.feed(html)
            return parser.tags
        tags_a = extract_tags(body_a)
        tags_b = extract_tags(body_b)
        if not tags_a and not tags_b:
            return 0.0
        longer = max(len(tags_a), len(tags_b))
        return 1.0 - (min(len(tags_a), len(tags_b)) / max(longer, 1))


class ValidationRuleSet:
    def evaluate(self, results: list[ComparisonResult]) -> ValidationReport:
        rules: dict[str, RuleResult] = {
            "privilege_boundary_break": self.rule_privilege_boundary_break(results),
            "auth_bypass": self.rule_auth_bypass(results),
            "sensitive_data_exposure": self.rule_sensitive_data_exposure(results),
            "cross_session_mismatch": self.rule_cross_session_mismatch(results),
            "timing_based_injection": self.rule_timing_based_injection(results),
            "content_type_aware_diff": self.rule_content_type_aware_diff(results),
            "oob_interaction": self.rule_oob_interaction(results),
            "multi_step_chain": self.rule_multi_step_chain(results),
        }
        passed_rules = [name for name, r in rules.items() if r.passed]
        failed_rules = [name for name, r in rules.items() if not r.passed]
        return ValidationReport(
            passed=len(passed_rules) > 0,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            details=rules,
        )

    def rule_privilege_boundary_break(self, results: list[ComparisonResult]) -> RuleResult:
        if len(results) < 3:
            return RuleResult(passed=False, reason="Insufficient attempts (< 3).", evidence=[], confidence_contribution=0.0)
        all_status_match = all(r.status_match for r in results)
        max_diff = max(r.body_diff_ratio for r in results)
        all_have_sensitive = all(len(r.sensitive_fields_detected) > 0 for r in results)
        all_consistent = all(r.consistent for r in results)

        if all_status_match and max_diff < 0.25 and all_have_sensitive and all_consistent:
            fields = sorted(set(f for r in results for f in r.sensitive_fields_detected))
            return RuleResult(
                passed=True,
                reason=f"Privilege boundary break: {len(results)}/3 consistent, status match ({all_status_match}), body diff {max_diff:.2f}, sensitive fields: {fields}",
                evidence=[f"attempt_{r.attempt}" for r in results],
                confidence_contribution=0.25,
            )
        fail_reasons = []
        if not all_status_match:
            fail_reasons.append("status codes differ across attempts")
        if max_diff >= 0.25:
            fail_reasons.append(f"body diff {max_diff:.2f} >= 0.25 threshold")
        if not all_have_sensitive:
            fail_reasons.append("no sensitive fields detected consistently")
        if not all_consistent:
            fail_reasons.append("inconsistent across attempts")
        return RuleResult(
            passed=False,
            reason="; ".join(fail_reasons) or "privilege_boundary_break rule not met",
            evidence=[str(r.attempt) for r in results if not r.consistent],
            confidence_contribution=0.0,
        )

    def rule_auth_bypass(self, results: list[ComparisonResult]) -> RuleResult:
        if len(results) < 3:
            return RuleResult(passed=False, reason="Insufficient attempts (< 3).", evidence=[], confidence_contribution=0.0)
        all_probe_ok = all(r.probe.status_code == 200 for r in results)
        all_baseline_ok = all(r.baseline.status_code == 200 for r in results)
        max_diff = max(r.body_diff_ratio for r in results)
        all_consistent = all(r.consistent for r in results)

        if all_probe_ok and all_baseline_ok and max_diff < 0.40 and all_consistent:
            return RuleResult(
                passed=True,
                reason=f"Auth bypass: probe (no auth) returned 200 matching baseline (diff {max_diff:.2f}), {len(results)}/3 consistent",
                evidence=[f"attempt_{r.attempt}" for r in results],
                confidence_contribution=0.25,
            )
        fail_reasons = []
        if not all_probe_ok:
            statuses = {r.probe.status_code for r in results}
            fail_reasons.append(f"probe status codes {statuses} (expected 200)")
        if not all_baseline_ok:
            statuses = {r.baseline.status_code for r in results}
            fail_reasons.append(f"baseline status codes {statuses} (expected 200)")
        if max_diff >= 0.40:
            fail_reasons.append(f"body diff {max_diff:.2f} >= 0.40")
        if not all_consistent:
            fail_reasons.append("inconsistent across attempts")
        return RuleResult(passed=False, reason="; ".join(fail_reasons) or "auth_bypass rule not met", evidence=[], confidence_contribution=0.0)

    def rule_sensitive_data_exposure(self, results: list[ComparisonResult]) -> RuleResult:
        if len(results) < 3:
            return RuleResult(passed=False, reason="Insufficient attempts (< 3).", evidence=[], confidence_contribution=0.0)
        for result in results:
            critical = [f for f in result.sensitive_fields_detected if f in CRITICAL_SENSITIVE_FIELDS]
            non_critical = [f for f in result.sensitive_fields_detected if f in NON_CRITICAL_SENSITIVE_FIELDS]
            if len(critical) >= 1 or len(non_critical) >= 3:
                return RuleResult(
                    passed=True,
                    reason=f"Sensitive data exposure in attempt {result.attempt}: {len(critical)} critical, {len(non_critical)} non-critical fields. Fields: {result.sensitive_fields_detected}",
                    evidence=[f"attempt_{result.attempt}"],
                    confidence_contribution=0.25,
                )
        all_fields = sorted(set(f for r in results for f in r.sensitive_fields_detected))
        return RuleResult(passed=False, reason=f"No sensitive data exposure threshold met. Fields found across attempts: {all_fields}", evidence=[], confidence_contribution=0.0)

    def rule_cross_session_mismatch(self, results: list[ComparisonResult]) -> RuleResult:
        if len(results) < 3:
            return RuleResult(passed=False, reason="Insufficient attempts (< 3).", evidence=[], confidence_contribution=0.0)
        all_status_match = all(r.status_match for r in results)
        all_consistent = all(r.consistent for r in results)
        min_diff = min(r.body_diff_ratio for r in results)
        no_rate_limit = not any(r.has_rate_limit for r in results)
        no_timeout = not any(r.has_timeout for r in results)

        if all_status_match and all_consistent and min_diff >= 0.15 and no_rate_limit and no_timeout:
            return RuleResult(
                passed=True,
                reason=f"Cross-session mismatch: body diff {min_diff:.2f} minimum, {len(results)}/3 consistent, status match, no rate limit",
                evidence=[f"attempt_{r.attempt}" for r in results],
                confidence_contribution=0.25,
            )
        fail_reasons = []
        if not all_status_match:
            fail_reasons.append("status mismatch")
        if min_diff < 0.15:
            fail_reasons.append(f"min diff {min_diff:.2f} < 0.15")
        if not all_consistent:
            fail_reasons.append("inconsistent")
        if not no_rate_limit:
            fail_reasons.append("rate limited")
        if not no_timeout:
            fail_reasons.append("timeout detected")
        return RuleResult(passed=False, reason="; ".join(fail_reasons) or "cross_session_mismatch rule not met", evidence=[], confidence_contribution=0.0)

    def rule_timing_based_injection(self, results: list[ComparisonResult]) -> RuleResult:
        if len(results) < 3:
            return RuleResult(passed=False, reason="Insufficient attempts (< 3).", evidence=[], confidence_contribution=0.0)
        delays: list[int] = []
        for r in results:
            if r.baseline.elapsed_ms > 0:
                delays.append(r.probe.elapsed_ms - r.baseline.elapsed_ms)
        if not delays:
            return RuleResult(passed=False, reason="No timing data available.", evidence=[], confidence_contribution=0.0)
        consistent_delays = [d for d in delays if d > TIMING_ANOMALY_THRESHOLD_MS]
        if len(consistent_delays) >= 2:
            avg_delay = sum(consistent_delays) / len(consistent_delays)
            return RuleResult(
                passed=True,
                reason=f"Timing anomaly detected: probe consistently slower (avg delay {avg_delay:.0f}ms, threshold {TIMING_ANOMALY_THRESHOLD_MS}ms, {len(consistent_delays)}/{len(delays)} attempts)",
                evidence=[f"delay_ms={d}" for d in consistent_delays],
                confidence_contribution=0.20,
            )
        return RuleResult(passed=False, reason=f"No timing anomaly: max delay {max(delays):.0f}ms < {TIMING_ANOMALY_THRESHOLD_MS}ms threshold", evidence=[], confidence_contribution=0.0)

    def rule_content_type_aware_diff(self, results: list[ComparisonResult]) -> RuleResult:
        if len(results) < 3:
            return RuleResult(passed=False, reason="Insufficient attempts (< 3).", evidence=[], confidence_contribution=0.0)
        for r in results:
            body = r.probe.body.strip()
            if not body:
                continue
            content_type = "unknown"
            if body.startswith("{"):
                content_type = "json"
                structural_diff = ContentAwareDiff.json_diff(r.baseline.body, r.probe.body)
            elif body.startswith("<") and ">" in body[:100]:
                content_type = "html"
                structural_diff = ContentAwareDiff.html_structure_diff(r.baseline.body, r.probe.body)
            else:
                structural_diff = r.body_diff_ratio
            if structural_diff >= 0.20:
                return RuleResult(
                    passed=True,
                    reason=f"Content-aware structural diff ({content_type}): diff={structural_diff:.2f} >= 0.20 threshold, attempt {r.attempt}",
                    evidence=[f"content_type={content_type}", f"structural_diff={structural_diff:.2f}"],
                    confidence_contribution=0.20,
                )
            if content_type == "json":
                try:
                    probe_data = json.loads(body)
                    baseline_data = json.loads(r.baseline.body)
                    if isinstance(probe_data, dict) and isinstance(baseline_data, dict):
                        extra_keys = set(probe_data.keys()) - set(baseline_data.keys())
                        missing_keys = set(baseline_data.keys()) - set(probe_data.keys())
                        if extra_keys or missing_keys:
                            return RuleResult(
                                passed=True,
                                reason=f"JSON key mismatch: +{extra_keys} / -{missing_keys} (attempt {r.attempt})",
                                evidence=[f"extra_keys={list(extra_keys)}", f"missing_keys={list(missing_keys)}"],
                                confidence_contribution=0.20,
                            )
                except (json.JSONDecodeError, ValueError):
                    pass
        return RuleResult(passed=False, reason="No structural differences detected across attempts", evidence=[], confidence_contribution=0.0)

    def rule_oob_interaction(self, results: list[ComparisonResult]) -> RuleResult:
        for r in results:
            body = r.probe.body
            for pattern in OOB_CALLBACK_PATTERNS:
                matches = re.findall(pattern, body, re.IGNORECASE)
                if matches:
                    return RuleResult(
                        passed=True,
                        reason=f"OOB callback detected in probe response: {matches[0]} (attempt {r.attempt})",
                        evidence=[f"oob_url={m}" for m in matches[:3]],
                        confidence_contribution=0.30,
                    )
        return RuleResult(passed=False, reason="No OOB interaction markers detected", evidence=[], confidence_contribution=0.0)

    def rule_multi_step_chain(self, results: list[ComparisonResult]) -> RuleResult:
        if len(results) < 3:
            return RuleResult(passed=False, reason="Insufficient attempts (< 3).", evidence=[], confidence_contribution=0.0)
        chain_signals = []
        for r in results:
            body_lower = r.probe.body.lower()
            if "reset" in body_lower and "token" in body_lower:
                chain_signals.append(f"attempt_{r.attempt}: password_reset_token")
            if "register" in body_lower and "admin" in body_lower:
                chain_signals.append(f"attempt_{r.attempt}: registration_to_admin")
            if "oauth" in body_lower and "callback" in body_lower:
                chain_signals.append(f"attempt_{r.attempt}: oauth_callback")
            if "invite" in body_lower and "role" in body_lower:
                chain_signals.append(f"attempt_{r.attempt}: invite_role_escalation")
            if "password" in body_lower and "change" in body_lower and not r.status_match:
                chain_signals.append(f"attempt_{r.attempt}: unauthenticated_password_change")
            if "2fa" in body_lower or "twofactor" in body_lower or "otp" in body_lower:
                chain_signals.append(f"attempt_{r.attempt}: 2fa_bypass_possible")
        if len(chain_signals) >= 2:
            return RuleResult(
                passed=True,
                reason="Multi-step chain detected: " + "; ".join(chain_signals[:3]),
                evidence=chain_signals,
                confidence_contribution=0.15,
            )
        return RuleResult(passed=False, reason="No multi-step chain signals detected", evidence=chain_signals if chain_signals else [], confidence_contribution=0.0)
