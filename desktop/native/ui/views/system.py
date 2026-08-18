"""System — native PySide6 system monitor view.

Displays system health metrics, resource usage, service status, payment
compatibility, knowledge bridge (Obsidian vault), and voice status.
Integrated with UnifiedMemoryStore health checks, EventBus status, and
the OwnEx backend API.
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

from desktop.native.services.api_client import ApiClient
from desktop.native.services.mission import MissionControlData, get_mission
from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView

logger = logging.getLogger("ownex.native.views.system")


class SystemView(BaseView):
    SECTION = "system"
    """System monitor — health metrics + service status + payment + knowledge + voice."""

    def __init__(self, mission: MissionControlData | None = None, parent: QWidget | None = None) -> None:
        super().__init__(
            mission=mission,
            section="system",
            label="System",
            icon="system",
            parent=parent,
        )

        self._api = ApiClient()

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

        # Payment KPI
        self._payment_kpi = QLabel("Payment: --")
        self._payment_kpi.setFont(QFont("Inter", 12))
        self._payment_kpi.setStyleSheet("color: #00D5FF;")

        # Knowledge KPI
        self._knowledge_kpi = QLabel("Knowledge: --")
        self._knowledge_kpi.setFont(QFont("Inter", 12))
        self._knowledge_kpi.setStyleSheet("color: #00D5FF;")

        # Voice KPI
        self._voice_kpi = QLabel("Voice: --")
        self._voice_kpi.setFont(QFont("Inter", 12))
        self._voice_kpi.setStyleSheet("color: #00D5FF;")

        kpi_grid.addWidget(QLabel("Targets"), 0, 0)
        kpi_grid.addWidget(self._targets_kpi, 0, 1)
        kpi_grid.addWidget(QLabel("Findings"), 1, 0)
        kpi_grid.addWidget(self._findings_kpi, 1, 1)
        kpi_grid.addWidget(QLabel("Operations"), 2, 0)
        kpi_grid.addWidget(self._ops_kpi, 2, 1)
        kpi_grid.addWidget(QLabel("Activity"), 3, 0)
        kpi_grid.addWidget(self._activity_kpi, 3, 1)
        kpi_grid.addWidget(QLabel("Payment"), 4, 0)
        kpi_grid.addWidget(self._payment_kpi, 4, 1)
        kpi_grid.addWidget(QLabel("Knowledge"), 5, 0)
        kpi_grid.addWidget(self._knowledge_kpi, 5, 1)
        kpi_grid.addWidget(QLabel("Voice"), 6, 0)
        kpi_grid.addWidget(self._voice_kpi, 6, 1)
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
            ("Payment", "offline"),
            ("Knowledge", "disconnected"),
            ("Voice", "offline"),
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

    # -- Data loading (real data from the mission service + API) --------------
    def refresh(self) -> None:
        mission = getattr(self, "mission", None) or get_mission()
        api = getattr(self, "api", None) or ApiClient()
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
        self._set_payment(api)
        self._set_knowledge(api)
        self._set_voice(api)

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

    def _set_payment(self, api: ApiClient) -> None:
        try:
            data = api.fetch_payment_network()
            if data and isinstance(data, dict):
                summary = data.get("summary", {})
                accounts = data.get("accounts", [])
                n_accounts = len(accounts) if accounts else 0
                self._payment_kpi.setText("Payment: " + str(n_accounts) + " accounts")
                if "Payment" in self._svc_labels:
                    self._svc_labels["Payment"].setText("Payment: online" if n_accounts > 0 else "Payment: offline")
            else:
                self._payment_kpi.setText("Payment: --")
                if "Payment" in self._svc_labels:
                    self._svc_labels["Payment"].setText("Payment: offline")
        except Exception as exc:  # noqa: BLE001
            logger.warning("system payment fetch failed: %s", exc)
            self._payment_kpi.setText("Payment: --")
            if "Payment" in self._svc_labels:
                self._svc_labels["Payment"].setText("Payment: offline")

    def _set_knowledge(self, api: ApiClient) -> None:
        try:
            data = api.fetch_knowledge_status()
            if data and isinstance(data, dict):
                connected = data.get("connected", False)
                n_notes = data.get("status", {}).get("last_scan", 0) if isinstance(data.get("status"), dict) else 0
                self._knowledge_kpi.setText("Knowledge: " + ("connected" if connected else "disconnected"))
                if "Knowledge" in self._svc_labels:
                    self._svc_labels["Knowledge"].setText("Knowledge: " + ("online" if connected else "disconnected"))
            else:
                self._knowledge_kpi.setText("Knowledge: --")
                if "Knowledge" in self._svc_labels:
                    self._svc_labels["Knowledge"].setText("Knowledge: disconnected")
        except Exception as exc:  # noqa: BLE001
            logger.warning("system knowledge fetch failed: %s", exc)
            self._knowledge_kpi.setText("Knowledge: --")
            if "Knowledge" in self._svc_labels:
                self._svc_labels["Knowledge"].setText("Knowledge: disconnected")

    def _set_voice(self, api: ApiClient) -> None:
        try:
            data = api.fetch_voice_status()
            if data and isinstance(data, dict):
                enabled = data.get("enabled", False)
                tts = data.get("tts_provider", "unknown")
                self._voice_kpi.setText("Voice: " + ("enabled" if enabled else "disabled"))
                if "Voice" in self._svc_labels:
                    self._svc_labels["Voice"].setText("Voice: " + ("online" if enabled else "offline"))
            else:
                self._voice_kpi.setText("Voice: --")
                if "Voice" in self._svc_labels:
                    self._svc_labels["Voice"].setText("offline")
        except Exception as exc:  # noqa: BLE001
            logger.warning("system voice fetch failed: %s", exc)
            self._voice_kpi.setText("Voice: --")
            if "Voice" in self._svc_labels:
                self._svc_labels["Voice"].setText("offline")

    # -- Helpers de estilo --
    def apply_theme(self) -> None:
        theme = get_theme()
        ws = "background-color: " + theme.background + ";"
        sf = "background-color: " + theme.surface + ";"
        st = "border: 1px solid " + theme.stroke + ";"
        self.setStyleSheet(
            "QWidget {" + ws + "}QFrame {" + sf + "border-radius: 6px;" + st + "}QLabel {" + theme.text + ";}"
        )
