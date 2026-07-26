"""ValidatorReport — genera reportes profesionales de bug bounty.

Toma un hallazgo validado y produce un reporte en formato markdown
con estructura lista para enviar al programa de bug bounty.

Secciones:
  1. Título y metadatos (severidad, CVSS, bounty estimado)
  2. Resumen ejecutivo
  3. Endpoint afectado
  4. Detalles técnicos
  5. PoC (curl + python)
  6. Evidencia (diff de respuestas, señales)
  7. Confianza y reproducibilidad
  8. Impacto potencial
  9. Remediation
  10. Timeline
"""

from __future__ import annotations

import datetime
import logging

logger = logging.getLogger("orion.core.reporting.validator_report")


# ── Remediation map ──────────────────────────────────────────────

_REMEDIATION_MAP: dict[str, str] = {
    "idor": (
        "Implement proper access control checks on the server side. "
        "Verify that the authenticated user owns or has permissions for the "
        "requested resource. Use indirect object references (e.g., UUIDs / GUIDs) "
        "instead of sequential IDs, but always combine with server-side "
        "authorization checks. Never rely on the client to restrict access."
    ),
    "auth_bypass": (
        "Ensure all authenticated endpoints verify the validity of the session "
        "token or authentication header before processing the request. "
        "Implement consistent authentication middleware that cannot be bypassed "
        "by simply removing, modifying, or providing empty auth headers. "
        "Apply authentication checks at the framework level, not per-route."
    ),
    "ssrf": (
        "Validate and sanitize all user-supplied URLs before making server-side "
        "requests. Implement an allowlist of permitted protocols (HTTPS only) and "
        "destinations. Disable URL schemas such as file://, gopher://, dict://. "
        "Use a dedicated HTTP client with no redirect following and no access to "
        "internal networks."
    ),
    "xss": (
        "Apply context-aware output encoding for all user-controlled data reflected "
        "in responses. Implement Content Security Policy (CSP) headers. "
        "Use framework-level auto-escaping templates. Validate and sanitize input "
        "on both client and server side. Consider using a strict CSP that blocks "
        "inline scripts."
    ),
    "sqli": (
        "Use parameterized queries / prepared statements for all database operations. "
        "Never concatenate user input directly into SQL queries. Apply an ORM with "
        "built-in parameterization. Implement a Web Application Firewall (WAF) as a "
        "defense-in-depth measure. Restrict database user permissions to the minimum "
        "required."
    ),
    "generic": (
        "Review the affected endpoint for input validation, access control, and "
        "secure configuration. Apply the principle of least privilege. "
        "Ensure all responses are sanitized and no sensitive data is leaked. "
        "Implement comprehensive logging and monitoring for this endpoint."
    ),
}

_CVSS_VECTORS: dict[str, str] = {
    "critical": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",  # 9.0-10.0
    "high": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",  # 7.0-8.9
    "medium": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N",  # 4.0-6.9
    "low": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:N/A:N",  # 0.1-3.9
    "info": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N",  # 0.0
}

_SEVERITY_PAYOUT_RANGES: dict[str, str] = {
    "critical": "$5,000 - $20,000+",
    "high": "$1,000 - $5,000",
    "medium": "$250 - $1,000",
    "low": "$50 - $250",
    "info": "$0 - $50",
}


class ValidatorReport:
    """Genera un reporte profesional de bug bounty desde un hallazgo validado."""

    def __init__(  # noqa: PLR0913
        self,
        finding_id: int,
        title: str,
        severity: str,
        target_name: str,
        endpoint_path: str,
        method: str,
        vulnerability_type: str,
        description: str,
        confidence: float,
        poc_curl: str = "",
        poc_python: str = "",
        evidence_data: dict | None = None,
        signals: list[str] | None = None,
        reproducible: bool = False,
        target_domain: str = "",
        bounty_estimate: str | None = None,
        cvss_vector_str: str | None = None,
        cvss_score: float | None = None,
    ):
        self.finding_id = finding_id
        self.title = title
        self.severity = severity.lower()
        self.target_name = target_name
        self.endpoint_path = endpoint_path
        self.method = method.upper()
        self.vulnerability_type = vulnerability_type.lower()
        self.description = description
        self.confidence = confidence
        self.poc_curl = poc_curl
        self.poc_python = poc_python
        self.evidence_data = evidence_data or {}
        self.signals = signals or []
        self.reproducible = reproducible
        self.target_domain = target_domain
        self._bounty_estimate = bounty_estimate
        self._cvss_vector = cvss_vector_str
        self._cvss_score = cvss_score

    # ── Derived properties ───────────────────────────────────────

    @property
    def cvss_vector(self) -> str:
        if self._cvss_vector:
            return self._cvss_vector
        return _CVSS_VECTORS.get(self.severity, _CVSS_VECTORS["medium"])

    @property
    def cvss_score(self) -> float:
        if self._cvss_score is not None:
            return self._cvss_score
        scores = {"critical": 9.5, "high": 8.0, "medium": 5.5, "low": 2.5, "info": 0.0}
        return scores.get(self.severity, 5.5)

    @property
    def bounty_estimate(self) -> str:
        if self._bounty_estimate:
            return self._bounty_estimate
        return _SEVERITY_PAYOUT_RANGES.get(self.severity, "$0 - $50")

    @property
    def remediation(self) -> str:
        return _REMEDIATION_MAP.get(self.vulnerability_type, _REMEDIATION_MAP["generic"])

    # ── Markdown generation ──────────────────────────────────────

    def to_markdown(self) -> str:
        """Genera el reporte completo en markdown."""
        sections = [
            self._header(),
            self._metadata_table(),
            self._executive_summary(),
            self._affected_endpoint(),
            self._technical_details(),
            self._poc_section(),
            self._evidence_section(),
            self._confidence_section(),
            self._reproducibility(),
            self._impact(),
            self._remediation_section(),
            self._timeline(),
            self._footer(),
        ]
        return "\n\n".join(sections)

    def _header(self) -> str:
        severity_badge = {
            "critical": "🔴 CRITICAL",
            "high": "🟠 HIGH",
            "medium": "🟡 MEDIUM",
            "low": "🔵 LOW",
            "info": "⚪ INFO",
        }.get(self.severity, self.severity.upper())

        return (
            f"# {self.title}\n\n"
            f"**Severity:** {severity_badge}  \n"
            f"**CVSS:** {self.cvss_vector} ({self.cvss_score:.1f})  \n"
            f"**Bounty Estimate:** {self.bounty_estimate}  \n"
            f"**Report ID:** CAT-{self.finding_id:05d}"
        )

    def _metadata_table(self) -> str:
        vuln_label = self.vulnerability_type.upper()
        return (
            "| Field | Value |\n"
            "|---|---|\n"
            f"| **Program / Target** | {self.target_name} |\n"
            f"| **Vulnerability Type** | `{vuln_label}` |\n"
            f"| **Finding ID** | #{self.finding_id} |\n"
            f"| **Confidence** | {self.confidence:.0%} |\n"
            f"| **Reproducible** | {'✅ Yes' if self.reproducible else '❌ No'} |\n"
            f"| **Reported** | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')} |"
        )

    def _executive_summary(self) -> str:
        return (
            "## Executive Summary\n\n"
            f"A {self.severity}-severity {self.vulnerability_type.upper()} vulnerability "
            f"was identified and validated in **{self.target_name}**. "
            f"The issue affects the endpoint "
            f"`{self.method} {self.endpoint_path}` "
            f"({'at ' + self.target_domain if self.target_domain else ''}) "
            f"and was confirmed with {self.confidence:.0%} confidence "
            f"{'and reproducible across multiple attempts' if self.reproducible else ''}."
            "\n\n"
            f"Validation was performed by the CATEYE autonomous validation engine "
            f"which executed a targeted probe plan against the identified attack surface. "
            f"The plan included baseline recording and differential probe analysis."
        )

    def _affected_endpoint(self) -> str:
        return (
            "## Affected Endpoint\n\n"
            "```\n"
            f"{self.method} {self.endpoint_path}\n"
            f"Host: {self.target_domain or self.target_name}\n"
            "```"
        )

    def _technical_details(self) -> str:
        return (
            "## Technical Details\n\n"
            f"{self.description}\n\n"
            "### Vulnerability Class\n\n"
            f"This finding falls under the **{self.vulnerability_type.upper()}** category. "
            + {
                "idor": (
                    "Insecure Direct Object Reference (IDOR) occurs when an application "
                    "exposes a direct reference to an internal implementation object, "
                    "such as a file, database record, or URL parameter, without proper "
                    "access control checks. An authenticated user can access resources "
                    "belonging to other users by manipulating the reference."
                ),
                "auth_bypass": (
                    "Authentication Bypass vulnerabilities allow an attacker to access "
                    "protected resources without valid authentication. This can occur "
                    "when the application fails to properly validate session tokens, "
                    "API keys, or other authentication mechanisms."
                ),
                "ssrf": (
                    "Server-Side Request Forgery (SSRF) allows an attacker to induce "
                    "the server-side application to make requests to unintended locations. "
                    "This can lead to accessing internal services, reading cloud metadata, "
                    "or performing port scans of internal networks."
                ),
                "xss": (
                    "Cross-Site Scripting (XSS) enables attackers to inject malicious "
                    "scripts into web pages viewed by other users. This can lead to "
                    "session hijacking, credential theft, or defacement."
                ),
                "sqli": (
                    "SQL Injection allows an attacker to interfere with the queries "
                    "that an application makes to its database. This can lead to "
                    "unauthorized data access, data modification, or database "
                    "compromise."
                ),
            }.get(self.vulnerability_type, "")
        )

    def _poc_section(self) -> str:
        sections = ["## Proof of Concept\n"]
        if self.poc_curl:
            sections.append("### cURL\n\n```bash\n" + self.poc_curl + "\n```")
        if self.poc_python:
            sections.append("### Python\n\n```python\n" + self.poc_python + "\n```")
        if not self.poc_curl and not self.poc_python:
            sections.append(
                "*No automated PoC was generated for this finding. "
                "Manual verification is recommended.*"
            )
        return "\n\n".join(sections)

    def _evidence_section(self) -> str:
        sec = ["## Evidence\n"]
        if self.signals:
            sec.append("### Signals Detected\n\n" + "\n".join(f"- `{s}`" for s in self.signals))
        evidence = self.evidence_data
        if evidence:
            if "baseline" in evidence:
                b = evidence["baseline"]
                sec.append(
                    "### Baseline Response\n\n"
                    f"- **Status Code:** {b.get('status_code', 'N/A')}\n"
                    f"- **Response Time:** {b.get('elapsed_ms', 'N/A')}ms\n"
                    f"- **Body Size:** {b.get('body_size', 'N/A')} bytes\n"
                    f"- **Preview:** `{b.get('body_preview', '')[:200]}...`"
                )
            probes = {k: v for k, v in evidence.items() if k != "baseline"}
            if probes:
                for name, p in probes.items():
                    sec.append(
                        f"### Probe: `{name}`\n\n"
                        f"- **Status Code:** {p.get('status_code', 'N/A')}\n"
                        f"- **Response Time:** {p.get('elapsed_ms', 'N/A')}ms\n"
                        f"- **Body Size:** {p.get('body_size', 'N/A')} bytes\n"
                        f"- **Preview:** `{p.get('body_preview', '')[:200]}...`"
                    )
        if not evidence and not self.signals:
            sec.append("*No evidence data was captured during validation.*")
        return "\n\n".join(sec)

    def _confidence_section(self) -> str:
        return (
            "## Confidence Assessment\n\n"
            f"The validation engine assigned a **{self.confidence:.0%}** confidence score "
            f"to this finding based on the following signals:\n\n"
            f"- **Response Differentials:** Evidence of behavior change between "
            f"baseline and probe requests.\n"
            f"- **Timing Analysis:** Response time variations were analyzed for anomalies.\n"
            f"- **Data Leak Detection:** Response bodies were checked for unauthorized data exposure.\n"
            f"- **Error Pattern Analysis:** Probe responses were analyzed for "
            f"error-based information disclosure.\n\n"
            f"**Threshold for promotion:** ≥ 70% confidence with reproducibility.  \n"
            f"**Current status:** {'✅ PASSED' if self.confidence >= 0.7 else '⚠️ BELOW THRESHOLD'}"
        )

    def _reproducibility(self) -> str:
        if self.reproducible:
            return (
                "## Reproducibility\n\n"
                "✅ **This finding was reproduced successfully.** "
                "The validation engine executed multiple independent attempts "
                "and confirmed consistent results. "
                "The vulnerability is not a transient or race-condition issue."
            )
        return (
            "## Reproducibility\n\n"
            "❌ **This finding was NOT reproduced in subsequent attempts.** "
            "Manual verification is strongly recommended before submitting to the program. "
            "The initial signal may have been a transient network behavior or environmental anomaly."
        )

    def _impact(self) -> str:
        return (
            "## Impact\n\n"
            + {
                "idor": (
                    "An attacker could access, modify, or delete resources belonging to "
                    "other users. Depending on the application, this may include personal "
                    "information, financial data, private messages, or administrative functions. "
                    "The business impact ranges from data breach (GDPR/CCPA liability) to "
                    "complete account takeover in severe cases."
                ),
                "auth_bypass": (
                    "An unauthenticated attacker could access protected endpoints, "
                    "perform privileged actions, or extract sensitive data. "
                    "This vulnerability undermines the entire authentication model "
                    "and may lead to full compromise of the affected system."
                ),
                "ssrf": (
                    "An attacker could probe internal network services, read cloud "
                    "instance metadata (e.g., AWS IAM credentials), or interact with "
                    "internal APIs. In cloud environments, this often leads to "
                    "credential exposure and lateral movement."
                ),
                "xss": (
                    "An attacker could execute arbitrary JavaScript in the context "
                    "of a victim user's session, leading to session hijacking, "
                    "credential theft, CSRF bypass, or malware distribution."
                ),
                "sqli": (
                    "An attacker could extract, modify, or delete database contents. "
                    "Severe cases allow reading the entire application database, "
                    "including password hashes, PII, and business-critical data. "
                    "In some configurations, code execution on the database server "
                    "is possible."
                ),
            }.get(
                self.vulnerability_type,
                "An attacker could exploit this vulnerability to compromise "
                "the confidentiality, integrity, or availability of the affected system. "
                "The exact impact depends on the specific application context.",
            )
        )

    def _remediation_section(self) -> str:
        return f"## Remediation\n\n{self.remediation}"

    def _timeline(self) -> str:
        now = datetime.datetime.now()
        return (
            "## Timeline\n\n"
            "| Date | Event |\n"
            "|---|---|\n"
            f"| {now.strftime('%Y-%m-%d')} | Automated discovery and hypothesis generation |\n"
            f"| {now.strftime('%Y-%m-%d')} | Validation Engine: plan → probe → evidence → promote |\n"
            f"| {now.strftime('%Y-%m-%d %H:%M')} | Report generated by CATEYE |\n"
        )

    def _footer(self) -> str:
        return (
            "---\n\n"
            "*Report generated by **CATEYE Autonomous Validation Engine**  \n"
            f"Generated at: {datetime.datetime.now().isoformat()}*"
        )
