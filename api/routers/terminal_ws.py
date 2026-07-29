"""
Terminal WebSocket endpoint — bridges a shell process to the browser-based terminal.

Connects to: ws://host:port/ws/terminal
Auth: token in query param (optional, inherits from auth middleware)

Provides a real shell (bash/powershell) inside the OWNEX Desktop terminal tab.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from contextlib import suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("cateye.api.terminal")

router = APIRouter()

# ── Help / MOTD ──────────────────────────────────────────────────
MOTD = (
    "\\r\\n"
    "\\x1b[36m╔══════════════════════════════════════════════════════╗\\x1b[0m\\r\\n"
    "\\x1b[36m║  \\x1b[1;34mOWNEX Terminal v5.0.0\\x1b[0m\\x1b[36m — Backend Shell Bridge    ║\\x1b[0m\\r\\n"
    "\\x1b[36m║  \\x1b[0mEjecutá cualquier comando del sistema aquí         \\x1b[36m║\\x1b[0m\\r\\n"
    "\\x1b[36m║  \\x1b[0mAtajos: Ctrl+L=clear · Ctrl+C=interrupt · Ctrl+D=exit\\x1b[36m ║\\x1b[0m\\r\\n"
    "\\x1b[36m╚══════════════════════════════════════════════════════╝\\x1b[0m\\r\\n"
    "\\r\\n"
)


def _detect_shell() -> list[str]:
    """Detect the best available shell for the current platform."""
    if sys.platform == "win32":
        for candidate in [
            ["powershell.exe", "-NoLogo", "-NoProfile"],
            ["pwsh.exe", "-NoLogo", "-NoProfile"],
            ["cmd.exe", "/Q"],
        ]:
            if _binary_exists(candidate[0]):
                return candidate
        return ["cmd.exe", "/Q"]
    else:
        user_shell = os.environ.get("SHELL", "/bin/bash")
        if user_shell and os.path.exists(user_shell):
            if "zsh" in user_shell:
                return [user_shell, "--no-rcs", "-i"]
            return [user_shell, "--norc", "-i"]
        return ["/bin/bash", "--norc", "-i"]


def _binary_exists(name: str) -> bool:
    """Check if a binary exists in PATH."""
    paths = os.environ.get("PATH", "").split(os.pathsep)
    for p in paths:
        full = os.path.join(p, name)
        if os.path.exists(full) and os.access(full, os.X_OK):
            return True
        full_exe = full + ".exe"
        if os.path.exists(full_exe):
            return True
    return False


async def _bridge_stdio(
    websocket: WebSocket,
    process: asyncio.subprocess.Process,
) -> None:
    """Bridge shell stdout/stderr → WebSocket, WebSocket → shell stdin."""

    async def _reader(stream: asyncio.StreamReader | None) -> None:
        """Read from shell stdout/stderr and send to WebSocket."""
        if stream is None:
            return
        try:
            while True:
                data = await stream.read(4096)
                if not data:
                    break
                await websocket.send_bytes(data)
        except (WebSocketDisconnect, ConnectionError):
            pass
        except Exception as exc:
            logger.debug("Terminal reader error: %s", exc)

    async def _writer() -> None:
        """Read from WebSocket and send to shell stdin."""
        try:
            while True:
                raw = await websocket.receive_bytes()
                if process.stdin and not process.stdin.is_closing():
                    process.stdin.write(raw)
                    await process.stdin.drain()
        except (WebSocketDisconnect, ConnectionError):
            pass
        except Exception as exc:
            logger.debug("Terminal writer error: %s", exc)

    try:
        with suppress(asyncio.CancelledError):
            await asyncio.gather(
                _reader(process.stdout),
                _reader(process.stderr),
                _writer(),
            )
    except asyncio.CancelledError:
        pass


@router.websocket("/api/ws/terminal")
async def terminal_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint that provides an interactive shell session.

    The user connects via the TerminalView.vue frontend component.
    A real shell process is spawned and its I/O is bridged to the WebSocket.
    """
    await websocket.accept()

    shell_cmd = _detect_shell()
    shell_name = os.path.basename(shell_cmd[0])
    logger.info("Terminal connecting: shell=%s platform=%s", shell_name, sys.platform)

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["LINES"] = "24"
    env["COLUMNS"] = "80"

    process: asyncio.subprocess.Process | None = None

    try:
        process = await asyncio.create_subprocess_exec(
            *shell_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=os.getcwd(),
        )

        logger.info("Shell spawned (PID=%s): %s", process.pid, " ".join(shell_cmd))

        await websocket.send_bytes(MOTD.encode())

        await _bridge_stdio(websocket, process)

    except FileNotFoundError:
        logger.error("Shell not found: %s", shell_cmd[0])
        await websocket.send_bytes(f"\\r\\n\\x1b[31mERROR: Shell '{shell_cmd[0]}' not found.\\x1b[0m\\r\\n".encode())
        await websocket.close(code=1011)
        return
    except Exception as exc:
        logger.error("Terminal error: %s", exc)
        await websocket.send_bytes(f"\\r\\n\\x1b[31mERROR: {exc}\\x1b[0m\\r\\n".encode())
        await websocket.close(code=1011)
        return
    finally:
        if process and process.returncode is None:
            with suppress(ProcessLookupError):
                process.send_signal(signal.SIGTERM)
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass

        logger.info("Terminal disconnected: shell=%s", shell_name)
