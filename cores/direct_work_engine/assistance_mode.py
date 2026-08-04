"""Guided Assistance System — mode switcher for OWNEX Alpha.

Four modes control how much OWNEX explains and what requires user approval:

- GUIDED:     explain everything, ask before each step (onboarding / first use).
- ASSISTED:   explain important decisions only (default for most users).
- AUTONOMOUS: execute approved workflows without interruption (trusted user).
- EXPERT:     show technical details, skip explanations (power user).

The current mode is persisted in UnifiedMemoryStore (namespace ``user``, key
``assistance_mode``) so it survives backend restarts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from core.memory.store import get_memory_store


class AssistanceMode(StrEnum):
    GUIDED = "guided"
    ASSISTED = "assisted"
    AUTONOMOUS = "autonomous"
    EXPERT = "expert"


MODES: dict[str, AssistanceMode] = {m.value: m for m in AssistanceMode}

GUIDANCE: dict[str, dict[str, Any]] = {
    AssistanceMode.GUIDED.value: {
        "label": "Guided",
        "description": "OWNEX explains every step and asks for your approval before proceeding.",
        "explain_plan": True,
        "explain_tools": True,
        "explain_verification": True,
        "auto_approve": False,
        "show_technical_details": False,
        "next_button_text": "Approve and continue",
    },
    AssistanceMode.ASSISTED.value: {
        "label": "Assisted",
        "description": "OWNEX explains important decisions and lets you review the plan before execution.",
        "explain_plan": True,
        "explain_tools": False,
        "explain_verification": True,
        "auto_approve": False,
        "show_technical_details": False,
        "next_button_text": "Review and approve",
    },
    AssistanceMode.AUTONOMOUS.value: {
        "label": "Autonomous",
        "description": "OWNEX executes approved workflows without interruption. You review the result.",
        "explain_plan": False,
        "explain_tools": False,
        "explain_verification": False,
        "auto_approve": True,
        "show_technical_details": False,
        "next_button_text": "Run autonomously",
    },
    AssistanceMode.EXPERT.value: {
        "label": "Expert",
        "description": "Technical details only. Minimal explanation, maximum control.",
        "explain_plan": False,
        "explain_tools": True,
        "explain_verification": False,
        "auto_approve": False,
        "show_technical_details": True,
        "next_button_text": "Execute",
    },
}

MEMORY_NAMESPACE = "user"
MEMORY_KEY = "assistance_mode"


def get_mode() -> AssistanceMode:
    store = get_memory_store()
    entry = store.get(MEMORY_NAMESPACE, MEMORY_KEY)
    if entry and isinstance(entry.get("content"), str):
        mode = MODES.get(entry["content"])
        if mode is not None:
            return mode
    return AssistanceMode.ASSISTED


def set_mode(mode: str) -> AssistanceMode:
    m = MODES.get(str(mode).lower())
    if m is None:
        raise ValueError(f"Invalid mode '{mode}'. Valid: {', '.join(MODES)}")
    store = get_memory_store()
    store.store(
        namespace=MEMORY_NAMESPACE,
        key=MEMORY_KEY,
        content=str(m),
        tags=["assistance_mode", "user_preference"],
        priority=2.0,
    )
    return m


def get_guidance(mode: AssistanceMode | str | None = None) -> dict[str, Any]:
    """Return the guidance configuration for a mode (or the current mode if None)."""
    key = (mode or get_mode()).value if isinstance(mode, AssistanceMode) else str(mode or get_mode().value)
    return GUIDANCE.get(key, GUIDANCE[AssistanceMode.ASSISTED.value])


@dataclass
class ModeInfo:
    current: str
    label: str
    description: str
    explain_plan: bool
    explain_tools: bool
    explain_verification: bool
    auto_approve: bool
    show_technical_details: bool
    next_button_text: str

    @classmethod
    def from_current(cls) -> ModeInfo:
        mode = get_mode()
        g = GUIDANCE[mode.value]
        return cls(
            current=mode.value,
            label=g["label"],
            description=g["description"],
            explain_plan=g["explain_plan"],
            explain_tools=g["explain_tools"],
            explain_verification=g["explain_verification"],
            auto_approve=g["auto_approve"],
            show_technical_details=g["show_technical_details"],
            next_button_text=g["next_button_text"],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
