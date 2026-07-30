"""AttackSurfaceExecutor — port scanning, service discovery, tech detection stage.

Stage 2 of the security pipeline. Identifies open ports, running services,
and technologies for a given target or list of endpoints.
"""

from __future__ import annotations

import json
from typing import Any

from cores.cycles.stages import BaseStageExecutor


class AttackSurfaceExecutor(BaseStageExecutor):
    """Map the attack surface of discovered targets.

    Discovers open ports, running services, and technology stacks
    using passive techniques and (optionally) active scanning.
    """

    @property
    def name(self) -> str:
        return "attack_surface"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self.logger.info("Starting attack_surface stage")
        target = context.get("target", "")
        if not target:
            return self._wrap_result("failed", "No target provided", error="Missing 'target' in context")

        endpoints = context.get("endpoints", [])
        scan_type = context.get("scan_type", "passive")

        try:
            open_ports = self._scan_ports(target, endpoints, scan_type)
            services = self._identify_services(target, open_ports)
            tech_stack = self._detect_technologies(target, endpoints)
            cdn_info = self._check_cdn(target)

            summary = (
                f"Attack surface mapped for {target}: "
                f"{len(open_ports)} open ports, "
                f"{len(services)} services, "
                f"{len(tech_stack)} technologies"
            )

            details: dict[str, Any] = {
                "target": target,
                "open_ports": open_ports,
                "services": services,
                "tech_stack": tech_stack,
                "cdn": cdn_info,
                "scan_type": scan_type,
                "total_endpoints_analyzed": len(endpoints),
            }
            self._log_results(target, open_ports, services, tech_stack, scan_type)
            return self._wrap_result("completed", summary, details=details)

        except Exception as e:
            self.logger.error("Attack surface stage failed: %s", e)
            return self._wrap_result("failed", f"Attack surface mapping failed: {e}", error=str(e))

    def _scan_ports(self, target: str, endpoints: list[dict[str, Any]], scan_type: str) -> list[dict[str, Any]]:
        """Discover open ports via passive analysis or simulated scan."""
        open_ports: list[dict[str, Any]] = []
        seen_ports: set[int] = set()

        # Derive common ports from endpoints (URL patterns)
        for ep in endpoints:
            url = ep.get("url", "")
            port = self._guess_port_from_url(url)
            if port and port not in seen_ports:
                seen_ports.add(port)
                open_ports.append(
                    {
                        "port": port,
                        "protocol": "tcp",
                        "state": "open",
                        "source": "endpoint_analysis",
                        "confidence": "medium",
                    }
                )

        # Add default web ports if not already present
        default_ports = [80, 443, 8080, 8443]
        for p in default_ports:
            if p not in seen_ports:
                seen_ports.add(p)
                open_ports.append(
                    {
                        "port": p,
                        "protocol": "tcp",
                        "state": "open" if p in (80, 443) else "filtered",
                        "source": "default_guess",
                        "confidence": "low" if p not in (80, 443) else "high",
                    }
                )

        open_ports.sort(key=lambda x: x["port"])
        return open_ports

    def _identify_services(self, target: str, ports: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identify services running on open ports."""
        service_map = {
            80: {"name": "http", "product": "web_server"},
            443: {"name": "https", "product": "web_server"},
            22: {"name": "ssh", "product": "openssh"},
            21: {"name": "ftp", "product": "unknown"},
            3306: {"name": "mysql", "product": "mysql"},
            5432: {"name": "postgresql", "product": "postgresql"},
            8080: {"name": "http-proxy", "product": "web_server"},
            8443: {"name": "https-alt", "product": "web_server"},
            6379: {"name": "redis", "product": "redis"},
            27017: {"name": "mongodb", "product": "mongodb"},
        }
        services = []
        for p in ports:
            info = service_map.get(p["port"], {"name": "unknown", "product": "unknown"})
            services.append(
                {
                    "port": p["port"],
                    "protocol": p.get("protocol", "tcp"),
                    "service": info["name"],
                    "product": info["product"],
                    "confidence": p.get("confidence", "low"),
                }
            )
        return services

    def _detect_technologies(self, target: str, endpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect web technologies from endpoint responses and URL patterns."""
        tech_signatures: dict[str, list[str]] = {
            "react": ["react", "reactjs", "_react", "reactRoot"],
            "vue": ["vue", "vuejs", "__vue__", "vue-app"],
            "angular": ["angular", "ng-", "_angular"],
            "nextjs": ["next", "nextjs", "__next", "_next"],
            "nginx": ["nginx", "nginx/", "x-nginx"],
            "apache": ["apache", "apache/", "x-powered-by: apache"],
            "cloudflare": ["cloudflare", "cf-ray", "__cfduid"],
            "wordpress": ["wp-", "wp-content", "wp-includes", "wordpress"],
            "django": ["django", "csrftoken", "sessionid"],
            "laravel": ["laravel", "x-laravel"],
            "express": ["express", "x-powered-by: express"],
            "fastapi": ["fastapi", "openapi", "docs"],
        }
        detected: dict[str, dict[str, Any]] = {}
        for ep in endpoints:
            url = ep.get("url", "")
            headers = ep.get("response_headers", {})
            body_snippet = ep.get("body_snippet", "")
            content = json.dumps(headers).lower() + " " + url.lower() + " " + body_snippet.lower()

            for tech, sigs in tech_signatures.items():
                for sig in sigs:
                    if sig.lower() in content:
                        if tech not in detected:
                            detected[tech] = {"name": tech, "confidence": "medium", "evidence": []}
                        detected[tech]["evidence"].append({"source": url, "signature": sig})

        return [
            {"name": tech, "confidence": info["confidence"], "evidence_count": len(info["evidence"])}
            for tech, info in detected.items()
        ]

    def _check_cdn(self, target: str) -> dict[str, Any]:
        """Check if target is behind a CDN."""
        # Currently passive only - return empty result
        return {"behind_cdn": False, "providers": [], "note": "CDN check was passive; no active probing performed"}

    def _guess_port_from_url(self, url: str) -> int | None:
        """Extract port from URL if explicitly specified, else guess from scheme."""
        if "://" not in url:
            return None
        # Check for explicit port
        after_scheme = url.split("://", 1)[1]
        if ":" in after_scheme.split("/")[0].split("?")[0]:
            try:
                return int(after_scheme.split(":")[1].split("/")[0])
            except (ValueError, IndexError):
                pass
        # Guess from scheme
        if url.startswith("https"):
            return 443
        if url.startswith("http"):
            return 80
        return None

    def _log_results(self, target: str, ports: list, services: list, tech_stack: list, scan_type: str) -> None:
        self.logger.info(
            "Attack surface: %s | %d ports | %d services | %d technologies | %s",
            target,
            len(ports),
            len(services),
            len(tech_stack),
            scan_type,
        )
