from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .amass import AmassTool
from .base import BaseTool, ToolResult, UnifiedResult
from .censys import CensysTool
from .computer_use import ComputerUseTool
from .httpx import HttpxTool
from .naabu import NaabuTool
from .nuclei import NucleiTool
from .shodan import ShodanTool
from .slither import SlitherTool
from .subfinder import SubfinderTool
from .uncover import UncoverTool

try:
    from cores.execution.mutation_engine import SmartMutationEngine

    HAS_MUTATION_ENGINE = True
except ImportError:
    HAS_MUTATION_ENGINE = False
    SmartMutationEngine = None  # type: ignore

logger = logging.getLogger("ownex.tools.extra")

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
            args.extend(
                [
                    "--level",
                    "3",
                    "--risk",
                    "2",
                    "--technique",
                    "BEUSTQ",
                    "--time-sec",
                    "3",
                    "--random-agent",
                    "--tamper",
                    tamper,
                ]
            )
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
            result = self.run(
                [
                    "-m",
                    str(input_file),
                    "--batch",
                    "--level",
                    "3",
                    "--risk",
                    "2",
                    "--technique",
                    "BEUSTQ",
                    "--random-agent",
                    "--tamper",
                    tamper,
                    "--output-dir",
                    str(output_dir),
                ],
                timeout=timeout,
            )
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


class GitleaksTool(BaseTool):
    """Secret scanning via Gitleaks (GitLab, industry standard).

    Scans git repos or directories for hardcoded secrets, API keys,
    tokens, and credentials. 150+ patterns across all major platforms.
    """

    name = "gitleaks"
    install_hint = "go install -v github.com/gitleaks/gitleaks@latest"
    min_version = "8.0.0"

    def scan_path(
        self,
        path: str | Path,
        report_format: str = "json",
        verbose: bool = False,
        timeout: int = 240,
    ) -> list[UnifiedResult]:
        cmd = ["detect", "--source", str(path), "--report-format", report_format, "--no-git"]
        if verbose:
            cmd.append("--verbose")
        result = self.run(cmd, timeout=timeout)
        return self._parse_output(result.stdout)

    def scan_repo(
        self,
        repo_path: str | Path,
        from_commit: str | None = None,
        to_commit: str | None = None,
        timeout: int = 300,
    ) -> list[UnifiedResult]:
        cmd = ["detect", "--source", str(repo_path), "--report-format", "json"]
        if from_commit:
            cmd.extend(["--log-opts", f"--since={from_commit}"])
        if to_commit:
            cmd.extend(["--log-opts", f"--until={to_commit}"])
        result = self.run(cmd, timeout=timeout)
        return self._parse_output(result.stdout)

    def _parse_output(self, stdout: str) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        if not stdout.strip():
            return results
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return results
        if isinstance(data, dict):
            entries = data.get("Findings", [])
        elif isinstance(data, list):
            entries = data
        else:
            return results
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            file_path = entry.get("File", entry.get("file", ""))
            secret = entry.get("Secret", entry.get("secret", ""))[:100]
            description = entry.get("Description", entry.get("description", "Gitleaks finding"))
            rule = entry.get("RuleID", entry.get("rule", ""))
            severity = "high" if entry.get("Severity", "").lower() in ("high", "critical") else "medium"

            results.append(
                UnifiedResult(
                    source="gitleaks",
                    target=str(file_path),
                    result_type="secret",
                    severity=severity,
                    confidence=0.75,
                    name=f"[{rule}] {description}",
                    description=description,
                    evidence={
                        "rule": rule,
                        "file": file_path,
                        "line": entry.get("StartLine", entry.get("startLine", "")),
                        "match": (entry.get("Match", entry.get("match", "")) or "")[:200],
                        "secret": secret,
                        "commit": entry.get("Commit", entry.get("commit", "")),
                        "fingerprint": entry.get("Fingerprint", entry.get("fingerprint", "")),
                    },
                    tags=["secrets", "gitleaks", rule.lower()],
                    raw=json.dumps(entry),
                )
            )
        return results

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_output(stdout)


class GarakTool(BaseTool):
    """LLM vulnerability scanner (NVIDIA Garak).

    Probes LLMs for prompt injection, jailbreaks, data leakage,
    agent security, and other AI-specific vulnerabilities.

    Supports 50+ probes, 23 model backends, 28 detectors.
    """

    name = "garak"
    install_hint = "pip install garak"
    min_version = "0.15.0"

    def __init__(self, binary_path: str | None = None):
        super().__init__(binary_path)
        self._use_python_module = False

    def is_available(self) -> bool:
        try:
            subprocess.run(
                [self._binary, "--version"],
                capture_output=True,
                timeout=10,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        try:
            subprocess.run(
                [sys.executable, "-m", "garak", "--version"],
                capture_output=True,
                timeout=15,
            )
            self._use_python_module = True
            self._binary = sys.executable
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def run(
        self,
        args: list[str],
        timeout: int = 120,
        input_data: str | None = None,
    ) -> ToolResult:
        if self._use_python_module:
            args = ["-m", "garak"] + args
        return super().run(args, timeout=timeout, input_data=input_data)

    PROBE_TYPES = {
        "prompt_injection": ["promptinject"],
        "jailbreak": ["jailbreak"],
        "data_leakage": ["leakreplay", "leakrevival"],
        "toxicity": ["toxicity", "dan", "codinggen"],
        "encoding": ["encoding"],
    }

    def scan_model(
        self,
        model_type: str = "openai",
        model_name: str = "gpt-3.5-turbo",
        probes: list[str] | None = None,
        timeout: int = 600,
    ) -> list[UnifiedResult]:
        args = [
            "--model_type",
            model_type,
            "--model_name",
            model_name,
            "--probes",
        ]
        probe_str = ",".join(probes) if probes else "promptinject"
        args.append(probe_str)
        result = self.run(args, timeout=timeout)
        return self._parse_output(result.stdout)

    def scan_ollama(
        self,
        model_name: str = "qwen3-coder:8b",
        probes: list[str] | None = None,
        timeout: int = 600,
    ) -> list[UnifiedResult]:
        return self.scan_model(
            model_type="ollama",
            model_name=model_name,
            probes=probes or ["promptinject", "jailbreak"],
            timeout=timeout,
        )

    def scan_endpoint(
        self,
        endpoint_url: str,
        model_name: str,
        probes: list[str] | None = None,
        timeout: int = 600,
    ) -> list[UnifiedResult]:
        args = [
            "--model_type",
            "rest",
            "--model_name",
            model_name,
            f"--endpoint_uri={endpoint_url}",
            "--probes",
        ]
        probe_str = ",".join(probes) if probes else "promptinject"
        args.append(probe_str)
        result = self.run(args, timeout=timeout)
        return self._parse_output(result.stdout)

    def _parse_output(self, stdout: str) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        if not stdout.strip():
            return results
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                if "PASS" in line or "FAIL" in line or "vulnerable" in line.lower():
                    results.append(
                        UnifiedResult(
                            source="garak",
                            target="",
                            result_type="vulnerability" if "FAIL" in line or "vulnerable" in line.lower() else "info",
                            severity="high" if "FAIL" in line else "info",
                            confidence=0.6,
                            name=line[:200],
                            evidence={"raw": line},
                            tags=["llm_security", "garak"],
                        )
                    )
                continue
            probe = data.get("probe", data.get("probe_name", data.get("entry_type", "")))
            detected = data.get("result", data.get("detected", data.get("status", False)))
            if isinstance(detected, str):
                detected = detected.lower() in ("true", "yes", "fail", "vulnerable")

            severity = "high" if detected else "low"
            confidence = 0.7 if detected else 0.5

            results.append(
                UnifiedResult(
                    source="garak",
                    target=str(probe),
                    result_type="vulnerability" if detected else "llm_test",
                    severity=severity,
                    confidence=confidence,
                    name=f"Garak {probe}: {'DETECTED' if detected else 'PASS'}",
                    description=data.get("output", data.get("detail", "")),
                    evidence=data,
                    tags=["llm_security", "garak", str(probe).lower()],
                    raw=line,
                )
            )
        return results

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_output(stdout)


class BrowserUseTool(BaseTool):
    """Autonomous AI browser agent via browser-use (105k+⭐).

    NOT a subprocess binary — uses the `browser_use` Python library
    to control a browser via LLM instructions.

    Enables autonomous complex testing:
    - Auth flow navigation
    - Multi-step form submission
    - JavaScript SPA deep crawling
    - DOM interaction for complex XSS/CSRF testing
    - Screenshot and evidence capture
    """

    name = "browser_use"
    install_hint = "pip install browser-use"
    min_version = "0.1.0"

    def __init__(self, llm=None, headless: bool = True):
        self._headless = headless
        self._agent = None
        self._llm = llm

    def is_available(self) -> bool:
        try:
            import browser_use  # noqa

            return True
        except ImportError:
            return False

    def run_task(
        self,
        task: str,
        max_steps: int = 50,
        timeout: int = 300,
        llm_config: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Execute an autonomous browser task."""
        try:
            from browser_use import Agent  # type: ignore[import-untyped]
            from langchain_openai import ChatOpenAI  # type: ignore[import-untyped]
        except ImportError:
            return ToolResult(
                success=False,
                results=[],
                command=task,
                error="browser-use not installed. pip install browser-use",
            )

        llm_kwargs = llm_config or {}
        llm = self._llm or ChatOpenAI(
            model=llm_kwargs.get("model", "gpt-4"),
            temperature=0,
        )

        agent = Agent(
            task=task,
            llm=llm,
            use_vision=llm_kwargs.get("use_vision", False),
            max_actions_per_step=max_steps,
            generate_gif=llm_kwargs.get("generate_gif", False),
        )

        import asyncio

        try:
            history = asyncio.run(agent.run(max_steps=max_steps))
        except Exception as exc:
            return ToolResult(
                success=False,
                results=[],
                command=task,
                error=str(exc),
            )

        results: list[UnifiedResult] = []
        if history:
            urls_visited = list(history.urls())

            for url in urls_visited:
                results.append(
                    UnifiedResult(
                        source="browser_use",
                        target=str(url),
                        result_type="browser_action",
                        confidence=0.9,
                        name=f"Browser Use visited: {url}",
                        evidence={"task": task, "urls": urls_visited[:20]},
                        tags=["browser_use", "autonomous"],
                    )
                )

            # Extract any security-relevant findings from task output
            final_result = history.final_result() or ""
            if final_result:
                for keyword in ("token", "api_key", "password", "secret", "captcha"):
                    if keyword in final_result.lower():
                        results.append(
                            UnifiedResult(
                                source="browser_use",
                                target=task[:200],
                                result_type="finding",
                                severity="medium",
                                confidence=0.6,
                                name=f"Sensitive data in browser output: {keyword}",
                                description=final_result[:500],
                                evidence={"task": task, "output": final_result[:1000]},
                                tags=["browser_use", keyword],
                            )
                        )

        return ToolResult(
            success=True,
            results=results,
            command=task,
        )

    def run(self, args: list[str], timeout: int = 300, input_data: str | None = None) -> ToolResult:
        return self.run_task(
            task=input_data or " ".join(args),
            timeout=timeout,
        )

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return []


TOOL_REGISTRY: dict[str, type[BaseTool]] = {
    "amass": AmassTool,
    "shodan": ShodanTool,
    "subfinder": SubfinderTool,
    "uncover": UncoverTool,
    "httpx": HttpxTool,
    "naabu": NaabuTool,
    "nuclei": NucleiTool,
    "katana": KatanaTool,
    "gau": GauTool,
    "ffuf": FfufTool,
    "linkfinder": LinkFinderTool,
    "dalfox": DalfoxTool,
    "sqlmap": SqlmapTool,
    "trufflehog": TruffleHogTool,
    "gitleaks": GitleaksTool,
    "garak": GarakTool,
    "browser_use": BrowserUseTool,
    "computer_use": ComputerUseTool,
    "censys": CensysTool,
    "slither": SlitherTool,
}
