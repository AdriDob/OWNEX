"""
OWNEX Remote Control Bridge — Omega Chat → Alpha PC Control.

Architecture:
Omega (mobile) → WebSocket → Bridge Server → Assistance Core → PC Execution
                         ↑
                    Copilot reasoning (OAR)
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cores.ai.runtime import TaskType, get_oar
from cores.assistance.core import AssistanceMode, ExecutionResult, get_assistance_engine
from cores.memory.system import MemoryNamespace, MemoryTier, get_memory_store

logger = logging.getLogger("ownex.remote_bridge")


class CommandRisk(StrEnum):
    SAFE = "safe"
    MODERATE = "moderate"
    RISKY = "risky"
    DESTRUCTIVE = "destructive"


@dataclass
class RemoteCommand:
    id: str
    user_input: str
    parsed_intent: dict[str, Any]
    risk_level: CommandRisk
    requires_confirmation: bool
    target_device: str = "alpha"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    session_id: str = ""
    status: str = "pending"
    result: Any = None
    error: str | None = None
    reasoning: str = ""


@dataclass
class BridgeSession:
    id: str
    device_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    context: dict[str, Any] = field(default_factory=dict)
    active_commands: list[str] = field(default_factory=list)


class CommandParser:
    """Parses free-form user input into structured intent with risk assessment."""

    def __init__(self):
        self.oar = get_oar()

    async def parse(self, user_input: str, context: dict[str, Any] | None = None) -> RemoteCommand:
        prompt = f"""
You are OWNEX Copilot. Parse this user request into a structured command for remote PC control.

USER INPUT: "{user_input}"

CONTEXT:
- Device: OWNEX Alpha (desktop PC)
- OS: Linux/Windows/macOS
- Current dir: ~/
- Available: terminal, file ops, code, git, docker, python, node, tools
- Memory: persistent, knows user patterns

Analyze and return JSON:
{{
  "action_type": "terminal|file|code|git|docker|tool|system|info|workflow",
  "intent": "clear one-sentence description of what user wants",
  "command": "exact command to execute (or null if multi-step)",
  "args": {{}},
  "risk_level": "safe|moderate|risky|destructive",
  "requires_confirmation": true/false,
  "reasoning": "why this risk level, what could go wrong, why it's needed",
  "estimated_duration_seconds": 30,
  "reversible": true/false,
  "alternatives": ["safer alternative 1", "safer alternative 2"],
  "preconditions": ["what must be true before running"],
  "postconditions": ["what should be true after success"]
}}

RISK GUIDELINES:
- safe: read-only, status, info, list, cat, git status, ps, df
- moderate: file write/edit, config change, pip install, npm install, git commit, docker build
- risky: system config, network changes, sudo, service restart, chmod 777, rm files
- destructive: rm -rf, format, fdisk, dd, shred, irreversible deletes

REQUIRES_CONFIRMATION: true for moderate+, false for safe
"""
        response = await self.oar.chat(
            prompt,
            task_type=TaskType.REASONING,
            temperature=0.1,
            max_tokens=2000,
        )

        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError:
            parsed = {
                "action_type": "terminal",
                "intent": user_input,
                "command": user_input,
                "args": {},
                "risk_level": "moderate",
                "requires_confirmation": True,
                "reasoning": "Could not parse, defaulting to moderate risk",
                "estimated_duration_seconds": 30,
                "reversible": True,
                "alternatives": [],
                "preconditions": [],
                "postconditions": [],
            }

        cmd = RemoteCommand(
            id=str(uuid.uuid4())[:8],
            user_input=user_input,
            parsed_intent=parsed,
            risk_level=CommandRisk(parsed.get("risk_level", "moderate")),
            requires_confirmation=parsed.get("requires_confirmation", True),
            session_id=context.get("session_id", "") if context else "",
        )
        cmd.reasoning = parsed.get("reasoning", "")
        return cmd


class RemoteExecutor:
    """Executes parsed commands on the Alpha PC."""

    def __init__(self):
        self.assistance = get_assistance_engine()
        self.memory = get_memory_store()

    async def execute(self, cmd: RemoteCommand, session: BridgeSession) -> ExecutionResult:
        parsed = cmd.parsed_intent
        action_type = parsed.get("action_type", "terminal")

        objective = f"Remote command from Omega: {parsed.get('intent', cmd.user_input)}"
        if parsed.get("command"):
            objective += f"\nCommand: {parsed['command']}"

        context = {
            "remote": True,
            "source": "omega",
            "session_id": session.id,
            "command_id": cmd.id,
            "risk_level": cmd.risk_level.value,
            "parsed": parsed,
        }

        if action_type in ("terminal", "file", "system") and parsed.get("command"):
            return await self._execute_direct(cmd, parsed, session)
        else:
            return await self.assistance.process_objective(
                objective=objective,
                mode=AssistanceMode.NORMAL,
                context=context,
            )

    async def _execute_direct(self, cmd: RemoteCommand, parsed: dict, session: BridgeSession) -> ExecutionResult:
        command = parsed.get("command", "")
        if not command:
            return ExecutionResult(
                plan_id=cmd.id,
                success=False,
                completed_subtasks=0,
                failed_subtasks=1,
                errors={cmd.id: "No command specified"},
            )

        start_time = datetime.now(UTC)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=session.context.get("cwd", str(Path.home())),
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            result = {
                "command": command,
                "exit_code": process.returncode,
                "stdout": stdout.decode()[:10000] if stdout else "",
                "stderr": stderr.decode()[:5000] if stderr else "",
                "duration_ms": duration_ms,
            }

            success = process.returncode == 0

            self.memory.set(
                MemoryNamespace.CONVERSATION,
                f"remote_cmd_{cmd.id}",
                {
                    "command": command,
                    "result": result,
                    "session_id": session.id,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                tier=MemoryTier.TEMPORARY,
                ttl_seconds=86400,
            )

            return ExecutionResult(
                plan_id=cmd.id,
                success=success,
                completed_subtasks=1 if success else 0,
                failed_subtasks=0 if success else 1,
                results={cmd.id: result},
                errors={} if success else {cmd.id: stderr.decode()[:500] if stderr else "Command failed"},
                total_duration_ms=duration_ms,
            )

        except TimeoutError:
            return ExecutionResult(
                plan_id=cmd.id,
                success=False,
                completed_subtasks=0,
                failed_subtasks=1,
                errors={cmd.id: "Command timed out (5 min)"},
            )
        except Exception as e:
            return ExecutionResult(
                plan_id=cmd.id,
                success=False,
                completed_subtasks=0,
                failed_subtasks=1,
                errors={cmd.id: str(e)},
            )


class RemoteBridge:
    """Main bridge managing Omega ↔ Alpha communication."""

    def __init__(self):
        self.parser = CommandParser()
        self.executor = RemoteExecutor()
        self.memory = get_memory_store()
        self._sessions: dict[str, BridgeSession] = {}

    def create_session(self, device_id: str, user_id: str) -> BridgeSession:
        session = BridgeSession(
            id=str(uuid.uuid4())[:8],
            device_id=device_id,
            user_id=user_id,
            created_at=datetime.now(UTC),
            last_activity=datetime.now(UTC),
        )
        self._sessions[session.id] = session

        self.memory.set(
            MemoryNamespace.CONVERSATION,
            f"bridge_session_{session.id}",
            {
                "session_id": session.id,
                "device_id": device_id,
                "user_id": user_id,
                "created_at": session.created_at.isoformat(),
            },
            tier=MemoryTier.TEMPORARY,
            ttl_seconds=604800,
        )
        return session

    def get_session(self, session_id: str) -> BridgeSession | None:
        return self._sessions.get(session_id)

    async def process_message(
        self,
        session_id: str,
        user_input: str,
        auto_approve: bool = False,
    ) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Invalid session", "session_id": session_id}

        session.last_activity = datetime.now(UTC)

        cmd = await self.parser.parse(user_input, {"session_id": session_id})
        session.active_commands.append(cmd.id)

        self.memory.set(
            MemoryNamespace.CONVERSATION,
            f"remote_cmd_{cmd.id}",
            {
                "id": cmd.id,
                "user_input": cmd.user_input,
                "parsed": cmd.parsed_intent,
                "risk_level": cmd.risk_level.value,
                "requires_confirmation": cmd.requires_confirmation,
                "session_id": session_id,
                "status": cmd.status,
                "created_at": cmd.created_at.isoformat(),
            },
            tier=MemoryTier.PERMANENT,
            tags=["remote_command", "audit"],
        )

        if cmd.requires_confirmation and not auto_approve:
            return {
                "type": "confirmation_required",
                "command_id": cmd.id,
                "intent": cmd.parsed_intent.get("intent"),
                "command": cmd.parsed_intent.get("command"),
                "risk_level": cmd.risk_level.value,
                "reasoning": cmd.reasoning,
                "alternatives": cmd.parsed_intent.get("alternatives", []),
                "preconditions": cmd.parsed_intent.get("preconditions", []),
                "message": f"⚠️ {cmd.reasoning}\n\nEjecutar: `{cmd.parsed_intent.get('command', 'N/A')}`?\n\nResponde 'sí' para confirmar o 'no' para cancelar.",
            }

        cmd.status = "executing"
        result = await self.executor.execute(cmd, session)
        cmd.status = "completed" if result.success else "failed"
        cmd.result = result.results
        cmd.error = str(result.errors) if result.errors else None

        self.memory.set(
            MemoryNamespace.CONVERSATION,
            f"remote_cmd_{cmd.id}",
            {
                "id": cmd.id,
                "user_input": cmd.user_input,
                "parsed": cmd.parsed_intent,
                "risk_level": cmd.risk_level.value,
                "session_id": session_id,
                "status": cmd.status,
                "result": str(result.results)[:2000] if result.results else None,
                "error": cmd.error,
                "duration_ms": result.total_duration_ms,
                "completed_at": datetime.now(UTC).isoformat(),
            },
            tier=MemoryTier.PERMANENT,
            tags=["remote_command", "audit"],
        )

        return {
            "type": "result",
            "command_id": cmd.id,
            "success": result.success,
            "output": str(result.results)[:3000] if result.results else None,
            "error": cmd.error,
            "duration_ms": result.total_duration_ms,
            "message": "✅ Completado" if result.success else f"❌ Error: {cmd.error}",
        }

    async def approve_command(self, session_id: str, command_id: str) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Invalid session"}

        cmd_data = self.memory.get(MemoryNamespace.CONVERSATION, f"remote_cmd_{command_id}")
        if not cmd_data:
            return {"error": "Command not found"}

        return await self.process_message(session_id, cmd_data["user_input"], auto_approve=True)


_bridge: RemoteBridge | None = None


def get_remote_bridge() -> RemoteBridge:
    global _bridge
    if _bridge is None:
        _bridge = RemoteBridge()
    return _bridge


async def omega_chat(
    session_id: str,
    message: str,
    auto_approve: bool = False,
) -> dict[str, Any]:
    bridge = get_remote_bridge()
    return await bridge.process_message(session_id, message, auto_approve)


async def omega_approve(session_id: str, command_id: str) -> dict[str, Any]:
    bridge = get_remote_bridge()
    return await bridge.approve_command(session_id, command_id)


def create_omega_session(device_id: str, user_id: str) -> BridgeSession:
    bridge = get_remote_bridge()
    return bridge.create_session(device_id, user_id)
