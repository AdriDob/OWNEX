#!/usr/bin/env python3
"""OWNEX Backend — Standalone entry point for Tauri sidecar.

Build with PyInstaller (OWNEX-Backend.spec).
Runs as a self-contained .exe — no Python required on target machine.

CLI args:
    --port <port>       Backend port (default: 8000)
    --host <host>       Bind address (default: 127.0.0.1)
    --data-dir <path>   Data directory (default: %LOCALAPPDATA%/OWNEX)
    --log-level <level> Log level (default: INFO)
"""

import argparse
import os
import signal
import sys
from pathlib import Path


def _resolve_root() -> Path:
    """Find the project root or frozen bundle directory."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def _ensure_data_dirs(data_dir: Path) -> None:
    """Create writable data directories."""
    for sub in ("", "database", "logs"):
        (data_dir / sub).mkdir(parents=True, exist_ok=True)


def _setup_logging(data_dir: Path, level: str) -> None:
    """Configure logging to file + stderr."""
    import logging

    log_file = data_dir / "logs" / "backend.log"
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = None
    try:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
    except OSError:
        # Data dir may be unwritable in exotic setups — never lose diagnostics.
        print(f"[ownex-backend] WARNING: cannot write log file {log_file}", file=sys.stderr)

    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    sh.setLevel(getattr(logging, level.upper(), logging.INFO))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    if fh is not None:
        root.addHandler(fh)
    root.addHandler(sh)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OWNEX Backend Sidecar")
    parser.add_argument("--port", type=int, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--data-dir", default=None, help="Data directory (default: auto-detect)")
    parser.add_argument("--log-level", default="INFO", help="Log level (default: INFO)")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    root = _resolve_root()

    # Determine data directory
    if args.data_dir:
        data_dir = Path(args.data_dir)
    elif sys.platform == "win32":
        # %LOCALAPPDATA% — matches database.db.user_data_dir() frozen default
        # (which migrates legacy %APPDATA%/OWNEX data on first run).
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        data_dir = base / "OWNEX"
    else:
        data_dir = Path.home() / ".local" / "share" / "OWNEX"

    _ensure_data_dirs(data_dir)
    _setup_logging(data_dir, args.log_level)

    import logging

    logger = logging.getLogger("ownex.backend")
    logger.info("OWNEX Backend starting...")
    logger.info("  Root: %s", root)
    logger.info("  Data: %s", data_dir)
    logger.info("  Port: %d", args.port)
    logger.info("  Host: %s", args.host)
    logger.info("  Python: %s", sys.version)
    logger.info("  Frozen: %s", getattr(sys, "frozen", False))

    # Inject environment variables
    os.environ["OWNEX_DATA_DIR"] = str(data_dir)
    os.environ["OWNEX_DB_DIR"] = str(data_dir / "database")
    # Packaged bundle always runs in desktop posture: restrictive CORS branch
    # (Tauri origins + credentials) instead of the wildcard dev default.
    os.environ["OWNEX_DESKTOP"] = "1"

    # Add project root to sys.path
    sys.path.insert(0, str(root))

    # Validate imports
    try:
        import api.main  # noqa: F401

        logger.info("  api.main imported OK")
    except Exception as exc:
        logger.error("  Failed to import api.main: %s", exc)
        return 1

    # Signal handlers (SIGTERM only on Unix; Windows uses SIGBREAK)
    def _shutdown(sig, _frame):
        logger.info("Received signal %s, shutting down...", sig)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _shutdown)

    # Run uvicorn
    import uvicorn

    config = uvicorn.Config(
        "api.main:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower(),
        access_log=False,
    )
    server = uvicorn.Server(config)

    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
    except Exception as exc:
        logger.error("Server error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
