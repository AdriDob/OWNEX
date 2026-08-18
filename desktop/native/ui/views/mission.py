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

from desktop.native.services.api_client import ApiClient
from desktop.native.services.mission import MissionControlData
from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView

logger = logging.getLogger("ownex.native.views.mission")


class MissionControlView(BaseView):
    """Mission Control dashboard — KPI cards + target list + actions."""

    SECTION = "mission"
    TITLE = "Mission Control"

    def __init__(self, mission: MissionControlData | None = None, parent: QWidget | None = None) -> None:
        super().__init__(mission=mission, parent=parent)

        # Initialize API client
        self._api = ApiClient()

        # Internal state for API-fetched data (used when no mission data provided)
        self._api_targets: list[dict] = []
        self._api_findings_count: int = 0
        self._api_activity_count: int = 0

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

        # Initial data load — use mission data if provided, otherwise API
        self.refresh()

    # -- Data loading (real data from API or mission data) ----------------
    def _fetch_api_data(self) -> dict | None:
        """Fetch KPI data and targets from the backend API."""
        try:
            targets = self._api.fetch_targets(limit=50)
        except Exception as exc:  # noqa: BLE001
            logger.warning("mission targets fetch failed: %s", exc)
            targets = []

        try:
            findings = self._api.fetch_findings(limit=50)
            findings_count = len(findings) if findings else 0
        except Exception as exc:  # noqa: BLE001
            logger.warning("mission findings fetch failed: %s", exc)
            findings_count = 0

        try:
            activity = self._api.fetch_activity(hours=24, limit=20)
            activity_count = len(activity) if activity else 0
        except Exception as exc:  # noqa: BLE001
            logger.warning("mission activity fetch failed: %s", exc)
            activity_count = 0

        return {
            "source": "api",
            "counts": {
                "targets": len(targets),
                "findings": findings_count,
                "opps": "n/a",
                "activity": activity_count,
            },
            "targets": targets,
        }

    def refresh(self) -> None:
        """Fetch fresh data and update the UI.

        Uses mission data if a mission with get_dashboard() was provided,
        otherwise falls back to backend API.
        """
        # Try mission data first (for test compatibility and offline mode)
        mission = getattr(self, "mission", None)
        if mission is not None and hasattr(mission, "get_dashboard"):
            try:
                data = mission.get_dashboard()
                counts = data.get("counts", {})
                self._set_kpis(
                    counts.get("targets", 0),
                    counts.get("findings", 0),
                    counts.get("opps", "n/a"),
                    counts.get("activity", 0),
                )
                self._set_source(str(data.get("source", "local")))
                self._populate_targets(data.get("targets", []))
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("mission dashboard refresh failed: %s", exc)

        # Fall back to API
        try:
            data = self._fetch_api_data()
        except Exception as exc:  # noqa: BLE001
            logger.warning("API dashboard refresh failed: %s", exc)
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
        self._set_source(str(data.get("source", "api")))
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
            status = "Active" if t.get("active") else "Inactive"
            self._table.setItem(row, 3, QTableWidgetItem(status))

    # -- Helpers de estilo — usando get_theme() en lugar de atributos directos --
    def apply_theme(self) -> None:
        theme = get_theme()

        ws = "background-color: " + theme.background + ";"
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
