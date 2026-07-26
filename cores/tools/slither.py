from __future__ import annotations

import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

from cores.tools.base import BaseTool, ToolResult, UnifiedResult

logger = logging.getLogger("cateye.tools.slither")

SLITHER_DETECTOR_MAP: dict[str, dict[str, str]] = {
    "reentrancy-eth": {"vuln_type": "reentrancy", "severity": "high"},
    "reentrancy-no-eth": {"vuln_type": "reentrancy", "severity": "medium"},
    "reentrancy-unlimited-gas": {"vuln_type": "reentrancy", "severity": "medium"},
    "unused-return": {"vuln_type": "unused_return", "severity": "medium"},
    "tx-origin": {"vuln_type": "access_control", "severity": "medium"},
    "timestamp": {"vuln_type": "timestamp_dependency", "severity": "low"},
    "block-timestamp": {"vuln_type": "timestamp_dependency", "severity": "low"},
    "controlled-delegatecall": {"vuln_type": "access_control", "severity": "high"},
    "suicidal": {"vuln_type": "access_control", "severity": "high"},
    "incorrect-equality": {"vuln_type": "precision_loss", "severity": "medium"},
    "locked-ether": {"vuln_type": "locked_funds", "severity": "medium"},
    "arbitrary-send": {"vuln_type": "access_control", "severity": "high"},
    "low-level-calls": {"vuln_type": "low_level_call", "severity": "medium"},
    "controlled-array-length": {"vuln_type": "access_control", "severity": "high"},
    "delegatecall-loop": {"vuln_type": "access_control", "severity": "high"},
    "uninitialized-state": {"vuln_type": "initialization", "severity": "medium"},
    "uninitialized-storage": {"vuln_type": "initialization", "severity": "high"},
    "shadowing-state": {"vuln_type": "code_quality", "severity": "low"},
    "shadowing-abstract": {"vuln_type": "code_quality", "severity": "low"},
    "naming-convention": {"vuln_type": "code_quality", "severity": "info"},
    "similar-names": {"vuln_type": "code_quality", "severity": "info"},
    "constant-function": {"vuln_type": "code_quality", "severity": "info"},
    "calls-loop": {"vuln_type": "gas", "severity": "low"},
    "expensive-operation": {"vuln_type": "gas", "severity": "low"},
    "public-mint": {"vuln_type": "access_control", "severity": "medium"},
    "unused-state": {"vuln_type": "code_quality", "severity": "info"},
    "assembly": {"vuln_type": "low_level_call", "severity": "low"},
    "divide-before-multiply": {"vuln_type": "precision_loss", "severity": "medium"},
    "cyclomatic-complexity": {"vuln_type": "code_quality", "severity": "info"},
}


class SlitherTool(BaseTool):
    """Static analysis for Solidity smart contracts via Slither.

    Runs `slither` CLI on Solidity source files and parses the JSON
    output into structured UnifiedResult objects. Supports 30+ built-in
    detectors covering reentrancy, access control, timestamp dependency,
    low-level calls, gas issues, and code quality.
    """

    name = "slither"
    install_hint = "pip install slither-analyzer"
    min_version = "0.10.0"

    def __init__(self, binary_path: str | None = None):
        super().__init__(binary_path or "slither")
        self._use_python_module = False
        self._venv_python = sys.executable

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                [self._binary, "--version"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        # Try current venv Python first (sys.executable from __init__)
        for py in [self._venv_python, "python3", "python"]:
            try:
                result = subprocess.run(
                    [py, "-m", "slither", "--version"],
                    capture_output=True,
                    timeout=15,
                )
                if result.returncode == 0:
                    self._use_python_module = True
                    self._binary = py
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return False

    def run(
        self,
        args: list[str],
        timeout: int = 120,
        input_data: str | None = None,
    ) -> ToolResult:
        if self._use_python_module:
            args = ["-m", "slither"] + args
        return super().run(args, timeout=timeout, input_data=input_data)

    def scan_source(
        self,
        source_path: str | Path,
        contract_name: str = "",
        timeout: int = 120,
    ) -> list[UnifiedResult]:
        """Run Slither on a Solidity source file and parse findings."""
        args = [
            str(source_path),
            "--json",
            "-",
            "--exclude-dependencies",
        ]
        result = self.run(args, timeout=timeout)
        if not result.success:
            logger.warning("Slither scan failed for %s: %s", source_path, result.error)
            return []
        return self._parse_output(result.stdout)

    def scan_source_code(
        self,
        source_code: str,
        contract_name: str = "contract.sol",
        timeout: int = 120,
    ) -> list[UnifiedResult]:
        """Write source code to a temp file and scan it with Slither."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".sol",
            delete=False,
        ) as f:
            f.write(source_code)
            tmp_path = f.name
        try:
            return self.scan_source(tmp_path, timeout=timeout)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _parse_output(self, stdout: str) -> list[UnifiedResult]:
        results: list[UnifiedResult] = []
        if not stdout.strip():
            return results
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            logger.warning("Slither output is not valid JSON: %.200s", stdout)
            return results

        if not data.get("success"):
            logger.warning("Slither analysis did not complete successfully")
            return results

        detectors = data.get("results", {}).get("detectors", [])
        for detector in detectors:
            check = detector.get("check", "unknown")
            impact = detector.get("impact", "Medium")
            confidence = detector.get("confidence", "Medium")
            description = detector.get("description", "")
            elements = detector.get("elements", [])

            sev_map = {"High": "high", "Medium": "medium", "Low": "low", "Informational": "info"}
            severity = sev_map.get(impact, "medium")
            conf_map = {"High": 0.9, "Medium": 0.7, "Low": 0.4}
            conf_value = conf_map.get(confidence, 0.5)

            detector_info = SLITHER_DETECTOR_MAP.get(check, {})
            vuln_type: str = detector_info.get("vuln_type") or check.replace("-", "_")

            if detector_info.get("severity") and severity == "medium":
                severity = detector_info["severity"]

            evidence = {
                "detector": check,
                "impact": impact,
                "confidence": confidence,
                "description": description,
                "elements": [
                    {"source_mapping": e.get("source_mapping", {}), "type": e.get("type", "")} for e in elements
                ],
            }

            target = ""
            if elements:
                first = elements[0]
                target = first.get("name", first.get("type", ""))
                if not target:
                    sm = first.get("source_mapping", {})
                    target = sm.get("filename_relative", "")

            results.append(
                UnifiedResult(
                    source="slither",
                    target=target,
                    result_type=vuln_type,
                    severity=severity,
                    confidence=conf_value,
                    name=f"{check}: {description[:120]}",
                    description=description,
                    evidence=evidence,
                    tags=["solidity", "static_analysis", "slither", check],
                )
            )
        return results

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        return self._parse_output(stdout)
