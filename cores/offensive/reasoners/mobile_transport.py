"""Mobile Transport Security Reasoner — detects transport weaknesses affecting
mobile clients.

Analyzes endpoints for: plain-HTTP hosts, session/auth material in URL paths,
and missing transport-hardening signals on endpoints that mobile apps call
over untrusted networks (public Wi-Fi, carrier NAT, VPNs).

Honest scope: this reasoner cannot observe TLS handshakes or verify
certificate pinning from HTTP metadata. It flags the server-visible
conditions that make transport attacks practical: cleartext hosts, tokens
in cacheable locations, and session identifiers in URL paths. Pinning
verification itself requires on-device testing and is called out in the
test instructions, not assumed.
"""

from __future__ import annotations

import logging
import re

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner

logger = logging.getLogger("orion.core.offensive.reasoners.mobile_transport")

# Session/auth material that must never sit in URL paths (cacheable, logged)
SESSION_IN_PATH_KEYWORDS: dict[str, float] = {
    "session": 0.9,
    "sessionid": 0.9,
    "session_id": 0.9,
    "jsessionid": 0.9,
    "phpsessid": 0.9,
    "token": 0.85,
    "auth": 0.8,
    "apikey": 0.85,
    "api_key": 0.85,
}

# Auth/session material in query strings (proxy/CDN logs, Referer leaks)
SESSION_IN_QUERY_KEYWORDS: dict[str, float] = {
    "sessionid": 0.85,
    "session_id": 0.85,
    "jsessionid": 0.85,
    "phpsessid": 0.85,
    "auth_token": 0.8,
    "access_token": 0.75,
}

PLAINTEXT_HOST_PATTERN = re.compile(r"^http://", re.IGNORECASE)


class MobileTransportReasoner(BaseReasoner):
    """Analyzes endpoints for mobile transport-security weaknesses."""

    @property
    def vulnerability_type(self) -> str:
        return "mobile_transport"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST", "PUT", "PATCH", "DELETE"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        # ── Signal 1: plain-HTTP host ──────────────────────────────
        host = (endpoint.host or "").strip()
        if host and PLAINTEXT_HOST_PATTERN.match(host):
            signals.append(f"Plain-HTTP host: {host} (mobile traffic interceptable on open networks)")
            params_of_interest.append("host")
            confidence += 0.6

        # ── Signal 2: session identifiers in URL path ──────────────
        path_parts = [p for p in endpoint.path.split("/") if p]
        for part in path_parts:
            score = SESSION_IN_PATH_KEYWORDS.get(part.lower(), 0.0)
            if score:
                signals.append(f"Session material in URL path segment: {part} (cached by proxies/CDN)")
                params_of_interest.append(part)
                confidence += score * 0.35

        # ── Signal 3: session/auth tokens in query string ──────────
        for qp in endpoint.query_params:
            score = SESSION_IN_QUERY_KEYWORDS.get(qp, SESSION_IN_QUERY_KEYWORDS.get(qp.lower(), 0.0))
            if score:
                signals.append(f"Auth/session token in query string: {qp} (Referer + proxy log leakage)")
                if qp not in params_of_interest:
                    params_of_interest.append(qp)
                confidence += score * 0.3

        # ── Signal 4: auth endpoints without token binding hints ───
        # Login/token endpoints over mobile networks are the highest-value
        # MiTM targets; flag them for pinning verification.
        path_lower = endpoint.path.lower()
        if endpoint.method.upper() == "POST" and any(
            k in path_lower for k in ("login", "token", "oauth", "auth", "session")
        ):
            signals.append("Auth/token endpoint used by mobile clients — verify certificate pinning on-device")
            confidence += 0.2

        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        return [
            Hypothesis(
                vulnerability_type="mobile_transport",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=self._compute_severity(confidence, signals),
                summary=f"Potential mobile transport weakness ({', '.join(params_of_interest[:3])}) on "
                f"{endpoint.method} {endpoint.path}",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} exposes transport-layer "
                    f"weakness relevant to mobile clients ({', '.join(params_of_interest[:4])}): "
                    f"mobile apps routinely operate on hostile networks where cleartext traffic, "
                    f"cached URLs, and logged query strings become credential theft. Session "
                    f"material in URLs is additionally stored by proxies, CDNs, and analytics."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because mobile MiTM is cheap (rogue "
                    f"hotspot + proxy) and transport flaws convert directly into session "
                    f"hijack. {len(signals)} indicators here."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    "Route a test device through an intercepting proxy with a custom CA: "
                    "if traffic flows, certificate pinning is absent or bypassable.",
                    f"Replay {endpoint.method} {endpoint.path} over plain HTTP (if the host "
                    "allows it) and confirm credentials traverse in cleartext.",
                    "Check Referer headers, CDN logs, and analytics beacons for the flagged query/path values.",
                ],
                alternative_explanations=[
                    {
                        "label": "https_enforced",
                        "description": "Server redirects all HTTP to HTTPS with HSTS and the flagged host is legacy.",
                        "how_to_rule_out": "Request the HTTP variant and confirm 301 + HSTS header.",
                    },
                    {
                        "label": "short_lived_tokens",
                        "description": "Tokens in URLs are single-use and expire in seconds.",
                        "how_to_rule_out": "Replay a captured token after 60 seconds.",
                    },
                ],
                scope_check=(
                    f"Verify that {endpoint.path} is within the program's scope. "
                    f"MiTM testing only against your own test device and accounts."
                ),
                reproducibility_notes=(
                    "Capture the same request twice through the proxy; deterministic "
                    "appearance of session material in URLs confirms the finding."
                ),
            )
        ]

    def _compute_severity(self, confidence: float, signals: list[str]) -> str:
        joined = " ".join(signals).lower()
        if "plain-http" in joined:
            return "high" if confidence >= 0.4 else "medium"
        if confidence >= 0.7:
            return "high"
        if confidence >= 0.4:
            return "medium"
        return "low"
