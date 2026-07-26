"""Lightweight OSINT engine — DNS, crt.sh, WHOIS, email security, GeoIP.

Zero-dependency HTTP-based OSINT queries (stdlib + httpx only).
Sources: HackerTarget (free, no key), crt.sh, ip-api.com.
"""

from __future__ import annotations

import logging
import socket
from typing import Any

import httpx

logger = logging.getLogger("cateye.osint")

HACKERTARGET = "https://api.hackertarget.com"


class OSINTEngine:
    def __init__(self) -> None:
        self._http = httpx.Client(timeout=10.0)

    def dns_resolve(self, domain: str, record: str = "a") -> dict[str, Any]:
        try:
            if record.lower() == "a":
                addrs = set()
                for info in socket.getaddrinfo(domain, 0, socket.AF_INET):
                    addrs.add(info[4][0])
                return {"domain": domain, "type": "A", "records": sorted(addrs), "count": len(addrs)}
            resp = self._http.get(f"{HACKERTARGET}/dnslookup/", params={"q": domain})
            if resp.status_code == 200:
                lines = [line for line in resp.text.strip().split("\n") if line.lower().startswith(domain.lower())]
                return {"domain": domain, "type": record.upper(), "records": lines[:20], "count": len(lines)}
            return {"domain": domain, "type": record.upper(), "records": [], "error": resp.text[:200]}
        except Exception as exc:
            logger.warning("dns_resolve(%s) failed: %s", domain, exc)
            return {"domain": domain, "type": record.upper(), "records": [], "error": str(exc)}

    def crtsh_search(self, domain: str) -> list[dict[str, Any]]:
        try:
            resp = self._http.get("https://crt.sh/", params={"q": domain, "output": "json"}, timeout=15.0)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return [
                        {"id": r.get("id"), "name_value": r.get("name_value", ""), "not_after": r.get("not_after", "")}
                        for r in data[:100]
                    ]
            return []
        except Exception as exc:
            logger.warning("crtsh_search(%s) failed: %s", domain, exc)
            return []

    def whois(self, domain: str) -> dict[str, Any]:
        try:
            resp = self._http.get(f"{HACKERTARGET}/whois/", params={"q": domain})
            if resp.status_code == 200:
                lines = resp.text.strip().split("\n")[:40]
                return {"domain": domain, "lines": lines, "count": len(lines)}
            return {"domain": domain, "error": resp.text[:200]}
        except Exception as exc:
            logger.warning("whois(%s) failed: %s", domain, exc)
            return {"domain": domain, "error": str(exc)}

    def email_security(self, domain: str) -> dict[str, Any]:
        try:
            spf = self._http.get(f"{HACKERTARGET}/dnslookup/", params={"q": domain}, timeout=8.0)
            mx = self._http.get(f"{HACKERTARGET}/mxlookup/", params={"q": domain}, timeout=8.0)
            dmarc = self._http.get(f"{HACKERTARGET}/dnslookup/", params={"q": f"_dmarc.{domain}"}, timeout=8.0)
            result: dict[str, Any] = {"domain": domain}
            if spf.status_code == 200:
                spf_lines = [line for line in spf.text.strip().split("\n") if "v=spf1" in line.lower()]
                result["spf"] = spf_lines[:5]
                result["spf_count"] = len(spf_lines)
            if mx.status_code == 200:
                mx_lines = [line for line in mx.text.strip().split("\n") if line.strip()]
                result["mx_records"] = mx_lines[:10]
                result["mx_count"] = len(mx_lines)
            if dmarc.status_code == 200:
                dmarc_lines = [line for line in dmarc.text.strip().split("\n") if "v=dmarc1" in line.lower()]
                result["dmarc"] = dmarc_lines[:5]
            return result
        except Exception as exc:
            logger.warning("email_security(%s) failed: %s", domain, exc)
            return {"domain": domain, "error": str(exc)}

    def geoip(self, ip: str) -> dict[str, Any]:
        try:
            resp = self._http.get(f"http://ip-api.com/json/{ip}", timeout=5.0)
            if resp.status_code == 200:
                return resp.json()
            return {"ip": ip, "error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            logger.warning("geoip(%s) failed: %s", ip, exc)
            return {"ip": ip, "error": str(exc)}

    def reverse_ip(self, ip: str) -> dict[str, Any]:
        try:
            resp = self._http.get(f"{HACKERTARGET}/reverseiplookup/", params={"q": ip})
            if resp.status_code == 200:
                domains = [
                    line.strip()
                    for line in resp.text.strip().split("\n")
                    if line.strip() and "error" not in line.lower()
                ]
                return {"ip": ip, "domains": domains[:50], "count": len(domains)}
            return {"ip": ip, "error": resp.text[:200]}
        except Exception as exc:
            logger.warning("reverse_ip(%s) failed: %s", ip, exc)
            return {"ip": ip, "error": str(exc)}

    def subdomain_discover(self, domain: str) -> list[str]:
        subdomains: list[str] = []
        try:
            crt = self.crtsh_search(domain)
            seen: set[str] = set()
            for entry in crt:
                for name in entry.get("name_value", "").split("\n"):
                    n = name.strip().lower()
                    if n.endswith(f".{domain}") and n not in seen:
                        seen.add(n)
                        subdomains.append(n)
        except Exception as exc:
            logger.warning("subdomain_discover(%s) failed: %s", domain, exc)
        return sorted(subdomains)[:200]

    def domain_recon(self, domain: str) -> dict[str, Any]:
        dns = self.dns_resolve(domain)
        subdomains = self.subdomain_discover(domain)
        whois_data = self.whois(domain)
        email = self.email_security(domain)
        result: dict[str, Any] = {
            "domain": domain,
            "ip_count": dns.get("count", 0),
            "subdomain_count": len(subdomains),
            "subdomains": subdomains[:50],
        }
        if dns.get("records"):
            result["ips"] = dns["records"]
        if whois_data.get("lines"):
            result["whois_preview"] = whois_data["lines"][:10]
        if email:
            for key in ("spf", "dmarc", "mx_records"):
                if email.get(key):
                    result[key] = email[key]
        return result


def get_osint_engine() -> OSINTEngine:
    return OSINTEngine()
