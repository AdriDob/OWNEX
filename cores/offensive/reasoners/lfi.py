"""LFI Reasoner — Local File Inclusion.

Detecta endpoints donde la entrada del usuario controla la ruta de un archivo
leído por el servidor (include, require, file_get_contents, readfile, fopen,
fread, open(), File.read, etc.).

Seguridad por construcción: solo rutas benignas conocidas, sin acceso a
datos sensibles. Solo objetivos autorizados o laboratorio propio.
"""

from __future__ import annotations

import logging

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner
from cores.offensive.templates import LFI_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.lfi")

# Fragmentos de path que sugieren lectura de archivos
LFI_PATHS: dict[str, float] = {
    "/file": 0.7,
    "/download": 0.75,
    "/read": 0.8,
    "/view": 0.7,
    "/preview": 0.65,
    "/display": 0.6,
    "/document": 0.6,
    "/template": 0.75,
    "/include": 0.85,
    "/load": 0.7,
    "/fetch": 0.65,
    "/getfile": 0.8,
    "/api/file": 0.75,
    "/api/download": 0.8,
    "/static/": 0.4,
    "/assets/": 0.3,
}

# Claves de body/query que suelen llevar rutas de archivo
LFI_KEYS: dict[str, float] = {
    "file": 0.95,
    "path": 0.9,
    "filename": 0.9,
    "filepath": 0.95,
    "document": 0.7,
    "template": 0.8,
    "page": 0.75,
    "view": 0.7,
    "include": 0.85,
    "load": 0.7,
    "src": 0.8,
    "source": 0.7,
    "url": 0.5,
    "link": 0.4,
    "resource": 0.5,
    "asset": 0.4,
    "doc": 0.6,
    "doc_id": 0.6,
    "document_id": 0.6,
}

# Rutas benignas conocidas para pruebas pasivas (existen en Linux/Unix estándar)
SAFE_READ_PROBES = [
    "/etc/passwd",  # lista usuarios, no secretos
    "/etc/hostname",  # hostname del sistema
    "/etc/os-release",  # info de distro
    "/proc/version",  # versión kernel
    "/proc/self/status",  # info del proceso actual
]

# Extensiones que delatan archivos estáticos (menos probables LFI)
STATIC_EXTS = (
    ".css",
    ".js",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".map",
)


class LFIReasoner(BaseReasoner):
    """Analiza endpoints para inclusión local de archivos."""

    @property
    def vulnerability_type(self) -> str:
        return "lfi"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        path_lower = (endpoint.path or "").lower()
        for frag, score in LFI_PATHS.items():
            if frag in path_lower:
                signals.append(f"LFI endpoint path: {frag}")
                confidence += score * 0.4

        blob_keys = [str(k) for k in (endpoint.body or {})]
        blob_keys += list(endpoint.query_params)
        lowered = {k.lower(): k for k in blob_keys}
        for low, orig in lowered.items():
            if low in LFI_KEYS:
                signals.append(f"File inclusion key: {orig}")
                params_of_interest.append(orig)
                confidence += LFI_KEYS[low] * 0.35

        # Filtrar extensiones estáticas obvias (bajan confianza)
        for bk, bv in (endpoint.body or {}).items():
            if isinstance(bv, str) and bv.lower().endswith(STATIC_EXTS):
                confidence *= 0.5
                signals.append(f"Static extension in {bk} lowers LFI likelihood")

        # Detectar path traversal patterns en valores existentes
        for bk, bv in (endpoint.body or {}).items():
            if isinstance(bv, str) and ("../" in bv or "..\\" in bv):
                signals.append(f"Path traversal sequence in {bk} value")
                confidence += 0.25
                if bk not in params_of_interest:
                    params_of_interest.append(bk)

        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        severity = "high" if confidence >= 0.5 else ("medium" if confidence >= 0.3 else "low")

        return [
            Hypothesis(
                vulnerability_type="lfi",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=severity,
                summary=f"Potential local file inclusion via {', '.join(params_of_interest[:3])} on {endpoint.method} {endpoint.path}",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} accepts parameters "
                    f"({', '.join(params_of_interest[:4])}) that may control file paths read by the server. "
                    f"LFI can leak source code, config, credentials, and escalate to RCE via log poisoning."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because {endpoint.method} "
                    f"{endpoint.path} has {len(signals)} LFI indicators. LFI pays $1k-10k+ "
                    f"and often chains to RCE via /proc/self/environ or log injection."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    "Confirm scope covers LFI testing before sending any payload.",
                    "Send a benign probe: /etc/passwd (standard Linux file, no secrets). Verify root:x:0:0 appears.",
                    "Try /etc/hostname and /proc/version — verify they reflect literally (no execution).",
                    "Test path traversal: ../../etc/passwd — only if base path is known subdirectory.",
                    "Do NOT attempt /etc/shadow, /root/.ssh/, or application config with secrets.",
                    "If benign probes return file contents — save request/response as PoC.",
                    "Stop at first proof. Test ONLY authorized targets or your own lab.",
                ],
                alternative_explanations=[
                    {"label": a["label"], "description": a["description"], "how_to_rule_out": a["how_to_rule_out"]}
                    for a in LFI_ALTERNATIVES.get("lfi", [])
                ],
                scope_check=(
                    f"Verify {endpoint.path} is in scope and file inclusion testing is allowed. "
                    f"Only benign standard files; no secrets. Test ONLY "
                    f"authorized targets or your own lab."
                ),
                reproducibility_notes=(
                    "Benign probes only (/etc/passwd, /etc/hostname). Same contents twice = reproducible."
                ),
            )
        ]
