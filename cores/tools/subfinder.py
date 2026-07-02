"""Subfinder wrapper — subdomain enumeration."""
import logging
import re

from cores.tools.base import BaseTool, UnifiedResult

logger = logging.getLogger("rastro.tools.subfinder")


class SubfinderTool(BaseTool):
    name = "subfinder"
    install_hint = "go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
    min_version = "2.6.0"

    def enumerate(
        self,
        domain: str,
        recursive: bool = False,
        silent: bool = True,
        timeout: int = 180,
    ) -> list[UnifiedResult]:
        args = ["-d", domain, "-oJ"]
        if recursive:
            args.append("-recursive")
        if silent:
            args.append("-silent")
        result = self.run(args, timeout=timeout)
        if result.success:
            return self._parse_json_lines(result.stdout)
        logger.warning("subfinder failed for %s: %s", domain, result.error)
        return []

    def _parse_json_lines(self, stdout: str) -> list[UnifiedResult]:
        results = []
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                import json
                data = json.loads(line)
                host = data.get("host", "")
                if host:
                    results.append(UnifiedResult(
                        source="subfinder",
                        target=host,
                        result_type="subdomain",
                        confidence=0.8,
                        name=f"Subdomain: {host}",
                        evidence={"source": data.get("source", ""), "input": data.get("input", "")},
                        tags=[data.get("source", "unknown")],
                    ))
            except json.JSONDecodeError:
                host = line.strip()
                if host and not host.startswith("[") and re.match(r"^[\w.-]+$", host):
                    results.append(UnifiedResult(
                        source="subfinder",
                        target=host,
                        result_type="subdomain",
                        confidence=0.6,
                        name=f"Subdomain: {host}",
                    ))
        return results

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_json_lines(stdout)
