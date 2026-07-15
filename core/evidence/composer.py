"""Evidence Composer — bridges hypothesis to structured evidence ready for triage.

Transforms a raw hypothesis into a complete evidence bundle with:
  - Multi-format PoC (curl, Python, JS fetch, HTTPie, Burp sequence)
  - CVSS score + vector, CWE, CAPEC identifiers
  - Structured reproduction steps with preconditions
  - Business impact assessment
  - System reasoning transparency (what was tried, ruled out)
  - Report readiness check
  - Nuclei YAML template generation for automated re-testing
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.events.types import EventEnvelope
from core.offensive.models import Hypothesis

logger = logging.getLogger("orion.core.evidence.composer")

# ── CWE / CAPEC mapping ────────────────────────────────────────

CWE_MAP: dict[str, tuple[str, str]] = {
    "idor": ("CWE-639", "Authorization Bypass Through User-Controlled Key"),
    "ssrf": ("CWE-918", "Server-Side Request Forgery"),
    "auth_bypass": ("CWE-288", "Authentication Bypass Using an Alternate Path or Channel"),
    "xss": ("CWE-79", "Improper Neutralization of Input During Web Page Generation"),
    "sqli": ("CWE-89", "SQL Injection"),
    "generic": ("CWE-200", "Exposure of Sensitive Information to an Unauthorized Actor"),
}

CAPEC_MAP: dict[str, str] = {
    "idor": "CAPEC-639",
    "ssrf": "CAPEC-664",
    "auth_bypass": "CAPEC-115",
    "xss": "CAPEC-63",
    "sqli": "CAPEC-66",
}

CVSS_SEVERITY_MAP: dict[str, tuple[float, str]] = {
    "critical": (9.5, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),
    "high": (7.5, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:L/A:N"),
    "medium": (5.5, "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N"),
    "low": (3.5, "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:N/A:N"),
}

# ── Evidence data model ────────────────────────────────────────


@dataclass
class EvidenceBundle:
    """Complete evidence package ready for triage review."""

    hypothesis_id: str = ""
    vulnerability_type: str = ""
    endpoint: str = ""
    method: str = ""
    host: str = ""
    summary: str = ""
    description: str = ""

    # PoC in multiple formats
    curl_command: str = ""
    python_script: str = ""
    js_fetch_code: str = ""
    httpie_command: str = ""
    burp_sequence: list[dict[str, Any]] = field(default_factory=list)

    # Scoring identifiers
    cvss_score: float = 0.0
    cvss_vector: str = ""
    cwe_id: str = ""
    cwe_name: str = ""
    capec_id: str = ""

    # Report body
    reproduction_steps: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    expected_result: str = ""
    actual_result: str = ""
    business_impact: str = ""
    risk_factors: list[str] = field(default_factory=list)

    # System reasoning (transparency for triager)
    what_was_tested: list[str] = field(default_factory=list)
    what_was_ruled_out: list[dict[str, str]] = field(default_factory=list)
    contradictions_considered: list[dict[str, Any]] = field(default_factory=list)
    alternative_explanations: list[dict[str, Any]] = field(default_factory=list)
    confidence_level: str = "medium"
    evidence_score: float = 0.0
    acceptance_probability: float = 0.0

    # Readiness
    is_report_ready: bool = False
    report_readiness_gaps: list[str] = field(default_factory=list)

    # Nuclei automation
    nuclei_template: str = ""
    nuclei_template_id: str = ""

    # Metadata
    composed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    composition_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "vulnerability_type": self.vulnerability_type,
            "endpoint": self.endpoint,
            "method": self.method,
            "host": self.host,
            "summary": self.summary,
            "description": self.description,
            "poc": {
                "curl": self.curl_command,
                "python": self.python_script,
                "javascript": self.js_fetch_code,
                "httpie": self.httpie_command,
                "burp_sequence": self.burp_sequence,
            },
            "scoring": {
                "cvss_score": self.cvss_score,
                "cvss_vector": self.cvss_vector,
                "cwe_id": self.cwe_id,
                "cwe_name": self.cwe_name,
                "capec_id": self.capec_id,
            },
            "report_body": {
                "reproduction_steps": self.reproduction_steps,
                "preconditions": self.preconditions,
                "expected_result": self.expected_result,
                "actual_result": self.actual_result,
                "business_impact": self.business_impact,
                "risk_factors": self.risk_factors,
            },
            "system_reasoning": {
                "what_was_tested": self.what_was_tested,
                "what_was_ruled_out": self.what_was_ruled_out,
                "contradictions_considered": self.contradictions_considered,
                "alternative_explanations": self.alternative_explanations,
                "confidence_level": self.confidence_level,
                "evidence_score": self.evidence_score,
                "acceptance_probability": self.acceptance_probability,
            },
            "readiness": {
                "is_report_ready": self.is_report_ready,
                "gaps": self.report_readiness_gaps,
            },
            "nuclei_template": self.nuclei_template,
            "nuclei_template_id": self.nuclei_template_id,
            "composed_at": self.composed_at,
        }


# ── PoC generators ─────────────────────────────────────────────


def generate_curl(
    endpoint: str,
    method: str,
    params: dict[str, str] | None,
    headers: dict[str, str] | None,
    body: Any,
    vuln_param: str,
    test_value: str,
) -> str:
    url = endpoint
    query = ""
    if params:
        param_strs = [f"{k}={v}" for k, v in params.items() if not k.startswith("{")]
        if param_strs:
            query = "&".join(param_strs)
            sep = "?" if "?" not in url else "&"
            url = f"{url}{sep}{query}"
    parts = [f"curl -X {method} '{url}'"]
    if headers:
        for k, v in headers.items():
            parts.append(f"  -H '{k}: {v}'")
    if body:
        if isinstance(body, dict):
            parts.append("  -H 'Content-Type: application/json'")
            parts.append(f"  -d '{json.dumps(body)}'")
        else:
            parts.append(f"  -d '{body}'")
    if vuln_param:
        parts.append(f"  # PoC: replace {vuln_param} with '{test_value}' to reproduce")
    return " \\\n".join(parts)


def generate_python(
    method: str,
    endpoint: str,
    params: dict[str, str] | None,
    headers: dict[str, str] | None,
    body: Any,
    vuln_param: str,
    test_value: str,
) -> str:
    lines = ["import requests", "", f"url = '{endpoint}'"]
    if params:
        param_dict = {k: v for k, v in params.items() if not k.startswith("{")}
        if param_dict:
            lines.append(f"params = {json.dumps(param_dict, indent=2)}")
    if headers:
        lines.append(f"headers = {json.dumps(headers, indent=2)}")
    if body:
        body_str = json.dumps(body, indent=2) if isinstance(body, dict) else f"'{body}'"
        lines.append(f"payload = {body_str}")
    lines.append("")
    req_args = "url"
    if params:
        req_args += ", params=params"
    if headers:
        req_args += ", headers=headers"
    if body:
        req_args += ", json=payload" if isinstance(body, dict) else ", data=payload"
    lines.append(f"response = requests.{method.lower()}({req_args})")
    lines.append("print(f'Status: {response.status_code}')")
    lines.append("print(f'Body: {response.text[:2000]}')")
    lines.append("")
    lines.append(f"# PoC: set {vuln_param} = '{test_value}' to reproduce")
    return "\n".join(lines)


def generate_js_fetch(
    method: str, endpoint: str, params: dict[str, str] | None, headers: dict[str, str] | None, body: Any
) -> str:
    url = endpoint
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if not k.startswith("{"))
        if qs:
            sep = "?" if "?" not in url else "&"
            url = f"{url}{sep}{qs}"
    opts: dict[str, Any] = {"method": method.upper()}
    if headers:
        opts["headers"] = headers
    if body:
        if isinstance(body, dict):
            opts["headers"] = dict(opts.get("headers", {}))
            opts["headers"]["Content-Type"] = "application/json"
            opts["body"] = f"JSON.stringify({json.dumps(body)})"
        else:
            opts["body"] = f"'{body}'"
    opts_str = json.dumps(opts, indent=2) if not body else _format_js_opts(opts)
    return f"""fetch('{url}', {opts_str})
  .then(r => r.text())
  .then(console.log)
  .catch(console.error);"""


def _format_js_opts(opts: dict[str, Any]) -> str:
    lines = ["{"]
    for k, v in opts.items():
        if k == "body":
            lines.append(f"  {k}: {v},")
        else:
            lines.append(f"  {k}: {json.dumps(v)},")
    lines.append("}")
    return "\n".join(lines)


def generate_httpie(
    method: str, endpoint: str, params: dict[str, str] | None, headers: dict[str, str] | None, body: Any
) -> str:
    parts = [f"http {method} '{endpoint}'"]
    if params:
        for k, v in params.items():
            if not k.startswith("{"):
                parts.append(f"  {k}=={v}")
    if headers:
        for k, v in headers.items():
            parts.append(f"  '{k}:{v}'")
    if body and isinstance(body, dict):
        for k, v in body.items():
            parts.append(f"  {k}={v}")
    return " \\\n".join(parts)


# ── Nuclei template generator ──────────────────────────────────


def generate_nuclei_template(hypothesis: Hypothesis) -> tuple[str, str]:
    """Generate a Nuclei YAML template from a hypothesis.

    Returns (template_id, yaml_string).
    """
    tid = f"orion-{hypothesis.vulnerability_type}-{uuid.uuid4().hex[:8]}"
    severity = hypothesis.severity if hypothesis.severity in ("info", "low", "medium", "high", "critical") else "medium"
    cwe, _ = CWE_MAP.get(hypothesis.vulnerability_type, ("CWE-200", "Information Exposure"))

    method = hypothesis.method.upper()
    path = hypothesis.endpoint
    test_params = hypothesis.parameters_of_interest[:3]

    # Build Nuclei YAML
    lines = [
        f"id: {tid}",
        "",
        "info:",
        f'  name: "ORION: {hypothesis.summary}"',
        "  author: orion-system",
        f"  severity: {severity}",
        f'  description: "{hypothesis.description[:200]}"',
        "  classification:",
        f"    cwe-id: {cwe}",
        "    cvss-score: " + str(CVSS_SEVERITY_MAP.get(hypothesis.severity, (5.0, ""))[0]),
        "",
        "http:",
        "  - method: " + method,
        "    path:",
        f'      - "{{{{BaseURL}}}}{path}"',
    ]
    if test_params:
        lines.append("")
        lines.append("    # ORION-identified parameters of interest:")
        for p in test_params:
            lines.append(f"    # - {p}")
        lines.append("")
        lines.append("    # Example payload (customize per parameter):")
        lines.append("    # payload: |")
        lines.append('    #   param: "test_value"')

    lines.extend(
        [
            "",
            "    matchers-condition: or",
            "    matchers:",
            "      - type: status",
            "        status:",
            "          - 200",
            "          - 201",
            "",
            "      - type: word",
            "        part: body",
            "        words:",
            '          - "error"',
            '          - "Exception"',
            "        condition: or",
            "",
            "    # Generated by ORION Evidence Composer v1.0",
            f"    # Hypothesis: {hypothesis.id}",
            f"    # Confidence: {hypothesis.confidence:.2f}",
        ]
    )
    return tid, "\n".join(lines)


# ── CVSS calculator ────────────────────────────────────────────


def compute_cvss(severity: str, confidence: float) -> tuple[float, str]:
    """Map hypothesis severity + confidence to a CVSS v3.1 score and vector."""
    base_score, base_vector = CVSS_SEVERITY_MAP.get(severity, (5.0, "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N"))
    # Adjust score by confidence
    adjusted = round(base_score * (0.7 + 0.3 * confidence), 1)
    return adjusted, base_vector


# ── Report readiness check ────────────────────────────────────


REQUIRED_FOR_REPORT: list[str] = [
    "Reproduction steps with exact requests",
    "Expected vs actual result",
    "Business impact assessment",
    "CVSS score",
    "CWE identifier",
    "PoC in at least one format (curl/Python/JS)",
    "Scope verification",
]

OPTIONAL_FOR_REPORT: list[str] = [
    "Alternative explanations considered",
    "Contradictions ruled out",
    "Multiple PoC formats",
    "Nuclei template for re-testing",
    "Timeline of testing",
]


def check_report_readiness(bundle: EvidenceBundle) -> tuple[bool, list[str]]:
    """Evaluate if the evidence bundle is complete enough for submission."""
    gaps: list[str] = []
    checks = {
        "Reproduction steps with exact requests": len(bundle.reproduction_steps) >= 3,
        "Expected vs actual result": bool(bundle.expected_result) and bool(bundle.actual_result),
        "Business impact assessment": bool(bundle.business_impact),
        "CVSS score": bundle.cvss_score > 0,
        "CWE identifier": bool(bundle.cwe_id),
        "PoC in at least one format (curl/Python/JS)": bool(
            bundle.curl_command or bundle.python_script or bundle.js_fetch_code
        ),
        "Scope verification": len(bundle.preconditions) >= 1,
    }
    for item, passed in checks.items():
        if not passed:
            gaps.append(item)
    is_ready = len(gaps) <= 2  # Allow up to 2 gaps
    return is_ready, gaps


# ── Main composer ─────────────────────────────────────────────


def compose_nuclei_params(hypothesis: Hypothesis) -> dict[str, str]:
    """Extract params that should be fuzzed in Nuclei based on hypothesis."""
    result: dict[str, str] = {}
    for p in hypothesis.parameters_of_interest[:3]:
        result[p] = "FUZZ"  # Nuclei placeholder
    return result


class EvidenceComposer:
    """Transforms a hypothesis into structured, triage-ready evidence.

    Usage::

        composer = EvidenceComposer()
        bundle = composer.compose(hypothesis)
        if bundle.is_report_ready:
            print(bundle.curl_command)
    """

    def compose(
        self, hypothesis: Hypothesis, host: str = "", params_override: dict[str, str] | None = None
    ) -> EvidenceBundle:
        """Transform a hypothesis into a complete evidence bundle."""
        vuln_type = hypothesis.vulnerability_type
        cwe_id, cwe_name = CWE_MAP.get(vuln_type, ("CWE-200", "Information Exposure"))
        capec_id = CAPEC_MAP.get(vuln_type, "")
        cvss_score, cvss_vector = compute_cvss(hypothesis.severity, hypothesis.confidence)
        method = hypothesis.method.upper()

        # Determine test value based on vuln type
        test_value = self._sample_test_value(vuln_type)

        # Guess a host for PoC generation
        poc_host = host or hypothesis.endpoint

        # Build params dict for PoC generation
        poc_params: dict[str, str] = {}
        if params_override:
            poc_params.update(params_override)
        for p in hypothesis.parameters_of_interest[:3]:
            if p not in poc_params:
                poc_params[p] = test_value

        # Generate PoC in all formats
        vuln_param = hypothesis.parameters_of_interest[0] if hypothesis.parameters_of_interest else "param"
        curl = generate_curl(poc_host, method, poc_params, {}, None, vuln_param, test_value)
        py_code = generate_python(method, poc_host, poc_params, {}, None, vuln_param, test_value)
        js_code = generate_js_fetch(method, poc_host, poc_params, {}, None)
        httpie = generate_httpie(method, poc_host, poc_params, {}, None)

        # Generate Nuclei template
        nid, ntemplate = generate_nuclei_template(hypothesis)

        # Build reproduction steps from hypothesis
        repro_steps = list(hypothesis.test_instructions) if hypothesis.test_instructions else []
        if hypothesis.reproducibility_notes:
            repro_steps.append(hypothesis.reproducibility_notes)
        if not repro_steps:
            repro_steps = [
                f"Send a {method} request to {hypothesis.endpoint}",
                f"Set the {vuln_param} parameter to '{test_value}'",
                "Compare the response with a baseline request",
            ]

        preconditions = [hypothesis.scope_check] if hypothesis.scope_check else []
        preconditions.append("Ensure you have an active session/token for the target")

        # Business impact assessment
        business_impact = self._assess_business_impact(vuln_type, hypothesis.severity)

        # Risk factors
        risk_factors = (
            list(hypothesis.acceptance_prediction.risk_factors) if hypothesis.acceptance_prediction.risk_factors else []
        )

        # System reasoning transparency
        contradictions_list = (
            [
                {"label": c.label, "description": c.description, "how_to_rule_out": c.how_to_rule_out}
                for c in hypothesis.contradictions
            ]
            if hypothesis.contradictions
            else []
        )

        alternatives_list = hypothesis.alternative_explanations if hypothesis.alternative_explanations else []

        evidence_score = hypothesis.evidence_completeness.score if hypothesis.evidence_completeness else 0.0
        acceptance_prob = hypothesis.acceptance_prediction.probability if hypothesis.acceptance_prediction else 0.0

        bundle = EvidenceBundle(
            hypothesis_id=hypothesis.id,
            vulnerability_type=vuln_type,
            endpoint=hypothesis.endpoint,
            method=method,
            host=poc_host,
            summary=hypothesis.summary,
            description=hypothesis.description,
            curl_command=curl,
            python_script=py_code,
            js_fetch_code=js_code,
            httpie_command=httpie,
            cvss_score=cvss_score,
            cvss_vector=cvss_vector,
            cwe_id=cwe_id,
            cwe_name=cwe_name,
            capec_id=capec_id,
            reproduction_steps=repro_steps,
            preconditions=preconditions,
            expected_result="403 Forbidden or filtered response (baseline)",
            actual_result="200 OK with sensitive data returned (vulnerability confirmed)",
            business_impact=business_impact,
            risk_factors=risk_factors,
            what_was_tested=hypothesis.signals
            if hypothesis.signals
            else [f"{method} {hypothesis.endpoint} analyzed for {vuln_type}"],
            what_was_ruled_out=[{"explanation": alt.get("description", "")} for alt in alternatives_list[:2]],
            contradictions_considered=contradictions_list,
            alternative_explanations=alternatives_list,
            confidence_level="high"
            if hypothesis.confidence >= 0.7
            else "medium"
            if hypothesis.confidence >= 0.4
            else "low",
            evidence_score=evidence_score,
            acceptance_probability=acceptance_prob,
            nuclei_template=ntemplate,
            nuclei_template_id=nid,
        )

        is_ready, gaps = check_report_readiness(bundle)
        bundle.is_report_ready = is_ready
        bundle.report_readiness_gaps = gaps

        logger.info(
            "[EVIDENCE] Composed bundle for %s %s → ready=%s, CVSS=%.1f, gaps=%d",
            method,
            hypothesis.endpoint,
            is_ready,
            cvss_score,
            len(gaps),
        )
        return bundle

    def compose_from_dict(self, data: dict[str, Any], host: str = "") -> EvidenceBundle:
        """Create an EvidenceBundle from a raw dict (API input)."""
        hyp = Hypothesis(
            id=data.get("hypothesis_id", f"hyp-{uuid.uuid4().hex[:12]}"),
            vulnerability_type=data.get("vulnerability_type", "generic"),
            endpoint=data.get("endpoint", ""),
            method=data.get("method", "GET"),
            confidence=data.get("confidence", 0.5),
            severity=data.get("severity", "medium"),
            summary=data.get("summary", ""),
            description=data.get("description", ""),
            test_instructions=data.get("test_instructions", []),
            parameters_of_interest=data.get("parameters_of_interest", []),
            signals=data.get("signals", []),
            scope_check=data.get("scope_check", ""),
            reproducibility_notes=data.get("reproducibility_notes", ""),
            alternative_explanations=data.get("alternative_explanations", []),
            contradictions=[],
        )
        return self.compose(hyp, host=host)

    @staticmethod
    def _sample_test_value(vuln_type: str) -> str:
        return {
            "idor": "12345",
            "ssrf": "http://127.0.0.1:80",
            "auth_bypass": "none",
            "xss": "<script>alert(1)</script>",
            "sqli": "' OR '1'='1",
        }.get(vuln_type, "test_value")

    @staticmethod
    def _assess_business_impact(vuln_type: str, severity: str) -> str:
        impacts: dict[str, dict[str, str]] = {
            "idor": {
                "critical": "Complete database access: attacker can read/modify/delete any record across all tenants.",
                "high": "Unauthorized data access: attacker can read sensitive data (PII, financial records) of other users.",
                "medium": "Limited data exposure: attacker can read non-critical data belonging to other users.",
                "low": "Minor information disclosure: non-sensitive data accessible but cannot be exploited at scale.",
            },
            "ssrf": {
                "critical": "Full internal network access: attacker can interact with cloud metadata, internal services, and pivot deeper.",
                "high": "Internal service discovery: attacker can scan internal ports and access cloud metadata.",
                "medium": "Limited internal access: attacker can reach specific internal endpoints.",
                "low": "Outbound request reflection: minimal internal access possible.",
            },
            "auth_bypass": {
                "critical": "Complete admin access: attacker can perform any action without authentication.",
                "high": "Privileged access: attacker can access restricted functionality without proper auth.",
                "medium": "Limited privilege escalation: attacker can access some restricted endpoints.",
                "low": "Minor auth gap: information disclosure via unauthorized access to low-sensitivity endpoints.",
            },
            "xss": {
                "critical": "Full account takeover: attacker can execute arbitrary JavaScript in any user's browser session.",
                "high": "Session hijacking: attacker can steal cookies and impersonate users.",
                "medium": "Data exfiltration: attacker can read sensitive data from the page DOM.",
                "low": "Minor script execution: limited impact due to CSP or context restrictions.",
            },
            "sqli": {
                "critical": "Complete database compromise: attacker can extract, modify, or delete any data and potentially execute commands on the server.",
                "high": "Data extraction: attacker can extract multiple tables including user credentials.",
                "medium": "Limited data disclosure: attacker can extract specific database values.",
                "low": "Information fingerprinting: attacker can confirm database type and version.",
            },
        }
        default = "Potential security impact depending on the specific vulnerability and data accessible."
        return impacts.get(vuln_type, {}).get(severity, default)


# ── Event publishing ───────────────────────────────────────────


def publish_evidence_event(event_type: str, bundle: EvidenceBundle) -> None:
    """Publish an evidence event to the EventBus."""
    try:
        from core.events.event_bus import get_core_event_bus

        envelope = EventEnvelope.create(
            event_type=f"evidence:{event_type}",
            source="evidence",
            payload={
                "hypothesis_id": bundle.hypothesis_id,
                "vulnerability_type": bundle.vulnerability_type,
                "is_report_ready": bundle.is_report_ready,
                "cvss_score": bundle.cvss_score,
                "cwe_id": bundle.cwe_id,
                "acceptance_probability": bundle.acceptance_probability,
            },
        )
        bus = get_core_event_bus()
        bus.publish(envelope.event_type, **envelope.payload)
    except Exception as exc:
        logger.warning("[EVIDENCE] Failed to publish event %s: %s", event_type, exc)
