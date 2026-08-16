"""Findings — native PySide6 view.

Displays discovered findings/vulnerabilities with:
- Findings table (id, type, severity, description, affected target)
- Evidence summary badges
- Promote to report action
- Export findings action
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView


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
        self._table.setHorizontalHeaderLabels(["ID", "Type", "Severity", "Description", "Target"])
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

        export_btn = QPushButton("Export")
        export_btn.setFont(QFont("Inter", 9))

        al.addWidget(promote_btn)
        al.addStretch()
        al.addWidget(export_btn)
        main.addWidget(actions, 0)

        # Aplicar tema
        self.apply_theme()

    # -- Helpers de estilo --
    def apply_theme(self) -> None:
        theme = get_theme()
        ws = "background-color: " + theme.text + ";"
        sf = "background-color: " + theme.surface + ";"
        st = "border: 1px solid " + theme.stroke + ";"
        self.setStyleSheet(
            "QWidget {" + ws + "}QFrame {" + sf + "border-radius: 6px;" + st + "}QLabel {" + theme.text + ";"
        )
