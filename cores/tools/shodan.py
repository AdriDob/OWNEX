"""ShodanTool — external intelligence via Shodan REST API.

No CLI binary required — uses Shodan's REST API directly.
API key sourced from env SHODAN_API_KEY or IdentityVault.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib.request import urlopen

from cores.tools.base import BaseTool, UnifiedResult

logger = logging.getLogger("ownex.tools.shodan")

SHODAN_API_BASE = "https://api.shodan.io"


class ShodanTool(BaseTool):
    """Shodan intelligence provider — searches exposed services, banners, technologies."""

    name = "shodan"
    install_hint = "Requires SHODAN_API_KEY env var (free tier: https://account.shodan.io)"
    min_version = "0.1"

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__()
        self._api_key = api_key or os.environ.get("SHODAN_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key)

    def search(self, query: str, limit: int = 50, timeout: int = 30) -> list[UnifiedResult]:
        """Search Shodan for hosts matching a query (domain, technology, port, etc.)."""
        if not self._api_key:
            return self._no_key_result()

        url = f"{SHODAN_API_BASE}/shodan/host/search?key={self._api_key}&query={query}&limit={limit}"
        try:
            resp = self._request(url, timeout)
            data = json.loads(resp)
        except Exception as exc:
            logger.warning("Shodan search failed: %s", exc)
            return []

        return self._parse_search(data, query)

    def host(self, ip: str, timeout: int = 15) -> list[UnifiedResult]:
        """Look up a single IP on Shodan."""
        if not self._api_key:
            return self._no_key_result()

        url = f"{SHODAN_API_BASE}/shodan/host/{ip}?key={self._api_key}"
        try:
            resp = self._request(url, timeout)
            data = json.loads(resp)
        except Exception as exc:
            logger.warning("Shodan host lookup failed for %s: %s", ip, exc)
            return []

        return self._parse_host(data)

    def domain(self, domain: str, timeout: int = 30) -> list[UnifiedResult]:
        """Search all Shodan data for a domain."""
        return self.search(f"hostname:{domain}", limit=100, timeout=timeout)

    def _request(self, url: str, timeout: int) -> str:
        """Make an HTTP GET request."""
        import ssl

        ctx = ssl.create_default_context()
        resp = urlopen(url, timeout=timeout, context=ctx)
        return resp.read().decode("utf-8")

    def _no_key_result(self) -> list[UnifiedResult]:
        logger.warning("Shodan API key not configured — set SHODAN_API_KEY")
        return []

    def _parse_search(self, data: dict[str, Any], query: str) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        matches = data.get("matches", [])
        total = data.get("total", 0)
        for m in matches[:50]:
            ip = m.get("ip_str", "")
            port = m.get("port", 0)
            hostnames = m.get("hostnames", [])
            services = []
            if m.get("data"):
                for d in m["data"][:3]:
                    if isinstance(d, dict) and d.get("product"):
                        services.append(d["product"])

            results.append(
                UnifiedResult(
                    source="shodan",
                    target=ip or query,
                    result_type="exposed_service",
                    severity=self._port_severity(port),
                    confidence=0.8,
                    name=f"Shodan: {ip}:{port}",
                    description=f"Port {port} open — {', '.join(hostnames[:3])}" if hostnames else f"Port {port} open",
                    evidence={
                        "ip": ip,
                        "port": port,
                        "hostnames": hostnames,
                        "services": services,
                        "org": m.get("org", ""),
                        "os": m.get("os", ""),
                        "country": m.get("location", {}).get("country_name", ""),
                        "tags": m.get("tags", []),
                    },
                    tags=["shodan", "exposed", f"port:{port}"],
                )
            )
        if results:
            results.insert(
                0,
                UnifiedResult(
                    source="shodan",
                    target=query,
                    result_type="search_meta",
                    confidence=0.95,
                    name=f"Shodan search: {query}",
                    description=f"Found {total} total results in Shodan",
                    evidence={"total": total, "query": query},
                    tags=["shodan", "search_meta"],
                    severity="info",
                ),
            )
        return results

    def _parse_host(self, data: dict[str, Any]) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        ip = data.get("ip_str", "")
        ports = data.get("ports", [])
        hostnames = data.get("hostnames", [])
        for port in ports[:20]:
            results.append(
                UnifiedResult(
                    source="shodan",
                    target=ip,
                    result_type="open_port",
                    severity=self._port_severity(port),
                    confidence=0.85,
                    name=f"Shodan host: {ip}:{port}",
                    evidence={"ip": ip, "port": port, "hostnames": hostnames, "os": data.get("os", "")},
                    tags=["shodan", "host"],
                )
            )
        return results

    @staticmethod
    def _port_severity(port: int) -> str:
        high_ports = {21, 22, 23, 3389, 5900, 6379, 27017, 9200}
        medium_ports = {80, 443, 8080, 8443, 3306, 5432, 1433}
        if port in high_ports:
            return "medium"
        if port in medium_ports:
            return "info"
        return "info"

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return []
