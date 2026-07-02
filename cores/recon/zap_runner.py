"""
core.recon.zap_runner — OWASP ZAP passive integration.

ZAP runs as a local daemon (zap.sh -daemon -port 8090 -config api.disablekey=true).
All operations are PASSIVE — spider discovers endpoints, passive scan observes
traffic. NO active scan (ascan) is called from this module.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass, field
from typing import Any

try:
    import aiohttp
except ImportError:
    aiohttp = None  # type: ignore[assignment]

LOG = logging.getLogger("catseye.recon.zap")


@dataclass
class ZapAlert:
    alert: str
    risk: str
    confidence: str
    url: str
    param: str
    attack: str
    description: str
    solution: str
    reference: str
    cwe_id: str = ""
    wasc_id: str = ""
    plugin_id: str = ""
    evidence: str = ""
    other: str = ""

    @property
    def risk_score(self) -> int:
        mapping = {"high": 3, "medium": 2, "low": 1, "info": 0, "informational": 0}
        return mapping.get(self.risk.lower(), 0)

    @property
    def is_passive(self) -> bool:
        return bool(self.plugin_id) and not self.attack


@dataclass
class ZapSite:
    name: str
    urls: list[str] = field(default_factory=list)
    alerts: list[ZapAlert] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)


def is_zap_installed() -> bool:
    return shutil.which("zap.sh") is not None or shutil.which("zaproxy") is not None


INSTALL_HINT = """
OWASP ZAP no está instalado. Instálalo:

  # Linux/WSL (snap)
  sudo snap install zaproxy --classic

  # O descarga directa desde https://www.zaproxy.org/download/

Luego inicia el daemon:
  zap.sh -daemon -port 8090 -config api.disablekey=true
"""


class ZapConnectionError(Exception):
    pass


class ZapRunner:
    def __init__(self, zap_api_url: str = "http://localhost:8090"):
        self.api_url = zap_api_url
        self._session = None

    async def _ensure_session(self):
        if aiohttp is None:
            raise ZapConnectionError("aiohttp is not installed — cannot connect to ZAP daemon")
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        session = await self._ensure_session()
        url = f"{self.api_url}/JSON/{endpoint}"
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    raise ZapConnectionError(f"ZAP API error {resp.status}: {await resp.text()}")
                return await resp.json()
        except asyncio.TimeoutError:
            raise ZapConnectionError(f"ZAP API timeout: {url}")
        except aiohttp.ClientConnectorError as e:
            raise ZapConnectionError(f"Cannot connect to ZAP daemon at {self.api_url}: {e}")

    async def _post(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        session = await self._ensure_session()
        url = f"{self.api_url}/JSON/{endpoint}"
        try:
            async with session.post(url, data=params, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                if resp.status != 200:
                    raise ZapConnectionError(f"ZAP API error {resp.status}: {await resp.text()}")
                return await resp.json()
        except asyncio.TimeoutError:
            raise ZapConnectionError(f"ZAP API timeout: {url}")
        except aiohttp.ClientConnectorError as e:
            raise ZapConnectionError(f"Cannot connect to ZAP daemon at {self.api_url}: {e}")

    # ── Spider (crawling, NOT active scanning) ─────────────────────────

    async def spider_scan(self, target_url: str, max_children: int = 10) -> dict:
        """Spider/crawl the target to discover endpoints, forms, parameters.

        This is a pure spider — it navigates links like a browser would.
        It does NOT send attack payloads.
        """
        LOG.info("ZAP spider starting: %s", target_url)

        scan = await self._post("spider/action/scan", {
            "url": target_url,
            "maxChildren": str(max_children),
            "recurse": "true",
        })
        scan_id = scan.get("scan")

        if not scan_id:
            raise ZapConnectionError("ZAP spider did not return a scan ID")

        LOG.info("ZAP spider scan ID: %s", scan_id)

        progress = 0
        while progress < 100:
            status = await self._get("spider/view/status", {"scanId": str(scan_id)})
            progress = int(status.get("status", 0))
            LOG.debug("ZAP spider progress: %d%%", progress)
            await asyncio.sleep(2)

        results = await self._get("spider/view/results", {"scanId": str(scan_id)})
        urls = results.get("urls", [])
        if isinstance(urls, str):
            urls = urls.split("\n") if urls.strip() else []

        full_results = await self._get("spider/view/fullResults", {"scanId": str(scan_id)})
        LOG.info("ZAP spider finished: %d URLs discovered", len(urls))

        return {
            "scan_id": scan_id,
            "urls_found": urls,
            "url_count": len(urls),
            "full_results": full_results,
        }

    # ── Passive Scan Results ───────────────────────────────────────────

    async def passive_scan_results(self, target_url: str) -> list[dict]:
        """Read passive scan alerts for the target.

        These are generated automatically by ZAP as it observes traffic:
          - Missing security headers (CSP, X-Frame-Options, HSTS, etc.)
          - Cookies without Secure/HttpOnly flags
          - Sensitive info exposed in responses
          - Detected technologies
          - Weak TLS configurations
          - Autocomplete fields, cacheable HTTPS, etc.

        ZAP generates these WITHOUT sending any attack payloads.
        """
        LOG.info("Fetching ZAP passive alerts for: %s", target_url)

        alerts = await self._get("alert/view/alerts", {
            "baseurl": target_url,
        })

        raw = alerts.get("alerts", [])
        results = []
        for a in raw:
            alert = self._normalize_alert(a)
            if alert.is_passive:
                results.append({
                    "alert": alert.alert,
                    "risk": alert.risk,
                    "risk_score": alert.risk_score,
                    "confidence": alert.confidence,
                    "url": alert.url,
                    "param": alert.param,
                    "description": alert.description,
                    "solution": alert.solution,
                    "cwe_id": alert.cwe_id,
                    "plugin_id": alert.plugin_id,
                    "evidence": alert.evidence,
                })

        LOG.info("ZAP passive alerts: %d found", len(results))
        return results

    async def get_alerts(
        self,
        target_url: str | None = None,
        risk_level: str | None = None,
    ) -> list[dict]:
        """Get ZAP alerts, optionally filtered by target URL and risk level.

        Normalized to the hypothesis format used by the system.
        """
        params: dict[str, Any] = {}
        if target_url:
            params["baseurl"] = target_url
        if risk_level:
            params["risk"] = risk_level

        alerts = await self._get("alert/view/alerts", params or None)
        raw = alerts.get("alerts", [])
        results = []
        for a in raw:
            alert = self._normalize_alert(a)
            if risk_level and alert.risk_score < self._risk_threshold(risk_level):
                continue
            results.append({
                "alert": alert.alert,
                "risk": alert.risk,
                "risk_score": alert.risk_score,
                "confidence": alert.confidence,
                "url": alert.url,
                "param": alert.param,
                "attack": alert.attack,
                "description": alert.description,
                "solution": alert.solution,
                "reference": alert.reference,
                "cwe_id": alert.cwe_id,
                "plugin_id": alert.plugin_id,
                "evidence": alert.evidence,
                "is_passive": alert.is_passive,
            })

        return results

    # ── Technology Detection ───────────────────────────────────────────

    async def get_technologies(self, target_url: str) -> list[str]:
        """Get technologies detected by ZAP's passive fingerprinting."""
        LOG.info("Fetching ZAP technologies for: %s", target_url)
        try:
            sites = await self._get("core/view/sites")
            site_list = sites.get("sites", [])
            for site in site_list:
                if target_url.rstrip("/") in site:
                    tech = await self._get("core/view/technology", {"site": site})
                    return tech.get("technologies", [])
        except Exception as e:
            LOG.warning("Failed to get ZAP technologies: %s", e)
        return []

    # ── Health Check ───────────────────────────────────────────────────

    async def health_check(self) -> dict:
        """Check if ZAP daemon is running and responsive."""
        try:
            version = await self._get("core/view/version")
            return {
                "running": True,
                "version": version.get("version", "unknown"),
            }
        except ZapConnectionError as e:
            return {
                "running": False,
                "error": str(e),
            }

    async def new_session(self, name: str = "CATEYE-scan", overwrite: bool = True) -> dict:
        """Create a new ZAP session for isolated scanning."""
        return await self._post("core/action/newSession", {
            "name": name,
            "overwrite": "true" if overwrite else "false",
        })

    async def access_url(self, url: str) -> dict:
        """Tell ZAP to access a URL so it can passively analyze it."""
        return await self._post("core/action/accessUrl", {"url": url})

    # ── Internals ──────────────────────────────────────────────────────

    def _normalize_alert(self, raw: dict) -> ZapAlert:
        return ZapAlert(
            alert=raw.get("alert", raw.get("name", "")),
            risk=raw.get("risk", raw.get("riskdesc", "Unknown")).split(" ")[0].title(),
            confidence=raw.get("confidence", "Unknown"),
            url=raw.get("url", ""),
            param=raw.get("param", ""),
            attack=raw.get("attack", ""),
            description=raw.get("description", ""),
            solution=raw.get("solution", ""),
            reference=raw.get("reference", ""),
            cwe_id=str(raw.get("cweid", "")),
            wasc_id=str(raw.get("wascid", "")),
            plugin_id=str(raw.get("pluginid", "")),
            evidence=raw.get("evidence", ""),
            other=raw.get("other", ""),
        )

    def _risk_threshold(self, level: str) -> int:
        mapping = {"high": 3, "medium": 2, "low": 1, "info": 0}
        return mapping.get(level.lower(), 0)


INSTALLED = is_zap_installed()
if not INSTALLED:
    LOG.warning("OWASP ZAP no está instalado. Algunas funciones de recon pasivo no estarán disponibles.")
    LOG.warning(INSTALL_HINT)
