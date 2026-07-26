from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any
from urllib.request import Request, urlopen

from cores.tools.base import BaseTool, UnifiedResult

logger = logging.getLogger("cateye.tools.censys")

CENSYS_API_BASE = "https://search.censys.io/api/v2"


class CensysTool(BaseTool):
    """Censys intelligence provider — internet asset discovery, certificate transparency."""

    name = "censys"
    install_hint = "Requires CENSYS_API_KEY + CENSYS_API_SECRET env vars (free: https://search.censys.io/account/api)"
    min_version = "0.1"

    def __init__(self, api_key: str | None = None, api_secret: str | None = None) -> None:
        super().__init__()
        self._api_key = api_key or os.environ.get("CENSYS_API_KEY", "")
        self._api_secret = api_secret or os.environ.get("CENSYS_API_SECRET", "")

    def is_available(self) -> bool:
        return bool(self._api_key) and bool(self._api_secret)

    def search_hosts(self, query: str, per_page: int = 10, timeout: int = 30) -> list[UnifiedResult]:
        if not self.is_available():
            return self._no_key_result()
        payload = json.dumps({"q": query, "per_page": per_page}).encode()
        try:
            resp = self._request(f"{CENSYS_API_BASE}/hosts/search", payload, timeout)
            data = json.loads(resp)
        except Exception as exc:
            logger.warning("Censys search_hosts failed: %s", exc)
            return []
        return self._parse_host_search(data, query)

    def host_view(self, ip: str, timeout: int = 15) -> list[UnifiedResult]:
        if not self.is_available():
            return self._no_key_result()
        try:
            resp = self._request(f"{CENSYS_API_BASE}/hosts/{ip}", None, timeout)
            data = json.loads(resp)
        except Exception as exc:
            logger.warning("Censys host_view failed for %s: %s", ip, exc)
            return []
        return self._parse_host_view(data, ip)

    def domain(self, domain: str, timeout: int = 30) -> list[UnifiedResult]:
        return self.search_hosts(f"dns.names: {domain}", per_page=50, timeout=timeout)

    def certificates(self, query: str, timeout: int = 30) -> list[UnifiedResult]:
        if not self.is_available():
            return self._no_key_result()
        payload = json.dumps({"q": query, "per_page": 10}).encode()
        try:
            resp = self._request(f"{CENSYS_API_BASE}/certificates/search", payload, timeout)
            data = json.loads(resp)
        except Exception as exc:
            logger.warning("Censys certificates failed: %s", exc)
            return []
        return self._parse_certificates(data, query)

    def _request(self, url: str, payload: bytes | None, timeout: int) -> str:
        import ssl

        auth_str = f"{self._api_key}:{self._api_secret}"
        b64 = base64.b64encode(auth_str.encode()).decode()
        req = Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Basic {b64}",
                "Content-Type": "application/json",
                "User-Agent": "Rastro-CATEYE/1.0",
            },
        )
        if payload is not None:
            req.method = "POST"
        ctx = ssl.create_default_context()
        resp = urlopen(req, timeout=timeout, context=ctx)
        return resp.read().decode("utf-8")

    def _no_key_result(self) -> list[UnifiedResult]:
        logger.warning("Censys API key/secret not configured — set CENSYS_API_KEY and CENSYS_API_SECRET")
        return []

    def _parse_host_search(self, data: dict[str, Any], query: str) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        hits = data.get("result", {}).get("hits", [])
        total = data.get("result", {}).get("total", 0)
        for h in hits[:20]:
            ip = h.get("ip", "")
            services = []
            for svc in h.get("services", [])[:3]:
                services.append(f"{svc.get('port', 0)}/{svc.get('service_name', '?')}")
            results.append(
                UnifiedResult(
                    source="censys",
                    target=ip,
                    result_type="exposed_service",
                    severity=self._port_severity(h),
                    confidence=0.8,
                    name=f"Censys: {ip}",
                    description=f"Services: {', '.join(services)}" if services else f"Host {ip}",
                    evidence={
                        "ip": ip,
                        "services": services,
                        "location": h.get("location", {}),
                        "operating_system": h.get("operating_system", {}),
                    },
                    tags=["censys", "exposed", f"query:{query}"],
                )
            )
        if results:
            results.insert(
                0,
                UnifiedResult(
                    source="censys",
                    target=query,
                    result_type="search_meta",
                    confidence=0.95,
                    name=f"Censys search: {query}",
                    description=f"Found {total} total results",
                    evidence={"total": total, "query": query},
                    tags=["censys", "search_meta"],
                    severity="info",
                ),
            )
        return results

    def _parse_host_view(self, data: dict[str, Any], ip: str) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        result = data.get("result", {})
        services = result.get("services", [])
        for svc in services[:20]:
            port = svc.get("port", 0)
            service = svc.get("service_name", "")
            transport = svc.get("transport_protocol", "")
            results.append(
                UnifiedResult(
                    source="censys",
                    target=ip,
                    result_type="open_port",
                    severity="medium" if port in {21, 22, 23, 3389, 5900, 6379} else "info",
                    confidence=0.85,
                    name=f"Censys host: {ip}:{port}",
                    description=f"{service}/{transport} on port {port}" if service else f"Port {port} open",
                    evidence={"ip": ip, "port": port, "service": service, "transport": transport},
                    tags=["censys", "host"],
                )
            )
        return results

    def _parse_certificates(self, data: dict[str, Any], query: str) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        hits = data.get("result", {}).get("hits", [])
        for h in hits[:10]:
            parsed = h.get("parsed", {})
            subject = parsed.get("subject", {})
            cn = subject.get("common_name", "") or subject.get("organization", "") or "?"
            issuer = parsed.get("issuer", {}).get("organization", "?")
            validity = parsed.get("validity_period", {})
            results.append(
                UnifiedResult(
                    source="censys",
                    target=query,
                    result_type="certificate",
                    severity="info",
                    confidence=0.9,
                    name=f"Cert: {cn}",
                    description=f"Issuer: {issuer}",
                    evidence={
                        "subject_cn": cn,
                        "issuer": issuer,
                        "not_before": validity.get("not_before", ""),
                        "not_after": validity.get("not_after", ""),
                        "fingerprint": h.get("fingerprint", {}).get("sha256", ""),
                    },
                    tags=["censys", "certificate"],
                )
            )
        return results

    @staticmethod
    def _port_severity(hit: dict[str, Any]) -> str:
        for svc in hit.get("services", []):
            if svc.get("port") in {21, 22, 23, 3389, 5900, 6379}:
                return "medium"
        return "info"

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return []
