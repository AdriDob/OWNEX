"""Team/Org API Router — Multi-hunter coordination."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from cores.team.org import (
    TeamRole,
    accept_invite,
    approve_request,
    create_approval_request,
    create_team,
    get_pending_approvals,
    get_team,
    get_user_teams,
    invite_user,
    reject_request,
)

logger = logging.getLogger("ownex.api.team")

router = APIRouter(prefix="/api/team", tags=["team"])


@router.post("/create")
async def api_create_team(
    name: str,
    owner_id: str,
    owner_email: str,
    owner_name: str,
) -> dict[str, Any]:
    """Create a new team."""
    team = create_team(name, owner_id, owner_email, owner_name)
    return team.__dict__


@router.get("/{team_id}")
async def api_get_team(team_id: str) -> dict[str, Any]:
    """Get team by ID."""
    team = get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team.__dict__


@router.get("/user/{user_id}")
async def api_get_user_teams(user_id: str) -> dict[str, Any]:
    """Get all teams for a user."""
    teams = get_user_teams(user_id)
    return {"teams": [t.__dict__ for t in teams]}


@router.post("/{team_id}/invite")
async def api_invite_user(
    team_id: str,
    requester_id: str,
    email: str,
    role: TeamRole = TeamRole.HUNTER,
) -> dict[str, Any]:
    """Invite a user to the team."""
    invite = invite_user(team_id, requester_id, email, role)
    return invite.__dict__


@router.post("/invite/{invite_id}/accept")
async def api_accept_invite(
    invite_id: str,
    user_id: str,
    email: str,
    name: str,
) -> dict[str, Any]:
    """Accept a team invitation."""
    member = accept_invite(invite_id, user_id, email, name)
    return member.__dict__


@router.post("/{team_id}/approval")
async def api_create_approval(
    team_id: str,
    requester_id: str,
    request_type: str,
    title: str,
    description: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Create an approval request."""
    request = create_approval_request(team_id, requester_id, request_type, title, description, payload)
    return request.__dict__


@router.post("/{team_id}/approval/{request_id}/approve")
async def api_approve_request(
    team_id: str,
    approver_id: str,
    request_id: str,
    reason: str = "",
) -> dict[str, Any]:
    """Approve a request."""
    request = approve_request(team_id, approver_id, request_id, reason)
    return request.__dict__


@router.post("/{team_id}/approval/{request_id}/reject")
async def api_reject_request(
    team_id: str,
    approver_id: str,
    request_id: str,
    reason: str,
) -> dict[str, Any]:
    """Reject a request."""
    request = reject_request(team_id, approver_id, request_id, reason)
    return request.__dict__


@router.get("/{team_id}/approvals/pending")
async def api_get_pending_approvals(
    team_id: str,
    user_id: str | None = Query(None),
) -> dict[str, Any]:
    """Get pending approval requests."""
    approvals = get_pending_approvals(team_id, user_id)
    return {"approvals": [a.__dict__ for a in approvals]}


@router.get("/{team_id}/members")
async def api_get_members(team_id: str) -> dict[str, Any]:
    """Get team members."""
    team = get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"members": [m.__dict__ for m in team.members.values()]}


@router.get("/{team_id}/invites")
async def api_get_invites(team_id: str) -> dict[str, Any]:
    """Get team invites."""
    team = get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"invites": [i.__dict__ for i in team.invites.values()]}
