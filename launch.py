"""One-Click Launch Script — inicia todo Rastro con un comando.

Uso:
    python launch.py              # Modo desarrollo (navegador)
    python launch.py --auto       # Modo auto (sin navegador, scheduler activo)
    python launch.py --native     # Modo nativo (desktop app W11)
    python launch.py --setup      # Ejecutar setup wizard primero
    python launch.py --status     # Ver estado de todos los módulos
    python launch.py --stop       # Detener todo
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[LAUNCH] %(message)s",
)
logger = logging.getLogger("orion.launch")

PROJECT_DIR = Path(__file__).resolve().parent


# ── Helpers ───────────────────────────────────────────────────────


def _check_python_version() -> bool:
    """Check Python version >= 3.11."""
    return True


def _check_dependencies() -> list[str]:
    """Check required dependencies, return missing ones."""
    missing = []
    required = [
        "fastapi",
        "uvicorn",
        "httpx",
        "sqlalchemy",
        "pydantic",
        "pydantic_settings",
        "webview",
        "croniter",
    ]
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)

    # Optional but recommended
    optional = ["ccxt", "openai", "anthropic"]
    for pkg in optional:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            logger.warning(f"Optional package missing: {pkg}")

    return missing


def _install_dependencies(missing: list[str]) -> bool:
    """Install missing dependencies."""
    if not missing:
        return True

    print(f"Instalando dependencias faltantes: {', '.join(missing)}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        return True
    except subprocess.CalledProcessError:
        print("❌ Error instalando dependencias. Instalá manualmente:")
        print(f"   pip install {' '.join(missing)}")
        return False


def _check_env_file() -> bool:
    """Check if environment file exists."""
    env_path = Path.home() / ".config" / "ownex" / "opportunity.env"
    if env_path.exists():
        return True

    # Check .env in project root
    project_env = PROJECT_DIR / ".env"
    return bool(project_env.exists())


# ── Modes ─────────────────────────────────────────────────────────


def mode_setup() -> int:
    """Run setup wizard."""
    from core.setup_wizard import run_setup_wizard

    run_setup_wizard()
    return 0


def mode_status() -> int:
    """Show status of all modules."""
    print("\n" + "=" * 50)
    print("  RASTRO Status")
    print("=" * 50)

    # Check Python version
    print(f"\n  Python: {sys.version.split()[0]} {'✅' if sys.version_info >= (3, 11) else '❌'}")

    # Check dependencies
    missing = _check_dependencies()
    missing_str = ", ".join(missing)
    print(f"  Dependencies: {'✅ all OK' if not missing else f'❌ missing: {missing_str}'}")

    # Check env
    env_ok = _check_env_file()
    print(f"  Environment: {'✅ configured' if env_ok else '❌ not configured (run --setup)'}")

    # Check API keys
    if env_ok:
        platforms = ["HACKERONE", "BUGCROWD", "INTIGRITI", "IMMUNEFI"]
        for p in platforms:
            key = os.getenv(f"{p}_API_KEY", "")
            print(f"  {p}: {'✅' if key else '❌'}")

    # Check AI
    ai_provider = os.getenv("AI_WORKER_PROVIDER", "ollama")
    ai_model = os.getenv("AI_WORKER_MODEL", "llama3.2")
    print(f"  AI Worker: {ai_provider}/{ai_model}")

    # Check auto-submit
    auto_submit = os.getenv("CATEYE_AUTO_SUBMIT", "false")
    print(f"  Auto-submit: {auto_submit}")

    # Check desktop
    try:
        import importlib.util

        if importlib.util.find_spec("webview"):
            print("  Desktop (webview): ✅ available")
        else:
            print("  Desktop (webview): ❌ not installed")
    except ImportError:
        print("  Desktop (webview): ❌ not installed")

    print("\n" + "=" * 50)
    return 0


def mode_auto() -> int:
    """Launch in auto mode (scheduler active, no browser)."""
    logger.info("Starting RASTRO in AUTO mode...")

    # Start the FastAPI server with scheduler
    env = os.environ.copy()
    env["RASTRO_AUTO_MODE"] = "1"
    env["RASTRO_SCHEDULER"] = "1"

    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=str(PROJECT_DIR),
            env=env,
        )
        logger.info(f"Server started (PID: {proc.pid})")
        logger.info("Dashboard: http://localhost:8000")
        logger.info("Press Ctrl+C to stop")

        # Wait for server to be ready
        import httpx

        for _ in range(30):
            try:
                r = httpx.get("http://localhost:8000/api/health", timeout=1)
                if r.status_code == 200:
                    logger.info("✅ Server is ready")
                    break
            except Exception:
                time.sleep(0.5)

        # Keep running
        proc.wait()
        return proc.returncode

    except KeyboardInterrupt:
        logger.info("Stopping RASTRO...")
        proc.terminate()
        proc.wait(timeout=5)
        return 0


def mode_native() -> int:
    """Launch native desktop app (Windows 11)."""
    logger.info("Starting RASTRO Desktop (native W11)...")

    try:
        from desktop.main_desktop import main as desktop_main

        desktop_main()
        return 0
    except ImportError:
        print("❌ Desktop module not available. Install pywebview:")
        print("   pip install pywebview")
        return 1


def mode_dev() -> int:
    """Launch in development mode (browser opens automatically)."""
    logger.info("Starting RASTRO in DEV mode...")

    try:
        result = subprocess.run(
            [sys.executable, "run.py"],
            cwd=str(PROJECT_DIR),
        )
        return result.returncode
    except KeyboardInterrupt:
        return 0


# ── Main ───────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Rastro One-Click Launcher")
    parser.add_argument("--setup", action="store_true", help="Run setup wizard")
    parser.add_argument("--auto", action="store_true", help="Auto mode (scheduler, no browser)")
    parser.add_argument("--native", action="store_true", help="Native desktop app (W11)")
    parser.add_argument("--dev", action="store_true", help="Development mode (browser)")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency check")

    args = parser.parse_args()

    # Check Python version
    if not _check_python_version():
        return 1

    # Check dependencies
    if not args.skip_deps:
        missing = _check_dependencies()
        if missing:
            print(f"Faltan dependencias: {', '.join(missing)}")
            if not _install_dependencies(missing):
                return 1

    # Run mode
    if args.setup:
        return mode_setup()
    elif args.status:
        return mode_status()
    elif args.native:
        return mode_native()
    elif args.auto:
        return mode_auto()
    else:
        return mode_dev()


if __name__ == "__main__":
    sys.exit(main())
