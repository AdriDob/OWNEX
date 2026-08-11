from __future__ import annotations

"""Command System — OWNEX's operational language runtime.
Fase 1 implementation: Command Registry + Dispatcher + Permission Validation.
"""
# ruff: noqa: E402
from core.commands.dispatcher import CommandDispatcher, get_command_dispatcher
from core.commands.models import (
    CommandCost,
    CommandDefinition,
    CommandFlag,
    CommandParam,
    CommandRecord,
    CommandResult,
    PermissionLevel,
)
from core.commands.registry import CommandRegistry, get_command_registry

__all__ = [
    "CommandCost",
    "CommandDefinition",
    "CommandFlag",
    "CommandParam",
    "CommandRecord",
    "CommandResult",
    "CommandRegistry",
    "CommandDispatcher",
    "PermissionLevel",
    "get_command_registry",
    "get_command_dispatcher",
]
