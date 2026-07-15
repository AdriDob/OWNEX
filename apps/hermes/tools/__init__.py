"""Hermes Tool Registry — auto-discovers and manages all desktop tools."""

from __future__ import annotations

from typing import Any

from apps.hermes.tools.base import BaseTool, ToolResult
from apps.hermes.tools.package_manager import ChocolateyTool, ScoopTool, WingetTool
from apps.hermes.tools.system import FileManager, ProcessManager, ServiceManager, SystemMonitor
from apps.hermes.tools.windows import EnvironmentManager, PowerShellRunner, ScheduledTasks

_BUILTIN_TOOLS: list[type[BaseTool]] = [
    WingetTool,
    ChocolateyTool,
    ScoopTool,
    ProcessManager,
    SystemMonitor,
    ServiceManager,
    FileManager,
    PowerShellRunner,
    ScheduledTasks,
    EnvironmentManager,
]


class ToolRegistry:
    """Registry of all available desktop tools with lazy instantiation."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        for tool_cls in _BUILTIN_TOOLS:
            inst = tool_cls()
            self._tools[inst.name] = inst

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_available(self) -> list[dict[str, Any]]:
        results = []
        for tool in self._tools.values():
            avail = tool.check_available()
            results.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "available": avail.success,
                    "requires_admin": tool.requires_admin,
                    "requires_windows": tool.requires_windows,
                    "message": avail.message,
                }
            )
        return results

    def all_tools(self) -> dict[str, BaseTool]:
        return dict(self._tools)


def get_tool_registry() -> ToolRegistry:
    return ToolRegistry()
