"""Tests for Hermes permission system."""

from __future__ import annotations

from apps.hermes.permissions import (
    ActionHistory,
    ActionPermission,
    ActionRecord,
    RiskLevel,
    evaluate_action,
    get_command_risk,
    needs_confirmation,
)


def test_risk_level_constants() -> None:
    assert RiskLevel.NONE == "none"
    assert RiskLevel.LOW == "low"
    assert RiskLevel.MEDIUM == "medium"
    assert RiskLevel.HIGH == "high"
    assert RiskLevel.CRITICAL == "critical"
    assert len(RiskLevel.ALL) == 5


def test_get_command_risk_read_commands() -> None:
    for cmd in ("status", "health", "help", "tools", "snapshot", "top", "ps", "packages", "disks", "services"):
        risk = get_command_risk(cmd)
        assert risk["risk"] in (RiskLevel.NONE, RiskLevel.LOW)
        assert risk["destructive"] is False


def test_get_command_risk_kill() -> None:
    risk = get_command_risk("kill")
    assert risk["risk"] == RiskLevel.HIGH
    assert risk["destructive"] is True


def test_get_command_risk_unknown_defaults_to_high() -> None:
    risk = get_command_risk("unknown_dangerous_action")
    assert risk["risk"] == RiskLevel.HIGH
    assert risk["destructive"] is True


def test_needs_confirmation_kill() -> None:
    assert needs_confirmation("kill", safe_mode=True) is True
    assert needs_confirmation("kill", safe_mode=False) is True


def test_needs_confirmation_read_command() -> None:
    assert needs_confirmation("status", safe_mode=True) is False
    assert needs_confirmation("status", safe_mode=False) is False


def test_needs_confirmation_destructive_in_safe_mode() -> None:
    assert needs_confirmation("kill", safe_mode=True) is True


def test_evaluate_action_none_risk() -> None:
    perm = evaluate_action("status", safe_mode=True)
    assert perm.allowed is True
    assert perm.risk == RiskLevel.NONE
    assert perm.requires_confirmation is False


def test_evaluate_action_blocks_kill_in_safe_mode() -> None:
    perm = evaluate_action("kill", safe_mode=True)
    assert perm.allowed is False
    assert perm.blocked_by == "safe_mode"
    assert perm.risk == RiskLevel.HIGH


def test_evaluate_action_blocks_kill_with_force() -> None:
    perm = evaluate_action("kill", safe_mode=True, force=True)
    assert perm.allowed is True


def test_evaluate_action_allows_kill_outside_safe_mode() -> None:
    perm = evaluate_action("kill", safe_mode=False)
    assert perm.allowed is True
    assert perm.requires_confirmation is True


def test_action_permission_dataclass() -> None:
    perm = ActionPermission(
        allowed=False,
        command="test",
        risk="critical",
        destructive=True,
        impact="Destroys everything",
        requires_confirmation=True,
        rollback_available=False,
        reason="Too dangerous",
        blocked_by="risk_threshold",
    )
    assert perm.allowed is False
    assert perm.command == "test"
    assert perm.blocked_by == "risk_threshold"


def test_action_history_records_and_limits() -> None:
    hist = ActionHistory(max_size=5)
    for i in range(10):
        hist.record(
            ActionRecord(command="test", status="completed", risk="low", destructive=False, message=f"action {i}")
        )
    recent = hist.recent()
    assert len(recent) == 5
    assert recent[0].message == "action 9"


def test_action_history_by_command() -> None:
    hist = ActionHistory()
    hist.record(ActionRecord(command="backup", status="completed", risk="low", destructive=False, message="ok"))
    hist.record(ActionRecord(command="kill", status="denied", risk="high", destructive=True, message="blocked"))
    hist.record(ActionRecord(command="backup", status="failed", risk="low", destructive=False, message="error"))
    backups = hist.by_command("backup")
    assert len(backups) == 2


def test_rollback_available_for_low_medium_risk() -> None:
    assert evaluate_action("backup", safe_mode=False).rollback_available is True
    assert evaluate_action("doctor", safe_mode=False).rollback_available is True


def test_rollback_not_available_for_high_risk() -> None:
    assert evaluate_action("kill", safe_mode=False).rollback_available is False
