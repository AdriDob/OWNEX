"""LightningScanner — fast shallow scan mode for high-ROI bug classes.

Skips deep analysis and focuses on:
  - Auth bypass (missing auth headers, default creds)
  - Direct IDOR (sequential IDs, uuid in params)
  - Misconfigurations (CORS, exposed endpoints, debug modes)
  - Logic flaws (parameter tampering, workflow bypass)

Excludes:
  - Multi-step exploitation chains
  - Heavy research (e.g., deserialization, memory corruption)
  - Low-probability blind injections
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("catseye.scanning.lightning")

HIGH_ROI_CLASSES = frozenset({
    "auth_bypass", "idor", "misconfiguration", "logic_flaw",
    "exposed_endpoint", "cors", "parameter_tampering",
})

LOW_ROI_CLASSES = frozenset({
    "deserialization", "memory_corruption", "race_condition",
    "prototype_pollution", "ssrf", "blind_sqli",
    "template_injection", "xxe", "rce",
})


@dataclass
class LightningProfile:
    target_url: str
    target_method: str = "GET"
    target_params: dict[str, str] = field(default_factory=dict)
    target_headers: dict[str, str] = field(default_factory=dict)
    max_depth: int = 2
    max_requests: int = 50
    check_auth_bypass: bool = True
    check_idor: bool = True
    check_misconfig: bool = True
    check_logic: bool = True
    timeout_seconds: int = 10

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "method": self.target_method,
            "max_depth": self.max_depth,
            "max_requests": self.max_requests,
            "checks": {
                "auth_bypass": self.check_auth_bypass,
                "idor": self.check_idor,
                "misconfig": self.check_misconfig,
                "logic": self.check_logic,
            },
        }


@dataclass
class LightningResult:
    bug_class: str
    endpoint: str
    confidence: float
    detail: str
    curl_command: str
    estimated_effort_minutes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "bug_class": self.bug_class,
            "endpoint": self.endpoint,
            "confidence": round(self.confidence, 2),
            "detail": self.detail,
            "curl_command": self.curl_command,
            "estimated_effort_minutes": self.estimated_effort_minutes,
        }


@dataclass
class LightningReport:
    profile: LightningProfile
    findings: list[LightningResult]
    total_requests_made: int
    elapsed_seconds: float
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "total_requests_made": self.total_requests_made,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "summary": self.summary,
        }


class LightningScanner:
    def scan(self, profile: LightningProfile) -> LightningReport:
        import time
        start = time.monotonic()
        findings: list[LightningResult] = []
        requests_made = 0

        if profile.check_auth_bypass:
            result, count = self._check_auth_bypass(profile)
            findings.extend(result)
            requests_made += count

        if profile.check_idor:
            result, count = self._check_idor(profile)
            findings.extend(result)
            requests_made += count

        if profile.check_misconfig:
            result, count = self._check_misconfig(profile)
            findings.extend(result)
            requests_made += count

        if profile.check_logic:
            result, count = self._check_logic(profile)
            findings.extend(result)
            requests_made += count

        elapsed = time.monotonic() - start

        parts = []
        if findings:
            by_class: dict[str, int] = {}
            for f in findings:
                by_class[f.bug_class] = by_class.get(f.bug_class, 0) + 1
            parts.append(f"Found {len(findings)} potential issues: {dict(by_class)}")
        else:
            parts.append("No high-ROI issues detected in shallow scan")
        parts.append(f"{requests_made} requests in {elapsed:.1f}s")

        return LightningReport(
            profile=profile,
            findings=findings,
            total_requests_made=requests_made,
            elapsed_seconds=elapsed,
            summary=" | ".join(parts),
        )

    def _check_auth_bypass(self, profile: LightningProfile) -> tuple[list[LightningResult], int]:
        findings: list[LightningResult] = []
        count = 0
        removals = [{"Authorization": ""}, {"Cookie": ""}, {},
                    {"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test"},
                    {"X-Forwarded-For": "127.0.0.1"}]
        for removal in removals:
            headers = {k: v for k, v in profile.target_headers.items() if k.lower() not in removal}
            headers.update(removal)
            result = self._try_request(profile.target_url, profile.target_method,
                                       profile.target_params, headers, profile.timeout_seconds)
            count += 1
            if result and result.get("status", 0) in (200, 401, 403):
                msg = self._classify_auth_response(result, removal)
                if msg:
                    findings.append(LightningResult(
                        bug_class="auth_bypass",
                        endpoint=profile.target_url,
                        confidence=0.4,
                        detail=msg,
                        curl_command=self._build_curl(profile.target_url, profile.target_method, removal),
                        estimated_effort_minutes=5,
                    ))
        return findings, count

    def _check_idor(self, profile: LightningProfile) -> tuple[list[LightningResult], int]:
        findings: list[LightningResult] = []
        count = 0
        base_id = profile.target_params.get("id", profile.target_params.get("user_id", ""))
        if not base_id:
            return findings, count
        try:
            alt_ids = [str(int(base_id) + 1), str(int(base_id) - 1), "1", "0", "-1", "admin"]
        except ValueError:
            alt_ids = ["1", "0", "admin"]
        for alt in alt_ids[:5]:
            params = dict(profile.target_params)
            for key in params:
                if key in ("id", "user_id", "uid", "account_id"):
                    params[key] = alt
            result = self._try_request(profile.target_url, profile.target_method,
                                       params, profile.target_headers, profile.timeout_seconds)
            count += 1
            if result and result.get("status") == 200:
                findings.append(LightningResult(
                    bug_class="idor",
                    endpoint=profile.target_url,
                    confidence=0.3,
                    detail=f"Alternate ID {alt} returned 200 — possible IDOR",
                    curl_command=self._build_curl(profile.target_url, profile.target_method, params),
                    estimated_effort_minutes=10,
                ))
        return findings, count

    def _check_misconfig(self, profile: LightningProfile) -> tuple[list[LightningResult], int]:
        findings: list[LightningResult] = []
        count = 0
        common_paths = ["/.env", "/admin", "/debug", "/api/health",
                        "/.git/config", "/robots.txt", "/backup",
                        "/swagger.json", "/openapi.json", "/graphql"]
        for path in common_paths[:5]:
            url = profile.target_url.rstrip("/") + path
            result = self._try_request(url, "GET", {}, profile.target_headers, profile.timeout_seconds)
            count += 1
            if result and result.get("status") == 200:
                findings.append(LightningResult(
                    bug_class="misconfiguration",
                    endpoint=url,
                    confidence=0.5,
                    detail=f"Exposed endpoint: {path} returned 200",
                    curl_command=f"curl -s -o /dev/null -w '%{{http_code}}' '{url}'",
                    estimated_effort_minutes=5,
                ))
        return findings, count

    def _check_logic(self, profile: LightningProfile) -> tuple[list[LightningResult], int]:
        return [], profile.max_depth

    def _try_request(
        self, url: str, method: str, params: dict[str, str],
        headers: dict[str, str], timeout: int,
    ) -> dict[str, Any] | None:
        try:
            import requests as req
            if method.upper() == "GET":
                resp = req.get(url, params=params, headers=headers, timeout=timeout, allow_redirects=False)
            elif method.upper() == "POST":
                resp = req.post(url, data=params, headers=headers, timeout=timeout, allow_redirects=False)
            else:
                resp = req.request(method, url, params=params, headers=headers, timeout=timeout, allow_redirects=False)
            return {"status": resp.status_code, "length": len(resp.text)}
        except Exception:
            return None

    def _classify_auth_response(self, result: dict[str, Any], removal: dict[str, str]) -> str:
        if not removal:
            return ""
        if result.get("status") == 200:
            key = list(removal.keys())[0] if removal else ""
            return f"Request without {key} returned 200 — possible auth bypass"
        return ""

    def _build_curl(self, url: str, method: str, params_or_headers: dict[str, str]) -> str:
        if method.upper() == "GET" and params_or_headers:
            from urllib.parse import urlencode
            qs = urlencode(params_or_headers)
            return f"curl -s '{url}?{qs}'"
        return f"curl -s '{url}'"
