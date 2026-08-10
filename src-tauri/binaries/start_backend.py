#!/usr/bin/env python3
"""OWNEX Backend Launcher — Tauri sidecar entry point.

This script starts the Python API server and keeps it running.
Compiled to a standalone .exe via PyInstaller for Windows distribution.
Development: run manually with `python api/main.py`.
"""

import os
import signal
import subprocess
import sys


def main():
    """Start the OWNEX API server as a subprocess."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    if not os.path.exists(os.path.join(project_root, "api", "main.py")):
        project_root = os.getcwd()

    venv_python = os.path.join(project_root, ".venv", "Scripts" if sys.platform == "win32" else "bin", "python")
    api_entry = os.path.join(project_root, "api", "main.py")

    if not os.path.exists(api_entry):
        api_entry = os.path.join(project_root, "_internal", "api", "main.py")

    if not os.path.exists(api_entry):
        print(
            f"[orion-backend] api/main.py not found under {project_root} — "
            "backend must run manually (uvicorn api.main:app on :8000)"
        )
        sys.stdout.flush()
        return 1

    python_exe = venv_python if os.path.exists(venv_python) else sys.executable

    print(f"[orion-backend] Starting API server: {python_exe} {api_entry}")
    sys.stdout.flush()

    proc = subprocess.Popen(
        [python_exe, api_entry],
        cwd=project_root,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    def handle_signal(sig, frame):
        print(f"[orion-backend] Received signal {sig}, shutting down...")
        proc.terminate()
        proc.wait(timeout=10)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait(timeout=10)

    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
