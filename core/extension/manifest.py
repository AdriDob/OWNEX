from __future__ import annotations

from dataclasses import dataclass, field

from core.extension.capabilities import Capability
from core.extension.settings import SettingsField


@dataclass
class ExtensionManifest:
    """Declarative manifest for an ORION extension.

    Every extension in ``extensions/<name>/`` MUST expose a module-level
    ``manifest`` instance of this class.
    """

    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    icon: str = "Puzzle"

    # What this extension provides
    capabilities: list[Capability | str] = field(default_factory=list)

    # Event hooks: {hook_point: handler_path}
    #   hook_point examples: "before_scan", "after_report", "before_publish"
    #   handler_path examples: "my_ext.hooks.on_before_scan"
    hooks: dict[str, str] = field(default_factory=dict)

    # Declarative settings (auto-generates Settings UI)
    settings: list[SettingsField] = field(default_factory=list)

    # Dependencies: list of app_id or capability strings
    dependencies: list[str] = field(default_factory=list)

    # Connectors this extension registers
    providers: list[str] = field(default_factory=list)

    # Scheduler jobs
    scheduler_jobs: list[dict] = field(default_factory=list)

    # If True, extension can be loaded/unloaded at runtime
    hot_reloadable: bool = True

    # Minimum core version required
    requires_core: str = "4.0.0"

    # Path (filled by registry at discovery time)
    _path: str = ""
