"""Playbooks de IA para hunting (F4) — JS-diff + redacción de reportes.

Metodología explícita que el copiloto no tiene hoy: dos flujos que la
humanidad tarda horas y un modelo hace en minutos.

- `js_diff_analysis(js, baseline_js=None)`: extrae endpoints/params nuevos de
  un bundle y marca los que no existían (primicia = menos duplicados).
- `report_draft(finding, platform)`: esqueleto de reporte con impacto de
  negocio cuantificado, siguiendo el formato que pagan las plataformas.

Puro (sin red, sin LLM): el modelo recibe el resultado y lo enriquece. Los
datos siempre vienen del finding real; nada se inventa.
"""

from __future__ import annotations

import re
from typing import Any

# ── F4.1: JS diffing (primicia) ───────────────────────────────────

_JS_ROUTES = (
    re.compile(r"""fetch\(\s*["'`]([^"'`\s]{2,200})["'`]"""),
    re.compile(r"""axios\.(?:get|post|put|patch|delete)\(\s*["'`]([^"'`\s]{2,200})["'`]"""),
    re.compile(
        r"""["'`](/(?:api|v\d|graphql|gql|internal|admin|auth|oauth|callback|beta|webhooks?)[^"'`\s]{0,180})["'`]"""
    ),
)

_JS_PARAMS = (
    re.compile(r"""["'`]([a-zA-Z_][a-zA-Z0-9_]{2,40})["'`]\s*:\s*\{?[a-zA-Z0-9_."'\[\]]*\}?"""),
    re.compile(r"""\b(?:var|let|const)\s+([a-zA-Z_][a-zA-Z0-9_]{2,40})\s*="""),
    re.compile(r"""\b([a-zA-Z_][a-zA-Z0-9_]{2,40})\s*=\s*["'`]"""),
)

_BETA = ("beta", "preview", "staging", "internal", "alpha", "v2", "v3", "debug")
_SENSITIVE = ("token", "secret", "apikey", "api_key", "password", "credential", "s3nse", "aws", "bearer")


def _js_routes(js: str) -> set[str]:
    out: set[str] = set()
    for rx in _JS_ROUTES:
        for m in rx.findall(js or ""):
            if m:
                out.add(m)
    return out


def _js_params(js: str) -> set[str]:
    out: set[str] = set()
    for rx in _JS_PARAMS:
        for m in rx.findall(js or ""):
            if m:
                out.add(m)
    return out


def js_diff_analysis(js: str, baseline_js: str | None = None) -> dict[str, Any]:
    """Rutas y params de un bundle; con baseline, marca lo NUEVO (primicia).

    Sin baseline: primer snapshot, nada es "nuevo" todavía (honesto: la
    primera vuelta no diferencia deltas, igual que el change monitor).
    """
    routes = _js_routes(js)
    params = _js_params(js)
    result: dict[str, Any] = {
        "total_routes": len(routes),
        "total_params": len(params),
        "new_routes": [],
        "new_params": [],
        "beta_like_routes": sorted(r for r in routes if any(b in r.lower() for b in _BETA)),
        "sensitive_hits": sorted(p for p in params if any(s in p.lower() for s in _SENSITIVE)),
        "top_routes": sorted(routes)[:25],
        "is_first_snapshot": baseline_js is None,
    }
    if baseline_js is not None:
        old_routes = _js_routes(baseline_js)
        old_params = _js_params(baseline_js)
        result["new_routes"] = sorted(routes - old_routes)[:25]
        result["new_params"] = sorted(params - old_params)[:25]
        result["is_first_snapshot"] = False
    return result


# ── F4.2: borrador de reporte con impacto de negocio ─────────────

_SEVERITY_IMPACT = {
    "critical": "allows una Actions on Production Systems / full compromise",
    "high": "allows una Actions on Production Systems at scale",
    "medium": "requires additional conditions or limited scope",
    "low": "limited impact without user interaction",
    "informational": "no direct impact, hardening observation",
}

_PLATFORM_HINTS = {
    "hackerone": "CWE + CVSS v4 + asset + step-by-step PoC (curl) + safe-harbor note",
    "bugcrowd": "VRT class + CVSS + priority justification + exact asset",
    "intigriti": "tags + CVSS v4 + reproducible steps + remediation",
}


def report_draft(finding: dict[str, Any], platform: str = "hackerone") -> dict[str, Any]:
    """Esqueleto de reporte: nunca inventa, ordena lo que el finding tiene."""
    out: dict[str, Any] = {
        "platform": platform,
        "platform_requirements": _PLATFORM_HINTS.get(platform.lower(), "CWE + CVSS + PoC + impact"),
        "missing": [],
    }
    title = str(finding.get("title", "") or "").strip()
    out["title"] = title
    if not title:
        out["missing"].append("title")

    vuln_type = str(finding.get("vulnerability_type", "") or "").strip()
    endpoint = str(finding.get("endpoint", "") or "").strip()
    out["vulnerability_type"] = vuln_type or "UNKNOWN"
    out["endpoint"] = endpoint or "UNKNOWN"
    if not vuln_type:
        out["missing"].append("vulnerability_type")

    steps = finding.get("reproduction_steps", []) or finding.get("test_instructions", []) or []
    out["reproduction_steps"] = [str(s) for s in steps][:12]
    if len(out["reproduction_steps"]) < 3:
        out["missing"].append("reproduction_steps<3")

    poc = finding.get("poc", {}) or {}
    curl = poc.get("curl", "") if isinstance(poc, dict) else str(poc)
    out["poc_curl"] = curl
    if not curl:
        out["missing"].append("poc_curl")

    evidence = finding.get("evidence", []) or []
    out["evidence"] = [str(e) for e in evidence][:8]
    if not out["evidence"]:
        out["missing"].append("evidence")

    severity = str(finding.get("severity", "") or "").lower() or "unknown"
    out["severity"] = severity
    out["cwe_id"] = str(finding.get("cwe_id", "") or "")
    out["cvss_score"] = finding.get("cvss_score", finding.get("cvss", 0)) or 0
    if not out["cwe_id"]:
        out["missing"].append("cwe_id")

    impact = str(finding.get("business_impact", finding.get("impact", "")) or "").strip()
    out["impact_statement"] = impact
    out["impact_frame"] = _SEVERITY_IMPACT.get(severity, "")
    if not impact:
        out["missing"].append("impact/business_impact")
    elif severity in ("high", "critical") and not any(
        k in impact.lower()
        for k in (
            "all",
            "any",
            "every",
            "entire",
            "mass",
            "database",
            "production",
            "financial",
            "pii",
            "record",
            "user",
        )
    ):
        out["missing"].append("impact_scale: quantify users/records/scope")

    out["remediation"] = str(finding.get("remediation", "") or "")
    if not out["remediation"]:
        out["missing"].append("remediation")

    out["ready_to_send"] = not out["missing"]
    out["note"] = "Borrador: completa lo que falte antes de enviar. Human Gate decide."
    return out
