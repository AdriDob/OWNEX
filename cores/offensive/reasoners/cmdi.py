"""CMDI Reasoner — Command Injection (RCE-level).

Detecta superficies donde la entrada del usuario llega a una shell del sistema:
exec(), system(), popen(), subprocess, backticks, eval() en bash, etc.

Seguridad por construcción: pruebas pasivas de eco y delay acotado (sin DoS).
Solo objetivos autorizados o laboratorio propio.
"""

from __future__ import annotations

import logging

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner
from cores.offensive.templates import CMDI_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.cmdi")

# Fragmentos de path que sugieren endpoint de ejecución de comandos
CMDI_PATHS: dict[str, float] = {
    "/exec": 0.9,
    "/execute": 0.85,
    "/run": 0.7,
    "/cmd": 0.8,
    "/command": 0.75,
    "/shell": 0.85,
    "/terminal": 0.6,
    "/api/exec": 0.9,
    "/api/run": 0.8,
    "/debug/exec": 0.7,
    "/admin/exec": 0.8,
    "/tools/exec": 0.65,
}

# Claves de body/query que suelen llevar comandos de shell
CMDI_KEYS: dict[str, float] = {
    "cmd": 0.95,
    "command": 0.95,
    "exec": 0.9,
    "execute": 0.85,
    "run": 0.7,
    "shell": 0.85,
    "code": 0.6,
    "script": 0.65,
    "payload": 0.5,
    "cmdline": 0.75,
    "commandline": 0.7,
    "args": 0.5,
    "arguments": 0.45,
}

# Patrones de eco seguros para confirmar inyección (math, no side effects)
SAFE_ECHO_PROBES = [
    ("echo", "echo {{RAND}}", "{{RAND}}"),
    ("printf", "printf '%s' '{{RAND}}'", "{{RAND}}"),
    ("expr", "expr {{A}} + {{B}}", None),  # resultado calculado
]

MAX_SAFE_DELAY = 3  # segundos máximo para time-based (anti-DoS)


class CMDIReasoner(BaseReasoner):
    """Analiza endpoints para inyección de comandos (RCE)."""

    @property
    def vulnerability_type(self) -> str:
        return "cmdi"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST", "PUT", "PATCH"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        path_lower = (endpoint.path or "").lower()
        for frag, score in CMDI_PATHS.items():
            if frag in path_lower:
                signals.append(f"CMDI endpoint path: {frag}")
                confidence += score * 0.4

        blob_keys = [str(k) for k in (endpoint.body or {})]
        blob_keys += list(endpoint.query_params)
        lowered = {k.lower(): k for k in blob_keys}
        for low, orig in lowered.items():
            if low in CMDI_KEYS:
                signals.append(f"Command injection key: {orig}")
                params_of_interest.append(orig)
                confidence += CMDI_KEYS[low] * 0.35

        # Detectar patrones de shell en valores existentes (heurística pasiva)
        for bk, bv in (endpoint.body or {}).items():
            if isinstance(bv, str) and any(p in bv for p in ["$(", "`", "&&", "||", ";", "|", ">"]):
                signals.append(f"Shell metacharacters in {bk} value")
                confidence += 0.15
                if bk not in params_of_interest:
                    params_of_interest.append(bk)

        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        severity = "critical" if confidence >= 0.7 else ("high" if confidence >= 0.4 else "medium")

        return [
            Hypothesis(
                vulnerability_type="cmdi",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=severity,
                summary=f"Potential command injection via {', '.join(params_of_interest[:3])} on {endpoint.method} {endpoint.path}",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} accepts parameters "
                    f"({', '.join(params_of_interest[:4])}) that may reach a system shell. "
                    f"Command injection yields direct RCE and pays Critical in most programs."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because {endpoint.method} "
                    f"{endpoint.path} has {len(signals)} CMDI indicators and pays $10k-50k+. "
                    f"RCE is the highest-impact class in bug bounty."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    "Confirm scope covers command injection testing before sending any payload.",
                    "Send a benign math probe: expr 7 + 5 and verify literal 12 in response (no execution = safe).",
                    "Test time-based delay with sleep 1 (max 3s). Observe latency increase without DoS.",
                    "Try echo {{RAND}} and verify random string reflects literally (no shell expansion).",
                    "If math probe evaluates OR sleep delays OR echo expands — save request/response as PoC.",
                    "Stop at first proof. Test ONLY authorized targets or your own lab.",
                ],
                alternative_explanations=[
                    {"label": a["label"], "description": a["description"], "how_to_rule_out": a["how_to_rule_out"]}
                    for a in CMDI_ALTERNATIVES.get("cmdi", [])
                ],
                scope_check=(
                    f"Verify {endpoint.path} is in scope and command injection testing is allowed. "
                    f"Keep probes cheap and few; stop at first proof. Test ONLY "
                    f"authorized targets or your own lab."
                ),
                reproducibility_notes=(
                    "Fixed benign probes, fresh session per run. Same evaluation/delay twice = reproducible."
                ),
            )
        ]
