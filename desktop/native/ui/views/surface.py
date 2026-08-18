"""Surface — Attack Surface native PySide6 view.

Displays the current attack surface targets with:
- Target list table (id, platform, category, barrier score, status)
- Quick filters by category/platform
- Refresh action
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop.native.services.mission import MissionControlData, get_mission
from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView

logger = logging.getLogger("ownex.native.views.surface")


class SurfaceView(BaseView):
    SECTION = "surface"
    """Attack Surface dashboard — target list + quick filters."""

    def __init__(self, mission: MissionControlData | None = None, parent: QWidget | None = None) -> None:
        super().__init__(
            mission=mission,
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

        add_btn = QPushButton("Add Target")
        add_btn.setFont(QFont("Inter", 10))
        self._add_btn = add_btn
        self._add_btn.clicked.connect(self._add_target)

        fl.addWidget(self._cat_filter)
        fl.addWidget(self._platform_filter)
        fl.addStretch()
        fl.addWidget(add_btn)
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
        if not targets:
            self._table.setRowCount(1)
            item = QTableWidgetItem("No targets configured yet — use 'Add Target' to start.")
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(0, 0, item)
            return
        for row, t in enumerate(targets):
            self._table.setItem(row, 0, QTableWidgetItem(str(t.get("id", ""))))
            self._table.setItem(row, 1, QTableWidgetItem(str(t.get("name", ""))))
            self._table.setItem(row, 2, QTableWidgetItem(str(t.get("domain", ""))))
            self._table.setItem(row, 3, QTableWidgetItem(str(t.get("endpoint_count", 0))))
            self._table.setItem(row, 4, QTableWidgetItem("Active" if t.get("active") else "Inactive"))

    # -- Add Target (real create via the shared data service) ------------
    def _add_target(self) -> None:
        mission = getattr(self, "mission", None) or get_mission()
        name, ok = QInputDialog.getText(self, "Add Target", "Target name:")
        if not ok or not name.strip():
            return
        domain, ok_d = QInputDialog.getText(self, "Add Target", "Domain (optional):")
        if not ok_d:
            return
        try:
            mission.get_targets()  # ensures the local schema/engines are ready
            from api.services.data_service import create_target

            result = create_target(name.strip(), domain.strip() or None)
        except Exception as exc:  # noqa: BLE001
            logger.warning("add target failed: %s", exc)
            QMessageBox.warning(self, "Add Target", "Could not add target:\n" + str(exc))
            return
        if result.get("duplicate"):
            QMessageBox.information(
                self, "Add Target", f"Target '{result.get('name')}' already exists (id={result.get('id')})."
            )
        self.refresh()

    # -- Helpers de estilo --

    def apply_theme(self) -> None:
        theme = get_theme()
        ws = "background-color: " + theme.background + ";"
        sf = "background-color: " + theme.surface + ";"
        st = "border: 1px solid " + theme.stroke + ";"
        self.setStyleSheet(
            "QWidget {" + ws + "}QFrame {" + sf + "border-radius: 6px;" + st + "}QLabel {" + theme.text + ";}"
        )
