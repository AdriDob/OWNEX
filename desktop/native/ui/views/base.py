"""Base view class for native desktop views.

All native views subclass BaseView, which is a thin QWidget wrapper that:
- owns a reference to the MissionControlData service
- exposes a `refresh()` hook the shell calls on navigation
- carries a `SECTION` identifier used by the shell's QStackedWidget
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget

from desktop.native.services.mission import MissionControlData, get_mission


class BaseView(QWidget):
    """Base class for all native desktop views.

    Attributes:
        SECTION: nav section identifier (must match a NavItem.section).
        TITLE: window subtitle shown in the topbar.
    """

    SECTION: str = "base"
    TITLE: str = "View"

    def __init__(self, mission: MissionControlData | None = None, **kwargs: Any) -> None:
        kwargs.pop("section", None)
        kwargs.pop("label", None)
        kwargs.pop("icon", None)
        super().__init__(**kwargs)
        self._mission = mission or get_mission()

    def refresh(self) -> None:
        """Called by the shell on every navigation to this view.

        Subclasses override to pull fresh data from their service.
        """
        pass

    @property
    def mission(self) -> MissionControlData:
        return self._mission


def load_view(section: str, mission: MissionControlData | None = None) -> BaseView | None:
    """Lazily import and instantiate the view for a nav section.

    Avoids importing heavy view modules (charts, terminal, tables) at startup.
    """
    from desktop.native.ui.navigation import NAVIGATION

    item = next((i for i in NAVIGATION if i.section == section), None)
    if item is None or not item.view_cls:
        return None
    mod_path, cls_name = item.view_cls.rsplit(".", 1)
    try:
        import importlib

        mod = importlib.import_module(mod_path)
        view_cls = getattr(mod, cls_name)
        return view_cls(mission=mission)  # type: ignore[arg-type]
    except Exception as exc:
        import logging

        logging.getLogger("ownex.native.ui").warning("view load failed for %s: %s", section, exc)
        return None
