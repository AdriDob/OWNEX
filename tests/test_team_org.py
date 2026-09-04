"""Tests for the Team/Org Mode (cores/team/org.py)."""

from __future__ import annotations

import pytest

from cores.team.org import (
    ApprovalStatus,
    TeamEngine,
    TeamRole,
    get_team_engine,
)


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    e = TeamEngine(data_dir=tmp_path)
    monkeypatch.setattr("cores.team.org._team_engine", e)
    return e


def test_create_team(engine):
    team = engine.create_team("Red Team", "owner1", "owner@x.io", "Owner")
    assert team.id.startswith("team_")
    assert "owner1" in team.members
    assert team.members["owner1"].role == TeamRole.OWNER
    assert engine.get_team(team.id) is not None


def test_add_and_remove_member(engine):
    team = engine.create_team("T", "owner1", "o@x.io", "O")
    engine.add_member(team.id, "owner1", "h1", "h1@x.io", "Hunter A", TeamRole.HUNTER)
    assert "h1" in engine.get_team(team.id).members
    engine.remove_member(team.id, "owner1", "h1")
    assert "h1" not in engine.get_team(team.id).members


def test_add_member_permission_denied_for_hunter(engine):
    team = engine.create_team("T", "owner1", "o@x.io", "O")
    engine.add_member(team.id, "owner1", "h1", "h1@x.io", "H", TeamRole.HUNTER)
    with pytest.raises(PermissionError):
        engine.add_member(team.id, "h1", "h2", "h2@x.io", "H2", TeamRole.HUNTER)


def test_revenue_split_validation(engine):
    team = engine.create_team("T", "owner1", "o@x.io", "O")
    engine.add_member(team.id, "owner1", "h1", "h1@x.io", "H", TeamRole.HUNTER)
    with pytest.raises(ValueError):
        engine.update_revenue_split(team.id, "owner1", {"owner1": 50.0, "h1": 40.0})  # sums to 90
    splits = engine.update_revenue_split(team.id, "owner1", {"owner1": 50.0, "h1": 50.0})
    assert splits["h1"] == 50.0


def test_invite_accept(engine):
    team = engine.create_team("T", "owner1", "o@x.io", "O")
    invite = engine.invite_user(team.id, "owner1", "new@x.io", TeamRole.HUNTER)
    assert invite.status.value == "pending"
    member = engine.accept_invite(invite.id, "n1", "new@x.io", "New")
    assert member.user_id == "n1"
    assert "n1" in engine.get_team(team.id).members


def test_approval_workflow(engine):
    team = engine.create_team("T", "owner1", "o@x.io", "O")
    engine.add_member(team.id, "owner1", "lead1", "lead@x.io", "Lead", TeamRole.LEAD)
    req = engine.create_approval_request(
        team.id,
        "lead1",
        "submission",
        "Submit report",
        "desc",
        {"report_id": "r1"},
    )
    assert req.status == ApprovalStatus.PENDING
    approved = engine.approve_request(team.id, "owner1", req.id, "ok")
    assert approved.status == ApprovalStatus.APPROVED
    assert engine.get_pending_approvals(team.id, "lead1") == []


def test_reject_approval(engine):
    team = engine.create_team("T", "owner1", "o@x.io", "O")
    req = engine.create_approval_request(
        team.id,
        "owner1",
        "expense",
        "Buy laptop",
        "desc",
        {"amount": 1000},
    )
    rejected = engine.reject_request(team.id, "owner1", req.id, "no budget")
    assert rejected.status == ApprovalStatus.REJECTED


def test_shared_resources_by_role(engine):
    team = engine.create_team("T", "owner1", "o@x.io", "O")
    engine.add_member(team.id, "owner1", "h1", "h1@x.io", "H", TeamRole.HUNTER)
    engine.add_member(team.id, "owner1", "v1", "v1@x.io", "V", TeamRole.VIEWER)
    engine.add_shared_resource(
        team.id,
        "owner1",
        "api_key",
        "H1 Key",
        "key",
        [TeamRole.HUNTER],
        {"value": "sk-..."},
    )
    hunter_res = engine.get_accessible_resources(team.id, "h1")
    viewer_res = engine.get_accessible_resources(team.id, "v1")
    assert len(hunter_res) == 1
    assert len(viewer_res) == 0  # viewer not in access_roles


def test_user_teams(engine):
    t1 = engine.create_team("A", "u1", "a@x.io", "A")
    t2 = engine.create_team("B", "u1", "a@x.io", "A")
    teams = engine.get_user_teams("u1")
    assert {t.id for t in teams} == {t1.id, t2.id}


def test_delete_team(engine):
    team = engine.create_team("T", "owner1", "o@x.io", "O")
    assert engine.delete_team(team.id, "owner1") is True
    assert engine.get_team(team.id) is None


def test_owner_required_for_delete(engine):
    team = engine.create_team("T", "owner1", "o@x.io", "O")
    engine.add_member(team.id, "owner1", "h1", "h1@x.io", "H", TeamRole.HUNTER)
    with pytest.raises(PermissionError):
        engine.delete_team(team.id, "h1")


def test_singleton():
    assert get_team_engine() is get_team_engine()
