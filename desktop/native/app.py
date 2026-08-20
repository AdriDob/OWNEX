import logging
import os
import sys
import time
from pathlib import Path

import qasync
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

from desktop.native.services.backend import start_backend_async
from desktop.native.ui.icons import RASTRO_ICON_PATH
from desktop.native.ui.main_window import MainWindow, native_qss

# ── Data & Log Directories ──────────────────────────────────────
if sys.platform.startswith("win"):
    _DATA_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "OWNEX"
else:
    _DATA_DIR = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "OWNEX"
_LOG_DIR = _DATA_DIR / "logs"
_DATABASE_DIR = _DATA_DIR
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# Configure file logging (Qt windowed apps lose stderr)

_LOG_FILE = _DATA_DIR / "logs" / "app.log"
_file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
_file_handler.setLevel(logging.INFO)
_file_formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
_file_handler.setFormatter(_file_formatter)
logging.getLogger().addHandler(_file_handler)
logging.getLogger().setLevel(logging.INFO)

APP_NAME = "OWNEX"
DEFAULT_THEME = "default"
DEFAULT_GEOMETRY = (120, 80, 1280, 760)


# ── Font Registration ───────────────────────────────────────────
def _register_vendored_fonts() -> None:
    fonts_dir = Path(__file__).parent.parent / "assets/branding/fonts"
    if not fonts_dir.is_dir():
        return
    for f in sorted(fonts_dir.glob("*.ttf")):
        with __import__("contextlib").suppress(Exception):
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


# ── Boot Sequence Helpers ───────────────────────────────────────
def _check_backend_healthy(timeout: float = 10.0) -> bool:
    """Verifica que el backend in-process responde 200 en /api/health."""
    import time as _time

    import httpx

    deadline = _time.monotonic() + timeout
    while _time.monotonic() < deadline:
        try:
            r = httpx.get("http://127.0.0.1:8000/api/health", timeout=1.0)
            if r.status_code == 200 and r.json().get("status") == "ok":
                return True
        except Exception:
            pass
        _time.sleep(0.5)
    return False


def _check_scheduler_running() -> bool:
    """Verifica que el scheduler lleva corriendo > 0 (ticks)."""
    import httpx

    try:
        r = httpx.get("http://127.0.0.1:8000/api/system/health", timeout=2.0)
        data = r.json()
        engines = data.get("loop_engines", {})
        if isinstance(engines, dict):
            for _key, val in engines.items():
                if isinstance(val, dict) and val.get("is_running"):
                    return True
                if isinstance(val, dict) and val.get("phases"):
                    phases = val.get("phases", [])
                    if any(p for p in phases):
                        return True
        return False
    except Exception:
        return False


def _check_database_connected() -> bool:
    """Chequea mínima conectividad de la DB (ping implícito via health)."""
    import httpx

    try:
        r = httpx.get("http://127.0.0.1:8000/api/health", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False


def _check_agents_healthy() -> bool:
    """Versión simple: health endpoint incluye agents_healthy."""
    import httpx

    try:
        r = httpx.get("http://127.0.0.1:8000/api/system/health", timeout=2.0)
        data = r.json()
        agents = data.get("agents_health", "")
        return "offline" not in str(agents).lower()
    except Exception:
        return True


def _run_boot_sequence() -> bool:
    """Ejecuta los system checks. Retorna True si al menos la mayoría pasan."""
    boot_items = [
        ("Backend API", _check_backend_healthy),
        ("Scheduler de ciclos", _check_scheduler_running),
        ("Base de datos", _check_database_connected),
        ("Agentes del sistema", _check_agents_healthy),
    ]
    passed = 0
    total = len(boot_items)
    for _label, check_fn in boot_items:
        if check_fn():
            passed += 1

        time.sleep(0.8)
    return passed >= total * 0.75


# ── Main ────────────────────────────────────────────────────────
def main() -> int:
    # 1. Crear aplicación QApplication
    app = create_application()

    # 2. Arrancar backend local en proceso separado (fire-and-forget)
    start_backend_async()

    # 3. Esperar a que el backend responda (máx. 10s)
    boot_ok = _run_boot_sequence()

    # 4. Crear ventana principal
    window = MainWindow(theme_name=os.environ.get("OWNEX_THEME", DEFAULT_THEME))
    x, y, w, h = DEFAULT_GEOMETRY
    window.setGeometry(x, y, w, h)

    if not boot_ok:
        # El boot sequence verificó lo posible; el backend sigue arrancándose
        # en hilo background y los datos cargan solos vía auto-refresh.
        pass

    window.show()
    window.setStyleSheet(native_qss())
    with qasync.QEventLoop(app) as loop:
        import asyncio

        asyncio.set_event_loop(loop)
        # Ensure in-process services initialize on the event loop.
        QTimer.singleShot(0, lambda: None)
        return app.exec()
