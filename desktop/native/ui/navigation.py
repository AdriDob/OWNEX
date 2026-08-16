"""Native navigation model — single source of truth for module routing.

Mirrors the OWNEX navigation groups defined in the spec. Each section maps
to a view class that the shell instantiates lazily (lazy loading of heavy views).
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction


@dataclass(frozen=True)
class NavItem:
    section: str
    label: str
    view_cls: str  # dotted path: desktop.native.ui.views.{module}.View
    icon: str  # semantic icon name from icons.SEMANTIC_ICONS
    shortcut: str = ""
    # When a view is not yet ported, view_cls is empty -> sidebar entry is hidden.
    hidden: bool = False


# Section groupings. The order here is the sidebar order.
NAVIGATION: list[NavItem] = [
    # --- Mission Control ---
    NavItem("mission", "Mission Control", "desktop.native.ui.views.mission.MissionControlView", "activity", "Ctrl+1"),
    # --- Intelligence ---
    NavItem(
        "intelligence",
        "Intelligence",
        "desktop.native.ui.views.intelligence.IntelligenceView",
        "intelligence",
        "Ctrl+2",
    ),
    # --- Surface ---
    NavItem("surface", "Attack Surface", "desktop.native.ui.views.surface.SurfaceView", "target", "Ctrl+3"),
    # --- Findings ---
    NavItem("findings", "Findings", "desktop.native.ui.views.findings.FindingsView", "finding", "Ctrl+4"),
    # --- Reports ---
    NavItem("reports", "Reports", "desktop.native.ui.views.reports.ReportsView", "report", "Ctrl+5"),
    # --- Operations ---
    NavItem("operations", "Operations", "desktop.native.ui.views.operations.OperationsView", "automation", "Ctrl+6"),
    # --- Terminal ---
    NavItem("terminal", "Terminal", "desktop.native.ui.views.terminal.TerminalView", "terminal", "Ctrl+`"),
    # --- System ---
    NavItem("system", "System", "desktop.native.ui.views.system.SystemView", "system", "Ctrl+,"),
    # --- Settings ---
    NavItem("settings", "Settings", "desktop.native.ui.views.settings.SettingsView", "settings", "Ctrl+,"),
]


# Section headers for the sidebar grouping (label, anchor).
SECTIONS: list[tuple[str, str]] = [
    ("MISSION", "mission"),
    ("INTELLIGENCE", "intelligence"),
    ("WORKSPACE", "surface"),
    ("RESULTS", "findings"),
    ("DELIVER", "reports"),
    ("OPERATIONS", "operations"),
    ("TOOLS", "terminal"),
    ("SYSTEM", "system"),
]


def build_nav_actions(owner: QObject | None = None) -> dict[str, QAction]:
    """Create QAction objects for each nav item, wired to `owner`.

    Returns a mapping of section -> QAction so the shell can show/hide views.
    View classes are imported lazily by the shell to avoid heavy imports
    at startup.
    """
    return {item.section: QAction(item.label, owner) for item in NAVIGATION}


# Re-export for convenience.
__all__ = ["NAVIGATION", "SECTIONS", "NavItem", "build_nav_actions"]
