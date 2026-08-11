"""Investigation Planner — generates step-by-step research plans per vulnerability type.

Each plan simulates how a Top 1% bug bounty hunter would approach
a finding: recon first, then probe, then attack, then document.
"""

from __future__ import annotations

import logging
from typing import Any

from core.offensive.models import Hypothesis, InvestigationPlan, InvestigationStep

logger = logging.getLogger("orion.core.offensive.planner")

IDOR_STEPS: list[dict[str, Any]] = [
    {
        "phase": "recon",
        "action": "Check if the endpoint requires authentication",
        "condition": "Always",
        "expected_outcome": "401/Unauthorized or redirect to login",
        "follow_up": "If no auth required, the endpoint may be public — adjust approach",
        "priority": 1,
    },
    {
        "phase": "recon",
        "action": "Analyze identifier pattern (sequential, UUID, hash, JWT)",
        "condition": "Endpoint has {id} or similar param in path",
        "expected_outcome": "IDs follow a predictable pattern (incrementing integers, timestamps)",
        "follow_up": "If UUID/hash, check for ID leakage via other endpoints",
        "priority": 2,
    },
    {
        "phase": "recon",
        "action": "Confirm the endpoint is in scope for the program",
        "condition": "Always",
        "expected_outcome": "Endpoint matches in-scope pattern",
        "follow_up": "If out of scope, still document but note low priority",
        "priority": 3,
    },
    {
        "phase": "probe",
        "action": "Create two accounts (A and B), capture both auth tokens",
        "condition": "Endpoint requires auth and has object IDs",
        "expected_outcome": "Two valid sessions acquired",
        "follow_up": "If only one account possible, try guest sessions",
        "priority": 4,
    },
    {
        "phase": "probe",
        "action": "Authenticate as A, access B's resource using B's identifier",
        "condition": "IDOR suspected",
        "expected_outcome": "Response contains B's data (name, email, private info)",
        "follow_up": "If 403/Forbidden, try different HTTP methods (PUT, PATCH, DELETE)",
        "priority": 5,
    },
    {
        "phase": "probe",
        "action": "Try the same object ID via different parameters (query, header, cookie, body)",
        "condition": "Direct path IDOR blocked by auth check",
        "expected_outcome": "Authorization may be path-specific but not parameter-specific",
        "follow_up": "Try: /api/resource?id=X instead of /api/resource/X",
        "priority": 6,
    },
    {
        "phase": "probe",
        "action": "Check for write access — try modifying/creating/deleting B's resource as A",
        "condition": "Read IDOR confirmed",
        "expected_outcome": "Write operations on another user's data (escalation)",
        "follow_up": "If read-only, still valuable — document data exposure",
        "priority": 7,
    },
    {
        "phase": "attack",
        "action": "Mass enumerate valid IDs to demonstrate impact at scale",
        "condition": "Sequential IDs confirmed and no rate limiting",
        "expected_outcome": "Harvested data of N users (quantify impact)",
        "follow_up": "If rate limited, document the limit and demonstrate with sample",
        "priority": 8,
    },
    {
        "phase": "attack",
        "action": "Look for chained IDOR — use one endpoint to leak IDs, another to access data",
        "condition": "Direct IDOR blocked but ID leakage suspected",
        "expected_outcome": "IDs leaked via search, autocomplete, webhook, or logs",
        "follow_up": "Check GraphQL, websockets, hidden endpoints for ID leakage",
        "priority": 9,
    },
    {
        "phase": "attack",
        "action": "Try IDOR via alternative content types (JSON vs XML vs Form)",
        "condition": "Standard IDOR blocked",
        "expected_outcome": "Content-type parsing differences bypass auth checks",
        "follow_up": "Try Accept: application/xml, Content-Type: text/xml",
        "priority": 10,
    },
    {
        "phase": "document",
        "action": "Record exact request/response pairs for every success and failure",
        "condition": "Always",
        "expected_outcome": "Complete evidence bundle including timing, headers, response bodies",
        "follow_up": "Use curl -v or Python requests script for reproducibility",
        "priority": 11,
    },
    {
        "phase": "document",
        "action": "Calculate business impact based on data sensitivity",
        "condition": "IDOR confirmed",
        "expected_outcome": "Clear impact statement (PII leaked, financial data, admin access)",
        "follow_up": "If impact is unclear, search for additional accessible data",
        "priority": 12,
    },
    {
        "phase": "document",
        "action": "Generate PoC script (Python requests or curl commands)",
        "condition": "IDOR confirmed",
        "expected_outcome": "One-step reproduction script",
        "follow_up": "Add comments explaining each step for triager",
        "priority": 13,
    },
]

SSRF_STEPS: list[dict[str, Any]] = [
    {
        "phase": "recon",
        "action": "Identify all parameters that accept URLs, IPs, or hostnames",
        "condition": "Always",
        "expected_outcome": "List of parameters that could be SSRF vectors",
        "follow_up": "Check query params, body fields, headers (Host, X-Forwarded-Host, Referer)",
        "priority": 1,
    },
    {
        "phase": "recon",
        "action": "Check if the server makes outbound HTTP requests to user-supplied inputs",
        "condition": "URL-accepting endpoint identified",
        "expected_outcome": "Server fetches the provided URL and returns the response",
        "follow_up": "Use a collaborator/request bin to detect outbound requests",
        "priority": 2,
    },
    {
        "phase": "probe",
        "action": "Test basic SSRF with internal IPs (127.0.0.1, 10.x.x.x, 172.16-31.x.x, 192.168.x.x)",
        "condition": "Outbound requests confirmed",
        "expected_outcome": "Server returns data from internal services",
        "follow_up": "If blocked, try URL encoding, IPv6 variants, decimal IPs",
        "priority": 3,
    },
    {
        "phase": "probe",
        "action": "Test cloud metadata endpoints (169.254.169.254 for AWS/GCP/Azure)",
        "condition": "Target is cloud-hosted",
        "expected_outcome": "Cloud metadata returned (IAM credentials, instance data)",
        "follow_up": "Try different cloud provider paths: /latest/meta-data/ for AWS",
        "priority": 4,
    },
    {
        "phase": "probe",
        "action": "Try DNS rebinding and redirect-based bypasses",
        "condition": "Direct IP blocked by allowlist or SSRF filter",
        "expected_outcome": "Server follows redirect to internal IP",
        "follow_up": "Set up a domain that resolves to 127.0.0.1 after TTL expiry",
        "priority": 5,
    },
    {
        "phase": "attack",
        "action": "Try protocol smuggling: file://, gopher://, dict://, ftp://",
        "condition": "HTTP-based SSRF confirmed or suspected",
        "expected_outcome": "Access to local files or internal services via alternative protocols",
        "follow_up": "Try file:///etc/passwd, gopher://localhost:6379/_ for Redis",
        "priority": 6,
    },
    {
        "phase": "attack",
        "action": "Try blind SSRF with out-of-band detection (Burp Collaborator, interactsh)",
        "condition": "No response data visible but outbound requests suspected",
        "expected_outcome": "DNS/HTTP callback to your server confirms SSRF",
        "follow_up": "Use blind SSRF to scan internal ports via timing differences",
        "priority": 7,
    },
    {
        "phase": "document",
        "action": "Record all tested URLs, bypass attempts, and responses",
        "condition": "Always",
        "expected_outcome": "Complete log of every SSRF test",
        "follow_up": "Note which bypasses worked and which didn't",
        "priority": 8,
    },
    {
        "phase": "document",
        "action": "Document internal services discovered and their potential impact",
        "condition": "SSRF confirmed",
        "expected_outcome": "Service inventory (internal ports, cloud metadata, file access)",
        "follow_up": "Combine with other endpoints for chained attacks",
        "priority": 9,
    },
]

AUTH_BYPASS_STEPS: list[dict[str, Any]] = [
    {
        "phase": "recon",
        "action": "Map all auth checkpoints — middleware, decorators, conditionals",
        "condition": "Always",
        "expected_outcome": "List of auth enforcement points in the request flow",
        "follow_up": "Check if some endpoints are missing auth middleware",
        "priority": 1,
    },
    {
        "phase": "recon",
        "action": "Check for public endpoints that expose sensitive data",
        "condition": "Always",
        "expected_outcome": "Identify endpoints accessible without auth that should require it",
        "follow_up": "Compare authenticated vs unauthenticated responses",
        "priority": 2,
    },
    {
        "phase": "probe",
        "action": "Try direct URL access without any auth headers or cookies",
        "condition": "Always",
        "expected_outcome": "Server rejects with 401/403 or unexpectedly returns data",
        "follow_up": "If 200 returned without auth, this is a direct auth bypass",
        "priority": 3,
    },
    {
        "phase": "probe",
        "action": "Try path traversal to bypass prefix-based auth (/admin/analytics/../users/)",
        "condition": "Auth enforced at path prefix level",
        "expected_outcome": "Middleware checks /admin/ prefix but normalized path resolves to /users/",
        "follow_up": "Try /./, //, /%2f/, /..;/ for path normalization bypass",
        "priority": 4,
    },
    {
        "phase": "probe",
        "action": "Try replaying requests with expired, modified, or alg=none JWTs",
        "condition": "JWT-based auth detected",
        "expected_outcome": "Server accepts alg=none tokens or doesn't verify signature",
        "follow_up": "Try kid injection, JWK injection, weak HMAC secret cracking",
        "priority": 5,
    },
    {
        "phase": "probe",
        "action": "Try HTTP method override headers (X-HTTP-Method-Override, X-Method-Override)",
        "condition": "Auth enforced on GET/POST but not on other methods",
        "expected_outcome": "Server checks auth on actual method but override creates bypass",
        "follow_up": "Also try OPTIONS, HEAD, TRACE, CONNECT",
        "priority": 6,
    },
    {
        "phase": "attack",
        "action": "Try forced browsing — access deeper nested resources that may have weaker auth",
        "condition": "Top-level auth is strong",
        "expected_outcome": "Deeply nested endpoints may skip auth checks inherited from parent",
        "follow_up": "Check /api/v2/admin/ if /api/admin/ is protected",
        "priority": 7,
    },
    {
        "phase": "document",
        "action": "Document the auth bypass chain from initial access to impact",
        "condition": "Bypass confirmed",
        "expected_outcome": "Clear step-by-step chain that any triager can reproduce",
        "follow_up": "Include curl commands for each step",
        "priority": 8,
    },
]

XSS_STEPS: list[dict[str, Any]] = [
    {
        "phase": "recon",
        "action": "Identify all user-controlled input reflected or stored in responses",
        "condition": "Always",
        "expected_outcome": "List of parameters that appear in response bodies",
        "follow_up": "Check query params, form fields, headers, file names, URL paths",
        "priority": 1,
    },
    {
        "phase": "probe",
        "action": "Test basic XSS payloads: <script>alert(1)</script>, <img src=x onerror=alert(1)>",
        "condition": "Reflected input detected",
        "expected_outcome": "Payload executes in browser (reflected/stored XSS)",
        "follow_up": "If filtered, try context-specific bypasses",
        "priority": 2,
    },
    {
        "phase": "probe",
        "action": "Check payload context (HTML body, attribute, JS string, CSS, URL)",
        "condition": "Basic payloads blocked or partially working",
        "expected_outcome": "Identify the exact context for context-specific bypasses",
        "follow_up": "Use ' to break out of JS strings, \"> for HTML attributes",
        "priority": 3,
    },
    {
        "phase": "attack",
        "action": "Try WAF bypasses: polyglots, unicode, nested encodings, mutation XSS",
        "condition": "WAF or filter blocking standard payloads",
        "expected_outcome": "Obfuscated payload bypasses filter",
        "follow_up": "Try <!--[if IE]><script>alert(1)</script><![endif]--> for IE",
        "priority": 4,
    },
    {
        "phase": "attack",
        "action": "Check for DOM-based XSS via hash, postMessage, document.referrer",
        "condition": "Client-side JS uses location.hash or similar",
        "expected_outcome": "XSS via URL fragment without server-side reflection",
        "follow_up": "Check for Sink-based XSS in Angular, React, Vue templates",
        "priority": 5,
    },
    {
        "phase": "document",
        "action": "Record proof-of-concept with specific payload and browser behavior",
        "condition": "XSS confirmed",
        "expected_outcome": "Reproducible PoC showing arbitrary JS execution",
        "follow_up": "Demonstrate impact: cookie theft, keylogging, CSRF token theft",
        "priority": 6,
    },
]

SQLI_STEPS: list[dict[str, Any]] = [
    {
        "phase": "recon",
        "action": "Identify all parameters that interact with a database",
        "condition": "Always",
        "expected_outcome": "List of potential SQL injection points",
        "follow_up": "Check for error-based, UNION, blind, and time-based vectors",
        "priority": 1,
    },
    {
        "phase": "probe",
        "action": "Test basic SQLi: ', \", ', --, ' OR '1'='1, '; DROP TABLE--",
        "condition": "DB-interacting endpoint identified",
        "expected_outcome": "Server returns SQL error, different response, or timing delay",
        "follow_up": "If no error, try blind SQLi techniques",
        "priority": 2,
    },
    {
        "phase": "probe",
        "action": "Check for error-based SQLi: extract DB version via error messages",
        "condition": "SQL errors visible in response",
        "expected_outcome": "Database name, version, or table names in error messages",
        "follow_up": "Use errors to extract data row by row",
        "priority": 3,
    },
    {
        "phase": "attack",
        "action": "Try UNION-based extraction to dump data",
        "condition": "Columns compatible with UNION SELECT",
        "expected_outcome": "Extractable data from arbitrary tables",
        "follow_up": "Enumerate columns first with ORDER BY / GROUP BY",
        "priority": 4,
    },
    {
        "phase": "attack",
        "action": "Try blind SQLi (boolean-based and time-based) if no visible output",
        "condition": "No visible errors or UNION output",
        "expected_outcome": "Data extraction via true/false or delay conditions",
        "follow_up": "Use SUBSTRING, SLEEP/BENCHMARK for time-based extraction",
        "priority": 5,
    },
    {
        "phase": "document",
        "action": "Record all tested payloads, responses, and extracted data",
        "condition": "SQLi confirmed",
        "expected_outcome": "Complete log of extraction with timing",
        "follow_up": "Document database schema, user privileges, and extracted secrets",
        "priority": 6,
    },
]

VULN_STEPS: dict[str, list[dict[str, Any]]] = {
    "idor": IDOR_STEPS,
    "ssrf": SSRF_STEPS,
    "auth_bypass": AUTH_BYPASS_STEPS,
    "xss": XSS_STEPS,
    "sqli": SQLI_STEPS,
    "generic": IDOR_STEPS,
}


class InvestigationPlanner:
    """Generates step-by-step research plans for vulnerability hypotheses.

    Usage::

        planner = InvestigationPlanner()
        plan = planner.plan(hypothesis)
        logger.info(plan.to_dict())
    """

    def plan(self, hypothesis: Hypothesis) -> InvestigationPlan:
        """Generate a complete investigation plan for a hypothesis."""
        vtype = hypothesis.vulnerability_type
        steps_raw = VULN_STEPS.get(vtype, VULN_STEPS["generic"])

        steps: list[InvestigationStep] = [
            InvestigationStep(
                phase=s["phase"],
                action=s["action"],
                condition=self._adapt_condition(s["condition"], hypothesis),
                expected_outcome=s["expected_outcome"],
                follow_up=s["follow_up"],
                priority=s["priority"],
            )
            for s in steps_raw
        ]

        effort = self._estimate_effort(vtype, hypothesis.severity)
        prereqs = self._get_prerequisites(vtype)
        alternatives = self._get_alternatives(vtype)
        priority = "high" if hypothesis.confidence >= 0.6 else "medium"

        return InvestigationPlan(
            hypothesis_id=hypothesis.id,
            vulnerability_type=vtype,
            endpoint=hypothesis.endpoint,
            method=hypothesis.method,
            summary=hypothesis.summary,
            steps=steps,
            estimated_effort=effort,
            priority=priority,
            prerequisites=prereqs,
            alternative_approaches=alternatives,
        )

    @staticmethod
    def _adapt_condition(condition: str, hypothesis: Hypothesis) -> str:
        if "{method}" in condition:
            return condition.replace("{method}", hypothesis.method)
        return condition

    @staticmethod
    def _estimate_effort(vtype: str, severity: str) -> str:
        if severity in ("high", "critical"):
            return "high"
        if vtype in ("sqli", "ssrf"):
            return "high" if severity == "medium" else "medium"
        return "medium"

    @staticmethod
    def _get_prerequisites(vtype: str) -> list[str]:
        common = ["Burp Suite or similar proxy", "API documentation or endpoint list"]
        if vtype == "idor":
            return common + ["Two user accounts (different privilege levels if possible)"]
        if vtype == "ssrf":
            return common + ["Collaborator/interactsh/request bin", "Cloud metadata knowledge"]
        if vtype == "auth_bypass":
            return common + ["Valid session/token", "Different privilege level accounts if possible"]
        if vtype == "xss":
            return common + ["Browser with developer tools"]
        if vtype == "sqli":
            return common + ["sqlmap or manual payload list", "Database-specific payload reference"]
        return common

    @staticmethod
    def _get_alternatives(vtype: str) -> list[str]:
        alts = {
            "idor": [
                "Try parameter pollution (id=1&id=2)",
                'Try JSON array injection ({"id":[1,2]})',
                "Try wildcard or null IDs (id=*, id=-1, id=null)",
                "Look for IDOR in related sub-resources",
                "Check IDOR via websocket messages or GraphQL mutations",
            ],
            "ssrf": [
                "Try alternative URL schemas (//, HTTP/0.9, \\)",
                "Try DNS pinning / rebinding",
                "Try localhost aliases (0.0.0.0, [::], 0x7f000001)",
                "Try SSRF via uploaded file URLs or webhooks",
            ],
            "auth_bypass": [
                "Try unicode/normalization bypass (admin vs ＡＤＭＩＮ)",
                "Try cookie without session, modify session in cookie",
                "Try OAuth misconfiguration (public client, redirect_uri bypass)",
            ],
            "xss": [
                "Try XSS via file upload (SVG, HTML file)",
                "Try XSS in CSP bypass via JSONP endpoints",
                "Try XSS via service worker or importScripts",
            ],
            "sqli": [
                "Try second-order SQLi (stored then executed)",
                "Try NoSQL injection if MongoDB is suspected",
                "Try ORM injection (HQL, JPQL, JPA)",
            ],
        }
        return alts.get(vtype, [])
