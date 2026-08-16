"""Mission Control — native PySide6 view.

Displays the OWNEX Mission Control dashboard with:
- KPI cards: targets, findings, opportunities, activity
- Targets table
- Quick action bar
- Theme-aware styling via ThemeRegistry/ThemeSpec.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from desktop.native.services.mission import MissionControlData
from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView


class MissionControlView(BaseView):
    """Mission Control dashboard — KPI cards + target list + actions."""

    SECTION = "mission"
    TITLE = "Mission Control"

    def __init__(self, mission: MissionControlData | None = None, parent: QWidget | None = None) -> None:
        super().__init__(mission=mission, parent=parent)

        # Layout principal: KPI cards en grid + tabla de targets + acciones
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(8)

        # --- KPI Cards Grid ---
        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(12)
        kpi_grid.setVerticalSpacing(12)

        # KPI: Targets
        self._targets_kpi = QLabel("Targets: --")
        self._targets_kpi.setFont(QFont("Inter", 12))
        self._targets_kpi.setStyleSheet("color: #00D5FF;")

        # KPI: Findings
        self._findings_kpi = QLabel("Findings: --")
        self._findings_kpi.setFont(QFont("Inter", 12))
        self._findings_kpi.setStyleSheet("color: #00D5FF;")

        # KPI: Opportunities
        self._opps_kpi = QLabel("Ops: --")
        self._opps_kpi.setFont(QFont("Inter", 12))
        self._opps_kpi.setStyleSheet("color: #00D5FF;")

        # KPI: Activity
        self._activity_kpi = QLabel("Activity: --")
        self._activity_kpi.setFont(QFont("Inter", 12))
        self._activity_kpi.setStyleSheet("color: #00D5FF;")

        kpi_grid.addWidget(QLabel("Targets"), 0, 0)
        kpi_grid.addWidget(self._targets_kpi, 0, 1)
        kpi_grid.addWidget(QLabel("Findings"), 1, 0)
        kpi_grid.addWidget(self._findings_kpi, 1, 1)
        kpi_grid.addWidget(QLabel("Operations"), 2, 0)
        kpi_grid.addWidget(self._opps_kpi, 2, 1)
        kpi_grid.addWidget(QLabel("Activity"), 3, 0)
        kpi_grid.addWidget(self._activity_kpi, 3, 1)

        main.addLayout(kpi_grid, 0)

        # --- Tabla de targets ---
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["ID", "Platform", "Category", "Status"])
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

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFont(QFont("Inter", 9))

        view_btn = QPushButton("View")
        view_btn.setFont(QFont("Inter", 9))

        al.addWidget(refresh_btn)
        al.addStretch()
        al.addWidget(view_btn)
        main.addWidget(actions, 0)

        # Aplicar tema
        self.apply_theme()

    # -- Helpers de estilo — usando get_theme() en lugar de atributos directos --
    def apply_theme(self) -> None:
        theme = get_theme()

        ws = "background-color: " + theme.text + ";"
        fc = "color: " + theme.text + ";"
        sf = "background-color: " + theme.surface + ";"
        st = "border: 1px solid " + theme.stroke + ";"

        self.setStyleSheet(
            "QWidget {" + ws + "}"
            "QFrame {" + sf + "border-radius: 6px;" + st + "}"
            "QTableWidget {" + sf + "border-radius: 6px;" + st + "gridline-color: " + theme.stroke + ";}"
            "QHeaderView::section {"
            + "background-color: "
            + theme.surface_alt
            + ";"
            + "color: "
            + theme.text
            + ";"
            + "border: none;"
            + "padding: 4px;"
            + "}"
            "QPushButton {"
            + sf
            + "color: "
            + theme.text
            + ";"
            + "border: 1px solid "
            + theme.stroke
            + ";"
            + "border-radius: 6px;"
            + "padding: 6px 12px;"
            + "}"
            "QPushButton:hover {" + "background-color: " + theme.surface_alt + ";" + "}"
            "QLabel {" + fc + "}"
        )
