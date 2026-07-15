"""Package management tools: winget, choco, scoop."""

from __future__ import annotations

import logging
import subprocess

from apps.hermes.tools.base import BaseTool, ToolResult

logger = logging.getLogger("catseye.hermes.tools.package")


class WingetTool(BaseTool):
    name = "winget"
    description = "Windows Package Manager — install, update, list, search packages"
    requires_windows = True

    def check_available(self) -> ToolResult:
        try:
            r = subprocess.run(["winget", "--version"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return ToolResult(True, f"winget {r.stdout.strip()}")
            return ToolResult(False, "winget not available")
        except FileNotFoundError:
            return ToolResult(False, "winget not found")

    def list_installed(self) -> ToolResult:
        try:
            r = subprocess.run(
                ["winget", "list", "--accept-source-agreements"], capture_output=True, text=True, timeout=30
            )
            if r.returncode == 0:
                lines = [line for line in r.stdout.split("\n") if line.strip()]
                return ToolResult(True, f"{len(lines)} packages", {"packages": lines[:100]})
            return ToolResult(False, r.stderr.strip())
        except subprocess.TimeoutExpired:
            return ToolResult(False, "winget list timed out")

    def search(self, query: str) -> ToolResult:
        try:
            r = subprocess.run(
                ["winget", "search", query, "--accept-source-agreements"], capture_output=True, text=True, timeout=30
            )
            if r.returncode == 0:
                lines = [line for line in r.stdout.split("\n") if line.strip()]
                return ToolResult(True, f"Found {len(lines)} results", {"results": lines[:50]})
            return ToolResult(False, r.stderr.strip())
        except subprocess.TimeoutExpired:
            return ToolResult(False, "winget search timed out")


class ChocolateyTool(BaseTool):
    name = "choco"
    description = "Chocolatey package manager — install, update, list packages"
    requires_windows = True
    requires_admin = True

    def check_available(self) -> ToolResult:
        try:
            r = subprocess.run(["choco", "--version"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return ToolResult(True, f"choco {r.stdout.strip()}")
            return ToolResult(False, "choco not available")
        except FileNotFoundError:
            return ToolResult(False, "choco not found")

    def list_installed(self) -> ToolResult:
        try:
            r = subprocess.run(["choco", "list", "--local-only"], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                lines = [line for line in r.stdout.split("\n") if line.strip() and "packages" not in line.lower()]
                return ToolResult(True, f"{len(lines)} packages", {"packages": lines})
            return ToolResult(False, r.stderr.strip())
        except subprocess.TimeoutExpired:
            return ToolResult(False, "choco list timed out")


class ScoopTool(BaseTool):
    name = "scoop"
    description = "Scoop package manager — install portable apps without admin"
    requires_windows = True

    def check_available(self) -> ToolResult:
        try:
            r = subprocess.run(["scoop", "--version"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return ToolResult(True, f"scoop {r.stdout.strip()}")
            return ToolResult(False, "scoop not available")
        except FileNotFoundError:
            return ToolResult(False, "scoop not found")

    def list_installed(self) -> ToolResult:
        try:
            r = subprocess.run(["scoop", "list"], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                lines = [line for line in r.stdout.split("\n") if line.strip()]
                return ToolResult(True, f"{len(lines)} apps", {"apps": lines})
            return ToolResult(False, r.stderr.strip())
        except subprocess.TimeoutExpired:
            return ToolResult(False, "scoop list timed out")
