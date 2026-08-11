"""Probes — individual probe implementations for each vulnerability type."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from core.http_probe.templates import ProbeTemplate

logger = logging.getLogger("ownex.http_probe.probes")

# ── HTTP response data ───────────────────────────────────────


@dataclass
class HttpResponse:
    """Normalized HTTP response from a probe request."""

    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""
    elapsed_ms: float = 0.0
    error: str = ""
    url: str = ""

    @property
    def is_error(self) -> bool:
        return bool(self.error)

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", self.headers.get("Content-Type", ""))

    @property
    def body_lower(self) -> str:
        return self.body.lower()


# ── Probe result ──────────────────────────────────────────────


@dataclass
class ProbeResult:
    """Result of executing a single probe against an endpoint."""

    hypothesis_id: str = ""
    vulnerability_type: str = ""
    endpoint: str = ""
    method: str = ""
    status: str = "unknown"  # confirmed / rejected / unknown
    confidence: float = 0.0
    evidence_snippets: list[str] = field(default_factory=list)
    indicators: list[str] = field(default_factory=list)
    probe_name: str = ""
    payload_used: dict[str, Any] = field(default_factory=dict)
    headers_used: dict[str, str] = field(default_factory=dict)
    baseline_response: HttpResponse | None = None
    probe_response: HttpResponse | None = None
    error: str = ""
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "vulnerability_type": self.vulnerability_type,
            "endpoint": self.endpoint,
            "method": self.method,
            "status": self.status,
            "confidence": round(self.confidence, 3),
            "evidence_snippets": self.evidence_snippets,
            "indicators": self.indicators,
            "probe_name": self.probe_name,
            "payload_used": self.payload_used,
            "headers_used": self.headers_used,
            "error": self.error,
            "elapsed_ms": round(self.elapsed_ms, 2),
        }


# ── Base probe ────────────────────────────────────────────────


class BaseProbe:
    """Base class for all vulnerability probes.

    Each probe knows how to:
    1. Build a baseline request (clean, no payload)
    2. Build probe requests (with payloads)
    3. Analyze responses for vulnerability indicators
    """

    def __init__(self) -> None:
        self._templates: list[ProbeTemplate] = []

    @property
    def vulnerability_type(self) -> str:
        raise NotImplementedError

    def build_baseline(
        self, endpoint: str, method: str, params: dict[str, str] | None = None, headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Build a clean baseline request (no malicious payload)."""
        return {
            "url": endpoint,
            "method": method.upper(),
            "params": {k: v for k, v in (params or {}).items() if not v.startswith("{")},
            "headers": dict(headers or {}),
        }

    def build_probe_requests(
        self,
        endpoint: str,
        method: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Build one or more probe requests with test payloads.

        Returns list of request dicts with 'url', 'method', 'params', 'headers', 'name', 'payload'.
        """
        raise NotImplementedError

    def analyze_responses(
        self,
        baseline: HttpResponse,
        probe_responses: list[HttpResponse],
        payload_used: dict[str, Any],
    ) -> tuple[str, float, list[str], list[str]]:
        """Analyze baseline vs probe responses.

        Returns (status, confidence, evidence_snippets, indicators).
        """
        raise NotImplementedError

    def _make_url(self, base: str, params: dict[str, str] | None) -> str:
        """Append params as query string to URL."""
        if not params:
            return base
        parsed = urlparse(base)
        existing = parse_qs(parsed.query)
        for k, v in params.items():
            existing[k] = [v]
        flat = {}
        for k, vals in existing.items():
            flat[k] = vals[0] if len(vals) == 1 else ",".join(vals)
        new_query = urlencode(flat)
        return urlunparse(parsed._replace(query=new_query))


# ── IDOR Probe ────────────────────────────────────────────────


class IDORProbe(BaseProbe):
    """Probe for IDOR: change numeric IDs in path/params, check for data leakage."""

    @property
    def vulnerability_type(self) -> str:
        return "idor"

    def build_probe_requests(
        self,
        endpoint: str,
        method: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        requests: list[dict[str, Any]] = []
        parsed = urlparse(endpoint)
        path_parts = [p for p in parsed.path.split("/") if p]

        # Strategy 1: Increment numeric path segments
        for i, part in enumerate(path_parts):
            if part.isdigit():
                alt_path = list(path_parts)
                alt_path[i] = str(int(part) + 1)
                new_path = "/" + "/".join(alt_path)
                new_url = urlunparse(parsed._replace(path=new_path))
                requests.append(
                    {
                        "url": new_url,
                        "method": method.upper(),
                        "params": {},
                        "headers": dict(headers or {}),
                        "name": f"idor_path_increment_{part}_to_{int(part) + 1}",
                        "payload": {"original": part, "modified": str(int(part) + 1)},
                    }
                )

        # Strategy 2: Change numeric query params
        clean_params = {k: v for k, v in (params or {}).items() if not v.startswith("{")}
        for k, v in clean_params.items():
            if v.isdigit():
                alt_params = dict(clean_params)
                alt_params[k] = str(int(v) + 1)
                requests.append(
                    {
                        "url": endpoint,
                        "method": method.upper(),
                        "params": alt_params,
                        "headers": dict(headers or {}),
                        "name": f"idor_param_{k}_{v}_to_{int(v) + 1}",
                        "payload": {k: str(int(v) + 1)},
                    }
                )

        # Strategy 3: Use well-known alternate IDs
        if not requests:
            for k in list(clean_params.keys())[:2]:
                alt_params = dict(clean_params)
                alt_params[k] = "999999"
                requests.append(
                    {
                        "url": endpoint,
                        "method": method.upper(),
                        "params": alt_params,
                        "headers": dict(headers or {}),
                        "name": f"idor_param_{k}_alternate",
                        "payload": {k: "999999"},
                    }
                )

        return requests

    def analyze_responses(
        self,
        baseline: HttpResponse,
        probe_responses: list[HttpResponse],
        payload_used: dict[str, Any],
    ) -> tuple[str, float, list[str], list[str]]:
        evidence: list[str] = []
        indicators: list[str] = []
        confidence = 0.0
        status = "rejected"

        if not probe_responses:
            return "unknown", 0.0, [], ["No probe responses received"]

        for resp in probe_responses:
            if resp.is_error:
                indicators.append(f"Probe request failed: {resp.error}")
                continue

            # Different status code = potential IDOR
            if baseline.status_code != resp.status_code:
                indicators.append(f"Status code changed: {baseline.status_code} -> {resp.status_code}")
                confidence += 0.3
                evidence.append(f"Baseline: {baseline.status_code}, Probe: {resp.status_code}, URL: {resp.url}")

            # 200 response with different content = possible data leakage
            if (
                resp.status_code == 200
                and baseline.status_code == 200
                and resp.body != baseline.body
                and len(resp.body) > 10
            ):
                indicators.append("Response body differs from baseline (possible data leakage)")
                confidence += 0.4
                snippet = resp.body[:500]
                evidence.append(f"Different content received: {snippet}")

            # 403 or 401 on probe = server properly enforces auth
            if resp.status_code in (401, 403):
                indicators.append(f"Server returned {resp.status_code} (authorization enforced)")
                confidence -= 0.3

        confidence = max(0.0, min(1.0, confidence))

        if confidence >= 0.5:
            status = "confirmed"
        elif confidence > 0.0:
            status = "unknown"
        else:
            status = "rejected"

        return status, confidence, evidence, indicators


# ── SSRF Probe ────────────────────────────────────────────────


class SSRFProbe(BaseProbe):
    """Probe for SSRF: inject internal/metadata URLs, check for response content."""

    INTERNAL_MARKERS = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "169.254.169.254",
        "metadata.google",
        "10.",
        "172.16",
        "192.168",
    ]
    METADATA_MARKERS = ["ami-id", "instance-id", "instance-type", "local-ipv4", "public-keys"]

    @property
    def vulnerability_type(self) -> str:
        return "ssrf"

    def build_probe_requests(
        self,
        endpoint: str,
        method: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        requests: list[dict[str, Any]] = []
        clean_params = {k: v for k, v in (params or {}).items() if not v.startswith("{")}

        ssrf_payloads = [
            ("http://127.0.0.1", "ssrf_localhost"),
            ("http://169.254.169.254/latest/meta-data/", "ssrf_metadata"),
            ("http://[::1]", "ssrf_ipv6_loopback"),
            ("http://0177.0.0.1", "ssrf_octal_ip"),
            ("http://2130706433", "ssrf_decimal_ip"),
        ]

        target_params = [
            k
            for k in clean_params
            if any(w in k.lower() for w in ["url", "file", "redirect", "target", "src", "path", "uri", "fetch", "load"])
        ]
        if not target_params:
            target_params = list(clean_params.keys())[:2]

        for param in target_params:
            for payload, name in ssrf_payloads:
                alt_params = dict(clean_params)
                alt_params[param] = payload
                requests.append(
                    {
                        "url": endpoint,
                        "method": method.upper(),
                        "params": alt_params,
                        "headers": dict(headers or {}),
                        "name": f"{name}_param_{param}",
                        "payload": {param: payload},
                    }
                )

        return requests

    def analyze_responses(
        self,
        baseline: HttpResponse,
        probe_responses: list[HttpResponse],
        payload_used: dict[str, Any],
    ) -> tuple[str, float, list[str], list[str]]:
        evidence: list[str] = []
        indicators: list[str] = []
        confidence = 0.0
        status = "rejected"

        for resp in probe_responses:
            if resp.is_error:
                indicators.append(f"Probe failed: {resp.error}")
                continue

            body_lower = resp.body_lower

            # Check for internal host content
            for marker in self.INTERNAL_MARKERS:
                if marker in body_lower:
                    indicators.append(f"Internal host marker found in response: {marker}")
                    confidence += 0.5
                    snippet = resp.body[:500]
                    evidence.append(f"Internal content leaked: {snippet}")
                    break

            # Check for cloud metadata
            for marker in self.METADATA_MARKERS:
                if marker in body_lower:
                    indicators.append(f"Cloud metadata marker found: {marker}")
                    confidence += 0.6
                    snippet = resp.body[:500]
                    evidence.append(f"Cloud metadata leaked: {snippet}")
                    break

            # Error with internal info
            if resp.status_code == 500 and any(
                w in body_lower for w in ["internal", "stack trace", "traceback", "exception"]
            ):
                indicators.append("Server error with internal info leaked")
                confidence += 0.2
                evidence.append(f"Error response with internal info: {resp.body[:300]}")

            # Status 200 with different content than baseline
            if (
                resp.status_code == 200
                and baseline.status_code == 200
                and resp.body != baseline.body
                and len(resp.body) > len(baseline.body) * 1.1
            ):
                indicators.append("Response body significantly larger (possible proxied content)")
                confidence += 0.2

        confidence = max(0.0, min(1.0, confidence))

        if confidence >= 0.5:
            status = "confirmed"
        elif confidence > 0.0:
            status = "unknown"
        else:
            status = "rejected"

        return status, confidence, evidence, indicators


# ── XSS Probe ────────────────────────────────────────────────


class XSSProbe(BaseProbe):
    """Probe for XSS: inject script payloads, check for unescaped reflection."""

    XSS_PAYLOAD = "<script>alert(1)</script>"
    XSS_CANARY = "xssprobe12345"

    @property
    def vulnerability_type(self) -> str:
        return "xss"

    def build_probe_requests(
        self,
        endpoint: str,
        method: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        requests: list[dict[str, Any]] = []
        clean_params = {k: v for k, v in (params or {}).items() if not v.startswith("{")}

        xss_payloads = [
            (f"<script>{self.XSS_CANARY}</script>", "xss_script_tag"),
            (f'"><script>{self.XSS_CANARY}</script>', "xss_breakout"),
            (f"<img src=x onerror=alert('{self.XSS_CANARY}')>", "xss_img_onerror"),
            (self.XSS_CANARY, "xss_reflection_check"),
        ]

        for param in list(clean_params.keys())[:3]:
            for payload, name in xss_payloads:
                alt_params = dict(clean_params)
                alt_params[param] = payload
                requests.append(
                    {
                        "url": endpoint,
                        "method": method.upper(),
                        "params": alt_params,
                        "headers": dict(headers or {}),
                        "name": f"{name}_param_{param}",
                        "payload": {param: payload},
                    }
                )

        return requests

    def analyze_responses(
        self,
        baseline: HttpResponse,
        probe_responses: list[HttpResponse],
        payload_used: dict[str, Any],
    ) -> tuple[str, float, list[str], list[str]]:
        evidence: list[str] = []
        indicators: list[str] = []
        confidence = 0.0
        status = "rejected"

        for resp in probe_responses:
            if resp.is_error:
                indicators.append(f"Probe failed: {resp.error}")
                continue

            body = resp.body

            # Check for unescaped script tag reflection
            if "<script>" in body and self.XSS_CANARY in body:
                indicators.append("Unescaped <script> tag reflected in response")
                confidence += 0.7
                snippet = body[:500]
                evidence.append(f"XSS payload reflected unescaped: {snippet}")

            # Check for canary in response (reflection check)
            elif self.XSS_CANARY in body:
                indicators.append("Probe canary reflected in response")
                confidence += 0.3
                snippet = body[:500]
                evidence.append(f"Canary reflected: {snippet}")

                # Check if it's escaped
                if "&lt;script&gt;" in body or "&amp;" in body:
                    indicators.append("Payload appears HTML-encoded (less likely XSS)")
                    confidence -= 0.2

            # Check Content-Type: text/html
            ct = resp.content_type
            if "text/html" in ct:
                indicators.append("Response is HTML (XSS more likely)")
                confidence += 0.1

        confidence = max(0.0, min(1.0, confidence))

        if confidence >= 0.5:
            status = "confirmed"
        elif confidence > 0.0:
            status = "unknown"
        else:
            status = "rejected"

        return status, confidence, evidence, indicators


# ── SQLi Probe ────────────────────────────────────────────────


class SQLiProbe(BaseProbe):
    """Probe for SQLi: inject SQL payloads, check for errors or behavior changes."""

    SQL_ERROR_PATTERNS = [
        re.compile(r"sql\s+syntax", re.IGNORECASE),
        re.compile(r"mysql", re.IGNORECASE),
        re.compile(r"ORA-\d{5}", re.IGNORECASE),
        re.compile(r"PostgreSQL", re.IGNORECASE),
        re.compile(r"SQLite", re.IGNORECASE),
        re.compile(r"unclosed quotation mark", re.IGNORECASE),
        re.compile(r"quoted string not properly terminated", re.IGNORECASE),
        re.compile(r"Syntax error.*sql", re.IGNORECASE),
        re.compile(r"Microsoft.*ODBC", re.IGNORECASE),
        re.compile(r"JET Database Engine", re.IGNORECASE),
        re.compile(r"mysql_fetch", re.IGNORECASE),
        re.compile(r"pg_query", re.IGNORECASE),
        re.compile(r"sqlite3", re.IGNORECASE),
    ]

    @property
    def vulnerability_type(self) -> str:
        return "sqli"

    def build_probe_requests(
        self,
        endpoint: str,
        method: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        requests: list[dict[str, Any]] = []
        clean_params = {k: v for k, v in (params or {}).items() if not v.startswith("{")}

        sqli_payloads = [
            ("' OR '1'='1", "sqli_or_true"),
            ("' OR 1=1--", "sqli_or_true_comment"),
            ("1' UNION SELECT NULL--", "sqli_union"),
            ("' AND SLEEP(3)--", "sqli_time"),
            ("'; WAITFOR DELAY '0:0:3'--", "sqli_time_mssql"),
            ("1' AND '1'='1", "sqli_and_true"),
            ("' OR ''='", "sqli_empty_or"),
        ]

        for param in list(clean_params.keys())[:3]:
            for payload, name in sqli_payloads:
                alt_params = dict(clean_params)
                alt_params[param] = payload
                requests.append(
                    {
                        "url": endpoint,
                        "method": method.upper(),
                        "params": alt_params,
                        "headers": dict(headers or {}),
                        "name": f"{name}_param_{param}",
                        "payload": {param: payload},
                    }
                )

        return requests

    def analyze_responses(
        self,
        baseline: HttpResponse,
        probe_responses: list[HttpResponse],
        payload_used: dict[str, Any],
    ) -> tuple[str, float, list[str], list[str]]:
        evidence: list[str] = []
        indicators: list[str] = []
        confidence = 0.0
        status = "rejected"

        baseline_has_errors = self._has_sql_errors(baseline.body)

        for resp in probe_responses:
            if resp.is_error:
                indicators.append(f"Probe failed: {resp.error}")
                continue

            # Check for SQL error messages
            if self._has_sql_errors(resp.body) and not baseline_has_errors:
                indicators.append("SQL error message in response (not in baseline)")
                confidence += 0.6
                snippet = self._extract_error_snippet(resp.body)
                evidence.append(f"SQL error: {snippet}")

            # Different response body (possible different behavior)
            if (
                resp.status_code == 200
                and baseline.status_code == 200
                and resp.body != baseline.body
                and "error" in resp.body_lower
                and "error" not in baseline.body_lower
            ):
                indicators.append("Error in probe response, not in baseline")
                confidence += 0.3
            elif (
                resp.status_code == 200
                and baseline.status_code == 200
                and resp.body != baseline.body
                and len(resp.body) > len(baseline.body) * 1.5
            ):
                indicators.append("Response body significantly larger (more data returned)")
                confidence += 0.3

            # Status code change
            if baseline.status_code == 200 and resp.status_code == 500:
                indicators.append("Server error (500) on SQLi payload")
                confidence += 0.4
                evidence.append(f"500 error on SQLi payload: {resp.body[:300]}")

            # Time-based detection
            if (
                "SLEEP" in str(payload_used) or "WAITFOR" in str(payload_used)
            ) and resp.elapsed_ms > baseline.elapsed_ms + 2500:
                indicators.append(
                    f"Time delay detected: {resp.elapsed_ms:.0f}ms vs baseline {baseline.elapsed_ms:.0f}ms"
                )
                confidence += 0.7
                evidence.append(f"Time-based SQLi: {resp.elapsed_ms:.0f}ms response time")

        confidence = max(0.0, min(1.0, confidence))

        if confidence >= 0.5:
            status = "confirmed"
        elif confidence > 0.0:
            status = "unknown"
        else:
            status = "rejected"

        return status, confidence, evidence, indicators

    def _has_sql_errors(self, body: str) -> bool:
        return any(p.search(body) for p in self.SQL_ERROR_PATTERNS)

    def _extract_error_snippet(self, body: str) -> str:
        for pat in self.SQL_ERROR_PATTERNS:
            match = pat.search(body)
            if match:
                start = max(0, match.start() - 100)
                end = min(len(body), match.end() + 100)
                return body[start:end]
        return body[:300]


# ── Auth Bypass Probe ────────────────────────────────────────


class AuthBypassProbe(BaseProbe):
    """Probe for auth bypass: test common auth bypass patterns."""

    @property
    def vulnerability_type(self) -> str:
        return "auth_bypass"

    def build_probe_requests(
        self,
        endpoint: str,
        method: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        requests: list[dict[str, Any]] = []
        base_headers = dict(headers or {})

        # Remove existing auth headers
        auth_keys = [k for k in base_headers if k.lower() in ("authorization", "x-auth-token", "x-api-key", "cookie")]

        # Strategy 1: Remove auth entirely
        no_auth_headers = {k: v for k, v in base_headers.items() if k.lower() not in [a.lower() for a in auth_keys]}
        requests.append(
            {
                "url": endpoint,
                "method": method.upper(),
                "params": {k: v for k, v in (params or {}).items() if not v.startswith("{")},
                "headers": no_auth_headers,
                "name": "auth_no_token",
                "payload": {},
            }
        )

        # Strategy 2: Null/empty tokens
        null_headers = dict(base_headers)
        for key in auth_keys:
            null_headers[key] = "null"
        requests.append(
            {
                "url": endpoint,
                "method": method.upper(),
                "params": {k: v for k, v in (params or {}).items() if not v.startswith("{")},
                "headers": null_headers,
                "name": "auth_null_token",
                "payload": {},
            }
        )

        # Strategy 3: Common bypass tokens
        bypass_headers = dict(base_headers)
        for key in auth_keys:
            bypass_headers[key] = "Bearer admin"
        requests.append(
            {
                "url": endpoint,
                "method": method.upper(),
                "params": {k: v for k, v in (params or {}).items() if not v.startswith("{")},
                "headers": bypass_headers,
                "name": "auth_admin_token",
                "payload": {},
            }
        )

        # Strategy 4: Method override
        override_headers = dict(base_headers)
        override_headers["X-HTTP-Method-Override"] = "GET"
        override_headers["X-Method-Override"] = "GET"
        requests.append(
            {
                "url": endpoint,
                "method": method.upper(),
                "params": {k: v for k, v in (params or {}).items() if not v.startswith("{")},
                "headers": override_headers,
                "name": "auth_method_override",
                "payload": {},
            }
        )

        return requests

    def analyze_responses(
        self,
        baseline: HttpResponse,
        probe_responses: list[HttpResponse],
        payload_used: dict[str, Any],
    ) -> tuple[str, float, list[str], list[str]]:
        evidence: list[str] = []
        indicators: list[str] = []
        confidence = 0.0
        status = "rejected"

        for resp in probe_responses:
            if resp.is_error:
                indicators.append(f"Probe failed: {resp.error}")
                continue

            # If baseline requires auth (401/403) but probe doesn't = bypass
            if baseline.status_code in (401, 403) and resp.status_code not in (401, 403):
                indicators.append(f"Auth bypass: baseline={baseline.status_code}, probe={resp.status_code}")
                confidence += 0.7
                evidence.append(f"Auth bypass via {resp.url}: status {resp.status_code}")

            # If baseline is 200 and probe is also 200 with no auth
            elif baseline.status_code == 200 and resp.status_code == 200:
                if "no_token" in resp.url or "null_token" in resp.url:
                    indicators.append("Endpoint accessible without authentication")
                    confidence += 0.4
                    evidence.append(f"Unauthenticated access: {resp.url}")

            # Different behavior
            if resp.status_code != baseline.status_code and resp.status_code not in (401, 403):
                indicators.append(f"Status changed: {baseline.status_code} -> {resp.status_code}")
                confidence += 0.2

        confidence = max(0.0, min(1.0, confidence))

        if confidence >= 0.5:
            status = "confirmed"
        elif confidence > 0.0:
            status = "unknown"
        else:
            status = "rejected"

        return status, confidence, evidence, indicators
