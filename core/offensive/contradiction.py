"""Contradiction Engine — attacks hypotheses with counterarguments.

For every hypothesis, generates contradictions that a triager
or program owner would raise. This forces the system to
consider alternative explanations BEFORE generating a report.

Only hypotheses that survive contradiction should proceed.
"""

from __future__ import annotations

import logging

from core.offensive.models import Contradiction, Hypothesis

logger = logging.getLogger("orion.core.offensive.contradiction")


class ContradictionEngine:
    """Generates counterarguments for a given hypothesis.

    Each vulnerability type has specific contradictions based on
    common triager objections and real-world program outcomes.
    """

    def attack(self, hypothesis: Hypothesis) -> list[Contradiction]:
        """Generate all contradictions for a hypothesis.

        Returns a list of Contradiction objects that weaken the hypothesis.
        """
        contradictions: list[Contradiction] = []
        vtype = hypothesis.vulnerability_type

        # Type-specific contradictions
        type_method = f"_attack_{vtype}"
        if hasattr(self, type_method):
            contradictions.extend(getattr(self, type_method)(hypothesis))

        # Generic contradictions that apply to everything
        contradictions.extend(self._attack_generic(hypothesis))

        # Deduplicate by label
        seen: set[str] = set()
        unique: list[Contradiction] = []
        for c in contradictions:
            if c.label not in seen:
                seen.add(c.label)
                unique.append(c)

        return unique

    # ── IDOR contradictions ──────────────────────────────────────

    def _attack_idor(self, hypothesis: Hypothesis) -> list[Contradiction]:
        return [
            Contradiction(
                label="Ownership verified server-side",
                description="The server may verify that the authenticated user owns the requested resource before returning it. The presence of an identifier in the endpoint does not guarantee IDOR.",
                confidence_reduction=0.35,
                how_to_rule_out="Try accessing a resource belonging to a different user account. If the server returns 403 or masks sensitive data, ownership is enforced.",
            ),
            Contradiction(
                label="Access control at gateway level",
                description="Authorization may be enforced at a reverse proxy, API gateway, or WAF level — not at the application endpoint itself.",
                confidence_reduction=0.25,
                how_to_rule_out="Check if the endpoint is behind a gateway that validates JWTs or session tokens. Try bypassing the gateway.",
            ),
            Contradiction(
                label="Resource may be public",
                description="The accessed resource might be intentionally public (e.g., a user's public profile). What looks like IDOR might be intended behavior.",
                confidence_reduction=0.3,
                how_to_rule_out="Check if the same data is accessible without authentication. If yes, it's public, not IDOR.",
            ),
            Contradiction(
                label="UUID/GUID not enumerable",
                description="If identifiers are random UUIDs, exploitation requires guessing or obtaining valid IDs through other means.",
                confidence_reduction=0.2,
                how_to_rule_out="Check if IDs follow a predictable pattern. Sequential numeric IDs are strong evidence of vulnerability.",
            ),
            Contradiction(
                label="Indirect reference map in use",
                description="The application may use indirect references (session-scoped mappings) rather than exposing direct object references.",
                confidence_reduction=0.3,
                how_to_rule_out="Try the same ID from a different session. If it resolves differently, indirect mapping is in use.",
            ),
            Contradiction(
                label="Rate limiting prevents mass enumeration",
                description="Even if IDOR exists, aggressive rate limiting may prevent practical exploitation at scale.",
                confidence_reduction=0.1,
                how_to_rule_out="Test rate limits by sending rapid requests. Check for X-RateLimit headers or 429 responses.",
            ),
            Contradiction(
                label="Authorization at parameter level not path level",
                description="The endpoint may authorize based on a different parameter than the one being tested. E.g., the path has user_id but auth checks the JWT sub claim.",
                confidence_reduction=0.25,
                how_to_rule_out="Try changing different parameters independently. Compare behavior when changing the path param vs a header/session.",
            ),
        ]

    # ── SSRF contradictions ──────────────────────────────────────

    def _attack_ssrf(self, hypothesis: Hypothesis) -> list[Contradiction]:
        return [
            Contradiction(
                label="Destination validation at application level",
                description="The application may validate URL destinations (allowlist/denylist) before making requests, preventing SSRF to internal services.",
                confidence_reduction=0.3,
                how_to_rule_out="Try accessing internal services only known to the application. If blocked, validation is likely in place.",
            ),
            Contradiction(
                label="Network restrictions prevent SSRF",
                description="The server may run in a restricted network environment with no access to internal IPs (private ranges, localhost).",
                confidence_reduction=0.25,
                how_to_rule_out="Attempt requests to common SSRF targets (169.254.169.254, 127.0.0.1, 192.168.*). If all fail, network restrictions may be in place.",
            ),
            Contradiction(
                label="Authentication middleware blocks SSRF",
                description="The endpoint may have authentication middleware that blocks requests from unauthorized services or domains.",
                confidence_reduction=0.2,
                how_to_rule_out="Try adding authorization headers or using a domain in the allowlist. If successful, auth middleware may be filtering.",
            ),
            Contradiction(
                label="SSH tunnel usage blocks SSRF attempts",
                description="The application may be behind a bastion host or SSH tunnel that only allows specific traffic patterns.",
                confidence_reduction=0.15,
                how_to_rule_out="Check network topology or firewall rules. Attempt different protocols (UDP vs TCP) or ports.",
            ),
            Contradiction(
                label="Destination may be public resource",
                description="The referenced endpoint might be a public service (e.g., google.com) rather than an internal vulnerability.",
                confidence_reduction=0.2,
                how_to_rule_out="Verify if the target is a legitimate business need. If not, it might be SSRF or misconfiguration.",
            ),
        ]

    # ── XSS contradictions ─────────────────────────────────────

    def _attack_xss(self, hypothesis: Hypothesis) -> list[Contradiction]:
        return [
            Contradiction(
                label="Output encoding implemented",
                description="The application may be encoding user input before rendering, preventing script execution even if input is reflected.",
                confidence_reduction=0.4,
                how_to_rule_out="Observe the response HTML. If all < and > characters are encoded as &lt; and &gt;, encoding is likely in place.",
            ),
            Contradiction(
                label="Content Security Policy (CSP) in place",
                description="The application may have CSP headers that block inline scripts and external script execution.",
                confidence_reduction=0.3,
                how_to_rule_out="Check response headers for Content-Security-Policy. If CSP blocks script execution, XSS may be prevented.",
            ),
            Contradiction(
                label="Request origin validation",
                description="The application may validate the source of requests and reject those from unauthorized origins.",
                confidence_reduction=0.25,
                how_to_rule_out="Try sending requests with Origin/Referer headers set to a legitimate domain. If rejected, origin validation exists.",
            ),
            Contradiction(
                label="Input sanitization middleware",
                description="The application may have input sanitization middleware that strips script tags before processing.",
                confidence_reduction=0.3,
                how_to_rule_out="Try various payload encodings (URL encoding, HTML entities). If all stripped, sanitization is likely active.",
            ),
            Contradiction(
                label="Cross-origin restrictions",
                description="The response may be subject to CORS policies that prevent script execution in attacker contexts.",
                confidence_reduction=0.2,
                how_to_rule_out="Check Access-Control-Allow-Origin headers. If restrictive, cross-origin XSS execution may be blocked.",
            ),
        ]

    # ── SQLi contradictions ─────────────────────────────────────

    def _attack_sqli(self, hypothesis: Hypothesis) -> list[Contradiction]:
        return [
            Contradiction(
                label="Parameterized queries used",
                description="The application may be using parameterized queries or prepared statements, which prevent SQL injection even if input is malicious.",
                confidence_reduction=0.5,
                how_to_rule_out="Attempt to break the query with complex SQL. If queries are properly escaped, parameterized queries are likely in use.",
            ),
            Contradiction(
                label="Input validation rejects SQL patterns",
                description="The application may reject SQL keywords (SELECT, UNION, etc.) or injection characters before query execution.",
                confidence_reduction=0.35,
                how_to_rule_out="Try injection with encoded keywords (encoded as %xx) or obfuscated patterns. If blocked, validation exists.",
            ),
            Contradiction(
                label="Least privilege database access",
                description="The database user may have limited permissions that prevent dangerous operations like UNION SELECT or data exfiltration.",
                confidence_reduction=0.3,
                how_to_rule_out="Attempt to extract system information, database list, or file read. If limited, least privilege may be in place.",
            ),
            Contradiction(
                label="Query timeout protection",
                description="The application may have query timeout or rate limiting that would block abusive SQL patterns.",
                confidence_reduction=0.2,
                how_to_rule_out="Observe response times or error patterns. Slow requests or specific error messages may indicate timeout protection.",
            ),
            Contradiction(
                label="Database WAF rules",
                description="The application may have database-level WAF rules that detect and block SQL injection patterns.",
                confidence_reduction=0.25,
                how_to_rule_out="Check database logs or error messages for WAF-related blocks. If detected, WAF protection likely exists.",
            ),
        ]

    # ── Auth bypass contradictions ─────────────────────────────────

    def _attack_auth_bypass(self, hypothesis: Hypothesis) -> list[Contradiction]:
        return [
            Contradiction(
                label="Session validation active",
                description="The application may validate session state, tokens, or cookies beyond simple authentication headers.",
                confidence_reduction=0.4,
                how_to_rule_out="Test with valid session tokens or cookies. If authentication succeeds, session validation may be robust.",
            ),
            Contradiction(
                label="Rate limiting blocks unauthorized access",
                description="The application may limit requests from unauthorized IPs or without proper credentials, preventing brute force attempts.",
                confidence_reduction=0.25,
                how_to_rule_out="Observe rate limit headers or error responses. If blocked after certain attempts, rate limiting may be in place.",
            ),
            Contradiction(
                label="Multi-factor authentication required",
                description="The application may require additional authentication factors beyond simple token-based auth.",
                confidence_reduction=0.3,
                how_to_rule_out="Try accessing sensitive endpoints with just a token. If rejected, additional auth factors may be required.",
            ),
            Contradiction(
                label="Role-based access control (RBAC)",
                description="The application may enforce RBAC rules that restrict access regardless of authentication status.",
                confidence_reduction=0.25,
                how_to_rule_out="Test with authenticated but unauthorized roles. If access denied, RBAC may be the cause.",
            ),
            Contradiction(
                label="Complex authentication flow",
                description="The application may require a complex multi-step authentication flow (OTP, 2FA, etc.) beyond simple token validation.",
                confidence_reduction=0.2,
                how_to_rule_out="Observe authentication challenges or additional verification steps. If detected, complex flow may exist.",
            ),
        ]

    # ── Generic contradictions ───────────────────────────────────

    @staticmethod
    def _attack_generic(hypothesis: Hypothesis) -> list[Contradiction]:
        contradictions: list[Contradiction] = []

        if hypothesis.confidence < 0.5:
            contradictions.append(
                Contradiction(
                    label="Low confidence hypothesis",
                    description=f"The hypothesis confidence is only {hypothesis.confidence:.2f}, meaning the signals are weak. A triager would deprioritize this.",
                    confidence_reduction=0.2,
                    how_to_rule_out="Gather more evidence before investigating. Look for additional signals.",
                )
            )

        if hypothesis.severity == "low":
            contradictions.append(
                Contradiction(
                    label="Low severity reduces triage priority",
                    description="Triagers prioritize high/critical severity findings. Low severity findings may not be triaged at all.",
                    confidence_reduction=0.1,
                    how_to_rule_out=None,
                )
            )

        if not hypothesis.reproducibility_notes:
            contradictions.append(
                Contradiction(
                    label="Missing reproduction steps",
                    description="Without clear reproduction steps, a triager cannot verify the finding. This is the #1 reason for 'cannot reproduce' rejections.",
                    confidence_reduction=0.3,
                    how_to_rule_out="Add precise steps: which account, which request, expected vs actual response.",
                )
            )

        if not hypothesis.alternative_explanations:
            contradictions.append(
                Contradiction(
                    label="No alternative explanations considered",
                    description="The hypothesis did not consider alternative explanations. A triager will — and may find one that invalidates the finding.",
                    confidence_reduction=0.15,
                    how_to_rule_out="Run through common alternative explanations for this vulnerability type.",
                )
            )

        return contradictions
