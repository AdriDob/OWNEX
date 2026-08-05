"""
OWNEX Remote Control API — Omega chat → Alpha PC.
WebSocket for real-time, REST for session management.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from cores.remote_control.bridge import (
    create_omega_session,
    get_remote_bridge,
    omega_approve,
    omega_chat,
)

router = APIRouter(prefix="/remote", tags=["remote-control"])


class CreateSessionRequest(BaseModel):
    device_id: str
    user_id: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    auto_approve: bool = False


class ApproveRequest(BaseModel):
    session_id: str
    command_id: str


@router.post("/session")
async def create_session(request: CreateSessionRequest) -> dict[str, Any]:
    """Create new Omega → Alpha bridge session."""
    session = create_omega_session(request.device_id, request.user_id)
    return {
        "session_id": session.id,
        "device_id": session.device_id,
        "user_id": session.user_id,
        "created_at": session.created_at.isoformat(),
        "message": "Session created. Connect to WebSocket for real-time chat.",
    }


@router.post("/chat")
async def chat_rest(request: ChatRequest) -> dict[str, Any]:
    """REST endpoint for chat (fallback if WebSocket unavailable)."""
    return await omega_chat(request.session_id, request.message, request.auto_approve)


@router.post("/approve")
async def approve_command(request: ApproveRequest) -> dict[str, Any]:
    """Approve a pending command."""
    return await omega_approve(request.session_id, request.command_id)


@router.get("/session/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    """Get session info."""
    bridge = get_remote_bridge()
    session = bridge.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "session_id": session.id,
        "device_id": session.device_id,
        "user_id": session.user_id,
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
        "active_commands": session.active_commands,
    }


@router.get("/history/{session_id}")
async def get_history(session_id: str, limit: int = 50) -> dict[str, Any]:
    """Get command history for session."""
    from cores.memory.system import MemoryNamespace, get_memory_store

    memory = get_memory_store()

    # Get all remote commands for this session
    entries = memory.list(MemoryNamespace.CONVERSATION, tag="remote_command")
    session_commands = [e for e in entries if e.value.get("session_id") == session_id]
    session_commands.sort(key=lambda x: x.created_at, reverse=True)

    return {
        "session_id": session_id,
        "commands": [
            {
                "id": e.key,
                "user_input": e.value.get("user_input"),
                "status": e.value.get("status"),
                "risk_level": e.value.get("risk_level"),
                "created_at": e.value.get("created_at"),
                "completed_at": e.value.get("completed_at"),
            }
            for e in session_commands[:limit]
        ],
    }


# ===== WebSocket for Real-time Chat =====


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send(self, session_id: str, message: dict):
        ws = self.active_connections.get(session_id)
        if ws:
            await ws.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time Omega ↔ Alpha chat."""

    bridge = get_remote_bridge()
    session = bridge.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Invalid session")
        return

    await manager.connect(session_id, websocket)

    try:
        # Send welcome
        await websocket.send_json(
            {
                "type": "connected",
                "session_id": session_id,
                "message": "🔗 Conectado a OWNEX Alpha. Escribe libremente para controlar tu PC.",
            }
        )

        while True:
            data = await websocket.receive_json()

            if data.get("type") == "chat":
                message = data.get("message", "")
                auto_approve = data.get("auto_approve", False)

                # Process through bridge
                result = await omega_chat(session_id, message, auto_approve)

                await websocket.send_json(result)

                # If confirmation required, wait for approval
                if result.get("type") == "confirmation_required":
                    # Wait for next message as approval
                    approval_data = await websocket.receive_json()
                    if approval_data.get("type") == "approval" and approval_data.get("approve"):
                        result = await omega_approve(session_id, result["command_id"])
                        await websocket.send_json(result)

            elif data.get("type") == "approval":
                command_id = data.get("command_id")
                if command_id:
                    result = await omega_approve(session_id, command_id)
                    await websocket.send_json(result)

            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        manager.disconnect(session_id)
