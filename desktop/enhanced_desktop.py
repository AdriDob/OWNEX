"""Desktop Enhanced Entry Point — native Windows 11 experience with all modules.

Integrates:
- Backend (FastAPI + scheduler)
- Frontend (Vue.js native-styled)
- System tray with full controls
- Windows 11 Mica/Acrylic
- Auto-start on boot
- Auto-updater
- All auto modules wired
"""

from __future__ import annotations

import asyncio
import logging
import threading

logger = logging.getLogger("orion.desktop.enhanced")


class EnhancedDesktop:
    """Full native Windows 11 desktop experience."""

    def __init__(self) -> None:
        self._server_thread = None
        self._scheduler_thread = None
        self._tray = None
        self._webview = None
        self._running = False

    async def start(self) -> None:
        """Start the enhanced desktop app."""
        logger.info("[DESKTOP] Starting Enhanced Desktop...")

        # 1. Start backend server
        self._start_server()

        # 2. Start scheduler
        self._start_scheduler()

        # 3. Start system tray
        self._start_tray()

        # 4. Create native window
        self._create_window()

        self._running = True
        logger.info("[DESKTOP] Enhanced Desktop started")

    def _start_server(self) -> None:
        """Start the FastAPI backend server."""
        try:
            from api.main import app
            from desktop.main_desktop import ServerThread

            self._server_thread = ServerThread("127.0.0.1", 8000)
            self._server_thread.start(app)
            logger.info("[DESKTOP] Backend server started on :8000")
        except Exception as e:
            logger.error("[DESKTOP] Server start failed: %s", e)

    def _start_scheduler(self) -> None:
        """Start the LifeScheduler with all jobs."""
        try:
            from core.scheduler.jobs import get_all_jobs
            from core.scheduler.life_scheduler import get_life_scheduler

            scheduler = get_life_scheduler()
            all_jobs = get_all_jobs()

            for _cycle, jobs in all_jobs.items():
                for job in jobs:
                    scheduler.register(job)

            # Run scheduler in background thread
            self._scheduler_thread = threading.Thread(
                target=lambda: asyncio.run(self._run_scheduler(scheduler)),
                daemon=True,
                name="orion-scheduler",
            )
            self._scheduler_thread.start()
            logger.info("[DESKTOP] Scheduler started with jobs from all cycles")
        except Exception as e:
            logger.error("[DESKTOP] Scheduler start failed: %s", e)

    async def _run_scheduler(self, scheduler) -> None:
        """Run the scheduler loop."""
        try:
            await scheduler.start()
        except Exception as e:
            logger.error("[DESKTOP] Scheduler error: %s", e)

    def _start_tray(self) -> None:
        """Start the system tray."""
        try:
            from desktop.tray import start_tray

            self._tray = start_tray(
                on_open_dashboard=self._open_dashboard,
                on_quit=self.stop,
            )
            logger.info("[DESKTOP] System tray started")
        except Exception as e:
            logger.warning("[DESKTOP] Tray not available: %s", e)

    def _create_window(self) -> None:
        """Create the native webview window."""
        try:
            import webview

            from desktop.native_w11 import get_native

            native = get_native()
            native.get_native_css_injection()

            window = webview.create_window(
                title="Rastro — Autonomous Income System",
                url="http://127.0.0.1:8000",
                width=1400,
                height=900,
                min_size=(1024, 700),
                frameless=False,
                easy_drag=True,
                background_color="#0a0b0f",
            )

            self._webview = window

            # Apply Windows 11 enhancements
            if native.is_windows11:
                webview.start(
                    func=lambda: self._apply_native_enhancements(window),
                    gui="edgechromium",
                )
            else:
                webview.start(gui="edgechromium")

        except ImportError:
            logger.error("[DESKTOP] pywebview not installed. Run: pip install pywebview")
        except Exception as e:
            logger.error("[DESKTOP] Window creation failed: %s", e)

    def _apply_native_enhancements(self, window) -> None:
        """Apply Windows 11 native enhancements after window creation."""
        try:
            from desktop.native_w11 import get_native

            native = get_native()

            # Get window handle
            import ctypes

            hwnd = ctypes.windll.user32.GetForegroundWindow()

            # Apply Mica backdrop
            native.apply_mica_backdrop(hwnd)

            # Set dark titlebar
            native.set_titlebar_color(hwnd, dark=True)

            logger.info("[DESKTOP] Windows 11 native enhancements applied")
        except Exception as e:
            logger.debug("[DESKTOP] Native enhancements skipped: %s", e)

    def _open_dashboard(self) -> None:
        """Open the dashboard in the webview."""
        try:
            import webview

            webview.create_window(
                "Rastro — Dashboard",
                url="http://127.0.0.1:8000",
                width=1400,
                height=900,
            )
            webview.start()
        except Exception as e:
            logger.error("[DESKTOP] Dashboard open failed: %s", e)

    def stop(self) -> None:
        """Stop the enhanced desktop."""
        self._running = False
        logger.info("[DESKTOP] Stopping Enhanced Desktop...")

        if self._server_thread:
            self._server_thread.stop()

        logger.info("[DESKTOP] Enhanced Desktop stopped")


_desktop: EnhancedDesktop | None = None


def get_desktop() -> EnhancedDesktop:
    """Get singleton EnhancedDesktop."""
    global _desktop
    if _desktop is None:
        _desktop = EnhancedDesktop()
    return _desktop


def main() -> None:
    """Main entry point for enhanced desktop."""
    desktop = get_desktop()
    asyncio.run(desktop.start())


if __name__ == "__main__":
    main()
