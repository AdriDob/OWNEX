"""Team/Org Mode — Multi-hunter coordination.

Enables multiple hunters to work together with roles, shared resources,
approval workflows, and revenue splitting.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.team.org")


# ─── Roles ───


class TeamRole(StrEnum):
    OWNER = "owner"  # Full access, can manage team
    ADMIN = "admin"  # Can manage members, settings
    LEAD = "lead"  # Can assign work, approve submissions
    HUNTER = "hunter"  # Can discover, prepare, submit
    VIEWER = "viewer"  # Read-only access


class InviteStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


# ─── Data Models ───


@dataclass
class TeamMember:
    """A member of a team/org."""

    user_id: str
    email: str
    name: str
    role: TeamRole = TeamRole.HUNTER
    joined_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    invited_by: str | None = None
    avatar_url: str | None = None
    timezone: str = "UTC"
    notifications_enabled: bool = True
    revenue_split: float = 0.0  # Percentage of team revenue


@dataclass
class TeamInvite:
    """An invitation to join a team."""

    id: str
    team_id: str
    email: str
    role: TeamRole
    invited_by: str
    status: InviteStatus = InviteStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    expires_at: str | None = None
    accepted_at: str | None = None


@dataclass
class ApprovalRequest:
    """A request for approval (submission, expense, etc.)."""

    id: str
    team_id: str
    requester_id: str
    type: str  # submission, expense, resource_access, payout
    title: str
    description: str
    payload: dict[str, Any]  # Type-specific data
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    decided_at: str | None = None
    decision_reason: str | None = None


@dataclass
class SharedResource:
    """A resource shared within the team."""

    id: str
    team_id: str
    type: str  # credential, api_key, document, template, tool_config
    name: str
    description: str
    owner_id: str
    access_roles: list[TeamRole] = field(default_factory=lambda: [TeamRole.HUNTER])
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class Team:
    """A team/org in OWNEX."""

    id: str
    name: str
    owner_id: str
    description: str = ""
    members: dict[str, TeamMember] = field(default_factory=dict)  # user_id -> TeamMember
    invites: dict[str, TeamInvite] = field(default_factory=dict)  # invite_id -> TeamInvite
    approval_requests: dict[str, ApprovalRequest] = field(default_factory=dict)
    shared_resources: dict[str, SharedResource] = field(default_factory=dict)
    revenue_split: dict[str, float] = field(default_factory=dict)  # user_id -> percentage
    settings: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# ─── Team Engine ───


class TeamEngine:
    """Manages teams, members, and coordination."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        base = os.environ.get("OWNEX_DATA_DIR")
        self.data_dir = (
            Path(data_dir)
            if data_dir
            else (Path(base) if base else Path(__file__).resolve().parents[3] / "data" / "teams")
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.teams_file = self.data_dir / "teams.json"

    # ─── Team CRUD ───

    def create_team(self, name: str, owner_id: str, owner_email: str, owner_name: str) -> Team:
        team = Team(
            id=f"team_{hashlib.sha256(f'{name}{owner_id}{datetime.now(UTC)}'.encode()).hexdigest()[:12]}",
            name=name,
            owner_id=owner_id,
            members={
                owner_id: TeamMember(
                    user_id=owner_id,
                    email=owner_email,
                    name=owner_name,
                    role=TeamRole.OWNER,
                    revenue_split=100.0,
                )
            },
            revenue_split={owner_id: 100.0},
        )
        self.save_team(team)
        logger.info(f"Created team '{name}' (id: {team.id}) for owner {owner_id}")
        return team

    def get_team(self, team_id: str) -> Team | None:
        teams = self._load_teams()
        if team_id in teams:
            return self._coerce_team(teams[team_id])
        return None

    def get_user_teams(self, user_id: str) -> list[Team]:
        teams = self._load_teams()
        result = []
        for team_data in teams.values():
            if user_id in team_data.get("members", {}):
                result.append(self._coerce_team(team_data))
        return result

    @staticmethod
    def _coerce_team(data: dict[str, Any]) -> Team:
        """Rebuild nested dataclasses (members/invites/approvals/resources) from JSON dicts."""
        team = Team(**data)
        team.members = {
            k: (v if isinstance(v, TeamMember) else TeamMember(**v)) for k, v in (team.members or {}).items()
        }
        team.invites = {
            k: (v if isinstance(v, TeamInvite) else TeamInvite(**v)) for k, v in (team.invites or {}).items()
        }
        team.approval_requests = {
            k: (v if isinstance(v, ApprovalRequest) else ApprovalRequest(**v))
            for k, v in (team.approval_requests or {}).items()
        }
        team.shared_resources = {
            k: (v if isinstance(v, SharedResource) else SharedResource(**v))
            for k, v in (team.shared_resources or {}).items()
        }
        return team

    def save_team(self, team: Team) -> None:
        team.updated_at = datetime.now(UTC).isoformat()
        teams = self._load_teams()
        teams[team.id] = team.__dict__
        self._save_teams(teams)

    def delete_team(self, team_id: str, requester_id: str) -> bool:
        team = self.get_team(team_id)
        if not team:
            return False
        if team.owner_id != requester_id:
            raise PermissionError("Only owner can delete team")
        teams = self._load_teams()
        del teams[team_id]
        self._save_teams(teams)
        return True

    # ─── Member Management ───

    def add_member(
        self, team_id: str, requester_id: str, user_id: str, email: str, name: str, role: TeamRole
    ) -> TeamMember:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        requester_role = team.members.get(requester_id, TeamMember(user_id="", email="", name="")).role
        if requester_role not in (TeamRole.OWNER, TeamRole.ADMIN):
            raise PermissionError("Only owner/admin can add members")

        if user_id in team.members:
            raise ValueError("User already in team")

        member = TeamMember(user_id=user_id, email=email, name=name, role=role, invited_by=requester_id)
        team.members[user_id] = member
        self.save_team(team)
        return member

    def remove_member(self, team_id: str, requester_id: str, user_id: str) -> bool:
        team = self.get_team(team_id)
        if not team:
            return False

        requester_role = team.members.get(requester_id, TeamMember(user_id="", email="", name="")).role
        target_role = team.members.get(user_id, TeamMember(user_id="", email="", name="")).role

        if requester_role == TeamRole.OWNER:
            pass  # Owner can remove anyone
        elif requester_role == TeamRole.ADMIN:
            if target_role in (TeamRole.OWNER, TeamRole.ADMIN):
                raise PermissionError("Admin cannot remove owner or other admins")
        else:
            raise PermissionError("Insufficient permissions")

        if user_id == team.owner_id:
            raise ValueError("Cannot remove owner")

        del team.members[user_id]
        if user_id in team.revenue_split:
            del team.revenue_split[user_id]
        self.save_team(team)
        return True

    def update_member_role(self, team_id: str, requester_id: str, user_id: str, new_role: TeamRole) -> TeamMember:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        requester_role = team.members.get(requester_id, TeamMember(user_id="", email="", name="")).role
        if requester_role not in (TeamRole.OWNER, TeamRole.ADMIN):
            raise PermissionError("Insufficient permissions")

        if user_id not in team.members:
            raise ValueError("User not in team")

        if new_role == TeamRole.OWNER and requester_id != team.owner_id:
            raise PermissionError("Only current owner can transfer ownership")

        member = team.members[user_id]
        member.role = new_role
        self.save_team(team)
        return member

    def update_revenue_split(self, team_id: str, requester_id: str, splits: dict[str, float]) -> dict[str, float]:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        if team.owner_id != requester_id:
            raise PermissionError("Only owner can update revenue splits")

        total = sum(splits.values())
        if abs(total - 100.0) > 0.01:
            raise ValueError("Revenue splits must sum to 100%")

        # Validate all user_ids are team members
        for uid in splits:
            if uid not in team.members:
                raise ValueError(f"User {uid} not in team")

        team.revenue_split = splits
        for uid, pct in splits.items():
            if uid in team.members:
                team.members[uid].revenue_split = pct
        self.save_team(team)
        return team.revenue_split

    # ─── Invites ───

    def invite_user(self, team_id: str, requester_id: str, email: str, role: TeamRole) -> TeamInvite:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        requester_role = team.members.get(requester_id, TeamMember(user_id="", email="", name="")).role
        if requester_role not in (TeamRole.OWNER, TeamRole.ADMIN):
            raise PermissionError("Insufficient permissions")

        invite = TeamInvite(
            id=f"invite_{hashlib.sha256(f'{team_id}{email}{datetime.now(UTC)}'.encode()).hexdigest()[:12]}",
            team_id=team_id,
            email=email,
            role=role,
            invited_by=requester_id,
            expires_at=(datetime.now(UTC) + timedelta(days=7)).isoformat(),
        )
        team.invites[invite.id] = invite
        self.save_team(team)
        return invite

    def accept_invite(self, invite_id: str, user_id: str, email: str, name: str) -> TeamMember:
        # Find invite across all teams
        teams = self._load_teams()
        invite = None
        team = None
        for t in teams.values():
            if invite_id in t.get("invites", {}):
                invite = TeamInvite(**t["invites"][invite_id])
                team = Team(**t)
                break

        if not invite or not team:
            raise ValueError("Invite not found")

        if invite.email != email:
            raise ValueError("Email mismatch")

        if invite.status != InviteStatus.PENDING:
            raise ValueError("Invite not pending")

        if invite.expires_at and datetime.fromisoformat(invite.expires_at) < datetime.now(UTC):
            invite.status = InviteStatus.EXPIRED
            raise ValueError("Invite expired")

        # Add member
        member = TeamMember(user_id=user_id, email=email, name=name, role=invite.role, invited_by=invite.invited_by)
        team.members[user_id] = member
        invite.status = InviteStatus.ACCEPTED
        invite.accepted_at = datetime.now(UTC).isoformat()
        del team.invites[invite_id]

        self.save_team(team)
        return member

    def decline_invite(self, invite_id: str) -> bool:
        teams = self._load_teams()
        for team_data in teams.values():
            if invite_id in team_data.get("invites", {}):
                invite = team_data["invites"][invite_id]
                invite.status = InviteStatus.DECLINED
                self.save_team(Team(**team_data))
                return True
        return False

    # ─── Approvals ───

    def create_approval_request(
        self,
        team_id: str,
        requester_id: str,
        request_type: str,
        title: str,
        description: str,
        payload: dict[str, Any],
    ) -> ApprovalRequest:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        if requester_id not in team.members:
            raise ValueError("Requester not in team")

        request = ApprovalRequest(
            id=f"approval_{hashlib.sha256(f'{team_id}{requester_id}{datetime.now(UTC)}'.encode()).hexdigest()[:12]}",
            team_id=team_id,
            requester_id=requester_id,
            type=request_type,
            title=title,
            description=description,
            payload=payload,
        )
        team.approval_requests[request.id] = request
        self.save_team(team)
        return request

    def approve_request(self, team_id: str, approver_id: str, request_id: str, reason: str = "") -> ApprovalRequest:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        approver = team.members.get(approver_id)
        if not approver or approver.role not in (TeamRole.OWNER, TeamRole.ADMIN, TeamRole.LEAD):
            raise PermissionError("Insufficient permissions to approve")

        request = team.approval_requests.get(request_id)
        if not request:
            raise ValueError("Request not found")

        if request.status != ApprovalStatus.PENDING:
            raise ValueError("Request already decided")

        request.status = ApprovalStatus.APPROVED
        request.approver_id = approver_id
        request.decided_at = datetime.now(UTC).isoformat()
        request.decision_reason = reason
        self.save_team(team)
        return request

    def reject_request(self, team_id: str, approver_id: str, request_id: str, reason: str) -> ApprovalRequest:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        approver = team.members.get(approver_id)
        if not approver or approver.role not in (TeamRole.OWNER, TeamRole.ADMIN, TeamRole.LEAD):
            raise PermissionError("Insufficient permissions to reject")

        request = team.approval_requests.get(request_id)
        if not request:
            raise ValueError("Request not found")

        if request.status != ApprovalStatus.PENDING:
            raise ValueError("Request already decided")

        request.status = ApprovalStatus.REJECTED
        request.approver_id = approver_id
        request.decided_at = datetime.now(UTC).isoformat()
        request.decision_reason = reason
        self.save_team(team)
        return request

    def request_changes(self, team_id: str, approver_id: str, request_id: str, reason: str) -> ApprovalRequest:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        approver = team.members.get(approver_id)
        if not approver or approver.role not in (TeamRole.OWNER, TeamRole.ADMIN, TeamRole.LEAD):
            raise PermissionError("Insufficient permissions")

        request = team.approval_requests.get(request_id)
        if not request:
            raise ValueError("Request not found")

        request.status = ApprovalStatus.CHANGES_REQUESTED
        request.approver_id = approver_id
        request.decided_at = datetime.now(UTC).isoformat()
        request.decision_reason = reason
        self.save_team(team)
        return request

    def get_pending_approvals(self, team_id: str, user_id: str | None = None) -> list[ApprovalRequest]:
        team = self.get_team(team_id)
        if not team:
            return []

        approvals = list(team.approval_requests.values())
        if user_id:
            approvals = [a for a in approvals if a.requester_id == user_id]
        return [a for a in approvals if a.status == ApprovalStatus.PENDING]

    # ─── Shared Resources ───

    def add_shared_resource(
        self,
        team_id: str,
        owner_id: str,
        resource_type: str,
        name: str,
        description: str,
        access_roles: list[TeamRole],
        data: dict[str, Any],
    ) -> SharedResource:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        if owner_id not in team.members:
            raise ValueError("Owner not in team")

        resource = SharedResource(
            id=f"resource_{hashlib.sha256(f'{team_id}{name}{datetime.now(UTC)}'.encode()).hexdigest()[:12]}",
            team_id=team_id,
            type=resource_type,
            name=name,
            description=description,
            owner_id=owner_id,
            access_roles=access_roles,
            data=data,
        )
        team.shared_resources[resource.id] = resource
        self.save_team(team)
        return resource

    def get_accessible_resources(self, team_id: str, user_id: str) -> list[SharedResource]:
        team = self.get_team(team_id)
        if not team or user_id not in team.members:
            return []

        user_role = team.members[user_id].role
        return [r for r in team.shared_resources.values() if user_role in r.access_roles or r.owner_id == user_id]

    # ─── Persistence ───

    def _load_teams(self) -> dict[str, dict]:
        try:
            with open(self.teams_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_teams(self, teams: dict[str, Any]) -> None:
        with open(self.teams_file, "w", encoding="utf-8") as f:
            json.dump(self._dump(teams), f, indent=2, ensure_ascii=False)

    @staticmethod
    def _dump(obj: Any) -> Any:
        """JSON-safe recursive dump for nested dataclasses."""
        from dataclasses import is_dataclass
        from enum import Enum

        if is_dataclass(obj):
            return {k: TeamEngine._dump(v) for k, v in obj.__dict__.items()}
        if isinstance(obj, dict):
            return {k: TeamEngine._dump(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [TeamEngine._dump(v) for v in obj]
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return obj


# ─── Global Instance ───

_team_engine: TeamEngine | None = None


def get_team_engine() -> TeamEngine:
    global _team_engine
    if _team_engine is None:
        _team_engine = TeamEngine()
    return _team_engine


# ─── API Functions ───


def create_team(name: str, owner_id: str, owner_email: str, owner_name: str) -> Team:
    return get_team_engine().create_team(name, owner_id, owner_email, owner_name)


def get_team(team_id: str) -> Team | None:
    return get_team_engine().get_team(team_id)


def get_user_teams(user_id: str) -> list[Team]:
    return get_team_engine().get_user_teams(user_id)


def invite_user(team_id: str, requester_id: str, email: str, role: TeamRole) -> TeamInvite:
    return get_team_engine().invite_user(team_id, requester_id, email, role)


def accept_invite(invite_id: str, user_id: str, email: str, name: str) -> TeamMember:
    return get_team_engine().accept_invite(invite_id, user_id, email, name)


def create_approval_request(
    team_id: str,
    requester_id: str,
    request_type: str,
    title: str,
    description: str,
    payload: dict[str, Any],
) -> ApprovalRequest:
    return get_team_engine().create_approval_request(team_id, requester_id, request_type, title, description, payload)


def approve_request(team_id: str, approver_id: str, request_id: str, reason: str = "") -> ApprovalRequest:
    return get_team_engine().approve_request(team_id, approver_id, request_id, reason)


def reject_request(team_id: str, approver_id: str, request_id: str, reason: str) -> ApprovalRequest:
    return get_team_engine().reject_request(team_id, approver_id, request_id, reason)


def get_pending_approvals(team_id: str, user_id: str | None = None) -> list[ApprovalRequest]:
    return get_team_engine().get_pending_approvals(team_id, user_id)
