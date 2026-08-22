import logging
import os
import sys
import time
import traceback
from pathlib import Path

# ── CRASH LOG: write to file BEFORE any imports that might fail ──
_CRASH_LOG = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "OWNEX" / "logs" / "crash.log"
_CRASH_LOG.parent.mkdir(parents=True, exist_ok=True)

def _log_crash(msg: str) -> None:
    try:
        with open(_CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass

_log_crash("=== OWNEX ENTRY POINT ===")
_log_crash(f"Python: {sys.version}")
_log_crash(f"Platform: {sys.platform}")
_log_crash(f"Frozen: {getattr(sys, 'frozen', False)}")
_log_crash(f"CWD: {os.getcwd()}")
_log_crash(f"sys.executable: {sys.executable}")
_log_crash(f"sys.path: {sys.path[:3]}")

try:
    import qasync
    _log_crash("qasync imported OK")
except Exception as e:
    _log_crash(f"qasync IMPORT FAILED: {e}")
    raise

try:
    from PySide6.QtCore import Qt, QTimer
    _log_crash("PySide6.QtCore imported OK")
except Exception as e:
    _log_crash(f"PySide6.QtCore IMPORT FAILED: {e}")
    raise

try:
    from PySide6.QtGui import QFontDatabase, QIcon
    _log_crash("PySide6.QtGui imported OK")
except Exception as e:
    _log_crash(f"PySide6.QtGui IMPORT FAILED: {e}")
    raise

try:
    from PySide6.QtWidgets import QApplication
    _log_crash("PySide6.QtWidgets imported OK")
except Exception as e:
    _log_crash(f"PySide6.QtWidgets IMPORT FAILED: {e}")
    raise

try:
    from desktop.native.services.backend import start_backend_async
    _log_crash("backend imported OK")
except Exception as e:
    _log_crash(f"backend IMPORT FAILED: {e}")
    raise

try:
    from desktop.native.ui.icons import RASTRO_ICON_PATH
    _log_crash(f"icons imported OK, RASTRO_ICON_PATH={RASTRO_ICON_PATH}")
except Exception as e:
    _log_crash(f"icons IMPORT FAILED: {e}")
    raise

try:
    from desktop.native.ui.main_window import MainWindow, native_qss
    _log_crash("MainWindow imported OK")
except Exception as e:
    _log_crash(f"MainWindow IMPORT FAILED: {e}")
    raise

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
    _log_crash("main() START")

    # 1. Crear aplicación QApplication
    try:
        _log_crash("Creating QApplication...")
        app = create_application()
        _log_crash(f"QApplication created: {app}")
    except Exception as e:
        _log_crash(f"QApplication CREATION FAILED: {e}\n{traceback.format_exc()}")
        raise

    # 2. Arrancar backend local en proceso separado (fire-and-forget)
    try:
        _log_crash("Starting backend async...")
        start_backend_async()
        _log_crash("Backend async started")
    except Exception as e:
        _log_crash(f"Backend start FAILED: {e}\n{traceback.format_exc()}")
        # Don't raise - backend is optional for GUI

    # 3. Esperar a que el backend responda (máx. 10s)
    try:
        _log_crash("Running boot sequence...")
        boot_ok = _run_boot_sequence()
        _log_crash(f"Boot sequence result: {boot_ok}")
    except Exception as e:
        _log_crash(f"Boot sequence FAILED: {e}\n{traceback.format_exc()}")
        boot_ok = False

    # 4. Crear ventana principal
    try:
        _log_crash("Creating MainWindow...")
        window = MainWindow(theme_name=os.environ.get("OWNEX_THEME", DEFAULT_THEME))
        _log_crash(f"MainWindow created: {window}")
        x, y, w, h = DEFAULT_GEOMETRY
        window.setGeometry(x, y, w, h)
        _log_crash(f"Window geometry set: {x},{y},{w},{h}")
    except Exception as e:
        _log_crash(f"MainWindow CREATION FAILED: {e}\n{traceback.format_exc()}")
        raise

    if not boot_ok:
        _log_crash("Boot sequence did not pass, continuing anyway")

    try:
        _log_crash("Calling window.show()...")
        window.show()
        _log_crash("window.show() called")
    except Exception as e:
        _log_crash(f"window.show() FAILED: {e}\n{traceback.format_exc()}")
        raise

    try:
        _log_crash("Setting stylesheet...")
        window.setStyleSheet(native_qss())
        _log_crash("Stylesheet set")
    except Exception as e:
        _log_crash(f"Stylesheet FAILED: {e}\n{traceback.format_exc()}")
        # Don't raise - stylesheet is cosmetic

    try:
        _log_crash("Creating qasync event loop...")
        with qasync.QEventLoop(app) as loop:
            import asyncio
            asyncio.set_event_loop(loop)
            _log_crash("Event loop created, starting app.exec()...")
            QTimer.singleShot(0, lambda: None)
            result = app.exec()
            _log_crash(f"app.exec() returned: {result}")
            return result
    except Exception as e:
        _log_crash(f"Event loop FAILED: {e}\n{traceback.format_exc()}")
        raise
