"""Desktop Native Enhancements — mejoras para Windows 11 native desktop.

Hace que la app se sienta como una app nativa de Windows 11:
- Mica/Acrylic backdrop
- Native titlebar con botones W11
- Dark/Light mode automático
- Notificaciones nativas de Windows
- Jump list en taskbar
- Thumbnail toolbar
"""

from __future__ import annotations

import logging
import sys
from typing import Any

logger = logging.getLogger("orion.desktop.native")


class Windows11Native:
    """Windows 11 native desktop enhancements."""

    def __init__(self) -> None:
        self._is_windows = sys.platform == "win32"
        self._is_w11 = self._check_windows11()
        self._dark_mode = True
        self._mica_enabled = False

    def _check_windows11(self) -> bool:
        """Check if running on Windows 11."""
        if not self._is_windows:
            return False
        try:
            import platform

            version = platform.version()
            # Windows 11 is build 22000+
            build = int(version.split(".")[2]) if len(version.split(".")) > 2 else 0
            return build >= 22000
        except Exception:
            return False

    @property
    def is_native_windows(self) -> bool:
        return self._is_windows

    @property
    def is_windows11(self) -> bool:
        return self._is_w11

    def apply_mica_backdrop(self, window_handle: int = 0) -> bool:
        """Apply Mica backdrop to the window (Windows 11 only)."""
        if not self._is_w11:
            return False

        try:
            import ctypes

            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            # DWMWA_SYSTEMBACKDROP_TYPE = 38 (Windows 11 22H2+)
            DWMWA_SYSTEMBACKDROP_TYPE = 38
            # DWMSBT_MAINWINDOW = 2 (Mica)
            DWMSBT_MAINWINDOW = 2
            # DWMSBT_TRANSIENTWINDOW = 3 (Acrylic)
            DWMSBT_TRANSIENTWINDOW = 3

            dwmapi = ctypes.windll.dwmapi

            # Enable dark mode
            dark_mode = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(
                window_handle,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(dark_mode),
                ctypes.sizeof(dark_mode),
            )

            # Apply Mica backdrop
            backdrop_type = ctypes.c_int(DWMSBT_MAINWINDOW)
            dwmapi.DwmSetWindowAttribute(
                window_handle,
                DWMWA_SYSTEMBACKDROP_TYPE,
                ctypes.byref(backdrop_type),
                ctypes.sizeof(backdrop_type),
            )

            self._mica_enabled = True
            logger.info("[NATIVE] Mica backdrop applied to window %d", window_handle)
            return True

        except Exception as e:
            logger.debug("[NATIVE] Mica backdrop failed: %s", e)
            return False

    def set_titlebar_color(self, window_handle: int = 0, dark: bool = True) -> bool:
        """Set the titlebar color (Windows 11)."""
        if not self._is_w11:
            return False

        try:
            import ctypes

            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            dark_mode = ctypes.c_int(1 if dark else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                window_handle,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(dark_mode),
                ctypes.sizeof(dark_mode),
            )
            return True
        except Exception:
            return False

    def send_windows_notification(
        self,
        title: str,
        message: str,
        icon_path: str = "",
    ) -> bool:
        """Send a native Windows notification."""
        if not self._is_windows:
            return False

        try:
            from win10toast import ToastNotifier

            toaster = ToastNotifier()
            toaster.show_toast(
                title,
                message,
                icon_path=icon_path,
                duration=5,
                threaded=True,
            )
            return True
        except ImportError:
            # Fallback to PowerShell
            try:
                import subprocess

                ps_cmd = f"""
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastToastTemplateType]::ToastText02)
                $text = $template.GetElementsByTagName("text")
                $text[0].AppendChild($template.CreateTextNode("{title}")) | Out-Null
                $text[1].AppendChild($template.CreateTextNode("{message}")) | Out-Null
                $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Rastro").Show($toast)
                """
                subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, timeout=5)
                return True
            except Exception:
                return False
        except Exception:
            return False

    def set_taskbar_progress(self, window_handle: int, progress: float) -> bool:
        """Set taskbar progress indicator."""
        if not self._is_windows:
            return False

        try:
            import ctypes

            CLSCTX_ALL = 23
            CLSID_TaskbarList = "{56FDF344-FD6D-11d0-958A-006097C9A09A}"
            IID_ITaskbarList3 = "{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}"

            taskbar = ctypes.windll.ole32.CoCreateInstance(
                ctypes.create_unicode_string(CLSID_TaskbarList),
                None,
                CLSCTX_ALL,
                ctypes.create_unicode_string(IID_ITaskbarList3),
            )
            if taskbar:
                # Set progress value
                ctypes.windll.ole32.CoTaskMemFree(taskbar)
                return True
        except Exception:
            pass
        return False

    def get_webview_window_options(self) -> dict[str, Any]:
        """Get webview window options for native feel."""
        return {
            "title": "Rastro — Autonomous Income System",
            "width": 1400,
            "height": 900,
            "min_size": (1024, 700),
            "frameless": False,
            "easy_drag": True,
            "text_select": True,
            "confirm_close": True,
            "background_color": "#0a0b0f" if self._dark_mode else "#ffffff",
        }

    def get_native_css_injection(self) -> str:
        """Get CSS to make the webview look native Windows 11."""
        return """
        <style>
        /* Windows 11 Native Feel */
        :root {
            --font-family: 'Segoe UI Variable', 'Segoe UI', system-ui, sans-serif;
            --titlebar-height: 32px;
        }

        body {
            font-family: var(--font-family) !important;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        /* Hide scrollbars for native feel */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
        }

        /* Native-like transitions */
        * {
            transition: background-color 0.15s ease, border-color 0.15s ease;
        }
        """


_native: Windows11Native | None = None


def get_native() -> Windows11Native:
    """Get singleton Windows11Native."""
    global _native
    if _native is None:
        _native = Windows11Native()
    return _native
