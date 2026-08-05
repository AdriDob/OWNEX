"""
OWNEX Guided Mode — Three levels of assistance.

Principiante (Beginner):
- Explains everything step by step
- Asks for confirmation before each action
- Shows reasoning and alternatives
- Teaches as it goes

Normal:
- Helps and automates
- Shows key decisions and progress
- Summarizes actions taken
- Balanced guidance/autonomy

Experto (Expert):
- Shows technical details
- Minimal handholding
- Direct execution
- Assumes knowledge
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class GuidedLevel(str, Enum):
    BEGINNER = "beginner"
    NORMAL = "normal"
    EXPERT = "expert"


@dataclass
class GuidedConfig:
    """Configuration for each guided level."""

    explain_everything: bool
    ask_confirmation: bool
    show_reasoning: bool
    show_alternatives: bool
    show_technical_details: bool
    summarize_actions: bool
    teach_mode: bool
    auto_execute_simple: bool
    progress_detail: str  # "verbose", "summary", "minimal"


GUIDED_CONFIGS: dict[GuidedLevel, GuidedConfig] = {
    GuidedLevel.BEGINNER: GuidedConfig(
        explain_everything=True,
        ask_confirmation=True,
        show_reasoning=True,
        show_alternatives=True,
        show_technical_details=False,
        summarize_actions=True,
        teach_mode=True,
        auto_execute_simple=False,
        progress_detail="verbose",
    ),
    GuidedLevel.NORMAL: GuidedConfig(
        explain_everything=False,
        ask_confirmation=False,
        show_reasoning=True,
        show_alternatives=False,
        show_technical_details=False,
        summarize_actions=True,
        teach_mode=False,
        auto_execute_simple=True,
        progress_detail="summary",
    ),
    GuidedLevel.EXPERT: GuidedConfig(
        explain_everything=False,
        ask_confirmation=False,
        show_reasoning=False,
        show_alternatives=False,
        show_technical_details=True,
        summarize_actions=False,
        teach_mode=False,
        auto_execute_simple=True,
        progress_detail="minimal",
    ),
}


class GuidedModeManager:
    """Manages guided mode behavior."""

    def __init__(self):
        self._current_level = GuidedLevel.NORMAL
        self._user_preferences: dict[str, Any] = {}

    @property
    def current_level(self) -> GuidedLevel:
        return self._current_level

    @property
    def config(self) -> GuidedConfig:
        return GUIDED_CONFIGS[self._current_level]

    def set_level(self, level: GuidedLevel | str) -> None:
        if isinstance(level, str):
            level = GuidedLevel(level.lower())
        self._current_level = level

    def should_explain(self, action_type: str) -> bool:
        """Determine if an action should be explained."""
        return self.config.explain_everything or action_type in (
            "destructive",
            "external",
            "costly",
        )

    def should_confirm(self, action_type: str) -> bool:
        """Determine if confirmation is needed."""
        return self.config.ask_confirmation or action_type in (
            "destructive",
            "external",
            "irreversible",
        )

    def should_show_reasoning(self) -> bool:
        return self.config.show_reasoning

    def should_show_alternatives(self) -> bool:
        return self.config.show_alternatives

    def format_progress(self, message: str, detail: str = "default") -> str:
        """Format progress message based on detail level."""
        if self.config.progress_detail == "verbose":
            return f"🔍 {message}"
        elif self.config.progress_detail == "summary":
            return f"▶ {message}"
        else:  # minimal
            return f"· {message}"

    def format_result(self, result: Any, action_type: str) -> str:
        """Format result based on guided level."""
        if self.config.show_technical_details:
            return str(result)

        if isinstance(result, str):
            if len(result) > 500:
                return result[:500] + "... [truncated]"
            return result

        if isinstance(result, dict):
            summary = {k: v for k, v in result.items() if not k.startswith("_")}
            return str(summary)

        return str(result)

    def get_teaching_tip(self, context: str) -> str | None:
        """Get teaching tip for beginner mode."""
        if not self.config.teach_mode:
            return None

        tips = {
            "tool_usage": "💡 Tip: This tool does X. You can also use it for Y.",
            "planning": "💡 Tip: Breaking tasks into steps helps track progress.",
            "error": "💡 Tip: Errors are normal. Check the logs for details.",
            "confirmation": "💡 Tip: Confirming prevents accidental changes.",
        }
        return tips.get(context)


# Global instance
_guided_manager: GuidedModeManager | None = None


def get_guided_manager() -> GuidedModeManager:
    global _guided_manager
    if _guided_manager is None:
        _guided_manager = GuidedModeManager()
    return _guided_manager


def set_guided_level(level: GuidedLevel | str) -> None:
    get_guided_manager().set_level(level)


def get_guided_level() -> GuidedLevel:
    return get_guided_manager().current_level


def get_guided_config() -> GuidedConfig:
    return get_guided_manager().config
