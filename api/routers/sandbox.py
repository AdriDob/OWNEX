"""API Router for Sandbox Mode."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.sandbox_mode import (
    get_sandbox_bounties,
    get_sandbox_bounty,
    get_sandbox_progress,
    reset_sandbox,
    submit_sandbox_bounty,
)

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


class SubmitRequest(BaseModel):
    bounty_id: str
    solution: str
    files: dict[str, str] = {}


@router.get("/bounties")
def list_sandbox_bounties():
    """List all available sandbox bounties."""
    return {"items": get_sandbox_bounties(), "total": len(get_sandbox_bounties())}


@router.get("/bounties/{bounty_id}")
def get_bounty(bounty_id: str):
    """Get single sandbox bounty details."""
    bounty = get_sandbox_bounty(bounty_id)
    if not bounty:
        raise HTTPException(status_code=404, detail="Bounty not found")
    return bounty


@router.post("/submit")
def submit_bounty(req: SubmitRequest):
    """Submit solution for sandbox bounty (auto-validated)."""
    result = submit_sandbox_bounty(req.bounty_id, req.solution, req.files)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Submission failed"))
    return result


@router.get("/progress")
def progress():
    """Get user's sandbox progress."""
    return get_sandbox_progress()


@router.post("/reset")
def reset():
    """Reset sandbox progress."""
    return reset_sandbox()


@router.get("/state")
def state():
    """Get full sandbox state for frontend."""
    return {
        "bounties": get_sandbox_bounties(),
        "progress": get_sandbox_progress(),
    }
