"""Native Application Shell — MainWindow.

Implements the OWNEX desktop shell spec:
  - Native sidebar with grouped, lazy-loaded section navigation
  - Top bar with project context + engine status
  - Central stacked widget (QStackedWidget) for views
  - Native status bar
  - System tray icon

No WebView, no HTTP server, no browser. Views are PySide6 QWidgets that
consume in-process services via desktop.native.services.*.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from desktop.native.ui.icons import RASTRO_ICON_PATH
from desktop.native.ui.navigation import NAVIGATION, SECTIONS
from desktop.native.ui.tokens import get_registry, get_theme
from desktop.native.ui.views.base import load_view

# ── Minimal Layout & Spacing Constants ─────────────────────────────
LAYOUT = type(
    "Layout",
    (),
    {
        "sidebar_width_default": 220,
        "content_max_width": 1080,
        "topbar_height": 48,
        "statusbar_height": 28,
    },
)()

SPACING = type(
    "Spacing",
    (),
    {
        "size_0": 0,
        "size_4": 4,
        "size_8": 8,
        "size_12": 12,
        "size_16": 16,
        "size_20": 20,
        "size_24": 24,
    },
)

# ── Global Singleton ──────────────────────────────────────────────
_Singleton: Any = None


def get_singleton() -> Any:
    global _Singleton
    if _Singleton is None:
        _Singleton = {}
    return _Singleton


# ── Font Registration ──────────────────────────────────────────────
def _register_vendored_fonts() -> None:
    """Register vendored V3 brand fonts (Inter / Space Grotesk / JetBrains Mono)."""
    fonts_dir = Path(__file__).parent.parent / "assets/branding/fonts"
    if not fonts_dir.is_dir():
        return
    for f in sorted(fonts_dir.glob("*.ttf")):
        with contextlib.suppress(Exception):
            QFontDatabase.addApplicationFont(str(f))


# ── QSS Builder (pure string concat, zero f-strings with theme attrs) ─────────────
def _qss(theme) -> str:
    """Build a minimal QSS snippet using plain string concatenation only."""
    # We never embed theme attributes inside f-string braces in source.
    # Instead we compose the final string via .format() with a pre-built dict,
    # or pure concatenation. Here we use pure concatenation for maximum safety.
    parts = []
    # Widget background
    parts.append("QWidget {background-color: " + theme.background + ";}")
    # Frame/surface
    parts.append(
        "QFrame {background-color: " + theme.surface + "; border-radius: 6px; border: 1px solid " + theme.stroke + ";}"
    )
    # Label text
    parts.append("QLabel {color: " + theme.text + ";}")
    # Pushbutton
    parts.append(
        "QPushButton {"
        "background-color: "
        + theme.surface
        + "; color: "
        + theme.text
        + "; border: 1px solid "
        + theme.stroke
        + "; border-radius: 6px; padding: 6px 12px;}"
    )
    parts.append("QPushButton:hover {background-color: " + theme.surface_alt + ";}")
    # Combo box
    parts.append(
        "QComboBox {"
        "background-color: "
        + theme.surface
        + "; color: "
        + theme.text
        + "; border: 1px solid "
        + theme.stroke
        + "; border-radius: 4px; padding: 4px 8px; font-family: 'Inter'; font-size: 12pt;}"
    )
    parts.append("QComboBox QAbstractItemView {background-color: " + theme.surface + "; color: " + theme.text + ";}")
    return "\n".join(parts)


# ── MainWindow Class ──────────────────────────────────────────────


# ── Native QSS Builder ──────────────────────────────────────────
def native_qss() -> str:
    """Return the QSS string for the active theme, generated from token values.

    Reads the currently active ThemeSpec from the ThemeRegistry and produces
    platform-native QSS using pure string concatenation (safe for PyInstaller
    bundles). The theme changes take effect without restarting the application.
    """
    theme = get_registry().current()
    # Use theme tokens via pure concatenation (safe for PyInstaller bundles)
    bg_color = theme.background
    surface_color = theme.surface
    text_color = theme.text
    stroke_color = theme.stroke
    surface_alt_color = theme.surface_alt
    return (
        "QWidget { background-color: " + bg_color + "; }"
        "QFrame { background-color: "
        + surface_color
        + "; border-radius: 6px; border: 1px solid "
        + stroke_color
        + "; }"
        "QTableWidget { background-color: "
        + surface_color
        + "; border-radius: 6px; border: 1px solid "
        + stroke_color
        + "; gridline-color: "
        + stroke_color
        + "; }"
        "QHeaderView::section { background-color: "
        + surface_alt_color
        + "; color: "
        + text_color
        + "; border: none; padding: 4px; }"
        "QPushButton { background-color: "
        + surface_color
        + "; color: "
        + text_color
        + "; border: 1px solid "
        + stroke_color
        + "; border-radius: 6px; padding: 6px 12px; }"
        "QPushButton:hover { background-color: " + surface_alt_color + "; }"
        "QLabel { color: " + text_color + "; }"
    )


class MainWindow(QMainWindow):
    """Native OWNEX Desktop MainWindow."""

    view_switched = Signal(str)
    theme_changed = Signal(str)

    def __init__(self, theme_name: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)

        self.setWindowTitle("OWNEX Desktop")
        _register_vendored_fonts()
        if RASTRO_ICON_PATH and Path(RASTRO_ICON_PATH).is_file():
            self.setWindowIcon(QIcon(RASTRO_ICON_PATH))

        self._theme_name = theme_name or get_registry().current().name
        self.theme_changed.emit(self._theme_name)

        # --- Sidebar ---
        self._sidebar = QFrame()
        self._sidebar.setFixedWidth(LAYOUT.sidebar_width_default)
        self._sidebar.setStyleSheet("QFrame { background: " + get_theme().surface + "; border: none; }")
        sidebar_layout = QVBoxLayout(self._sidebar)
        sidebar_layout.setContentsMargins(SPACING.size_4, SPACING.size_4, SPACING.size_4, SPACING.size_4)
        sidebar_layout.setSpacing(SPACING.size_4)

        self._nav_buttons: dict[str, QPushButton] = {}
        self._view_stack = QStackedWidget()

        for _, section in SECTIONS:
            nav_cfg = next((n for n in NAVIGATION if n.section == section), None)
            if not nav_cfg:
                continue
            btn = QPushButton(nav_cfg.label)
            btn.setFixedHeight(40)
            btn.setCheckable(True)
            btn.setProperty("section", section)
            btn.clicked.connect(lambda checked, s=section: self._on_nav_clicked(s))
            if section == SECTIONS[0][1]:
                btn.setChecked(True)
            self._nav_buttons[section] = btn
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()
        self._sidebar.setLayout(sidebar_layout)

        # --- Top Bar ---
        self._top_bar = QFrame()
        self._top_bar.setFixedHeight(LAYOUT.topbar_height)
        self._top_bar.setStyleSheet("QFrame { background: " + get_theme().surface + "; border: none; }")
        top_layout = QHBoxLayout(self._top_bar)
        top_layout.setContentsMargins(SPACING.size_4, 0, SPACING.size_4, 0)
        top_layout.setSpacing(SPACING.size_4)

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
        self._theme_combo.setFixedWidth(180)
        self._theme_combo.setStyleSheet(
            "QComboBox { background: #111318; color: #F6F8FB; border: 1px solid #2A2E37; border-radius: 4px; padding: 4px 8px; }"
            "QComboBox QAbstractItemView { background: #111318; color: #F6F8FB; }"
        )
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        top_layout.addWidget(QLabel("Theme:"))
        top_layout.addWidget(self._theme_combo)

        self._app_name = QLabel("OWNEX Desktop")
        self._app_name.setStyleSheet(
            "color: #00D5FF; font-family: 'Space Grotesk'; font-size: 12pt; font-weight: Bold;"
        )
        top_layout.addWidget(self._app_name)
        top_layout.addStretch()

        # --- Central Widget ---
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self._sidebar)
        central_layout.addWidget(self._view_stack, 1)
        central_layout.addWidget(self._top_bar, 0)
        self.setCentralWidget(central)

        # --- Status Bar ---
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("OWNEX Desktop Ready")

        # --- Signals ---
        self.view_switched.connect(self._on_view_switched)
        self.theme_changed.connect(self._on_theme_changed_internal)

        # --- Auto-refresh: while the in-process backend boots, periodically
        # refresh the active view so real data appears as soon as it is ready.
        self._auto_refresh = QTimer(self)
        self._auto_refresh.setInterval(10000)
        self._auto_refresh.timeout.connect(self._refresh_active_view)
        self._auto_refresh.start()

        # Initialize
        self._on_nav_clicked(SECTIONS[0][1])
        self.apply_theme()

    def _refresh_active_view(self) -> None:
        current = self._view_stack.currentWidget()
        if current is not None and hasattr(current, "refresh"):
            with contextlib.suppress(Exception):
                current.refresh()

    def apply_theme(self) -> None:
        # Use the native QSS builder that reads from the active ThemeSpec.
        # Antiguamente usaba _qss(), pero este último aplicaba theme.text sobre
        # QWidget mientras que native_qss() usa theme.background. Para que el
        # cambio de tema en runtime sea coherente, delegamos a native_qss().
        self.setStyleSheet(native_qss())

    # --- Navigation ---
    def _on_nav_clicked(self, section: str) -> None:
        for sec, btn in self._nav_buttons.items():
            btn.setChecked(sec == section)
        view = load_view(section)
        if view is None:
            view = QWidget()
            lay = QVBoxLayout(view)
            lay.addWidget(QLabel("Section: " + section + " (view under construction)"))
        self._view_stack.addWidget(view)
        self._view_stack.setCurrentWidget(view)
        if hasattr(view, "refresh"):
            with contextlib.suppress(Exception):
                view.refresh()
        self.view_switched.emit(section)
        self._status_bar.showMessage("Section: " + section)

    # --- View Switched ---
    def _on_view_switched(self, section: str) -> None:
        self._status_bar.showMessage("Section: " + section)

    # --- Theme ---
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
        self._theme_name = name
        self.theme_changed.emit(name)

    def _on_theme_changed_internal(self, name: str) -> None:
        self._theme_name = name
        self._theme_combo.setCurrentText(name)
        self.apply_theme()
        current = self._view_stack.currentWidget()
        if current is not None and hasattr(current, "apply_theme"):
            current.apply_theme()
