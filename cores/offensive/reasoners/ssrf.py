from __future__ import annotations

import logging
import re
from typing import Any

from core.offensive.models import EndpointInfo, Hypothesis
from core.offensive.reasoners.base import BaseReasoner
from core.offensive.templates import SSRF_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.ssrf")

URL_PARAM_KEYWORDS: dict[str, float] = {
    "url": 0.95,
    "uri": 0.9,
    "href": 0.85,
    "src": 0.85,
    "target": 0.8,
    "endpoint": 0.8,
    "webhook": 0.85,
    "callback": 0.85,
    "redirect": 0.85,
    "return_url": 0.85,
    "returnUrl": 0.85,
    "redirect_uri": 0.85,
    "redirectUri": 0.85,
    "next": 0.8,
    "path": 0.7,
    "file": 0.75,
    "download": 0.75,
    "upload_url": 0.75,
    "uploadUrl": 0.75,
    "image_url": 0.8,
    "imageUrl": 0.8,
    "avatar_url": 0.8,
    "avatarUrl": 0.8,
    "link": 0.7,
    "host": 0.7,
    "domain": 0.7,
    "proxy": 0.75,
    "forward": 0.75,
    "fetch": 0.85,
    "import": 0.8,
    "export_url": 0.8,
    "exportUrl": 0.8,
    "reference": 0.6,
    "source": 0.7,
    "destination": 0.7,
}

METHOD_RISK: dict[str, float] = {
    "GET": 0.7,
    "POST": 0.7,
    "PUT": 0.6,
    "PATCH": 0.6,
}

IP_PATTERN = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)


class SSRFReasoner(BaseReasoner):
    @property
    def vulnerability_type(self) -> str:
        return "ssrf"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST", "PUT", "PATCH"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        # Signal 1: URL-accepting parameters (highest signal)
        all_param_names = list(endpoint.params.keys())
        if endpoint.body:
            all_param_names.extend(endpoint.body.keys())
        if endpoint.headers:
            all_param_names.extend(endpoint.headers.keys())

        for pname in all_param_names:
            score = URL_PARAM_KEYWORDS.get(pname.lower(), 0.0)
            if score >= 0.8:
                signals.append(f"High-confidence URL parameter: {pname}")
                params_of_interest.append(pname)
                confidence += score * 0.35
            elif score >= 0.6:
                signals.append(f"URL-related parameter: {pname}")
                params_of_interest.append(pname)
                confidence += score * 0.25

        # Signal 2: URL values in existing parameters
        for pname, pval in endpoint.params.items():
            if isinstance(pval, str) and URL_PATTERN.search(pval):
                signals.append(f"URL value found in {pname}")
                params_of_interest.append(pname)
                confidence += 0.3
            if isinstance(pval, str) and IP_PATTERN.match(pval):
                signals.append(f"IP address in parameter {pname}")
                params_of_interest.append(pname)
                confidence += 0.25

        # Signal 3: HTTP method risk
        method = endpoint.method.upper()
        if method in METHOD_RISK:
            confidence += METHOD_RISK[method] * 0.15

        # Signal 4: Path-based URL indicators
        path_lower = endpoint.path.lower()
        path_url_indicators = ["proxy", "fetch", "webhook", "callback", "redirect", "forward", "download", "import"]
        for indicator in path_url_indicators:
            if indicator in path_lower:
                signals.append(f"SSRF-consistent path segment: {indicator}")
                confidence += 0.15
                break

        # Signal 5: Body parameters with URL patterns
        if endpoint.body:
            for key, val in endpoint.body.items():
                if isinstance(val, str) and URL_PATTERN.search(val):
                    signals.append(f"URL value in body field {key}")
                    params_of_interest.append(key)
                    confidence += 0.25

        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        severity = self._compute_severity(confidence, method)

        hypothesis = Hypothesis(
            vulnerability_type="ssrf",
            endpoint=endpoint.path,
            method=endpoint.method,
            confidence=confidence,
            severity=severity,
            summary=self._build_summary(endpoint, params_of_interest),
            description=self._build_description(endpoint, params_of_interest, method),
            why_human_would_investigate=self._build_triager_justification(
                endpoint, params_of_interest, method, signals
            ),
            why_triager_might_reject=self._build_triager_rejection(endpoint, params_of_interest, method, signals),
            parameters_of_interest=params_of_interest,
            signals=signals,
            test_instructions=self._build_test_instructions(endpoint, params_of_interest, method),
            alternative_explanations=self._build_alternatives(),
            scope_check=self._scope_check(endpoint),
            reproducibility_notes=self._reproducibility_notes(method, params_of_interest),
        )

        return [hypothesis]

    def _compute_severity(self, confidence: float, method: str) -> str:
        if confidence >= 0.7:
            return "high"
        if confidence >= 0.4:
            return "medium"
        return "low"

    def _build_summary(self, endpoint: EndpointInfo, params: list[str]) -> str:
        refs = ", ".join(params[:3])
        return f"Potential SSRF via {refs} on {endpoint.method} {endpoint.path}"

    def _build_description(self, endpoint: EndpointInfo, params: list[str], method: str) -> str:
        refs = ", ".join(params[:4])
        return (
            f"The endpoint {endpoint.method} {endpoint.path} accepts URL-related parameters "
            f"({refs}) that could allow an attacker to make the server send requests to "
            f"arbitrary destinations. If the server does not validate destination URLs, "
            f"this could enable SSRF to internal services, cloud metadata endpoints, or "
            f"external systems for blind SSRF data exfiltration."
        )

    def _build_triager_justification(
        self, endpoint: EndpointInfo, params: list[str], method: str, signals: list[str]
    ) -> str:
        return (
            f"A human triager would investigate this because: "
            f"{endpoint.method} {endpoint.path} accepts URL parameters ({params[0] if params else 'unknown'}) "
            f"that could be exploited for server-side request forgery. "
            f"SSRF can lead to cloud metadata exposure, internal network scanning, "
            f"and remote code execution via internal service interaction. "
            f"The endpoint has {len(signals)} SSRF indicators."
        )

    def _build_triager_rejection(
        self, endpoint: EndpointInfo, params: list[str], method: str, signals: list[str]
    ) -> str:
        rejections = []
        if not endpoint.headers:
            rejections.append("No authentication or authorization headers present")
        if not params:
            rejections.append("No URL parameters detected for exploitation")
        else:
            rejections.append("Destination validation may be in place (allowlist/denylist)")
        if len(signals) < 3:
            rejections.append("Insufficient technical indicators for credible SSRF")
        if method.upper() in ["GET", "POST"]:
            rejections.append("Low-risk methods may not justify investigation time")
        return ". ".join(rejections)

    def _scope_check(self, endpoint: EndpointInfo) -> str:
        return (
            f"Verify that {endpoint.path} is within scope. "
            f"Check if SSRF and out-of-band testing are permitted. "
            f"Confirm no rate limits that would block multiple SSRF probe requests."
        )

    def _reproducibility_notes(self, method: str, params: list[str]) -> str:
        param = params[0] if params else "the URL parameter"
        return (
            f"Use a collaborator (interact.sh, Burp Collaborator) to detect outbound requests. "
            f"Send {method} request with {param}=http://YOUR-COLLABORATOR-DOMAIN. "
            f"If a callback is received, SSRF is confirmed."
        )

    def _build_alternatives(self) -> list[dict[str, Any]]:
        return [
            {"label": alt["label"], "description": alt["description"], "how_to_rule_out": alt["how_to_rule_out"]}
            for alt in SSRF_ALTERNATIVES
        ]

    def _build_test_instructions(self, endpoint: EndpointInfo, params: list[str], method: str) -> list[str]:
        instructions = []
        for param in params[:2]:
            instructions.extend(
                [
                    f"Try setting {param} to http://127.0.0.1:80 and observe the response.",
                    f"Try setting {param} to http://169.254.169.254/latest/meta-data/ (AWS metadata).",
                    f"Try setting {param} to file:///etc/passwd for local file access.",
                    "Monitor outbound requests using a collaborator / request bin.",
                ]
            )
        instructions.append(
            "If direct SSRF is blocked, try: DNS rebinding, redirect-based bypass, "
            "alternative protocols (gopher://, dict://), IPv6 variants, decimal IPs."
        )
        return instructions
