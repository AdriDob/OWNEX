"""System — native PySide6 system monitor view.

Displays system health metrics, resource usage, and service status.
Integrated with UnifiedMemoryStore health checks and EventBus status.
"""

from __future__ import annotations

import logging

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.native.services.mission import MissionControlData, get_mission
from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView

logger = logging.getLogger("ownex.native.views.system")


class SystemView(BaseView):
    SECTION = "system"
    """System monitor — health metrics + service status."""

    def __init__(self, mission: MissionControlData | None = None, parent: QWidget | None = None) -> None:
        super().__init__(
            mission=mission,
            section="system",
            label="System",
            icon="system",
            parent=parent,
        )

        # Layout principal: grid de KPIs + estado de servicios
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(8)

        # --- Grid de KPIs ---
        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(12)
        kpi_grid.setVerticalSpacing(12)

        # Targets KPI
        self._targets_kpi = QLabel("Targets: --")
        self._targets_kpi.setFont(QFont("Inter", 12))
        self._targets_kpi.setStyleSheet("color: #00D5FF;")

        # Findings KPI
        self._findings_kpi = QLabel("Findings: --")
        self._findings_kpi.setFont(QFont("Inter", 12))
        self._findings_kpi.setStyleSheet("color: #00D5FF;")

        # Ops KPI
        self._ops_kpi = QLabel("Ops: --")
        self._ops_kpi.setFont(QFont("Inter", 12))
        self._ops_kpi.setStyleSheet("color: #00D5FF;")

        # Activity KPI
        self._activity_kpi = QLabel("Activity: --")
        self._activity_kpi.setFont(QFont("Inter", 12))
        self._activity_kpi.setStyleSheet("color: #00D5FF;")

        kpi_grid.addWidget(QLabel("Targets"), 0, 0)
        kpi_grid.addWidget(self._targets_kpi, 0, 1)
        kpi_grid.addWidget(QLabel("Findings"), 1, 0)
        kpi_grid.addWidget(self._findings_kpi, 1, 1)
        kpi_grid.addWidget(QLabel("Operations"), 2, 0)
        kpi_grid.addWidget(self._ops_kpi, 2, 1)
        kpi_grid.addWidget(QLabel("Activity"), 3, 0)
        kpi_grid.addWidget(self._activity_kpi, 3, 1)

        main.addLayout(kpi_grid, 0)

        # --- Estado de servicios ---
        svc_grid = QGridLayout()
        svc_grid.setHorizontalSpacing(12)
        svc_grid.setVerticalSpacing(6)

        services = [
            ("Backend API", "offline"),
            ("Scheduler", "n/a"),
            ("Direct Work", "n/a"),
            ("Event Bus", "local"),
        ]
        self._svc_labels: dict[str, QLabel] = {}
        for i, (name, status) in enumerate(services):
            lbl = QLabel(f"{name}: {status}")
            lbl.setFont(QFont("Inter", 9))
            lbl.setStyleSheet("color: #8B8D98;")
            self._svc_labels[name] = lbl
            svc_grid.addWidget(lbl, i // 2, i % 2)

        main.addLayout(svc_grid, 1)

        # --- Botón de actualizar ---
        refresh = QPushButton("Refresh Status")
        refresh.setFont(QFont("Inter", 9))
        refresh.setFixedHeight(30)
        self._refresh_btn = refresh
        self._refresh_btn.clicked.connect(self.refresh)
        main.addWidget(refresh, 0)

        # Aplicar tema
        self.apply_theme()

    # -- Data loading (real data from the mission service) --------------
    def refresh(self) -> None:
        mission = getattr(self, "mission", None) or get_mission()
        try:
            data = mission.get_dashboard()
        except Exception as exc:  # noqa: BLE001
            logger.warning("system refresh failed: %s", exc)
            return
        counts = data.get("counts", {})
        self._targets_kpi.setText("Targets: " + str(counts.get("targets", 0)))
        self._findings_kpi.setText("Findings: " + str(counts.get("findings", 0)))
        self._ops_kpi.setText("Ops: " + str(counts.get("opps", "n/a")))
        self._activity_kpi.setText("Activity: " + str(counts.get("activity", 0)))
        self._set_services(data)

    def _set_services(self, data: dict) -> None:
        if data.get("source") == "api":
            ops = str(data.get("counts", {}).get("opps", "n/a"))
            statuses = {
                "Backend API": "online",
                "Scheduler": "running" if ops == "running" else "stopped",
                "Direct Work": ops,
                "Event Bus": "online",
            }
        else:
            statuses = {
                "Backend API": "offline",
                "Scheduler": "n/a",
                "Direct Work": "n/a",
                "Event Bus": "local",
            }
        for name, status in statuses.items():
            lbl = self._svc_labels.get(name)
            if lbl is not None:
                lbl.setText(f"{name}: {status}")

    # -- Helpers de estilo --

    def apply_theme(self) -> None:
        theme = get_theme()
        ws = "background-color: " + theme.background + ";"
        sf = "background-color: " + theme.surface + ";"
        st = "border: 1px solid " + theme.stroke + ";"
        self.setStyleSheet(
            "QWidget {" + ws + "}QFrame {" + sf + "border-radius: 6px;" + st + "}QLabel {" + theme.text + ";}"
        )
