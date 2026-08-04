#!/usr/bin/env python3
"""
Hermes Agent Development Environment Setup Script

This script sets up a complete development environment for Hermes Agent project.
It creates a virtual environment, installs dependencies, and verifies the setup.
"""

import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

# Constants
VENV_NAME = "venv_hermes3_9"
VENV_PATH = Path.home() / VENV_NAME
REQUIRED_PYTHON_VERSION = (3, 9, 0)


def check_python_version():
    """
    Check if the current Python version meets requirements.
    """
    current_version = sys.version_info
    version_tuple = (current_version.major, current_version.minor, current_version.micro)

    print(f"💻 Current Python version: {current_version.major}.{current_version.minor}.{current_version.micro}")
    print(
        f"🎯 Required Python version: {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}.{REQUIRED_PYTHON_VERSION[2]}"
    )

    if version_tuple >= REQUIRED_PYTHON_VERSION:
        print("✅ Python version requirement satisfied!")
        return True
    else:
        print("❌ Python version does not meet requirements!")
        print(
            f"   Please upgrade to Python {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}.{REQUIRED_PYTHON_VERSION[2]} or higher"
        )
        return False


def create_virtual_environment() -> dict[str, Any]:
    """
    Create virtual environment if it doesn't exist.
    """

    print(f"🔍 Checking virtual environment at: {VENV_PATH}")

    if VENV_PATH.exists():
        print(f"✅ Virtual environment already exists at: {VENV_PATH}")
        return {"status": "exists", "path": str(VENV_PATH), "message": "Virtual environment already exists"}

    print("🔨 Creating new virtual environment...")

    try:
        # Create virtual environment
        result = subprocess.run([sys.executable, "-m", "venv", str(VENV_PATH)], capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ Successfully created virtual environment at: {VENV_PATH}")

            # Get Python executable path
            if platform.system() == "Windows":
                python_executable = VENV_PATH / "Scripts" / "python.exe"
            else:
                python_executable = VENV_PATH / "bin" / "python"

            # Get Python version in new environment
            version_result = subprocess.run([str(python_executable), "--version"], capture_output=True, text=True)

            return {
                "status": "created",
                "path": str(VENV_PATH),
                "python_executable": str(python_executable),
                "activation_command": generate_activation_command(VENV_PATH),
                "python_version": version_result.stdout.strip(),
            }
        else:
            raise Exception(f"Failed to create virtual environment: {result.stderr}")

    except Exception as e:
        print(f"❌ Error creating virtual environment: {e}")
        return {"status": "error", "error": str(e)}


def generate_activation_command(venv_path: Path) -> str:
    """
    Generate appropriate activation command for the operating system.
    """
    if platform.system() == "Windows":
        return f"{venv_path / 'Scripts' / 'activate.bat'}"
    else:
        return f"source {venv_path / 'bin' / 'activate'}"


def install_essential_packages() -> dict[str, Any]:
    """
    Install essential packages for Hermes development.
    """

    # Essential packages for Hermes development
    essential_packages = [
        "requests>=2.25.1",
        "pytest>=6.2.5",
        "ruff>=0.1.5",
        "pytest-cov>=2.12.1",
        "pytest-timeout>=2.0.3",
        "pytest-html>=3.2.0",
        "requests>=2.25.1",
        "pytest>=6.2.0",
        "ruff>=0.1.0",
        "pytest-cov>=2.12.0",
    ]

    print("📦 Installing development packages...")

    try:
        # Get pip executable
        if platform.system() == "Windows":
            pip_executable = VENV_PATH / "Scripts" / "pip.exe"
        else:
            pip_executable = VENV_PATH / "bin" / "pip"

        for package in essential_packages:
            print(f"📥 Installing: {package}")

            result = subprocess.run([str(pip_executable), "install", package], capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ Successfully installed: {package}")
            else:
                print(f"❌ Failed to install {package}: {result.stderr}")
                return {"status": "error", "package": package, "error": result.stderr}

        print("✅ All packages installed successfully!")
        return {"status": "success", "packages_installed": len(essential_packages)}

    except Exception as e:
        print(f"❌ Error during package installation: {e}")
        return {"status": "error", "exception": str(e)}


def verify_virtual_environment() -> bool:
    """
    Verify that the virtual environment is correctly configured.
    """

    if not VENV_PATH.exists():
        print("❌ Virtual environment does not exist!")
        return False

    # Check Python executable in virtual environment
    python_executable = (
        VENV_PATH / "bin" / "python" if platform.system() != "Windows" else VENV_PATH / "Scripts" / "python.exe"
    )

    if not python_executable.exists():
        print("❌ Python executable not found in virtual environment!")
        return False

    # Try to execute a simple command
    try:
        result = subprocess.run([str(python_executable), "--version"], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Virtual environment is properly configured!")
            print(f"Python version: {result.stdout.strip()}")
            return True
        else:
            print("❌ Virtual environment Python execution failed!")
            return False

    except Exception as e:
        print(f"❌ Error testing virtual environment: {e}")
        return False


def main():
    """
    Main function to execute the entire virtual environment setup process.
    """

    print("🚀 Hermes Agent - Virtual Environment Setup")
    print("=" * 50)

    # Step 1: Check Python version
    if not check_python_version():
        print("❌ Python version check failed. Exiting.")
        return

    # Step 2: Create or verify virtual environment
    venv_setup = create_virtual_environment()
    print(f"🏗️ Virtual Environment Status: {venv_setup['status']}")

    # Step 3: Install dependencies if environment was created
    if venv_setup["status"] == "created":
        deps_status = install_essential_packages()
        print(f"📦 Dependencies Installation: {deps_status['status']}")

        if deps_status["status"] == "success":
            print("✨ Development environment is ready!")
            print("📁 You can now activate the virtual environment using:")
            print(f"   source {venv_setup['path']}/bin/activate")
            print("   Or on Windows:")
            print(f"   {venv_setup['path']}/Scripts/activate.bat")
        else:
            print(f"❌ Error during dependency installation: {deps_status['error']}")

    # Step 4: Verify virtual environment setup
    print("\n🔍 Verifying virtual environment setup...")
    verification_result = verify_virtual_environment()

    if verification_result:
        print("🎉 Development environment is ready for use!")
    else:
        print("❌ Development environment setup failed!")

    print("=" * 50)
    print("✨ Hermes Agent development environment setup completed!")

    return venv_setup


if __name__ == "__main__":
    main()
