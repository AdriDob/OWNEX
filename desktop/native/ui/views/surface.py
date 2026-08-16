"""Surface — Attack Surface native PySide6 view.

Displays the current attack surface targets with:
- Target list table (id, platform, category, barrier score, status)
- Quick filters by category/platform
- Refresh action
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
    QVBoxLayout,
    QWidget,
)

from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView


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

        fl.addWidget(self._cat_filter)
        fl.addWidget(self._platform_filter)
        fl.addStretch()
        fl.addWidget(refresh_btn)
        main.addWidget(filt)

        # --- Tabla de targets ---
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["ID", "Platform", "Category", "Barrier", "Status"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setFont(QFont("Inter", 9))

        main.addWidget(self._table, 1)

        # Aplicar tema base
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
