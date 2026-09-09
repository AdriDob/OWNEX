"""Command Dispatcher — permission validation, EventBus publishing, execution history."""

from __future__ import annotations

import logging
import time
from typing import Any

from core.commands.models import (
    CommandDefinition,
    CommandRecord,
    CommandResult,
    PermissionLevel,
)
from core.commands.registry import get_command_registry

logger = logging.getLogger("orion.core.commands.dispatcher")


class CommandDispatcher:
    """Validates permissions, dispatches commands, publishes events, tracks history.

    The dispatcher is the runtime engine for Fase 1 of the Command System.
    It validates that the executing agent has sufficient authority, publishes
    lifecycle events to EventBus, and records execution history.
    """

    def __init__(self, max_history: int = 500) -> None:
        self._registry = get_command_registry()
        self._history: list[CommandRecord] = []
        self._max_history = max_history
        self._event_bus = None
        self._capability_registry = None

    # ── Optional binding to external systems ────────────────────

    def bind_event_bus(self, event_bus: Any) -> None:  # noqa: ANN401
        self._event_bus = event_bus

    def bind_capability_registry(self, cap_registry: Any) -> None:  # noqa: ANN401
        self._capability_registry = cap_registry
        self._register_capabilities()

    def _register_capabilities(self) -> None:
        if self._capability_registry is None:
            return
        for cap, module, meta in self._registry.to_capability_registry():
            try:
                self._capability_registry.register(cap, module, meta)  # type: ignore[union-attr]
            except Exception as exc:
                logger.warning("Failed to register capability '%s': %s", cap, exc)

    # ── Core dispatch logic ─────────────────────────────────────

    def dispatch(
        self,
        command_name: str,
        args: dict[str, Any] | None = None,
        authority: str | None = None,
        user: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Dispatch a command for execution.

        Args:
            command_name: Name of the command (with or without leading /).
            args: Arguments/parameters for the command.
            authority: Authority level of the executor (maps to PermissionLevel).
            user: User identifier for audit trail.
            dry_run: If True, validate only, don't execute.

        Returns:
            CommandResult with execution status.
        """
        start = time.time()
        name = command_name.lstrip("/")
        cmd = self._registry.get(name)

        # ── Command not found ──────────────────────────────────
        if cmd is None:
            result = CommandResult(
                command=name,
                status="failed",
                permission="unknown",
                reason=f"Command '/{name}' not found",
                duration_ms=(time.time() - start) * 1000,
                error="Unknown command. Use /help or list commands via API.",
            )
            self._record(result)
            self._publish_event("command:failed", name, result, user)
            return result

        # ── Permission validation ──────────────────────────────
        if not self._check_permission(cmd, authority):
            result = CommandResult(
                command=name,
                status="rejected",
                permission=cmd.permission.value,
                reason=f"Permission '{cmd.permission.value}' required, got '{authority or 'none'}'",
                duration_ms=(time.time() - start) * 1000,
                error=f"Insufficient permission. Command '/{name}' requires {cmd.permission.value} level.",
            )
            self._record(result)
            self._publish_event("command:rejected", name, result, user)
            return result

        # ── Dry run ────────────────────────────────────────────
        if dry_run:
            result = CommandResult(
                command=name,
                status="simulated",
                permission=cmd.permission.value,
                reason=f"Dry run: would execute '/{name}' with args {args or {}}",
                output=cmd.dict(),
                duration_ms=(time.time() - start) * 1000,
            )
            self._record(result)
            return result

        # ── Execute ────────────────────────────────────────────
        try:
            output = self._execute(cmd, args or {})
            elapsed = (time.time() - start) * 1000
            result = CommandResult(
                command=name,
                status="executed",
                permission=cmd.permission.value,
                reason=f"Command '/{name}' executed successfully",
                output=output,
                duration_ms=elapsed,
            )
            self._record(result)
            self._publish_event("command:executed", name, result, user)
            return result

        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            logger.exception("Command '/%s' failed", name)
            result = CommandResult(
                command=name,
                status="failed",
                permission=cmd.permission.value,
                reason=f"Command '/{name}' failed: {exc}",
                duration_ms=elapsed,
                error=str(exc),
            )
            self._record(result)
            self._publish_event("command:failed", name, result, user)
            return result

    # ── Permission check ────────────────────────────────────────

    def _check_permission(self, cmd: CommandDefinition, authority: str | None) -> bool:
        if authority is None:
            return cmd.permission == PermissionLevel.PUBLIC

        authority_map = {
            "observer": PermissionLevel.PUBLIC,
            "assistant": PermissionLevel.PUBLIC,
            "operator": PermissionLevel.OPERATOR,
            "senior_hunter": PermissionLevel.ADMIN,
            "administrator": PermissionLevel.DANGEROUS,
        }

        max_permitted = authority_map.get(authority.lower(), PermissionLevel.PUBLIC)
        required = cmd.permission

        order = [
            PermissionLevel.PUBLIC,
            PermissionLevel.OPERATOR,
            PermissionLevel.ADMIN,
            PermissionLevel.SYSTEM,
            PermissionLevel.DANGEROUS,
        ]

        return order.index(max_permitted) >= order.index(required)

    # ── Execution ───────────────────────────────────────────────

    def _execute(self, cmd: CommandDefinition, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a command. For Fase 1, this returns a stub result.

        In Fase 2, this will resolve to Execution Platform workflows.
        In Fase 3, COPILOT will handle complex commands.
        """
        return {
            "command": cmd.name,
            "status": "dispatched",
            "args": args,
            "note": "Fase 1 dispatcher — handler resolution pending (Fase 2)",
            "capabilities_needed": cmd.capabilities_used,
            "events_would_publish": cmd.events_published,
        }

    # ── History ─────────────────────────────────────────────────

    def _record(self, result: CommandResult) -> None:
        record = CommandRecord(
            command=result.command,
            status=result.status,
            permission=result.permission,
            reason=result.reason,
            duration_ms=result.duration_ms,
            error=result.error,
        )
        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    def history(self, limit: int = 20, status: str | None = None) -> list[CommandRecord]:
        records = list(reversed(self._history))
        if status:
            records = [r for r in records if r.status == status]
        return records[:limit]

    def history_by_command(self, command: str, limit: int = 10) -> list[CommandRecord]:
        return [r for r in reversed(self._history) if r.command == command][:limit]

    # ── Event publishing ────────────────────────────────────────

    def _publish_event(self, event_type: str, command: str, result: CommandResult, user: str | None = None) -> None:
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(  # type: ignore[union-attr]
                event_type,
                payload={
                    "command": command,
                    "status": result.status,
                    "permission": result.permission,
                    "reason": result.reason,
                    "duration_ms": result.duration_ms,
                    "error": result.error,
                },
                source="command_dispatcher",
                user=user,
            )
        except Exception as exc:
            logger.warning("Failed to publish event '%s': %s", event_type, exc)


# ── Singleton ────────────────────────────────────────

_dispatcher: CommandDispatcher | None = None


def get_command_dispatcher() -> CommandDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = CommandDispatcher()
    return _dispatcher


def reset_command_dispatcher() -> None:
    global _dispatcher
    _dispatcher = None
