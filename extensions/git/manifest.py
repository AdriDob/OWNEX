from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="git",
    name="Git Automation",
    version="1.0.0",
    description="Git integration for OWNEX. "
    "Enables automatic commit, diff review, branch management, "
    "and PR creation for code changes made during autonomous workflows.",
    author="OWNEX",
    icon="GitBranch",
    capabilities=[
        Capability(
            id="git_commit",
            name="Git Commit",
            description="Auto-commit changes with contextual messages",
        ),
        Capability(
            id="git_diff",
            name="Git Diff",
            description="Review and validate changes",
        ),
        Capability(
            id="git_pr",
            name="Pull Request",
            description="Create and review pull requests",
        ),
    ],
    hooks={
        "before_publish": "git.hooks.before_publish",
        "after_publish": "git.hooks.after_publish",
    },
    dependencies=["core/event_bus", "core/secrets"],
    providers=["git_adapter"],
    hot_reloadable=True,
    requires_core="5.0.0",
)
