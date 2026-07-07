from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .base import BaseTool, UnifiedResult
from .httpx import HttpxTool
from .nuclei import NucleiTool
from .subfinder import SubfinderTool

try:
    from cores.execution.mutation_engine import SmartMutationEngine
    HAS_MUTATION_ENGINE = True
except ImportError:
    HAS_MUTATION_ENGINE = False
    SmartMutationEngine = None  # type: ignore

logger = logging.getLogger("cateye.tools.extra")

DEFAULT_SECLISTS_PATH = os.environ.get("SECLISTS_PATH", "/usr/share/seclists")
DEFAULT_FFUF_PROFILES = {
    "fast": {
        "wordlist": "Discovery/Web-Content/common.txt",
        "extensions": [],
        "max_time": 60,
    },
    "balanced": {
        "wordlist": "Discovery/Web-Content/raft-large-directories.txt",
        "extensions": ["php", "asp", "aspx", "jsp", "txt", "bak", "zip", "tar.gz"],
        "max_time": 180,
    },
    "api": {
        "wordlist": "Discovery/Web-Content/api/actions-lowercase.txt",
        "extensions": ["json", "xml", "yaml", "yml", "proto"],
        "max_time": 120,
    },
}


class KatanaTool(BaseTool):
    name = "katana"
    install_hint = "go install -v github.com/projectdiscovery/katana/cmd/katana@latest"
    min_version = "0.12.0"

    def crawl(self, domain: str, timeout: int = 300) -> list[UnifiedResult]:
        with tempfile.TemporaryDirectory(prefix="katana_") as tmpdir:
            output_file = Path(tmpdir) / "katana.jsonl"
            result = self.run(
                ["-u", domain, "-jsonl", "-o", str(output_file)],
                timeout=timeout,
            )
            if result.success and output_file.exists():
                return self._parse_output(output_file.read_text(encoding="utf-8", errors="ignore"))
            return self._parse_output(result.stdout)

    def _parse_output(self, stdout: str) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        for line in stdout.splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            target = data.get("url") or data.get("matched-at") or data.get("uri") or data.get("host")
            if not target:
                continue
            results.append(
                UnifiedResult(
                    source="katana",
                    target=str(target),
                    result_type="endpoint",
                    confidence=0.75,
                    name=f"Katana endpoint: {target}",
                    evidence={"tool": "katana", **data},
                    tags=["crawl", "katana"],
                )
            )
        return results

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_output(stdout)


class GauTool(BaseTool):
    name = "gau"
    install_hint = "go install -v github.com/lc/gau/v2/cmd/gau@latest"
    min_version = "1.0.0"

    def discover_urls(
        self,
        domain: str,
        max_urls: int = 5000,
        filters: list[str] | None = None,
        timeout: int = 120,
    ) -> list[UnifiedResult]:
        with tempfile.TemporaryDirectory(prefix="gau_") as tmpdir:
            output_file = Path(tmpdir) / "gau.txt"
            args = ["--o", str(output_file), "--max-urls", str(max_urls), domain]
            if filters:
                args.extend(["--filter", ",".join(filters)])
            result = self.run(args, timeout=timeout)
            if result.success and output_file.exists():
                return self._parse_output(output_file.read_text(encoding="utf-8", errors="ignore"))
            return self._parse_output(result.stdout)

    def _parse_output(self, stdout: str) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        for line in stdout.splitlines():
            url = line.strip()
            if not url or not url.startswith("http"):
                continue
            results.append(
                UnifiedResult(
                    source="gau",
                    target=url,
                    result_type="endpoint",
                    confidence=0.65,
                    name=f"Historical URL: {url}",
                    evidence={"source": "gau"},
                    tags=["historical", "gau"],
                )
            )
        return results

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_output(stdout)


class FfufTool(BaseTool):
    name = "ffuf"
    install_hint = "go install -v github.com/ffuf/ffuf@latest"
    min_version = "1.4.0"

    def discover_paths(
        self,
        target_url: str,
        profile: str = "fast",
        timeout: int = 180,
    ) -> list[UnifiedResult]:
        profile_cfg: dict[str, Any] = dict(DEFAULT_FFUF_PROFILES.get(profile, DEFAULT_FFUF_PROFILES["fast"]))
        wordlist = self._resolve_wordlist(str(profile_cfg.get("wordlist", "")))
        if not wordlist:
            logger.warning("ffuf wordlist not found for profile '%s'", profile)
            return []

        with tempfile.TemporaryDirectory(prefix="ffuf_") as tmpdir:
            output_file = Path(tmpdir) / "ffuf.json"
            cmd = [
                "-u",
                f"{target_url}/FUZZ",
                "-w",
                wordlist,
                "-of",
                "json",
                "-o",
                str(output_file),
                "-s",
            ]
            extensions = profile_cfg.get("extensions")
            if isinstance(extensions, list):
                for ext in extensions:
                    cmd.extend(["-e", f".{ext}"])
            result = self.run(cmd, timeout=timeout)
            if result.success and output_file.exists():
                return self._parse_output(output_file.read_text(encoding="utf-8", errors="ignore"))
            return self._parse_output(result.stdout)

    def _resolve_wordlist(self, relative: str) -> str | None:
        candidate = Path(DEFAULT_SECLISTS_PATH) / relative
        if candidate.exists():
            return str(candidate)
        return None

    def _parse_output(self, output: str) -> list[UnifiedResult]:
        if not output:
            return []
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, dict):
            return []
        results: list[UnifiedResult] = []
        entries = data.get("results")
        if not isinstance(entries, list):
            return []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            url = entry.get("url") or entry.get("input")
            if not isinstance(url, str) or not url:
                continue
            results.append(
                UnifiedResult(
                    source="ffuf",
                    target=url,
                    result_type="endpoint",
                    confidence=0.7,
                    name=f"Fuzz discovery: {url}",
                    evidence={
                        "status": entry.get("status"),
                        "length": entry.get("length"),
                        "words": entry.get("words"),
                    },
                    tags=["fuzz", "ffuf"],
                )
            )
        return results

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_output(stdout)


def instantiate_tool(name: str) -> BaseTool | None:
    tool_class = TOOL_REGISTRY.get(name.lower())
    if not tool_class:
        logger.warning("Tool '%s' is not registered", name)
        return None
    try:
        return tool_class()
    except Exception as exc:
        logger.warning("Failed to instantiate tool '%s': %s", name, exc)
        return None


class LinkFinderTool(BaseTool):
    name = "linkfinder"
    install_hint = "pip install LinkFinder"
    min_version = "1.0.0"

    def discover_links(self, target_url: str, timeout: int = 120) -> list[UnifiedResult]:
        result = self.run(
            ["-i", target_url, "-o", "cli"],
            timeout=timeout,
        )
        return self._parse_output(result.stdout)

    def _parse_output(self, stdout: str) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        for line in stdout.splitlines():
            link = line.strip()
            if link.startswith("http"):
                results.append(
                    UnifiedResult(
                        source="linkfinder",
                        target=link,
                        result_type="endpoint",
                        confidence=0.6,
                        name=f"JS endpoint: {link}",
                        evidence={"source": "linkfinder"},
                        tags=["js", "linkfinder"],
                    )
                )
        return results

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_output(stdout)


class DalfoxTool(BaseTool):
    name = "dalfox"
    install_hint = "go install -v github.com/hahwul/dalfox/v2@latest"
    min_version = "2.0.0"

    def scan_urls(
        self,
        urls: list[str],
        timeout: int = 600,
        deep: bool = True,
        mutation_plan: Any = None,
    ) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        for url in urls:
            args = ["-u", url, "--batch", "--json"]
            if deep:
                args.extend(["--deep", "--dom", "--mining-dict", "--follow-redirects"])
            result = self.run(args, timeout=timeout)
            if result.success:
                parsed = self._parse_output(result.stdout, url)
                # Enrich with mutation metadata
                if mutation_plan and parsed:
                    for p in parsed:
                        p.tags.append("mutated")
                        p.evidence["mutation"] = str(mutation_plan)
                results.extend(parsed)
        return results

    def scan_dom(self, url: str, timeout: int = 300) -> list[UnifiedResult]:
        """DOM-only XSS scanning via Playwright/headless.
        Dalfox supports --dom flag for DOM-based XSS analysis.
        """
        result = self.run(
            ["-u", url, "--batch", "--json", "--dom", "--deep", "--mining-dict"],
            timeout=timeout,
        )
        return self._parse_output(result.stdout, url)

    def _parse_output(self, stdout: str, url: str) -> list[UnifiedResult]:
        findings: list[UnifiedResult] = []
        for line in stdout.splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                if "XSS" in line.upper() or "vulnerable" in line.lower():
                    findings.append(
                        UnifiedResult(
                            source="dalfox",
                            target=url,
                            result_type="vulnerability",
                            severity="high",
                            confidence=0.7,
                            name=f"Dalfox XSS: {url}",
                            evidence={"raw": line},
                            tags=["xss", "dalfox"],
                        )
                    )
                continue
            if data.get("vulnerability"):
                findings.append(
                    UnifiedResult(
                        source="dalfox",
                        target=url,
                        result_type="vulnerability",
                        severity="high",
                        confidence=0.75,
                        name=data.get("vulnerability", "Dalfox finding"),
                        description=data.get("detail", ""),
                        evidence=data,
                        tags=["xss", "dalfox"],
                    )
                )
        return findings

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_output(stdout, "")


class SqlmapTool(BaseTool):
    name = "sqlmap"
    install_hint = "pip install sqlmap"
    min_version = "1.7"

    def scan_url(
        self,
        url: str,
        timeout: int = 600,
        aggressive: bool = True,
        tamper_scripts: str | None = None,
    ) -> list[UnifiedResult]:
        args = ["-u", url, "--batch"]
        if aggressive:
            tamper = tamper_scripts or "between,randomcase,space2comment"
            args.extend([
                "--level", "3", "--risk", "2",
                "--technique", "BEUSTQ",
                "--time-sec", "3",
                "--random-agent",
                "--tamper", tamper,
            ])
        else:
            args.extend(["--level", "1", "--risk", "1"])
        result = self.run(args, timeout=timeout)
        return self._parse_output(result.stdout, url)

    def scan_urls_batch(
        self,
        urls: list[str],
        timeout: int = 900,
        tamper_scripts: str | None = None,
    ) -> list[UnifiedResult]:
        if not urls:
            return []
        tamper = tamper_scripts or "between,randomcase,space2comment"
        with tempfile.TemporaryDirectory(prefix="sqlmap_") as tmpdir:
            input_file = Path(tmpdir) / "urls.txt"
            input_file.write_text("\n".join(urls))
            output_dir = Path(tmpdir) / "output"
            result = self.run([
                "-m", str(input_file),
                "--batch", "--level", "3", "--risk", "2",
                "--technique", "BEUSTQ",
                "--random-agent",
                "--tamper", tamper,
                "--output-dir", str(output_dir),
            ], timeout=timeout)
            return self._parse_output(result.stdout, urls[0] if urls else "")

    def _parse_output(self, stdout: str, url: str) -> list[UnifiedResult]:
        findings: list[UnifiedResult] = []
        if not stdout:
            return findings
        lower = stdout.lower()
        detected = False
        vuln_type = "SQL Injection"
        if re.search(r"is vulnerable", lower):
            detected = True
        if re.search(r"payload.*success", lower):
            detected = True
            vuln_type = "SQL Injection (time-based)"
        if re.search(r"blind.*sqli|time.*based|blind.*sql", lower):
            detected = True
            vuln_type = "SQL Injection (blind)"
        if re.search(r"error.*based|sql.*error|ora|mysql.*error|postgres.*error", lower):
            detected = True
            vuln_type = "SQL Injection (error-based)"
        if detected:
            findings.append(
                UnifiedResult(
                    source="sqlmap",
                    target=url,
                    result_type="vulnerability",
                    severity="high",
                    confidence=0.8,
                    name=f"{vuln_type}: {url}",
                    evidence={"raw_output": stdout[:1500]},
                    tags=["sqli", "sqlmap", vuln_type.lower().replace(" ", "_")],
                )
            )
        return findings

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_output(stdout, "")


class TruffleHogTool(BaseTool):
    name = "trufflehog"
    install_hint = "pip install truffleHog"
    min_version = "3.0"

    def scan_path(
        self,
        path: str,
        timeout: int = 240,
    ) -> list[UnifiedResult]:
        result = self.run(
            ["filesystem", "--json", path, "--no-update"],
            timeout=timeout,
        )
        return self._parse_output(result.stdout)

    def _parse_output(self, stdout: str) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        for line in stdout.splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue
            target = data.get("path") or data.get("reason") or "trufflehog"
            results.append(
                UnifiedResult(
                    source="trufflehog",
                    target=str(target),
                    result_type="secret",
                    severity="medium",
                    confidence=0.6,
                    name="TruffleHog secret finding",
                    evidence=data,
                    tags=["secrets", "trufflehog"],
                )
            )
        return results

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_output(stdout)


TOOL_REGISTRY: dict[str, type[BaseTool]] = {
    "subfinder": SubfinderTool,
    "httpx": HttpxTool,
    "nuclei": NucleiTool,
    "katana": KatanaTool,
    "gau": GauTool,
    "ffuf": FfufTool,
    "linkfinder": LinkFinderTool,
    "dalfox": DalfoxTool,
    "sqlmap": SqlmapTool,
    "trufflehog": TruffleHogTool,
}
