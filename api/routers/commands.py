"""Command System API — list, execute, inspect commands."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from core.commands import (
    get_command_dispatcher,
    get_command_registry,
)
from core.commands.dispatcher import CommandDispatcher

logger = logging.getLogger("cateye.api.commands")

router = APIRouter(prefix="/api/commands", tags=["commands"])

_dispatcher: CommandDispatcher | None = None


def _set_dispatcher(instance: CommandDispatcher) -> None:
    global _dispatcher
    _dispatcher = instance


def _get_dispatcher() -> CommandDispatcher:
    if _dispatcher is not None:
        return _dispatcher
    return get_command_dispatcher()


def _get_registry():
    return get_command_registry()


@router.get("")
def list_commands(
    category: str | None = Query(None, description="Filter by category"),
    permission: str | None = Query(None, description="Filter by permission level"),
):
    """List all registered commands, optionally filtered."""
    reg = _get_registry()
    cmds = reg.list(category=category, permission=permission)
    return {
        "total": len(cmds),
        "commands": [c.dict() for c in cmds],
        "categories": reg.categories(),
    }


@router.get("/categories")
def list_categories():
    """List all command categories."""
    return {"categories": _get_registry().categories()}


@router.get("/{command_name}")
def get_command(command_name: str):
    """Get details of a specific command."""
    cmd = _get_registry().get(command_name)
    if cmd is None:
        raise HTTPException(status_code=404, detail=f"Command '/{command_name}' not found")
    return cmd.dict()


@router.post("/{command_name}/execute")
def execute_command(
    command_name: str,
    args: dict[str, Any] | None = None,
    authority: str | None = "observer",
    user: str | None = None,
    dry_run: bool = False,
):
    """Execute a command with optional arguments."""
    disp = _get_dispatcher()
    result = disp.dispatch(
        command_name=command_name,
        args=args or {},
        authority=authority,
        user=user,
        dry_run=dry_run,
    )
    if result.status == "failed":
        raise HTTPException(status_code=404, detail=result.error)
    if result.status == "rejected":
        raise HTTPException(status_code=403, detail=result.error)
    return {
        "command": result.command,
        "status": result.status,
        "permission": result.permission,
        "reason": result.reason,
        "output": result.output,
        "duration_ms": result.duration_ms,
        "timestamp": result.timestamp,
    }


@router.get("/history/all")
def command_history(
    limit: int = Query(20, ge=1, le=200),
    status: str | None = Query(None, description="Filter by status"),
):
    """Get command execution history."""
    disp = _get_dispatcher()
    records = disp.history(limit=limit, status=status)
    return {
        "total": len(records),
        "records": [
            {
                "command": r.command,
                "status": r.status,
                "permission": r.permission,
                "reason": r.reason,
                "duration_ms": r.duration_ms,
                "error": r.error,
                "timestamp": r.timestamp,
            }
            for r in records
        ],
    }
