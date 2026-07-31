from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.setup.models import WizardStepDef

_STEP_REGISTRY: dict[str, WizardStepDef] = {}


def define_step(
    step_id: str,
    label: str,
    description: str,
    icon: str = "circle",
    order: int = 0,
    required: bool = True,
    schema: dict[str, Any] | None = None,
) -> Callable[[Callable[..., dict[str, Any]]], Callable[..., dict[str, Any]]]:
    def decorator(fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
        _STEP_REGISTRY[step_id] = WizardStepDef(
            step_id=step_id,
            label=label,
            description=description,
            icon=icon,
            order=order,
            required=required,
            execute_fn=fn,
            schema=schema,
        )
        return fn

    return decorator


def get_step(step_id: str) -> WizardStepDef | None:
    return _STEP_REGISTRY.get(step_id)


def get_all_steps() -> list[WizardStepDef]:
    return sorted(_STEP_REGISTRY.values(), key=lambda s: s.order)


def register_step(defn: WizardStepDef) -> None:
    _STEP_REGISTRY[defn.step_id] = defn


def clear_steps() -> None:
    _STEP_REGISTRY.clear()


def count_steps() -> int:
    return len(_STEP_REGISTRY)


# Import steps explicitly to register them
from core.setup.steps.copilot_step import copilot_step  # noqa: E402
from core.setup.steps.identity_step import identity_step  # noqa: E402
from core.setup.steps.integrations_step import integrations_step  # noqa: E402
from core.setup.steps.personalization_step import personalization_step  # noqa: E402
from core.setup.steps.smartwatch_step import smartwatch_step  # noqa: E402
from core.setup.steps.system_step import system_step  # noqa: E402
from core.setup.steps.test_step import test_step  # noqa: E402
