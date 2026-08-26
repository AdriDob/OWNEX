"""Settings view for OWNEX Desktop.

Allows basic configuration: theme selection, data directory info, and
application version.  Minimal interface — the full settings flow will be
expanded in a later phase.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QVBoxLayout, QWidget

from desktop.native.services.mission import get_mission
from desktop.native.ui.tokens import get_registry


class SettingsView(QWidget):
    """Widget shown when the user selects «Settings» in the navigation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setObjectName("SettingsView")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("Configuración")
        title.setStyleSheet("font-family: 'Space Grotesk'; font-size: 20pt; font-weight: Bold; color: #00D5FF;")
        layout.addWidget(title)

        # Theme selector
        theme_label = QLabel("Tema")
        theme_label.setStyleSheet("font-size: 12pt; color: #C0C8D8;")
        layout.addWidget(theme_label)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(
            [
                "default",
                "tesla",
                "event_horizon",
                "executive_intelligence",
                "neural_flow",
                "precision_lab",
                "quantum_glass",
            ]
        )
        # Pre-select current theme
        current_theme = get_registry().current_name
        idx = self._theme_combo.findText(current_theme)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        layout.addWidget(self._theme_combo)

        # Version info + backend state (real health from the mission service)
        ver_label = QLabel("OWNEX Desktop v7.0.0")
        ver_label.setStyleSheet("font-size: 11pt; color: #8B8D98; margin-top: 12px;")
        layout.addWidget(ver_label)

        self._backend_label = QLabel("Backend: checking...")
        self._backend_label.setStyleSheet("font-size: 10pt; color: #8B8D98;")
        layout.addWidget(self._backend_label)
        self._refresh_backend()

        # Initial theme application
        self.apply_theme()

    def _refresh_backend(self) -> None:
        try:
            health = get_mission().get_health()
        except Exception:  # noqa: BLE001
            health = {}
        status = str(health.get("status", "offline"))
        version = str(health.get("version", ""))
        if status == "ok":
            self._backend_label.setText(f"Backend: online (v{version})" if version else "Backend: online")
        else:
            self._backend_label.setText("Backend: offline — Mission Control shows local data")

    def _on_theme_changed(self, index: int) -> None:
        themes = [
            "default",
            "tesla",
            "event_horizon",
            "executive_intelligence",
            "neural_flow",
            "precision_lab",
            "quantum_glass",
        ]
        name = themes[index] if 0 <= index < len(themes) else "default"
        get_registry().set_current(name)
        self.apply_theme()

    def apply_theme(self) -> None:
        # Delegated to the native QSS builder in main_window
        from desktop.native.ui.main_window import native_qss  # late import to avoid circulars

        self.setStyleSheet(native_qss())
