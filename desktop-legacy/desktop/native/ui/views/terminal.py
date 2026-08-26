"""Terminal — native PySide6 shell view (QWebSocket bridge).

Connects to the backend WebSocket terminal endpoint
(ws://127.0.0.1:8000/api/ws/terminal) with PySide6's QWebSocket — no
WebView, no subprocess, no new dependencies. The backend spawns the local
shell (bash/zsh on POSIX, powershell/cmd on Windows) and streams output.

States are honest: Disconnected / Connecting / Connected. If the backend is
offline the view stays Disconnected and the user can retry with
'Start Terminal'. Shell selection is a backend concern (server-side
detection) — this view exposes no fake controls.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QUrl
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtNetwork import QAbstractSocket
from PySide6.QtWebSockets import QWebSocket
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop.native.services.mission import MissionControlData
from desktop.native.ui.tokens import get_theme
from desktop.native.ui.views.base import BaseView

TERMINAL_WS_URL = "ws://127.0.0.1:8000/api/ws/terminal"
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

_STATUS_DISCONNECTED = ("Disconnected", "#FF6B35")
_STATUS_CONNECTING = ("Connecting", "#FFB54D")
_STATUS_CONNECTED = ("Connected", "#00E39A")


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


class TerminalView(BaseView):
    SECTION = "terminal"
    """Terminal/spawn console — native shell bridge."""

    def __init__(self, mission: MissionControlData | None = None, parent: QWidget | None = None) -> None:
        super().__init__(
            mission=mission,
            section="terminal",
            label="Terminal",
            icon="terminal",
            parent=parent,
        )

        self._ws: QWebSocket | None = None

        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(6)

        # --- Barra de conexión ---
        conn = QFrame()
        cl = QHBoxLayout(conn)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(6)

        self._conn_status = QLabel("Disconnected")
        self._conn_status.setFont(QFont("Inter", 9))
        self._set_status(*_STATUS_DISCONNECTED)

        self._connect_btn = QPushButton("Start Terminal")
        self._connect_btn.setFont(QFont("Inter", 9))
        self._connect_btn.setFixedWidth(130)
        self._connect_btn.clicked.connect(self._on_start)

        cl.addWidget(self._conn_status)
        cl.addStretch(1)
        cl.addWidget(self._connect_btn)
        main.addWidget(conn)

        # --- Área de salida (read-only) ---
        self._term = QTextEdit()
        self._term.setReadOnly(True)
        self._term.setFont(QFont("Consolas", 9))
        self._term.setPlaceholderText("Terminal not connected — click 'Start Terminal'")
        self._term.setLineWrapMode(QTextEdit.WidgetWidth)

        main.addWidget(self._term, 1)

        # --- Línea de entrada + controles ---
        controls = QFrame()
        ctl = QHBoxLayout(controls)
        ctl.setContentsMargins(0, 0, 0, 0)
        ctl.setSpacing(6)

        self._input = QLineEdit()
        self._input.setFont(QFont("Consolas", 9))
        self._input.setPlaceholderText("Type a command and press Send (Enter)")
        self._input.returnPressed.connect(self._on_send)

        self._send_btn = QPushButton("Send")
        self._send_btn.setFont(QFont("Inter", 9))
        self._send_btn.setEnabled(False)
        self._send_btn.clicked.connect(self._on_send)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setFont(QFont("Inter", 9))
        self._clear_btn.clicked.connect(self._on_clear)

        ctl.addWidget(self._input, 1)
        ctl.addWidget(self._send_btn)
        ctl.addWidget(self._clear_btn)
        main.addWidget(controls, 0)

        self.apply_theme()

    # -- helpers -----------------------------------------------------------
    def _set_status(self, text: str, color: str) -> None:
        self._conn_status.setText(text)
        self._conn_status.setStyleSheet("color: " + color + ";")

    def _append(self, text: str) -> None:
        cursor = self._term.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self._term.setTextCursor(cursor)
        scroll = self._term.verticalScrollBar()
        scroll.setValue(scroll.maximum())

    # -- websocket lifecycle ----------------------------------------------
    def _on_start(self) -> None:
        if self._ws is not None:
            return
        self._set_status(*_STATUS_CONNECTING)
        ws = QWebSocket()
        ws.connected.connect(self._on_connected)
        ws.disconnected.connect(self._on_disconnected)
        ws.binaryMessageReceived.connect(self._on_binary)
        ws.textMessageReceived.connect(self._on_text)
        ws.errorOccurred.connect(self._on_error)
        self._ws = ws
        ws.open(QUrl(TERMINAL_WS_URL))

    def _on_connected(self) -> None:
        self._set_status(*_STATUS_CONNECTED)
        self._send_btn.setEnabled(True)

    def _on_disconnected(self) -> None:
        self._set_status(*_STATUS_DISCONNECTED)
        self._send_btn.setEnabled(False)
        self._append("\n[terminal disconnected]\n")
        if self._ws is not None:
            ws, self._ws = self._ws, None
            ws.deleteLater()

    def _on_binary(self, message) -> None:
        payload = bytes(message.data())
        self._append(_strip_ansi(payload.decode("utf-8", errors="replace")))

    def _on_text(self, message: str) -> None:
        self._append(_strip_ansi(message))

    def _on_error(self, _error) -> None:  # noqa: ARG002
        self._set_status(*_STATUS_DISCONNECTED)
        self._send_btn.setEnabled(False)

    # -- actions -----------------------------------------------------------
    def _on_send(self) -> None:
        line = self._input.text()
        if not line:
            return
        ws = self._ws
        if ws is None or ws.state() != QAbstractSocket.SocketState.ConnectedState:
            return
        self._append(line + "\n")
        ws.sendBinaryMessage((line + "\r").encode("utf-8"))
        self._input.clear()

    def _on_clear(self) -> None:
        self._term.clear()

    # -- estilo ------------------------------------------------------------
    def apply_theme(self) -> None:
        theme = get_theme()
        ws = "background-color: " + theme.background + ";"
        sf = "background-color: " + theme.surface + ";"
        st = "border: 1px solid " + theme.stroke + ";"
        self.setStyleSheet(
            "QWidget {"
            + ws
            + "}QFrame {"
            + sf
            + "border-radius: 6px;"
            + st
            + "}QLabel {color: "
            + theme.text
            + ";}"
            + "QLineEdit {"
            + sf
            + st
            + "border-radius: 4px;padding: 4px;color: "
            + theme.text
            + ";}"
        )
