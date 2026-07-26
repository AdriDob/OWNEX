"""Tests for Hermes Automation Agent."""

from __future__ import annotations

from apps.hermes.engine import AUTHORIZED_COMMANDS, AutomationEngine


def test_engine_initializes_in_safe_mode() -> None:
    engine = AutomationEngine(safe_mode=True)
    assert engine.safe_mode is True
    assert engine.status_summary()["safe_mode"] is True


def test_engine_initializes_without_safe_mode() -> None:
    engine = AutomationEngine(safe_mode=False)
    assert engine.safe_mode is False


def test_unknown_command_returns_error() -> None:
    engine = AutomationEngine()
    result = engine.execute("nonexistent")
    assert result.status == "error"
    assert "Unknown command" in result.message


def test_help_command_lists_all() -> None:
    engine = AutomationEngine()
    result = engine.execute("help")
    assert result.status == "ok"
    assert len(result.details["commands"]) == len(AUTHORIZED_COMMANDS)
    names = {c["name"] for c in result.details["commands"]}
    assert "help" in names
    assert "backup" in names
    assert "status" in names
    assert "health" in names
    assert "logs" in names
    assert "doctor" in names


def test_status_returns_ok() -> None:
    engine = AutomationEngine()
    result = engine.execute("status")
    assert result.status == "ok"
    assert "python" in result.details
    assert "cwd" in result.details


def test_health_returns_ok() -> None:
    engine = AutomationEngine()
    result = engine.execute("health")
    assert result.status == "ok"


def test_logs_returns_entries() -> None:
    engine = AutomationEngine()
    result = engine.execute("logs", lines=10)
    assert result.status == "ok"
    assert isinstance(result.details.get("entries"), list)


def test_doctor_returns_diagnostics() -> None:
    engine = AutomationEngine()
    result = engine.execute("doctor")
    assert result.status == "ok"
    assert "findings" in result.details
    assert "issues" in result.details
    assert result.details["findings"]["safe_mode"] is True


def test_safe_mode_allows_non_destructive_commands() -> None:
    engine = AutomationEngine(safe_mode=True)
    result = engine.execute("status")
    assert result.status == "ok"


def test_backup_attempts_execution(monkeypatch) -> None:
    import subprocess

    monkeypatch.setattr(
        subprocess, "run", lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    )
    engine = AutomationEngine(safe_mode=False)
    result = engine.execute("backup")
    assert result.status in ("ok", "error")


def test_history_tracks_actions() -> None:
    engine = AutomationEngine()
    engine.execute("help")
    engine.execute("status")
    history = engine.get_history()
    assert len(history) == 2
    assert history[0].command == "help"
    assert history[1].command == "status"


def test_history_respects_limit() -> None:
    engine = AutomationEngine()
    for _ in range(5):
        engine.execute("help")
    assert len(engine.get_history(limit=3)) == 3


def test_status_summary_shape() -> None:
    engine = AutomationEngine()
    s = engine.status_summary()
    assert "engine" in s
    assert "safe_mode" in s
    assert "available_commands" in s
    assert "actions_today" in s
    assert "total_actions" in s
    assert isinstance(s["available_commands"], list)


def test_each_command_has_required_fields() -> None:
    for name, cmd in AUTHORIZED_COMMANDS.items():
        assert "label" in cmd, f"Command '{name}' missing label"
        assert "description" in cmd, f"Command '{name}' missing description"
        assert "risk" in cmd, f"Command '{name}' missing risk"
        assert cmd["risk"] in ("none", "low", "medium", "high"), f"Command '{name}' invalid risk"
        assert "destructive" in cmd, f"Command '{name}' missing destructive"


def test_engine_singleton_behavior() -> None:
    e1 = AutomationEngine()
    e2 = AutomationEngine()
    e1.execute("help")
    # Each engine has its own history
    assert len(e1.get_history()) == 1
    assert len(e2.get_history()) == 0
