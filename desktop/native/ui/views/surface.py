"""Surface — Attack Surface native PySide6 view.

Displays the current attack surface targets with:
- Target list table (id, platform, category, barrier score, status)
- Quick filters by category/platform
- Refresh action
"""

from __future__ import annotations

import logging

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop.native.services.mission import get_mission
from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView

logger = logging.getLogger("ownex.native.views.surface")


class SurfaceView(BaseView):
    SECTION = "surface"
    """Attack Surface dashboard — target list + quick filters."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            section="surface",
            label="Attack Surface",
            icon="target",
            parent=parent,
        )

        # Layout principal: filtros + tabla de targets
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(8)

        # --- Filtros ---
        filt = QFrame()
        fl = QHBoxLayout(filt)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(6)

        self._cat_filter = QLabel("All")
        self._cat_filter.setFont(QFont("Inter", 10))

        self._platform_filter = QLabel("All")
        self._platform_filter.setFont(QFont("Inter", 10))

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFont(QFont("Inter", 10))

        self._refresh_btn = refresh_btn
        self._refresh_btn.clicked.connect(self.refresh)

        fl.addWidget(self._cat_filter)
        fl.addWidget(self._platform_filter)
        fl.addStretch()
        fl.addWidget(refresh_btn)
        main.addWidget(filt)

        # --- Tabla de targets ---
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["ID", "Name", "Domain", "Endpoints", "Status"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setFont(QFont("Inter", 9))

        main.addWidget(self._table, 1)

        # Aplicar tema base
        self.apply_theme()

    # -- Data loading (real targets from the mission service) ------------
    def refresh(self) -> None:
        mission = getattr(self, "mission", None) or get_mission()
        try:
            targets = mission.get_targets()
        except Exception as exc:  # noqa: BLE001
            logger.warning("targets refresh failed: %s", exc)
            targets = []
        self._table.setRowCount(len(targets))
        for row, t in enumerate(targets):
            self._table.setItem(row, 0, QTableWidgetItem(str(t.get("id", ""))))
            self._table.setItem(row, 1, QTableWidgetItem(str(t.get("name", ""))))
            self._table.setItem(row, 2, QTableWidgetItem(str(t.get("domain", ""))))
            self._table.setItem(row, 3, QTableWidgetItem(str(t.get("endpoint_count", 0))))
            self._table.setItem(row, 4, QTableWidgetItem("Active" if t.get("active") else "Inactive"))

    # -- Helpers de estilo --
    def apply_theme(self) -> None:
        theme = get_theme()
        ws = "background-color: " + theme.text + ";"
        sf = "background-color: " + theme.surface + ";"
        st = "border: 1px solid " + theme.stroke + ";"
        self.setStyleSheet(
            "QWidget {" + ws + "}QFrame {" + sf + "border-radius: 6px;" + st + "}QLabel {" + theme.text + ";"
        )
