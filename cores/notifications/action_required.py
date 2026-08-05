"""Action Required — structured notifications for manual interventions.

When the system needs human intervention, it creates an ActionRequired with:
- Precise description of what happened
- Why manual intervention is needed
- Exact steps to resolve (numbered)
- UI path where the action can be taken
- Priority/urgency
- Direct link/route to resolve
- Category (credentials, review, approval, funding, health, scope, config)

Usage::

    from cores.notifications.action_required import notify_action_required

    notify_action_required(
        title="API Key missing for HackerOne",
        reason="Cannot submit reports to HackerOne without API key",
        impact="3 reports queued, unable to submit",
        steps=[
            "Open Settings > API Keys",
            "Click 'Add' next to HackerOne",
            "Enter your HACKERONE_API_KEY",
            "Click 'Verify' to confirm",
        ],
        ui_path="/settings?tab=apikeys",
        category="credentials",
        priority="high",
        channels=["web", "desktop", "discord"],
        subject_id="hackerone",
        subject_type="platform",
    )
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cores.notifications.hub import Notification, get_hub

logger = logging.getLogger("ownex.notifications.action_required")


ACTION_CATEGORIES = {
    "credentials": {
        "label": "Credentials",
        "icon": "Key",
        "color": "#F59E0B",
        "description": "API keys, tokens, or credentials needed",
    },
    "review": {
        "label": "Review Required",
        "icon": "Eye",
        "color": "#3B82F6",
        "description": "Manual review of automated output needed",
    },
    "approval": {
        "label": "Approval Needed",
        "icon": "CheckCircle",
        "color": "#10B981",
        "description": "Explicit approval required to proceed",
    },
    "funding": {
        "label": "Funding Needed",
        "icon": "DollarSign",
        "color": "#EF4444",
        "description": "Capital or funding action required",
    },
    "health": {
        "label": "System Health",
        "icon": "HeartPulse",
        "color": "#EF4444",
        "description": "System component unhealthy or stalled",
    },
    "scope": {
        "label": "Scope Verification",
        "icon": "Target",
        "color": "#8B5CF6",
        "description": "Target scope needs verification",
    },
    "config": {
        "label": "Configuration",
        "icon": "Settings",
        "color": "#6B7280",
        "description": "System configuration needed",
    },
    "escalation": {
        "label": "Escalation",
        "icon": "AlertTriangle",
        "color": "#DC2626",
        "description": "Previous action ignored, escalated",
    },
}

PRIORITY_LABELS = {
    "critical": {"label": "CRITICAL", "color": "#DC2626", "max_snooze_minutes": 0},
    "high": {"label": "HIGH", "color": "#EF4444", "max_snooze_minutes": 30},
    "medium": {"label": "MEDIUM", "color": "#F59E0B", "max_snooze_minutes": 120},
    "low": {"label": "LOW", "color": "#6B7280", "max_snooze_minutes": 480},
}


@dataclass
class ActionRequired:
    """A structured action-required notification."""

    id: str = field(default_factory=lambda: f"ar-{uuid.uuid4().hex[:12]}")
    title: str = ""
    reason: str = ""
    impact: str = ""
    steps: list[str] = field(default_factory=list)
    ui_path: str = ""
    category: str = "config"
    priority: str = "medium"
    channels: list[str] = field(default_factory=lambda: ["web"])
    subject_id: str = ""
    subject_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    resolved: bool = False
    resolved_at: str | None = None
    snoozed_until: str | None = None
    escalation_count: int = 0

    def to_notification(self) -> Notification:
        """Convert to a Notification for the hub."""
        category_info = ACTION_CATEGORIES.get(self.category, ACTION_CATEGORIES["config"])

        # Build structured message with clear steps
        parts = []
        if self.reason:
            parts.append(f"**Why:** {self.reason}")
        if self.impact:
            parts.append(f"**Impact:** {self.impact}")
        if self.steps:
            parts.append("\n**What to do:**")
            for i, step in enumerate(self.steps, 1):
                parts.append(f"{i}. {step}")
        if self.ui_path:
            parts.append(f"\n**Go to:** {self.ui_path}")

        message = "\n".join(parts)

        return Notification(
            id=self.id,
            type="action_required",
            title=f"[{category_info['label']}] {self.title}",
            message=message,
            severity=self.priority,
            priority=self.priority,
            channels=self.channels,
            metadata={
                "action_id": self.id,
                "category": self.category,
                "ui_path": self.ui_path,
                "steps": self.steps,
                "subject_id": self.subject_id,
                "subject_type": self.subject_type,
                "created_at": self.created_at,
                "escalation_count": self.escalation_count,
                **self.metadata,
            },
            dedup_key=f"action_required:{self.subject_type}:{self.subject_id}:{self.category}",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "reason": self.reason,
            "impact": self.impact,
            "steps": self.steps,
            "ui_path": self.ui_path,
            "category": self.category,
            "priority": self.priority,
            "channels": self.channels,
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at,
            "snoozed_until": self.snoozed_until,
            "escalation_count": self.escalation_count,
        }


# ── Registry of pending actions ─────────────────────────────────

_PENDING_ACTIONS: dict[str, ActionRequired] = {}


def register_action(action: ActionRequired) -> ActionRequired:
    """Register an action as pending and send notification."""
    _PENDING_ACTIONS[action.id] = action
    notif = action.to_notification()
    get_hub().send(notif)
    logger.info(
        "[ACTION_REQUIRED] %s | %s | %s | path=%s",
        action.priority.upper(),
        action.category,
        action.title,
        action.ui_path,
    )
    return action


def resolve_action(action_id: str) -> ActionRequired | None:
    """Mark an action as resolved."""
    action = _PENDING_ACTIONS.get(action_id)
    if action:
        action.resolved = True
        action.resolved_at = datetime.now(UTC).isoformat()
        logger.info("[ACTION_RESOLVED] %s: %s", action_id, action.title)
    return action


def get_pending_actions(
    category: str | None = None,
    priority: str | None = None,
) -> list[ActionRequired]:
    """Get all unresolved actions, optionally filtered."""
    actions = [a for a in _PENDING_ACTIONS.values() if not a.resolved]
    if category:
        actions = [a for a in actions if a.category == category]
    if priority:
        actions = [a for a in actions if a.priority == priority]
    return sorted(actions, key=lambda a: a.created_at, reverse=True)


# ── Convenience functions for common interventions ───────────────


def notify_credentials_missing(
    platform: str,
    credential_name: str,
    impact: str = "",
    docs_url: str = "",
) -> ActionRequired:
    """Notify that API credentials are missing."""
    steps = [
        "Go to Settings > API Keys",
        f"Find {platform} section",
        f"Enter your {credential_name}",
        "Click 'Verify' to confirm",
    ]
    if docs_url:
        steps.append(f"Docs: {docs_url}")

    return register_action(
        ActionRequired(
            title=f"API Key missing for {platform}",
            reason=f"Cannot authenticate with {platform} API",
            impact=impact or f"Operations requiring {platform} are paused",
            steps=steps,
            ui_path="/settings?tab=apikeys",
            category="credentials",
            priority="high",
            channels=["web", "desktop", "discord"],
            subject_id=platform,
            subject_type="platform",
        )
    )


def notify_scope_unverified(
    target_name: str,
    platform: str,
    target_id: int | None = None,
) -> ActionRequired:
    """Notify that target scope needs verification."""
    return register_action(
        ActionRequired(
            title=f"Scope unverified: {target_name}",
            reason="Target added but scope not verified — risk of out-of-scope testing",
            impact="All findings may be rejected if target is out of scope",
            steps=[
                f"Go to Targets > {target_name}",
                "Click 'Verify Scope' button",
                f"Confirm scope matches {platform} program rules",
                "Mark as 'In Scope' or remove target",
            ],
            ui_path=f"/targets/{target_id}" if target_id else "/targets",
            category="scope",
            priority="medium",
            channels=["web"],
            subject_id=str(target_id) if target_id else target_name,
            subject_type="target",
        )
    )


def notify_review_required(
    title: str,
    reason: str,
    ui_path: str,
    subject_id: str = "",
    subject_type: str = "",
    steps: list[str] | None = None,
    priority: str = "medium",
) -> ActionRequired:
    """Notify that manual review is needed."""
    default_steps = [
        f"Go to {ui_path}",
        "Review the flagged item",
        "Approve, reject, or request changes",
    ]
    return register_action(
        ActionRequired(
            title=title,
            reason=reason,
            impact="Item queued pending manual review",
            steps=steps or default_steps,
            ui_path=ui_path,
            category="review",
            priority=priority,
            channels=["web", "desktop"],
            subject_id=subject_id,
            subject_type=subject_type,
        )
    )


def notify_funding_needed(
    adapter_name: str,
    current_balance: float,
    minimum_needed: float,
) -> ActionRequired:
    """Notify that investment adapter needs funding."""
    return register_action(
        ActionRequired(
            title=f"Funding needed: {adapter_name}",
            reason=f"Balance ({current_balance}) below minimum ({minimum_needed})",
            impact=f"Adapter {adapter_name} is paused until funded",
            steps=[
                f"Go to Investment Hub > {adapter_name}",
                "Click 'Add Capital' button",
                f"Enter amount (minimum {minimum_needed})",
                "Confirm allocation",
            ],
            ui_path=f"/investments?tab={adapter_name}",
            category="funding",
            priority="high",
            channels=["web", "desktop", "discord"],
            subject_id=adapter_name,
            subject_type="adapter",
        )
    )


def notify_system_stalled(
    component: str,
    reason: str,
    impact: str,
    resolution_steps: list[str],
) -> ActionRequired:
    """Notify that a system component is stalled."""
    return register_action(
        ActionRequired(
            title=f"System stalled: {component}",
            reason=reason,
            impact=impact,
            steps=resolution_steps,
            ui_path="/operations/health",
            category="health",
            priority="critical",
            channels=["web", "desktop", "discord", "whatsapp"],
            subject_id=component,
            subject_type="component",
        )
    )


def notify_action_required(
    title: str,
    reason: str,
    impact: str,
    steps: list[str],
    ui_path: str,
    category: str = "config",
    priority: str = "medium",
    channels: list[str] | None = None,
    subject_id: str = "",
    subject_type: str = "",
    metadata: dict[str, Any] | None = None,
) -> ActionRequired:
    """Generic action-required notification."""
    return register_action(
        ActionRequired(
            title=title,
            reason=reason,
            impact=impact,
            steps=steps,
            ui_path=ui_path,
            category=category,
            priority=priority,
            channels=channels or ["web"],
            subject_id=subject_id,
            subject_type=subject_type,
            metadata=metadata or {},
        )
    )


# ── Escalation ──────────────────────────────────────────────────


def escalate_ignored_actions(max_age_minutes: int = 60) -> list[ActionRequired]:
    """Escalate actions that have been ignored beyond threshold."""
    escalated: list[ActionRequired] = []
    now = datetime.now(UTC)

    for action in _PENDING_ACTIONS.values():
        if action.resolved:
            continue
        if action.escalation_count >= 3:
            continue

        created = datetime.fromisoformat(action.created_at)
        age_minutes = (now - created).total_seconds() / 60

        if age_minutes < max_age_minutes:
            continue

        # Check if snoozed
        if action.snoozed_until:
            snoozed = datetime.fromisoformat(action.snoozed_until)
            if now < snoozed:
                continue

        action.escalation_count += 1

        # Escalate priority
        if action.priority == "low":
            action.priority = "medium"
        elif action.priority == "medium":
            action.priority = "high"
        elif action.priority == "high":
            action.priority = "critical"

        # Add escalation channel
        if "discord" not in action.channels:
            action.channels.append("discord")
        if action.priority == "critical" and "whatsapp" not in action.channels:
            action.channels.append("whatsapp")

        # Re-send with escalation note
        escalated_action = ActionRequired(
            id=f"{action.id}-esc{action.escalation_count}",
            title=f"ESCALATED ({action.escalation_count}x): {action.title}",
            reason=action.reason,
            impact=f"IGNORED for {int(age_minutes)} minutes. {action.impact}",
            steps=action.steps,
            ui_path=action.ui_path,
            category="escalation" if action.escalation_count >= 2 else action.category,
            priority=action.priority,
            channels=action.channels,
            subject_id=action.subject_id,
            subject_type=action.subject_type,
            metadata={**action.metadata, "escalated_from": action.id},
        )
        register_action(escalated_action)
        escalated.append(escalated_action)

        logger.warning(
            "[ESCALATION] Action %s ignored for %d min, escalated to %s (count=%d)",
            action.id,
            int(age_minutes),
            action.priority,
            action.escalation_count,
        )

    return escalated
