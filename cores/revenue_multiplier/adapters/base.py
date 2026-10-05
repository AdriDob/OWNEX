from __future__ import annotations

import abc
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from cores.revenue_multiplier.models import Finding

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

    @staticmethod
    def _clone_for_scan(url: str) -> tuple[str | None, str | None]:
        """Clona un repo GitHub a un temp para escanearlo.

        Devuelve (ruta_local, tmp_dir_para_borrar) o (None, None) si no se
        pudo clonar. Sólo github.com — es lo que genera el hunter.
        """
        import re
        import tempfile

        m = re.match(r"^https?://github\.com/([^/]+)/([^/?#]+)", url)
        if not m:
            return None, None
        owner, repo = m.group(1), m.group(2).removesuffix(".git")
        tmp = tempfile.mkdtemp(prefix="ownex-gitleaks-")
        local = str(Path(tmp) / repo)
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--quiet", f"https://github.com/{owner}/{repo}", local],
                capture_output=True,
                text=True,
                timeout=180,
                check=True,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            logger.warning("gitleaks: no se pudo clonar %s/%s (%s)", owner, repo, exc)
            shutil.rmtree(tmp, ignore_errors=True)
            return None, None
        return local, tmp

    def run(self, target: str, **kwargs: Any) -> list[Finding]:
        """Escanea secretos de un repo o path local.

         Gitleaks sólo acepta **paths locales** (`--source`), no URLs. Antes el
         hunter pasaba `repo_path=f"https://github.com/{domain}"`, que gitleaks
         no puede abrir: FileNotFoundError -> output vacío -> `except` en el
         caller lo logueaba como warning y el stage "Secret scanning" no
        (reportaba nunca. Un escáner que siempre devuelve 0 hallazgos no es un
         escáner: es ruido.

         Si `repo_path` parece una URL de GitHub, se clona primero a un temp
         (depth 1) y se escanea el clon. Sin red o sin git, se devuelve []
         con un warning explícito: menos "0 hallazgos" y más "no escaneado".
        """
        import json
        import re

        repo_path = kwargs.get("repo_path") or target
        tmp_dir: str | None = None

        if re.match(r"^https?://", str(repo_path)):
            repo_path, tmp_dir = self._clone_for_scan(str(repo_path))
            if tmp_dir is None:
                logger.warning(
                    "gitleaks: %s es una URL y no se pudo clonar; stage NO ejecutado (no '0 secretos')",
                    repo_path,
                )
                return []

        try:
            cmd = [
                self._binary,
                "detect",
                "--source",
                str(repo_path),
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
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        return findings
