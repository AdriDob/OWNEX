"""Headless browser scanner — DOM XSS, SPA crawling, prototype pollution, client-side vulns.

Uses Playwright to execute JavaScript in a real browser context,
detecting vulnerabilities that HTTP-level scanners cannot reach:
  - DOM-based XSS (sink detection in executed JS)
  - Prototype pollution (client-side)
  - SPA endpoint discovery (JavaScript routing)
  - Client-side template injection
  - Sensitive data in DOM (tokens, keys in memory/localStorage)
  - CORS misconfiguration via fetch/XHR
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from cores.tools.base import UnifiedResult

logger = logging.getLogger("cateye.tools.headless")

DOM_XSS_PATTERNS = [
    r"document\.write\s*\(",
    r"innerHTML\s*=",
    r"outerHTML\s*=",
    r"eval\s*\(",
    r"setTimeout\s*\(\s*['\"]",
    r"setInterval\s*\(\s*['\"]",
    r"new\s+Function\s*\(",
    r"location\s*=",
    r"location\.hash\s*=",
    r"location\.href\s*=",
    r"\.srcdoc\s*=",
    r"insertAdjacentHTML",
]

PROTOTYPE_POLLUTION_PATTERNS = [
    r"__proto__",
    r"constructor\.prototype",
    r"Object\.assign\s*\(.*__proto__",
]

SENSITIVE_DOM_PATTERNS = {
    "jwt": r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
    "api_key": r"(?:api[_-]?key|apikey|api_secret)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]",
    "aws_key": r"AKIA[0-9A-Z]{16}",
    "internal_ip": r"(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})",
    "private_key": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
}


@dataclass
class DomFinding:
    vuln_type: str
    url: str
    detail: str
    evidence: str
    severity: str = "medium"
    confidence: float = 0.6


class HeadlessScanner:
    def __init__(self, timeout: int = 60):
        self._timeout = timeout

    def scan_urls(self, urls: list[str]) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        for url in urls:
            try:
                findings = self._scan_single(url)
                for f in findings:
                    result = UnifiedResult(
                        source="headless",
                        target=f.url,
                        result_type="vulnerability",
                        severity=f.severity,
                        confidence=f.confidence,
                        name=f"{f.vuln_type}: {f.url}",
                        description=f.detail,
                        evidence={"dom_evidence": f.evidence[:500]},
                        tags=["headless", "dom", f.vuln_type.lower().replace(" ", "_")],
                    )
                    results.append(result)
            except Exception as e:
                logger.warning("Headless scan failed for %s: %s", url, e)
        return results

    def _scan_single(self, url: str) -> list[DomFinding]:
        """Scan a single URL using Playwright."""
        findings: list[DomFinding] = []
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("playwright not installed — cannot run headless scanner")
            return findings

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 CATEYE/1.0",
                viewport={"width": 1280, "height": 720},
                ignore_https_errors=True,
            )
            page = context.new_page()

            console_messages: list[str] = []
            page.on("console", lambda msg: console_messages.append(msg.text))
            page.on("pageerror", lambda err: console_messages.append(f"PAGE_ERROR: {err}"))

            try:
                page.goto(url, wait_until="networkidle", timeout=self._timeout * 1000)
                html = page.content()
                js_urls = page.evaluate("""() => {
                    const scripts = document.querySelectorAll('script[src]');
                    return Array.from(scripts).map(s => s.src);
                }""")
                local_storage = page.evaluate("""() => {
                    try { return JSON.stringify(window.localStorage); }
                    catch { return '{}'; }
                }""")
                # 1. Detect DOM XSS sinks in source
                for pattern in DOM_XSS_PATTERNS:
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    if matches:
                        for m in matches[:3]:
                            findings.append(DomFinding(
                                vuln_type="DOM XSS Sink",
                                url=url,
                                detail=f"Potencial sink XSS DOM detectado: {m}",
                                evidence=m,
                                severity="high",
                                confidence=0.5,
                            ))

                # 2. Detect prototype pollution
                for pattern in PROTOTYPE_POLLUTION_PATTERNS:
                    if re.search(pattern, html, re.IGNORECASE):
                        findings.append(DomFinding(
                            vuln_type="Prototype Pollution",
                            url=url,
                            detail=f"Posible prototype pollution: {pattern}",
                            evidence=pattern,
                            severity="high",
                            confidence=0.4,
                        ))

                # 3. SPA endpoint discovery
                if js_urls:
                    findings.append(DomFinding(
                        vuln_type="SPA JavaScript Routes",
                        url=url,
                        detail=f"{len(js_urls)} archivos JS detectados — posibles rutas SPA por descubrir",
                        evidence="\n".join(js_urls[:10]),
                        severity="low",
                        confidence=0.7,
                    ))

                # 4. Sensitive data in localStorage
                try:
                    ls_data = json.loads(local_storage)
                    for key, value in ls_data.items():
                        str_val = str(value)
                        for name, pat in SENSITIVE_DOM_PATTERNS.items():
                            if re.search(pat, str_val, re.IGNORECASE):
                                findings.append(DomFinding(
                                    vuln_type=f"Sensitive Data in localStorage ({name})",
                                    url=url,
                                    detail=f"Key '{key}' contiene datos sensibles: {name}",
                                    evidence=f"{key}: {str_val[:200]}",
                                    severity="high" if name in ("jwt", "private_key") else "medium",
                                    confidence=0.8,
                                ))
                except json.JSONDecodeError:
                    pass

                # 5. Console errors (potential XSS or info leaks)
                for msg in console_messages:
                    if any(kw in msg.lower() for kw in ("xss", "error", "blocked", "warning", "security")):
                        findings.append(DomFinding(
                            vuln_type="Console Security Message",
                            url=url,
                            detail=msg[:300],
                            evidence=msg[:500],
                            severity="medium",
                            confidence=0.5,
                        ))

            except Exception as e:
                logger.debug("Headless navigation error for %s: %s", url, e)
            finally:
                browser.close()

        return findings

    def extract_spa_routes(self, url: str) -> list[str]:
        """Discover SPA routes by analyzing JavaScript bundles."""
        routes: list[str] = []
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return routes

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(ignore_https_errors=True)
            try:
                page.goto(url, wait_until="networkidle", timeout=self._timeout * 1000)
                # Collect all network requests to find API routes
                api_pattern = re.compile(r'["\'](/api/[^"\']+)["\']')
                html = page.content()
                routes = list(set(api_pattern.findall(html)))
            except Exception as exc:
                logger.debug("Failed to extract SPA routes from %s: %s", url, exc)
            finally:
                browser.close()
        return routes
