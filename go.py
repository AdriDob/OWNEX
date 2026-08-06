"""Rastro Ultimate Launcher — un comando para dominarlos a todos.

Uso:
    python go                    # Modo desarrollo
    python go --auto             # Modo auto (scheduler + workers)
    python go --native           # Desktop nativo W11
    python go --setup            # Setup wizard
    python go --status           # Ver estado
    python go --stop             # Detener
    python go --build            # Compilar .exe
    python go --full-cycle       # Ejecutar un ciclo completo manual
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

logging.basicConfig(
    level=logging.INFO,
    format="[GO] %(message)s",
)
logger = logging.getLogger("orion.go")


def cmd_setup() -> int:
    """Run setup wizard."""
    from core.setup_wizard import run_setup_wizard

    run_setup_wizard()
    return 0


def cmd_status() -> int:
    """Show system status."""
    print("\n" + "=" * 60)
    print("  RASTRO Status")
    print("=" * 60)

    # Python version
    print(f"\n  Python: {sys.version.split()[0]}")

    # Dependencies
    required = ["fastapi", "uvicorn", "httpx", "sqlalchemy", "pydantic", "webview"]
    for pkg in required:
        try:
            __import__(pkg)
            print(f"  {pkg}: ✅")
        except ImportError:
            print(f"  {pkg}: ❌")

    # API keys
    keys = ["HACKERONE_API_KEY", "BUGCROWD_API_KEY", "IMMUNEFI_API_KEY", "OPENAI_API_KEY"]
    for key in keys:
        val = os.getenv(key, "")
        print(f"  {key}: {'✅' if val else '❌'}")

    # AI Worker
    print(f"  AI Worker: {os.getenv('AI_WORKER_PROVIDER', 'ollama')}/{os.getenv('AI_WORKER_MODEL', 'llama3.2')}")

    # Auto-submit
    print(f"  Auto-submit: {os.getenv('CATEYE_AUTO_SUBMIT', 'false')}")

    print("\n" + "=" * 60)
    return 0


def cmd_auto() -> int:
    """Start in auto mode."""
    logger.info("Starting RASTRO in AUTO mode...")

    env = os.environ.copy()
    env["RASTRO_AUTO_MODE"] = "1"

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(PROJECT_DIR),
        env=env,
    )

    logger.info(f"Server started (PID: {proc.pid})")
    logger.info("Dashboard: http://localhost:8000")
    logger.info("Press Ctrl+C to stop")

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait(timeout=5)

    return 0


def cmd_native() -> int:
    """Start native desktop app."""
    logger.info("Starting RASTRO Desktop (native W11)...")

    try:
        from desktop.enhanced_desktop import main as desktop_main

        desktop_main()
        return 0
    except ImportError:
        print("❌ Desktop module not available. Install: pip install pywebview")
        return 1


def cmd_build() -> int:
    """Build Windows executable."""
    logger.info("Building RASTRO Windows executable...")

    try:
        result = subprocess.run(
            [sys.executable, "desktop/build/build_desktop.py", "--onefile", "--name", "Rastro"],
            cwd=str(PROJECT_DIR),
        )
        return result.returncode
    except Exception as e:
        print(f"❌ Build failed: {e}")
        return 1


def cmd_full_cycle() -> int:
    """Run a full autonomous cycle manually."""

    async def _run():
        from core.full_auto import get_full_auto

        auto = get_full_auto()
        result = await auto.run_full_cycle()
        import json

        print(json.dumps(result, indent=2, default=str))

    asyncio.run(_run())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Rastro Ultimate Launcher")
    parser.add_argument("--setup", action="store_true", help="Run setup wizard")
    parser.add_argument("--auto", action="store_true", help="Auto mode")
    parser.add_argument("--native", action="store_true", help="Native desktop W11")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--build", action="store_true", help="Build .exe")
    parser.add_argument("--full-cycle", action="store_true", help="Run full cycle")

    args = parser.parse_args()

    if args.setup:
        return cmd_setup()
    elif args.status:
        return cmd_status()
    elif args.native:
        return cmd_native()
    elif args.build:
        return cmd_build()
    elif args.full_cycle:
        return cmd_full_cycle()
    else:
        return cmd_auto()


if __name__ == "__main__":
    sys.exit(main())
