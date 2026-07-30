"""Naabu wrapper — fast port scanning from ProjectDiscovery."""

from __future__ import annotations

import json
import logging

from cores.tools.base import BaseTool, UnifiedResult

logger = logging.getLogger("ownex.tools.naabu")


class NaabuTool(BaseTool):
    name = "naabu"
    install_hint = "go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"
    min_version = "2.0.0"

    PORT_SEVERITY_MAP: dict[str, str] = {
        "21": "medium",
        "22": "low",
        "23": "medium",
        "25": "medium",
        "53": "low",
        "80": "info",
        "443": "info",
        "445": "high",
        "8080": "medium",
        "8443": "medium",
        "1433": "high",
        "1521": "high",
        "3306": "high",
        "3389": "high",
        "5432": "high",
        "27017": "high",
        "6379": "high",
        "9200": "medium",
    }

    def scan(
        self,
        host: str,
        ports: str = "top-1000",
        rate: int = 1000,
        timeout: int = 300,
        service_detect: bool = True,
        exclude_cdn: bool = True,
    ) -> list[UnifiedResult]:
        """Run naabu port scan against a single host."""
        args = ["-host", host, "-json"]
        if ports:
            args.extend(["-p", ports])
        args.extend(["-rate", str(rate)])
        if service_detect:
            args.append("-s")
        if exclude_cdn:
            args.append("-exclude-cdn")
        result = self.run(args, timeout=timeout)
        if result.success:
            return self._parse_json_lines(result.stdout)
        logger.warning("naabu scan failed for %s: %s", host, result.error[:200])
        return []

    def scan_multi(
        self,
        hosts: list[str],
        ports: str = "top-1000",
        rate: int = 1000,
        timeout: int = 600,
    ) -> list[UnifiedResult]:
        """Run naabu against multiple hosts using a temp file."""
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp(prefix="naabu_"))
        try:
            host_file = tmp / "hosts.txt"
            host_file.write_text("\n".join(hosts))
            args = ["-l", str(host_file), "-json", "-p", ports, "-rate", str(rate), "-s"]
            result = self.run(args, timeout=timeout)
            if result.success:
                return self._parse_json_lines(result.stdout)
            logger.warning("naabu multi-scan failed: %s", result.error[:200])
            return []
        finally:
            import shutil

            shutil.rmtree(tmp, ignore_errors=True)

    def _parse_json_lines(self, stdout: str) -> list[UnifiedResult]:
        results = []
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            host = data.get("host", data.get("ip", ""))
            port = str(data.get("port", ""))
            protocol = data.get("protocol", "tcp")
            service = data.get("service", "")
            title = data.get("title", "")

            severity = self.PORT_SEVERITY_MAP.get(port, "info")
            name_parts = [f"Port {port}/{protocol}"]
            if service:
                name_parts.append(f"({service})")
            if title:
                name_parts.append(f" - {title}")

            results.append(
                UnifiedResult(
                    source="naabu",
                    target=host,
                    result_type="open_port",
                    severity=severity,
                    confidence=0.9,
                    name=" ".join(name_parts),
                    description=f"Open port {port}/{protocol}{' running ' + service if service else ''}",
                    evidence={
                        "port": port,
                        "protocol": protocol,
                        "service": service,
                        "title": title,
                        "ip": host,
                    },
                    tags=["port", protocol, service] if service else ["port", protocol],
                    raw=line,
                )
            )
        return results

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_json_lines(stdout)
