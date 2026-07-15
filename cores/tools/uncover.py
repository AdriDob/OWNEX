"""UncoverTool — multi-engine search via ProjectDiscovery uncover.

Queries Shodan, Censys, Fofa, Shodan InternetDB, and other search engines
via the `uncover` CLI tool. Returns JSON lines with IP, port, host, and metadata.
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

from cores.tools.base import BaseTool, UnifiedResult

logger = logging.getLogger("cateye.tools.uncover")

DEFAULT_ENGINES = ["shodan", "censys", "fofa"]
ALL_ENGINES = ["shodan", "shodan-idb", "censys", "fofa", "zoomeye", "hunter"]

_TIMEOUT_SEC = 120


class UncoverTool(BaseTool):
    """Multi-engine search via ProjectDiscovery uncover.

    Requires `uncover` installed and API keys configured via env vars
    (e.g. SHODAN_API_KEY, CENSYS_API_KEY, FOFA_EMAIL, etc.).
    """

    name = "uncover"
    install_hint = "go install -v github.com/projectdiscovery/uncover/cmd/uncover@latest"
    min_version = "0.1.0"

    def search(self, query: str, engines: list[str] | None = None, limit: int = 100) -> list[UnifiedResult]:
        """Search across multiple external intelligence engines."""
        selected = (engines or DEFAULT_ENGINES)[:5]
        engines_flag = ",".join(selected)

        with tempfile.TemporaryDirectory(prefix="uncover_") as tmpdir:
            output_file = Path(tmpdir) / "uncover.json"
            args = [
                "-q",
                query,
                "-e",
                engines_flag,
                "-json",
                str(output_file),
                "-nc",  # no color
                "-limit",
                str(limit),
            ]
            result = self.run(args, timeout=_TIMEOUT_SEC)
            if not result.success:
                logger.warning("uncover search failed for %s: %s", query, result.error[:200])
            raw = output_file.read_text(encoding="utf-8", errors="ignore") if output_file.exists() else result.stdout
            return self._parse_output(raw, query)

    def search_ip(self, ip: str, limit: int = 50) -> list[UnifiedResult]:
        """Search for IP in all available engines."""
        return self.search(f"ip={ip}", engines=ALL_ENGINES[:4], limit=limit)

    def search_domain(self, domain: str, limit: int = 100) -> list[UnifiedResult]:
        """Search for a domain across all engines."""
        return self.search(f"hostname={domain}", limit=limit)

    def _parse_output(self, stdout: str, query: str) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        seen: set[str] = set()
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            ip = data.get("ip", "") or data.get("host", "")
            port = data.get("port", 0)
            host = data.get("host", ip)
            engine = data.get("source", "uncover")
            unique_key = f"{engine}:{ip}:{port}"
            if unique_key in seen:
                continue
            seen.add(unique_key)

            results.append(
                UnifiedResult(
                    source=engine or "uncover",
                    target=ip or query,
                    result_type="exposed_service",
                    severity=self._port_severity(int(port)) if port else "info",
                    confidence=0.75,
                    name=f"{engine}: {ip}:{port}" if port else f"{engine}: {ip}",
                    description=f"Discovered via {engine}{' on port ' + str(port) if port else ''}",
                    evidence={
                        "ip": ip,
                        "port": port,
                        "host": host,
                        "engine": engine,
                        "query": query,
                    },
                    tags=[engine, "exposed", f"port:{port}"] if port else [engine, "discovered"],
                )
            )
        if not results:
            logger.debug("uncover: no results for %s", query)
        return results

    @staticmethod
    def _port_severity(port: int) -> str:
        if port in (21, 22, 23, 3389, 5900, 6379, 27017, 9200):
            return "medium"
        return "info"

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_output(stdout, "")
