"""Curiosity Engine — generates expert-level questions about an endpoint.

Unlike reasoners that produce answers (hypotheses), the Curiosity Engine
produces questions. It identifies what a human expert would wonder about:

  - "What if the auth check is on GET but not PUT?"
  - "What if the user_id can be passed as a header instead of path?"
  - "What endpoints share this object ID pattern?"
  - "What if there's a race condition between auth and data fetch?"
"""

from __future__ import annotations

import logging
from typing import Any

from core.offensive.models import CuriosityQuestion, CuriosityResult, Hypothesis

logger = logging.getLogger("orion.core.offensive.curiosity")

CATEGORY_WEIGHTS: dict[str, float] = {
    "auth": 0.25,
    "logic": 0.25,
    "business": 0.20,
    "technical": 0.15,
    "edge_case": 0.15,
}

IDOR_QUESTIONS: list[dict[str, Any]] = [
    {
        "question": "What if the authorization check only applies to GET but PUT/PATCH/DELETE skip it?",
        "category": "auth",
        "rationale": "Many APIs verify ownership on read operations but forget to check on write operations.",
        "test_suggestion": "Try modifying B's resource with A's session using PUT/PATCH/DELETE.",
    },
    {
        "question": "What if the object ID can be passed in a header or cookie instead of the URL?",
        "category": "auth",
        "rationale": "Authorization may be path-based but not header-based, creating a bypass.",
        "test_suggestion": "Try X-Object-Id: <id> header or cookie-based resource selection.",
    },
    {
        "question": "What if this endpoint returns data in a different format that bypasses filtering?",
        "category": "technical",
        "rationale": "Response formatting may strip certain fields or apply different auth rules per content type.",
        "test_suggestion": "Try Accept: application/xml, text/csv, application/vnd.api+json, text/plain.",
    },
    {
        "question": "What if the ID is validated as an integer but passed as an array/object?",
        "category": "edge_case",
        "rationale": "PHP/Node.js/Ruby may handle type confusion differently than the auth logic expects.",
        "test_suggestion": 'Try id=1&id=2 (parameter pollution), id[]=1, id[0]=1, {"id": [1,2]}.',
    },
    {
        "question": "What if there's a race condition between the auth check and the data fetch?",
        "category": "logic",
        "rationale": "TOCTOU bugs are rare but high-impact. Swap the session token between auth and fetch.",
        "test_suggestion": "Send concurrent requests swapping the session cookie between requests.",
    },
    {
        "question": "What if the same ID resolves differently depending on the session state?",
        "category": "logic",
        "rationale": "Indirect reference maps (IRM) may map IDs per-session. Check if the same ID returns different data from different sessions.",
        "test_suggestion": "Log in as A, capture response for /resource/123. Log in as B, request /resource/123. Compare responses.",
    },
    {
        "question": "What if the endpoint is behind a CDN cache that returns stale/other users' data?",
        "category": "technical",
        "rationale": "Misconfigured CDN caching can serve user A's data to user B via cache hits.",
        "test_suggestion": "Add cache-busting params, check for CF-Cache-Status: HIT, vary cookies between requests.",
    },
    {
        "question": "What if the real vulnerability is in a sibling endpoint, not this one?",
        "category": "technical",
        "rationale": "The pattern suggests a family of endpoints — another one may have weaker auth.",
        "test_suggestion": "Map all endpoints with the same path template and test each with the same technique.",
    },
    {
        "question": "What if an IDOR here can chain into a higher-privilege action?",
        "category": "business",
        "rationale": "Leaking a user ID might seem low impact, but combined with another endpoint could enable account takeover.",
        "test_suggestion": "Use leaked data as input to adjacent endpoints, especially password change, email change, 2FA disable.",
    },
    {
        "question": "What if the same endpoint behaves differently with HTTP/1.1 vs HTTP/2?",
        "category": "edge_case",
        "rationale": "HTTP/2 handling may differ in middleware, especially for header-based auth checks.",
        "test_suggestion": "Switch between HTTP/1.1 and HTTP/2, observe response differences.",
    },
]

SSRF_QUESTIONS: list[dict[str, Any]] = [
    {
        "question": "What if the SSRF filter only checks the hostname, not the resolved IP?",
        "category": "technical",
        "rationale": "DNS pinning/rebinding can bypass hostname-based allowlists.",
        "test_suggestion": "Use a domain that initially resolves to an allowed IP, then switches to 127.0.0.1.",
    },
    {
        "question": "What if the application follows redirects and the first redirect lands on internal IP?",
        "category": "logic",
        "rationale": "Server-side redirect following can bypass initial URL validation.",
        "test_suggestion": "Set up a URL that returns 302 redirect to http://169.254.169.254/.",
    },
    {
        "question": "What if file:// protocol can read local application source code?",
        "category": "technical",
        "rationale": "Source code reveals API keys, internal endpoints, and business logic.",
        "test_suggestion": "Try file:///etc/passwd, file:///proc/self/environ, file:///app/config.py.",
    },
    {
        "question": "What if the target is behind a load balancer and SSRF hits a different backend node?",
        "category": "technical",
        "rationale": "Internal service discovery via load balancer internal IP ranges.",
        "test_suggestion": "Try internal IP ranges of known cloud providers (10.x.x.x for AWS VPC).",
    },
]

AUTH_BYPASS_QUESTIONS: list[dict[str, Any]] = [
    {
        "question": "What if the auth middleware checks a prefix but path traversal bypasses the check?",
        "category": "auth",
        "rationale": "Path normalization differences between middleware and application create bypasses.",
        "test_suggestion": "Try /admin/../api/users, /api/../admin/users, //api/admin/users.",
    },
    {
        "question": "What if the JWT is verified but the audience/issuer claim is not checked?",
        "category": "auth",
        "rationale": "Tokens from other services may be accepted, enabling cross-service escalation.",
        "test_suggestion": "Try a token issued for a different service/audience on this endpoint.",
    },
    {
        "question": "What if there is no CSRF protection on state-changing endpoints?",
        "category": "auth",
        "rationale": "CSRF + known endpoints = account takeover without knowing the victim's password.",
        "test_suggestion": "Try making a cross-origin request from a different origin without custom headers.",
    },
    {
        "question": "What if rate limiting is only on auth endpoints, not on data access endpoints?",
        "category": "business",
        "rationale": "No rate limiting on data access enables mass data harvesting once auth is bypassed.",
        "test_suggestion": "Send 100 rapid requests to the data endpoint and check for 429 responses.",
    },
]

_QUESTIONS_BY_TYPE: dict[str, list[dict[str, Any]]] = {
    "idor": IDOR_QUESTIONS,
    "ssrf": SSRF_QUESTIONS,
    "auth_bypass": AUTH_BYPASS_QUESTIONS,
    "xss": [
        {
            "question": "What if the XSS filter only checks <script> but not event handlers?",
            "category": "technical",
            "rationale": "Event handlers (onload, onerror, onfocus) often bypass naive filters.",
            "test_suggestion": "Try <img src=x onerror=alert(1)>, <body onload=alert(1)>.",
        },
        {
            "question": "What if the CSP header is present but allows unsafe-inline or unsafe-eval?",
            "category": "technical",
            "rationale": "Misconfigured CSP can be bypassed with known techniques.",
            "test_suggestion": "Check for 'unsafe-inline', 'unsafe-eval', or missing object-src.",
        },
    ],
    "sqli": [
        {
            "question": "What if the endpoint uses an ORM that's vulnerable to NoSQL injection?",
            "category": "technical",
            "rationale": "MongoDB/Mongoose $where, $gt operators can bypass ORM query building.",
            "test_suggestion": "Try {'$gt': ''}, {'$ne': ''}, admin' && this.password.match(/^a/) || true",
        },
        {
            "question": "What if the SQL error is suppressed but the injection still works blind?",
            "category": "technical",
            "rationale": "Time-based and boolean-based blind SQLi work without error messages.",
            "test_suggestion": "Try ' AND SLEEP(5)--, ' OR '1'='1' AND BENCHMARK(10000000,MD5(1))--",
        },
    ],
    "generic": IDOR_QUESTIONS[:6],
}

BLIND_SPOTS_BY_TYPE: dict[str, list[str]] = {
    "idor": [
        "No information about the authorization model (RBAC, ABAC, ACL, per-ownership)",
        "No visibility into rate limiting configuration",
        "Unknown if audit logging detects anomalous access patterns",
        "Unknown if there are write-only endpoints that accept the same ID",
    ],
    "ssrf": [
        "No visibility into internal network topology",
        "Unknown cloud provider (AWS/GCP/Azure/Oracle/private)",
        "Unknown if outbound traffic filtering is in place",
        "Unknown internal service discovery mechanisms",
    ],
    "auth_bypass": [
        "Unknown auth middleware stack (order matters for bypasses)",
        "Unknown if WAF/API gateway applies additional auth rules",
        "Unknown JWT verification implementation (alg whitelist, key rotation)",
    ],
    "xss": [
        "No visibility into client-side JS frameworks and their XSS protections",
        "Unknown CSP headers and their effectiveness",
        "Unknown if user input reaches dangerous DOM sinks",
    ],
    "sqli": [
        "Unknown database type and version",
        "Unknown ORM framework and its escaping behavior",
        "Unknown WAF rules specific to SQL injection patterns",
    ],
    "generic": [
        "No endpoint authentication requirements mapped",
        "No rate limiting or throttling information",
        "No data about the user's privilege level relative to the endpoint's requirements",
    ],
}


class CuriosityEngine:
    """Generates expert-level questions and identifies blind spots.

    Usage::

        engine = CuriosityEngine()
        result = engine.explore(hypothesis)
        for q in result.questions:
            print(q.question)
    """

    def explore(self, hypothesis: Hypothesis) -> CuriosityResult:
        """Generate questions and identify blind spots for a hypothesis."""
        vtype = hypothesis.vulnerability_type
        raw_questions = _QUESTIONS_BY_TYPE.get(vtype, _QUESTIONS_BY_TYPE["generic"])

        questions = [
            CuriosityQuestion(
                question=q["question"],
                category=q["category"],
                rationale=q["rationale"],
                test_suggestion=q["test_suggestion"],
            )
            for q in raw_questions
        ]

        blind_spots = list(BLIND_SPOTS_BY_TYPE.get(vtype, BLIND_SPOTS_BY_TYPE["generic"]))

        recommended_focus = self._recommend_focus(vtype, hypothesis, questions)

        return CuriosityResult(
            endpoint=hypothesis.endpoint,
            method=hypothesis.method,
            vulnerability_type=vtype,
            questions=questions,
            blind_spots=blind_spots,
            recommended_focus=recommended_focus,
        )

    def explore_endpoint(
        self,
        path: str,
        method: str,
        vuln_type: str = "idor",
        params: list[str] | None = None,
    ) -> CuriosityResult:
        """Generate curiosity questions for an endpoint without a full hypothesis.

        Useful for quick exploration during manual review.
        """
        raw_questions = _QUESTIONS_BY_TYPE.get(vuln_type, _QUESTIONS_BY_TYPE["generic"])

        questions = [
            CuriosityQuestion(
                question=q["question"],
                category=q["category"],
                rationale=q["rationale"],
                test_suggestion=q["test_suggestion"],
            )
            for q in raw_questions
        ]

        blind_spots = list(BLIND_SPOTS_BY_TYPE.get(vuln_type, BLIND_SPOTS_BY_TYPE["generic"]))
        recommended_focus = "Explore sibling and child endpoints first, then follow the auth question chain."

        return CuriosityResult(
            endpoint=path,
            method=method,
            vulnerability_type=vuln_type,
            questions=questions,
            blind_spots=blind_spots,
            recommended_focus=recommended_focus,
        )

    @staticmethod
    def _recommend_focus(vtype: str, hypothesis: Hypothesis, questions: list[CuriosityQuestion]) -> str:
        if not questions:
            return "No specific focus recommended."
        cat_scores: dict[str, float] = {}
        for q in questions:
            w = CATEGORY_WEIGHTS.get(q.category, 0.1)
            cat_scores[q.category] = cat_scores.get(q.category, 0) + w
        if not cat_scores:
            return "Review all questions systematically."
        best_cat = max(cat_scores, key=lambda k: cat_scores[k])
        return f"Focus on {best_cat}-related questions first, then address identified blind spots."
