from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("cateye.recon.fingerprint")

TECH_PATTERNS: dict[str, list[dict[str, Any]]] = {
    "react": [
        {"type": "html", "pattern": r"__NEXT_DATA__", "weight": 1.0},
        {"type": "html", "pattern": r'id=["\']__next["\']', "weight": 0.8},
        {"type": "html", "pattern": r"_next/static/", "weight": 0.7},
        {"type": "html", "pattern": r"data-reactroot", "weight": 0.6},
        {"type": "html", "pattern": r"react[" '"]?>', "weight": 0.4},
        {"type": "header", "pattern": r"x-powered-by.*express", "flags": re.I, "weight": 0.3},
    ],
    "vue": [
        {"type": "html", "pattern": r"__NUXT__", "weight": 1.0},
        {"type": "html", "pattern": r'id=["\']__nuxt["\']', "weight": 0.8},
        {"type": "html", "pattern": r"vue", "weight": 0.3},
        {"type": "html", "pattern": r"data-v-", "weight": 0.4},
    ],
    "angular": [
        {"type": "html", "pattern": r"ng-version", "weight": 0.9},
        {"type": "html", "pattern": r"ng-app", "weight": 0.7},
        {"type": "html", "pattern": r"__ngContext__", "weight": 0.8},
        {"type": "html", "pattern": r"<app-root", "weight": 0.5},
    ],
    "laravel": [
        {"type": "cookie", "pattern": r"laravel_session", "weight": 0.9},
        {"type": "cookie", "pattern": r"XSRF-TOKEN", "weight": 0.5},
        {"type": "header", "pattern": r"x-powered-by.*laravel", "flags": re.I, "weight": 0.8},
        {"type": "html", "pattern": r"livewire", "weight": 0.6},
        {"type": "html", "pattern": r'csrf-token.*content=["\']', "weight": 0.4},
    ],
    "django": [
        {"type": "cookie", "pattern": r"csrftoken", "weight": 0.8},
        {"type": "cookie", "pattern": r"sessionid", "weight": 0.5},
        {"type": "header", "pattern": r"x-powered-by.*django", "flags": re.I, "weight": 0.7},
        {"type": "html", "pattern": r"__admin", "weight": 0.3},
    ],
    "graphql": [
        {"type": "path", "pattern": r"/graphql", "weight": 1.0},
        {"type": "path", "pattern": r"/gql", "weight": 0.8},
        {"type": "path", "pattern": r"/v1/graphql", "weight": 0.9},
        {"type": "path", "pattern": r"/api/graphql", "weight": 0.9},
        {"type": "html", "pattern": r"graphql", "weight": 0.3},
    ],
    "wordpress": [
        {"type": "path", "pattern": r"/wp-content/", "weight": 1.0},
        {"type": "path", "pattern": r"/wp-json/", "weight": 0.9},
        {"type": "path", "pattern": r"/wp-admin/", "weight": 0.8},
        {"type": "cookie", "pattern": r"wordpress_logged_in", "weight": 0.8},
        {"type": "html", "pattern": r"/wp-includes/", "weight": 0.7},
    ],
    "spring": [
        {"type": "header", "pattern": r"x-application-context", "flags": re.I, "weight": 0.9},
        {"type": "path", "pattern": r"/actuator", "weight": 0.8},
        {"type": "path", "pattern": r"/swagger-ui", "weight": 0.7},
        {"type": "header", "pattern": r"x-powered-by.*spring", "flags": re.I, "weight": 0.6},
    ],
    "fastapi": [
        {"type": "path", "pattern": r"/docs", "weight": 0.7},
        {"type": "path", "pattern": r"/openapi.json", "weight": 0.9},
        {"type": "header", "pattern": r"server.*uvicorn", "flags": re.I, "weight": 0.5},
    ],
    "express": [
        {"type": "header", "pattern": r"x-powered-by.*express", "flags": re.I, "weight": 0.8},
        {"type": "cookie", "pattern": r"connect\.sid", "weight": 0.7},
    ],
    "api": [
        {"type": "path", "pattern": r"/api/", "weight": 0.5},
        {"type": "path", "pattern": r"/v[0-9]+/", "weight": 0.4},
        {"type": "path", "pattern": r"/rest/", "weight": 0.3},
        {"type": "header", "pattern": r"content-type.*application/json", "flags": re.I, "weight": 0.2},
    ],
}


@dataclass
class TechnologyDetected:
    name: str
    category: str = ""
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)


@dataclass
class FingerprintResult:
    technologies: list[TechnologyDetected] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    paths_checked: list[str] = field(default_factory=list)
    body_snippet: str = ""

    @property
    def primary_tech(self) -> str:
        if not self.technologies:
            return "unknown"
        return max(self.technologies, key=lambda t: t.confidence).name

    @property
    def tech_summary(self) -> str:
        if not self.technologies:
            return "unknown"
        parts = [f"{t.name}({t.confidence:.0%})" for t in sorted(self.technologies, key=lambda t: -t.confidence)]
        return ", ".join(parts[:5])

    def has_tech(self, name: str) -> bool:
        return any(t.name == name for t in self.technologies)

    def get_confidence(self, name: str) -> float:
        for t in self.technologies:
            if t.name == name:
                return t.confidence
        return 0.0


class Fingerprinter:
    def __init__(self, timeout: float = 10.0):
        self._timeout = timeout

    MIN_CONFIDENCE = 0.2

    def fingerprint(self, domain: str, paths: list[str] | None = None) -> FingerprintResult:
        if paths is None:
            paths = ["/"]

        result = FingerprintResult()
        result.paths_checked = paths

        combined_html = ""
        combined_headers: dict[str, str] = {}
        combined_cookies: dict[str, str] = {}

        for path in paths:
            url = f"https://{domain}{path}"
            try:
                import httpx

                resp = httpx.get(url, timeout=self._timeout, verify=False, follow_redirects=True)
                combined_html += resp.text
                combined_headers.update(dict(resp.headers))
                for cookie in resp.cookies:
                    combined_cookies[cookie.name] = cookie.value
                if not result.body_snippet and resp.text:
                    result.body_snippet = resp.text[:500]
            except Exception:
                continue

        result.headers = combined_headers
        result.cookies = combined_cookies

        matched = self._match_technologies(combined_html, combined_headers, combined_cookies, paths)
        result.technologies = [t for t in matched if t.confidence >= self.MIN_CONFIDENCE]

        return result

    def _match_technologies(
        self,
        html: str,
        headers: dict[str, str],
        cookies: dict[str, str],
        paths: list[str],
    ) -> list[TechnologyDetected]:
        detected: list[TechnologyDetected] = []

        for tech_name, patterns in TECH_PATTERNS.items():
            score = 0.0
            evidence: list[str] = []

            for rule in patterns:
                rule_type = rule["type"]
                pattern = rule["pattern"]
                weight = rule["weight"]
                flags = rule.get("flags", 0)

                if rule_type == "html":
                    if re.search(pattern, html, flags):
                        score += weight
                        evidence.append(f"html:{pattern}")
                elif rule_type == "header":
                    for k, v in headers.items():
                        if re.search(pattern, f"{k}: {v}", flags):
                            score += weight
                            evidence.append(f"header:{k}")
                            break
                elif rule_type == "cookie":
                    for k in cookies:
                        if re.search(pattern, k, flags):
                            score += weight
                            evidence.append(f"cookie:{k}")
                            break
                elif rule_type == "path":
                    for p in paths:
                        if re.search(pattern, p, flags):
                            score += weight
                            evidence.append(f"path:{p}")
                            break

            if score > 0:
                detected.append(
                    TechnologyDetected(
                        name=tech_name,
                        category=_category_for(tech_name),
                        confidence=min(score / max(len(patterns) * 0.6, 0.5), 1.0),
                        evidence=evidence,
                    )
                )

        return detected


def _category_for(tech: str) -> str:
    categories = {
        "react": "spa",
        "vue": "spa",
        "angular": "spa",
        "laravel": "framework",
        "django": "framework",
        "spring": "framework",
        "fastapi": "framework",
        "express": "framework",
        "graphql": "api",
        "wordpress": "cms",
        "api": "api",
    }
    return categories.get(tech, "unknown")
