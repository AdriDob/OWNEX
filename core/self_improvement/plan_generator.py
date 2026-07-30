"""Improvement Plan Generator — AI-powered reasoning to generate actionable improvements."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.self_improvement.reflection import (
    IssueType,
    Reflection,
    SelfReflectionEngine,
    Severity,
    get_reflection_engine,
)

logger = logging.getLogger("ownex.self_improvement.plan_generator")


@dataclass
class ImprovementAction:
    """A specific action to implement an improvement."""
    id: str
    reflection_id: str
    action_type: str  # "add_file", "modify_file", "add_config", "add_dependency", "add_test"
    target: str  # file path or config key
    description: str
    code_snippet: str | None = None
    priority: int = 5
    estimated_effort: str = "medium"  # low, medium, high
    status: str = "pending"  # pending, approved, implemented, rejected
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "reflection_id": self.reflection_id,
            "action_type": self.action_type,
            "target": self.target,
            "description": self.description,
            "code_snippet": self.code_snippet,
            "priority": self.priority,
            "estimated_effort": self.estimated_effort,
            "status": self.status,
            "created_at": self.created_at,
        }


class ImprovementPlanGenerator:
    """Generate actionable improvement plans from reflections."""

    def __init__(self, storage_path: str | Path = "~/.config/ownex/improvement_plan.json"):
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._actions: list[ImprovementAction] = []
        self._load_actions()

    def _load_actions(self) -> None:
        """Load improvement actions from storage."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                self._actions = [
                    ImprovementAction(
                        id=a["id"],
                        reflection_id=a["reflection_id"],
                        action_type=a["action_type"],
                        target=a["target"],
                        description=a["description"],
                        code_snippet=a.get("code_snippet"),
                        priority=a["priority"],
                        estimated_effort=a["estimated_effort"],
                        status=a["status"],
                        created_at=a["created_at"],
                    )
                    for a in data
                ]
                logger.info(f"Loaded {len(self._actions)} improvement actions")
            except Exception as e:
                logger.warning(f"Failed to load improvement actions: {e}")

    def _save_actions(self) -> None:
        """Save improvement actions to storage."""
        try:
            data = [a.to_dict() for a in self._actions]
            self.storage_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save improvement actions: {e}")

    def generate_actions_from_reflection(self, reflection: Reflection) -> list[ImprovementAction]:
        """Generate improvement actions from a reflection using AI reasoning."""
        actions = []

        # Pattern-based action generation (can be enhanced with AI)
        if reflection.issue_type == IssueType.API_FAILURE:
            if "API key" in reflection.failure.lower():
                actions.append(
                    ImprovementAction(
                        id=f"act_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_1",
                        reflection_id=reflection.id,
                        action_type="add_config",
                        target="~/.config/ownex/opportunity.env",
                        description=f"Add {reflection.metadata.get('platform', 'platform')} API key configuration",
                        code_snippet=f"{reflection.metadata.get('platform', 'PLATFORM').upper()}_API_KEY=your_api_key_here",
                        priority=8,
                        estimated_effort="low",
                    )
                )
            else:
                actions.append(
                    ImprovementAction(
                        id=f"act_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_1",
                        reflection_id=reflection.id,
                        action_type="modify_file",
                        target="core/task_hub/sync.py",
                        description=f"Add error handling for {reflection.metadata.get('platform', 'platform')} API",
                        code_snippet="# Add try/except with retry logic",
                        priority=7,
                        estimated_effort="medium",
                    )
                )

        elif reflection.issue_type == IssueType.MISSING_FEATURE:
            actions.append(
                ImprovementAction(
                    id=f"act_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_1",
                    reflection_id=reflection.id,
                    action_type="add_file",
                    target=f"core/opportunity/adapters/{reflection.metadata.get('platform', 'new_platform')}.py",
                    description=f"Create adapter for {reflection.metadata.get('platform', 'new_platform')} platform",
                    code_snippet="# Implement platform adapter",
                    priority=6,
                    estimated_effort="high",
                )
            )

        elif reflection.issue_type == IssueType.USER_REJECTED:
            actions.append(
                ImprovementAction(
                    id=f"act_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_1",
                    reflection_id=reflection.id,
                    action_type="modify_file",
                    target="core/opportunity/guides/platform_guides.py",
                    description=f"Update guide for {reflection.metadata.get('platform', 'platform')} with better instructions",
                    code_snippet="# Add more detailed steps",
                    priority=5,
                    estimated_effort="medium",
                )
            )

        elif reflection.issue_type == IssueType.ERROR:
            actions.append(
                ImprovementAction(
                    id=f"act_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_1",
                    reflection_id=reflection.id,
                    action_type="add_test",
                    target=f"tests/test_{reflection.metadata.get('module', 'module')}.py",
                    description=f"Add test case for {reflection.metadata.get('module', 'module')} to prevent regression",
                    code_snippet="# Add test case",
                    priority=8,
                    estimated_effort="medium",
                )
            )

        elif reflection.issue_type == IssueType.LIMITATION:
            actions.append(
                ImprovementAction(
                    id=f"act_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_1",
                    reflection_id=reflection.id,
                    action_type="modify_file",
                    target="core/ai/model_router.py",
                    description="Add fallback models for better reasoning",
                    code_snippet="# Add more model options",
                    priority=4,
                    estimated_effort="low",
                )
            )

        # Add actions to storage
        for action in actions:
            self._actions.append(action)

        self._save_actions()
        logger.info(f"Generated {len(actions)} actions from reflection {reflection.id}")
        return actions

    def get_pending_actions(self) -> list[ImprovementAction]:
        """Get all pending improvement actions."""
        return [a for a in self._actions if a.status == "pending"]

    def get_high_priority_actions(self, limit: int = 10) -> list[ImprovementAction]:
        """Get highest priority pending actions."""
        pending = self.get_pending_actions()
        return sorted(pending, key=lambda a: a.priority, reverse=True)[:limit]

    def update_action_status(self, action_id: str, new_status: str) -> bool:
        """Update status of an action."""
        for a in self._actions:
            if a.id == action_id:
                a.status = new_status
                self._save_actions()
                return True
        return False

    def auto_generate_plan(self) -> dict[str, Any]:
        """Auto-generate improvement plan from all pending reflections."""
        reflection_engine = get_reflection_engine()
        pending_reflections = reflection_engine.get_pending_reflections()

        for reflection in pending_reflections:
            # Only generate actions if not already generated
            existing = [a for a in self._actions if a.reflection_id == reflection.id]
            if not existing:
                self.generate_actions_from_reflection(reflection)

        return {
            "total_actions": len(self._actions),
            "pending_actions": len(self.get_pending_actions()),
            "high_priority": len(self.get_high_priority_actions()),
        }


_plan_generator: ImprovementPlanGenerator | None = None


def get_plan_generator() -> ImprovementPlanGenerator:
    """Get singleton improvement plan generator."""
    global _plan_generator
    if _plan_generator is None:
        _plan_generator = ImprovementPlanGenerator()
    return _plan_generator
