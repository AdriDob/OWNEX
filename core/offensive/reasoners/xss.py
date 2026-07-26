from __future__ import annotations

import logging
import re
from typing import Any

from core.offensive.models import EndpointInfo, Hypothesis
from core.offensive.reasoners.base import BaseReasoner
from core.offensive.templates import XSS_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.xss")

REFLECTED_INPUT_KEYWORDS: dict[str, float] = {
    "q": 0.7,
    "query": 0.7,
    "search": 0.7,
    "s": 0.6,
    "keyword": 0.6,
    "term": 0.6,
    "name": 0.5,
    "message": 0.6,
    "comment": 0.6,
    "text": 0.5,
    "content": 0.5,
    "title": 0.5,
    "callback": 0.7,
    "jsonp": 0.75,
    "redirect": 0.6,
    "return_url": 0.6,
    "returnUrl": 0.6,
    "next": 0.6,
    "url": 0.6,
    "file": 0.4,
    "filename": 0.5,
    "upload": 0.5,
}

XSS_SENSITIVE_PATHS: list[tuple[str, float]] = [
    (r"/search", 0.7),
    (r"/api/search", 0.65),
    (r"/comment", 0.7),
    (r"/post", 0.6),
    (r"/profile", 0.6),
    (r"/feedback", 0.7),
    (r"/contact", 0.65),
    (r"/review", 0.65),
    (r"/message", 0.7),
    (r"/chat", 0.7),
    (r"/upload", 0.6),
    (r"/api/upload", 0.55),
    (r"/redirect", 0.6),
    (r"/proxy", 0.5),
]

HTML_INDICATORS = re.compile(
    r"<[^>]*>|&lt;|&gt;|%3C|%3E|&#x3C;|&#60;",
    re.IGNORECASE,
)

SCRIPT_INDICATORS = re.compile(
    r"<script|<img|<svg|<iframe|<body|<input|<textarea|<math",
    re.IGNORECASE,
)
class XSSReasoner(BaseReasoner):
    @property
    def vulnerability_type(self) -> str:
        return "xss"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST", "PUT", "PATCH"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        # Signal 1: Reflected input keywords in params
        for pname in endpoint.params:
            score = REFLECTED_INPUT_KEYWORDS.get(pname.lower(), 0.0)
            if score >= 0.6:
                signals.append(f"XSS-relevant query parameter: {pname}")
                params_of_interest.append(pname)
                confidence += score * 0.3
            elif score >= 0.4:
                signals.append(f"User-controlled parameter: {pname}")
                params_of_interest.append(pname)
                confidence += score * 0.2

        # Signal 2: Path-based XSS indicators
        path_lower = endpoint.path.lower()
        for pattern, score in XSS_SENSITIVE_PATHS:
            if re.search(pattern, path_lower):
                signals.append(f"XSS-common path pattern: {pattern}")
                confidence += score * 0.25
                break

        # Signal 3: HTML content in existing values (suggests reflection)
        for pname, pval in endpoint.params.items():
            if isinstance(pval, str):
                if HTML_INDICATORS.search(pval):
                    signals.append(f"HTML entities in parameter {pname}")
                    params_of_interest.append(pname)
                    confidence += 0.3
                if SCRIPT_INDICATORS.search(pval):
                    signals.append(f"Script-like content in parameter {pname}")
                    params_of_interest.append(pname)
                    confidence += 0.4

        # Signal 4: JSONP/callback patterns
        if "callback" in endpoint.params or "jsonp" in endpoint.params:
            signals.append("JSONP callback parameter detected — potential XSS via callback")
            params_of_interest.extend(["callback", "jsonp"])
            confidence += 0.4

        # Signal 5: Response sample analysis
        if endpoint.response_sample:
            sample_str = str(endpoint.response_sample)
            if HTML_INDICATORS.search(sample_str):
                signals.append("Response contains HTML — potential reflection point")
                confidence += 0.2
            # Check if any param values appear in response
            for pname, pval in endpoint.params.items():
                if isinstance(pval, str) and len(pval) > 3 and pval in sample_str:
                    signals.append(f"Parameter {pname} value reflected in response")
                    params_of_interest.append(pname)
                    confidence += 0.35
                    break

        # Signal 6: POST body with text fields
        if endpoint.body and isinstance(endpoint.body, dict):
            text_fields = [k for k, v in endpoint.body.items() if isinstance(v, str) and len(v) > 5]
            if text_fields:
                signals.append(f"Body contains text fields ({len(text_fields)}) that may be stored/reflected")
                params_of_interest.extend(text_fields[:3])
                confidence += 0.2

        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        method = endpoint.method.upper()
        severity = self._compute_severity(confidence, method)

        # Build summary with top 3 params for readability
        summary_params = params_of_interest[:3]
        summary = f"Potential XSS via {', '.join(summary_params)} on {endpoint.method} {endpoint.path}"

        hypothesis = Hypothesis(
            vulnerability_type="xss",
            endpoint=endpoint.path,
            method=endpoint.method,
            confidence=confidence,
            severity=severity,
            summary=summary,
            description=self._build_description(endpoint, params_of_interest, method),
            why_human_would_investigate=self._build_triager_justification(
                endpoint, params_of_interest, method, signals
            ),
            why_triager_might_reject=self._build_triager_rejection(
                endpoint, params_of_interest, method, signals
            ),
            parameters_of_interest=params_of_interest,
            signals=signals,
            test_instructions=self._build_test_instructions(endpoint, params_of_interest, method),
            alternative_explanations=self._build_alternatives(),
            scope_check=self._scope_check(endpoint),
            reproducibility_notes=self._reproducibility_notes(method, params_of_interest),
        )

        return [hypothesis]

    def _compute_severity(self, confidence: float, method: str) -> str:
        if confidence >= 0.6:
            return "high"
        if confidence >= 0.35:
            return "medium"
        return "low"

    def _build_description(self, endpoint: EndpointInfo, params: list[str], method: str) -> str:
        refs = ", ".join(params[:4])
        return (
            f"The endpoint {endpoint.method} {endpoint.path} accepts user-controlled input "
            f"({refs}) that may be reflected or stored and later served to users. "
            f"If the input is not properly sanitized, an attacker could inject JavaScript "
            f"that executes in victims' browsers, leading to session theft, data exfiltration, "
            f"or account takeover."
        )

    def _build_triager_justification(
        self, endpoint: EndpointInfo, params: list[str], method: str, signals: list[str]
    ) -> str:
        return (
            f"A human triager would investigate this because: "
            f"{endpoint.method} {endpoint.path} reflects or stores user input ({params[0] if params else 'unknown'}). "
            f"The endpoint has {len(signals)} XSS indicators. "
            f"A simple test with a script payload would confirm or rule out XSS."
        )

    def _build_triager_rejection(
        self, endpoint: EndpointInfo, params: list[str], method: str, signals: list[str]
    ) -> str:
        rejections = []
        if not endpoint.headers:
            rejections.append("No authentication or authorization headers present")
        if len(signals) < 2:
            rejections.append("Insufficient technical indicators for credible XSS")
        if method.upper() == "GET":
            rejections.append("GET-only endpoints may not justify XSS investigation time")
        else:
            rejections.append("Output encoding or CSP likely in place preventing execution")
        return ". ".join(rejections)

    def _scope_check(self, endpoint: EndpointInfo) -> str:
        return (
            f"Verify that {endpoint.path} is within scope. "
            f"Check if XSS is considered valid (some programs deprioritize reflected XSS). "
            f"Confirm the output context (HTML body, attribute, JS, CSS)."
        )

    @staticmethod
    def _reproducibility_notes(method: str, params: list[str]) -> str:
        param = params[0] if params else "the input"
        return (
            f"Send {method} request with XSS payload in {param}. "
            f"If the payload executes in the browser (alert, console.log), XSS is confirmed. "
            f"Provide the exact payload and a screenshot of execution."
        )

    def _build_alternatives(self) -> list[dict[str, Any]]:
        return [
            {"label": alt["label"], "description": alt["description"], "how_to_rule_out": alt["how_to_rule_out"]}
            for alt in XSS_ALTERNATIVES
        ]

    def _build_test_instructions(self, endpoint: EndpointInfo, params: list[str], method: str) -> list[str]:
        instructions = []
        for param in params[:2]:
            instructions.extend(
                [
                    f"Try setting {param} to <script>alert(1)</script> and check if it executes.",
                    f"Try setting {param} to <img src=x onerror=alert(1)> for event handler XSS.",
                    f"Try setting {param} to ';alert(1)// for JS string context XSS.",
                    f'Try setting {param} to "><script>alert(1)</script><" for HTML attribute context.',
                ]
            )
        instructions.append(
            "If basic XSS is blocked, check: encoding bypass, polyglot payloads, "
            "DOM-based XSS via URL fragment, and stored XSS via POST."
        )
        return instructions
