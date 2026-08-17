"""Findings — native PySide6 view.

Displays discovered findings/vulnerabilities with:
- Findings table (id, type, severity, description, affected target)
- Evidence summary badges
- Promote to report action
- Export findings action
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop.native.services.mission import get_mission
from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView

logger = logging.getLogger("ownex.native.views.findings")


class FindingsView(BaseView):
    SECTION = "findings"
    """Findings dashboard — discovered vulnerabilities + evidence."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            section="findings",
            label="Findings",
            icon="finding",
            parent=parent,
        )

        # Layout principal: tabla + acciones
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(8)

        # --- Tabla de findings ---
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["ID", "Title", "Severity", "Status", "Target"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setFont(QFont("Inter", 8))

        main.addWidget(self._table, 1)

        # --- Barra de acciones ---
        actions = QFrame()
        al = QHBoxLayout(actions)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(6)

        promote_btn = QPushButton("Promote to Report")
        promote_btn.setFont(QFont("Inter", 9))

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFont(QFont("Inter", 9))

        export_btn = QPushButton("Export")
        export_btn.setFont(QFont("Inter", 9))

        self._refresh_btn = refresh_btn
        self._refresh_btn.clicked.connect(self.refresh)

        al.addWidget(promote_btn)
        al.addWidget(refresh_btn)
        al.addStretch()
        al.addWidget(export_btn)
        main.addWidget(actions, 0)

        # Aplicar tema
        self.apply_theme()

    # -- Data loading (real data from the mission service) --------------
    def refresh(self) -> None:
        mission = getattr(self, "mission", None) or get_mission()
        try:
            findings = mission.get_findings()
        except Exception as exc:  # noqa: BLE001
            logger.warning("findings refresh failed: %s", exc)
            findings = []
        self._table.setRowCount(len(findings))
        if not findings:
            self._table.setRowCount(1)
            item = QTableWidgetItem("No findings yet — run the pipeline or wait for the scheduler.")
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(0, 0, item)
            return
        for row, f in enumerate(findings):
            self._table.setItem(row, 0, QTableWidgetItem(str(f.get("id", ""))))
            self._table.setItem(row, 1, QTableWidgetItem(str(f.get("title", ""))))
            self._table.setItem(row, 2, QTableWidgetItem(str(f.get("severity", "info"))))
            self._table.setItem(row, 3, QTableWidgetItem(str(f.get("status", "new"))))
            self._table.setItem(row, 4, QTableWidgetItem(str(f.get("target_id", ""))))

    # -- Helpers de estilo --
    def apply_theme(self) -> None:
        theme = get_theme()
        ws = "background-color: " + theme.text + ";"
        sf = "background-color: " + theme.surface + ";"
        st = "border: 1px solid " + theme.stroke + ";"
        self.setStyleSheet(
            "QWidget {" + ws + "}QFrame {" + sf + "border-radius: 6px;" + st + "}QLabel {" + theme.text + ";"
        )
