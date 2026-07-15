from __future__ import annotations

from core.setup.first_run import is_setup_complete, setup_status
from core.setup.requirements_check import check_all
from core.setup.steps import get_all_steps
from core.setup.wizard import go_back, reset_wizard, run_step, skip_step, wizard_status


def test_requirements_check_returns_valid_structure():
    result = check_all()
    assert "status" in result
    assert result["status"] in ("ok", "warning", "error")
    assert "total" in result
    assert result["total"] > 0
    assert "results" in result
    assert "by_category" in result


def test_requirements_check_has_categories():
    result = check_all()
    assert "system" in result["by_category"]
    assert "security" in result["by_category"]


def test_requirements_check_python_ok():
    """Python check should always pass (we're running Python)."""
    result = check_all()
    python_result = [r for r in result["results"] if r["name"] == "python"]
    assert len(python_result) == 1
    assert python_result[0]["status"] == "ok"


def test_requirements_check_vault():
    """Vault check should not crash."""
    result = check_all()
    vault = [r for r in result["results"] if r["name"] == "vault"]
    assert len(vault) == 1
    assert vault[0]["status"] in ("ok", "warning")


def test_wizard_has_registered_steps():
    steps = get_all_steps()
    assert len(steps) >= 6
    step_ids = [s.step_id for s in steps]
    assert "identity" in step_ids
    assert "system" in step_ids
    assert "copilot" in step_ids
    assert "integrations" in step_ids
    assert "smartwatch" in step_ids
    assert "test" in step_ids


def test_wizard_initial_state():
    reset_wizard()
    status = wizard_status()
    assert status["started"] is False
    assert status["completed"] is False
    assert status["progress"] == 0.0
    assert len(status["steps"]) >= 6
    assert "step_data" in status


def test_wizard_system_step():
    reset_wizard()
    result = run_step("system")
    assert result["started"] is True
    assert "system" in result["step_data"]
    step_data = result["step_data"]["system"]
    assert "total_checks" in step_data
    assert step_data["total_checks"] > 0


def test_wizard_full_flow():
    reset_wizard()

    r1 = run_step("identity", {"username": "testuser", "role": "observer"})
    assert r1["step_data"]["identity"]["username"] == "testuser"

    r2 = run_step("system")
    assert "system" in r2["step_data"]

    r3 = run_step("copilot", {"authority_level": "observer", "llm_provider": "ollama"})
    assert r3["step_data"]["copilot"]["authority_level"] == "observer"

    r4 = run_step("integrations")
    assert "integrations" in r4["step_data"]

    r5 = run_step("smartwatch", {"enable_watch": False})
    assert r5["step_data"]["smartwatch"]["enabled"] is False

    r6 = run_step("test")
    assert "test" in r6["step_data"]

    result = run_step("finish")
    assert result["completed"] is True
    assert result["progress"] == 100.0


def test_wizard_go_back():
    reset_wizard()
    run_step("identity")
    run_step("system")
    state_before = wizard_status()
    current = state_before["current_step"]

    result = go_back()
    assert result["current_step"] == current - 1


def test_wizard_skip_non_required():
    reset_wizard()
    run_step("identity")
    run_step("system")
    run_step("copilot")
    result = skip_step("smartwatch")
    assert "smartwatch" in result["step_data"] or result["current_step"] > 4


def test_wizard_reset():
    reset_wizard()
    run_step("identity")
    result = reset_wizard()
    assert result["started"] is False
    assert result["completed"] is False
    assert result["progress"] == 0.0


def test_wizard_unknown_step():
    reset_wizard()
    result = run_step("nonexistent")
    assert result["step_data"].get("nonexistent", {}).get("error")


def test_setup_status():
    status = setup_status()
    assert "completed" in status
    assert status["completed"] is False or status["completed"] is True


def test_is_setup_complete():
    result = is_setup_complete()
    assert isinstance(result, bool)
