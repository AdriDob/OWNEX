from __future__ import annotations

import json
import logging
import time
from typing import Any

from core import OWNEX_DIR
from core.setup.models import STEP_STATUS_COMPLETED, STEP_STATUS_FAILED, WizardState
from core.setup.steps import get_all_steps, get_step

logger = logging.getLogger("ownex.core.setup.wizard")

WIZARD_STATE_PATH = OWNEX_DIR / "config" / "wizard_state.json"
WIZARD_CONFIG_PATH = OWNEX_DIR / "config" / "wizard.json"


def _load_state() -> WizardState:
    if WIZARD_STATE_PATH.exists():
        try:
            raw = json.loads(WIZARD_STATE_PATH.read_text())
            return WizardState(
                current_step_index=raw.get("current_step_index", 0),
                started=raw.get("started", False),
                completed=raw.get("completed", False),
                started_at=raw.get("started_at"),
                completed_at=raw.get("completed_at"),
                step_data=raw.get("step_data", {}),
                step_status=raw.get("step_status", {}),
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load wizard state: %s", exc)
    return WizardState()


def _save_state(state: WizardState) -> None:
    try:
        OWNEX_DIR.mkdir(parents=True, exist_ok=True)
        (OWNEX_DIR / "config").mkdir(parents=True, exist_ok=True)
        WIZARD_STATE_PATH.write_text(
            json.dumps(
                {
                    "current_step_index": state.current_step_index,
                    "started": state.started,
                    "completed": state.completed,
                    "started_at": state.started_at,
                    "completed_at": state.completed_at,
                    "step_data": state.step_data,
                    "step_status": state.step_status,
                },
                indent=2,
            )
        )
    except OSError as exc:
        logger.error("Failed to save wizard state: %s", exc)


def _save_config(state: WizardState) -> None:
    try:
        OWNEX_DIR.mkdir(parents=True, exist_ok=True)
        (OWNEX_DIR / "config").mkdir(parents=True, exist_ok=True)
        WIZARD_CONFIG_PATH.write_text(json.dumps(state.get_config(), indent=2))
    except OSError as exc:
        logger.error("Failed to save wizard config: %s", exc)


_STATE: WizardState | None = None


def _get_state() -> WizardState:
    global _STATE
    if _STATE is None:
        _STATE = _load_state()
    return _STATE


def _reset_state() -> None:
    global _STATE
    _STATE = WizardState()
    _save_state(_STATE)


def wizard_status() -> dict[str, Any]:
    state = _get_state()
    steps = get_all_steps()
    return state.to_dict(steps)


def get_wizard_progress() -> float:
    state = _get_state()
    steps = get_all_steps()
    if state.completed:
        return 100.0
    if not state.started:
        return 0.0
    total = len(steps)
    if total == 0:
        return 0.0
    return round((state.current_step_index / total) * 100, 1)


def run_step(step_id: str | None = None, step_data: dict[str, Any] | None = None) -> dict[str, Any]:
    state = _get_state()
    steps = get_all_steps()

    if not steps:
        return {"status": "error", "message": "No hay pasos registrados en el wizard"}

    state.started = True
    if state.started_at is None:
        state.started_at = time.time()

    if not step_id:
        step_id = (
            steps[state.current_step_index].step_id if state.current_step_index < len(steps) else steps[-1].step_id
        )

    if step_id == "finish":
        return _complete_wizard(state, steps)

    step_def = get_step(step_id)
    if not step_def:
        state.mark_step(step_id, STEP_STATUS_FAILED, {"error": f"Paso desconocido: {step_id}"})
        _save_state(state)
        return state.to_dict(steps)

    if not step_def.execute_fn:
        state.mark_step(step_id, STEP_STATUS_FAILED, {"error": f"Paso {step_id} no tiene función execute"})
        _save_state(state)
        return state.to_dict(steps)

    step_input = {**(step_data or {}), **state.step_data.get(step_id, {})}
    try:
        result = step_def.execute_fn(step_input)
    except Exception as exc:
        logger.error("Wizard step '%s' crashed: %s", step_id, exc)
        state.mark_step(step_id, STEP_STATUS_FAILED, {"error": str(exc)})
        _save_state(state)
        return state.to_dict(steps)

    result_status = result.get("status", "ok")
    if result_status == "error":
        state.mark_step(step_id, STEP_STATUS_FAILED, result.get("data", {}))
        logger.warning("Wizard step '%s' failed: %s", step_id, result.get("message", ""))
    else:
        state.mark_step(step_id, STEP_STATUS_COMPLETED, result.get("data", {}))
        next_idx = state.current_step_index + 1
        if next_idx < len(steps):
            state.current_step_index = next_idx
        else:
            state.current_step_index = len(steps) - 1

    _save_state(state)
    return state.to_dict(steps)


def go_back() -> dict[str, Any]:
    state = _get_state()
    steps = get_all_steps()
    if state.current_step_index > 0:
        state.current_step_index -= 1
        _save_state(state)
    return state.to_dict(steps)


def skip_step(step_id: str) -> dict[str, Any]:
    state = _get_state()
    steps = get_all_steps()
    step_def = get_step(step_id)
    if step_def and step_def.required:
        return {
            "status": "error",
            "message": f"El paso '{step_def.label}' es obligatorio y no puede saltarse",
            **state.to_dict(steps),
        }
    if step_def:
        state.mark_step(step_id, STEP_STATUS_FAILED, {"skipped": True})
        next_idx = state.current_step_index + 1
        if next_idx < len(steps):
            state.current_step_index = next_idx
        _save_state(state)
    return state.to_dict(steps)


def _complete_wizard(state: WizardState, steps: list) -> dict[str, Any]:
    state.completed = True
    state.completed_at = time.time()
    state.current_step_index = len(steps)

    for s in steps:
        if s.step_id not in state.step_status:
            state.step_status[s.step_id] = STEP_STATUS_COMPLETED
        if s.step_id not in state.step_data:
            state.step_data[s.step_id] = {}

    config = state.get_config()
    config["summary"] = _build_summary(state, steps)

    try:
        OWNEX_DIR.mkdir(parents=True, exist_ok=True)
        (OWNEX_DIR / "config").mkdir(parents=True, exist_ok=True)
        WIZARD_CONFIG_PATH.write_text(json.dumps(config, indent=2))
    except OSError as exc:
        logger.error("Failed to save wizard config: %s", exc)

    _save_state(state)

    duration = state.completed_at - (state.started_at or state.completed_at)
    logger.info("Wizard completed in %.1fs", duration)

    return state.to_dict(steps)


def _build_summary(state: WizardState, steps: list) -> dict[str, Any]:
    completed = sum(1 for s in steps if state.step_status.get(s.step_id) == STEP_STATUS_COMPLETED)
    failed = sum(1 for s in steps if state.step_status.get(s.step_id) == STEP_STATUS_FAILED)
    total = len(steps)

    identity_data = state.step_data.get("identity", {})
    system_data = state.step_data.get("system", {})
    copilot_data = state.step_data.get("copilot", {})

    return {
        "total_steps": total,
        "completed": completed,
        "failed": failed,
        "username": identity_data.get("username", ""),
        "role": identity_data.get("role", ""),
        "authority_level": copilot_data.get("authority_level", ""),
        "system_ok": system_data.get("ok", 0),
        "system_warnings": system_data.get("warnings", 0),
        "system_errors": system_data.get("errors", 0),
    }


def reset_wizard() -> dict[str, Any]:
    _reset_state()
    steps = get_all_steps()
    return _get_state().to_dict(steps)
