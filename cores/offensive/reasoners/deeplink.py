"""Deep Link Hijack Reasoner — detects mobile deep-link attack surface.

Analyzes the server-visible API surface used by mobile clients for deep-link
handling patterns: custom schemes, unvalidated redirect/host parameters, and
sensitive tokens passed through link parameters.

Honest scope: this reasoner sees HTTP endpoints, not the app binary. It flags
server-side link-handling weaknesses (open redirects via deep-link params,
auth codes in URLs, missing host validation signals). Client-side manifest
analysis (exported activities, intent filters) is out of scope.
"""

from __future__ import annotations

import logging
import re

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner

logger = logging.getLogger("orion.core.offensive.reasoners.deeplink")

# Deep-link / redirect parameter names — higher = more hijack-prone
LINK_PARAM_KEYWORDS: dict[str, float] = {
    # Custom scheme / link plumbing
    "scheme": 0.8,
    "deeplink": 0.9,
    "deep_link": 0.9,
    "deepLink": 0.9,
    "universal_link": 0.85,
    "applink": 0.85,
    "app_link": 0.85,
    "intent": 0.75,
    "intent_uri": 0.8,
    # Redirect / navigation targets (open-redirect primitive)
    "redirect": 0.8,
    "redirect_uri": 0.9,
    "redirect_url": 0.9,
    "callback": 0.8,
    "callback_url": 0.85,
    "return_to": 0.75,
    "return_url": 0.8,
    "next": 0.6,
    "url": 0.55,
    "target_url": 0.75,
    "continue": 0.6,
    # Sensitive values that must never travel in links
    "auth_code": 0.95,
    "authcode": 0.95,
    "code": 0.6,
    "token": 0.85,
    "access_token": 0.95,
    "id_token": 0.9,
    "session": 0.8,
    "session_id": 0.85,
}

# Path segments suggesting deep-link handling endpoints
LINK_PATH_KEYWORDS: dict[str, float] = {
    "deeplink": 0.9,
    "deep-link": 0.9,
    "applink": 0.85,
    "universal-link": 0.85,
    "redirect": 0.8,
    "callback": 0.8,
    "oauth": 0.7,
    "authorize": 0.7,
    "invite": 0.65,
    "share": 0.6,
    "open": 0.5,
}

SCHEME_PATTERN = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
MOBILE_UA_PATTERN = re.compile(r"android|iphone|ipad|ios|dalvik|cfnetwork|okhttp|alamofire", re.IGNORECASE)


class DeepLinkReasoner(BaseReasoner):
    """Analyzes endpoints for mobile deep-link hijack patterns."""

    @property
    def vulnerability_type(self) -> str:
        return "deeplink_hijack"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        # ── Signal 1: link-handling path segments ──────────────────
        path_parts = [p for p in endpoint.path.split("/") if p]
        for part in path_parts:
            score = LINK_PATH_KEYWORDS.get(part.lower(), 0.0)
            if score:
                signals.append(f"Path suggests deep-link handling: {part}")
                params_of_interest.append(part)
                confidence += score * 0.35

        # ── Signal 2: link/redirect parameters ─────────────────────
        for name in list(endpoint.query_params) + list(endpoint.path_params):
            score = LINK_PARAM_KEYWORDS.get(name, LINK_PARAM_KEYWORDS.get(name.lower(), 0.0))
            if score:
                signals.append(f"Deep-link parameter: {name}")
                params_of_interest.append(name)
                confidence += score * 0.3
                val = endpoint.params.get(name, "")
                if val and SCHEME_PATTERN.match(val):
                    signals.append(f"Custom scheme value in {name}: {val[:40]}")
                    confidence += 0.2

        # ── Signal 3: sensitive values in link-reachable params ────
        sensitive = {"auth_code", "authcode", "token", "access_token", "id_token", "session", "session_id"}
        for name in endpoint.query_params:
            if name.lower() in sensitive:
                signals.append(f"Sensitive value travels in URL parameter: {name} (leaks via link/logs)")
                confidence += 0.25

        # ── Signal 4: mobile client indicators ─────────────────────
        ua = " ".join(endpoint.headers.values())
        if ua and MOBILE_UA_PATTERN.search(ua):
            signals.append("Mobile client indicators in headers (deep links reachable from app)")
            confidence += 0.15

        # ── Signal 5: body link parameters (POST handlers) ─────────
        if endpoint.body:
            for key in endpoint.body:
                score = LINK_PARAM_KEYWORDS.get(key, LINK_PARAM_KEYWORDS.get(str(key).lower(), 0.0))
                if score:
                    signals.append(f"Body contains link parameter: {key}")
                    params_of_interest.append(str(key))
                    confidence += score * 0.2

        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        return [
            Hypothesis(
                vulnerability_type="deeplink_hijack",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=self._compute_severity(confidence),
                summary=f"Potential deep-link hijack via {', '.join(params_of_interest[:3])} on "
                f"{endpoint.method} {endpoint.path}",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} handles parameters "
                    f"({', '.join(params_of_interest[:4])}) typical of mobile deep-link flows. "
                    f"If redirect targets or auth values in these parameters are not validated "
                    f"against an allowlist, a malicious app or link can hijack the flow "
                    f"(open redirect, auth-code theft, account takeover)."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because deep-link handlers are a "
                    f"top mobile account-takeover primitive: {len(signals)} indicators here, "
                    f"and a single unvalidated redirect/token parameter is enough for impact."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    f"Send {endpoint.method} {endpoint.path} with {params_of_interest[0]} pointing "
                    f"to an attacker-controlled host/scheme and observe whether it is accepted.",
                    "For auth-code/token params: check if the value leaks into redirects, logs, or Referer headers.",
                    "On Android/iOS: verify whether the OS disambiguates the link target "
                    "(verified applinks/universal links) or any app can claim it.",
                ],
                alternative_explanations=[
                    {
                        "label": "validated_allowlist",
                        "description": "Redirect targets are validated against a strict allowlist.",
                        "how_to_rule_out": "Submit a non-allowlisted host and confirm rejection.",
                    },
                    {
                        "label": "no_sensitive_flow",
                        "description": "The parameters drive navigation only, never auth/session state.",
                        "how_to_rule_out": "Trace whether the params influence tokens or sessions.",
                    },
                ],
                scope_check=(
                    f"Verify that {endpoint.path} is within the program's scope. "
                    f"Deep-link testing must not involve other users' accounts or devices."
                ),
                reproducibility_notes=(
                    "Replay the request with a controlled redirect target twice; "
                    "consistent acceptance across sessions confirms the finding."
                ),
            )
        ]

    def _compute_severity(self, confidence: float) -> str:
        if confidence >= 0.7:
            return "high"
        if confidence >= 0.4:
            return "medium"
        return "low"
