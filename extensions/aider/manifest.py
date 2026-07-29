from __future__ import annotations

from core.extension.manifest import ExtensionManifest
from core.extension.capabilities import Capability

manifest = ExtensionManifest(
    id="aider",
    name="Aider Code Editor",
    version="1.0.0",
    description="AI-assisted code editing and repository management plugin. "
    "Enables OWNEX to make targeted edits to code in real repositories, "
    "run tests, and review changes via Git integration.",
    author="OWNEX",
    icon="Code2",
    capabilities=[
        Capability(
            id="code_editor",
            name="Code Editor",
            description="Make targeted edits to source files",
        ),
        Capability(
            id="git_integration",
            name="Git Integration",
            description="Commit, diff, and review changes",
        ),
        Capability(
            id="test_runner",
            name="Test Runner",
            description="Run tests in the target repository",
        ),
    ],
    hooks={
        "before_validation": "aider.hooks.before_validation",
        "after_report": "aider.hooks.after_report",
    },
    dependencies=["core/event_bus", "core/secrets", "core/storage"],
    providers=["aider_editor"],
    hot_reloadable=True,
    requires_core="5.0.0",
)
