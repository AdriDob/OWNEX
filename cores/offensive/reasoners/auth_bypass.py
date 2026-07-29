from __future__ import annotations

import logging
import re
from typing import Any

from core.offensive.models import EndpointInfo, Hypothesis
from core.offensive.reasoners.base import BaseReasoner
from core.offensive.templates import AUTH_BYPASS_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.auth_bypass")

AUTH_BYPASS_KEYWORDS: dict[str, float] = {
    "admin": 0.85,
    "administrator": 0.8,
    "moderator": 0.6,
    "manager": 0.5,
    "internal": 0.7,
    "private": 0.65,
    "restricted": 0.7,
    "dashboard": 0.6,
    "config": 0.6,
    "configuration": 0.5,
    "settings": 0.4,
    "debug": 0.7,
    "swagger": 0.65,
    "api-docs": 0.6,
    "graphql": 0.6,
    "beta": 0.5,
    "staging": 0.5,
    "dev": 0.5,
    "test": 0.4,
    "v2": 0.3,
    "v3": 0.3,
}

WEAK_ENDPOINT_PATTERNS: list[tuple[str, float]] = [
    (r"/api/(v[0-9]+/)?internal/", 0.8),
    (r"/api/(v[0-9]+/)?admin/", 0.85),
    (r"/api/(v[0-9]+/)?debug/", 0.7),
    (r"/api/(v[0-9]+/)?health", 0.3),
    (r"/api/(v[0-9]+/)?metrics", 0.5),
    (r"/graphql", 0.6),
    (r"/api/(v[0-9]+/)?swagger", 0.65),
    (r"/api/(v[0-9]+/)?docs", 0.5),
    (r"/.env", 0.9),
    (r"/api/(v[0-9]+/)?config", 0.7),
]

JWT_INDICATORS: list[str] = [
    "authorization",
    "bearer",
    "jwt",
    "token",
    "x-auth-token",
    "x-access-token",
    "api-key",
    "x-api-key",
]

NO_AUTH_INDICATORS: list[str] = [
    "public",
    "static",
    "assets",
    "files",
    "health",
    "version",
    "status",
    "ping",
    "open",
    "docs",
]

AUTH_PATTERN = re.compile(r"auth|login|session|token|jwt|bearer|oauth", re.IGNORECASE)
JWT_PATTERN = re.compile(r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+")


class AuthBypassReasoner(BaseReasoner):
    @property
    def vulnerability_type(self) -> str:
        return "auth_bypass"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        # Signal 1: Path contains admin/restricted keywords
        path_lower = endpoint.path.lower()
        for keyword, score in AUTH_BYPASS_KEYWORDS.items():
            if keyword in path_lower:
                signals.append(f"Restricted path segment detected: {keyword}")
                params_of_interest.append(keyword)
                confidence += score * 0.25

        # Signal 2: Weak endpoint pattern matching
        for pattern, score in WEAK_ENDPOINT_PATTERNS:
            if re.search(pattern, path_lower):
                signals.append(f"Weak/restricted endpoint pattern: {pattern}")
                confidence += score * 0.3
                break

        # Signal 3: No auth headers present
        if endpoint.headers:
            has_auth = False
            for header_name in endpoint.headers:
                if any(ind in header_name.lower() for ind in JWT_INDICATORS):
                    has_auth = True
                    if JWT_PATTERN.match(str(endpoint.headers.get(header_name, ""))):
                        signals.append("JWT token found in headers")
                        confidence += 0.2
                    break
            if not has_auth:
                signals.append("No authentication headers detected")
                confidence += 0.3

        # Signal 4: Public-indicating path
        has_public_indicator = any(ind in path_lower for ind in NO_AUTH_INDICATORS)
        if has_public_indicator and any(kw in path_lower for kw in AUTH_BYPASS_KEYWORDS):
            signals.append("Mixed public/restricted path patterns")
            confidence += 0.2

        # Signal 5: Path traversal potential
        if ".." in endpoint.path or "%2f" in path_lower or "//" in endpoint.path.strip("/"):
            signals.append("Path traversal characters detected")
            confidence += 0.25

        # Signal 6: OPTIONS method (preflight) may bypass auth
        if endpoint.method.upper() == "OPTIONS":
            signals.append("OPTIONS method may bypass auth middleware")
            confidence += 0.15

        # Signal 7: Path depth anomaly — very deep paths may have weaker auth
        depth = len([p for p in endpoint.path.split("/") if p])
        if depth >= 5:
            signals.append(f"Deep path (depth={depth}) may have weaker auth checks")
            confidence += 0.15

        if confidence < 0.1:
            return []

        confidence = min(confidence, 1.0)
        method = endpoint.method.upper()
        severity = self._compute_severity(confidence, method)

        hypothesis = Hypothesis(
            vulnerability_type="auth_bypass",
            endpoint=endpoint.path,
            method=endpoint.method,
            confidence=confidence,
            severity=severity,
            summary=self._build_summary(endpoint),
            description=self._build_description(endpoint, method),
            why_human_would_investigate=self._build_triager_justification(endpoint, method, signals),
            parameters_of_interest=params_of_interest,
            signals=signals,
            test_instructions=self._build_test_instructions(endpoint, method),
            alternative_explanations=self._build_alternatives(),
            scope_check=self._scope_check(endpoint),
            reproducibility_notes=self._reproducibility_notes(method),
        )

        return [hypothesis]

    def _compute_severity(self, confidence: float, method: str) -> str:
        if confidence >= 0.65:
            return "high"
        if confidence >= 0.4:
            return "medium"
        return "low"

    def _build_summary(self, endpoint: EndpointInfo) -> str:
        return f"Potential authentication bypass on {endpoint.method} {endpoint.path}"

    def _build_description(self, endpoint: EndpointInfo, method: str) -> str:
        return (
            f"The endpoint {endpoint.method} {endpoint.path} may have missing or "
            f"insufficient authentication. If accessible without valid credentials, "
            f"this could allow unauthorized access to sensitive data or functionality. "
            f"Auth bypass can range from missing middleware to path traversal bypassing "
            f"prefix-based auth checks."
        )

    def _build_triager_justification(self, endpoint: EndpointInfo, method: str, signals: list[str]) -> str:
        return (
            f"A human triager would investigate this because: "
            f"{endpoint.method} {endpoint.path} has indicators of weak or missing "
            f"authentication. The endpoint has {len(signals)} bypass signals including "
            f"path patterns that suggest restricted functionality. "
            f"Auth bypass is typically high-impact as it can expose all downstream functionality."
        )

    def _build_test_instructions(self, endpoint: EndpointInfo, method: str) -> list[str]:
        return [
            "Try accessing the endpoint without any Authorization header or cookies.",
            "Try accessing the endpoint with an empty/invalid token.",
            f"Try path traversal: /admin/../{endpoint.path.lstrip('/')}",
            "Try HTTP method override: X-HTTP-Method-Override: GET",
            "Try alternative content types that may skip auth middleware.",
            "Check if OPTIONS request returns different auth requirements.",
            "For JWT-protected endpoints, try: alg=none, remove signature, kid injection.",
        ]

    def _build_alternatives(self) -> list[dict[str, Any]]:
        return [
            {"label": alt["label"], "description": alt["description"], "how_to_rule_out": alt["how_to_rule_out"]}
            for alt in AUTH_BYPASS_ALTERNATIVES
        ]

    def _scope_check(self, endpoint: EndpointInfo) -> str:
        return (
            f"Verify that {endpoint.path} is within scope. "
            f"Check if auth bypass testing is explicitly permitted. "
            f"Confirm that the endpoint is not intentionally public."
        )

    @staticmethod
    def _reproducibility_notes(method: str) -> str:
        return (
            f"Send a {method} request to the endpoint with NO authentication. "
            f"If the endpoint returns 200 with sensitive data, auth bypass is confirmed. "
            f"Then try with an invalid/wrong token to confirm it's not just CORS misconfiguration."
        )
