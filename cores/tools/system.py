"""
OWNEX Tool System — Manager, installation, detection, status, compatibility.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.tools")


class ToolStatus(StrEnum):
    AVAILABLE = "available"
    NOT_INSTALLED = "not_installed"
    OUTDATED = "outdated"
    ERROR = "error"
    UNKNOWN = "unknown"


class ToolCategory(StrEnum):
    CLI = "cli"
    PYTHON = "python"
    NODE = "node"
    DOCKER = "docker"
    BINARY = "binary"
    API = "api"
    AI = "ai"


@dataclass
class ToolSpec:
    """Tool specification."""

    name: str
    category: ToolCategory
    description: str
    install_command: str | None = None
    check_command: str | None = None
    version_flag: str = "--version"
    required: bool = False
    dependencies: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolStatusInfo:
    """Tool status information."""

    name: str
    status: ToolStatus
    version: str | None = None
    path: str | None = None
    last_checked: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolManager:
    """Manages tool detection, installation, and status."""

    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}
        self._status_cache: dict[str, ToolStatusInfo] = {}
        self._register_core_tools()

    def _register_core_tools(self) -> None:
        """Register core OWNEX tools."""
        core_tools = [
            ToolSpec(
                name="python",
                category=ToolCategory.CLI,
                description="Python interpreter",
                check_command="python --version",
                required=True,
            ),
            ToolSpec(
                name="pip",
                category=ToolCategory.CLI,
                description="Python package manager",
                check_command="pip --version",
                required=True,
            ),
            ToolSpec(
                name="node",
                category=ToolCategory.CLI,
                description="Node.js runtime",
                check_command="node --version",
                required=False,
            ),
            ToolSpec(
                name="npm",
                category=ToolCategory.CLI,
                description="Node package manager",
                check_command="npm --version",
                required=False,
            ),
            ToolSpec(
                name="docker",
                category=ToolCategory.DOCKER,
                description="Docker container runtime",
                check_command="docker --version",
                required=False,
            ),
            ToolSpec(
                name="git",
                category=ToolCategory.CLI,
                description="Git version control",
                check_command="git --version",
                required=True,
            ),
            ToolSpec(
                name="curl",
                category=ToolCategory.CLI,
                description="HTTP client",
                check_command="curl --version",
                required=False,
            ),
            ToolSpec(
                name="sqlite3",
                category=ToolCategory.CLI,
                description="SQLite database CLI",
                check_command="sqlite3 --version",
                required=False,
            ),
            ToolSpec(
                name="burpsuite",
                category=ToolCategory.BINARY,
                description="Burp Suite Pro (security testing)",
                check_command="burpsuite --version",
                required=False,
                alternatives=["owasp-zap"],
            ),
            ToolSpec(
                name="owasp-zap",
                category=ToolCategory.BINARY,
                description="OWASP ZAP (security scanning)",
                check_command="zap.sh -version",
                required=False,
            ),
            ToolSpec(
                name="nmap",
                category=ToolCategory.CLI,
                description="Network mapper",
                check_command="nmap --version",
                required=False,
            ),
            ToolSpec(
                name="sqlmap",
                category=ToolCategory.PYTHON,
                description="SQL injection tool",
                check_command="sqlmap --version",
                required=False,
            ),
            ToolSpec(
                name="ffuf",
                category=ToolCategory.BINARY,
                description="Fast web fuzzer",
                check_command="ffuf -V",
                required=False,
            ),
            ToolSpec(
                name="subfinder",
                category=ToolCategory.BINARY,
                description="Subdomain discovery",
                check_command="subfinder -version",
                required=False,
            ),
            ToolSpec(
                name="httpx",
                category=ToolCategory.BINARY,
                description="Fast HTTP probe",
                check_command="httpx -version",
                required=False,
            ),
            ToolSpec(
                name="nuclei",
                category=ToolCategory.BINARY,
                description="Vulnerability scanner",
                check_command="nuclei -version",
                required=False,
            ),
            ToolSpec(
                name="golang",
                category=ToolCategory.CLI,
                description="Go programming language",
                check_command="go version",
                required=False,
            ),
        ]

        for tool in core_tools:
            self.register(tool)

    def register(self, spec: ToolSpec) -> None:
        """Register a tool specification."""
        self._tools[spec.name] = spec

    def get_spec(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def list_tools(self, category: ToolCategory | None = None) -> list[ToolSpec]:
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    async def check_tool(self, name: str, force: bool = False) -> ToolStatusInfo:
        """Check tool availability and version."""
        if not force and name in self._status_cache:
            cached = self._status_cache[name]
            if (datetime.now(UTC) - cached.last_checked).total_seconds() < 3600:
                return cached

        spec = self._tools.get(name)
        if not spec:
            return ToolStatusInfo(name=name, status=ToolStatus.UNKNOWN, error="Tool not registered")

        try:
            # Check if executable exists
            path = shutil.which(name)
            if not path:
                # Try check_command if specified
                if spec.check_command:
                    result = await self._run_command(spec.check_command)
                    if result.returncode == 0:
                        version = self._extract_version(result.stdout, spec.version_flag)
                        status = ToolStatus.AVAILABLE
                    else:
                        status = ToolStatus.NOT_INSTALLED
                        version = None
                else:
                    status = ToolStatus.NOT_INSTALLED
                    version = None
            else:
                # Get version
                result = await self._run_command(f"{name} {spec.version_flag}")
                if result.returncode == 0:
                    version = self._extract_version(result.stdout, spec.version_flag)
                    status = ToolStatus.AVAILABLE
                else:
                    status = ToolStatus.ERROR
                    version = None

            info = ToolStatusInfo(
                name=name,
                status=status,
                version=version,
                path=path,
                last_checked=datetime.now(UTC),
            )

        except Exception as e:
            info = ToolStatusInfo(
                name=name,
                status=ToolStatus.ERROR,
                error=str(e),
                last_checked=datetime.now(UTC),
            )

        self._status_cache[name] = info
        return info

    async def _run_command(self, command: str) -> subprocess.CompletedProcess:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=10,
            ),
        )

    def _extract_version(self, output: str, version_flag: str) -> str:
        lines = output.strip().split("\n")
        for line in lines:
            if any(c.isdigit() for c in line):
                return line.strip()
        return "unknown"

    async def check_all(self, category: ToolCategory | None = None) -> dict[str, ToolStatusInfo]:
        """Check all registered tools."""
        tools = self.list_tools(category)
        results = {}
        for tool in tools:
            results[tool.name] = await self.check_tool(tool.name)
        return results

    async def install_tool(self, name: str) -> bool:
        """Install a tool using its install command."""
        spec = self._tools.get(name)
        if not spec or not spec.install_command:
            logger.error("No install command for %s", name)
            return False

        logger.info("Installing %s...", name)
        try:
            result = await self._run_command(spec.install_command)
            if result.returncode == 0:
                # Re-check after install
                await self.check_tool(name, force=True)
                logger.info("Successfully installed %s", name)
                return True
            else:
                logger.error("Failed to install %s: %s", name, result.stderr)
                return False
        except Exception as e:
            logger.error("Error installing %s: %s", name, e)
            return False

    def get_compatibility_report(self) -> dict[str, Any]:
        """Generate compatibility report."""
        report = {
            "total_tools": len(self._tools),
            "by_category": {},
            "required": [],
            "optional": [],
            "missing_required": [],
            "missing_optional": [],
        }

        for tool in self._tools.values():
            cat = tool.category.value
            report["by_category"][cat] = report["by_category"].get(cat, 0) + 1

            if tool.required:
                report["required"].append(tool.name)
            else:
                report["optional"].append(tool.name)

        return report


class ToolCompatibilityChecker:
    """Checks tool compatibility and version requirements."""

    def __init__(self, manager: ToolManager):
        self.manager = manager
        self._version_requirements: dict[str, str] = {
            "python": ">=3.11",
            "node": ">=18",
            "npm": ">=9",
            "docker": ">=24",
            "git": ">=2.30",
        }

    def check_version(self, tool_name: str, current_version: str) -> bool:
        """Check if version meets requirements."""
        req = self._version_requirements.get(tool_name)
        if not req:
            return True

        # Simple version comparison (can be enhanced with packaging.version)
        try:
            if req.startswith(">="):
                min_ver = req[2:]
                return self._compare_versions(current_version, min_ver) >= 0
        except Exception:
            pass
        return True

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare version strings. Returns 1 if v1 > v2, 0 if equal, -1 if v1 < v2."""
        # Extract numbers from version strings
        import re

        nums1 = [int(x) for x in re.findall(r"\d+", v1)]
        nums2 = [int(x) for x in re.findall(r"\d+", v2)]

        for n1, n2 in zip(nums1, nums2):
            if n1 > n2:
                return 1
            elif n1 < n2:
                return -1

        if len(nums1) > len(nums2):
            return 1
        elif len(nums1) < len(nums2):
            return -1
        return 0

    async def full_compatibility_check(self) -> dict[str, Any]:
        """Run full compatibility check."""
        results = {
            "compatible": True,
            "issues": [],
            "warnings": [],
            "tool_status": {},
        }

        for name, spec in self.manager._tools.items():
            status = await self.manager.check_tool(name)
            results["tool_status"][name] = {
                "status": status.status.value,
                "version": status.version,
                "required": spec.required,
            }

            if (
                status.status == ToolStatus.AVAILABLE
                and status.version
                and not self.check_version(name, status.version)
            ):
                results["warnings"].append(f"{name} version {status.version} may be outdated")

            if spec.required and status.status != ToolStatus.AVAILABLE:
                results["compatible"] = False
                results["issues"].append(f"Required tool {name} not available")

        return results


# Global instances
_tool_manager: ToolManager | None = None
_compatibility_checker: ToolCompatibilityChecker | None = None


def get_tool_manager() -> ToolManager:
    global _tool_manager
    if _tool_manager is None:
        _tool_manager = ToolManager()
    return _tool_manager


def get_compatibility_checker() -> ToolCompatibilityChecker:
    global _compatibility_checker
    if _compatibility_checker is None:
        _compatibility_checker = ToolCompatibilityChecker(get_tool_manager())
    return _compatibility_checker


async def check_tool(name: str) -> ToolStatusInfo:
    return await get_tool_manager().check_tool(name)


async def check_all_tools(category: ToolCategory | None = None) -> dict[str, ToolStatusInfo]:
    return await get_tool_manager().check_all(category)


async def install_tool(name: str) -> bool:
    return await get_tool_manager().install_tool(name)


async def check_compatibility() -> dict[str, Any]:
    return await get_compatibility_checker().full_compatibility_check()
