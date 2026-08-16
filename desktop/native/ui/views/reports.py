"""Reports — native PySide6 view.

Displays generated reports with:
- Reports list table (id, title, platform, created, status, actions)
- Report preview pane (read-only)
- Generate new report action
- Export reports action
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView


class ReportsView(BaseView):
    SECTION = "reports"
    """Reports dashboard — generated reports list + preview."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            section="reports",
            label="Reports",
            icon="report",
            parent=parent,
        )

        # Layout principal: lista + panel de vista previa
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(8)

        # --- Lista de reports ---
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["ID", "Title", "Platform", "Created", "Status"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setFont(QFont("Inter", 8))

        main.addWidget(self._table, 1)

        # --- Panel de vista previa ---
        preview = QFrame()
        preview.setObjectName("section-frame")
        pl = QVBoxLayout(preview)
        pl.setContentsMargins(8, 8, 8, 8)
        self._preview_text = QTextEdit()
        self._preview_text.setReadOnly(True)
        self._preview_text.setFont(QFont("Inter", 9))
        self._preview_text.setPlaceholderText("Select a report to preview...")
        pl.addWidget(self._preview_text)

        main.addWidget(preview, 0)

        # --- Barra de acciones ---
        actions = QFrame()
        al = QHBoxLayout(actions)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(6)

        generate_btn = QPushButton("Generate Report")
        generate_btn.setFont(QFont("Inter", 9))

        export_btn = QPushButton("Export")
        export_btn.setFont(QFont("Inter", 9))

        al.addWidget(generate_btn)
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
