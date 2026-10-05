"""Deserialization/SSTI Reasoner — RCE directo por plantillas y objetos.

Detecta superficie de deserialización insegura y Server-Side Template
Injection: parámetros que llegan a motores de plantillas (Jinja2, Twig,
Freemarker, ERB, Velocity) o a deserializadores (pickle, yaml, PHP, Java).
Es la franja $10-30k: RCE sin interacción.

Seguridad por construcción: análisis estático de nombres; las instrucciones
usan payloads benignos de detección (aritmética, sin exfiltración, sin
escritura). Solo objetivos autorizados o laboratorio propio.
"""

from __future__ import annotations

import logging

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner
from cores.offensive.templates import DESERIALIZATION_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.deserialization")

# Motores de plantilla server-side por nombre/parámetro visible
TEMPLATE_ENGINES: dict[str, float] = {
    "jinja": 0.9,
    "jinja2": 0.95,
    "twig": 0.9,
    "freemarker": 0.85,
    "velocity": 0.85,
    "erb": 0.85,
    "ejs": 0.8,
    "handlebars": 0.7,
    "mustache": 0.65,
    "smarty": 0.8,
    "blade": 0.7,
    "template": 0.6,
}

# Sinks que solo cuentan si hay señal de motor en la superficie (evita ruido
# en endpoints CRUD comunes: /api/users?name=...).
WEAK_SINK_PARAMS: dict[str, float] = {
    "template": 0.85,
    "view": 0.6,
    "page": 0.5,
    "layout": 0.7,
    "theme": 0.65,
    "name": 0.55,
    "message": 0.5,
    "title": 0.5,
    "body": 0.5,
    "content": 0.55,
}

# Sinks que son estructura de deserialización por sí mismos: no necesitan
# otra señal para justificar la hipótesis.
STRONG_SINK_PARAMS: dict[str, float] = {
    "data": 0.6,
    "object": 0.7,
    "payload": 0.75,
    "state": 0.6,
}

# Formatos/keywords de deserialización
DESER_HINTS: dict[str, float] = {
    "pickle": 0.95,
    "yaml": 0.8,
    "marshal": 0.85,
    "serialize": 0.8,
    "unserialize": 0.9,
    "deserialize": 0.9,
    "objectinputstream": 0.9,
    "base64": 0.6,
}


def _has_template_signal(blob: str) -> bool:
    """¿Hay señal de motor de plantilla o deserializador en la superficie?"""
    return any(f in blob for f in TEMPLATE_ENGINES) or any(h in blob for h in DESER_HINTS)


class DeserializationReasoner(BaseReasoner):
    """Analiza superficie SSTI/deserialización con payloads benignos."""

    @property
    def vulnerability_type(self) -> str:
        return "deserialization"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST", "PUT", "PATCH"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        blob = f"{endpoint.path} {' '.join(endpoint.query_params)}"
        if endpoint.body:
            blob += " " + " ".join(str(k) for k in endpoint.body)
        low = blob.lower()

        for frag, score in TEMPLATE_ENGINES.items():
            if frag in low:
                signals.append(f"Template engine visible: {frag}")
                # El motor expuesto ES la señal: puede no haber un sink clásico.
                if frag not in params_of_interest:
                    params_of_interest.append(frag)
                confidence += score * 0.4

        has_template = _has_template_signal(low)
        candidates = list(endpoint.query_params) + list(endpoint.path_params)
        if endpoint.body:
            candidates += [str(k) for k in endpoint.body]

        for name in candidates:
            key = name.lower()
            if key in STRONG_SINK_PARAMS:
                signals.append(f"Deserialization sink parameter: {name}")
                params_of_interest.append(name)
                confidence += STRONG_SINK_PARAMS[key] * 0.35
            elif key in WEAK_SINK_PARAMS and has_template:
                signals.append(f"Template sink parameter: {name}")
                params_of_interest.append(name)
                confidence += WEAK_SINK_PARAMS[key] * 0.3
            if key in DESER_HINTS:
                signals.append(f"Deserialization keyword as parameter: {name}")
                if name not in params_of_interest:
                    params_of_interest.append(name)
                confidence += DESER_HINTS[key] * 0.35

        for hint, score in DESER_HINTS.items():
            if hint in low and hint not in {c.lower() for c in candidates}:
                signals.append(f"Deserialization keyword in surface: {hint}")
                if hint not in params_of_interest:
                    params_of_interest.append(hint)
                confidence += score * 0.2

        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        severity = "high" if confidence >= 0.6 else ("medium" if confidence >= 0.35 else "low")

        return [
            Hypothesis(
                vulnerability_type="deserialization",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=severity,
                summary=f"Potential SSTI/deserialization via {', '.join(params_of_interest[:3])} "
                f"on {endpoint.method} {endpoint.path}",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} reflects caller input "
                    f"({', '.join(params_of_interest[:4])}) into what looks like template "
                    f"rendering or object deserialization. Server-Side Template Injection "
                    f"and insecure deserialization lead straight to RCE — the $10-30k band."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because {endpoint.method} "
                    f"{endpoint.path} feeds {params_of_interest[0] if params_of_interest else 'input'} "
                    f"into a template/deserializer ({len(signals)} indicators). One benign "
                    f"math payload distinguishes SSTI from RCE path in minutes."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    "Confirm scope; use ONLY benign detection payloads (arithmetic).",
                    "Try a math probe first (e.g., 7*7 in template syntax): rendered '49' = SSTI.",
                    "If SSTI confirmed, escalate stepwise toward object access — never exfiltrate "
                    "or write files on targets you do not own.",
                    "For deserialization: send type-tagged benign objects and watch for "
                    "class instantiation errors (info leak, not exploitation).",
                    "Benign arithmetic rendered or class instantiated = PoC. Stop there and report.",
                ],
                alternative_explanations=[
                    {"label": a["label"], "description": a["description"], "how_to_rule_out": a["how_to_rule_out"]}
                    for a in DESERIALIZATION_ALTERNATIVES.get("deserialization", [])
                ],
                scope_check=(
                    f"Verify {endpoint.path} is in scope. Benign payloads only; no file "
                    f"writes, no exfiltration, no persistence. Test ONLY authorized "
                    f"targets or your own lab."
                ),
                reproducibility_notes=(
                    "Fixed benign math payload, fresh session per run. Same rendered result twice = reproducible."
                ),
            )
        ]
