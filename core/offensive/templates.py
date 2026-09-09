"""Templates — IDOR patterns, alternative explanations, and test patterns.

Organized by vulnerability type, following the same pattern as
``cores/validation/challenger.py``.
"""

from __future__ import annotations

from typing import Any

IDOR_PATTERNS: dict[str, Any] = {
    "path_indicators": [
        "{id}",
        "{user_id}",
        "{userId}",
        "{uid}",
        "{account_id}",
        "{customer_id}",
        "{document_id}",
        "{order_id}",
        "{file_id}",
        "{profile_id}",
    ],
    "param_indicators": [
        "id",
        "user_id",
        "userId",
        "uid",
        "account_id",
        "accountId",
        "customer_id",
        "customerId",
        "profile_id",
        "profileId",
        "document_id",
        "documentId",
        "file_id",
        "fileId",
        "owner",
        "owner_id",
        "ownerId",
    ],
    "test_instructions": [
        "Create two distinct user accounts (A and B).",
        "Authenticate as user A and obtain a valid identifier.",
        "Authenticate as user B and substitute A's identifier.",
        "If user A's data is accessible — it's IDOR.",
    ],
}

IDOR_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "idor": [
        {
            "label": "Ownership verified server-side",
            "description": "The server checks that the requested resource belongs to the authenticated user before returning it.",
            "how_to_rule_out": "Try accessing a resource belonging to a different user. If blocked, ownership is working.",
        },
        {
            "label": "Public resource misidentified",
            "description": "The resource might be intentionally public (e.g., a public profile) and not an authorization failure.",
            "how_to_rule_out": "Verify if the endpoint requires authentication. If not, the resource may be intentionally public.",
        },
        {
            "label": "GUID/UUID not enumerable",
            "description": "The identifier is a non-guessable UUID, making exploitation infeasible even without authorization.",
            "how_to_rule_out": "Check if the ID follows a predictable pattern. If it's a random UUID, enumeration is impractical.",
        },
        {
            "label": "Rate limiting prevents abuse",
            "description": "The endpoint may enforce rate limits that prevent mass enumeration or brute-force of identifiers.",
            "how_to_rule_out": "Check response headers for X-RateLimit-* or similar. Send multiple requests and observe blocking.",
        },
        {
            "label": "Indirect reference map (IRM)",
            "description": "The server uses an indirect reference (e.g., session-scoped mapping) rather than the direct identifier.",
            "how_to_rule_out": "Try the same request with a different session. If IDs are session-scoped, the attack fails.",
        },
    ],
}

SSRF_ALTERNATIVES: list[dict[str, str]] = [
    {
        "label": "Outbound traffic blocked by firewall",
        "description": "The server may have egress filtering that prevents connections to internal or external targets.",
        "how_to_rule_out": "Try a collaborator/request bin first. If no callback, egress filtering may be in place.",
    },
    {
        "label": "URL allowlist restricts destinations",
        "description": "Only specific domains/IPs are allowed for outbound requests.",
        "how_to_rule_out": "Try redirect-based bypass: allowed domain → redirect → internal IP.",
    },
    {
        "label": "DNS rebinding protection active",
        "description": "The server validates that the resolved IP matches the original hostname at request time.",
        "how_to_rule_out": "Try multiple DNS lookups with short TTL, or use IPv6 variants.",
    },
    {
        "label": "Protocol restriction (HTTP(S) only)",
        "description": "Non-HTTP protocols (file://, gopher://, dict://) may be explicitly blocked.",
        "how_to_rule_out": "Try these protocols and observe if errors differ from HTTP-based SSRF attempts.",
    },
]

AUTH_BYPASS_ALTERNATIVES: list[dict[str, str]] = [
    {
        "label": "Endpoint is intentionally public",
        "description": "The endpoint may be designed to be accessible without authentication.",
        "how_to_rule_out": "Check if the endpoint exposes sensitive data. Public endpoints should not return PII.",
    },
    {
        "label": "Auth enforced at different layer",
        "description": "Authorization may be handled by a reverse proxy, API gateway, or service mesh — not the application.",
        "how_to_rule_out": "Try bypassing the gateway (direct IP access, alternative hostnames).",
    },
    {
        "label": "Session validation via cookies",
        "description": "Even without Authorization header, the server may validate session cookies.",
        "how_to_rule_out": "Remove both Authorization header and session cookies. If still accessible, auth is truly missing.",
    },
    {
        "label": "CORS misconfiguration, not auth bypass",
        "description": "What looks like an auth bypass may be CORS misconfiguration (different origin, same auth).",
        "how_to_rule_out": "Test with credentials from a different user account, not just a different origin.",
    },
]

XSS_ALTERNATIVES: list[dict[str, str]] = [
    {
        "label": "HTML encoding prevents execution",
        "description": "The application may HTML-encode user input, preventing script execution even though the payload is reflected.",
        "how_to_rule_out": "Check the raw response for encoding. &lt;script&gt; (encoded) vs <script> (raw).",
    },
    {
        "label": "CSP blocks arbitrary script execution",
        "description": "A strict Content-Security-Policy may prevent inline script execution even if injection exists.",
        "how_to_rule_out": "Check CSP headers. Look for script-src with nonce or hash.",
    },
    {
        "label": "SameSite cookies limit impact",
        "description": "Cookies with SameSite=Lax/Strict may prevent cookie theft via XSS.",
        "how_to_rule_out": "Check Set-Cookie headers for SameSite attribute.",
    },
    {
        "label": "Input is sanitized server-side",
        "description": "The server may strip or sanitize HTML/script tags before reflecting user input.",
        "how_to_rule_out": "Try polyglot payloads, nested encodings, or context-specific bypasses.",
    },
]

SQLI_ALTERNATIVES: list[dict[str, str]] = [
    {
        "label": "ORM / parameterized query in use",
        "description": "The application likely uses parameterized queries or an ORM that prevents SQL injection.",
        "how_to_rule_out": "Try advanced payloads that exploit specific ORM edge cases (e.g., NoSQL injection, HQL injection).",
    },
    {
        "label": "WAF blocks SQL injection payloads",
        "description": "A Web Application Firewall may block SQL injection patterns before they reach the application.",
        "how_to_rule_out": "Try WAF bypass techniques: encoding, case variation, comment injection, parameter pollution.",
    },
    {
        "label": "Error messages suppressed",
        "description": "The application may suppress database errors, but SQL injection may still work via blind techniques.",
        "how_to_rule_out": "Test time-based and boolean-based blind SQL injection techniques.",
    },
    {
        "label": "Input type validation (numeric expected)",
        "description": "If the parameter expects an integer, the application may reject non-numeric input before database interaction.",
        "how_to_rule_out": "Test with numeric payloads that preserve the integer type: 1 OR 1=1, 1 AND SLEEP(5).",
    },
]

ALTERNATIVES_BY_TYPE: dict[str, list[dict[str, str]]] = {
    "idor": IDOR_ALTERNATIVES["idor"],
    "ssrf": SSRF_ALTERNATIVES,
    "auth_bypass": AUTH_BYPASS_ALTERNATIVES,
    "xss": XSS_ALTERNATIVES,
    "sqli": SQLI_ALTERNATIVES,
}

SCOPE_QUESTIONS: dict[str, list[str]] = {
    "idor": [
        "Is the endpoint authenticated?",
        "Does the program have a clear authorization test policy?",
        "Is mass enumeration explicitly out of scope?",
        "Are there separate rate limits for authenticated endpoints?",
    ],
    "ssrf": [
        "Is SSRF explicitly in scope for this program?",
        "Does the program allow out-of-band (OOB) testing?",
        "Is there a known cloud provider (AWS/GCP/Azure)?",
        "Are there rate limits on the endpoint?",
    ],
    "auth_bypass": [
        "What authentication mechanisms are supported (JWT, OAuth, Session)?",
        "Is there a public API key vs authenticated user distinction?",
        "Are there CORS restrictions that limit exploitation?",
        "Does the program have a clear auth bypass testing boundary?",
    ],
    "xss": [
        "Is the input reflected immediately or stored?",
        "Does the program consider stored XSS as higher impact?",
        "Is there a CSP that limits exploitation?",
        "Does the output context allow for JavaScript execution?",
    ],
    "sqli": [
        "What database technology is known/expected?",
        "Is SQL injection explicitly in scope?",
        "Are there rate limits on the endpoint?",
        "Does the program allow time-based testing?",
    ],
}
