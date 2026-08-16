"""Intelligence — native PySide6 view.

Lays out the OWNEX Intelligence dashboard with:
- Target intelligence cards (targets + opportunity scores)
- Threat landscape summary
- Platform analysis grid
- Quick action bar

Responsive: single-column on mobile, multi-column on desktop.
"""

from __future__ import annotations

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

from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView


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

        hlay.addWidget(title)
        hlay.addStretch()
        hlay.addWidget(subtitle)
        main.addWidget(header)

        # --- Grid de cards ---
        self._cards_frame = QFrame()
        self._cards_frame.setObjectName("section-frame")
        glay = QGridLayout(self._cards_frame)
        glay.setHorizontalSpacing(12)
        glay.setVerticalSpacing(12)
        glay.setContentsMargins(8, 8, 8, 8)
        # Placeholder: 3x2 grid de cards vacías (se poblarán desde el service)
        for _ in range(6):
            card = QFrame()
            card.setFixedHeight(80)
            card.setStyleSheet("background: #111318; border-radius: 6px; border: 1px solid #2A2E37;")
            glay.addWidget(card, _ // 2, _ % 2)
        main.addWidget(self._cards_frame, 1)

        # --- Barra de acciones ---
        action_bar = QFrame()
        action_bar.setObjectName("section-frame")
        ablay = QHBoxLayout(action_bar)
        ablay.setContentsMargins(8, 8, 8, 8)
        ablay.setSpacing(8)
        scan_btn = QPushButton("Scan Targets")
        scan_btn.setFont(QFont("Inter", 10))
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFont(QFont("Inter", 10))
        ablay.addWidget(scan_btn)
        ablay.addStretch()
        ablay.addWidget(refresh_btn)
        main.addWidget(action_bar, 0)

        # Conexión lazy al service (se hará desde el shell)
        self._scan_connected = False

        # Aplicar tema
        self.apply_theme()

    # -- Helpers de estilo (usando get_theme()) --
    def apply_theme(self) -> None:
        theme = get_theme()

        ws = "background-color: " + theme.text + ";"
        sf = "background-color: " + theme.surface + ";"
        st = "border: 1px solid " + theme.stroke + ";"

        self.setStyleSheet(
            "QWidget {" + ws + "}QFrame {" + sf + "border-radius: 6px;" + st + "}QLabel {" + theme.text + ";}"
        )
