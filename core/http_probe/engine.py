"""Probe Engine — orchestrates hypothesis → probe → analysis → evidence pipeline."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from core.capabilities.registry import get_capability_registry
from core.http_probe.analyzer import AnalysisResult, Analyzer
from core.http_probe.probes import (
    AuthBypassProbe,
    BaseProbe,
    HttpResponse,
    IDORProbe,
    ProbeResult,
    SQLiProbe,
    SSRFProbe,
    XSSProbe,
)

logger = logging.getLogger("cateye.http_probe.engine")

# ── HTTP client abstraction ───────────────────────────────────


@dataclass
class ProbeRequest:
    """A request to send."""

    url: str
    method: str = "GET"
    params: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    timeout: float = 10.0


class HTTPClient:
    """HTTP client for sending probe requests.

    Wraps httpx with retry, timeout, and redirect control.
    Falls back to urllib if httpx is unavailable.
    """

    def __init__(self, timeout: float = 10.0, follow_redirects: bool = False) -> None:
        self._timeout = timeout
        self._follow_redirects = follow_redirects
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            import httpx

            self._client = httpx.Client(
                timeout=self._timeout,
                follow_redirects=self._follow_redirects,
                verify=False,
            )
        except ImportError:
            self._client = None

    def send(self, request: ProbeRequest) -> HttpResponse:
        """Send a request and return a normalized HttpResponse."""
        if self._client:
            return self._send_with_httpx(request)
        return self._send_with_urllib(request)

    def _send_with_httpx(self, request: ProbeRequest) -> HttpResponse:
        import httpx

        assert self._client is not None
        try:
            kwargs: dict[str, Any] = {
                "method": request.method,
                "url": request.url,
                "headers": request.headers or None,
                "params": request.params or None,
            }
            if request.body:
                kwargs["json"] = request.body

            response = self._client.request(**kwargs)
            return HttpResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.text,
                elapsed_ms=response.elapsed.total_seconds() * 1000,
                url=str(response.url),
            )
        except httpx.TimeoutException:
            return HttpResponse(status_code=0, error="Request timed out", url=request.url)
        except httpx.ConnectError as e:
            return HttpResponse(status_code=0, error=f"Connection error: {e}", url=request.url)
        except Exception as e:
            return HttpResponse(status_code=0, error=f"Request failed: {e}", url=request.url)

    def _send_with_urllib(self, request: ProbeRequest) -> HttpResponse:
        import urllib.error
        import urllib.parse
        import urllib.request

        url = request.url
        if request.params:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{urllib.parse.urlencode(request.params)}"

        headers = dict(request.headers)
        data = None
        if request.body:
            data = json.dumps(request.body).encode()
            headers.setdefault("Content-Type", "application/json")

        req = urllib.request.Request(url, data=data, headers=headers, method=request.method)
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=request.timeout) as resp:
                body = resp.read().decode(errors="replace")
                elapsed = (time.time() - start) * 1000
                return HttpResponse(
                    status_code=resp.status,
                    headers=dict(resp.headers),
                    body=body,
                    elapsed_ms=elapsed,
                    url=url,
                )
        except urllib.error.HTTPError as e:
            body = ""
            import contextlib

            with contextlib.suppress(Exception):
                body = e.read().decode(errors="replace")
            elapsed = (time.time() - start) * 1000
            return HttpResponse(
                status_code=e.code,
                headers=dict(e.headers) if hasattr(e, "headers") else {},
                body=body,
                elapsed_ms=elapsed,
                error=f"HTTP {e.code}",
                url=url,
            )
        except urllib.error.URLError as e:
            return HttpResponse(status_code=0, error=f"URL error: {e.reason}", url=url)
        except Exception as e:  # noqa: BLE001
            return HttpResponse(status_code=0, error=str(e), url=url)

    def close(self) -> None:
        if self._client and hasattr(self._client, "close"):
            self._client.close()


# ── Probe Engine ──────────────────────────────────────────────


class ProbeEngine:
    """Main engine that orchestrates hypothesis probing.

    Flow:
    1. Accept a hypothesis (with endpoint, method, vuln_type, params)
    2. Select the appropriate probe based on vulnerability type
    3. Send baseline request (clean) + probe requests (with payloads)
    4. Analyze responses for vulnerability indicators
    5. Return structured ProbeResult + AnalysisResult

    Integration:
    - Registers capabilities in CapabilityRegistry
    - Publishes events (probe:started, probe:completed, probe:failed)
    - Returns data compatible with EvidenceComposer
    """

    PROBE_MAP: dict[str, type[BaseProbe]] = {
        "idor": IDORProbe,
        "ssrf": SSRFProbe,
        "xss": XSSProbe,
        "sqli": SQLiProbe,
        "auth_bypass": AuthBypassProbe,
    }

    def __init__(self, http_client: HTTPClient | None = None) -> None:
        self._client = http_client or HTTPClient(timeout=10.0, follow_redirects=False)
        self._analyzer = Analyzer()
        self._register_capabilities()

    def _register_capabilities(self) -> None:
        reg = get_capability_registry()
        reg.register(
            "probe_idor",
            "http_probe",
            {"vuln_type": "idor", "description": "Probe for IDOR vulnerabilities"},
            description="Probe endpoints for Insecure Direct Object Reference vulnerabilities",
        )
        reg.register(
            "probe_ssrf",
            "http_probe",
            {"vuln_type": "ssrf", "description": "Probe for SSRF vulnerabilities"},
            description="Probe endpoints for Server-Side Request Forgery vulnerabilities",
        )
        reg.register(
            "probe_xss",
            "http_probe",
            {"vuln_type": "xss", "description": "Probe for XSS vulnerabilities"},
            description="Probe endpoints for Cross-Site Scripting vulnerabilities",
        )
        reg.register(
            "probe_sqli",
            "http_probe",
            {"vuln_type": "sqli", "description": "Probe for SQL injection vulnerabilities"},
            description="Probe endpoints for SQL Injection vulnerabilities",
        )
        reg.register(
            "probe_auth_bypass",
            "http_probe",
            {"vuln_type": "auth_bypass", "description": "Probe for authentication bypass vulnerabilities"},
            description="Probe endpoints for authentication bypass vulnerabilities",
        )
        logger.info("HTTP Probe capabilities registered")

    def _publish_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish an event to the EventBus if available."""
        try:
            from cores.events.event_bus import get_event_bus as _get_bus

            bus = _get_bus()
            bus.publish(event_type, **payload)
        except Exception:  # noqa: BLE001
            pass  # Event bus may not be initialized

    def probe(
        self,
        hypothesis_id: str,
        endpoint: str,
        method: str,
        vulnerability_type: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> AnalysisResult:
        """Probe a hypothesis endpoint for the specified vulnerability type.

        This is the main public method.

        Args:
            hypothesis_id: ID of the hypothesis being tested
            endpoint: Full URL to probe
            method: HTTP method (GET, POST, etc.)
            vulnerability_type: One of idor, ssrf, xss, sqli, auth_bypass
            params: Query/body parameters
            headers: Request headers (including auth)

        Returns:
            AnalysisResult with status, confidence, evidence, and PoC data
        """
        start_time = time.time()
        logger.info(
            "[PROBE] Starting probe: hypothesis=%s type=%s endpoint=%s %s",
            hypothesis_id,
            vulnerability_type,
            method,
            endpoint,
        )

        self._publish_event(
            "probe:started",
            {
                "hypothesis_id": hypothesis_id,
                "vulnerability_type": vulnerability_type,
                "endpoint": endpoint,
                "method": method,
            },
        )

        probe_class = self.PROBE_MAP.get(vulnerability_type)
        if not probe_class:
            logger.warning("[PROBE] Unknown vulnerability type: %s", vulnerability_type)
            result = AnalysisResult(
                hypothesis_id=hypothesis_id,
                vulnerability_type=vulnerability_type,
                endpoint=endpoint,
                method=method,
                status="unknown",
                indicators=[f"Unsupported vulnerability type: {vulnerability_type}"],
            )
            self._publish_event(
                "probe:failed",
                {
                    "hypothesis_id": hypothesis_id,
                    "error": f"Unsupported vulnerability type: {vulnerability_type}",
                },
            )
            return result

        probe = probe_class()
        probe_results: list[ProbeResult] = []

        try:
            # 1. Send baseline request
            baseline_req = probe.build_baseline(endpoint, method, params, headers)
            baseline = self._send(baseline_req)
            logger.debug("[PROBE] Baseline: status=%d elapsed=%.0fms", baseline.status_code, baseline.elapsed_ms)

            # 2. Build and send probe requests
            probe_requests = probe.build_probe_requests(endpoint, method, params, headers)
            logger.info("[PROBE] Sending %d probe requests", len(probe_requests))

            for req in probe_requests:
                probe_resp = self._send(req)
                status, conf, evidence, indicators = probe.analyze_responses(
                    baseline, [probe_resp], req.get("payload", {})
                )
                pr = ProbeResult(
                    hypothesis_id=hypothesis_id,
                    vulnerability_type=vulnerability_type,
                    endpoint=endpoint,
                    method=method,
                    status=status,
                    confidence=conf,
                    evidence_snippets=evidence,
                    indicators=indicators,
                    probe_name=req.get("name", "unknown"),
                    payload_used=req.get("payload", {}),
                    headers_used=req.get("headers", {}),
                    baseline_response=baseline,
                    probe_response=probe_resp,
                    elapsed_ms=probe_resp.elapsed_ms,
                )
                probe_results.append(pr)

            # 3. Analyze all probe results
            analysis = self._analyzer.analyze(
                probe_results,
                hypothesis_id=hypothesis_id,
                vulnerability_type=vulnerability_type,
            )

            elapsed = (time.time() - start_time) * 1000
            logger.info(
                "[PROBE] Complete: status=%s confidence=%.3f probes=%d elapsed=%.0fms",
                analysis.status,
                analysis.confidence,
                len(probe_results),
                elapsed,
            )

            self._publish_event(
                "probe:completed",
                {
                    "hypothesis_id": hypothesis_id,
                    "vulnerability_type": vulnerability_type,
                    "status": analysis.status,
                    "confidence": analysis.confidence,
                    "probe_count": len(probe_results),
                    "evidence_count": len(analysis.evidence_items),
                    "elapsed_ms": elapsed,
                },
            )

            return analysis

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error("[PROBE] Failed: %s (%.0fms)", e, elapsed)
            self._publish_event(
                "probe:failed",
                {
                    "hypothesis_id": hypothesis_id,
                    "error": str(e),
                    "elapsed_ms": elapsed,
                },
            )
            return AnalysisResult(
                hypothesis_id=hypothesis_id,
                vulnerability_type=vulnerability_type,
                endpoint=endpoint,
                method=method,
                status="unknown",
                indicators=[f"Probe failed: {e}"],
            )

    def probe_batch(
        self,
        hypotheses: list[dict[str, Any]],
    ) -> list[AnalysisResult]:
        """Probe multiple hypotheses in sequence.

        Each hypothesis dict must contain:
            hypothesis_id, endpoint, method, vulnerability_type
            Optional: params, headers
        """
        results: list[AnalysisResult] = []
        for hyp in hypotheses:
            result = self.probe(
                hypothesis_id=hyp.get("hypothesis_id", ""),
                endpoint=hyp.get("endpoint", ""),
                method=hyp.get("method", "GET"),
                vulnerability_type=hyp.get("vulnerability_type", "generic"),
                params=hyp.get("params"),
                headers=hyp.get("headers"),
            )
            results.append(result)
        return results

    def supported_types(self) -> list[str]:
        """Return list of supported vulnerability types."""
        return list(self.PROBE_MAP.keys())

    def _send(self, req: dict[str, Any]) -> HttpResponse:
        """Send a request dict via the HTTP client."""
        probe_req = ProbeRequest(
            url=req.get("url", ""),
            method=req.get("method", "GET"),
            params=req.get("params", {}),
            headers=req.get("headers", {}),
            body=req.get("body"),
        )
        return self._client.send(probe_req)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
