"""OWNEX/Rastro Desktop — native shell (PySide6/Qt, no WebView, no browser).

Entry point for the native desktop application. Replaces the legacy web-based
shells (pywebview browser fallback, Vite dev server, Tauri WebView, FastAPI HTTP).

Architecture:
  - PySide6.QtWidgets QApplication (native, CPU-only)
  - qasync.QEventLoop bridges Qt <-> asyncio
  - In-process services (desktop.native.services.*) wrap the backend engines
  - No HTTP server, no browser, no localhost UI
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import sys
from pathlib import Path

import qasync
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

logger = logging.getLogger("ownex.native.app")

from desktop.native.services.backend import start_backend_async  # noqa: E402
from desktop.native.ui.icons import RASTRO_ICON_PATH  # noqa: E402
from desktop.native.ui.main_window import MainWindow, native_qss  # noqa: E402

# ── Data & Log Directories ──────────────────────────────────────
# Windows: %APPDATA%/OWNEX/
# POSIX:  ~/.config/OWNEX/
if sys.platform.startswith("win"):
    _DATA_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "OWNEX"
else:
    _DATA_DIR = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "OWNEX"
_LOG_DIR = _DATA_DIR / "logs"
_DATABASE_DIR = _DATA_DIR  # DB lives alongside other data
_DATABASE_DIR.mkdir(parents=True, exist_ok=True)
_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure file logging (Qt windowed apps lose stderr)
_LOG_FILE = _DATA_DIR / "logs" / "app.log"
_file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
_file_handler.setLevel(logging.INFO)
_file_formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
_file_handler.setFormatter(_file_formatter)
logger.addHandler(_file_handler)

APP_NAME = "OWNEX"
DEFAULT_THEME = "default"
DEFAULT_GEOMETRY = (120, 80, 1280, 760)  # x, y, w, h — adaptive-desktop friendly.


# ── Font Registration ───────────────────────────────────────────
def _register_vendored_fonts() -> None:
    """Register vendored V3 brand fonts (Inter / Space Grotesk / JetBrains Mono)."""
    fonts_dir = Path(__file__).parent.parent / "assets/branding/fonts"
    if not fonts_dir.is_dir():
        return
    for f in sorted(fonts_dir.glob("*.ttf")):
        with contextlib.suppress(Exception):
            QFontDatabase.addApplicationFont(str(f))


# ── Application Factory ─────────────────────────────────────────
def create_application() -> QApplication:
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    if RASTRO_ICON_PATH and Path(RASTRO_ICON_PATH).is_file():
        app.setWindowIcon(QIcon(RASTRO_ICON_PATH))
    _register_vendored_fonts()
    return app


# ── Main ────────────────────────────────────────────────────────
def main() -> int:
    start_backend_async()
    app = create_application()
    window = MainWindow(theme_name=os.environ.get("OWNEX_THEME", DEFAULT_THEME))
    x, y, w, h = DEFAULT_GEOMETRY
    window.setGeometry(x, y, w, h)
    window.show()
    window.setStyleSheet(native_qss())
    with qasync.QEventLoop(app) as loop:
        asyncio.set_event_loop(loop)
        # Ensure in-process services initialize on the event loop.
        QTimer.singleShot(0, lambda: None)
        return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
