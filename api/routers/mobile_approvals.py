"""Mobile Approvals API — manage approval requests for autonomous actions."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from cores.events.event_bus import get_event_bus
from database.db import SessionLocal
from database.models import MobileApproval

logger = logging.getLogger("ownex.api.mobile_approvals")

router = APIRouter(prefix="/mobile", tags=["mobile-approvals"])


# WebSocket connection manager for mobile approvals
class ApprovalNotificationManager:
    """Manages WebSocket connections for real-time approval notifications."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("[ApprovalWS] Client connected. Total connections: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("[ApprovalWS] Client disconnected. Total connections: %d", len(self.active_connections))

    async def broadcast(self, message: dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning("[ApprovalWS] Failed to send to client: %s", e)
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

        logger.info("[ApprovalWS] Broadcasted to %d clients", len(self.active_connections))


_approval_ws_manager = ApprovalNotificationManager()


def get_approval_ws_manager() -> ApprovalNotificationManager:
    return _approval_ws_manager


# Pydantic models
class ApprovalRequest(BaseModel):
    entity_type: str
    entity_id: str
    title: str
    description: str | None = None
    metadata: dict[str, Any] | None = None
    priority: str = "medium"


class ApprovalResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    title: str
    description: str | None
    metadata: dict[str, Any] | None
    status: str
    priority: str
    approved_by: str | None
    approved_at: str | None
    rejection_reason: str | None
    created_at: str
    updated_at: str


@router.get("/pending-approvals", response_model=list[ApprovalResponse])
async def get_pending_approvals():
    """Get all pending mobile approvals."""
    db = SessionLocal()
    try:
        approvals = (
            db.query(MobileApproval)
            .filter(MobileApproval.status == "pending")
            .order_by(MobileApproval.priority.desc(), MobileApproval.created_at.asc())
            .all()
        )

        return [
            ApprovalResponse(
                id=a.id,
                entity_type=a.entity_type,
                entity_id=a.entity_id,
                title=a.title,
                description=a.description,
                metadata=json.loads(a.metadata_json) if a.metadata_json else None,
                status=a.status,
                priority=a.priority,
                approved_by=a.approved_by,
                approved_at=a.approved_at.isoformat() if a.approved_at else None,
                rejection_reason=a.rejection_reason,
                created_at=a.created_at.isoformat(),
                updated_at=a.updated_at.isoformat(),
            )
            for a in approvals
        ]
    finally:
        db.close()


@router.post("/create-approval", response_model=ApprovalResponse)
async def create_approval(request: ApprovalRequest):
    """Create a new mobile approval request."""
    db = SessionLocal()
    try:
        # Check if approval already exists for this entity
        existing = (
            db.query(MobileApproval)
            .filter(
                MobileApproval.entity_type == request.entity_type,
                MobileApproval.entity_id == request.entity_id,
                MobileApproval.status == "pending",
            )
            .first()
        )

        if existing:
            # Return existing approval
            return ApprovalResponse(
                id=existing.id,
                entity_type=existing.entity_type,
                entity_id=existing.entity_id,
                title=existing.title,
                description=existing.description,
                metadata=json.loads(existing.metadata_json) if existing.metadata_json else None,
                status=existing.status,
                priority=existing.priority,
                approved_by=existing.approved_by,
                approved_at=existing.approved_at.isoformat() if existing.approved_at else None,
                rejection_reason=existing.rejection_reason,
                created_at=existing.created_at.isoformat(),
                updated_at=existing.updated_at.isoformat(),
            )

        approval = MobileApproval(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            title=request.title,
            description=request.description,
            metadata_json=json.dumps(request.metadata) if request.metadata else None,
            priority=request.priority,
            status="pending",
        )

        db.add(approval)
        db.commit()
        db.refresh(approval)

        # Publish event for notification
        event_bus = get_event_bus()
        event_bus.publish(
            "approval:requested",
            {
                "approval_id": approval.id,
                "entity_type": approval.entity_type,
                "entity_id": approval.entity_id,
                "title": approval.title,
                "priority": approval.priority,
            },
        )

        # Broadcast via WebSocket (fire and forget)
        asyncio.create_task(
            get_approval_ws_manager().broadcast(
                {
                    "type": "approval_requested",
                    "approval_id": approval.id,
                    "entity_type": approval.entity_type,
                    "entity_id": approval.entity_id,
                    "title": approval.title,
                    "priority": approval.priority,
                }
            )
        )

        logger.info(
            "[MobileApprovals] Created approval %s for %s/%s",
            approval.id,
            approval.entity_type,
            approval.entity_id,
        )

        return ApprovalResponse(
            id=approval.id,
            entity_type=approval.entity_type,
            entity_id=approval.entity_id,
            title=approval.title,
            description=approval.description,
            metadata=json.loads(approval.metadata_json) if approval.metadata_json else None,
            status=approval.status,
            priority=approval.priority,
            approved_by=approval.approved_by,
            approved_at=approval.approved_at.isoformat() if approval.approved_at else None,
            rejection_reason=approval.rejection_reason,
            created_at=approval.created_at.isoformat(),
            updated_at=approval.updated_at.isoformat(),
        )
    finally:
        db.close()


@router.post("/approve/{approval_id}", response_model=ApprovalResponse)
async def approve_approval(approval_id: int, approved_by: str = "mobile"):
    """Approve a pending approval."""
    db = SessionLocal()
    try:
        approval = db.query(MobileApproval).filter(MobileApproval.id == approval_id).first()

        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")

        if approval.status != "pending":
            raise HTTPException(status_code=400, detail=f"Approval already {approval.status}")

        approval.status = "approved"
        approval.approved_by = approved_by
        approval.approved_at = datetime.now(UTC)
        db.commit()
        db.refresh(approval)

        # Publish event for notification
        event_bus = get_event_bus()
        event_bus.publish(
            "approval:approved",
            {
                "approval_id": approval.id,
                "entity_type": approval.entity_type,
                "entity_id": approval.entity_id,
                "approved_by": approved_by,
            },
        )

        # Broadcast via WebSocket (fire and forget)
        asyncio.create_task(
            get_approval_ws_manager().broadcast(
                {
                    "type": "approval_approved",
                    "approval_id": approval.id,
                    "entity_type": approval.entity_type,
                    "entity_id": approval.entity_id,
                }
            )
        )

        logger.info(
            "[MobileApprovals] Approved %s for %s/%s by %s",
            approval.id,
            approval.entity_type,
            approval.entity_id,
            approved_by,
        )

        return ApprovalResponse(
            id=approval.id,
            entity_type=approval.entity_type,
            entity_id=approval.entity_id,
            title=approval.title,
            description=approval.description,
            metadata=json.loads(approval.metadata_json) if approval.metadata_json else None,
            status=approval.status,
            priority=approval.priority,
            approved_by=approval.approved_by,
            approved_at=approval.approved_at.isoformat() if approval.approved_at else None,
            rejection_reason=approval.rejection_reason,
            created_at=approval.created_at.isoformat(),
            updated_at=approval.updated_at.isoformat(),
        )
    finally:
        db.close()


@router.post("/reject/{approval_id}", response_model=ApprovalResponse)
async def reject_approval(approval_id: int, rejection_reason: str = "", rejected_by: str = "mobile"):
    """Reject a pending approval."""
    db = SessionLocal()
    try:
        approval = db.query(MobileApproval).filter(MobileApproval.id == approval_id).first()

        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")

        if approval.status != "pending":
            raise HTTPException(status_code=400, detail=f"Approval already {approval.status}")

        approval.status = "rejected"
        approval.approved_by = rejected_by
        approval.rejection_reason = rejection_reason
        db.commit()
        db.refresh(approval)

        # Publish event for notification
        event_bus = get_event_bus()
        event_bus.publish(
            "approval:rejected",
            {
                "approval_id": approval.id,
                "entity_type": approval.entity_type,
                "entity_id": approval.entity_id,
                "rejected_by": rejected_by,
                "reason": rejection_reason,
            },
        )

        # Broadcast via WebSocket (fire and forget)
        asyncio.create_task(
            get_approval_ws_manager().broadcast(
                {
                    "type": "approval_rejected",
                    "approval_id": approval.id,
                    "entity_type": approval.entity_type,
                    "entity_id": approval.entity_id,
                }
            )
        )

        logger.info(
            "[MobileApprovals] Rejected %s for %s/%s by %s: %s",
            approval.id,
            approval.entity_type,
            approval.entity_id,
            rejected_by,
            rejection_reason,
        )

        return ApprovalResponse(
            id=approval.id,
            entity_type=approval.entity_type,
            entity_id=approval.entity_id,
            title=approval.title,
            description=approval.description,
            metadata=json.loads(approval.metadata_json) if approval.metadata_json else None,
            status=approval.status,
            priority=approval.priority,
            approved_by=approval.approved_by,
            approved_at=approval.approved_at.isoformat() if approval.approved_at else None,
            rejection_reason=approval.rejection_reason,
            created_at=approval.created_at.isoformat(),
            updated_at=approval.updated_at.isoformat(),
        )
    finally:
        db.close()


@router.get("/approval/{approval_id}", response_model=ApprovalResponse)
async def get_approval(approval_id: int):
    """Get a specific approval by ID."""
    db = SessionLocal()
    try:
        approval = db.query(MobileApproval).filter(MobileApproval.id == approval_id).first()

        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")

        return ApprovalResponse(
            id=approval.id,
            entity_type=approval.entity_type,
            entity_id=approval.entity_id,
            title=approval.title,
            description=approval.description,
            metadata=json.loads(approval.metadata_json) if approval.metadata_json else None,
            status=approval.status,
            priority=approval.priority,
            approved_by=approval.approved_by,
            approved_at=approval.approved_at.isoformat() if approval.approved_at else None,
            rejection_reason=approval.rejection_reason,
            created_at=approval.created_at.isoformat(),
            updated_at=approval.updated_at.isoformat(),
        )
    finally:
        db.close()


@router.get("/approvals/count")
async def get_approvals_count():
    """Get count of pending approvals by priority."""
    db = SessionLocal()
    try:
        pending = db.query(MobileApproval).filter(MobileApproval.status == "pending").count()
        high_priority = (
            db.query(MobileApproval)
            .filter(MobileApproval.status == "pending", MobileApproval.priority.in_(["high", "critical"]))
            .count()
        )

        return {"pending": pending, "high_priority": high_priority}
    finally:
        db.close()


@router.websocket("/ws/approvals")
async def websocket_approvals(websocket: WebSocket):
    """WebSocket endpoint for real-time approval notifications."""
    await get_approval_ws_manager().connect(websocket)

    try:
        while True:
            # Keep connection alive and handle ping/pong
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        get_approval_ws_manager().disconnect(websocket)
    except Exception as e:
        logger.warning("[ApprovalWS] WebSocket error: %s", e)
        get_approval_ws_manager().disconnect(websocket)
