from __future__ import annotations

import abc
import logging
import subprocess
from typing import Any

from core.revenue_multiplier.models import Finding

logger = logging.getLogger("orion.revenue.adapter")


class ToolAdapter(abc.ABC):
    def __init__(self, binary: str = "") -> None:
        self._binary = binary

    @abc.abstractmethod
    def run(self, target: str, **kwargs: Any) -> list[Finding]: ...

    @property
    @abc.abstractmethod
    def name(self) -> str: ...

    def _execute(self, cmd: list[str], timeout: int = 300) -> str:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0 and result.stderr:
                logger.warning("%s stderr: %s", self.name, result.stderr[:200])
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.warning("%s timed out after %ds", self.name, timeout)
            return ""
        except FileNotFoundError:
            logger.error("%s binary not found: %s", self.name, cmd[0])
            return ""


class NucleiAdapter(ToolAdapter):
    def __init__(self, binary: str = "nuclei", templates: str = "") -> None:
        super().__init__(binary)
        self._templates = templates

    @property
    def name(self) -> str:
        return "nuclei"

    def run(self, target: str, **kwargs: Any) -> list[Finding]:
        cmd = [self._binary, "-u", target, "-json", "-silent"]
        if self._templates:
            cmd.extend(["-t", self._templates])
        if kwargs.get("severity"):
            cmd.extend(["-severity", kwargs["severity"]])
        if kwargs.get("rate_limit"):
            cmd.extend(["-rl", str(kwargs["rate_limit"])])
        if kwargs.get("tags"):
            cmd.extend(["-tags", kwargs["tags"]])

        output = self._execute(cmd, timeout=kwargs.get("timeout", 600))
        return self._parse_output(output, target)

    def _parse_output(self, output: str, target: str) -> list[Finding]:
        import json

        findings: list[Finding] = []
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                findings.append(
                    Finding(
                        title=data.get("info", {}).get("name", "Nuclei finding"),
                        description=data.get("info", {}).get("description", ""),
                        severity=data.get("info", {}).get("severity", "unknown"),
                        cvss_score=float(data.get("info", {}).get("classification", {}).get("cvss-score", 0)),
                        cwe=data.get("info", {}).get("classification", {}).get("cwe", ""),
                        tool="nuclei",
                        target=target,
                        endpoint=data.get("matched-at", ""),
                        evidence=json.dumps(data.get("extracted-results", {})),
                        confidence=0.7 if data.get("info", {}).get("severity") in ("critical", "high") else 0.5,
                        raw_output=data,
                    )
                )
            except json.JSONDecodeError:
                continue
        return findings


class KatanaAdapter(ToolAdapter):
    def __init__(self, binary: str = "katana") -> None:
        super().__init__(binary)

    @property
    def name(self) -> str:
        return "katana"

    def run(self, target: str, **kwargs: Any) -> list[Finding]:
        cmd = [self._binary, "-u", target, "-silent", "-json"]
        if kwargs.get("depth"):
            cmd.extend(["-d", str(kwargs["depth"])])
        if kwargs.get("rate_limit"):
            cmd.extend(["-rl", str(kwargs["rate_limit"])])

        output = self._execute(cmd, timeout=kwargs.get("timeout", 300))
        return [
            Finding(
                tool="katana",
                target=target,
                endpoint=line.strip(),
                title=f"Crawled: {line.strip()[:80]}",
                confidence=0.3,
            )
            for line in output.strip().split("\n")
            if line.strip()
        ]


class FfufAdapter(ToolAdapter):
    def __init__(self, binary: str = "ffuf", wordlist: str = "") -> None:
        super().__init__(binary)
        self._wordlist = wordlist or "/usr/share/wordlists/dirb/common.txt"

    @property
    def name(self) -> str:
        return "ffuf"

    def run(self, target: str, **kwargs: Any) -> list[Finding]:
        url = target.rstrip("/") + "/FUZZ"
        cmd = [self._binary, "-u", url, "-w", self._wordlist, "-json", "-silent"]
        if kwargs.get("rate_limit"):
            cmd.extend(["-rate", str(kwargs["rate_limit"])])
        if kwargs.get("extensions"):
            cmd.extend(["-e", kwargs["extensions"]])

        output = self._execute(cmd, timeout=kwargs.get("timeout", 600))
        return self._parse_output(output, target)

    def _parse_output(self, output: str, target: str) -> list[Finding]:
        import json

        findings: list[Finding] = []
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                status = data.get("status", 0)
                if status in (200, 201, 204, 301, 302, 307, 401, 403, 405):
                    findings.append(
                        Finding(
                            title=f"Endpoint: {data.get('url', '')} [{status}]",
                            description=f"Discovered via ffuf with status {status}",
                            tool="ffuf",
                            target=target,
                            endpoint=data.get("url", ""),
                            confidence=0.4,
                            raw_output=data,
                        )
                    )
            except json.JSONDecodeError:
                continue
        return findings


class SubfinderAdapter(ToolAdapter):
    def __init__(self, binary: str = "subfinder") -> None:
        super().__init__(binary)

    @property
    def name(self) -> str:
        return "subfinder"

    def run(self, target: str, **kwargs: Any) -> list[Finding]:
        cmd = [self._binary, "-d", target, "-silent"]
        output = self._execute(cmd, timeout=kwargs.get("timeout", 120))
        return [
            Finding(
                tool="subfinder",
                target=target,
                endpoint=line.strip(),
                title=f"Subdomain: {line.strip()}",
                confidence=0.6,
            )
            for line in output.strip().split("\n")
            if line.strip()
        ]


class GauAdapter(ToolAdapter):
    def __init__(self, binary: str = "gau") -> None:
        super().__init__(binary)

    @property
    def name(self) -> str:
        return "gau"

    def run(self, target: str, **kwargs: Any) -> list[Finding]:
        cmd = [self._binary, "--subs", target]
        output = self._execute(cmd, timeout=kwargs.get("timeout", 180))
        return [
            Finding(
                tool="gau",
                target=target,
                endpoint=line.strip(),
                title=f"URL: {line.strip()[:80]}",
                confidence=0.3,
            )
            for line in output.strip().split("\n")
            if line.strip()
        ]


class SqlmapAdapter(ToolAdapter):
    def __init__(self, binary: str = "sqlmap") -> None:
        super().__init__(binary)

    @property
    def name(self) -> str:
        return "sqlmap"

    def run(self, target: str, **kwargs: Any) -> list[Finding]:
        cmd = [
            self._binary,
            "-u",
            target,
            "--batch",
            "--random-agent",
            "--smart",
            "--level",
            str(kwargs.get("level", 3)),
            "--risk",
            str(kwargs.get("risk", 2)),
        ]
        if kwargs.get("data"):
            cmd.extend(["--data", kwargs["data"]])
        if kwargs.get("method"):
            cmd.extend(["--method", kwargs["method"]])

        output = self._execute(cmd, timeout=kwargs.get("timeout", 900))
        findings: list[Finding] = []
        if "identified the following injection" in output.lower():
            findings.append(
                Finding(
                    title="SQL Injection detected",
                    description="sqlmap identified an injection point",
                    severity="critical",
                    tool="sqlmap",
                    target=target,
                    endpoint=target,
                    confidence=0.8,
                    raw_output={"output_preview": output[:500]},
                )
            )
        return findings


class XSStrikeAdapter(ToolAdapter):
    def __init__(self, binary: str = "xsstrike") -> None:
        super().__init__(binary)

    @property
    def name(self) -> str:
        return "xsstrike"

    def run(self, target: str, **kwargs: Any) -> list[Finding]:
        cmd = ["python3", "-m", "xsstrike", "-u", target, "--silent"]
        if kwargs.get("params"):
            cmd.extend(["--params", kwargs["params"]])

        output = self._execute(cmd, timeout=kwargs.get("timeout", 300))
        findings: list[Finding] = []
        if "XSS found" in output:
            findings.append(
                Finding(
                    title="XSS vulnerability detected",
                    description="XSStrike confirmed a cross-site scripting vulnerability",
                    severity="high",
                    tool="xsstrike",
                    target=target,
                    endpoint=target,
                    confidence=0.7,
                    raw_output={"output_preview": output[:500]},
                )
            )
        return findings


class GitleaksAdapter(ToolAdapter):
    def __init__(self, binary: str = "gitleaks") -> None:
        super().__init__(binary)

    @property
    def name(self) -> str:
        return "gitleaks"

    def run(self, target: str, **kwargs: Any) -> list[Finding]:
        import json

        repo_path = kwargs.get("repo_path", target)
        cmd = [
            self._binary,
            "detect",
            "--source",
            repo_path,
            "--no-git",
            "--report-format",
            "json",
            "--report-path",
            "/dev/stdout",
            "-v",
        ]
        output = self._execute(cmd, timeout=kwargs.get("timeout", 120))

        findings: list[Finding] = []
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                findings.append(
                    Finding(
                        title=f"Secret leak: {data.get('Description', 'Unknown')}",
                        description=f"File: {data.get('File', '')} - {data.get('Match', '')[:200]}",
                        severity="high",
                        tool="gitleaks",
                        target=target,
                        endpoint=data.get("File", ""),
                        evidence=data.get("Secret", "")[:50],
                        confidence=0.8,
                        raw_output=data,
                    )
                )
            except json.JSONDecodeError:
                continue
        return findings
