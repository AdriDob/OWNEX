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

PROMPT_INJECTION_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "prompt_injection": [
        {
            "label": "System instructions are fixed server-side",
            "description": "The model call may use a fixed server-side system prompt and treat all caller input as untrusted data, not instructions.",
            "how_to_rule_out": "Attempt instruction override and system-content extraction. If the model never deviates, instructions are fixed.",
        },
        {
            "label": "Output filtering and guardrails in place",
            "description": "A moderation layer or output filter may block leaked instructions, disallowed content, and tool abuse.",
            "how_to_rule_out": "Test multi-turn exfiltration (split the secret across turns) and encoded outputs.",
        },
        {
            "label": "Low-privilege tool sandbox",
            "description": "Connected tools may run with minimal permissions on non-sensitive data, limiting injection impact.",
            "how_to_rule_out": "Map every connected tool and the data it touches before claiming impact.",
        },
        {
            "label": "Human review before consequential actions",
            "description": "Sensitive operations may require human approval, so a steered model alone cannot complete the attack.",
            "how_to_rule_out": "Trace the full action path: if a human gate stands before the payout action, impact is contained.",
        },
        {
            "label": "Not an LLM endpoint (keyword coincidence)",
            "description": "Words like 'chat', 'ask' or 'message' may belong to a plain CRUD/support feature with no model behind it.",
            "how_to_rule_out": "Probe with a nonsense instruction: a non-LLM endpoint returns static or template output.",
        },
    ],
}


BACL_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "bacl": [
        {
            "label": "Role checked server-side per object",
            "description": "The server verifies the caller's role against the specific object on every request, regardless of visible params.",
            "how_to_rule_out": "Same identifier as two roles: identical allow/deny behavior means checks hold.",
        },
        {
            "label": "Role param is display-only",
            "description": "The visible role indicator is cosmetic; the real authorization comes from the session.",
            "how_to_rule_out": "Tamper the role param without changing the session. No behavior change = cosmetic.",
        },
        {
            "label": "Admin path behind middleware",
            "description": "The /admin prefix may be enforced by gateway middleware before the app ever sees the request.",
            "how_to_rule_out": "Request the admin path with a low-priv session. A 403/redirect from the edge proves middleware.",
        },
        {
            "label": "Same data scope for both roles",
            "description": "Both roles may legitimately see the same fields (e.g., own profile shape).",
            "how_to_rule_out": "Request another user's object, not your own. Cross-user data = real gap.",
        },
    ],
}

BUSINESS_FLOW_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "business_logic": [
        {
            "label": "Server recomputes price server-side",
            "description": "Totals, discounts and fees are recalculated from catalog data; caller values are echoed, not trusted.",
            "how_to_rule_out": "Tamper price/quantity and compare the charged total. Unchanged total = recomputed.",
        },
        {
            "label": "Idempotency keys enforced",
            "description": "Replays and double-submits collapse into one effect via idempotency keys.",
            "how_to_rule_out": "Double-submit the same operation. Single side effect = idempotent.",
        },
        {
            "label": "Payment verified by provider webhook",
            "description": "The final amount is confirmed by the payment provider callback, not the client request.",
            "how_to_rule_out": "Complete a tampered checkout and check what was actually charged.",
        },
        {
            "label": "State machine enforced",
            "description": "Skipped or reordered steps are rejected because the backend tracks flow state.",
            "how_to_rule_out": "Skip a step (e.g., pay) and call the next one. An error means the machine holds.",
        },
    ],
}


GRAPHQL_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "graphql": [
        {
            "label": "Introspection disabled in production",
            "description": "The schema query may return an error while the API itself works normally.",
            "how_to_rule_out": "Send {__schema{queryType{name}}}. A clean error with working operations = disabled.",
        },
        {
            "label": "Cost/depth analysis enforced",
            "description": "The server may compute query complexity and reject expensive queries.",
            "how_to_rule_out": "Grow nesting one level at a time up to the safe cap. Rejection = enforced.",
        },
        {
            "label": "Batching limited or disabled",
            "description": "Multiple aliases per request may be rejected or collapse into one execution.",
            "how_to_rule_out": "Send the small capped batch. Error or single execution = limited.",
        },
        {
            "label": "Field resolvers re-check authorization",
            "description": "Each field may enforce the caller's role even when the schema is visible.",
            "how_to_rule_out": "Same field query as two roles. Identical allow/deny = enforced.",
        },
    ],
}


OAUTH_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "oauth": [
        {
            "label": "Redirect allowlist enforced",
            "description": "The redirect_uri is validated against a registered allowlist; tampered values are rejected.",
            "how_to_rule_out": "Send an attacker redirect_uri. An error naming the allowlist = enforced.",
        },
        {
            "label": "State bound to session",
            "description": "The state value is tied to the login session and single-use, blocking login CSRF.",
            "how_to_rule_out": "Drop or replay state across sessions. Rejection = bound.",
        },
        {
            "label": "PKCE S256 required",
            "description": "Public clients must use S256 code_challenge; plain/none is refused.",
            "how_to_rule_out": "Omit the challenge or send plain. Refusal = required.",
        },
        {
            "label": "Short-lived single-use codes",
            "description": "Codes expire in seconds and burn on first use, so a leak alone rarely replays.",
            "how_to_rule_out": "Replay a captured code in a second session. Failure = single-use.",
        },
    ],
}


DESERIALIZATION_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "deserialization": [
        {
            "label": "Output escaped, not rendered",
            "description": "The input is reflected HTML-escaped or as plain text, never evaluated as template code.",
            "how_to_rule_out": "Send the benign math probe. Literal echo (not 49) = escaped.",
        },
        {
            "label": "Sandboxed template engine",
            "description": "The engine runs in sandbox mode without object access or dangerous tags.",
            "how_to_rule_out": "Try object traversal after the math hit. Blocked = sandboxed (still reportable as low).",
        },
        {
            "label": "Safe deserializer (allowlist)",
            "description": "Only allowlisted classes/primitives deserialize; the rest raise.",
            "how_to_rule_out": "Send a tagged exotic class. Clean error = allowlisted.",
        },
        {
            "label": "Keyword coincidence (view/page params)",
            "description": "Common param names (view, page, name) may map to static files, not rendering.",
            "how_to_rule_out": "Math probe decides: no evaluation = coincidence.",
        },
    ],
}


CMDI_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "cmdi": [
        {
            "label": "Input passed to safe API, not shell",
            "description": "The parameter may be used in a subprocess call with shell=False and argument list, preventing injection.",
            "how_to_rule_out": "Try ; cat /etc/passwd. If it returns literal text or error, shell is not invoked.",
        },
        {
            "label": "Allowlist of allowed commands",
            "description": "The server may validate the command against a fixed allowlist before execution.",
            "how_to_rule_out": "Try a command not in typical allowlists (e.g., 'id'). Rejection = allowlist.",
        },
        {
            "label": "Container without shell",
            "description": "The runtime may be a minimal container (distroless) without /bin/sh, making shell injection impossible.",
            "how_to_rule_out": "Try 'which sh' or 'ls /bin/sh'. Clean error or missing = no shell.",
        },
        {
            "label": "WAF blocks shell metacharacters",
            "description": "A WAF may strip or block ; & | $ ( ) ` before the application sees them.",
            "how_to_rule_out": "Try encoded variants (URL, Unicode). If blocked but plain works, WAF is the barrier.",
        },
        {
            "label": "Keyword coincidence (deploy/build tools)",
            "description": "Params like 'cmd', 'run', 'exec' may belong to CI/CD or build tools, not a shell.",
            "how_to_rule_out": "Math probe decides: no evaluation = coincidence.",
        },
    ],
}

LFI_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "lfi": [
        {
            "label": "Path resolved via safe API (realpath + allowlist)",
            "description": "The server may resolve the path with realpath() and validate it against an allowlist directory.",
            "how_to_rule_out": "Try ../etc/passwd. If it resolves outside allowlist and returns 404/error, allowlist works.",
        },
        {
            "label": "Static file server (no dynamic include)",
            "description": "The endpoint may serve files from a static directory without any path processing.",
            "how_to_rule_out": "Request a non-existent file. 404 with no path traversal attempt = static server.",
        },
        {
            "label": "Extension whitelist enforced",
            "description": "Only specific extensions (.txt, .pdf, .log) are allowed; others rejected.",
            "how_to_rule_out": "Try .php, .jsp, .asp extensions. Rejection = whitelist.",
        },
        {
            "label": "Chroot / container isolation",
            "description": "The process may be chrooted or in a container where /etc/passwd is not the host's.",
            "how_to_rule_out": "/etc/passwd returns container users (often just root). Still LFI, but limited impact.",
        },
        {
            "label": "Keyword coincidence (document viewers)",
            "description": "Params like 'file', 'doc', 'page' may belong to a document viewer with no path control.",
            "how_to_rule_out": "Benign probe returns viewer UI, not file contents = coincidence.",
        },
    ],
}

RACE_CONDITION_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "race_condition": [
        {
            "label": "Idempotency key enforced per operation",
            "description": "The server requires a unique idempotency key for each mutating request; duplicates are collapsed.",
            "how_to_rule_out": "Send same request with same idempotency key. Single effect = enforced.",
        },
        {
            "label": "Database row-level locking",
            "description": "The operation uses SELECT FOR UPDATE or equivalent pessimistic locking.",
            "how_to_rule_out": "Concurrent requests queue and serialize. No duplicate effect = locked.",
        },
        {
            "label": "Optimistic concurrency control (version/timestamp)",
            "description": "Each record has a version; updates fail if version changed since read.",
            "how_to_rule_out": "Concurrent requests: one succeeds, others fail with version conflict.",
        },
        {
            "label": "Distributed lock (Redis/ZooKeeper)",
            "description": "A distributed mutex protects the critical section across instances.",
            "how_to_rule_out": "Concurrent requests serialize. Lock acquisition visible in logs = distributed lock.",
        },
        {
            "label": "Single-threaded runtime (no concurrency)",
            "description": "The endpoint runs in a single-threaded environment (e.g., Python GIL without workers).",
            "how_to_rule_out": "Concurrent requests queue at OS level. No parallelism = no race window.",
        },
        {
            "label": "Rate limit masks race window",
            "description": "A strict rate limit (e.g., 1 req/s) makes concurrent exploitation impractical.",
            "how_to_rule_out": "Check rate limit headers. If 1 req/s, race window is ~1s but hard to hit.",
        },
    ],
}

CORS_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "cors": [
        {
            "label": "Origin allowlist enforced",
            "description": "The server validates Origin against a registered allowlist and rejects unknown origins.",
            "how_to_rule_out": "Send Origin: https://evil.com. Rejection or non-reflection = allowlist.",
        },
        {
            "label": "Credentials not allowed with wildcard",
            "description": "The spec forbids Access-Control-Allow-Credentials: true with Allow-Origin: *. Server may ignore credentials.",
            "how_to_rule_out": "Test with credentials. If cookies not sent despite Allow-Credentials, wildcard blocks it.",
        },
        {
            "label": "SameSite cookies mitigate impact",
            "description": "Cookies with SameSite=Lax/Strict are not sent on cross-site requests even if CORS allows it.",
            "how_to_rule_out": "Check Set-Cookie headers. Lax/Strict = mitigated for most cross-origin cases.",
        },
        {
            "label": "Preflight required for non-simple requests",
            "description": "Custom headers or non-simple methods trigger preflight; server can reject there.",
            "how_to_rule_out": "Send request with custom header. Preflight rejection = protected.",
        },
        {
            "label": "API only consumed by first-party SPA",
            "description": "The API may be designed for a single SPA origin; permissive CORS is intentional but scoped.",
            "how_to_rule_out": "Check if the API is public or internal. Internal-only = lower risk.",
        },
    ],
}

CSRF_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "csrf": [
        {
            "label": "SameSite=Lax/Strict cookies",
            "description": "Cookies with SameSite=Lax are not sent on cross-site subrequests (forms, iframes). Strict blocks all cross-site.",
            "how_to_rule_out": "Check Set-Cookie headers. Lax/Strict = CSRF mitigated for most vectors.",
        },
        {
            "label": "Double-submit cookie pattern",
            "description": "Server sets a CSRF cookie and expects the same value in a custom header or body param.",
            "how_to_rule_out": "Check for cookie + header/param pair. Absence in our static analysis ≠ absence in reality.",
        },
        {
            "label": "Custom header required (X-Requested-With, etc.)",
            "description": "The endpoint may require a custom header that browsers don't send cross-origin without CORS.",
            "how_to_rule_out": "Check if request works without the header. Failure = header required.",
        },
        {
            "label": "Referer/Origin header validation",
            "description": "Server validates that Referer or Origin matches expected origin.",
            "how_to_rule_out": "Send request with spoofed Origin. Rejection = validation.",
        },
        {
            "label": "Single-page app with anti-CSRF in framework",
            "description": "Modern frameworks (React, Vue, Angular) often inject CSRF tokens automatically.",
            "how_to_rule_out": "Inspect network tab for token in requests. Our static analysis may miss it.",
        },
        {
            "label": "Read-only endpoint (GET misclassified)",
            "description": "The endpoint may be a GET that we flagged, but GETs shouldn't mutate state.",
            "how_to_rule_out": "Verify method is actually mutating. If GET, it's not CSRF (but may be other issue).",
        },
    ],
}

OPEN_REDIRECT_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "open_redirect": [
        {
            "label": "Allowlist of allowed redirect destinations",
            "description": "The server validates the redirect URL against a registered allowlist of domains/paths.",
            "how_to_rule_out": "Try redirect to https://evil.com. Rejection = allowlist.",
        },
        {
            "label": "Relative paths only (no absolute URLs)",
            "description": "The server only accepts relative paths (/dashboard, /settings) and rejects absolute URLs.",
            "how_to_rule_out": "Try https://evil.com. Rejection or relative-only = safe.",
        },
        {
            "label": "Domain suffix validation",
            "description": "The server validates that the redirect domain matches *.target.com or similar.",
            "how_to_rule_out": "Try subdomain.evil.com. Rejection = suffix validation.",
        },
        {
            "label": "User confirmation page",
            "description": "The redirect goes through an intermediate page asking 'Leave site?'",
            "how_to_rule_out": "Check if redirect is immediate or shows a confirmation page.",
        },
        {
            "label": "State parameter binds redirect to session",
            "description": "OAuth/OpenID Connect flows use state to bind redirect_uri to the login session.",
            "how_to_rule_out": "Check if state is required and validated. Missing state = bypassable.",
        },
        {
            "label": "Keyword coincidence (navigation helpers)",
            "description": "Params like 'next', 'continue', 'goto' may be for internal navigation only.",
            "how_to_rule_out": "Test with relative path. Works internally but rejects external = internal nav.",
        },
    ],
}

GENERIC_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "generic": [
        {
            "label": "Anomaly is expected behavior",
            "description": "The flagged behavior (e.g., debug endpoint, verbose errors) may be intentional for development/staging environments.",
            "how_to_rule_out": "Check if target is production. Verify with program policy if debug features are in scope.",
        },
        {
            "label": "Security headers missing but mitigated elsewhere",
            "description": "Missing headers (CSP, HSTS, etc.) may be enforced at CDN/WAF/load balancer layer.",
            "how_to_rule_out": "Test via direct IP/origin bypass. Check if headers appear when hitting origin directly.",
        },
        {
            "label": "Error messages are genericized in production",
            "description": "Stack traces/debug info may only appear in non-production environments.",
            "how_to_rule_out": "Verify target environment. Compare staging vs production responses.",
        },
        {
            "label": "Large payloads are legitimate (file upload, data import)",
            "description": "Endpoints accepting large payloads may be designed for file upload or bulk data operations.",
            "how_to_rule_out": "Check Content-Type and endpoint purpose. Legitimate upload endpoints have size limits and validation.",
        },
        {
            "label": "Admin/debug endpoints are IP-restricted",
            "description": "Exposed admin paths may be protected by IP allowlist, VPN, or network segmentation.",
            "how_to_rule_out": "Test from different IPs/networks. 403 from external = protected.",
        },
        {
            "label": "False positive from heuristic",
            "description": "Generic anomaly detection uses broad heuristics that may flag benign patterns.",
            "how_to_rule_out": "Manual review required. If no security impact after testing, mark as false positive.",
        },
    ],
}


ALTERNATIVES_BY_TYPE: dict[str, list[dict[str, str]]] = {
    "idor": IDOR_ALTERNATIVES["idor"],
    "ssrf": SSRF_ALTERNATIVES,
    "auth_bypass": AUTH_BYPASS_ALTERNATIVES,
    "xss": XSS_ALTERNATIVES,
    "sqli": SQLI_ALTERNATIVES,
    "prompt_injection": PROMPT_INJECTION_ALTERNATIVES["prompt_injection"],
    "bacl": BACL_ALTERNATIVES["bacl"],
    "business_logic": BUSINESS_FLOW_ALTERNATIVES["business_logic"],
    "graphql": GRAPHQL_ALTERNATIVES["graphql"],
    "oauth": OAUTH_ALTERNATIVES["oauth"],
    "deserialization": DESERIALIZATION_ALTERNATIVES["deserialization"],
    "cmdi": CMDI_ALTERNATIVES["cmdi"],
    "lfi": LFI_ALTERNATIVES["lfi"],
    "race_condition": RACE_CONDITION_ALTERNATIVES["race_condition"],
    "cors": CORS_ALTERNATIVES["cors"],
    "csrf": CSRF_ALTERNATIVES["csrf"],
    "open_redirect": OPEN_REDIRECT_ALTERNATIVES["open_redirect"],
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
    "cmdi": [
        "Is command injection explicitly in scope for this program?",
        "Does the program allow time-based testing (sleep/delay)?",
        "Is there a known shell environment (bash, sh, cmd.exe)?",
        "Are there rate limits on the endpoint?",
    ],
    "lfi": [
        "Is local file inclusion explicitly in scope?",
        "Does the program allow reading /etc/passwd or equivalent?",
        "Are there path traversal protections in scope?",
        "Is there a known OS (Linux/Windows) for path syntax?",
    ],
    "race_condition": [
        "Is race condition / concurrency testing explicitly allowed?",
        "Does the program have a clear policy on Turbo Intruder / single-packet attacks?",
        "Are there rate limits that would prevent concurrent requests?",
        "Is the target endpoint idempotent or state-mutating?",
    ],
    "cors": [
        "Is CORS misconfiguration testing in scope?",
        "Does the program allow OPTIONS preflight testing?",
        "Are credentials (cookies, auth headers) in scope for cross-origin?",
        "Is the API public or internal-only?",
    ],
    "csrf": [
        "Is CSRF testing explicitly in scope?",
        "Does the program consider SameSite=Lax as sufficient mitigation?",
        "Are there endpoints that change sensitive state (password, email, payment)?",
        "Does the program allow auto-submit form testing?",
    ],
    "open_redirect": [
        "Is open redirect / unvalidated redirect testing in scope?",
        "Does the program allow testing OAuth/OIDC redirect_uri?",
        "Are there known redirect parameters (next, return_url, callback)?",
        "Does the program allow testing with external domains?",
    ],
}
