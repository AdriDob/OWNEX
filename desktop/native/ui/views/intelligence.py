"""Intelligence — native PySide6 view.

Displays the OWNEX Intelligence dashboard with:
- Target intelligence KPIs (targets, findings, operations, activity)
- Threat landscape summary from the mission service
- Refresh action wired to the mission service
"""

from __future__ import annotations

import logging

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.native.services.mission import get_mission
from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView

logger = logging.getLogger("ownex.native.views.intelligence")


class IntelligenceView(BaseView):
    """Intelligence dashboard — threat landscape + opportunity scoring."""

    SECTION = "intelligence"
    TITLE = "Intelligence"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)

        # Layout principal: tarjetas en grid + barra de acciones
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(12)

        # --- Header ---
        header = QFrame()
        header.setObjectName("section-frame")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(8, 8, 8, 8)

        title = QLabel("Intelligence")
        title.setObjectName("section-title")
        title.setFont(QFont("Space Grotesk", 16, QFont.Bold))

        subtitle = QLabel("Threat landscape + opportunity scoring")
        subtitle.setObjectName("section-subtitle")
        subtitle.setFont(QFont("Inter", 10))

        self._source_label = QLabel("Source: --")
        self._source_label.setFont(QFont("Inter", 9))

        hlay.addWidget(title)
        hlay.addWidget(subtitle)
        hlay.addStretch()
        hlay.addWidget(self._source_label)
        main.addWidget(header)

        # --- Grid de KPIs (datos reales del service, nunca hardcoded) ---
        self._cards_frame = QFrame()
        self._cards_frame.setObjectName("section-frame")
        glay = QGridLayout(self._cards_frame)
        glay.setHorizontalSpacing(12)
        glay.setVerticalSpacing(12)
        glay.setContentsMargins(8, 8, 8, 8)

        kpi_defs = [
            ("Targets", "targets"),
            ("Findings", "findings"),
            ("Operations", "opps"),
            ("Activity", "activity"),
            ("Ready to deliver", "ready_to_deliver"),
            ("Status", "status"),
        ]
        self._kpi_labels: dict[str, QLabel] = {}
        for i, (label, key) in enumerate(kpi_defs):
            card = QFrame()
            card.setFixedHeight(80)
            card.setStyleSheet("background: #111318; border-radius: 6px; border: 1px solid #2A2E37;")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(8, 8, 8, 8)
            name = QLabel(label)
            name.setFont(QFont("Inter", 8))
            name.setStyleSheet("color: #8B8D98;")
            value = QLabel("--")
            value.setFont(QFont("Inter", 14))
            value.setStyleSheet("color: #00D5FF;")
            cl.addWidget(name)
            cl.addStretch()
            cl.addWidget(value)
            self._kpi_labels[key] = value
            glay.addWidget(card, i // 2, i % 2)
        main.addWidget(self._cards_frame, 1)

        # --- Barra de acciones ---
        action_bar = QFrame()
        action_bar.setObjectName("section-frame")
        ablay = QHBoxLayout(action_bar)
        ablay.setContentsMargins(8, 8, 8, 8)
        ablay.setSpacing(8)

        scan_hint = QLabel("Scheduler runs in the in-process backend; press Refresh to pull the latest state.")
        scan_hint.setFont(QFont("Inter", 9))
        scan_hint.setStyleSheet("color: #8B8D98;")

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFont(QFont("Inter", 10))
        self._refresh_btn = refresh_btn
        self._refresh_btn.clicked.connect(self.refresh)

        ablay.addWidget(scan_hint)
        ablay.addStretch()
        ablay.addWidget(refresh_btn)
        main.addWidget(action_bar, 0)

        # Aplicar tema
        self.apply_theme()

    # -- Data loading (real data from the mission service) ---------------
    def refresh(self) -> None:
        mission = getattr(self, "mission", None) or get_mission()
        try:
            data = mission.get_dashboard()
        except Exception as exc:  # noqa: BLE001
            logger.warning("intelligence refresh failed: %s", exc)
            self._source_label.setText("Source: error")
            return
        source = str(data.get("source", "local"))
        self._source_label.setText("Source: " + source)
        counts = data.get("counts", {})
        status = data.get("status", {})
        values: dict[str, str] = {
            "targets": str(counts.get("targets", 0)),
            "findings": str(counts.get("findings", 0)),
            "opps": str(counts.get("opps", "n/a")),
            "activity": str(counts.get("activity", 0)),
            "ready_to_deliver": str(counts.get("ready_to_deliver", 0)),
            "status": "running" if status.get("running") else "stopped",
        }
        for key, lbl in self._kpi_labels.items():
            lbl.setText(values.get(key, "--"))

    # -- Helpers de estilo (usando get_theme()) --
    def apply_theme(self) -> None:
        theme = get_theme()

        ws = "background-color: " + theme.text + ";"
        sf = "background-color: " + theme.surface + ";"
        st = "border: 1px solid " + theme.stroke + ";"

        self.setStyleSheet(
            "QWidget {" + ws + "}QFrame {" + sf + "border-radius: 6px;" + st + "}QLabel {" + theme.text + ";}"
        )
