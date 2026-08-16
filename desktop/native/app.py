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
import logging
import os
import sys
from pathlib import Path

import qasync
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

# Allow `import desktop.native...` from the repo root when run as a script.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from desktop.native.ui.icons import RASTRO_ICON_PATH  # noqa: E402
from desktop.native.ui.main_window import MainWindow, native_qss  # noqa: E402

logger = logging.getLogger("ownex.native.app")

# Single source of truth for the window title (matches tokens window_title).
APP_NAME = "OWNEX"
DEFAULT_THEME = "default"
DEFAULT_GEOMETRY = (120, 80, 1280, 760)  # x, y, w, h — adaptive-desktop friendly.


def _load_fonts() -> None:
    """Register vendored V3 brand fonts (Inter / Space Grotesk / JetBrains Mono)."""
    fonts_dir = _REPO_ROOT / "assets/branding/fonts"
    if not fonts_dir.is_dir():
        return
    families_added: set[str] = set()
    for f in sorted(fonts_dir.glob("*.ttf")):
        if f.stem.split("-")[0].lower() in families_added:
            continue
        try:
            QFontDatabase.addApplicationFont(str(f))
            families_added.add(f.stem.split("-")[0].lower())
        except Exception as exc:
            logger.warning("font load failed %s: %s", f.name, exc)


def create_application() -> QApplication:
    QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    if RASTRO_ICON_PATH and Path(RASTRO_ICON_PATH).is_file():
        app.setWindowIcon(QIcon(RASTRO_ICON_PATH))
    _load_fonts()
    return app


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("RASTRRO_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
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
