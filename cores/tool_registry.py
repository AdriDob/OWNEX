"""Tool Registry — central registry for all tools with permission/risk declarations.

Each tool declares:
- Name, function, description
- Required permissions
- Risk level
- Input/output schema
- Validation rules
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from core.events.event_bus import get_core_event_bus
from cores.prometheus_metrics import (
    record_execution_action,
)

logger = logging.getLogger("ownex.tool_registry")


class ToolPermission(Enum):
    """Permission levels required for tool usage."""

    NONE = "none"  # No special permission needed
    READ_ONLY = "read_only"  # Read-only access to resources
    WRITE = "write"  # Can modify resources
    EXECUTE = "execute"  # Can execute code/commands
    NETWORK = "network"  # Can make network requests
    FILESYSTEM = "filesystem"  # Can access filesystem
    SECRETS = "secrets"  # Can access secrets/vault
    ADMIN = "admin"  # Administrative privileges


class ToolRisk(Enum):
    """Risk level of tool execution."""

    NONE = 0  # Read-only, no side effects
    LOW = 1  # Minor side effects, easily reversible
    MEDIUM = 2  # Moderate side effects, requires approval
    HIGH = 3  # Significant side effects, requires explicit approval
    CRITICAL = 4  # Irreversible or high-impact actions


@dataclass
class ToolInputSchema:
    """Input schema for a tool."""

    properties: dict[str, dict[str, Any]]  # JSON Schema properties
    required: list[str] = field(default_factory=list)
    additional_properties: bool = False


@dataclass
class ToolOutputSchema:
    """Output schema for a tool."""

    properties: dict[str, dict[str, Any]]
    required: list[str] = field(default_factory=list)


@dataclass
class ToolValidationRule:
    """Validation rule for tool input/output."""

    name: str
    description: str
    validator: Callable[[Any], bool]  # Returns True if valid
    error_message: str
    applies_to: str = "input"  # "input", "output", or "both"


@dataclass
class ToolManifest:
    """Complete tool declaration/manifest."""

    name: str
    description: str
    version: str = "1.0.0"
    category: str = "general"

    # Permissions & Risk
    required_permissions: list[ToolPermission] = field(default_factory=list)
    risk_level: ToolRisk = ToolRisk.NONE
    requires_approval: bool = False
    approval_reason: str = ""

    # Schemas
    input_schema: ToolInputSchema | None = None
    output_schema: ToolOutputSchema | None = None

    # Validation
    validation_rules: list[ToolValidationRule] = field(default_factory=list)

    # Execution
    timeout_seconds: int = 30
    max_retries: int = 2
    retryable_errors: list[str] = field(default_factory=list)

    # Metadata
    tags: list[str] = field(default_factory=list)
    author: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deprecated: bool = False
    replacement_tool: str | None = None


class BaseTool(ABC):
    """Abstract base class for all tools."""

    def __init__(self, manifest: ToolManifest):
        self.manifest = manifest
        self._execution_count = 0
        self._total_duration = 0.0
        self._last_error: str | None = None
        self._last_executed: datetime | None = None

    @abstractmethod
    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool with given inputs."""
        pass

    async def validate_input(self, inputs: dict[str, Any]) -> list[str]:
        """Validate inputs against schema and rules."""
        errors = []

        if self.manifest.input_schema:
            # Check required fields
            for req in self.manifest.input_schema.required:
                if req not in inputs:
                    errors.append(f"Missing required field: {req}")

            # Check additional properties
            if not self.manifest.input_schema.additional_properties:
                allowed = set(self.manifest.input_schema.properties.keys())
                for key in inputs:
                    if key not in allowed:
                        errors.append(f"Unexpected field: {key}")

        # Run custom validation rules
        for rule in self.manifest.validation_rules:
            if rule.applies_to in ("input", "both"):
                try:
                    if not rule.validator(inputs):
                        errors.append(rule.error_message)
                except Exception as e:
                    errors.append(f"Validation error in {rule.name}: {e}")

        return errors

    async def validate_output(self, output: dict[str, Any]) -> list[str]:
        """Validate output against schema and rules."""
        errors = []

        if self.manifest.output_schema:
            for req in self.manifest.output_schema.required:
                if req not in output:
                    errors.append(f"Missing required output field: {req}")

        for rule in self.manifest.validation_rules:
            if rule.applies_to in ("output", "both"):
                try:
                    if not rule.validator(output):
                        errors.append(rule.error_message)
                except Exception as e:
                    errors.append(f"Output validation error in {rule.name}: {e}")

        return errors

    async def execute_safe(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute with full validation, retries, and metrics."""
        start_time = time.time()

        # Validate input
        input_errors = await self.validate_input(inputs)
        if input_errors:
            raise ValueError(f"Input validation failed: {input_errors}")

        # Execute with retries
        last_exception = None
        for attempt in range(self.manifest.max_retries + 1):
            try:
                output = await asyncio.wait_for(self.execute(inputs), timeout=self.manifest.timeout_seconds)

                # Validate output
                output_errors = await self.validate_output(output)
                if output_errors:
                    raise ValueError(f"Output validation failed: {output_errors}")

                # Record success metrics
                duration = time.time() - start_time
                self._execution_count += 1
                self._total_duration += duration
                self._last_executed = datetime.now(UTC)
                self._last_error = None

                record_execution_action(
                    action_type=self.manifest.name, capability=self.manifest.category, duration=duration, success=True
                )

                return output

            except Exception as e:
                last_exception = e
                error_str = str(e)

                # Check if retryable
                is_retryable = any(retry_err in error_str for retry_err in self.manifest.retryable_errors)

                if attempt < self.manifest.max_retries and is_retryable:
                    logger.warning(
                        "Tool %s attempt %d failed, retrying: %s", self.manifest.name, attempt + 1, error_str
                    )
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                    continue
                else:
                    break

        # All retries failed
        duration = time.time() - start_time
        self._last_error = str(last_exception)

        record_execution_action(
            action_type=self.manifest.name, capability=self.manifest.category, duration=duration, success=False
        )

        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("Tool execution failed with unknown error")

    def get_stats(self) -> dict[str, Any]:
        """Get tool execution statistics."""
        avg_duration = self._total_duration / max(self._execution_count, 1)
        return {
            "name": self.manifest.name,
            "executions": self._execution_count,
            "total_duration": self._total_duration,
            "avg_duration": avg_duration,
            "last_error": self._last_error,
            "last_executed": self._last_executed.isoformat() if self._last_executed else None,
        }


class ToolRegistry:
    """
    Central registry for all tools in the system.

    Manages tool registration, discovery, execution, and access control.
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._manifests: dict[str, ToolManifest] = {}
        self._categories: dict[str, list[str]] = {}
        self._permission_index: dict[ToolPermission, list[str]] = {}
        self.event_bus = get_core_event_bus()
        logger.info("ToolRegistry initialized")

    def register(self, tool: BaseTool) -> None:
        """Register a tool in the registry."""
        name = tool.manifest.name

        if name in self._tools:
            logger.warning("Tool %s already registered, replacing", name)

        self._tools[name] = tool
        self._manifests[name] = tool.manifest

        # Update category index
        category = tool.manifest.category
        if category not in self._categories:
            self._categories[category] = []
        if name not in self._categories[category]:
            self._categories[category].append(name)

        # Update permission index
        for perm in tool.manifest.required_permissions:
            if perm not in self._permission_index:
                self._permission_index[perm] = []
            if name not in self._permission_index[perm]:
                self._permission_index[perm].append(name)

        logger.info("Registered tool: %s (category=%s, risk=%s)", name, category, tool.manifest.risk_level.name)

        self.event_bus.publish(
            "tool:registered",
            name=name,
            category=category,
            risk=tool.manifest.risk_level.name,
            permissions=[p.value for p in tool.manifest.required_permissions],
        )

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name not in self._tools:
            return False

        tool = self._tools[name]
        category = tool.manifest.category

        del self._tools[name]
        del self._manifests[name]

        if category in self._categories:
            self._categories[category].remove(name)

        for perm_list in self._permission_index.values():
            if name in perm_list:
                perm_list.remove(name)

        logger.info("Unregistered tool: %s", name)
        self.event_bus.publish("tool:unregistered", name=name)
        return True

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_manifest(self, name: str) -> ToolManifest | None:
        """Get a tool manifest by name."""
        return self._manifests.get(name)

    def list_tools(self, category: str | None = None) -> list[ToolManifest]:
        """List all tools, optionally filtered by category."""
        names = self._categories.get(category, []) if category else list(self._tools.keys())
        return [self._manifests[n] for n in names]

    def list_categories(self) -> list[str]:
        """List all tool categories."""
        return list(self._categories.keys())

    def find_by_permission(self, permission: ToolPermission) -> list[ToolManifest]:
        """Find tools requiring a specific permission."""
        names = self._permission_index.get(permission, [])
        return [self._manifests[n] for n in names]

    def find_by_risk(self, max_risk: ToolRisk) -> list[ToolManifest]:
        """Find tools with risk level at or below max_risk."""
        return [m for m in self._manifests.values() if m.risk_level.value <= max_risk.value]

    def find_by_tag(self, tag: str) -> list[ToolManifest]:
        """Find tools with a specific tag."""
        return [m for m in self._manifests.values() if tag in m.tags]

    async def execute(
        self,
        name: str,
        inputs: dict[str, Any],
        permissions: list[ToolPermission] | None = None,
        auto_approve: bool = False,
    ) -> dict[str, Any]:
        """
        Execute a tool with permission checking.

        Args:
            name: Tool name
            inputs: Input parameters
            permissions: User's granted permissions
            auto_approve: Skip approval check (for autonomous mode)
        """
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")

        manifest = tool.manifest

        # Check permissions
        if permissions is not None:
            missing = [p for p in manifest.required_permissions if p not in permissions]
            if missing:
                raise PermissionError(f"Missing permissions for {name}: {[p.value for p in missing]}")

        # Check approval requirement
        if manifest.requires_approval and not auto_approve:
            raise PermissionError(f"Tool {name} requires approval: {manifest.approval_reason}")

        # Check deprecation
        if manifest.deprecated:
            replacement = manifest.replacement_tool or "unknown"
            logger.warning("Tool %s is deprecated, use %s instead", name, replacement)

        # Execute
        return await tool.execute_safe(inputs)

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_tools": len(self._tools),
            "categories": {cat: len(tools) for cat, tools in self._categories.items()},
            "by_risk": {risk.name: len(self.find_by_risk(risk)) for risk in ToolRisk},
            "tools": {name: tool.get_stats() for name, tool in self._tools.items()},
        }

    async def health_check(self) -> dict[str, Any]:
        """Check health of all tools."""
        issues = []
        for name, tool in self._tools.items():
            if tool.manifest.deprecated:
                issues.append(f"Tool {name} is deprecated")
            if tool._last_error:
                issues.append(f"Tool {name} last error: {tool._last_error}")

        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "total_tools": len(self._tools),
        }


# ──────────────────────────────────────────────────────────────────────────
# BUILT-IN TOOLS
# ──────────────────────────────────────────────────────────────────────────


class BrowserTool(BaseTool):
    """Tool for web browsing and automation."""

    def __init__(self):
        manifest = ToolManifest(
            name="browser",
            description="Web browser automation using Playwright",
            category="browser",
            required_permissions=[ToolPermission.NETWORK, ToolPermission.EXECUTE],
            risk_level=ToolRisk.MEDIUM,
            requires_approval=True,
            approval_reason="Browser automation can interact with external websites",
            timeout_seconds=120,
            max_retries=2,
            retryable_errors=["timeout", "navigation"],
            tags=["web", "automation", "playwright"],
        )
        super().__init__(manifest)

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        action = inputs.get("action", "navigate")

        if action == "navigate":
            url = inputs["url"]
            # In real implementation: use Playwright
            return {"action": "navigate", "url": url, "status": "completed"}

        elif action == "screenshot":
            return {"action": "screenshot", "path": "/tmp/screenshot.png"}

        elif action == "extract":
            selector = inputs.get("selector", "body")
            return {"action": "extract", "selector": selector, "data": "extracted content"}

        elif action == "click":
            selector = inputs["selector"]
            return {"action": "click", "selector": selector, "status": "completed"}

        else:
            raise ValueError(f"Unknown browser action: {action}")


class TerminalTool(BaseTool):
    """Tool for executing terminal commands."""

    def __init__(self):
        manifest = ToolManifest(
            name="terminal",
            description="Execute shell commands",
            category="terminal",
            required_permissions=[ToolPermission.EXECUTE, ToolPermission.FILESYSTEM],
            risk_level=ToolRisk.HIGH,
            requires_approval=True,
            approval_reason="Terminal can execute arbitrary commands on the system",
            timeout_seconds=300,
            max_retries=1,
            retryable_errors=["timeout"],
            tags=["shell", "command", "execution"],
        )
        super().__init__(manifest)

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        import subprocess

        command = inputs["command"]
        timeout = inputs.get("timeout", 60)
        cwd = inputs.get("cwd", ".")

        # In real implementation, use async subprocess
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

        return {
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }


class GitTool(BaseTool):
    """Tool for Git operations."""

    def __init__(self):
        manifest = ToolManifest(
            name="git",
            description="Git version control operations",
            category="git",
            required_permissions=[ToolPermission.EXECUTE, ToolPermission.FILESYSTEM],
            risk_level=ToolRisk.MEDIUM,
            requires_approval=True,
            approval_reason="Git can modify repository history",
            timeout_seconds=60,
            max_retries=2,
            tags=["version_control", "git", "repository"],
        )
        super().__init__(manifest)

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        action = inputs.get("action", "status")

        if action == "status":
            return {"action": "status", "clean": True, "branch": "main"}

        elif action == "commit":
            message = inputs["message"]
            return {"action": "commit", "message": message, "hash": "abc123"}

        elif action == "push":
            remote = inputs.get("remote", "origin")
            branch = inputs.get("branch", "main")
            return {"action": "push", "remote": remote, "branch": branch}

        elif action == "diff":
            return {"action": "diff", "changes": []}

        else:
            raise ValueError(f"Unknown git action: {action}")


class EditorTool(BaseTool):
    """Tool for file editing operations."""

    def __init__(self):
        manifest = ToolManifest(
            name="editor",
            description="File editing and manipulation",
            category="editor",
            required_permissions=[ToolPermission.FILESYSTEM, ToolPermission.WRITE],
            risk_level=ToolRisk.MEDIUM,
            requires_approval=True,
            approval_reason="Editor can modify files on the filesystem",
            timeout_seconds=30,
            max_retries=2,
            tags=["file", "edit", "write"],
        )
        super().__init__(manifest)

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        action = inputs.get("action", "read")

        if action == "read":
            path = inputs["path"]
            return {"action": "read", "path": path, "content": "file content"}

        elif action == "write":
            path = inputs["path"]
            content = inputs["content"]
            return {"action": "write", "path": path, "bytes": len(content)}

        elif action == "patch":
            path = inputs["path"]
            inputs["old_string"]
            inputs["new_string"]
            return {"action": "patch", "path": path, "replaced": True}

        elif action == "list":
            path = inputs.get("path", ".")
            return {"action": "list", "path": path, "files": []}

        else:
            raise ValueError(f"Unknown editor action: {action}")


class APITool(BaseTool):
    """Tool for making HTTP API requests."""

    def __init__(self):
        manifest = ToolManifest(
            name="api",
            description="HTTP API client for REST/GraphQL",
            category="api",
            required_permissions=[ToolPermission.NETWORK],
            risk_level=ToolRisk.LOW,
            requires_approval=False,
            timeout_seconds=30,
            max_retries=3,
            retryable_errors=["timeout", "connection", "5xx"],
            tags=["http", "rest", "graphql", "api"],
        )
        super().__init__(manifest)

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        method = inputs.get("method", "GET")
        url = inputs["url"]
        inputs.get("headers", {})
        inputs.get("body")

        # In real implementation: use aiohttp
        return {
            "method": method,
            "url": url,
            "status": 200,
            "headers": {"content-type": "application/json"},
            "body": {"result": "success"},
        }


class DatabaseTool(BaseTool):
    """Tool for database operations."""

    def __init__(self):
        manifest = ToolManifest(
            name="database",
            description="Database query and manipulation",
            category="database",
            required_permissions=[ToolPermission.READ_ONLY, ToolPermission.WRITE],
            risk_level=ToolRisk.MEDIUM,
            requires_approval=True,
            approval_reason="Database tool can read and modify data",
            timeout_seconds=60,
            max_retries=2,
            tags=["sql", "query", "database"],
        )
        super().__init__(manifest)

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        action = inputs.get("action", "query")

        if action == "query":
            sql = inputs["sql"]
            return {"action": "query", "sql": sql, "rows": [], "row_count": 0}

        elif action == "execute":
            sql = inputs["sql"]
            return {"action": "execute", "sql": sql, "affected_rows": 0}

        else:
            raise ValueError(f"Unknown database action: {action}")


class VoiceTool(BaseTool):
    """Tool for text-to-speech and speech recognition."""

    def __init__(self):
        manifest = ToolManifest(
            name="voice",
            description="Text-to-speech and speech-to-text",
            category="voice",
            required_permissions=[ToolPermission.NETWORK, ToolPermission.EXECUTE],
            risk_level=ToolRisk.LOW,
            requires_approval=False,
            timeout_seconds=60,
            max_retries=2,
            tags=["tts", "stt", "speech", "audio"],
        )
        super().__init__(manifest)

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        action = inputs.get("action", "speak")

        if action == "speak":
            text = inputs["text"]
            voice = inputs.get("voice", "default")
            return {"action": "speak", "text": text, "voice": voice, "audio_url": "/tmp/speech.mp3"}

        elif action == "listen":
            duration = inputs.get("duration", 10)
            return {"action": "listen", "duration": duration, "transcript": "recognized speech"}

        else:
            raise ValueError(f"Unknown voice action: {action}")


class DocumentTool(BaseTool):
    """Tool for document processing (PDF, Word, etc.)."""

    def __init__(self):
        manifest = ToolManifest(
            name="document",
            description="Document processing and extraction",
            category="document",
            required_permissions=[ToolPermission.FILESYSTEM, ToolPermission.READ_ONLY],
            risk_level=ToolRisk.LOW,
            requires_approval=False,
            timeout_seconds=120,
            max_retries=2,
            tags=["pdf", "docx", "extraction", "ocr"],
        )
        super().__init__(manifest)

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        action = inputs.get("action", "extract_text")

        if action == "extract_text":
            path = inputs["path"]
            return {"action": "extract_text", "path": path, "text": "extracted text"}

        elif action == "convert":
            path = inputs["path"]
            format = inputs.get("format", "pdf")
            return {"action": "convert", "path": path, "format": format, "output": "/tmp/output.pdf"}

        else:
            raise ValueError(f"Unknown document action: {action}")


# ──────────────────────────────────────────────────────────────────────────
# REGISTRY INITIALIZATION
# ──────────────────────────────────────────────────────────────────────────

_tool_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        _register_builtin_tools(_tool_registry)
    return _tool_registry


def _register_builtin_tools(registry: ToolRegistry) -> None:
    """Register all built-in tools."""
    tools = [
        BrowserTool(),
        TerminalTool(),
        GitTool(),
        EditorTool(),
        APITool(),
        DatabaseTool(),
        VoiceTool(),
        DocumentTool(),
    ]

    for tool in tools:
        registry.register(tool)

    logger.info("Registered %d built-in tools", len(tools))


async def initialize_tool_registry() -> ToolRegistry:
    """Initialize and return the tool registry."""
    registry = get_tool_registry()
    health = await registry.health_check()
    logger.info("Tool registry initialized: %s", "healthy" if health["healthy"] else "issues found")
    return registry
