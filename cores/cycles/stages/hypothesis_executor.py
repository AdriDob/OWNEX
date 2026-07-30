"""HypothesisExecutor — vulnerability hypothesis generation stage.

Stage 3 of the security pipeline. Generates testable vulnerability
hypotheses based on attack surface analysis and threat models.
"""

from __future__ import annotations

from typing import Any

from cores.cycles.stages import BaseStageExecutor


class HypothesisExecutor(BaseStageExecutor):
    """Generate and prioritise vulnerability hypotheses.

    Analyses the attack surface, technology stack, and known vulnerability
    patterns to produce ranked, testable hypotheses for the validation stage.
    """

    @property
    def name(self) -> str:
        return "hypothesis"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self.logger.info("Starting hypothesis stage")
        target = context.get("target", "")
        if not target:
            return self._wrap_result("failed", "No target provided", error="Missing 'target' in context")

        attack_surface = context.get("attack_surface", {})
        tech_stack = attack_surface.get("tech_stack", [])
        attack_surface.get("open_ports", [])
        services = attack_surface.get("services", [])
        endpoints = context.get("endpoints", [])

        try:
            hypotheses = self._generate_hypotheses(target, tech_stack, services, endpoints, context)
            hypotheses = self._rank_hypotheses(hypotheses)
            top_hypotheses = hypotheses[:10]

            summary = f"Generated {len(hypotheses)} hypotheses, top {len(top_hypotheses)} prioritised"

            details: dict[str, Any] = {
                "target": target,
                "total_hypotheses": len(hypotheses),
                "hypotheses": top_hypotheses,
                "tech_stack_analyzed": [t["name"] for t in tech_stack],
                "services_analyzed": len(services),
            }
            self._log_hypotheses(target, hypotheses)
            return self._wrap_result("completed", summary, details=details)

        except Exception as e:
            self.logger.error("Hypothesis stage failed: %s", e)
            return self._wrap_result("failed", f"Hypothesis generation failed: {e}", error=str(e))

    def _generate_hypotheses(
        self,
        target: str,
        tech_stack: list[dict[str, Any]],
        services: list[dict[str, Any]],
        endpoints: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate vulnerability hypotheses based on attack surface."""
        hypotheses: list[dict[str, Any]] = []
        tech_names = {t["name"].lower() for t in tech_stack}
        service_names = {s["service"].lower() for s in services}

        # ── Technology-based hypotheses ──
        tech_vulns = {
            "nginx": [
                (
                    "Misconfigured NGINX",
                    "NGINX path traversal or misconfiguration",
                    "medium",
                    ["path_traversal", "misconfiguration"],
                ),
                (
                    "NGINX Insecure Directives",
                    "Weak NGINX security directives allowing information disclosure",
                    "medium",
                    ["info_disclosure"],
                ),
            ],
            "apache": [
                (
                    "Apache Misconfiguration",
                    "Apache server info disclosure via server-status",
                    "medium",
                    ["misconfiguration"],
                ),
                ("Apache Path Traversal", "Potential path traversal in Apache aliases", "high", ["path_traversal"]),
            ],
            "wordpress": [
                ("WordPress Plugin Vulnerability", "Outdated or vulnerable WordPress plugin", "high", ["known_vuln"]),
                (
                    "WordPress User Enumeration",
                    "WordPress user enumeration via REST API",
                    "medium",
                    ["info_disclosure"],
                ),
                ("WordPress Admin Access", "Weak admin credentials or exposed wp-admin", "critical", ["auth_bypass"]),
            ],
            "django": [
                ("Django Debug Mode", "Django DEBUG=True exposing sensitive config", "critical", ["info_disclosure"]),
                ("Django Session Hijacking", "Predictable session cookies or CSRF bypass", "high", ["session"]),
            ],
            "express": [
                ("Express Error Handling", "Express stack traces in error responses", "medium", ["info_disclosure"]),
                (
                    "Express CORS Misconfiguration",
                    "Overly permissive CORS on Express endpoints",
                    "high",
                    ["misconfiguration"],
                ),
            ],
            "fastapi": [
                (
                    "FastAPI OpenAPI Exposure",
                    "Exposed /docs or /openapi.json providing attack surface",
                    "medium",
                    ["info_disclosure"],
                ),
                ("FastAPI Input Validation", "Missing input validation on FastAPI endpoints", "high", ["injection"]),
            ],
            "react": [
                (
                    "React API Key Exposure",
                    "API keys or secrets exposed in React bundle",
                    "critical",
                    ["info_disclosure"],
                ),
                ("React Client-Side Routing", "Client-side access control bypass", "medium", ["auth_bypass"]),
            ],
            "vue": [
                ("Vue API Key Exposure", "Sensitive data in Vue store or components", "high", ["info_disclosure"]),
                ("Vue Insecure Directives", "XSS via v-html or unsafe binding", "high", ["xss"]),
            ],
        }

        for tech_name in tech_names:
            if tech_name in tech_vulns:
                for vuln_name, description, severity, tags in tech_vulns[tech_name]:
                    hypotheses.append(
                        {
                            "title": vuln_name,
                            "description": description,
                            "severity": severity,
                            "tags": tags,
                            "source": f"tech:{tech_name}",
                            "confidence": "medium",
                        }
                    )

        # ── Service-based hypotheses ──
        service_vulns = {
            "http": [
                ("Open HTTP Service", "Standard HTTP service may expose internal endpoints", "medium", ["discovery"])
            ],
            "https": [
                ("HTTPS Service", "Standard HTTPS service, check TLS configuration", "low", ["tls", "discovery"])
            ],
            "ssh": [("SSH Service", "Open SSH port, potential brute-force or weak keys", "medium", ["brute_force"])],
            "mysql": [
                (
                    "MySQL Database Exposure",
                    "Open MySQL port, potential SQL injection or weak auth",
                    "critical",
                    ["injection"],
                )
            ],
            "postgresql": [
                ("PostgreSQL Database Exposure", "Open PostgreSQL port, potential weak auth", "critical", ["injection"])
            ],
            "redis": [
                (
                    "Redis Unauthenticated Access",
                    "Open Redis port without auth, potential data exposure",
                    "critical",
                    ["misconfiguration"],
                )
            ],
            "mongodb": [
                ("MongoDB Unauthenticated Access", "Open MongoDB port without auth", "critical", ["misconfiguration"])
            ],
        }

        for service_name in service_names:
            if service_name in service_vulns:
                for vuln_name, description, severity, tags in service_vulns[service_name]:
                    hypotheses.append(
                        {
                            "title": vuln_name,
                            "description": description,
                            "severity": severity,
                            "tags": tags,
                            "source": f"service:{service_name}",
                            "confidence": "medium",
                        }
                    )

        # ── Generic endpoint hypotheses ──
        generic_hypotheses = [
            ("Missing Authentication", "Endpoint accessible without authentication", "high", ["auth_bypass", "idora"]),
            (
                "Insecure Direct Object Reference",
                "Predictable resource IDs allowing unauthorised access",
                "high",
                ["idora", "access_control"],
            ),
            ("SQL Injection", "Potential SQL injection in query parameters", "critical", ["injection", "sqli"]),
            ("Cross-Site Scripting (XSS)", "Reflected or stored XSS in user input", "high", ["xss", "injection"]),
            ("Server-Side Request Forgery", "Potential SSRF in URL parameters", "critical", ["ssrf", "injection"]),
            (
                "Rate Limiting Missing",
                "Endpoint without rate limiting, potential brute-force",
                "medium",
                ["misconfiguration"],
            ),
            ("Information Disclosure", "Sensitive information in responses or headers", "medium", ["info_disclosure"]),
            ("Open Redirect", "Unvalidated redirect parameters", "medium", ["redirect"]),
            (
                "Path Traversal",
                "Path traversal in file or static resource endpoints",
                "high",
                ["path_traversal", "injection"],
            ),
            ("Mass Assignment", "Unprotected model properties in POST/PUT requests", "high", ["misconfiguration"]),
        ]

        for vuln_name, description, severity, tags in generic_hypotheses:
            hypotheses.append(
                {
                    "title": vuln_name,
                    "description": description,
                    "severity": severity,
                    "tags": tags,
                    "source": "generic",
                    "confidence": "low",
                }
            )

        # Deduplicate by title
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for h in hypotheses:
            if h["title"] not in seen:
                seen.add(h["title"])
                unique.append(h)

        return unique

    def _rank_hypotheses(self, hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank hypotheses by severity priority and confidence."""
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        confidence_order = {"high": 0, "medium": 1, "low": 2}

        def sort_key(h: dict[str, Any]) -> tuple:
            sev = severity_order.get(h.get("severity", "low"), 99)
            conf = confidence_order.get(h.get("confidence", "low"), 99)
            return (sev, conf)

        return sorted(hypotheses, key=sort_key)

    def _log_hypotheses(self, target: str, hypotheses: list[dict[str, Any]]) -> None:
        by_severity: dict[str, int] = {}
        for h in hypotheses:
            sev = h.get("severity", "unknown")
            by_severity[sev] = by_severity.get(sev, 0) + 1
        severity_counts = ", ".join(f"{k}={v}" for k, v in sorted(by_severity.items()))
        self.logger.info("Hypotheses for %s: %d total [%s]", target, len(hypotheses), severity_counts)
