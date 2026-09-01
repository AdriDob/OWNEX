"""Platform Form Mapper — Maps platform UIs to fillable form fields.

This module provides the intelligence layer for Computer Use to fill web forms
on bug bounty and freelance platforms. It stores platform-specific knowledge
(login flows, submission forms, field positions) so that Computer Use can
execute tasks without re-learning the UI every time.

Architecture:
    PlatformTemplate (static knowledge) → Computer Use (dynamic execution) → Submission

Each platform template defines:
    - Login flow (steps to authenticate)
    - Submission form (fields, selectors, flow)
    - Confirmation detection (how to know submission succeeded)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.computer_use.platform_forms")


class FieldKind(StrEnum):
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    FILE = "file"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    BUTTON = "button"
    DROPDOWN = "dropdown"


@dataclass
class FormField:
    """A single field in a platform submission form."""

    name: str  # logical name (e.g., "title", "description", "severity")
    kind: FieldKind = FieldKind.TEXT
    label: str = ""  # visible label text to look for
    placeholder: str = ""  # placeholder text
    required: bool = True
    default_value: str = ""  # pre-fill value
    options: list[str] = field(default_factory=list)  # for select/radio
    css_selector: str = ""  # optional CSS selector override
    coordinates: tuple[int, int] | None = None  # optional pixel coordinates
    fill_strategy: str = "label"  # "label" | "selector" | "coordinates" | "tab_order"

    def to_dict(self) -> dict[str, Any]:
        d = {
            "name": self.name,
            "kind": self.kind.value,
            "label": self.label,
            "required": self.required,
            "fill_strategy": self.fill_strategy,
        }
        if self.placeholder:
            d["placeholder"] = self.placeholder
        if self.options:
            d["options"] = self.options
        if self.css_selector:
            d["css_selector"] = self.css_selector
        if self.coordinates:
            d["coordinates"] = list(self.coordinates)
        return d


@dataclass
class PlatformTemplate:
    """Complete UI template for a platform's submission flow."""

    platform_id: str
    platform_name: str
    submission_url: str  # URL to navigate to for submission
    login_url: str = ""
    login_fields: list[FormField] = field(default_factory=list)
    submission_fields: list[FormField] = field(default_factory=list)
    submit_button: str = "Submit"  # text of submit button
    success_indicators: list[str] = field(default_factory=list)  # text to look for on success
    error_indicators: list[str] = field(default_factory=list)  # text to look for on error
    notes: str = ""
    version: str = "1.0"
    last_verified: str = ""  # ISO date of last manual verification

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform_id": self.platform_id,
            "platform_name": self.platform_name,
            "submission_url": self.submission_url,
            "login_url": self.login_url,
            "login_fields": [f.to_dict() for f in self.login_fields],
            "submission_fields": [f.to_dict() for f in self.submission_fields],
            "submit_button": self.submit_button,
            "success_indicators": self.success_indicators,
            "error_indicators": self.error_indicators,
            "notes": self.notes,
            "version": self.version,
            "last_verified": self.last_verified,
        }


# ── Built-in Platform Templates ───────────────────────────────────

_BUILTIN_TEMPLATES: dict[str, PlatformTemplate] = {}


def _register_builtin(template: PlatformTemplate) -> None:
    _BUILTIN_TEMPLATES[template.platform_id] = template


# HackerOne — API-based (no form filling needed, but template for reference)
_register_builtin(
    PlatformTemplate(
        platform_id="hackerone",
        platform_name="HackerOne",
        submission_url="https://hackerone.com/programs",
        login_url="https://hackerone.com/login",
        login_fields=[
            FormField(name="email", kind=FieldKind.TEXT, label="Email"),
            FormField(name="password", kind=FieldKind.TEXT, label="Password"),
        ],
        submission_fields=[
            FormField(name="program", kind=FieldKind.DROPDOWN, label="Program"),
            FormField(name="vulnerability_title", kind=FieldKind.TEXT, label="Title"),
            FormField(name="vulnerability_report", kind=FieldKind.TEXTAREA, label="Report"),
            FormField(
                name="severity",
                kind=FieldKind.SELECT,
                label="Severity",
                options=["critical", "high", "medium", "low", "informational"],
            ),
        ],
        submit_button="Submit Report",
        success_indicators=["Report submitted", "Thank you"],
        error_indicators=["Error", "Required field"],
        notes="HackerOne has a REST API — prefer API submission over form filling.",
    )
)

# Bugcrowd — API-based
_register_builtin(
    PlatformTemplate(
        platform_id="bugcrowd",
        platform_name="Bugcrowd",
        submission_url="https://bugcrowd.com/submissions/new",
        login_url="https://bugcrowd.com/login",
        login_fields=[
            FormField(name="email", kind=FieldKind.TEXT, label="Email"),
            FormField(name="password", kind=FieldKind.TEXT, label="Password"),
        ],
        submission_fields=[
            FormField(name="program", kind=FieldKind.DROPDOWN, label="Program"),
            FormField(name="vulnerability_title", kind=FieldKind.TEXT, label="Title"),
            FormField(name="vulnerability_report", kind=FieldKind.TEXTAREA, label="Description"),
            FormField(
                name="severity", kind=FieldKind.SELECT, label="Priority", options=["critical", "high", "medium", "low"]
            ),
        ],
        submit_button="Submit Report",
        success_indicators=["Submission received", "Thank you"],
        error_indicators=["Error", "is required"],
        notes="Bugcrowd has a REST API — prefer API submission.",
    )
)

# Opire — OSS bounties
_register_builtin(
    PlatformTemplate(
        platform_id="opire",
        platform_name="Opire",
        submission_url="https://opire.dev",
        submission_fields=[
            FormField(name="bounty_id", kind=FieldKind.TEXT, label="Bounty"),
            FormField(name="pr_url", kind=FieldKind.TEXT, label="Pull Request URL"),
            FormField(name="description", kind=FieldKind.TEXTAREA, label="Description"),
        ],
        submit_button="Submit",
        success_indicators=["submitted", "success"],
        error_indicators=["error", "failed"],
        notes="Opire has an API adapter — prefer API submission.",
    )
)

# IssueHunt — OSS bounties
_register_builtin(
    PlatformTemplate(
        platform_id="issuehunt",
        platform_name="IssueHunt",
        submission_url="https://issuehunt.io",
        submission_fields=[
            FormField(name="bounty_id", kind=FieldKind.TEXT, label="Issue"),
            FormField(name="pr_url", kind=FieldKind.TEXT, label="Pull Request"),
        ],
        submit_button="Submit PR",
        success_indicators=["submitted", "PR linked"],
        error_indicators=["error"],
        notes="IssueHunt has an API adapter — prefer API submission.",
    )
)

# Outlier — AI training (form-based, no public API)
_register_builtin(
    PlatformTemplate(
        platform_id="outlier",
        platform_name="Outlier",
        submission_url="https://outlier.ai",
        login_url="https://outlier.ai/login",
        login_fields=[
            FormField(name="email", kind=FieldKind.TEXT, label="Email"),
            FormField(name="password", kind=FieldKind.TEXT, label="Password"),
        ],
        submission_fields=[
            FormField(name="task_type", kind=FieldKind.SELECT, label="Task Type"),
            FormField(name="response", kind=FieldKind.TEXTAREA, label="Response"),
        ],
        submit_button="Submit",
        success_indicators=["Thank you", "submitted", "completed"],
        error_indicators=["Error", "required", "invalid"],
        notes="Outlier has no public API. Computer Use form filling is the only automation path.",
    )
)

# Mindrift — AI training (form-based)
_register_builtin(
    PlatformTemplate(
        platform_id="mindrift",
        platform_name="Mindrift",
        submission_url="https://mindrift.ai",
        login_url="https://mindrift.ai/login",
        login_fields=[
            FormField(name="email", kind=FieldKind.TEXT, label="Email"),
            FormField(name="password", kind=FieldKind.TEXT, label="Password"),
        ],
        submission_fields=[
            FormField(name="task_type", kind=FieldKind.SELECT, label="Task"),
            FormField(name="response", kind=FieldKind.TEXTAREA, label="Response"),
        ],
        submit_button="Submit",
        success_indicators=["Thank you", "completed"],
        error_indicators=["Error", "required"],
        notes="Mindrift has no public API. Computer Use form filling is the only automation path.",
    )
)

# Freelancer — freelance platform (form-based for submissions)
_register_builtin(
    PlatformTemplate(
        platform_id="freelancer",
        platform_name="Freelancer",
        submission_url="https://freelancer.com",
        login_url="https://freelancer.com/login.php",
        login_fields=[
            FormField(name="email", kind=FieldKind.TEXT, label="Email"),
            FormField(name="password", kind=FieldKind.TEXT, label="Password"),
        ],
        submission_fields=[
            FormField(name="project_id", kind=FieldKind.TEXT, label="Project"),
            FormField(name="bid_amount", kind=FieldKind.TEXT, label="Bid Amount"),
            FormField(name="description", kind=FieldKind.TEXTAREA, label="Description"),
            FormField(name="delivery_days", kind=FieldKind.TEXT, label="Delivery Days"),
        ],
        submit_button="Place Bid",
        success_indicators=["Bid placed", "submitted"],
        error_indicators=["Error", "required"],
        notes="Freelancer has an API but many actions require form filling.",
    )
)

# Fiverr — freelance platform
_register_builtin(
    PlatformTemplate(
        platform_id="fiverr",
        platform_name="Fiverr",
        submission_url="https://fiverr.com",
        login_url="https://fiverr.com/login",
        login_fields=[
            FormField(name="email", kind=FieldKind.TEXT, label="Email"),
            FormField(name="password", kind=FieldKind.TEXT, label="Password"),
        ],
        submission_fields=[
            FormField(name="gig_title", kind=FieldKind.TEXT, label="Gig Title"),
            FormField(name="description", kind=FieldKind.TEXTAREA, label="Description"),
            FormField(name="price", kind=FieldKind.TEXT, label="Price"),
        ],
        submit_button="Publish",
        success_indicators=["published", "live"],
        error_indicators=["Error", "required"],
        notes="Fiverr gig creation is form-based.",
    )
)


# ── Template Manager ──────────────────────────────────────────────


class PlatformFormManager:
    """Manages platform form templates — load, save, query, custom templates."""

    def __init__(self, templates_dir: str | Path | None = None):
        self._templates_dir = Path(templates_dir) if templates_dir else Path("data/platform_templates")
        self._templates_dir.mkdir(parents=True, exist_ok=True)
        self._templates: dict[str, PlatformTemplate] = dict(_BUILTIN_TEMPLATES)
        self._load_custom_templates()

    def _load_custom_templates(self) -> None:
        """Load custom templates from disk (overrides builtins)."""
        for f in self._templates_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                template = PlatformTemplate(**data)
                self._templates[template.platform_id] = template
            except Exception as exc:
                logger.warning("Failed to load template %s: %s", f, exc)

    def get_template(self, platform_id: str) -> PlatformTemplate | None:
        """Get template for a platform."""
        return self._templates.get(platform_id)

    def list_templates(self) -> list[dict[str, Any]]:
        """List all available templates."""
        return [t.to_dict() for t in self._templates.values()]

    def save_template(self, template: PlatformTemplate) -> None:
        """Save a custom template to disk."""
        path = self._templates_dir / f"{template.platform_id}.json"
        path.write_text(json.dumps(template.to_dict(), indent=2))
        self._templates[template.platform_id] = template
        logger.info("Saved template for %s to %s", template.platform_id, path)

    def has_template(self, platform_id: str) -> bool:
        """Check if a template exists for a platform."""
        return platform_id in self._templates

    def needs_form_filling(self, platform_id: str) -> bool:
        """Check if a platform requires form filling (no API submission available).

        Platforms with API adapters return False. Platforms that need
        Computer Use for form filling return True.
        """
        # Platforms with API adapters — prefer API
        api_platforms = {"hackerone", "bugcrowd", "intigriti", "yeswehack", "opire", "issuehunt", "algora"}
        if platform_id.lower() in api_platforms:
            return False
        # All others need form filling
        return self.has_template(platform_id)


# ── Form Filling Task Generator ───────────────────────────────────


def generate_filling_task(
    template: PlatformTemplate,
    work_data: dict[str, Any],
    action: str = "submit",
) -> str:
    """Generate a natural-language task for Computer Use to fill a form.

    Args:
        template: Platform form template
        work_data: Data to fill in the form (title, description, severity, etc.)
        action: "login" | "submit" | "both"

    Returns:
        Task string for ComputerUseAgent
    """
    parts: list[str] = []

    if action in ("login", "both") and template.login_url:
        parts.append(f"Navigate to {template.login_url} and log in.")
        for field_ in template.login_fields:
            if field_.name in work_data:
                parts.append(f"Enter '{work_data[field_.name]}' in the {field_.label} field.")
        parts.append("Click the login button.")

    if action in ("submit", "both"):
        if template.submission_url:
            parts.append(f"Navigate to {template.submission_url}.")

        parts.append("Fill in the submission form:")
        for field_ in template.submission_fields:
            value = work_data.get(field_.name, field_.default_value)
            if value:
                if field_.kind == FieldKind.SELECT and field_.options:
                    parts.append(f"  - {field_.label}: select '{value}' from options {field_.options}")
                elif field_.kind == FieldKind.FILE:
                    parts.append(f"  - {field_.label}: upload file from '{value}'")
                else:
                    parts.append(f"  - {field_.label}: enter '{value}'")

        parts.append(f"Click the '{template.submit_button}' button.")
        parts.append(f"Verify success by looking for: {template.success_indicators}")

    return "\n".join(parts)


# ── Singleton ─────────────────────────────────────────────────────

_manager: PlatformFormManager | None = None


def get_platform_form_manager(templates_dir: str | Path | None = None) -> PlatformFormManager:
    """Get or create the platform form manager singleton."""
    global _manager
    if _manager is None:
        _manager = PlatformFormManager(templates_dir)
    return _manager
