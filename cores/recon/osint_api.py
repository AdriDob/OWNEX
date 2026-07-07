"""
OSINT API clients for external intelligence gathering.

Each client is a minimal wrapper over httpx that handles auth, errors,
and returns structured dicts. Configure API keys via .env or settings.

Supported services:
  1. Shodan
  2. Censys
  3. VirusTotal
  4. SecurityTrails
  5. AlienVault OTX
  6. URLScan.io
  7. Hunter.io
  8. BuiltWith
  9. Have I Been Pwned
  10. GreyNoise
  11. IntelX (Intelligence X)
  12. Pulsedive
  13. SpoofCheck (email spoof analysis)
  14. ThreatFox
  15. IPInfo
  16. AbstractAPI (geolocation, email validation)
"""

import hashlib
import logging
import os
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("cateye.osint")


class OSINTClient:
    """Base client with shared HTTP logic."""

    def __init__(self, base_url: str, api_key_env: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get(api_key_env, "")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"User-Agent": "CATEYE-OSINT/1.0"},
            )
        return self._client

    async def _get(self, path: str, params: dict | None = None) -> dict[str, Any] | None:
        if not self.api_key:
            logger.warning("%s: no API key configured (env %s)", type(self).__name__, self.api_key)
            return None
        client = await self._get_client()
        try:
            r = await client.get(path, params=params)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            logger.warning("%s HTTP %s: %s", type(self).__name__, e.response.status_code, e.response.text[:200])
            return None
        except Exception as e:
            logger.error("%s request failed: %s", type(self).__name__, e)
            return None

    async def _post(self, path: str, json: dict | None = None) -> dict[str, Any] | None:
        if not self.api_key:
            return None
        client = await self._get_client()
        try:
            r = await client.post(path, json=json)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            logger.warning("%s HTTP %s: %s", type(self).__name__, e.response.status_code, e.response.text[:200])
            return None
        except Exception as e:
            logger.error("%s request failed: %s", type(self).__name__, e)
            return None

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


class ShodanClient(OSINTClient):
    """Shodan — service banners, open ports, vulns."""

    def __init__(self):
        super().__init__("https://api.shodan.io", "SHODAN_API_KEY")

    async def host(self, ip: str) -> dict[str, Any] | None:
        return await self._get(f"/shodan/host/{ip}", params={"key": self.api_key})

    async def search(self, query: str, page: int = 1) -> dict[str, Any] | None:
        return await self._get("/shodan/host/search", params={"key": self.api_key, "query": query, "page": page})

    async def dns_resolve(self, domain: str) -> dict[str, Any] | None:
        return await self._get("/dns/resolve", params={"key": self.api_key, "hostnames": domain})

    async def exploits(self, query: str) -> dict[str, Any] | None:
        return await self._get("/shodan/exploit/search", params={"key": self.api_key, "query": query})


class CensysClient(OSINTClient):
    """Censys — internet asset discovery, certificate transparency."""

    def __init__(self):
        super().__init__("https://search.censys.io/api/v2", "CENSYS_API_KEY")
        self.secret = os.environ.get("CENSYS_API_SECRET", "")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            auth = httpx.BasicAuth(self.api_key, self.secret) if self.api_key and self.secret else None
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                auth=auth,
                headers={"User-Agent": "CATEYE-OSINT/1.0"},
            )
        return self._client

    async def search_hosts(self, query: str, per_page: int = 10) -> dict[str, Any] | None:
        return await self._post("/hosts/search", json={"q": query, "per_page": per_page})

    async def host_view(self, ip: str) -> dict[str, Any] | None:
        return await self._get(f"/hosts/{ip}")

    async def certificates_search(self, query: str) -> dict[str, Any] | None:
        return await self._post("/certificates/search", json={"q": query, "per_page": 10})


class VirusTotalClient(OSINTClient):
    """VirusTotal — file/URL/IP threat intelligence."""

    def __init__(self):
        super().__init__("https://www.virustotal.com/api/v3", "VIRUSTOTAL_API_KEY")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "x-apikey": self.api_key,
                    "User-Agent": "CATEYE-OSINT/1.0",
                },
            )
        return self._client

    async def ip_report(self, ip: str) -> dict[str, Any] | None:
        return await self._get(f"/ip_addresses/{ip}")

    async def domain_report(self, domain: str) -> dict[str, Any] | None:
        return await self._get(f"/domains/{domain}")

    async def url_report(self, url: str) -> dict[str, Any] | None:
        url_id = hashlib.sha256(url.encode()).hexdigest()
        return await self._get(f"/urls/{url_id}")

    async def file_report(self, file_hash: str) -> dict[str, Any] | None:
        return await self._get(f"/files/{file_hash}")


class SecurityTrailsClient(OSINTClient):
    """SecurityTrails — DNS, subdomain, WHOIS intelligence."""

    def __init__(self):
        super().__init__("https://api.securitytrails.com/v1", "SECURITYTRAILS_API_KEY")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "APIKEY": self.api_key,
                    "User-Agent": "CATEYE-OSINT/1.0",
                },
            )
        return self._client

    async def domain_info(self, domain: str) -> dict[str, Any] | None:
        return await self._get(f"/domain/{domain}")

    async def subdomains(self, domain: str) -> list[str]:
        data = await self._get(f"/domain/{domain}/subdomains")
        if data and "subdomains" in data:
            return [f"{sub}.{domain}" for sub in data["subdomains"]]
        return []

    async def dns_history(self, domain: str, record_type: str = "a") -> dict[str, Any] | None:
        return await self._get(f"/domain/{domain}/history/{record_type}")

    async def whois(self, domain: str) -> dict[str, Any] | None:
        return await self._get(f"/domain/{domain}/whois")


class AlienVaultClient(OSINTClient):
    """AlienVault OTX — threat intelligence, IoCs."""

    def __init__(self):
        super().__init__("https://otx.alienvault.com/api/v1", "ALIENVAULT_OTX_KEY")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "X-OTX-API-KEY": self.api_key,
                    "User-Agent": "CATEYE-OSINT/1.0",
                },
            )
        return self._client

    async def ip_reputation(self, ip: str) -> dict[str, Any] | None:
        return await self._get(f"/indicators/IPv4/{ip}/general")

    async def domain_reputation(self, domain: str) -> dict[str, Any] | None:
        return await self._get(f"/indicators/domain/{domain}/general")

    async def url_reputation(self, url: str) -> dict[str, Any] | None:
        encoded = quote(url, safe="")
        return await self._get(f"/indicators/url/{encoded}/general")

    async def pulses(self, limit: int = 10) -> dict[str, Any] | None:
        return await self._get("/pulses/subscribed", params={"limit": limit})


class URLScanClient(OSINTClient):
    """URLScan.io — website screenshot, DOM, requests analysis."""

    def __init__(self):
        super().__init__("https://urlscan.io/api/v1", "URLSCAN_API_KEY")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            api_key = self.api_key
            headers = {"User-Agent": "CATEYE-OSINT/1.0"}
            if api_key:
                headers["API-Key"] = api_key
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, headers=headers)
        return self._client

    async def search(self, query: str, size: int = 10) -> dict[str, Any] | None:
        return await self._get("/search/", params={"q": query, "size": size})

    async def submit(self, url: str) -> dict[str, Any] | None:
        return await self._post("/scan/", json={"url": url, "visibility": "unlisted"})

    async def result(self, uuid: str) -> dict[str, Any] | None:
        return await self._get(f"/result/{uuid}")


class HunterClient(OSINTClient):
    """Hunter.io — email pattern discovery, domain email search."""

    def __init__(self):
        super().__init__("https://api.hunter.io/v2", "HUNTER_API_KEY")

    async def domain_search(self, domain: str) -> dict[str, Any] | None:
        return await self._get("/domain-search", params={"domain": domain, "api_key": self.api_key})

    async def email_finder(self, domain: str, first_name: str, last_name: str) -> dict[str, Any] | None:
        return await self._get("/email-finder", params={
            "domain": domain, "first_name": first_name, "last_name": last_name, "api_key": self.api_key,
        })

    async def email_verifier(self, email: str) -> dict[str, Any] | None:
        return await self._get("/email-verifier", params={"email": email, "api_key": self.api_key})


class BuiltWithClient(OSINTClient):
    """BuiltWith — website technology profiling."""

    def __init__(self):
        super().__init__("https://api.builtwith.com", "BUILTWITH_API_KEY")

    async def tech_lookup(self, domain: str) -> dict[str, Any] | None:
        return await self._get("/v21/api/api.json", params={"KEY": self.api_key, "LOOKUP": domain})


class HIBPClient(OSINTClient):
    """Have I Been Pwned — breach and paste account monitoring."""

    def __init__(self):
        super().__init__("https://haveibeenpwned.com/api/v3", "HIBP_API_KEY")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "hibp-api-key": self.api_key,
                    "User-Agent": "CATEYE-OSINT/1.0",
                },
            )
        return self._client

    async def breached_account(self, email: str) -> list[dict[str, Any]] | None:
        data = await self._get(f"/breachedaccount/{quote(email)}", params={"truncateResponse": "false"})
        return data if isinstance(data, list) else None

    async def all_breaches(self) -> list[dict[str, Any]] | None:
        data = await self._get("/breaches")
        return data if isinstance(data, list) else None

    async def paste_account(self, email: str) -> list[dict[str, Any]] | None:
        data = await self._get(f"/pasteaccount/{quote(email)}")
        return data if isinstance(data, list) else None


class GreyNoiseClient(OSINTClient):
    """GreyNoise — internet noise / threat context for IPs."""

    def __init__(self):
        super().__init__("https://api.greynoise.io/v2", "GREYNOISE_API_KEY")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "key": self.api_key,
                    "User-Agent": "CATEYE-OSINT/1.0",
                },
            )
        return self._client

    async def ip_context(self, ip: str) -> dict[str, Any] | None:
        return await self._get(f"/noise/context/{ip}")

    async def ip_quick(self, ip: str) -> dict[str, Any] | None:
        return await self._get(f"/noise/quick/{ip}")


class IntelXClient(OSINTClient):
    """Intelligence X — dark web, leaked data, document search."""

    def __init__(self):
        super().__init__("https://2.intelx.io", "INTELX_API_KEY")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "x-key": self.api_key,
                    "User-Agent": "CATEYE-OSINT/1.0",
                },
            )
        return self._client

    async def search(self, term: str, max_results: int = 10) -> dict[str, Any] | None:
        return await self._get("/intelligent/search", params={"term": term, "maxresults": max_results, "sort": 2})

    async def search_result(self, id: str) -> dict[str, Any] | None:
        return await self._get(f"/intelligent/search/result?id={id}&statistics=0&case=0")


class PulsediveClient(OSINTClient):
    """Pulsedive — free threat intelligence & IoC enrichment."""

    def __init__(self):
        super().__init__("https://pulsedive.com/api", "PULSEDIVE_API_KEY")

    async def indicator_info(self, indicator: str) -> dict[str, Any] | None:
        return await self._get("/info.php", params={"indicator": indicator, "key": self.api_key})

    async def threat_lookup(self, threat_id: str) -> dict[str, Any] | None:
        return await self._get("/threat.php", params={"tid": threat_id, "key": self.api_key})

    async def search(self, query: str) -> dict[str, Any] | None:
        return await self._get("/search.php", params={"value": query, "key": self.api_key})


class ThreatFoxClient(OSINTClient):
    """ThreatFox (abuse.ch) — malware IoC feed."""

    def __init__(self):
        super().__init__("https://threatfox-api.abuse.ch/api/v1", "")

    async def search_ioc(self, ioc: str) -> dict[str, Any] | None:
        return await self._post("/", json={"query": "search_ioc", "search_term": ioc})

    async def recent(self, limit: int = 20) -> dict[str, Any] | None:
        return await self._post("/", json={"query": "get_recent", "limit": limit})


class IPInfoClient(OSINTClient):
    """IPInfo — geolocation, ASN, carrier data."""

    def __init__(self):
        super().__init__("https://ipinfo.io", "IPINFO_API_KEY")

    async def ip_data(self, ip: str) -> dict[str, Any] | None:
        token = f"?token={self.api_key}" if self.api_key else ""
        return await self._get(f"/{ip}{token}")

    async def bulk_lookup(self, ips: list[str]) -> dict[str, Any] | None:
        return await self._post(f"/batch?token={self.api_key}" if self.api_key else "/batch", json={"ips": ips})


class SpoofCheckClient(OSINTClient):
    """Check SPF/DMARC/DKIM records for email spoof risk."""

    def __init__(self):
        super().__init__("https://spoofcheck.io/api", "")

    async def check_domain(self, domain: str) -> dict[str, Any] | None:
        return await self._get(f"/domain/{domain}")


# Registry for discovery
CLIENTS: dict[str, OSINTClient] = {
    "shodan": ShodanClient(),
    "censys": CensysClient(),
    "virustotal": VirusTotalClient(),
    "securitytrails": SecurityTrailsClient(),
    "alienvault": AlienVaultClient(),
    "urlscan": URLScanClient(),
    "hunter": HunterClient(),
    "builtwith": BuiltWithClient(),
    "hibp": HIBPClient(),
    "greynoise": GreyNoiseClient(),
    "intelx": IntelXClient(),
    "pulsedive": PulsediveClient(),
    "threatfox": ThreatFoxClient(),
    "ipinfo": IPInfoClient(),
    "spoofcheck": SpoofCheckClient(),
}


async def query_all(service: str, target: str) -> dict[str, Any]:
    """Query a specific OSINT service about a target (IP/domain/email/URL).

    Returns the raw result dict, or an error dict if the service is unknown
    or has no API key configured.
    """
    client = CLIENTS.get(service)
    if not client:
        return {"error": f"Unknown OSINT service: {service}. Available: {', '.join(CLIENTS)}"}

    method = getattr(client, target.replace(".", "_"), None)
    if method is None:
        return {"error": f"Target type not supported by {service}"}

    result = await method(target)
    if result is None:
        return {"error": f"No data or API key not configured for {service}"}
    return {"service": service, "target": target, "data": result}


async def close_all():
    for client in CLIENTS.values():
        await client.close()
