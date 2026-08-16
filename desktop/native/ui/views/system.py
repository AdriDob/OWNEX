"""System — native PySide6 system monitor view.

Displays system health metrics, resource usage, and service status.
Integrated with UnifiedMemoryStore health checks and EventBus status.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView


class SystemView(BaseView):
    SECTION = "system"
    """System monitor — health metrics + service status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
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
            ("Event Bus", "running"),
            ("Scheduler", "stopped"),
            ("Direct Work", "stopped"),
            ("Mission Control", "stopped"),
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
        main.addWidget(refresh, 0)

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
