"""Generic Reasoner — Catch-all anomaly detector for unclassified endpoints.

Analiza endpoints que no matchean ningún tipo de vulnerabilidad específico,
buscando anomalías generales: parámetros inusuales, respuestas anómalas,
headers de seguridad faltantes, patrones de error, etc.

Seguridad por construcción: análisis estático + heurísticas pasivas.
Solo objetivos autorizados o laboratorio propio.
"""

from __future__ import annotations

import logging
import re

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner
from cores.offensive.templates import GENERIC_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.generic")

# Patrones de parámetros que sugieren superficie de ataque genérica
GENERIC_PARAM_PATTERNS = {
    # Parámetros de ID/referencia
    r"^(id|uuid|guid|ref|reference|key|token|secret|password|pass|pwd)$": 0.4,
    r".*(id|uuid|guid|ref|key|token|secret|password|pass|pwd)$": 0.3,
    # Parámetros de archivo/ruta
    r".*(file|path|url|link|redirect|next|return|callback|dest|target|goto).*": 0.35,
    # Parámetros de comando/ejecución
    r".*(cmd|command|exec|execute|run|shell|script|code|payload).*": 0.5,
    # Parámetros de debug/admin
    r".*(debug|test|admin|dev|internal|private|hidden|secret).*": 0.45,
    # Parámetros de serialización
    r".*(data|input|output|payload|body|content|message|json|xml|yaml).*": 0.25,
}

# Patrones de respuesta anómala
ANOMALY_RESPONSE_PATTERNS = {
    # Errores de servidor expuestos
    r"(stack trace|traceback|exception|error at|file \"|line \d+)": 0.5,
    # Info de versión/tecnología
    r"(server:|x-powered-by:|x-aspnet-version:|php/|apache/|nginx/)": 0.3,
    # Mensajes de debug
    r"(debug|trace|verbose|dump|var_dump|print_r|console\.log)": 0.35,
    # SQL errors
    r"(sql syntax|mysql|postgresql|ora-\d+|sqlite_|syntax error)": 0.6,
    # Path disclosure
    r"(/home/|/var/www|/opt/|/usr/local|C:\\|D:\\)": 0.5,
    # Auth bypass hints
    r"(unauthorized|forbidden|access denied|invalid token|expired token)": 0.25,
}

# Headers de seguridad esperados (su ausencia es anomalía)
SECURITY_HEADERS = {
    "x-frame-options": 0.3,
    "x-content-type-options": 0.25,
    "strict-transport-security": 0.3,
    "content-security-policy": 0.35,
    "referrer-policy": 0.2,
    "permissions-policy": 0.2,
}

# Métodos que mutan estado
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class GenericReasoner(BaseReasoner):
    """Detector de anomalías genéricas para endpoints no clasificados."""

    @property
    def vulnerability_type(self) -> str:
        return "generic"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        # 1. Análisis de parámetros sospechosos
        blob_keys = [str(k) for k in (endpoint.body or {})]
        blob_keys += list(endpoint.query_params)
        lowered = {k.lower(): k for k in blob_keys}

        for pattern, score in GENERIC_PARAM_PATTERNS.items():
            for low, orig in lowered.items():
                if re.search(pattern, low, re.IGNORECASE):
                    signals.append(f"Suspicious parameter pattern: {orig} (~{pattern})")
                    params_of_interest.append(orig)
                    confidence += score * 0.2

        # 2. Detección de muchos parámetros (posible surface amplio)
        if len(blob_keys) > 10:
            signals.append(f"High parameter count: {len(blob_keys)} parameters")
            confidence += 0.15

        # 3. Parámetros con valores largos (posible inyección/payload)
        for bk, bv in (endpoint.body or {}).items():
            if isinstance(bv, str) and len(bv) > 500:
                signals.append(f"Large payload in {bk} ({len(bv)} chars)")
                confidence += 0.2
                if bk not in params_of_interest:
                    params_of_interest.append(bk)

        # 4. Análisis de headers de respuesta (si hay sample)
        if endpoint.response_sample:
            resp = endpoint.response_sample
            headers = {k.lower(): v for k, v in (resp.get("headers") or {}).items()}
            body = resp.get("body", "") or ""
            status = resp.get("status", 0)

            # Headers de seguridad faltantes
            for hdr, score in SECURITY_HEADERS.items():
                if hdr not in headers:
                    signals.append(f"Missing security header: {hdr}")
                    confidence += score * 0.15

            # Patrones anómalos en body
            for pattern, score in ANOMALY_RESPONSE_PATTERNS.items():
                if re.search(pattern, body, re.IGNORECASE):
                    signals.append(f"Anomalous response pattern: {pattern}")
                    confidence += score * 0.2

            # Status codes inusuales
            if status in (500, 502, 503, 504):
                signals.append(f"Server error status: {status}")
                confidence += 0.3
            elif status == 403 and endpoint.method.upper() in MUTATING_METHODS:
                signals.append("403 on mutating endpoint - potential auth bypass surface")
                confidence += 0.25

        # 5. Path traversal patterns en path
        path_lower = (endpoint.path or "").lower()
        if re.search(r"\.\./|\.\.\\|%2e%2e%2f|%2e%2e/", path_lower):
            signals.append("Path traversal sequence in URL path")
            confidence += 0.4

        # 6. Endpoints de admin/debug expuestos
        admin_patterns = (
            "/admin",
            "/debug",
            "/test",
            "/dev",
            "/internal",
            "/actuator",
            "/health",
            "/metrics",
            "/.git",
            "/.env",
            "/config",
            "/backup",
        )
        if any(p in path_lower for p in admin_patterns):
            signals.append(f"Potential admin/debug endpoint: {endpoint.path}")
            confidence += 0.35

        if confidence < 0.15 or not signals:
            return []

        confidence = min(confidence, 1.0)
        severity = "medium" if confidence >= 0.4 else "low"

        return [
            Hypothesis(
                vulnerability_type="generic",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=severity,
                summary=f"Generic anomaly detected on {endpoint.method} {endpoint.path} ({len(signals)} signals)",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} exhibits {len(signals)} "
                    f"generic anomaly signals: {', '.join(signals[:3])}. "
                    f"These may indicate misconfiguration, information disclosure, "
                    f"or an attack surface not covered by specific vulnerability types."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because {endpoint.method} "
                    f"{endpoint.path} shows {len(signals)} anomaly signals that don't fit "
                    f"specific vulnerability classes but could indicate security issues. "
                    f"Generic anomalies often reveal novel attack vectors."
                ),
                parameters_of_interest=params_of_interest[:5],
                signals=signals,
                test_instructions=[
                    "Confirm scope covers generic anomaly testing.",
                    "Manually review the endpoint for each signal listed above.",
                    "Check for missing security headers using browser dev tools or curl -I.",
                    "Test parameter manipulation: send oversized payloads, special chars, path traversal.",
                    "Review response bodies for stack traces, version info, path disclosure.",
                    "Verify authentication/authorization on admin/debug endpoints.",
                    "Document any finding that doesn't fit standard vuln classes — it may be novel.",
                    "Test ONLY authorized targets or your own lab.",
                ],
                alternative_explanations=[
                    {"label": a["label"], "description": a["description"], "how_to_rule_out": a["how_to_rule_out"]}
                    for a in GENERIC_ALTERNATIVES.get("generic", [])
                ],
                scope_check=(
                    f"Verify {endpoint.path} is in scope. Generic anomaly testing is low-impact. "
                    f"Test ONLY authorized targets or your own lab."
                ),
                reproducibility_notes=(
                    "Same anomaly signals on repeated requests = reproducible. "
                    "Document exact parameter values and response patterns."
                ),
            )
        ]
