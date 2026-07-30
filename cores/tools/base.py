"""Unified tool wrapper system — every tool speaks the same format.

Each tool wrapper:
1. Executes the binary
2. Parses output into UnifiedResult[]
3. Returns typed, structured data

Correlation layer later cross-references results across tools.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.tools")


@dataclass
class UnifiedResult:
    """Every tool output converges to this format."""

    source: str  # subfinder, nuclei, httpx, etc.
    target: str  # domain, URL, IP
    result_type: str  # subdomain, endpoint, vulnerability, tech, etc.
    severity: str = "info"
    confidence: float = 0.5
    name: str = ""
    description: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    raw: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class ToolResult:
    """Result from running a tool."""

    success: bool
    results: list[UnifiedResult]
    command: str
    stdout: str = ""
    stderr: str = ""
    elapsed_ms: int = 0
    error: str = ""


class BaseTool:
    """Base class for all tool wrappers.

    Subclasses define:
    - name: tool binary name
    - install_hint: how to install it
    - parse_output: convert raw output to UnifiedResult[]
    """

    name: str = ""
    install_hint: str = ""
    min_version: str = ""

    def __init__(self, binary_path: str | None = None):
        self._binary = binary_path or self.name

    def is_available(self) -> bool:
        """Check if tool is installed and in PATH."""
        try:
            subprocess.run(
                [self._binary, "--version"],
                capture_output=True,
                timeout=10,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def run(
        self,
        args: list[str],
        timeout: int = 120,
        input_data: str | None = None,
    ) -> ToolResult:
        """Execute the tool and return structured results."""
        cmd = [self._binary] + args
        start = datetime.now(UTC)
        try:
            proc = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            elapsed = int((datetime.now(UTC) - start).total_seconds() * 1000)
            if proc.returncode != 0:
                return ToolResult(
                    success=False,
                    results=[],
                    command=" ".join(cmd),
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    elapsed_ms=elapsed,
                    error=proc.stderr[:500] or f"exit code {proc.returncode}",
                )
            results = self.parse_output(proc.stdout)
            return ToolResult(
                success=True,
                results=results,
                command=" ".join(cmd),
                stdout=proc.stdout,
                elapsed_ms=elapsed,
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                results=[],
                command=" ".join(cmd),
                error=f"{self.name} not found. {self.install_hint}",
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                results=[],
                command=" ".join(cmd),
                error=f"{self.name} timed out after {timeout}s",
            )

    def parse_output(self, stdout: str) -> list[UnifiedResult]:
        """Override in subclass. Convert raw stdout to UnifiedResult[]."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} binary={self._binary}>"
