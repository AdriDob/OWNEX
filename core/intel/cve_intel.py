from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("catseye.intel.cve")

TECH_CVE_MAP = {
    "nginx": [
        {
            "id": "CVE-2024-24989",
            "cvss": 7.5,
            "epss": 0.85,
            "kev": True,
            "description": "HTTP/2 memory consumption leads to DoS via rapid stream reset",
            "fix": "Upgrade nginx to ≥1.25.3 or apply the patch for HTTP/2 stream limits.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-24989",
        },
        {
            "id": "CVE-2024-31079",
            "cvss": 6.5,
            "epss": 0.42,
            "kev": False,
            "description": "MP4 module memory disclosure when processing crafted MP4 files",
            "fix": "Disable ngx_http_mp4_module if not in use, or upgrade to ≥1.26.0.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-31079",
        },
    ],
    "python": [
        {
            "id": "CVE-2024-9287",
            "cvss": 8.1,
            "epss": 0.91,
            "kev": True,
            "description": "Python tarfile module directory traversal via symlinks in tar archives",
            "fix": "Upgrade Python to ≥3.12.8, ≥3.13.3. Use extract filter in tarfile.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-9287",
        },
        {
            "id": "CVE-2024-6232",
            "cvss": 7.5,
            "epss": 0.63,
            "kev": False,
            "description": "Python urllib HTTP redirect cookie manipulation via crafted server response",
            "fix": "Upgrade Python to ≥3.12.6, ≥3.13.0rc2. Ensure HTTPRedirectHandler validates cookies.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-6232",
        },
    ],
    "node": [
        {
            "id": "CVE-2024-37890",
            "cvss": 7.5,
            "epss": 0.72,
            "kev": True,
            "description": "Node.js HTTP request smuggling via Content-Length + Transfer-Encoding discrepancy",
            "fix": "Upgrade Node.js to ≥20.15.0, ≥22.4.0. Use --http-server-default-timeout.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-37890",
        },
    ],
    "postgresql": [
        {
            "id": "CVE-2024-4318",
            "cvss": 8.8,
            "epss": 0.95,
            "kev": True,
            "description": "PostgreSQL SQL injection via crafted pg_dump output during restore with pg_restore",
            "fix": "Upgrade PostgreSQL to ≥16.3, ≥15.7, ≥14.12. Avoid restoring untrusted dumps.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-4318",
        },
    ],
    "redis": [
        {
            "id": "CVE-2024-46981",
            "cvss": 7.5,
            "epss": 0.55,
            "kev": False,
            "description": "Redis Lua sandbox escape via crafted script using debug() and table functions",
            "fix": "Upgrade Redis to ≥7.2.6, ≥7.4.1. Disable Lua scripting if not needed.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-46981",
        },
    ],
    "docker": [
        {
            "id": "CVE-2024-21626",
            "cvss": 8.6,
            "epss": 0.88,
            "kev": True,
            "description": "Docker runC container escape via crafted /proc/self/fd symlink leading to host filesystem access",
            "fix": "Upgrade Docker to ≥25.0.2, runC to ≥1.1.12. Use --userns-remap for additional isolation.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-21626",
        },
    ],
    "wordpress": [
        {
            "id": "CVE-2024-44000",
            "cvss": 9.8,
            "epss": 0.97,
            "kev": True,
            "description": "WordPress RCE via arbitrary file upload in plugin/theme installation due to insufficient type validation",
            "fix": "Upgrade WordPress to ≥6.6.2. Harden wp-config with DISALLOW_FILE_EDIT and DISALLOW_FILE_MODS.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-44000",
        },
    ],
    "apache": [
        {
            "id": "CVE-2024-38477",
            "cvss": 9.1,
            "epss": 0.92,
            "kev": True,
            "description": "Apache HTTP Server mod_proxy SSRF via crafted HTTP requests that bypass access controls",
            "fix": "Upgrade Apache HTTP Server to ≥2.4.60. Restrict mod_proxy with Allow/Deny rules.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-38477",
        },
    ],
    "kubernetes": [
        {
            "id": "CVE-2024-3177",
            "cvss": 8.0,
            "epss": 0.78,
            "kev": False,
            "description": "Kubernetes RBAC privilege escalation via crafted role binding that grants cluster-admin through namespaced roles",
            "fix": "Upgrade Kubernetes to ≥1.29.5, ≥1.30.1. Audit RBAC with `kubectl auth reconcile`.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-3177",
        },
    ],
    "openssl": [
        {
            "id": "CVE-2024-9143",
            "cvss": 7.5,
            "epss": 0.68,
            "kev": False,
            "description": "OpenSSL certificate verification bypass via crafted intermediate CA certificates",
            "fix": "Upgrade OpenSSL to ≥3.0.15, ≥3.3.3. Verify with `openssl verify -CAfile`.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-9143",
        },
    ],
    "mongodb": [
        {
            "id": "CVE-2024-3371",
            "cvss": 7.5,
            "epss": 0.60,
            "kev": False,
            "description": "MongoDB aggregation pipeline injection allowing arbitrary field access via $lookup and $graphLookup",
            "fix": "Upgrade MongoDB to ≥7.0.12, ≥8.0.0. Sanitize user input in aggregation pipelines.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-3371",
        },
    ],
    "git": [
        {
            "id": "CVE-2024-32002",
            "cvss": 8.0,
            "epss": 0.81,
            "kev": True,
            "description": "Git clone RCE via crafted submodule URL with hook injection during recursive clone",
            "fix": "Upgrade Git to ≥2.45.1. Use `git config --global protocol.file.allow never`.",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-32002",
        },
    ],
}


@dataclass
class CVEResult:
    id: str
    cvss: float
    epss: float
    priority_score: float
    description: str
    kev: bool
    tech: str
    priority_label: str
    fix: str
    url: str
    data_sources: list[str] = field(default_factory=lambda: ["NVD", "EPSS (FIRST)", "CISA KEV"])


def _compute_priority(cvss: float, epss: float, kev: bool) -> tuple[float, str]:
    score = cvss * 0.4 + epss * 10 * 0.35 + (1.0 if kev else 0) * 2.5
    score = min(score, 10.0)
    if score >= 8.0:
        label = "Critical"
    elif score >= 6.0:
        label = "High"
    elif score >= 4.0:
        label = "Medium"
    else:
        label = "Low"
    return round(score, 1), label


async def prioritize_cves(tech_stack: list[str]) -> list[CVEResult]:
    seen: set[str] = set()
    results: list[CVEResult] = []
    for raw_tech in tech_stack:
        tech = raw_tech.strip().lower()
        for cve_list_key, cves in TECH_CVE_MAP.items():
            if cve_list_key != tech and tech not in cve_list_key:
                continue
            for c in cves:
                if c["id"] in seen:
                    continue
                seen.add(c["id"])
                score, label = _compute_priority(c["cvss"], c["epss"], c["kev"])
                results.append(
                    CVEResult(
                        id=c["id"],
                        cvss=c["cvss"],
                        epss=c["epss"],
                        priority_score=score,
                        description=c["description"],
                        kev=c["kev"],
                        tech=cve_list_key,
                        priority_label=label,
                        fix=c["fix"],
                        url=c["url"],
                    )
                )
    results.sort(key=lambda r: r.priority_score, reverse=True)
    return results
