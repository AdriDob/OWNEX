"""Operations — native PySide6 view.

Displays automation operations with:
- Operations list (running/queued/completed/cancelled)
- Progress bars per operation
- Stop/Cancel actions
- Log output area
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView


class OperationsView(BaseView):
    SECTION = "operations"
    """Operations dashboard — automation workflow status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
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
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["ID", "Workflow", "Status", "Progress", "Actions"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setFont(QFont("Inter", 8))

        # Columna de progress bar personalizada
        self._table.setColumnWidth(3, 80)

        main.addWidget(self._table, 1)

        # --- Log output ---
        log_label = QLabel("Log output:")
        log_label.setFont(QFont("Inter", 9))

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Consolas", 8))
        self._log.setPlaceholderText("No operations running...")

        main.addWidget(self._log, 0)

        # --- Barra de acciones ---
        actions = QFrame()
        al = QHBoxLayout(actions)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(6)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFont(QFont("Inter", 9))

        stop_all_btn = QPushButton("Stop All")
        stop_all_btn.setFont(QFont("Inter", 9))

        al.addWidget(refresh_btn)
        al.addStretch()
        al.addWidget(stop_all_btn)
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
