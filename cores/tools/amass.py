"""Amass wrapper — network mapping and subdomain discovery."""

from __future__ import annotations

import json
import logging

from cores.tools.base import BaseTool, UnifiedResult

logger = logging.getLogger("cateye.tools.amass")


class AmassTool(BaseTool):
    name = "amass"
    install_hint = "go install -v github.com/owasp-amass/amass/v4/...@master"
    min_version = "4.0.0"

    def enumerate(
        self,
        domain: str,
        mode: str = "passive",
        timeout: int = 600,
    ) -> list[UnifiedResult]:
        """Run amass enumeration against a domain."""
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp(prefix="amass_"))
        output_file = tmp / "output.json"
        try:
            args = ["enum", "-d", domain, "-json", str(output_file), "-nocolor"]
            if mode == "passive":
                args.append("-passive")
            elif mode == "active":
                args.extend(["-active", "-brute"])

            result = self.run(args, timeout=timeout)
            parsed = []
            if output_file.exists():
                parsed = self._parse_json_file(str(output_file))
            elif result.success:
                parsed = self._parse_json_lines(result.stdout)
            else:
                logger.warning("amass enum failed for %s: %s", domain, result.error[:200])
            return parsed
        finally:
            import shutil

            shutil.rmtree(tmp, ignore_errors=True)

    def intel(
        self,
        domain: str,
        timeout: int = 300,
    ) -> list[UnifiedResult]:
        """Amass intel — collect open data about a domain."""
        args = ["intel", "-whois", "-d", domain, "-json"]
        result = self.run(args, timeout=timeout)
        if result.success:
            return self._parse_json_lines(result.stdout)
        logger.warning("amass intel failed for %s: %s", domain, result.error[:200])
        return []

    def _parse_json_file(self, path: str) -> list[UnifiedResult]:
        from pathlib import Path

        p = Path(path)
        if not p.exists():
            return []
        return self._parse_json_lines(p.read_text(encoding="utf-8", errors="ignore"))

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

            name = data.get("name", "")
            domain = data.get("domain", "")
            addresses = data.get("addresses", [])
            ips = [a.get("ip", "") for a in addresses if a.get("ip")]

            event_type = data.get("event_type", "")
            if event_type == "synced":
                continue

            result_type = "subdomain"
            if event_type == "cert":
                result_type = "certificate"
            elif addresses:
                result_type = "resolved_subdomain"

            results.append(
                UnifiedResult(
                    source="amass",
                    target=name or domain,
                    result_type=result_type,
                    severity="info",
                    confidence=0.8,
                    name=f"Subdomain: {name}" if name else f"Intel: {domain}",
                    description=f"Discovered {name or domain}{' (' + ', '.join(ips) + ')' if ips else ''}",
                    evidence={
                        "domain": domain,
                        "name": name,
                        "addresses": addresses,
                        "event_type": event_type,
                        "tag": data.get("tag", ""),
                    },
                    tags=["subdomain", result_type, domain],
                    raw=line,
                )
            )
        return results

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_json_lines(stdout)
