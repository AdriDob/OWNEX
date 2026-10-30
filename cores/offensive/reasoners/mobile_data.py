"""Mobile Data Exposure Reasoner — detects server-visible signs of insecure
mobile data handling.

Analyzes API endpoints for patterns indicating the mobile client (or its
traffic) exposes sensitive data: secrets in query strings, PII in GET
parameters, debug/verbose flags, and backup/export endpoints reachable
without extra protection.

Honest scope: this reasoner sees HTTP traffic shapes, not the device. It
cannot inspect Keychain/Keystore/SharedPreferences directly. It flags the
server-visible half of insecure storage: credentials and PII that travel
in URLs, logs, and backups — exactly what makes client-side storage flaws
exploitable at scale.
"""

from __future__ import annotations

import logging

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner

logger = logging.getLogger("orion.core.offensive.reasoners.mobile_data")

# Secrets that must never appear in URLs (query strings end up in logs,
# history, analytics, and crash reports — all readable on a device)
SECRET_PARAM_KEYWORDS: dict[str, float] = {
    "api_key": 0.95,
    "apikey": 0.95,
    "api_secret": 0.95,
    "secret": 0.9,
    "client_secret": 0.95,
    "password": 0.95,
    "passwd": 0.9,
    "pwd": 0.85,
    "auth_token": 0.95,
    "authtoken": 0.95,
    "access_token": 0.9,
    "refresh_token": 0.9,
    "session_token": 0.9,
    "private_key": 0.95,
    "encryption_key": 0.9,
}

# PII that is high-risk in GET/query parameters
PII_PARAM_KEYWORDS: dict[str, float] = {
    "ssn": 0.95,
    "social_security": 0.9,
    "credit_card": 0.95,
    "card_number": 0.9,
    "cvv": 0.95,
    "pin": 0.85,
    "email": 0.55,
    "phone": 0.6,
    "phone_number": 0.65,
    "address": 0.6,
    "date_of_birth": 0.7,
    "dob": 0.65,
    "passport": 0.8,
    "license": 0.6,
    "biometric": 0.85,
    "fingerprint": 0.8,
}

# Debug/verbose flags that widen exposure on mobile builds
DEBUG_PARAM_KEYWORDS: dict[str, float] = {
    "debug": 0.7,
    "verbose": 0.65,
    "trace": 0.65,
    "log_level": 0.6,
    "dump": 0.75,
    "export_logs": 0.7,
}

# Backup/export path segments (mobile backup extraction surface)
EXPORT_PATH_KEYWORDS: dict[str, float] = {
    "backup": 0.8,
    "export": 0.75,
    "dump": 0.8,
    "sync": 0.55,
    "restore": 0.7,
    "download-all": 0.7,
}


class MobileDataExposureReasoner(BaseReasoner):
    """Analyzes endpoints for mobile data-exposure patterns."""

    @property
    def vulnerability_type(self) -> str:
        return "mobile_data_exposure"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST", "PUT"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        # ── Signal 1: secrets in query string (GET) ────────────────
        if endpoint.method.upper() == "GET":
            for qp in endpoint.query_params:
                score = SECRET_PARAM_KEYWORDS.get(qp, SECRET_PARAM_KEYWORDS.get(qp.lower(), 0.0))
                if score:
                    signals.append(f"Secret travels in URL query parameter: {qp} (cached/logged on device)")
                    params_of_interest.append(qp)
                    confidence += score * 0.4

        # ── Signal 2: PII in query string ──────────────────────────
        for qp in endpoint.query_params:
            score = PII_PARAM_KEYWORDS.get(qp, PII_PARAM_KEYWORDS.get(qp.lower(), 0.0))
            if score:
                signals.append(f"PII in URL query parameter: {qp}")
                if qp not in params_of_interest:
                    params_of_interest.append(qp)
                confidence += score * (0.35 if endpoint.method.upper() == "GET" else 0.2)

        # ── Signal 3: debug/verbose flags ──────────────────────────
        for name in list(endpoint.query_params) + list(endpoint.path_params):
            score = DEBUG_PARAM_KEYWORDS.get(name, DEBUG_PARAM_KEYWORDS.get(name.lower(), 0.0))
            if score:
                val = endpoint.params.get(name, "")
                if str(val).lower() in ("true", "1", "yes", "debug", "verbose"):
                    signals.append(f"Debug mode switch exposed: {name}={val}")
                    params_of_interest.append(name)
                    confidence += score * 0.3

        # ── Signal 4: backup/export endpoints ──────────────────────
        path_parts = [p for p in endpoint.path.split("/") if p]
        for part in path_parts:
            score = EXPORT_PATH_KEYWORDS.get(part.lower(), 0.0)
            if score:
                signals.append(f"Bulk data endpoint reachable: {part} (mobile backup extraction risk)")
                params_of_interest.append(part)
                confidence += score * 0.3

        # ── Signal 5: secrets anywhere in parameters (weaker) ──────
        for name in endpoint.query_params:
            if name not in params_of_interest:
                score = SECRET_PARAM_KEYWORDS.get(name.lower(), 0.0)
                if score:
                    signals.append(f"Secret-like parameter: {name}")
                    params_of_interest.append(name)
                    confidence += score * 0.2

        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        return [
            Hypothesis(
                vulnerability_type="mobile_data_exposure",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=self._compute_severity(confidence, params_of_interest),
                summary=f"Potential mobile data exposure via {', '.join(params_of_interest[:3])} on "
                f"{endpoint.method} {endpoint.path}",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} moves sensitive values "
                    f"({', '.join(params_of_interest[:4])}) through channels that persist on "
                    f"mobile devices: URL query strings land in logs, history, analytics, and "
                    f"crash reports; bulk endpoints feed device backups. Any other app, backup "
                    f"extraction, or log reader on the device can recover them."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because on-device data exposure turns "
                    f"every other mobile flaw (backup theft, log leakage, malicious keyboard/VPN) "
                    f"into credential/PII compromise. {len(signals)} indicators here."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    f"Send {endpoint.method} {endpoint.path} and inspect whether {params_of_interest[0]} "
                    f"is required in the URL (vs body/header) — URL placement confirms exposure.",
                    "Check server access logs, error pages, and analytics beacons for the value in cleartext.",
                    "On a test device: trigger the call, then pull logcat/syslog and app backups for the value.",
                ],
                alternative_explanations=[
                    {
                        "label": "short_lived_low_value",
                        "description": "The value is short-lived and low-impact (e.g., CSRF token).",
                        "how_to_rule_out": "Check token lifetime and what it authorizes.",
                    },
                    {
                        "label": "masked_logging",
                        "description": "Server redacts the parameter in all logs and error output.",
                        "how_to_rule_out": "Force an error with the parameter and inspect the output.",
                    },
                ],
                scope_check=(
                    f"Verify that {endpoint.path} is within the program's scope. "
                    f"Use only test accounts; never exfiltrate other users' data."
                ),
                reproducibility_notes=(
                    "Repeat the request and confirm the sensitive value appears in the URL "
                    "or response deterministically across sessions."
                ),
            )
        ]

    def _compute_severity(self, confidence: float, params: list[str]) -> str:
        joined = " ".join(params).lower()
        if any(k in joined for k in ("password", "private_key", "api_key", "secret", "ssn", "credit_card")):
            return "high" if confidence >= 0.4 else "medium"
        if confidence >= 0.7:
            return "high"
        if confidence >= 0.4:
            return "medium"
        return "low"
