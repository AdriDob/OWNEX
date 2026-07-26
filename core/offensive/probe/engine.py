"""HTTP Probe Engine — confirms or rejects hypotheses with real HTTP requests.

Pipeline:
   1. Build baseline request (normal parameters)
   2. Send baseline → capture response
   3. Build test request (malicious payload from hypothesis)
   4. Send test → capture response
   5. Compare responses → detect vulnerability
   6. Return ProbeResult with evidence

Usage::

    engine = ProbeEngine()
    result = engine.probe(hypothesis, host="https://api.target.com")
    if result.confirmed:
        logger.info("Confirmed %s via %s", result.vulnerability_type, result.detection_method)
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from core.offensive.attack.models import AttackStep, TestPlan
from core.offensive.models import Hypothesis
from core.offensive.probe.models import ProbeEvidence, ProbeRequest, ProbeResponse, ProbeResult

logger = logging.getLogger("orion.core.offensive.probe")

_TIMEOUT = 15.0
_MAX_BODY_SAMPLE = 5000
_USER_AGENT = "ORION-Probe/1.0"


class ProbeEngine:
    """Sends real HTTP requests to confirm or reject hypotheses."""

    def probe(
        self,
        hypothesis: Hypothesis,
        host: str = "",
        auth_headers: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
        baseline_params: dict[str, str] | None = None,
        test_value_override: str = "",
        verify_request: bool = True,
    ) -> ProbeResult:
        """Probe an endpoint to confirm or reject the hypothesis.

        Args:
            hypothesis: The hypothesis to test.
            host: Base URL (e.g. https://api.target.com). Falls back to hypothesis.endpoint.
            auth_headers: Auth headers needed to reach the endpoint.
            extra_headers: Additional headers for all requests.
            baseline_params: Override params for the baseline request.
            test_value_override: Override the test value for the vulnerability.
            verify_request: Send a third verification request if confirmed.

        Returns:
            ProbeResult with evidence and confirmation status.
        """
        started_at = datetime.now(timezone.utc).isoformat()
        result = ProbeResult(
            hypothesis_id=hypothesis.id,
            vulnerability_type=hypothesis.vulnerability_type,
            endpoint=hypothesis.endpoint,
            method=hypothesis.method.upper(),
            started_at=started_at,
        )

        try:
            test_value = test_value_override or _test_value_for(hypothesis.vulnerability_type)
            base_url = host or _extract_host(hypothesis.endpoint)
            vuln_param = hypothesis.parameters_of_interest[0] if hypothesis.parameters_of_interest else ""

            if not vuln_param:
                result.error = "No parameters of interest to test"
                result.completed_at = datetime.now(timezone.utc).isoformat()
                return result

            method = hypothesis.method.upper()
            all_headers = dict(extra_headers or {})
            if auth_headers:
                all_headers.update(auth_headers)
            all_headers.setdefault("User-Agent", _USER_AGENT)

            # Build test params: replace the vulnerable param with test value
            test_params = dict(baseline_params or {})
            for p in hypothesis.parameters_of_interest:
                test_params[p] = test_value

            # Build baseline params (normal values)
            bl_params = dict(baseline_params or {})
            for p in hypothesis.parameters_of_interest:
                if p not in bl_params:
                    bl_params[p] = _baseline_value_for(p)

            with httpx.Client(timeout=_TIMEOUT, verify=False) as client:
                # Step 1: Baseline request
                bl_evidence = self._send_request(
                    client=client,
                    label="baseline",
                    method=method,
                    url=base_url,
                    params=bl_params,
                    headers=all_headers,
                    body=hypothesis.relationship_context.collection_endpoint or None,
                )
                result.evidence.append(bl_evidence)

                # Step 2: Test request with malicious payload
                test_evidence = self._send_request(
                    client=client,
                    label="test",
                    method=method,
                    url=base_url,
                    params=test_params,
                    headers=all_headers,
                    body=hypothesis.relationship_context.collection_endpoint or None,
                )
                result.evidence.append(test_evidence)

                # Step 3: Analyze for vulnerability
                detection = _detect_vulnerability(
                    hypothesis.vulnerability_type,
                    bl_evidence.response,
                    test_evidence.response,
                    vuln_param,
                    test_value,
                    bl_params.get(vuln_param, ""),
                )

                result.confirmed = detection["confirmed"]
                result.confidence = detection["confidence"]
                result.detection_method = detection["method"]
                result.detection_details = detection["details"]
                result.false_positive_risk = detection["false_positive_risk"]
                result.alternative_explanations = detection["alternative_explanations"]
                result.test_value = test_value
                result.vulnerable_param = vuln_param
                result.test_request = test_evidence.request
                result.baseline_response = bl_evidence.response
                result.test_response = test_evidence.response

                # Step 4: Verification request if confirmed
                if result.confirmed and verify_request:
                    verify_evidence = self._send_request(
                        client=client,
                        label="verify",
                        method=method,
                        url=base_url,
                        params=bl_params,
                        headers=all_headers,
                    )
                    result.evidence.append(verify_evidence)

        except Exception as exc:
            logger.warning("[PROBE] Error probing %s: %s", hypothesis.endpoint, exc)
            result.error = str(exc)[:200]

        result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    def probe_raw(
        self,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        body: Any = None,
    ) -> ProbeResponse:
        """Send a single HTTP request and return the response.

        Useful for manual testing or verification.
        """
        all_headers = dict(headers or {})
        all_headers.setdefault("User-Agent", _USER_AGENT)

        try:
            with httpx.Client(timeout=_TIMEOUT, verify=False) as client:
                start = time.monotonic()
                response = client.request(
                    method=method,
                    url=url,
                    headers=all_headers,
                    params=params,
                    content=json.dumps(body) if isinstance(body, dict) else body,
                )
                elapsed = (time.monotonic() - start) * 1000
                body_text = response.text[:_MAX_BODY_SAMPLE]
                return ProbeResponse(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    body=body_text,
                    body_size=len(response.content),
                    elapsed_ms=round(elapsed, 1),
                )
        except Exception as exc:
            return ProbeResponse(
                status_code=0,
                body=str(exc),
                body_size=0,
            )

    def execute_plan(
        self,
        plan: TestPlan,
        auth_headers: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> ProbeResult:
        """Execute a TestPlan and return the consolidated result.

        Sends baseline, then iterates over all attack steps with multiple payloads,
        compares responses, and scores confidence.
        """
        started_at = datetime.now(timezone.utc).isoformat()
        base_url = plan.target
        result = ProbeResult(
            hypothesis_id=plan.hypothesis_id,
            vulnerability_type=plan.vulnerability_type,
            endpoint=plan.endpoint_path,
            method=plan.steps[0].method if plan.steps else "GET",
            started_at=started_at,
        )

        if not plan.steps:
            result.error = "No attack steps in plan"
            result.completed_at = datetime.now(timezone.utc).isoformat()
            return result

        all_headers = dict(extra_headers or {})
        if auth_headers:
            all_headers.update(auth_headers)
        all_headers.setdefault("User-Agent", _USER_AGENT)

        all_responses: list[tuple[AttackStep, ProbeResponse]] = []

        with httpx.Client(timeout=_TIMEOUT, verify=False) as client:
            for step in plan.steps:
                probe_req = step.to_request(base_url)
                ev = self._send_request(
                    client=client,
                    label=step.purpose,
                    method=probe_req.method,
                    url=probe_req.url,
                    params=probe_req.params,
                    headers=all_headers,
                    body=probe_req.body,
                )
                result.evidence.append(ev)
                all_responses.append((step, ev.response))

        if not all_responses:
            result.error = "No responses collected"
            result.completed_at = datetime.now(timezone.utc).isoformat()
            return result

        baseline_resp = all_responses[0][1]
        detection = _detect_from_plan(all_responses, plan, baseline_resp)
        result.confirmed = detection["confirmed"]
        result.confidence = detection["confidence"]
        result.detection_method = detection["method"]
        result.detection_details = detection["details"]
        result.false_positive_risk = detection["false_positive_risk"]
        result.alternative_explanations = detection["alternative_explanations"]
        result.baseline_response = baseline_resp

        # Populate test_value and vulnerable_param from best detection
        if detection.get("tested_params"):
            best_params = detection["tested_params"]
            result.vulnerable_param = next(iter(best_params), "")
            result.test_value = best_params.get(result.vulnerable_param, "")
        if detection.get("tested_payload_key"):
            result.detection_details += f" (payload: {detection['tested_payload_key']})"

        for step, resp in all_responses[1:]:
            if resp.status_code in (200, 201) and resp.body_size > 10:
                result.test_response = resp
                result.test_request = step.to_request(base_url)
                break

        # Verify step if confirmed
        if result.confirmed:
            bl_step = plan.steps[0] if plan.steps else None
            if bl_step:
                try:
                    with httpx.Client(timeout=_TIMEOUT, verify=False) as client:
                        verify_ev = self._send_request(
                            client=client,
                            label="verify",
                            method=bl_step.method,
                            url=base_url,
                            params=bl_step.params,
                            headers=all_headers,
                            body=bl_step.body,
                        )
                        result.evidence.append(verify_ev)
                except Exception:
                    pass

        result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    def _send_request(
        self,
        client: httpx.Client,
        label: str,
        method: str,
        url: str,
        params: dict[str, str] | None,
        headers: dict[str, str] | None,
        body: Any = None,
    ) -> ProbeEvidence:
        """Send a single request and return ProbeEvidence."""
        start = time.monotonic()
        response_url = url
        try:
            response = client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                content=json.dumps(body) if isinstance(body, dict) else body,
            )
            elapsed = (time.monotonic() - start) * 1000
            body_text = response.text[:_MAX_BODY_SAMPLE]
            response_url = str(response.url)
            probe_resp = ProbeResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=body_text,
                body_size=len(response.content),
                elapsed_ms=round(elapsed, 1),
            )
        except Exception as exc:
            probe_resp = ProbeResponse(
                status_code=0,
                body=str(exc),
                body_size=0,
            )

        probe_req = ProbeRequest(
            method=method,
            url=response_url,
            headers=dict(headers or {}),
            body=body,
            params=dict(params or {}),
        )

        return ProbeEvidence(label=label, request=probe_req, response=probe_resp)


# ── Helpers ─────────────────────────────────────────────────────


def _test_value_for(vuln_type: str) -> str:
    return {
        "idor": "999999",
        "ssrf": "http://127.0.0.1:8080",
        "auth_bypass": "admin",
        "xss": "<img src=x onerror=alert(1)>",
        "sqli": "' OR '1'='1' --",
        "generic": "test_value",
    }.get(vuln_type, "test_value")


def _baseline_value_for(param_name: str) -> str:
    name_lower = param_name.lower()
    if "id" in name_lower or "uuid" in name_lower:
        return "1"
    if "email" in name_lower:
        return "user@example.com"
    if "user" in name_lower:
        return "user"
    if "page" in name_lower or "offset" in name_lower:
        return "0"
    if "limit" in name_lower:
        return "10"
    return "1"


def _extract_host(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return endpoint


# ── Detection logic ─────────────────────────────────────────────


def _detect_vulnerability(
    vuln_type: str,
    baseline: ProbeResponse,
    test: ProbeResponse,
    vuln_param: str,
    test_value: str,
    baseline_value: str,
) -> dict[str, Any]:
    """Compare baseline and test responses to detect vulnerability.

    Returns a dict with:
        confirmed, confidence, method, details, false_positive_risk, alternative_explanations
    """
    detector = _DETECTORS.get(vuln_type)
    if detector:
        return detector(baseline, test, vuln_param, test_value, baseline_value)

    # Generic fallback
    return _detect_generic(baseline, test, vuln_param, test_value, baseline_value)


def _detect_idor(
    baseline: ProbeResponse,
    test: ProbeResponse,
    vuln_param: str,
    test_value: str,
    baseline_value: str,
) -> dict[str, Any]:
    """IDOR: access to a resource that should be inaccessible.

    Detection: test returns 200 with meaningful body while requesting another user's resource.
    """
    details: list[str] = []
    alt: list[str] = []

    baseline_ok = baseline.status_code in (200, 201)
    test_ok = test.status_code in (200, 201)
    baseline_size = baseline.body_size
    test_size = test.body_size
    size_diff_ratio = abs(test_size - baseline_size) / max(baseline_size, 1)

    # Both return 200 with similar body size = likely IDOR
    if baseline_ok and test_ok and size_diff_ratio < 0.5 and baseline_size > 10 and test_size > 10:
        details.append(
            f"Both requests returned 200 with similar body sizes (baseline={baseline_size}, test={test_size})"
        )
        alt.append("Both resources exist and are publicly accessible")
        alt.append("The parameter might not control access")
        return {
            "confirmed": True,
            "confidence": 0.8 if test.status_code == baseline.status_code else 0.6,
            "method": "status_diff",
            "details": " ".join(details),
            "false_positive_risk": "medium",
            "alternative_explanations": alt,
        }

    # Baseline 403/401, test 200 = clear IDOR
    if baseline.status_code in (401, 403) and test.status_code in (200, 201):
        details.append(
            f"Baseline returned {baseline.status_code} (expected), "
            f"test returned {test.status_code} with different resource"
        )
        alt.append("The baseline value might be invalid/expired, not protected")
        return {
            "confirmed": True,
            "confidence": 0.9,
            "method": "status_diff",
            "details": " ".join(details),
            "false_positive_risk": "low",
            "alternative_explanations": alt,
        }

    details.append(f"No IDOR pattern detected (baseline={baseline.status_code}, test={test.status_code})")
    return {
        "confirmed": False,
        "confidence": 0.0,
        "method": "status_diff",
        "details": " ".join(details),
        "false_positive_risk": "low",
        "alternative_explanations": alt,
    }


def _detect_ssrf(
    baseline: ProbeResponse,
    test: ProbeResponse,
    vuln_param: str,
    test_value: str,
    baseline_value: str,
) -> dict[str, Any]:
    """SSRF: server makes requests to attacker-controlled URLs.

    Detection: test with internal URL causes different response (timeout, error, or access).
    """
    alt: list[str] = []
    details: list[str] = []

    if test.elapsed_ms > baseline.elapsed_ms * 1.5 and test.elapsed_ms > 5000:
        details.append(
            f"Test request took {test.elapsed_ms:.0f}ms vs baseline {baseline.elapsed_ms:.0f}ms "
            f"— possible SSRF timeout to internal host"
        )
        return {
            "confirmed": True,
            "confidence": 0.75,
            "method": "timing",
            "details": " ".join(details),
            "false_positive_risk": "medium",
            "alternative_explanations": ["Network latency, not SSRF"],
        }

    if test.status_code in (502, 504) and baseline.status_code in (200, 201):
        details.append(f"Test caused {test.status_code} (gateway error) while baseline was OK")
        alt.append("The parameter value might be invalid, causing an error, not SSRF")
        return {
            "confirmed": True,
            "confidence": 0.6,
            "method": "error_pattern",
            "details": " ".join(details),
            "false_positive_risk": "high",
            "alternative_explanations": alt,
        }

    return {
        "confirmed": False,
        "confidence": 0.0,
        "method": "timing",
        "details": "No SSRF pattern detected",
        "false_positive_risk": "low",
        "alternative_explanations": [],
    }


def _detect_xss(
    baseline: ProbeResponse,
    test: ProbeResponse,
    vuln_param: str,
    test_value: str,
    baseline_value: str,
) -> dict[str, Any]:
    """XSS: injected script appears in the response.

    Detection: test_value appears unescaped in the response body.
    """
    if "<img src=x" in test.body or "onerror=alert(1)" in test.body or test_value in test.body:
        return {
            "confirmed": True,
            "confidence": 0.85,
            "method": "reflection",
            "details": f"Test value '{test_value[:30]}' reflected in response body",
            "false_positive_risk": "low" if test_value in test.body else "medium",
            "alternative_explanations": ["The value might be reflected in an error message, not executed"]
            if test_value in test.body
            else [],
        }

    return {
        "confirmed": False,
        "confidence": 0.0,
        "method": "reflection",
        "details": "Test value not reflected in response",
        "false_positive_risk": "low",
        "alternative_explanations": [],
    }


def _detect_sqli(
    baseline: ProbeResponse,
    test: ProbeResponse,
    vuln_param: str,
    test_value: str,
    baseline_value: str,
) -> dict[str, Any]:
    """SQLi: SQL error or different response with SQL payload.

    Detection: test causes 500, different body, or SQL error messages.
    """
    alt: list[str] = []
    details: list[str] = []

    sql_errors = ["SQL", "mysql", "syntax error", "ORA-", "PostgreSQL", "SQLite", "unclosed quotation"]

    if test.status_code == 500:
        error_found = [e for e in sql_errors if e.lower() in test.body.lower()]
        if error_found:
            details.append(f"Test caused 500 with SQL error: {error_found[0]}")
            return {
                "confirmed": True,
                "confidence": 0.9,
                "method": "error_pattern",
                "details": " ".join(details),
                "false_positive_risk": "low",
                "alternative_explanations": [],
            }
        details.append("Test caused 500 but no SQL error pattern found")
        alt.append("Generic server error, not SQL injection")

    # Check for boolean-based detection
    if (
        test.status_code == baseline.status_code
        and test.body_size != baseline.body_size
        and abs(test.body_size - baseline.body_size) / max(baseline.body_size, 1) > 0.1
    ):
        return {
            "confirmed": True,
            "confidence": 0.6,
            "method": "body_diff",
            "details": f"Response body differs (baseline={baseline.body_size}, test={test.body_size})",
            "false_positive_risk": "high",
            "alternative_explanations": ["Different data, not SQL injection"],
        }

    return {
        "confirmed": False,
        "confidence": 0.0,
        "method": "error_pattern",
        "details": "No SQLi pattern detected",
        "false_positive_risk": "low",
        "alternative_explanations": [],
    }


def _detect_auth_bypass(
    baseline: ProbeResponse,
    test: ProbeResponse,
    vuln_param: str,
    test_value: str,
    baseline_value: str,
) -> dict[str, Any]:
    """Auth Bypass: accessing protected endpoints with manipulated credentials.

    Detection: test with modified auth value succeeds where it shouldn't.
    """
    if test.status_code in (200, 201) and test.body_size > 50:
        return {
            "confirmed": True,
            "confidence": 0.7,
            "method": "status_diff",
            "details": f"Test with value '{test_value}' returned {test.status_code} with {test.body_size} bytes",
            "false_positive_risk": "high",
            "alternative_explanations": [
                "The test value might be a valid credential, not a bypass",
                "The endpoint might not require auth for this specific resource",
            ],
        }

    return {
        "confirmed": False,
        "confidence": 0.0,
        "method": "status_diff",
        "details": "No auth bypass detected",
        "false_positive_risk": "low",
        "alternative_explanations": [],
    }


def _detect_generic(
    baseline: ProbeResponse,
    test: ProbeResponse,
    vuln_param: str,
    test_value: str,
    baseline_value: str,
) -> dict[str, Any]:
    """Generic detection: any behavioral difference between baseline and test."""
    diff_parts: list[str] = []
    if test.status_code != baseline.status_code:
        diff_parts.append(f"status {baseline.status_code}→{test.status_code}")
    size_ratio = abs(test.body_size - baseline.body_size) / max(baseline.body_size, 1)
    if size_ratio > 0.2:
        diff_parts.append(f"body size {baseline.body_size}→{test.body_size} ({size_ratio:.0%})")
    if test.elapsed_ms > baseline.elapsed_ms * 2:
        diff_parts.append(f"timing {baseline.elapsed_ms:.0f}→{test.elapsed_ms:.0f}ms")

    if diff_parts:
        return {
            "confirmed": True,
            "confidence": 0.4,
            "method": "behavioral_diff",
            "details": "Difference detected: " + ", ".join(diff_parts),
            "false_positive_risk": "high",
            "alternative_explanations": ["Natural variance, not a vulnerability"],
        }

    return {
        "confirmed": False,
        "confidence": 0.0,
        "method": "behavioral_diff",
        "details": "No behavioral difference detected",
        "false_positive_risk": "low",
        "alternative_explanations": [],
    }


def _detect_from_plan(
    all_responses: list[tuple[AttackStep, ProbeResponse]],
    plan: TestPlan,
    baseline: ProbeResponse,
) -> dict[str, Any]:
    """Analyze all responses from a TestPlan execution.

    Evaluates each test step against the baseline, aggregates findings,
    and returns the best detection result across all payloads.
    """
    if not all_responses or len(all_responses) < 2:
        return {
            "confirmed": False,
            "confidence": 0.0,
            "method": "",
            "details": "No test responses",
            "false_positive_risk": "low",
            "alternative_explanations": [],
        }

    best: dict[str, Any] = {
        "confirmed": False,
        "confidence": 0.0,
        "method": "",
        "details": "",
        "false_positive_risk": "low",
        "alternative_explanations": [],
    }

    detector = _DETECTORS.get(plan.vulnerability_type)
    for step, resp in all_responses[1:]:
        if step.purpose == "baseline":
            continue
        det = detector(baseline, resp, "", "", "") if detector else _detect_generic(baseline, resp, "", "", "")
        if det["confirmed"] and det["confidence"] > best["confidence"]:
            best = det
            best["tested_payload_key"] = step.payload_key
            best["tested_params"] = step.params

    return best if best["confirmed"] else best


_DETECTORS = {
    "idor": _detect_idor,
    "ssrf": _detect_ssrf,
    "xss": _detect_xss,
    "sqli": _detect_sqli,
    "auth_bypass": _detect_auth_bypass,
}
