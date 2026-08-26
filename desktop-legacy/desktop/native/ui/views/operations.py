"""Operations — native PySide6 view.

Displays automation operations with:
- Operations list (pipeline / work bank / targets / findings)
- Status per operation from the mission service
- Log output area
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop.native.services.mission import MissionControlData, get_mission
from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView

logger = logging.getLogger("ownex.native.views.operations")


class OperationsView(BaseView):
    SECTION = "operations"
    """Operations dashboard — automation workflow status."""

    def __init__(self, mission: MissionControlData | None = None, parent: QWidget | None = None) -> None:
        super().__init__(
            mission=mission,
            section="operations",
            label="Operations",
            icon="automation",
            parent=parent,
        )

        # Layout principal: tabla + log + acciones
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(8)

        # --- Tabla de operaciones ---
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Workflow", "Status", "Progress", "Actions"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setFont(QFont("Inter", 8))

        main.addWidget(self._table, 1)

        # --- Log output ---
        log_label = QLabel("Log output:")
        log_label.setFont(QFont("Inter", 9))

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Consolas", 8))
        self._log.setPlaceholderText("No operations logged yet. Press Refresh to pull the current state.")

        main.addWidget(self._log, 0)

        # --- Barra de acciones ---
        actions = QFrame()
        al = QHBoxLayout(actions)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(6)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFont(QFont("Inter", 9))
        self._refresh_btn = refresh_btn
        self._refresh_btn.clicked.connect(self.refresh)

        self._source_label = QLabel("Source: --")
        self._source_label.setFont(QFont("Inter", 9))

        al.addWidget(refresh_btn)
        al.addWidget(self._source_label)
        al.addStretch()
        main.addWidget(actions, 0)

        # Aplicar tema
        self.apply_theme()

    # -- Data loading (real data from the mission service) ---------------
    def refresh(self) -> None:
        mission = getattr(self, "mission", None) or get_mission()
        try:
            data = mission.get_dashboard()
        except Exception as exc:  # noqa: BLE001
            logger.warning("operations refresh failed: %s", exc)
            self._source_label.setText("Source: error")
            self._log.append(f"[error] operations refresh failed: {exc}")
            return
        source = str(data.get("source", "local"))
        self._source_label.setText("Source: " + source)
        counts = data.get("counts", {})
        status = data.get("status", {})

        rows = [
            (
                "Mission pipeline",
                "running" if status.get("running") else "stopped",
                str(counts.get("opps", "n/a")),
                "-",
            ),
            ("Work Bank", "ready", str(counts.get("ready_to_deliver", 0)) + " deliverable", "-"),
            ("Targets", "configured", str(counts.get("targets", 0)) + " active", "-"),
            ("Findings", "tracked", str(counts.get("findings", 0)) + " recorded", "-"),
        ]
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self._table.setItem(r, c, item)

        activity = data.get("activity", [])
        if activity:
            last = activity[-1]
            self._log.append(f"[{source}] {len(activity)} recent events; latest: {last.get('title', '')}")
        else:
            self._log.append(f"[{source}] no activity yet — start an operation or wait for the scheduler.")

    # -- Helpers de estilo --
    def apply_theme(self) -> None:
        theme = get_theme()
        ws = "background-color: " + theme.background + ";"
        sf = "background-color: " + theme.surface + ";"
        st = "border: 1px solid " + theme.stroke + ";"
        self.setStyleSheet(
            "QWidget {" + ws + "}QFrame {" + sf + "border-radius: 6px;" + st + "}QLabel {" + theme.text + ";}"
        )
