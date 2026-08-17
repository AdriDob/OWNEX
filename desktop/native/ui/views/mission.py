"""Mission Control — native PySide6 view.

Displays the OWNEX Mission Control dashboard with:
- KPI cards: targets, findings, opportunities, activity
- Targets table
- Quick action bar
- Theme-aware styling via ThemeRegistry/ThemeSpec.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop.native.services.mission import MissionControlData, get_mission
from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView

logger = logging.getLogger("ownex.native.views.mission")


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
        self._table.setHorizontalHeaderLabels(["ID", "Name", "Domain", "Status"])
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

        self._refresh_btn = refresh_btn
        self._refresh_btn.clicked.connect(self.refresh)

        self._source_label = QLabel("Source: --")
        self._source_label.setFont(QFont("Inter", 9))

        view_btn = QPushButton("View")
        view_btn.setFont(QFont("Inter", 9))

        al.addWidget(refresh_btn)
        al.addWidget(self._source_label)
        al.addStretch()
        al.addWidget(view_btn)
        main.addWidget(actions, 0)

        # Aplicar tema
        self.apply_theme()

    # -- Data loading (real data, never hardcoded KPIs) ----------------
    def refresh(self) -> None:
        mission = getattr(self, "mission", None) or get_mission()
        try:
            data = mission.get_dashboard()
        except Exception as exc:  # noqa: BLE001
            logger.warning("mission dashboard refresh failed: %s", exc)
            self._set_kpis("--", "--", "error", "--")
            self._set_source("error")
            self._table.setRowCount(0)
            return
        counts = data.get("counts", {})
        self._set_kpis(
            counts.get("targets", 0),
            counts.get("findings", 0),
            counts.get("opps", "n/a"),
            counts.get("activity", 0),
        )
        self._set_source(str(data.get("source", "local")))
        self._populate_targets(data.get("targets", []))

    def _set_kpis(self, targets: object, findings: object, opps: object, activity: object) -> None:
        self._targets_kpi.setText("Targets: " + str(targets))
        self._findings_kpi.setText("Findings: " + str(findings))
        self._opps_kpi.setText("Ops: " + str(opps))
        self._activity_kpi.setText("Activity: " + str(activity))

    def _set_source(self, source: str) -> None:
        self._source_label.setText("Source: " + source)

    def _populate_targets(self, targets: list[dict]) -> None:
        if not targets:
            self._table.setRowCount(1)
            item = QTableWidgetItem("No targets configured yet — use 'Add Target' in Attack Surface to start.")
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(0, 0, item)
            return
        self._table.setRowCount(len(targets))
        for row, t in enumerate(targets):
            self._table.setItem(row, 0, QTableWidgetItem(str(t.get("id", ""))))
            self._table.setItem(row, 1, QTableWidgetItem(str(t.get("name", ""))))
            self._table.setItem(row, 2, QTableWidgetItem(str(t.get("domain", ""))))
            self._table.setItem(row, 3, QTableWidgetItem("Active" if t.get("active") else "Inactive"))

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
