"""Approvals API — Human-in-the-loop approval endpoints.

Endpoints for requesting, approving, and tracking approvals.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class RequestApprovalRequest(BaseModel):
    action_type: str  # submit_report, send_external, financial_transfer, etc.
    title: str
    description: str
    risk_level: str = "medium"
    estimated_impact: str = ""


class DecideRequest(BaseModel):
    notes: str = ""


@router.get("/pending")
async def get_pending():
    """Get all pending approval requests."""
    from cores.approval.gates import get_approval_gate

    gate = get_approval_gate()
    return {"pending": [r.to_dict() for r in gate.get_pending()]}


@router.post("/request")
async def request_approval(request: RequestApprovalRequest):
    """Request approval for an action."""
    from cores.approval.gates import ActionType, get_approval_gate

    gate = get_approval_gate()
    try:
        action_type = ActionType(request.action_type)
    except ValueError:
        return {"error": f"Invalid action type: {request.action_type}"}

    req = gate.request_approval(
        action_type=action_type,
        title=request.title,
        description=request.description,
        risk_level=request.risk_level,
        estimated_impact=request.estimated_impact,
    )

    if req is None:
        return {"status": "auto_approved", "message": "No approval needed (AUTO level)"}

    return {"status": "pending", "request": req.to_dict()}


@router.post("/{request_id}/approve")
async def approve(request_id: str, request: DecideRequest):
    """Approve a pending request."""
    from cores.approval.gates import get_approval_gate

    gate = get_approval_gate()
    success = gate.approve(request_id, notes=request.notes)
    if not success:
        return {"error": f"Request {request_id} not found or not pending"}
    return {"status": "approved", "request_id": request_id}


@router.post("/{request_id}/reject")
async def reject(request_id: str, request: DecideRequest):
    """Reject a pending request."""
    from cores.approval.gates import get_approval_gate

    gate = get_approval_gate()
    success = gate.reject(request_id, notes=request.notes)
    if not success:
        return {"error": f"Request {request_id} not found or not pending"}
    return {"status": "rejected", "request_id": request_id}


@router.get("/history")
async def get_history(limit: int = 50):
    """Get approval history."""
    from cores.approval.gates import get_approval_gate

    gate = get_approval_gate()
    return {"history": [r.to_dict() for r in gate.get_history(limit)]}


@router.get("/stats")
async def get_stats():
    """Get approval statistics."""
    from cores.approval.gates import get_approval_gate

    gate = get_approval_gate()
    return gate.get_stats()
